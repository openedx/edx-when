# -*- coding: utf-8 -*-
"""
Database models for edx_when.
"""

from __future__ import absolute_import, unicode_literals

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField

try:
    from openedx.core.djangoapps.schedules.models import Schedule
# TODO: Move schedules into edx-when
except ImportError:
    Schedule = None


class DatePolicy(TimeStampedModel):
    """
    Stores a date (either absolute or relative).

    .. no_pii:
    """

    abs_date = models.DateTimeField(null=True, blank=True, db_index=True)
    rel_date = models.DurationField(null=True, blank=True, db_index=True)

    class Meta:
        """Django Metadata."""

        verbose_name_plural = 'Date policies'

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        return str(self.abs_date) if self.abs_date else str(self.rel_date)

    def actual_date(self, schedule=None, end_datetime=None):
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
            # If the course has an end date defined, we will prefer the course end date
            # if the relative date is later than the course end date.
            # Note: This can result in several dates being listed the same as the course end date
            if end_datetime:
                return min(schedule.start_date + self.rel_date, end_datetime)
            return schedule.start_date + self.rel_date
        else:
            return self.abs_date

    def clean(self):
        """
        Validate data before saving.
        """
        if self.abs_date and self.rel_date:
            raise ValidationError(_("Absolute and relative dates cannot both be used"))


class ContentDate(models.Model):
    """
    Ties a DatePolicy to a specific piece of course content. (e.g. a due date for a homework).

    .. no_pii:
    """

    course_id = CourseKeyField(db_index=True, max_length=255)
    policy = models.ForeignKey(DatePolicy, on_delete=models.CASCADE)
    location = UsageKeyField(null=True, default=None, db_index=True, max_length=255)
    field = models.CharField(max_length=255, default='')
    active = models.BooleanField(default=True)

    class Meta:
        """Django Metadata."""

        unique_together = ('policy', 'location', 'field')

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        # Location already holds course id
        return '{}, {}'.format(self.location, self.field)

    def schedule_for_user(self, user):
        """
        Return the schedule for the supplied user that applies to this piece of content or None.
        """
        no_schedules_found = None
        if Schedule is None:
            return no_schedules_found
        if isinstance(user, int):
            try:
                return Schedule.objects.get(enrollment__user__id=user, enrollment__course__id=self.course_id)
            except ObjectDoesNotExist:
                return no_schedules_found
        else:
            # TODO: We could contemplate using pre-fetched enrollments/schedules,
            # but for the moment, just use the fastests non-prefetchable query
            try:
                return Schedule.objects.get(enrollment__user__id=user.id, enrollment__course__id=self.course_id)
            except ObjectDoesNotExist:
                return no_schedules_found


class UserDate(TimeStampedModel):
    """
    Stores a user-specific date override for a given ContentDate.

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

        schedule_for_user = self.content_date.schedule_for_user(self.user)
        policy_date = self.content_date.policy.actual_date(schedule_for_user)
        if schedule_for_user and self.rel_date:
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

        user_schedule = self.content_date.schedule_for_user(self.user)
        policy_date = self.content_date.policy.actual_date(schedule=user_schedule)
        if self.rel_date is not None and self.rel_date.total_seconds() < 0:
            raise ValidationError(_("Override date must be later than policy date"))
        if self.abs_date is not None and isinstance(policy_date, datetime) and self.abs_date < policy_date:
            raise ValidationError(_("Override date must be later than policy date"))

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        # Location already holds course id
        # pylint: disable=no-member
        return '{}, {}, {}'.format(self.user.username, self.content_date.location, self.content_date.field)
