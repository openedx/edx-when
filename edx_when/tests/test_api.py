"""
Tests for course date signals tasks.
"""
from unittest.mock import Mock, patch
from django.test import TestCase
from opaque_keys.edx.keys import CourseKey, UsageKey
from django.contrib.auth import get_user_model
from datetime import datetime, timedelta, timezone

from edx_when.api import update_or_create_assignments_due_dates, UserDateHandler, _Assignment
from edx_when.models import ContentDate, DatePolicy, UserDate

User = get_user_model()


class TestUpdateAssignmentDatesForCourse(TestCase):
    """
    Tests for the update_assignment_dates_for_course task.
    """

    def setUp(self):
        self.course_key = CourseKey.from_string('course-v1:edX+DemoX+Demo_Course')
        self.course_key_str = str(self.course_key)
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            is_staff=True
        )
        self.block_key = UsageKey.from_string(
            'block-v1:edX+DemoX+Demo_Course+type@sequential+block@test1'
        )
        self.due_date = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)
        self.assignments = [
            Mock(
                title='Test Assignment',
                date=self.due_date,
                block_key=self.block_key,
                assignment_type='Homework'
            )
        ]

    def test_update_assignment_dates_new_records(self):
        """
        Test inserting new records when missing.
        """
        update_or_create_assignments_due_dates(self.course_key, self.assignments)

        content_date = ContentDate.objects.get(
            course_id=self.course_key,
            location=self.block_key
        )
        self.assertEqual(content_date.assignment_title, 'Test Assignment')
        self.assertEqual(content_date.block_type, 'Homework')
        self.assertEqual(content_date.policy.abs_date, self.due_date)

    def test_update_assignment_dates_existing_records(self):
        """
        Test updating existing records when values differ.
        """
        existing_policy = DatePolicy.objects.create(
            abs_date=datetime(2024, 6, 1, tzinfo=timezone.utc)
        )
        ContentDate.objects.create(
            course_id=self.course_key,
            location=self.block_key,
            field='due',
            block_type='Homework',
            policy=existing_policy,
            assignment_title='Old Title',
            course_name=self.course_key.course,
            subsection_name='Old Title'
        )
        new_assignment = Mock(
            title='Updated Assignment',
            date=self.due_date,
            block_key=self.block_key,
            assignment_type='Homework'
        )

        update_or_create_assignments_due_dates(self.course_key, [new_assignment])

        content_date = ContentDate.objects.get(
            course_id=self.course_key,
            location=self.block_key
        )
        self.assertEqual(content_date.assignment_title, 'Updated Assignment')
        self.assertEqual(content_date.policy.abs_date, self.due_date)

    def test_assignment_with_null_date(self):
        """
        Test handling assignments with null dates.
        """
        null_date_assignment = Mock(
            title='Null Date Assignment',
            date=None,
            block_key=self.block_key,
            assignment_type='Homework'
        )
        update_or_create_assignments_due_dates(self.course_key, [null_date_assignment])

        content_date_exists = ContentDate.objects.filter(
            course_id=self.course_key,
            location=self.block_key
        ).exists()
        self.assertFalse(content_date_exists)

    def test_assignment_with_missing_metadata(self):
        """
        Test handling assignments with missing metadata.
        """
        assignment = Mock(
            date=self.due_date,
            block_key=self.block_key,
        )
        update_or_create_assignments_due_dates(self.course_key, [assignment])

        content_date_exists = ContentDate.objects.filter(
            course_id=self.course_key,
            location=self.block_key
        ).exists()
        self.assertFalse(content_date_exists)

    def test_multiple_assignments(self, mock_get_assignments):
        """
        Test processing multiple assignments.
        """
        assignment1 = Mock(
            title='Assignment 1',
            date=self.due_date,
            block_key=self.block_key,
            assignment_type='Gradeable'
        )

        assignment2 = Mock(
            title='Assignment 2',
            date=datetime(2025, 1, 15, tzinfo=timezone.utc),
            block_key=UsageKey.from_string(
                'block-v1:edX+DemoX+Demo_Course+type@sequential+block@test2'
            ),
            assignment_type='Homework'
        )
        update_or_create_assignments_due_dates(self.course_key, [assignment1, assignment2])
        self.assertEqual(ContentDate.objects.count(), 2)

    def test_empty_assignments_list(self, mock_get_assignments):
        """
        Test handling empty assignments list.
        """
        update_or_create_assignments_due_dates(self.course_key, [])
        self.assertEqual(ContentDate.objects.count(), 0)

    @patch('edx_when.models.DatePolicy.objects.get_or_create')
    def test_date_policy_creation_exception(self, mock_policy_create, mock_get_assignments):
        """
        Test handling exception during DatePolicy creation.
        """
        assignment = Mock(
            title='Test Assignment',
            date=self.due_date,
            block_key=self.block_key,
            assignment_type='problem'
        )
        mock_policy_create.side_effect = Exception('Database Error')

        with self.assertRaises(Exception):
            update_or_create_assignments_due_dates(self.course_key, [assignment])


class TestGetUserDates(TestCase):
    """
    Test cases for the get_user_dates API function.
    """

    def test_get_user_dates_basic(self):
        """
        Test basic functionality of get_user_dates.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        block_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@test')

        policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=True,
            policy=policy,
            block_type='sequential'
        )

        result = api.get_user_dates(course_id, user_id)

        expected_key = (block_key, 'due')
        self.assertIn(expected_key, result)
        self.assertEqual(result[expected_key], datetime(2023, 1, 15, 10, 0, 0, tzinfo=timezone.utc))

    def test_get_user_dates_with_user_overrides(self):
        """
        Test get_user_dates with user overrides taking priority.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        block_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@test')

        policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        content_date = ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=True,
            policy=policy,
            block_type='sequential'
        )

        user = User.objects.create(username='testuser', id=user_id)
        UserDate.objects.create(
            user=user,
            content_date=content_date,
            abs_date=datetime(2023, 1, 20, 10, 0, 0)
        )

        result = api.get_user_dates(course_id, user_id)

        expected_key = (block_key, 'due')
        self.assertIn(expected_key, result)
        self.assertEqual(result[expected_key], datetime(2023, 1, 20, 10, 0, 0, tzinfo=timezone.utc))

    def test_get_user_dates_with_block_type_filter(self):
        """
        Test get_user_dates with block type filtering.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        seq_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@seq1')
        seq_policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=seq_key,
            field='due',
            active=True,
            policy=seq_policy,
            block_type='sequential'
        )

        seq_2_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@seq2')
        seq_2_policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 16, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=seq_2_key,
            field='due',
            active=True,
            policy=seq_2_policy,
            block_type='vertical'
        )

        result = api.get_user_dates(course_id, user_id, block_types=['sequential'])

        self.assertEqual(len(result), 1)
        self.assertIn((seq_key, 'due'), result)
        self.assertNotIn((seq_2_key, 'due'), result)

    def test_get_user_dates_with_block_keys_filter(self):
        """
        Test get_user_dates with specific block keys filtering.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        block1_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@seq1')
        block1_policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=block1_key,
            field='due',
            active=True,
            policy=block1_policy,
            block_type='sequential'
        )

        block2_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@seq2')
        block2_policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 16, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=block2_key,
            field='due',
            active=True,
            policy=block2_policy,
            block_type='sequential'
        )

        result = api.get_user_dates(course_id, user_id, block_keys=[block1_key])

        self.assertEqual(len(result), 1)
        self.assertIn((block1_key, 'due'), result)
        self.assertNotIn((block2_key, 'due'), result)

    def test_get_user_dates_with_date_types_filter(self):
        """
        Test get_user_dates with date type filtering.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        block_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@test')

        due_policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=True,
            policy=due_policy,
            block_type='sequential'
        )

        start_policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 10, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='start',
            active=True,
            policy=start_policy,
            block_type='sequential'
        )

        result = api.get_user_dates(course_id, user_id, date_types=['due'])

        self.assertEqual(len(result), 1)
        self.assertIn((block_key, 'due'), result)
        self.assertNotIn((block_key, 'start'), result)

    def test_get_user_dates_multiple_filters(self):
        """
        Test get_user_dates with multiple filters combined.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        seq_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@seq1')
        vert_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@vertical+block@vert1')

        seq_due_policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=seq_key,
            field='due',
            active=True,
            policy=seq_due_policy,
            block_type='sequential'
        )

        seq_start_policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 10, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=seq_key,
            field='start',
            active=True,
            policy=seq_start_policy,
            block_type='sequential'
        )

        vert_due_policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 16, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=vert_key,
            field='due',
            active=True,
            policy=vert_due_policy,
            block_type='vertical'
        )

        result = api.get_user_dates(
            course_id, user_id,
            block_types=['sequential'],
            date_types=['due']
        )

        self.assertEqual(len(result), 1)
        self.assertIn((seq_key, 'due'), result)
        self.assertNotIn((seq_key, 'start'), result)
        self.assertNotIn((vert_key, 'due'), result)

    def test_get_user_dates_inactive_dates_excluded(self):
        """
        Test that inactive content dates are excluded.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        block_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@test')

        policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=False,
            policy=policy,
            block_type='sequential'
        )

        result = api.get_user_dates(course_id, user_id)
        self.assertEqual(len(result), 0)

    def test_get_user_dates_missing_schedule_error_handled(self):
        """
        Test that MissingScheduleError is handled gracefully.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        block_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@test')

        policy = DatePolicy.objects.create(rel_date=timedelta(days=7))
        ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=True,
            policy=policy,
            block_type='sequential'
        )

        result = api.get_user_dates(course_id, user_id)
        self.assertEqual(len(result), 0)

    def test_get_user_dates_string_course_key(self):
        """
        Test get_user_dates with string course key.
        """
        course_id_str = 'course-v1:TestX+Test+2023'
        course_id = CourseKey.from_string(course_id_str)
        user_id = 123

        block_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@test')

        policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=True,
            policy=policy,
            block_type='sequential'
        )

        result = api.get_user_dates(course_id_str, user_id)

        expected_key = (block_key, 'due')
        self.assertIn(expected_key, result)

    def test_get_user_dates_string_block_keys(self):
        """
        Test get_user_dates with string block keys in filter.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        block_key_str = 'block-v1:TestX+Test+2023+type@sequential+block@test'
        block_key = UsageKey.from_string(block_key_str)

        policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=True,
            policy=policy,
            block_type='sequential'
        )

        result = api.get_user_dates(course_id, user_id, block_keys=[block_key_str])

        expected_key = (block_key, 'due')
        self.assertIn(expected_key, result)

    def test_get_user_dates_empty_result(self):
        """
        Test get_user_dates with no matching dates.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        result = api.get_user_dates(course_id, user_id)

        self.assertEqual(result, {})

    def test_get_user_dates_latest_user_override(self):
        """
        Test that the latest user override is used when multiple exist.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        block_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@test')

        policy = DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        content_date = ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=True,
            policy=policy,
            block_type='sequential'
        )

        user = User.objects.create(username='testuser', id=user_id)

        older_override = UserDate.objects.create(
            user=user,
            content_date=content_date,
            abs_date=datetime(2023, 1, 20, 10, 0, 0)
        )
        older_override.modified = datetime(2023, 1, 1, 10, 0, 0)
        older_override.save()

        newer_override = UserDate.objects.create(
            user=user,
            content_date=content_date,
            abs_date=datetime(2023, 1, 25, 10, 0, 0)
        )
        newer_override.modified = datetime(2023, 1, 2, 10, 0, 0)
        newer_override.save()

        result = api.get_user_dates(course_id, user_id)

        expected_key = (block_key, 'due')
        self.assertEqual(result[expected_key], datetime(2023, 1, 25, 10, 0, 0, tzinfo=timezone.utc))


class TestUserDateHandler(TestCase):
    """
    Tests for the UserDateHandler class, which manages creation, deletion, and synchronization of UserDate records
    for users in a given course.
    The tests verify that UserDateHandler correctly interacts with the database when handling course-level and
    assignment-level content dates. They focus on the public API methods of the handler:
    create_for_user, delete_for_user, sync_for_user.
    """

    def setUp(self):
        self.user = User.objects.create(username="test_user")
        self.course_key = CourseKey.from_string('course-v1:TestX+Test+2025')
        self.block_key = UsageKey.from_string('block-v1:TestX+Test+2025+type@sequential+block@test')
        self.course_block_key = UsageKey.from_string('block-v1:TestX+Test+2025+type@course+block@course')
        self.policy = DatePolicy.objects.create(abs_date=datetime(2025, 1, 15, 10, 0, 0))
        self.content_date = ContentDate.objects.create(
            course_id=self.course_key,
            location=self.block_key,
            field='due',
            active=True,
            policy=self.policy,
            block_type='sequential'
        )
        self.content_date_course_start = ContentDate.objects.create(
            course_id=self.course_key,
            location=self.course_block_key,
            field='start',
            active=True,
            policy=DatePolicy.objects.create(abs_date=datetime(2025, 1, 2)),
            block_type='course'
        )
        self.content_date_course_end = ContentDate.objects.create(
            course_id=self.course_key,
            location=self.course_block_key,
            field='end',
            active=True,
            policy=DatePolicy.objects.create(abs_date=datetime(2025, 1, 3)),
            block_type='course'
        )
        self.assignments = [
            _Assignment(
                title='Test Assignment 1',
                date=datetime(2025, 12, 31, 23, 59, 59, tzinfo=timezone.utc),
                block_key=self.block_key,
                assignment_type='Homework',
                first_component_block_id=self.block_key,
                contains_gated_content=False,

            )
        ]
        self.course_data = {
            "start": datetime(2025, 1, 1),
            "end": datetime(2025, 2, 1),
            "location": str(self.course_block_key),
        }
        self.handler = UserDateHandler(str(self.course_key))

    def test_user_dates_are_created(self):
        """
        Ensure that `create_for_user` correctly creates UserDate records for both course-level (start/end)
        and assignment-level dates when provided with course data and assignment input.

        This test verifies:
          - The expected number of UserDate objects is created.
          - The created UserDates are linked to the correct ContentDate rows.
        """
        self.handler.create_for_user(self.user.id, self.assignments, self.course_data)

        uds = UserDate.objects.filter(user_id=self.user.id)
        self.assertEqual(uds.count(), 3)
        self.assertSetEqual(
            {ud.content_date_id for ud in uds},
            {self.content_date.id, self.content_date_course_start.id, self.content_date_course_end.id})

    def test_user_dates_are_deleted(self):
        """
        Ensure that `delete_for_user` removes all UserDate records associated with a specific user and course.

        This test verifies:
         - UserDate rows associated with the target course are deleted.
         - UserDate rows associated with a different course are kept untouched.
        """
        ud_to_delete = UserDate.objects.create(user=self.user, content_date=self.content_date)

        course_key_2 = CourseKey.from_string('course-v1:Other+Course+2026')
        block_key_2 = UsageKey.from_string('block-v1:Other+Course+2026+type@sequential+block@test')
        policy_2 = DatePolicy.objects.create(abs_date=datetime(2026, 1, 15, 10, 0, 0))
        content_date_2 = ContentDate.objects.create(
            course_id=course_key_2,
            location=block_key_2,
            field='due',
            active=True,
            policy=policy_2,
            block_type='sequential'
        )
        ud_to_keep = UserDate.objects.create(user=self.user, content_date=content_date_2)

        self.handler.delete_for_user(self.user.id)

        self.assertFalse(UserDate.objects.filter(id=ud_to_delete.id).exists())
        self.assertTrue(UserDate.objects.filter(id=ud_to_keep.id).exists())

    def test_user_dates_are_synced(self):
        """
        Ensure that `sync_for_user` synchronizes the UserDate rows for a user by creating, updating, and deleting rows
        to reflect the current state. This test verifies that:
          - New UserDates are created when missing.
          - Existing UserDates are updated when values differ.
          - UserDates that no longer correspond to active content dates are deleted.
        """
        ud_to_update = UserDate.objects.create(
            user_id=self.user.id,
            content_date=self.content_date,
            first_component_block_id=self.block_key,
            is_content_gated=False,
        )
        content_date_2 = ContentDate.objects.create(
            course_id=self.course_key,
            location=UsageKey.from_string('block-v1:TestX+Test+2025+type@sequential+block@test3'),
            field='due',
            active=True,
            policy=DatePolicy.objects.create(abs_date=datetime(2026, 1, 1)),
            block_type='sequential'
        )
        ud_to_delete = UserDate.objects.create(user=self.user, content_date=content_date_2)

        block_key_1 = UsageKey.from_string('block-v1:TestX+Test+2025+type@sequential+block@test1')
        block_key_2 = UsageKey.from_string('block-v1:TestX+Test+2025+type@sequential+block@test2')

        content_date_2 = ContentDate.objects.create(
            course_id=self.course_key,
            location=block_key_2,
            field='due',
            active=True,
            policy=DatePolicy.objects.create(abs_date=datetime(2026, 1, 1)),
            block_type='sequential'
        )

        assignments = [
            _Assignment(
                title='Test Assignment 1',
                date=datetime(2025, 10, 10),
                block_key=self.block_key,
                assignment_type='Homework',
                # fields with new values that should be populated in the existing UserDate
                first_component_block_id=block_key_1,
                contains_gated_content=True,
            ),
            _Assignment(
                title='Test Assignment 2',
                date=datetime(2025, 11, 11),
                block_key=block_key_2,
                assignment_type='Lab',
                first_component_block_id=block_key_2,
                contains_gated_content=True,
            )
        ]
        course_data = {
            "start": datetime(2025, 1, 1),
            "end": datetime(2025, 2, 1),
            "location": str(self.course_key),
        }

        self.handler.sync_for_user(self.user.id, assignments, course_data)

        # Test create
        created_uds = UserDate.objects.filter(user=self.user, content_date=content_date_2)
        self.assertTrue(created_uds.exists())
        created_ud = created_uds[0]
        self.assertEqual(created_ud.first_component_block_id, block_key_2)
        self.assertTrue(created_ud.is_content_gated, True)

        # Test update
        updated_uds = UserDate.objects.filter(id=ud_to_update.id)
        self.assertTrue(updated_uds.exists())
        updated_ud = updated_uds[0]
        self.assertEqual(updated_ud.first_component_block_id, block_key_1)
        self.assertTrue(updated_ud.is_content_gated, True)

        # Test delete
        self.assertFalse(UserDate.objects.filter(id=ud_to_delete.id).exists())
