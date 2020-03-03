#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Tests for the `edx-when` models module.
"""

from __future__ import absolute_import, unicode_literals

from datetime import datetime, timedelta

import ddt
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.test import TestCase
from mock import patch

from edx_when.models import ContentDate, DatePolicy
from tests.test_models_app.models import DummyCourse, DummyEnrollment, DummySchedule

User = get_user_model()


@ddt.ddt
class TestDatePolicy(TestCase):
    """
    Tests of the DatePolicy model.
    """

    @ddt.data(
        (None, None, None, None),
        (datetime(2020, 1, 1), None, None, datetime(2020, 1, 1)),
        (datetime(2020, 1, 1), None, DummySchedule(start_date=datetime(2020, 3, 1)), datetime(2020, 1, 1)),
        (None, timedelta(days=1), DummySchedule(start_date=datetime(2020, 1, 1)), datetime(2020, 1, 2)),
        (datetime(2020, 3, 1), timedelta(days=1), DummySchedule(start_date=datetime(2020, 1, 1)), datetime(2020, 1, 2)),
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
        with self.assertRaises(ValueError):
            policy.actual_date(schedule)

    def test_mixed_dates(self):
        with self.assertRaises(ValidationError):
            DatePolicy(abs_date=datetime(2020, 1, 1), rel_date=timedelta(days=1)).full_clean()


class TestContentDate(TestCase):
    """
    Tests of the ContentDate model.
    """
    def setUp(self):
        super(TestContentDate, self).setUp()
        self.course = DummyCourse(id='course-v1:edX+Test+Course')
        self.course.save()

        self.user = User()
        self.user.save()

        self.enrollment = DummyEnrollment(user=self.user, course=self.course)
        self.enrollment.save()

        self.schedule = DummySchedule(enrollment=self.enrollment, start_date=datetime(2020, 1, 1))
        self.schedule.save()

        self.policy = DatePolicy(abs_date=datetime(2020, 1, 1))
        self.content_date = ContentDate(course_id=self.course.id, policy=self.policy)

    @patch('edx_when.models.Schedule', DummySchedule)
    def test_schedule_for_user_id(self):
        assert self.content_date.schedule_for_user(self.user.id) == self.schedule

    @patch('edx_when.models.Schedule', wraps=DummySchedule)
    def test_schedule_for_user_with_object_does_not_exist(self, dummy_schedule):
        """Test that None is returned when schedules are fetched for user."""
        dummy_schedule.objects.get.side_effect = ObjectDoesNotExist()
        assert self.content_date.schedule_for_user(self.user) is None

    @patch('edx_when.models.Schedule', None)
    def test_schedule_for_user_id_no_schedule_installed(self):
        assert self.content_date.schedule_for_user(self.user.id) is None

    @patch('edx_when.models.Schedule', DummySchedule)
    def test_schedule_for_user_obj(self):
        assert self.content_date.schedule_for_user(self.user) == self.schedule

    @patch('edx_when.models.Schedule', wraps=DummySchedule)
    def test_schedule_for_user_obj_no_enrollments(self, mock_schedule):
        mock_schedule.objects.get.side_effect = ObjectDoesNotExist()
        assert self.content_date.schedule_for_user(self.user) is None


class TestUserDate(TestCase):
    """
    Tests of the UserDate model.
    """

    def test_something(self):
        """TODO: Write real test cases."""
        pass
