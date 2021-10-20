"""
Database models for edx_when.
"""

from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField

from .utils import get_schedule_for_user


class MissingScheduleError(ValueError):
    pass


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

    def actual_date(self, schedule=None, end_datetime=None, cutoff_datetime=None):
        """
        Return the normalized date.

        Arguments:
            schedule (Schedule): user schedule, only used for relative dates
            end_datetime (datetime): no relative dates will be given after this date
            cutoff_datetime (datetime): no relative dates will be given if user originally started past this date
        """
        if self.rel_date is not None:
            if schedule is None:
                raise MissingScheduleError(
                    "Can't interpret relative date {} for {!r} without a user schedule".format(
                        self.rel_date,
                        self
                    )
                )

            # If the user first enrolled after the cutoff date (or reset their schedule after the course end), we
            # don't want to return any dates.
            if ((cutoff_datetime and schedule.created > cutoff_datetime) or
                    (end_datetime and schedule.start_date > end_datetime)):
                return None

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
    block_type = models.CharField(max_length=255, null=True)

    class Meta:
        """Django Metadata."""

        unique_together = ('policy', 'location', 'field')
        indexes = [
            models.Index(fields=('course_id', 'block_type'), name='edx_when_course_block_type_idx'),
        ]

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        # Location already holds course id
        return f'ContentDate({self.policy}, {self.location}, {self.field}, {self.block_type})'


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

        schedule = get_schedule_for_user(self.user.id, self.content_date.course_id)  # pylint: disable=no-member
        policy_date = self.content_date.policy.actual_date(schedule)
        if schedule and self.rel_date:
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

        schedule = get_schedule_for_user(self.user.id, self.content_date.course_id)  # pylint: disable=no-member
        policy_date = self.content_date.policy.actual_date(schedule=schedule)
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
        return f'{self.user.username}, {self.content_date.location}, {self.content_date.field}'
