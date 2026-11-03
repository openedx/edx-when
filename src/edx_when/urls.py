"""
URLs for edx_when.
"""

from django.conf import settings
from django.urls import re_path

from . import views

app_name = 'edx_when'

urlpatterns = [
    re_path(
        r'edx_when/course/{}'.format(settings.COURSE_ID_PATTERN),
        views.CourseDates.as_view(),
        name='course_dates'
    )
]
