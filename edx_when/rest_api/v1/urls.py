"""
URLs for edx_when REST API v1.
"""

from django.conf import settings
from django.urls import re_path

from . import views

urlpatterns = [
    re_path(
        r'user-dates/{}'.format(settings.COURSE_ID_PATTERN),
        views.UserDatesView.as_view(),
        name='user_dates',
    ),
]
