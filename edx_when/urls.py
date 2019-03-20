# -*- coding: utf-8 -*-
"""
URLs for edx_when.
"""
from __future__ import absolute_import, unicode_literals

from django.conf import settings
from django.conf.urls import url

from . import views

app_name = 'edx_when'

urlpatterns = [
    url(
        r'edx_when/course/{}'.format(settings.COURSE_ID_PATTERN),
        views.CourseDates.as_view(),
        name='course_dates'
    )
]
