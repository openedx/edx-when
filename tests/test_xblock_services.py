"""
Tests for XBlock related stuff.
"""

import datetime
from unittest import mock

from django.contrib import auth
from django.test import TestCase

from edx_when import api, field_data
from test_utils import make_items

NUM_OVERRIDES = 6

User = auth.get_user_model()


class MockBlock:
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
        super().setUp()
        self.items = make_items(with_relative=True)
        self.course_id = self.items[0][0].course_key
        api.set_dates_for_course(self.course_id, self.items)
        self.user = User(username='tester', email='tester@test.com')
        self.user.save()

        schedule = mock.Mock(name="schedule", start_date=datetime.datetime(2019, 4, 1))

        mock_Schedule = mock.Mock(name="Schedule")
        mock_Schedule.objects.get.return_value = schedule
        schedule_patcher = mock.patch('edx_when.utils.Schedule', mock_Schedule)
        schedule_patcher.start()
        self.addCleanup(schedule_patcher.stop)


class TestFieldData(XblockTests):
    """
    Tests for the FieldData subclass.
    """

    def test_field_data_get(self):
        defaults = mock.MagicMock()
        dfd = field_data.DateLookupFieldData(defaults, course_id=self.course_id, use_cached=False, user=self.user)
        block = MockBlock(self.items[0][0])

        date = dfd.get(block, 'due')
        assert date == self.items[0][1]['due']

        # non-date
        dfd.get(block, 'foo')
        defaults.get.assert_called_once_with(block, 'foo')

        # non-existent value
        defaults.has.return_value = False
        badblock = MockBlock('foo')
        assert dfd.has(badblock, 'foo') is False

        # block with parent with date
        child = MockBlock('child', block)
        date = dfd.get(child, 'due')
        assert dfd.get(child, 'due') is defaults.get(child, 'due')
        assert dfd.default(child, 'due') == self.items[0][1]['due']

        assert dfd.get(badblock, 'due') is defaults.get(badblock, 'due')

    def test_field_data_has(self):
        defaults = mock.MagicMock()
        dfd = field_data.DateLookupFieldData(defaults, course_id=self.course_id, use_cached=False, user=self.user)
        block = MockBlock(self.items[0][0])

        assert dfd.has(block, 'due') is True
        assert dfd.has(block, 'foo') is defaults.has(block, 'foo')
        child = MockBlock('child', block)
        assert dfd.has(child, 'due') is False
        assert dfd.default(child, 'due') == self.items[0][1]['due']
        assert dfd.default(child, 'foo') is defaults.default(child, 'foo')

    def test_field_data_set_delete(self):
        defaults = mock.MagicMock()
        dfd = field_data.DateLookupFieldData(defaults, course_id=self.course_id, use_cached=False, user=self.user)
        dfd.set('foo', 'bar', 'x')
        defaults.set.assert_called_once_with('foo', 'bar', 'x')
        dfd.delete('baz', 'boing')
        defaults.delete.assert_called_once_with('baz', 'boing')

    def test_wrapped_fielddata(self):
        defaults = mock.MagicMock()
        dfd1 = field_data.DateLookupFieldData(defaults, course_id=self.course_id, use_cached=False, user=self.user)
        dfd2 = field_data.DateLookupFieldData(dfd1, course_id=self.course_id, user=self.user)
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
        block_structure.request_xblock_fields.assert_called_once_with('due', 'start', 'end')

    @mock.patch('edx_when.api._are_relative_dates_enabled', return_value=True)
    def test_transform(self, _mock):
        override = datetime.datetime(2020, 1, 1)
        api.set_date_for_block(self.items[0][0].course_key, self.items[0][0], 'due', override, user=self.user)
        usage_info = mock.MagicMock()
        usage_info.course_key = self.course_id
        block_structure = mock.MagicMock()
        transformer = field_data.DateOverrideTransformer(self.user)
        transformer.transform(usage_info, block_structure)
        assert block_structure.override_xblock_field.call_count == NUM_OVERRIDES
        args = block_structure.override_xblock_field.call_args_list
        for arg in args:
            call_args = arg[0]
            if call_args[0] == self.items[0][0]:
                assert call_args[2] == override

        # now make it raise exceptions
        # attributeerror is swallowed
        # in the case where a block does not exist for some reason
        block_structure.override_xblock_field.side_effect = AttributeError()
        transformer.transform(usage_info, block_structure)
        # other exceptions should bubble up
        block_structure.override_xblock_field.side_effect = ValueError()
        with self.assertRaises(ValueError):
            transformer.transform(usage_info, block_structure)
