"""
Test cases for the api module of edx-when.
"""
from datetime import datetime, timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from opaque_keys.edx.keys import CourseKey, UsageKey

from edx_when import api, models

User = get_user_model()


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

        policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        models.ContentDate.objects.create(
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
        self.assertEqual(result[expected_key], datetime(2023, 1, 15, 10, 0, 0))

    def test_get_user_dates_with_user_overrides(self):
        """
        Test get_user_dates with user overrides taking priority.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        block_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@test')

        policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        content_date = models.ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=True,
            policy=policy,
            block_type='sequential'
        )

        user = User.objects.create(username='testuser', id=user_id)
        models.UserDate.objects.create(
            user=user,
            content_date=content_date,
            abs_date=datetime(2023, 1, 20, 10, 0, 0)
        )

        result = api.get_user_dates(course_id, user_id)

        expected_key = (block_key, 'due')
        self.assertIn(expected_key, result)
        self.assertEqual(result[expected_key], datetime(2023, 1, 20, 10, 0, 0))

    def test_get_user_dates_with_block_type_filter(self):
        """
        Test get_user_dates with block type filtering.
        """
        course_id = CourseKey.from_string('course-v1:TestX+Test+2023')
        user_id = 123

        seq_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@seq1')
        seq_policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        models.ContentDate.objects.create(
            course_id=course_id,
            location=seq_key,
            field='due',
            active=True,
            policy=seq_policy,
            block_type='sequential'
        )

        seq_2_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@seq2')
        seq_2_policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 16, 10, 0, 0))
        models.ContentDate.objects.create(
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
        block1_policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        models.ContentDate.objects.create(
            course_id=course_id,
            location=block1_key,
            field='due',
            active=True,
            policy=block1_policy,
            block_type='sequential'
        )

        block2_key = UsageKey.from_string('block-v1:TestX+Test+2023+type@sequential+block@seq2')
        block2_policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 16, 10, 0, 0))
        models.ContentDate.objects.create(
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

        due_policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        models.ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=True,
            policy=due_policy,
            block_type='sequential'
        )

        start_policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 10, 10, 0, 0))
        models.ContentDate.objects.create(
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

        seq_due_policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        models.ContentDate.objects.create(
            course_id=course_id,
            location=seq_key,
            field='due',
            active=True,
            policy=seq_due_policy,
            block_type='sequential'
        )

        seq_start_policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 10, 10, 0, 0))
        models.ContentDate.objects.create(
            course_id=course_id,
            location=seq_key,
            field='start',
            active=True,
            policy=seq_start_policy,
            block_type='sequential'
        )

        vert_due_policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 16, 10, 0, 0))
        models.ContentDate.objects.create(
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

        policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        models.ContentDate.objects.create(
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

        policy = models.DatePolicy.objects.create(rel_date=timedelta(days=7))
        models.ContentDate.objects.create(
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

        policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        models.ContentDate.objects.create(
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

        policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        models.ContentDate.objects.create(
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

        policy = models.DatePolicy.objects.create(abs_date=datetime(2023, 1, 15, 10, 0, 0))
        content_date = models.ContentDate.objects.create(
            course_id=course_id,
            location=block_key,
            field='due',
            active=True,
            policy=policy,
            block_type='sequential'
        )

        user = User.objects.create(username='testuser', id=user_id)

        older_override = models.UserDate.objects.create(
            user=user,
            content_date=content_date,
            abs_date=datetime(2023, 1, 20, 10, 0, 0)
        )
        older_override.modified = datetime(2023, 1, 1, 10, 0, 0)
        older_override.save()

        newer_override = models.UserDate.objects.create(
            user=user,
            content_date=content_date,
            abs_date=datetime(2023, 1, 25, 10, 0, 0)
        )
        newer_override.modified = datetime(2023, 1, 2, 10, 0, 0)
        newer_override.save()

        result = api.get_user_dates(course_id, user_id)

        expected_key = (block_key, 'due')
        self.assertEqual(result[expected_key], datetime(2023, 1, 25, 10, 0, 0))
