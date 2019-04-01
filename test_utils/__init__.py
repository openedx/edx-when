"""
Test utilities.

Since py.test discourages putting __init__.py into test directory (i.e. making tests a package)
one cannot import from anywhere under tests folder. However, some utility classes/methods might be useful
in multiple test modules (i.e. factoryboy factories, base test classes). So this package is the place to put them.
"""
from __future__ import absolute_import, unicode_literals

import uuid
from datetime import datetime

from opaque_keys.edx.keys import UsageKey


def make_block_id(course_id='testX+tt101+2019', block_type='sequential+block'):
    guid = uuid.uuid4().hex
    block_id = 'block-v1:%s+type@%s@%s' % (course_id, block_type, guid)
    return UsageKey.from_string(block_id)


def make_items():
    """
    Return item list for set_dates_for_course.
    """
    items = [
        (make_block_id(), {'due': datetime(2019, 3, 22)}),
        (make_block_id(), {'due': datetime(2019, 3, 23), 'test': '1'}),
        (make_block_id(), {'start': datetime(2019, 3, 21), 'test': '1'}),
        (make_block_id(), {'start': None, 'test': '1'}),
    ]
    return items
