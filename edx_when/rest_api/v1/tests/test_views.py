"""
Tests for the UserDatesView in the edx_when REST API.
"""

from datetime import datetime
from unittest.mock import patch

from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase


class TestUserDatesView(APITestCase):
    """
    Tests for UserDatesView.
    """

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='testpass')
        self.course_id = 'course-v1:TestOrg+TestCourse+TestRun'
        self.url = reverse('edx_when:v1:user_dates', kwargs={'course_id': self.course_id})

    @patch('edx_when.rest_api.v1.views.get_user_dates')
    def test_get_user_dates_success(self, mock_get_user_dates):
        """
        Test successful retrieval of user dates.
        """
        mock_user_dates = {
            ('assignment_1', 'due'): datetime(2023, 12, 15, 23, 59, 59),
            ('quiz_1', 'due'): datetime(2023, 12, 20, 23, 59, 59),
        }
        mock_get_user_dates.return_value = mock_user_dates

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {
            'assignment_1': datetime(2023, 12, 15, 23, 59, 59),
            'quiz_1': datetime(2023, 12, 20, 23, 59, 59),
        })
        mock_get_user_dates.assert_called_once_with(
            self.course_id,
            self.user.id,
            block_types=None,
            block_keys=None,
            date_types=None
        )

    @patch('edx_when.rest_api.v1.views.get_user_dates')
    def test_get_user_dates_with_filters(self, mock_get_user_dates):
        """
        Test retrieval of user dates with query parameter filters.
        """
        mock_get_user_dates.return_value = {}

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {
            'block_types': 'assignment,quiz',
            'block_keys': 'block1,block2',
            'date_types': 'due,start'
        })

        self.assertEqual(response.status_code, 200)
        mock_get_user_dates.assert_called_once_with(
            self.course_id,
            self.user.id,
            block_types=['assignment', 'quiz'],
            block_keys=['block1', 'block2'],
            date_types=['due', 'start']
        )

    @patch('edx_when.rest_api.v1.views.get_user_dates')
    def test_get_user_dates_empty_filters(self, mock_get_user_dates):
        """
        Test that empty filter parameters are converted to None.
        """
        mock_get_user_dates.return_value = {}

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url, {
            'block_types': '',
            'block_keys': '',
            'date_types': ''
        })

        self.assertEqual(response.status_code, 200)
        mock_get_user_dates.assert_called_once_with(
            self.course_id,
            self.user.id,
            block_types=None,
            block_keys=None,
            date_types=None
        )

    def test_get_user_dates_unauthenticated(self):
        """
        Test that unauthenticated requests return 401.
        """
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 401)

    @patch('edx_when.rest_api.v1.views.get_user_dates')
    def test_get_user_dates_empty_response(self, mock_get_user_dates):
        """
        Test successful retrieval with empty user dates.
        """
        mock_get_user_dates.return_value = {}

        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {})
