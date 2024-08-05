"""
Utility functions to use across edx-when.
"""
from django.core.exceptions import ObjectDoesNotExist
from edx_django_utils.cache.utils import RequestCache

try:
    from openedx.core.djangoapps.schedules.models import Schedule
# TODO: Move schedules into edx-when
except ImportError:
    Schedule = None


def get_schedule_for_user(user_id, course_key, use_cached=True):
    """
    Return the schedule for the user in the course or None if it does not exist or the Schedule model is undefined.
    """
    # If Schedule is not defined, there's nothing to query, so return None. This
    # hackiness is happening because the Schedule model is in edx-platform at
    # the moment.
    if not Schedule:
        return None

    # This is intentionally a RequestCache and not a TieredCache–that way it's
    # just a local memory reference, and we don't have to worry about the
    # complications that can come with pickling model objects.
    cache = RequestCache('edx-when')
    cache_key = f"get_schedule_for_user::{user_id}::{course_key}"
    if use_cached:
        cache_response = cache.get_cached_response(cache_key)
        if cache_response.is_found:
            return cache_response.value

    try:
        schedule = Schedule.objects.get(
            enrollment__user__id=user_id,
            enrollment__course__id=course_key,
        )
    except ObjectDoesNotExist:
        schedule = None

    cache.set(cache_key, schedule)

    return schedule
