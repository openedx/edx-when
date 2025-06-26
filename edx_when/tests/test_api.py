"""
Tests for course date signals tasks.
"""
from unittest.mock import Mock, patch
from django.test import TestCase
from opaque_keys.edx.keys import CourseKey, UsageKey
from django.contrib.auth import get_user_model
from datetime import datetime, timezone

from edx_when.api import update_or_create_assignments_due_dates
from edx_when.models import ContentDate, DatePolicy

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
