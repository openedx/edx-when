"""FieldData support for date lookups."""
from __future__ import absolute_import, unicode_literals

import logging

from edx_django_utils.db.read_replica import read_queries_only
from six import text_type
from xblock.field_data import FieldData

from . import api

try:
    from xmodule.modulestore.inheritance import InheritanceMixin
    INHERITABLE_FIELDS = set(InheritanceMixin.fields.keys())
except ImportError:
    INHERITABLE_FIELDS = set(('due', 'start', 'end'))


log = logging.getLogger(__name__)

NOT_FOUND = object()


def _lineage(block):
    """
    Return an iterator over all ancestors of the given block.
    """
    parent = block.get_parent()
    while parent:
        yield parent
        parent = parent.get_parent()


class DateLookupFieldData(FieldData):
    """
    FieldData instance that looks up date fields in django models.

    falling back on the provided FieldData object if the date isn't found
    """

    def __init__(self, defaults, course_id=None, user=None, use_cached=True):
        """
        Create a new FieldData that contains relational-backed dates.

        defaults: FieldData instance to consult if the field is not in our database
        course_id: CourseKey for course
        user: User object to look for date overrides
        """
        super(DateLookupFieldData, self).__init__()
        if isinstance(defaults, DateLookupFieldData):
            defaults = defaults._defaults
        self._defaults = defaults
        self._load_dates(course_id, user, use_cached=use_cached)

    def _load_dates(self, course_id, user, use_cached=True):
        """
        Load the dates from the database.
        """
        with read_queries_only():
            dates = {}
            for (location, field), date in api.get_dates_for_course(course_id, user, use_cached=use_cached).items():
                dates[text_type(location), field] = date

        self._course_dates = dates

    def has(self, block, name):
        """
        Return whether the field exists in the block.
        """
        val = self._get(block, name)
        if val is NOT_FOUND:
            if name in INHERITABLE_FIELDS:
                for ancestor in _lineage(block):
                    if self._get(ancestor, name) is not NOT_FOUND:
                        return False

        return val is not NOT_FOUND or self._defaults.has(block, name)

    def _get(self, block, name):
        """
        Return the value, if it's in edx-when.

        Otherwise, return NOT_FOUND
        """
        if not isinstance(name, text_type):
            name = text_type(name)
        if name in api.FIELDS_TO_EXTRACT:
            val = self._course_dates.get((text_type(block.location), name), NOT_FOUND)
        else:
            val = NOT_FOUND
        return val

    def get(self, block, name):
        """
        Return field value for given block and field name.
        """
        val = self._get(block, name)
        if val is not NOT_FOUND:
            return val
        return self._defaults.get(block, name)

    def default(self, block, name):
        """
        Return the default for the field.
        """
        if name in INHERITABLE_FIELDS:
            for ancestor in _lineage(block):
                value = self._get(ancestor, name)
                if value is not NOT_FOUND:
                    return value
        return self._defaults.default(block, name)

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


class DateOverrideTransformer:
    """
    A transformer that loads date data in xblock.
    """

    WRITE_VERSION = 1
    READ_VERSION = 1

    def __init__(self, user):
        """
        Initialize the transformer with a given user.
        """
        self.user = user

    @classmethod
    def name(cls):
        """
        Return unique identifier for the transformer's class.

        same identifier used in setup.py.
        """
        return "load_date_data"

    @classmethod
    def collect(cls, block_structure):
        """
        Collect any information that's necessary to execute this transformer's transform method.
        """
        block_structure.request_xblock_fields(*api.FIELDS_TO_EXTRACT)

    def transform(self, usage_info, block_structure):
        """
        Load override data into blocks.
        """
        dates = api.get_dates_for_course(usage_info.course_key, self.user)
        for (location, field), date in dates.items():
            try:
                block_structure.override_xblock_field(
                    location,
                    field,
                    date)
            except AttributeError:
                log.debug('Missing block %s %s', location, field)
