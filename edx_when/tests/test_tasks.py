from unittest.mock import Mock, patch
from django.test import TestCase
from opaque_keys.edx.keys import CourseKey, UsageKey
from edx_when.tasks import update_assignment_dates_for_course
from edx_when.models import ContentDate, DatePolicy
from django.contrib.auth import get_user_model
from datetime import datetime, timezone

User = get_user_model()


class TestUpdateAssignmentDatesForCourse(TestCase):
    
    def setUp(self):
        self.course_key = CourseKey.from_string('course-v1:edX+DemoX+Demo_Course')
        self.course_key_str = str(self.course_key)
        self.staff_user = User.objects.create_user(
            username='staff_user',
            email='staff@example.com',
            is_staff=True
        )
        self.block_key = UsageKey.from_string(
            'block-v1:edX+DemoX+Demo_Course+type@sequential@test1'
        )
        self.due_date = datetime(2024, 12, 31, 23, 59, 59, tzinfo=timezone.utc)

    @patch('edx_when.tasks.get_course_assignments')
    def test_update_assignment_dates_new_records(self, mock_get_assignments):
        """
        Test inserting new records when missing.
        """
        assignment = Mock()
        assignment.title = 'Test Assignment'
        assignment.date = self.due_date
        assignment.block_key = self.block_key
        assignment.assignment_type = 'Homework'
        mock_get_assignments.return_value = [assignment]

        update_assignment_dates_for_course(self.course_key_str)

        content_date = ContentDate.objects.get(
            course_id=self.course_key,
            location=self.block_key
        )
        self.assertEqual(content_date.assignment_title, 'Test Assignment')
        self.assertEqual(content_date.block_type, 'problem')
        self.assertEqual(content_date.policy.abs_date, self.due_date)

    @patch('edx_when.tasks.get_course_assignments')
    def test_update_assignment_dates_existing_records(self, mock_get_assignments):
        """
        Test updating existing records when values differ.
        """
        existing_policy = DatePolicy.objects.create(
            abs_date=datetime(2024, 6, 1, tzinfo=timezone.utc)
        )
        ContentDate.objects.create(
            course_id=self.course_key,
            location=self.block_key,
            field='date',
            block_type='Homework',
            policy=existing_policy,
            assignment_title='Old Title',
            course_name=self.course_key.course,
            subsection_name='Old Title'
        )

        assignment = Mock()
        assignment.title = 'Updated Assignment'
        assignment.date = self.due_date
        assignment.block_key = self.block_key
        assignment.assignment_type = 'Homework'
        mock_get_assignments.return_value = [assignment]

        update_assignment_dates_for_course(self.course_key_str)

        content_date = ContentDate.objects.get(
            course_id=self.course_key,
            location=self.block_key
        )
        self.assertEqual(content_date.assignment_title, 'Updated Assignment')
        self.assertEqual(content_date.policy.abs_date, self.due_date)

    @patch('edx_when.tasks.get_course_assignments')
    def test_missing_staff_user(self, mock_get_assignments):
        """
        Test graceful handling when no staff user exists.
        """
        User.objects.filter(is_staff=True).delete()

        update_assignment_dates_for_course(self.course_key_str)

        mock_get_assignments.assert_not_called()

    @patch('edx_when.tasks.get_course_assignments')
    def test_assignment_with_null_date(self, mock_get_assignments):
        """
        Test handling assignments with null dates.
        """
        assignment = Mock()
        assignment.title = 'No Due Date Assignment'
        assignment.date = None
        assignment.block_key = self.block_key
        assignment.assignment_type = 'Homework'
        mock_get_assignments.return_value = [assignment]

        update_assignment_dates_for_course(self.course_key_str)

        content_date = ContentDate.objects.filter(
            course_id=self.course_key,
            location=self.block_key
        ).first()
        self.assertIsNone(content_date)

    @patch('edx_when.tasks.get_course_assignments')
    def test_assignment_with_missing_metadata(self, mock_get_assignments):
        """
        Test handling assignments with missing metadata.
        """
        assignment = Mock()
        assignment.title = None
        assignment.date = self.due_date
        assignment.block_key = self.block_key
        assignment.assignment_type = None
        mock_get_assignments.return_value = [assignment]

        update_assignment_dates_for_course(self.course_key_str)

        content_date = ContentDate.objects.get(
            course_id=self.course_key,
            location=self.block_key
        )
        self.assertIsNone(content_date.assignment_title)
        self.assertIsNone(content_date.block_type)

    @patch('edx_when.tasks.get_course_assignments')
    def test_unsupported_block_types(self, mock_get_assignments):
        """
        Test handling unsupported block types.
        """
        assignment = Mock()
        assignment.title = 'Unsupported Block'
        assignment.date = self.due_date
        assignment.block_key = self.block_key
        assignment.block_type = 'unsupported_type'
        mock_get_assignments.return_value = [assignment]

        update_assignment_dates_for_course(self.course_key_str)

        content_date = ContentDate.objects.get(
            course_id=self.course_key,
            location=self.block_key
        )
        self.assertEqual(content_date.block_type, 'unsupported_type')
        self.assertEqual(content_date.assignment_title, 'Unsupported Block')

    @patch('edx_when.tasks.get_course_assignments')
    def test_multiple_assignments(self, mock_get_assignments):
        """
        Test processing multiple assignments.
        """
        assignment1 = Mock()
        assignment1.title = 'Assignment 1'
        assignment1.date = self.due_date
        assignment1.block_key = self.block_key
        assignment1.assignment_type = 'Gradeable'

        assignment2 = Mock()
        assignment2.title = 'Assignment 2'
        assignment2.date = datetime(2025, 1, 15, tzinfo=timezone.utc)
        assignment2.block_key = UsageKey.from_string(
            'block-v1:edX+DemoX+Demo_Course+type@sequential@test2'
        )
        assignment2.assignment_type = 'Homework'

        mock_get_assignments.return_value = [assignment1, assignment2]

        update_assignment_dates_for_course(self.course_key_str)

        self.assertEqual(ContentDate.objects.count(), 2)

    @patch('edx_when.tasks.get_course_assignments')
    def test_invalid_course_key(self, mock_get_assignments):
        """
        Test handling invalid course key.
        """
        with self.assertRaises(Exception):
            update_assignment_dates_for_course('invalid-course-key')

    @patch('edx_when.tasks.get_course_assignments')
    def test_get_course_assignments_exception(self, mock_get_assignments):
        """
        Test handling exception from get_course_assignments.
        """
        mock_get_assignments.side_effect = Exception('API Error')

        with self.assertRaises(Exception):
            update_assignment_dates_for_course(self.course_key_str)

    @patch('edx_when.tasks.get_course_assignments')
    def test_empty_assignments_list(self, mock_get_assignments):
        """
        Test handling empty assignments list.
        """
        mock_get_assignments.return_value = []

        update_assignment_dates_for_course(self.course_key_str)

        self.assertEqual(ContentDate.objects.count(), 0)

    @patch('edx_when.tasks.get_course_assignments')
    @patch('edx_when.models.DatePolicy.objects.get_or_create')
    def test_date_policy_creation_exception(self, mock_policy_create, mock_get_assignments):
        """
        Test handling exception during DatePolicy creation.
        """
        assignment = Mock()
        assignment.title = 'Test Assignment'
        assignment.date = self.due_date
        assignment.block_key = self.block_key
        assignment.assignment_type = 'problem'
        mock_get_assignments.return_value = [assignment]
        mock_policy_create.side_effect = Exception('Database Error')

        with self.assertRaises(Exception):
            update_assignment_dates_for_course(self.course_key_str)
