"""
API for retrieving and setting dates.
"""
from __future__ import absolute_import, unicode_literals

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db.models import ObjectDoesNotExist
from edx_django_utils.cache.utils import DEFAULT_REQUEST_CACHE
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey

from . import models

log = logging.getLogger(__name__)

FIELDS_TO_EXTRACT = ('due', 'start', 'end')


def _ensure_key(key_class, key_obj):
    if not isinstance(key_obj, key_class):
        key_obj = key_class.from_string(key_obj)
    return key_obj


def is_enabled_for_course(course_key):
    """
    Return whether edx-when is enabled for this course.
    """
    return models.ContentDate.objects.filter(course_id=course_key, active=True).exists()


def override_enabled():
    """
    Return decorator that enables edx-when.
    """
    from waffle.testutils import override_flag
    return override_flag('edx-when-enabled', active=True)


def set_dates_for_course(course_key, items):
    """
    Extract dates from blocks.

    items is an iterator of (location, field metadata dictionary)
    """
    clear_dates_for_course(course_key)
    for location, fields in items:
        for field in FIELDS_TO_EXTRACT:
            if field in fields:
                val = fields[field]
                if val:
                    log.info('Setting date for %r, %s, %r', location, field, val)
                    set_date_for_block(course_key, location, field, val)


def clear_dates_for_course(course_key):
    """
    Set all dates to inactive.
    """
    course_key = _ensure_key(CourseKey, course_key)
    models.ContentDate.objects.filter(course_id=course_key, active=True).update(active=False)


# TODO: Record dates for every block in the course, not just the ones where the block
# has an explicitly set date.
def get_dates_for_course(course_id, user=None, use_cached=True, schedule=None):
    """
    Return dictionary of dates for the given course_id and optional user.

        key: block location, field name
        value: datetime object
    """
    log.debug("Getting dates for %s as %s", course_id, user)

    cache_key = 'course_dates.%s' % course_id
    if user:
        if isinstance(user, int):
            user_id = user
        else:
            user_id = user.id if not user.is_anonymous else ''
        cache_key += '.%s' % user_id
    else:
        user_id = None

    dates = DEFAULT_REQUEST_CACHE.data.get(cache_key, None)
    if use_cached and dates is not None:
        return dates

    course_id = _ensure_key(CourseKey, course_id)
    qset = models.ContentDate.objects.filter(course_id=course_id, active=True).select_related('policy')
    dates = {}
    policies = {}
    for cdate in qset:
        if schedule is None and user is not None:
            try:
                schedule = cdate.schedule_for_user(user)
            except ObjectDoesNotExist:
                schedule = None

        key = (cdate.location, cdate.field)
        try:
            dates[key] = cdate.policy.actual_date(schedule)
        except ValueError:
            log.warning("Unable to read date for %s", cdate.location, exc_info=True)
        policies[cdate.id] = key
    if user_id:
        for userdate in models.UserDate.objects.filter(
            user_id=user_id,
            content_date__course_id=course_id,
            content_date__active=True
        ).select_related(
            'content_date', 'content_date__policy'
        ).order_by('modified'):

            try:
                dates[policies[userdate.content_date_id]] = userdate.actual_date
            except (ValueError, ObjectDoesNotExist):
                log.warning("Unable to read date for %s", userdate.content_date, exc_info=True)

    DEFAULT_REQUEST_CACHE.data[cache_key] = dates
    return dates


def get_date_for_block(course_id, block_id, name='due', user=None):
    """
    Return the date for block in the course for the (optional) user.
    """
    try:
        return get_dates_for_course(course_id, user).get((_ensure_key(UsageKey, block_id), name), None)
    except InvalidKeyError:
        return None


def get_overrides_for_block(course_id, block_id):
    """
    Return list of date overrides for a block.

    list of (username, full_name, date)
    """
    course_id = _ensure_key(CourseKey, course_id)
    block_id = _ensure_key(UsageKey, block_id)

    query = models.UserDate.objects.filter(
                content_date__course_id=course_id,
                content_date__location=block_id,
                content_date__active=True).order_by('-modified')
    dates = []
    users = set()
    for udate in query:
        if udate.user_id in users:
            continue
        else:
            users.add(udate.user_id)
        username = udate.user.username
        try:
            full_name = udate.user.profile.name
        except AttributeError:
            full_name = 'unknown'
        override = udate.actual_date
        dates.append((username, full_name, override))
    return dates


def get_overrides_for_user(course_id, user):
    """
    Return all user date overrides for a particular course.

    iterator of {'location': location, 'actual_date': date}
    """
    course_id = _ensure_key(CourseKey, course_id)

    query = models.UserDate.objects.filter(
                content_date__course_id=course_id,
                user=user,
                content_date__active=True).order_by('-modified')
    blocks = set()
    for udate in query:
        if udate.content_date.location in blocks:
            continue
        else:
            blocks.add(udate.content_date.location)
        yield {'location': udate.content_date.location, 'actual_date': udate.actual_date}


def set_date_for_block(course_id, block_id, field, date_or_timedelta, user=None, reason='', actor=None):
    """
    Save the date for a particular field in a block.

    date_or_timedelta: The absolute or relative date to set for the block
    user: user object to override date
    reason: explanation for override
    actor: user object of person making the override
    """
    course_id = _ensure_key(CourseKey, course_id)
    block_id = _ensure_key(UsageKey, block_id)

    if date_or_timedelta is None:
        date_kwargs = {'rel_date': None, 'abs_date': None}
    elif isinstance(date_or_timedelta, timedelta):
        date_kwargs = {'rel_date': date_or_timedelta}
    else:
        date_kwargs = {'abs_date': date_or_timedelta}

    try:
        existing_date = models.ContentDate.objects.get(course_id=course_id, location=block_id, field=field)
        existing_date.active = True
    except models.ContentDate.DoesNotExist:
        if user:
            raise MissingDateError(block_id)
        existing_date = models.ContentDate(course_id=course_id, location=block_id, field=field)
        existing_date.policy, __ = models.DatePolicy.objects.get_or_create(**date_kwargs)

    if user and not user.is_anonymous:
        userd = models.UserDate(
            user=user,
            actor=actor,
            reason=reason or '',
            content_date=existing_date,
            **date_kwargs
        )
        try:
            userd.full_clean()
        except ValidationError:
            raise InvalidDateError(userd.actual_date)
        userd.save()
        log.info('Saved override for user=%d loc=%s date=%s', userd.user_id, userd.location, userd.actual_date)
    else:
        if existing_date.policy.abs_date != date_or_timedelta and existing_date.policy.rel_date != date_or_timedelta:
            log.info(
                'updating policy %r %r -> %r',
                existing_date,
                existing_date.policy.abs_date or existing_date.policy.rel_date,
                date_or_timedelta
            )
            existing_date.policy = models.DatePolicy.objects.get_or_create(**date_kwargs)[0]
    existing_date.save()


class BaseWhenException(Exception):
    pass


class MissingDateError(BaseWhenException):
    pass


class InvalidDateError(BaseWhenException):
    pass
