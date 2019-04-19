"""edx_when signal handlers."""
from __future__ import absolute_import, unicode_literals

import logging

from .api import set_dates_for_course

log = logging.getLogger('edx-when')


def extract_dates(sender, course_key, **kwargs):  # pylint: disable=unused-argument
    """
    Extract dates from blocks when publishing a course.
    """
    from xmodule.modulestore.django import modulestore  # pylint: disable=import-error
    from xmodule.modulestore.inheritance import own_metadata  # pylint: disable=import-error

    log.info('publishing course dates for %s', course_key)
    date_items = []
    items = modulestore().get_items(course_key)
    log.info('extracting dates from %d items in %s', len(items), course_key)
    for item in items:
        date_items.append((item.location, own_metadata(item)))

    try:
        set_dates_for_course(course_key, date_items)
    except Exception:  # pylint: disable=broad-except
        log.exception('setting dates for %s', course_key)
