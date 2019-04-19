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
        'url_config': {
            'lms.djangoapp': {
                'namespace': u'edx_when',
                'regex': u'^api/',
                'relative_path': u'urls',
            },
        },
        'signals_config': {
            'cms.djangoapp': {
                'receivers': [
                    {
                        'receiver_func_name': 'extract_dates',
                        'signal_path': 'xmodule.modulestore.django.COURSE_PUBLISHED'
                    }
                ]
            }
        }
    }
