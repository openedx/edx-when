from django.db import transaction
from django.dispatch import receiver

from xmodule.modulestore.django import SignalHandler


@receiver(SignalHandler.course_published)
def listen_for_course_publish(sender, course_key, **kwargs):  # pylint: disable=unused-argument
    """
    Receive the course_published signal and update assignment dates for the course.
    """
    # import here, because signal is registered at startup, but items in tasks are not available yet
    from edx_when.tasks import update_assignment_dates_for_course

    course_key_str = str(course_key)
    transaction.on_commit(lambda: update_assignment_dates_for_course.delay(course_key_str))
