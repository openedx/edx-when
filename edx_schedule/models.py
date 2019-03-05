# -*- coding: utf-8 -*-
"""
Database models for edx_schedule.
"""

from __future__ import absolute_import, unicode_literals

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.utils.translation import gettext_lazy as _
from model_utils.models import TimeStampedModel
from opaque_keys.edx.django.models import BlockTypeKeyField, CourseKeyField


@python_2_unicode_compatible
class DatePolicy(TimeStampedModel):
    """
    TODO: replace with a brief description of the model.

    .. no_pii:
    """

    course_id = CourseKeyField(db_index=True, max_length=255)
    abs_date = models.DateTimeField(null=True)
    rel_date = models.IntegerField(null=True)

    def clean(self):
        """
        Validate data before saving.
        """
        if self.abs_date and self.rel_date:
            raise ValidationError(_("Absolute and relative dates cannot both be used"))
        elif not (self.abs_date or self.rel_date):
            raise ValidationError(_("Either absolute or relative date must be set"))

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

    policy = models.ForeignKey(DatePolicy)
    location = BlockTypeKeyField(null=True, default=None, db_index=True, max_length=255)

    class Meta:
        """Django Metadata."""

        unique_together = ('policy', 'location')

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
    policy = models.ForeignKey(DatePolicy)
    abs_date = models.DateTimeField(null=True)
    rel_date = models.IntegerField(null=True)
    reason = models.TextField(default='')
    actor = models.ForeignKey(get_user_model(), null=True, default=None, related_name="actor")

    def clean(self):
        """
        Validate data before saving.
        """
        if self.abs_date and self.rel_date:
            raise ValidationError(_("Absolute and relative dates cannot both be used"))
        elif not (self.abs_date or self.rel_date):
            raise ValidationError(_("Either absolute or relative date must be set"))

    def __str__(self):
        """
        Get a string representation of this model instance.
        """
        # TODO: return a string appropriate for the data fields
        return '<UserDate, ID: {}>'.format(self.id)
