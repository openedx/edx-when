"""FieldData support for date lookups."""
from __future__ import absolute_import, unicode_literals

import logging

from xblock.field_data import FieldData

from . import api

log = logging.getLogger('edx-when')

NOT_FOUND = object()


class DateLookupFieldData(FieldData):
    """
    FieldData instance that looks up date fields in django models.

    falling back on the provided FieldData object if the date isn't found
    """

    def __init__(self, defaults, course_id, user=None):
        """
        Create a new FieldData that contains relational-backed dates.

        defaults: FieldData instance to consult if the field is not in our database
        course_id: CourseKey for course
        user: User object to look for date overrides
        """
        super(DateLookupFieldData, self).__init__()
        self._defaults = defaults
        self._course_dates = api.get_dates_for_course(course_id, user)

    def get(self, block, name):
        """
        Return field value for given block and field name.
        """
        if name in api.FIELDS_TO_EXTRACT:
            log.debug('location %r %r', block.location, name)
            val = self._course_dates.get((block.location, name), NOT_FOUND)
        else:
            val = NOT_FOUND
        if val is NOT_FOUND:
            val = self._defaults.get(block, name)
        else:
            log.debug('Got value for %r, %s, %s', block.location, name, val)
        return val

    def set(self, block, name, value):
        """
        Set the value in the default FieldData.
        """
        return self._defaults.set(block, name, value)

    def delete(self, block, name):
        """
        Delete the value in the default FieldData.
        """
        return self._defaults.delete(block, name)
