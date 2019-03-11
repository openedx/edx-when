# -*- coding: utf-8 -*-
"""
edx_when Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

from django.apps import AppConfig


class EdxWhenConfig(AppConfig):
    """
    Configuration for the edx_when Django application.
    """

    name = 'edx_when'
    plugin_app = {
        u'url_config': {
            u'lms.djangoapp': {
                u'namespace': u'edx_when',
                u'regex': u'^api/',
                u'relative_path': u'urls',
            },
        },
    }
