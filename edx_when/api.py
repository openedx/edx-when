"""
API for retrieving and setting dates.
"""
from __future__ import absolute_import, unicode_literals

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
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


def _are_relative_dates_enabled(course_key=None):
    """
    Return whether it's OK to consider relative dates. If not, pretend those database entries don't exist.
    """
    try:
        # It's bad form to depend on LMS code from inside a plugin like this. But we gracefully fail, and this is
        # temporary code anyway, while we develop this feature.
        from openedx.features.course_experience import RELATIVE_DATES_FLAG
    except ImportError:
        return False

    return RELATIVE_DATES_FLAG.is_enabled(course_key)


def is_enabled_for_course(course_key):
    """
    Return whether edx-when is enabled for this course.
    """
    return models.ContentDate.objects.filter(course_id=course_key, active=True).exists()


def set_dates_for_course(course_key, items):
    """
    Set dates for blocks.

    items is an iterator of (location, field metadata dictionary)
    """
    with transaction.atomic():
        active_date_ids = []

        for location, fields in items:
            for field in FIELDS_TO_EXTRACT:
                if field in fields:
                    val = fields[field]
                    if val:
                        log.info('Setting date for %r, %s, %r', location, field, val)
                        active_date_ids.append(set_date_for_block(course_key, location, field, val))

        # Now clear out old dates that we didn't touch
        clear_dates_for_course(course_key, keep=active_date_ids)


def clear_dates_for_course(course_key, keep=None):
    """
    Set all dates to inactive.

    Arguments:
        course_key: either a CourseKey or string representation of same
        keep: an iterable of ContentDate ids to keep active
    """
    course_key = _ensure_key(CourseKey, course_key)
    dates = models.ContentDate.objects.filter(course_id=course_key, active=True)
    if keep:
        dates = dates.exclude(id__in=keep)
    dates.update(active=False)


# TODO: Record dates for every block in the course, not just the ones where the block
# has an explicitly set date.
def get_dates_for_course(course_id, user=None, use_cached=True, schedule=None):
    """
    Return dictionary of dates for the given course_id and optional user.

        key: block location, field name
        value: datetime object

    Arguments:
        course_id: either a CourseKey or string representation of same
        user: None, an int, or a User object
        use_cached: will skip cache lookups (but not saves) if False
        schedule: optional override for a user's enrollment Schedule, used for relative date calculations
    """
    course_id = _ensure_key(CourseKey, course_id)
    log.debug("Getting dates for %s as %s", course_id, user)
    allow_relative_dates = _are_relative_dates_enabled(course_id)

    cache_key = 'course_dates.%s' % course_id
    if user:
        if isinstance(user, int):
            user_id = user
        else:
            user_id = user.id if not user.is_anonymous else ''
        cache_key += '.%s' % user_id
    else:
        user_id = None
    if schedule:
        cache_key += '.schedule-%s' % schedule.start_date
    if allow_relative_dates:
        cache_key += '.with-rel-dates'

    dates = DEFAULT_REQUEST_CACHE.data.get(cache_key, None)
    if use_cached and dates is not None:
        return dates

    rel_lookup = {} if allow_relative_dates else {'policy__rel_date': None}
    qset = models.ContentDate.objects.filter(course_id=course_id, active=True, **rel_lookup).select_related('policy')

    dates = {}
    policies = {}
    need_schedule = schedule is None and user is not None
    end_content_date = list(filter(lambda cd: cd.location.block_type == 'course' and cd.field == 'end', qset))
    end_datetime = None
    if end_content_date:
        end_datetime = end_content_date[0].policy.abs_date
    for cdate in qset:
        if need_schedule:
            need_schedule = False
            schedule = cdate.schedule_for_user(user)

        key = (cdate.location, cdate.field)
        try:
            dates[key] = cdate.policy.actual_date(schedule, end_datetime)
        except ValueError:
            log.warning("Unable to read date for %s", cdate.location, exc_info=True)
        policies[cdate.id] = key

    if user_id:
        for userdate in models.UserDate.objects.filter(
            user_id=user_id,
            content_date__course_id=course_id,
            content_date__active=True,
        ).select_related(
            'content_date', 'content_date__policy'
        ).order_by('modified'):
            try:
                dates[policies[userdate.content_date_id]] = userdate.actual_date
            except (ValueError, ObjectDoesNotExist, KeyError):
                log.warning("Unable to read date for %s", userdate.content_date, exc_info=True)

    DEFAULT_REQUEST_CACHE.data[cache_key] = dates
    return dates


def get_date_for_block(course_id, block_id, name='due', user=None):
    """
    Return the date for block in the course for the (optional) user.

    Arguments:
        course_id: either a CourseKey or string representation of same
        block_id: either a UsageKey or string representation of same
        name (optional): the name of the date field to read
        user: None, an int, or a User object
    """
    try:
        return get_dates_for_course(course_id, user).get((_ensure_key(UsageKey, block_id), name), None)
    except InvalidKeyError:
        return None


def get_overrides_for_block(course_id, block_id):
    """
    Return list of date overrides for a block.

    Arguments:
        course_id: either a CourseKey or string representation of same
        block_id: either a UsageKey or string representation of same

    Returns:
        list of (username, full_name, date)
    """
    course_id = _ensure_key(CourseKey, course_id)
    block_id = _ensure_key(UsageKey, block_id)

    query = models.UserDate.objects.filter(
        content_date__course_id=course_id,
        content_date__location=block_id,
        content_date__active=True,
    ).order_by('-modified')
    dates = []
    users = set()
    for udate in query:
        if udate.user_id in users:
            continue

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

    Arguments:
        course_id: either a CourseKey or string representation of same
        user: a User object

    Returns:
        iterator of {'location': location, 'actual_date': date}
    """
    course_id = _ensure_key(CourseKey, course_id)

    query = models.UserDate.objects.filter(
        content_date__course_id=course_id,
        user=user,
        content_date__active=True,
    ).order_by('-modified')
    blocks = set()
    for udate in query:
        if udate.content_date.location in blocks:
            continue

        blocks.add(udate.content_date.location)
        yield {'location': udate.content_date.location, 'actual_date': udate.actual_date}


def set_date_for_block(course_id, block_id, field, date_or_timedelta, user=None, reason='', actor=None):
    """
    Save the date for a particular field in a block.

    date_or_timedelta: The absolute or relative date to set for the block
    user: user object to override date
    reason: explanation for override
    actor: user object of person making the override

    Returns:
        a unique id for this block date
    """
    course_id = _ensure_key(CourseKey, course_id)
    block_id = _ensure_key(UsageKey, block_id)

    if date_or_timedelta is None:
        date_kwargs = {'rel_date': None, 'abs_date': None}
    elif isinstance(date_or_timedelta, timedelta):
        date_kwargs = {'rel_date': date_or_timedelta}
    else:
        date_kwargs = {'abs_date': date_or_timedelta}

    with transaction.atomic(savepoint=False):  # this is frequently called in a loop, let's avoid the savepoints
        try:
            existing_date = models.ContentDate.objects.select_related('policy').get(
                course_id=course_id, location=block_id, field=field
            )
            needs_save = not existing_date.active
            existing_date.active = True
        except models.ContentDate.DoesNotExist:
            if user:
                raise MissingDateError(block_id)
            existing_date = models.ContentDate(course_id=course_id, location=block_id, field=field)
            existing_date.policy, __ = models.DatePolicy.objects.get_or_create(**date_kwargs)
            needs_save = True

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
            if date_or_timedelta not in (existing_date.policy.abs_date, existing_date.policy.rel_date):
                log.info(
                    'updating policy %r %r -> %r',
                    existing_date,
                    existing_date.policy.abs_date or existing_date.policy.rel_date,
                    date_or_timedelta
                )
                existing_date.policy = models.DatePolicy.objects.get_or_create(**date_kwargs)[0]
                needs_save = True

        if needs_save:
            existing_date.save()
        return existing_date.id


class BaseWhenException(Exception):
    pass


class MissingDateError(BaseWhenException):
    pass


class InvalidDateError(BaseWhenException):
    pass
