# -*- coding: utf-8 -*-
"""
Database models for edx_when.
"""

from __future__ import absolute_import, unicode_literals

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import CourseKeyField, UsageKeyField


@python_2_unicode_compatible
class DatePolicy(TimeStampedModel):
    """
    TODO: replace with a brief description of the model.

    .. no_pii:
    """

    abs_date = models.DateTimeField(null=True, db_index=True)

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        # TODO: return a string appropriate for the data fields
        return '<DatePolicy, ID: {}>'.format(self.id)


@python_2_unicode_compatible
class ContentDate(models.Model):
    """
    TODO: replace with a brief description of the model.

    .. no_pii:
    """

    course_id = CourseKeyField(db_index=True, max_length=255)
    policy = models.ForeignKey(DatePolicy)
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


@python_2_unicode_compatible
class UserDate(TimeStampedModel):
    """
    TODO: replace with a brief description of the model.

    .. no_pii:
    """

    user = models.ForeignKey(get_user_model())
    content_date = models.ForeignKey(ContentDate)
    abs_date = models.DateTimeField(null=True, blank=True)
    rel_date = models.IntegerField(null=True, blank=True)
    reason = models.TextField(default='', blank=True)
    actor = models.ForeignKey(get_user_model(), null=True, default=None, blank=True, related_name="actor")

    @property
    def actual_date(self):
        """
        Return the normalized date.
        """
        if self.abs_date:
            return self.abs_date
        else:
            return self.content_date.policy.abs_date + timedelta(days=self.rel_date or 0)

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
        elif self.actual_date < self.content_date.policy.abs_date:
            raise ValidationError(_("Override date must be later than policy date"))

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        # TODO: return a string appropriate for the data fields
        return '<UserDate, ID: {}>'.format(self.id)
