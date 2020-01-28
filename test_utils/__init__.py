"""
Test utilities.

Since py.test discourages putting __init__.py into test directory (i.e. making tests a package)
one cannot import from anywhere under tests folder. However, some utility classes/methods might be useful
in multiple test modules (i.e. factoryboy factories, base test classes). So this package is the place to put them.
"""
from __future__ import absolute_import, unicode_literals

import uuid
from datetime import datetime, timedelta

from opaque_keys.edx.locator import BlockUsageLocator, CourseLocator


def make_block_id(course_id=CourseLocator('testX', 'tt101', '2019'), block_type='sequential'):
    guid = uuid.uuid4().hex
    return BlockUsageLocator(course_key=course_id, block_type=block_type, block_id=guid)


def make_items(course_id=CourseLocator('testX', 'tt101', '2019'), with_relative=False):
    """
    Return item list for set_dates_for_course.
    """
    items = [
        (make_block_id(course_id), {'due': datetime(2019, 3, 22)}),
        (make_block_id(course_id), {'due': datetime(2019, 3, 23), 'test': '1'}),
        (make_block_id(course_id), {'start': datetime(2019, 3, 21), 'test': '1'}),
        (make_block_id(course_id), {'start': None, 'test': '1'}),
    ]
    if with_relative:
        items.extend([
            (make_block_id(course_id), {'due': timedelta(days=1)}),
            (make_block_id(course_id), {'due': timedelta(days=7), 'test': '1'}),
            (make_block_id(course_id), {'start': timedelta(hours=12), 'test': '1'}),
        ])
    return items
