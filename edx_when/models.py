# -*- coding: utf-8 -*-
"""
Database models for edx_when.
"""

from __future__ import absolute_import, unicode_literals

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField

try:
    from openedx.core.djangoapps.schedule import Schedule
# TODO: Move schedules into edx-when
except ImportError:
    Schedule = None


@python_2_unicode_compatible
class DatePolicy(TimeStampedModel):
    """
    TODO: replace with a brief description of the model.

    .. no_pii:
    """

    abs_date = models.DateTimeField(null=True, blank=True, db_index=True)
    rel_date = models.DurationField(null=True, blank=True, db_index=True)

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        # TODO: return a string appropriate for the data fields
        return '<DatePolicy, ID: {}>'.format(self.id)

    def actual_date(self, schedule=None):
        """
        Return the normalized date.
        """
        if self.rel_date is not None:
            if schedule is None:
                raise ValueError(
                    "Can't interpret relative date {} for {!r} without a user schedule".format(
                        self.rel_date,
                        self
                    )
                )
            return schedule.start_date + self.rel_date
        else:
            return self.abs_date

    def clean(self):
        """
        Validate data before saving.
        """
        if self.abs_date and self.rel_date:
            raise ValidationError(_("Absolute and relative dates cannot both be used"))


@python_2_unicode_compatible
class ContentDate(models.Model):
    """
    TODO: replace with a brief description of the model.

    .. no_pii:
    """

    course_id = CourseKeyField(db_index=True, max_length=255)
    policy = models.ForeignKey(DatePolicy, on_delete=models.CASCADE)
    location = UsageKeyField(null=True, default=None, db_index=True, max_length=255)
    field = models.CharField(max_length=255, default='')
    active = models.BooleanField(default=True, db_index=True)

    class Meta:
        """Django Metadata."""

        unique_together = ('policy', 'location', 'field')

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        # TODO: return a string appropriate for the data fields
        return '<ContentDate, ID: {}>'.format(self.id)

    def schedule_for_user(self, user):
        """
        Return the schedule for the supplied user that applies to this piece of content.
        """
        if isinstance(user, int):
            if Schedule is None:
                return None

            return Schedule.objects.get(enrollment__user__id=user, enrollment__course__id=self.course_id)
        else:
            if not hasattr(user, 'courseenrollment_set'):
                return None

            # TODO: This will break prefetching, if the user object already had enrollments/schedules prefetched
            return user.courseenrollment_set.get(course__id=self.course_id).schedule


@python_2_unicode_compatible
class UserDate(TimeStampedModel):
    """
    TODO: replace with a brief description of the model.

    .. no_pii:
    """

    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    content_date = models.ForeignKey(ContentDate, on_delete=models.CASCADE)
    abs_date = models.DateTimeField(null=True, blank=True)
    rel_date = models.DurationField(null=True, blank=True, db_index=True)
    reason = models.TextField(default='', blank=True)
    actor = models.ForeignKey(
        get_user_model(), null=True, default=None, blank=True, related_name="actor", on_delete=models.CASCADE
    )

    @property
    def actual_date(self):
        """
        Return the normalized date.
        """
        if self.abs_date:
            return self.abs_date

        policy_date = self.content_date.policy.actual_date(self.content_date.schedule_for_user(self.user))
        if self.rel_date:
            return policy_date + self.rel_date
        else:
            return policy_date

    @property
    def location(self):
        """
        Return the content location.
        """
        return self.content_date.location

    def clean(self):
        """
        Validate data before saving.
        """
        if self.abs_date and self.rel_date:
            raise ValidationError(_("Absolute and relative dates cannot both be used"))

        policy_date = self.content_date.policy.actual_date(self.content_date.schedule_for_user(self.user))
        if self.rel_date is not None and self.rel_date.total_seconds() < 0:
            raise ValidationError(_("Override date must be later than policy date"))
        if self.abs_date is not None and isinstance(policy_date, datetime) and self.abs_date < policy_date:
            raise ValidationError(_("Override date must be later than policy date"))

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        # TODO: return a string appropriate for the data fields
        return '<UserDate, ID: {}>'.format(self.id)
