"""edx_when signal handlers."""
from __future__ import absolute_import, unicode_literals

import logging

from django.dispatch import receiver

from xmodule.modulestore.django import SignalHandler, modulestore  # pylint: disable=import-error
from xmodule.modulestore.inheritance import own_metadata  # pylint: disable=import-error

from .api import set_dates_for_course

log = logging.getLogger('edx-when')


def _get_item_metadata(course_key):
    items = modulestore().get_items(course_key)
    log.info('extracting dates from %d items in %s', len(items), course_key)
    for item in items:
        fields = own_metadata(item)
        yield item.location, fields


@receiver(SignalHandler.course_published)
def extract_dates(sender, course_key, **kwargs):  # pylint: disable=unused-argument
    """
    Extract dates from blocks when publishing a course.
    """
    log.info('publishing course dates for %s', course_key)
    try:
        set_dates_for_course(course_key, _get_item_metadata(course_key))
    except Exception:  # pylint: disable=broad-except
        log.exception('setting dates for %s', course_key)
