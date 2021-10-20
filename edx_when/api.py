"""
API for retrieving and setting dates.
"""

import logging
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import DateTimeField, ExpressionWrapper, F, ObjectDoesNotExist, Q
from edx_django_utils.cache.utils import TieredCache
from opaque_keys import InvalidKeyError
from opaque_keys.edx.keys import CourseKey, UsageKey

from . import models
from .utils import get_schedule_for_user

try:
    from openedx.core.djangoapps.schedules.models import Schedule
# TODO: Move schedules into edx-when
except ImportError:
    Schedule = None

log = logging.getLogger(__name__)

FIELDS_TO_EXTRACT = ('due', 'start', 'end')


def _content_dates_cache_key(course_key, query_dict, subsection_and_higher_only, published_version):
    """
    Memcached key for ContentDates given course_key, filter args, subsection and higher blocks, and published version.

    Adding the course's published version makes cache invalidation unnecessary,
    as setting new course block dates will always be a new course version.
    """
    query_dict_str = ".".join(
        sorted(
            "{},{}".format(key, value or "")
            for key, value in query_dict.items()
        )
    )
    subsection_and_higher_only_str = ''
    if subsection_and_higher_only:
        subsection_and_higher_only_str = 'subsection_and_higher_only'
    published_version_str = ''
    if published_version:
        published_version_str = published_version

    return f'edx-when.content_dates:{course_key}:{query_dict_str}:'\
           f'{subsection_and_higher_only_str}:{published_version_str}'


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
        from openedx.features.course_experience import RELATIVE_DATES_FLAG  # pylint: disable=import-outside-toplevel
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

    items: iterator of (location, field metadata dictionary)
    """
    with transaction.atomic():
        active_date_ids = []

        for location, fields in items:
            for field in FIELDS_TO_EXTRACT:
                if field in fields:
                    val = fields[field]
                    if val:
                        log.info('Setting date for %r, %s, %r', location, field, val)
                        active_date_ids.append(
                            set_date_for_block(course_key, location, field, val)
                        )

        # Now clear out old dates that we didn't touch
        _clear_dates_for_course(course_key, active_date_ids)


def _clear_dates_for_course(course_key, keep=None):
    """
    Set all dates to inactive.

    This method changes currently-cached rows - but the cache key contains the course's published version.
    And the calling method is *only* invoked upon course publish, which guarantees that a new course published
    version will be used to get course dates after this call is made, invalidating existing cache entries.

    Arguments:
        course_key: either a CourseKey or string representation of same
        keep: an iterable of ContentDate ids to keep active
    """
    course_key = _ensure_key(CourseKey, course_key)
    dates = models.ContentDate.objects.filter(course_id=course_key, active=True)
    if keep:
        dates = dates.exclude(id__in=keep)
    dates.update(active=False)


def _get_end_dates_from_content_dates(qset):
    """
    Get end and cutoff dates from a queryset of ContentDates.
    """
    end_content_date = list(filter(lambda cd: cd.location.block_type == 'course' and cd.field == 'end', qset))
    if not end_content_date:
        return None, None

    end_datetime = end_content_date[0].policy.abs_date

    # Note the date where a learner has just enough time to hit every due date before the course ends on them.
    # (this is to prevent a learner starting a course a week from end date and having 8 weeks of homework due in 1)
    last_date = max((cd.policy.rel_date for cd in qset if cd.field == 'due' and cd.policy.rel_date), default=None)
    cutoff_datetime = end_datetime - last_date if last_date else end_datetime

    return end_datetime, cutoff_datetime


def _processed_results_cache_key(
        course_id, user_id, schedule, allow_relative_dates,
        subsection_and_higher_only, published_version
        ):
    """
    Construct the cache key, incorporating all parameters which would cause a different query set to be returned.
    """
    cache_key = 'course_dates.%s' % course_id
    if user_id:
        cache_key += '.%s' % user_id
    if schedule:
        cache_key += '.schedule-%s' % schedule.start_date
    if allow_relative_dates:
        cache_key += '.with-rel-dates'
    if subsection_and_higher_only:
        # cache key incremented with ".v2" so we don't mix buggy cached data with fixed data
        cache_key += '.subsection_and_higher_only.v2'
    cache_key += '.%s' % published_version if published_version else ''
    return cache_key


# TODO: Record dates for every block in the course, not just the ones where the block
# has an explicitly set date.
def get_dates_for_course(
        course_id,
        user=None, use_cached=True, schedule=None,
        subsection_and_higher_only=False, published_version=None
        ):
    """
    Return dictionary of dates for the given course_id and optional user.

        key: block location, field name
        value: datetime object

    Arguments:
        course_id: either a CourseKey or string representation of same
        user: None, an int (user_id), or a User object
        use_cached: bool (optional) - skips cache lookups (but not saves) if False
        schedule: Schedule obj (optional) - override for a user's enrollment Schedule, used
            for relative date calculations
        subsection_and_higher_only: bool (optional) - only returns dates for blocks at the subsection
            level and higher (i.e. course, section (chapter), subsection (sequential)).
        published_version: (optional) string representing the ID of the course's published version
    """
    course_id = _ensure_key(CourseKey, course_id)
    log.debug("Getting dates for %s as %s", course_id, user)
    allow_relative_dates = _are_relative_dates_enabled(course_id)

    user_id = None
    if user:
        if isinstance(user, int):
            user_id = user
        else:
            user_id = user.id if not user.is_anonymous else ''

    if schedule is None and user is not None and user_id != '':
        schedule = get_schedule_for_user(user_id, course_id)

    # Construct the cache key, incorporating all parameters which would cause a different
    # query set to be returned.
    processed_results_cache_key = _processed_results_cache_key(
        course_id, user_id, schedule, allow_relative_dates, subsection_and_higher_only, published_version
    )

    dates = None
    cached_response = TieredCache.get_cached_response(processed_results_cache_key)
    if cached_response.is_found:
        dates = cached_response.value

    if use_cached and dates is not None:
        return dates

    rel_lookup = {} if allow_relative_dates else {'policy__rel_date': None}

    # If more possible permutations are added to rel_lookup, be sure to also add
    # to cache invalidation in clear_dates_for_course. This is only safe to do
    # because a) we serialize to cache with pickle; b) we don't write to
    # ContentDate in this function; This is not a great long-term solution.
    raw_results_cache_key = _content_dates_cache_key(
        course_id, rel_lookup, subsection_and_higher_only, published_version
    )
    qset = None
    if use_cached:
        cached_response = TieredCache.get_cached_response(raw_results_cache_key)
        if cached_response.is_found:
            qset = cached_response.value
    if qset is None:
        qset = models.ContentDate.objects.filter(course_id=course_id, active=True, **rel_lookup)
        if subsection_and_higher_only:
            # Include NULL block_type values as well because of lazy rollout.
            qset = qset.filter(
                Q(block_type__in=('course', 'chapter', 'sequential')) |
                Q(block_type__isnull=True)
            )

        qset = list(
            qset.select_related('policy')
                .only(
                    "course_id", "policy__rel_date",
                    "policy__abs_date", "location", "field"
                )
        )
        TieredCache.set_all_tiers(raw_results_cache_key, qset)

    dates = {}
    policies = {}
    end_datetime, cutoff_datetime = _get_end_dates_from_content_dates(qset)

    for cdate in qset:
        key = (cdate.location.map_into_course(course_id), cdate.field)
        try:
            dates[key] = cdate.policy.actual_date(schedule, end_datetime, cutoff_datetime)
        except models.MissingScheduleError:
            # We had a relative date but no schedule. This is permissible in some cases (staff users viewing a course
            # they are not enrolled in, for example). Just let it go by.
            pass
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

    TieredCache.set_all_tiers(processed_results_cache_key, dates)

    return dates


def get_date_for_block(course_id, block_id, name='due', user=None, published_version=None):
    """
    Return the date for block in the course for the (optional) user.

    Arguments:
        course_id: either a CourseKey or string representation of same
        block_id: either a UsageKey or string representation of same
        name (optional): the name of the date field to read
        user: None, an int, or a User object
        published_version: (optional) string representing the ID of the course's published version
    """
    try:
        return get_dates_for_course(
            course_id, user=user, published_version=published_version
        ).get(
            (_ensure_key(UsageKey, block_id), name),
            None
        )
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


def set_date_for_block(
        course_id, block_id, field, date_or_timedelta,
        user=None, reason='', actor=None
        ):
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

    def _set_content_date_policy(date_kwargs, existing_content_date):
        # Race conditions were creating multiple DatePolicies w/ the same values. Handle that case.
        existing_policies = list(models.DatePolicy.objects.filter(**date_kwargs).order_by('id'))
        if existing_policies:
            existing_content_date.policy = existing_policies[0]
        else:
            existing_content_date.policy = models.DatePolicy.objects.create(**date_kwargs)

    with transaction.atomic(savepoint=False):  # this is frequently called in a loop, let's avoid the savepoints
        try:
            existing_date = models.ContentDate.objects.select_related('policy').get(
                course_id=course_id, location=block_id, field=field
            )
            needs_save = not existing_date.active
            existing_date.active = True
        except models.ContentDate.DoesNotExist as error:
            if user:
                # A UserDate creation below requires an existing ContentDate.
                raise MissingDateError(block_id) from error
            existing_date = models.ContentDate(course_id=course_id, location=block_id, field=field)
            _set_content_date_policy(date_kwargs, existing_date)
            needs_save = True

        # Determine if ourse block date is for a particular user -or- for the course in general.
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
            except ValidationError as error:
                raise InvalidDateError(userd.actual_date) from error
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
                _set_content_date_policy(date_kwargs, existing_date)
                needs_save = True

        # Sync the block_type for the ContentDate, if needed.
        if existing_date.block_type != block_id.block_type:
            existing_date.block_type = block_id.block_type
            needs_save = True

        if needs_save:
            existing_date.save()
        return existing_date.id


def get_schedules_with_due_date(course_id, assignment_date):
    """
    Get all Schedules with assignments due on a specific date for a Course.

    Arguments:
        course_id: either a CourseKey or string representation of same
        assignment_date: a date object

    Returns:
        a QuerySet of Schedule objects for Users who have content due on the specified assignment_date
    """
    user_ids = models.UserDate.objects.select_related('content_date', 'content_date__policy').annotate(
        computed_date=ExpressionWrapper(
            F('content_date__policy__abs_date') + F('rel_date'),
            output_field=DateTimeField()
        ),
    ).filter(
        Q(computed_date__date=assignment_date, abs_date__isnull=True) |
        Q(content_date__policy__abs_date__date=assignment_date, rel_date__isnull=True)
    ).values_list('user_id', flat=True).distinct()

    schedules = Schedule.objects.filter(
        enrollment__course_id=course_id,
        enrollment__user_id__in=user_ids,
    )

    # Get all relative dates for a course, we want them distinct, it doesn't matter how many of each due date there is
    rel_dates = models.ContentDate.objects.filter(
        course_id=course_id,
        active=True,
        policy__rel_date__isnull=False,
    ).select_related('policy').values_list('policy__rel_date', flat=True).distinct()

    # Using those relative dates, get all Schedules that have a "hit" by working backwards to the start_date
    rel_start_dates = [assignment_date - rel_date for rel_date in rel_dates]

    if rel_start_dates:
        # Exclude any user that has an overridden date for a course on the specified day so there aren't duplicates
        schedules = Schedule.objects.filter(
            enrollment__course_id=course_id,
            enrollment__is_active=True,
            start_date__date__in=rel_start_dates,
        ).exclude(enrollment__user_id__in=user_ids).select_related('enrollment') | schedules

    # Add in all users with relative dates to exclude from the absolute dates query to prevent duplicates
    user_ids = schedules.all().values_list('enrollment__user_id', flat=True).distinct()

    has_abs_date_on_day = models.ContentDate.objects.filter(
        course_id=course_id,
        active=True,
        policy__abs_date__date=assignment_date,
    ).first()

    # If there is an absolute day for this specified date for this
    # course, we want all active schedules to receive an email
    if has_abs_date_on_day:
        schedules = Schedule.objects.filter(
            enrollment__course_id=course_id,
            enrollment__is_active=True,
        ).exclude(enrollment__user_id__in=user_ids).select_related('enrollment') | schedules

    return schedules


class BaseWhenException(Exception):
    pass


class MissingDateError(BaseWhenException):
    pass


class InvalidDateError(BaseWhenException):
    pass
