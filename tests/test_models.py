#!/usr/bin/env python
"""
Tests for the `edx-when` models module.
"""

from datetime import datetime, timedelta

import ddt
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from edx_when.models import DatePolicy, MissingScheduleError
from tests.test_models_app.models import DummySchedule

User = get_user_model()


@ddt.ddt
class TestDatePolicy(TestCase):
    """
    Tests of the DatePolicy model.
    """

    @ddt.data(
        (None, None, None, None),
        (datetime(2020, 1, 1), None, None, datetime(2020, 1, 1)),
        (datetime(2020, 1, 1), None,
            DummySchedule(created=datetime(2020, 3, 1), start_date=datetime(2020, 3, 1)), datetime(2020, 1, 1)),
        (None, timedelta(days=1),
            DummySchedule(created=datetime(2020, 1, 1), start_date=datetime(2020, 1, 1)), datetime(2020, 1, 2)),
        (datetime(2020, 3, 1), timedelta(days=1),
            DummySchedule(created=datetime(2020, 1, 1), start_date=datetime(2020, 1, 1)), datetime(2020, 1, 2)),
    )
    @ddt.unpack
    def test_actual_date(self, abs_date, rel_date, schedule, expected):
        policy = DatePolicy(abs_date=abs_date, rel_date=rel_date)
        assert policy.actual_date(schedule) == expected

    @ddt.data(
        (None, timedelta(days=1), None),
        (datetime(2020, 1, 1), timedelta(days=1), None),
    )
    @ddt.unpack
    def test_actual_date_failure(self, abs_date, rel_date, schedule):
        policy = DatePolicy(abs_date=abs_date, rel_date=rel_date)
        with self.assertRaises(MissingScheduleError):
            policy.actual_date(schedule)

    def test_actual_date_schedule_after_end(self):
        # This only applies for relative dates so we are not testing abs date.
        policy = DatePolicy(rel_date=timedelta(days=1))
        schedule = DummySchedule(created=datetime(2020, 4, 1), start_date=datetime(2020, 4, 1))
        self.assertIsNone(policy.actual_date(schedule, end_datetime=datetime(2020, 1, 1)))

    def test_actual_date_schedule_after_cutoff(self):
        # This only applies for relative dates so we are not testing abs date.
        day = timedelta(days=1)
        policy = DatePolicy(rel_date=day)
        schedule = DummySchedule(created=datetime(2020, 4, 1), start_date=datetime(2020, 4, 1))
        self.assertIsNone(policy.actual_date(schedule, cutoff_datetime=schedule.created - day))
        self.assertIsNotNone(policy.actual_date(schedule, cutoff_datetime=schedule.created + day))

    def test_mixed_dates(self):
        with self.assertRaises(ValidationError):
            DatePolicy(abs_date=datetime(2020, 1, 1), rel_date=timedelta(days=1)).full_clean()
