"""
Tests for edx_when.api
"""
from __future__ import absolute_import, unicode_literals

from datetime import datetime, timedelta

import ddt
import six
from django.contrib.auth.models import User
from django.test import TestCase
from edx_django_utils.cache.utils import DEFAULT_REQUEST_CACHE
from mock import patch

from edx_when import api, models
from test_utils import make_block_id, make_items

NUM_OVERRIDES = 3


@ddt.ddt
class ApiTests(TestCase):
    """
    Tests for edx_when.api
    """
    def setUp(self):
        super(ApiTests, self).setUp()
        self.user = User(username='tester', email='tester@test.com')
        self.user.save()
        self.schedule = Mock(name="schedule", start=datetime(2019, 4, 1))

        User.enrollments = Mock(name="enrollments")
        User.enrollments.find_one.return_value.schedule = self.schedule
        self.addCleanup(delattr, User, 'enrollments')

        mock_Schedule = Mock(name="Schedule")
        mock_Schedule.objects.find_one.return_value = self.schedule
        schedule_patcher = patch('edx_when.models.Schedule', mock_Schedule)
        schedule_patcher.start()
        self.addCleanup(schedule_patcher.stop)

        DEFAULT_REQUEST_CACHE.clear()

    def test_set_dates_for_course(self):
        items = make_items()
        api.set_dates_for_course(items[0][0].course_key, items)

        cdates = models.ContentDate.objects.all()
        assert len(cdates) == NUM_OVERRIDES

    def test_get_dates_for_course(self):
        items = make_items()
        api.set_dates_for_course(items[0][0].course_key, items)
        retrieved = api.get_dates_for_course(items[0][0].course_key)
        assert len(retrieved) == NUM_OVERRIDES
        first = items[0]
        assert retrieved[(first[0], 'due')] == first[1]['due']

        # second time is cached
        retrieved = api.get_dates_for_course(items[0][0].course_key)
        assert len(retrieved) == NUM_OVERRIDES

        # third time with new course_id
        new_items = make_items('testX+tt202+2019')
        api.set_dates_for_course(new_items[0][0].course_key, new_items)
        new_retrieved = api.get_dates_for_course(new_items[0][0].course_key)
        assert len(new_retrieved) == NUM_OVERRIDES
        first_id = list(new_retrieved.keys())[0][0]
        last_id = list(retrieved.keys())[0][0]
        assert first_id.course_key != last_id.course_key
        return items

    def test_clear_dates_for_course(self):
        items = self.test_get_dates_for_course()
        api.clear_dates_for_course(items[0][0].course_key)
        retrieved = api.get_dates_for_course(items[0][0].course_key, use_cached=False)
        assert not retrieved

    def test_set_user_override_invalid_block(self):
        items = make_items()
        first = items[0]
        block_id = first[0]
        api.set_dates_for_course(six.text_type(block_id.course_key), items)

        with self.assertRaises(api.MissingDateError):
            # can't set a user override for content without a date
            bad_block_id = make_block_id()
            api.set_date_for_block(bad_block_id.course_key, bad_block_id, 'due', datetime(2019, 4, 6), user=self.user)

    @ddt.data(
        (datetime(2019, 4, 6), datetime(2019, 4, 3)),
        (datetime(2019, 4, 6), timedelta(days=-1)),
        (timedelta(days=5), timedelta(days=-1)),
    )
    @ddt.unpack
    def test_set_user_override_invalid_date(self, initial_date, override_date):
        items = make_items()
        first = items[0]
        block_id = first[0]
        items[0][1]['due'] = initial_date
        api.set_dates_for_course(six.text_type(block_id.course_key), items)

        with self.assertRaises(api.InvalidDateError):
            api.set_date_for_block(block_id.course_key, block_id, 'due', override_date, user=self.user)

    @ddt.data(
        (datetime(2019, 4, 6), datetime(2019, 4, 10), datetime(2019, 4, 10)),
        (datetime(2019, 4, 6), timedelta(days=3), datetime(2019, 4, 9)),
        (timedelta(days=3), datetime(2019, 4, 10), datetime(2019, 4, 10)),
        (timedelta(days=3), timedelta(days=2), datetime(2019, 4, 6)),
    )
    @ddt.unpack
    def test_set_user_override(self, initial_date, override_date, expected_date):
        items = make_items()
        first = items[0]
        block_id = first[0]
        items[0][1]['due'] = initial_date

        api.set_dates_for_course(six.text_type(block_id.course_key), items)

        api.set_date_for_block(block_id.course_key, block_id, 'due', override_date, user=self.user)
        DEFAULT_REQUEST_CACHE.clear()
        retrieved = api.get_dates_for_course(block_id.course_key, user=self.user.id)
        assert len(retrieved) == NUM_OVERRIDES
        assert retrieved[block_id, 'due'] == expected_date

        overrides = api.get_overrides_for_block(block_id.course_key, block_id)
        assert len(overrides) == 1
        assert overrides[0][2] == expected_date

        overrides = list(api.get_overrides_for_user(block_id.course_key, self.user))
        assert len(overrides) == 1
        assert overrides[0] == {'location': block_id, 'actual_date': expected_date}

    @ddt.data(
        (datetime(2019, 4, 6), datetime(2019, 4, 10), datetime(2019, 4, 10)),
        (datetime(2019, 4, 6), timedelta(days=3), datetime(2019, 4, 9)),
        (timedelta(days=3), datetime(2019, 4, 10), datetime(2019, 4, 10)),
        (timedelta(days=3), timedelta(days=2), datetime(2019, 4, 6)),
    )
    @ddt.unpack
    def test_remove_user_override(self, initial_date, override_date, expected_date):
        items = make_items()
        first = items[0]
        block_id = first[0]
        items[0][1]['due'] = initial_date

        api.set_dates_for_course(six.text_type(block_id.course_key), items)

        api.set_date_for_block(block_id.course_key, block_id, 'due', override_date, user=self.user)
        DEFAULT_REQUEST_CACHE.clear()
        retrieved = api.get_dates_for_course(block_id.course_key, user=self.user.id)
        assert len(retrieved) == NUM_OVERRIDES
        assert retrieved[block_id, 'due'] == expected_date

        api.set_date_for_block(block_id.course_key, block_id, 'due', None, user=self.user)
        DEFAULT_REQUEST_CACHE.clear()
        retrieved = api.get_dates_for_course(block_id.course_key, user=self.user.id)
        assert len(retrieved) == NUM_OVERRIDES
        if isinstance(initial_date, timedelta):
            user_initial_date = self.schedule.start + initial_date
        else:
            user_initial_date = initial_date
        assert retrieved[block_id, 'due'] == user_initial_date

    def test_get_date_for_block(self):
        items = make_items()
        course_id = items[0][0].course_key
        api.set_dates_for_course(course_id, items)
        block_id, data = items[0]
        assert api.get_date_for_block(course_id, block_id, user=self.user) == data['due']
        assert api.get_date_for_block(course_id, 'bad', user=self.user) is None

    def test_is_enabled(self):
        items = make_items()
        course_id = items[0][0].course_key
        assert not api.is_enabled_for_course(course_id)
        api.set_dates_for_course(course_id, items)
        assert api.is_enabled_for_course(course_id)
