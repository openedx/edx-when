"""
Tests for edx_when.api
"""
from __future__ import absolute_import, unicode_literals

from datetime import datetime

import six
from django.contrib.auth.models import User
from django.test import TestCase

from edx_when import api, models
from test_utils import make_block_id, make_items


class ApiTests(TestCase):
    """
    Tests for edx_when.api
    """
    def test_set_dates_for_course(self):
        items = make_items()
        api.set_dates_for_course(items[0][0].course_key, items)

        cdates = models.ContentDate.objects.all()
        assert len(cdates) == 3

    def test_get_dates_for_course(self):
        items = make_items()
        api.set_dates_for_course(items[0][0].course_key, items)
        retrieved = api.get_dates_for_course(items[0][0].course_key)
        assert len(retrieved) == 3
        first = items[0]
        assert retrieved[(first[0], 'due')] == first[1]['due']

        # second time is cached
        retrieved = api.get_dates_for_course(items[0][0].course_key)
        assert len(retrieved) == 3

    def test_set_user_override(self):
        user = User(username='tester', email='tester@test.com')
        user.save()
        items = make_items()
        first = items[0]
        block_id = first[0]
        api.set_dates_for_course(six.text_type(block_id.course_key), items)

        override_date = datetime(2019, 4, 6)
        api.set_date_for_block(block_id.course_key, block_id, 'due', override_date, user=user)
        retrieved = api.get_dates_for_course(block_id.course_key, user=user)
        assert len(retrieved) == 3
        assert retrieved[block_id, 'due'] == override_date

        with self.assertRaises(api.MissingDateError):
            # can't set a user override for content without a date
            bad_block_id = make_block_id()
            api.set_date_for_block(bad_block_id.course_key, bad_block_id, 'due', override_date, user=user)

        with self.assertRaises(api.InvalidDateError):
            # can't set an override in the past
            invalid_date = datetime(2000, 1, 1)
            api.set_date_for_block(block_id.course_key, block_id, 'due', invalid_date, user=user)

        overrides = api.get_overrides_for_block(block_id.course_key, block_id)
        assert len(overrides) == 1
        assert overrides[0][2] == override_date

        overrides = list(api.get_overrides_for_user(block_id.course_key, user))
        assert len(overrides) == 1
        assert overrides[0] == {'location': block_id, 'actual_date': override_date}
