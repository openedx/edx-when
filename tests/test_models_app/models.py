# -*- coding: utf-8 -*-

"""
Dummy models for use when testing edx-when
"""

from django.contrib.auth import get_user_model
from django.db import models
from opaque_keys.edx.django.models import CourseKeyField


class DummyCourse(models.Model):
    """
    .. no_pii:
    """

    id = CourseKeyField(db_index=True, primary_key=True, max_length=255)


class DummyEnrollment(models.Model):
    """
    .. no_pii:
    """

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE, related_name="courseenrollment_set")

    course = models.ForeignKey(
        DummyCourse,
        db_constraint=False,
        on_delete=models.DO_NOTHING,
    )

    is_active = models.BooleanField(default=True)


class DummySchedule(models.Model):
    """
    .. no_pii:
    """

    created = models.DateTimeField()
    enrollment = models.OneToOneField(DummyEnrollment, null=False, on_delete=models.CASCADE, related_name="schedule")
    start_date = models.DateTimeField(
        db_index=True,
        help_text='Date this schedule went into effect'
    )

    def __init__(self, *args, created=None, start_date=None, **kwargs):
        # Ensure we have a created value, if possible
        if not created and start_date:
            created = start_date
        super().__init__(*args, created=created, start_date=start_date, **kwargs)
