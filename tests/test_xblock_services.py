"""
Tests for XBlock related stuff.
"""
from __future__ import absolute_import, unicode_literals

import datetime

import mock
from django.contrib.auth.models import User
from django.test import TestCase

from edx_when import api, field_data
from test_utils import make_items


class MockBlock(object):
    """
    Fake Xblock
    """

    def __init__(self, location, parent=None):
        self.location = location
        self.parent = parent

    def get_parent(self):
        """
        Return the parent block.
        """
        return self.parent


class XblockTests(TestCase):
    """
    Base class for these tests.
    """

    def setUp(self):
        super(XblockTests, self).setUp()
        self.items = make_items()
        self.course_id = self.items[0][0].course_key
        api.set_dates_for_course(self.course_id, self.items)
        self.user = User(username='tester', email='tester@test.com')
        self.user.save()


class TestFieldData(XblockTests):
    """
    Tests for the FieldData subclass.
    """

    def test_field_data_get(self):
        defaults = mock.MagicMock()
        dfd = field_data.DateLookupFieldData(defaults, course_id=self.course_id, use_cached=False)
        block = MockBlock(self.items[0][0])

        date = dfd.get(block, 'due')
        assert date == self.items[0][1]['due']

        # non-date
        dfd.get(block, b'foo')
        assert defaults.get.called_once_with(block.location, 'foo')

        # non-existent value
        defaults.get.side_effect = KeyError()
        badblock = MockBlock('foo')
        assert dfd.has(badblock, 'foo') is False

        # block with parent with date
        child = MockBlock('child', block)
        date = dfd.get(child, 'due')
        assert date == self.items[0][1]['due']

        with self.assertRaises(KeyError):
            dfd.get(badblock, 'due')

    def test_field_data_set_delete(self):
        defaults = mock.MagicMock()
        dfd = field_data.DateLookupFieldData(defaults, course_id=self.course_id, use_cached=False)
        dfd.set('foo', 'bar', 'x')
        assert defaults.called_once_with('foo', 'bar', 'x')
        dfd.delete('baz', 'boing')
        assert defaults.called_once_with('baz', 'boing')

    def test_wrapped_fielddata(self):
        defaults = mock.MagicMock()
        dfd1 = field_data.DateLookupFieldData(defaults, course_id=self.course_id, use_cached=False)
        dfd2 = field_data.DateLookupFieldData(dfd1, course_id=self.course_id)
        assert dfd1._defaults == dfd2._defaults  # pylint: disable=protected-access


class TransformerTests(XblockTests):
    """
    Tests for the BlockTransformer class.
    """

    def test_name(self):
        assert field_data.DateOverrideTransformer.name() == 'load_date_data'

    def test_collect(self):
        block_structure = mock.MagicMock()
        field_data.DateOverrideTransformer.collect(block_structure)
        assert block_structure.request_xblock_fields.called_once_with('due', 'start')

    def test_transform(self):
        override = datetime.datetime(2020, 1, 1)
        api.set_date_for_block(self.items[0][0].course_key, self.items[0][0], 'due', override, user=self.user)
        usage_info = mock.MagicMock()
        usage_info.course_key = self.course_id
        block_structure = mock.MagicMock()
        transformer = field_data.DateOverrideTransformer(self.user)
        transformer.transform(usage_info, block_structure)
        assert block_structure.override_xblock_field.call_count == 3
        args = block_structure.override_xblock_field.call_args_list
        for arg in args:
            call_args = arg[0]
            if call_args[0] == self.items[0][0]:
                assert call_args[2] == override
