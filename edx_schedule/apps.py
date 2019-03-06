# -*- coding: utf-8 -*-
"""
edx_schedule Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig


class EdxScheduleConfig(AppConfig):
    """
    Configuration for the edx_schedule Django application.
    """

    name = 'edx_schedule'
    plugin_app = {
        u'url_config': {
            u'lms.djangoapp': {
                u'namespace': u'edx_schedule',
                u'regex': u'^api/',
                u'relative_path': u'urls',
            },
        },
    }
