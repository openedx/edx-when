"""
Utility functions to use across edx-when.
"""
from django.core.exceptions import ObjectDoesNotExist

try:
    from openedx.core.djangoapps.schedules.models import Schedule
# TODO: Move schedules into edx-when
except ImportError:
    Schedule = None


def get_schedule_for_user(user_id, course_key):
    """
    Return the schedule for the user in the course or None if it does not exist or the Schedule model is undefined.
    """
    if Schedule:
        try:
            return Schedule.objects.get(enrollment__user__id=user_id, enrollment__course__id=course_key)
        except ObjectDoesNotExist:
            pass
    return None
