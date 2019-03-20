# -*- coding: utf-8 -*-
"""
edx_when Django application initialization.
"""

from __future__ import absolute_import, unicode_literals

import traceback
import warnings

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

    def ready(self):
        """
        Set up signal handlers for edx_when.
        """
        try:
            import edx_when.signals  # pylint: disable=unused-variable
        except ImportError:
            warnings.warn("Not able to import code from edx-platform")
            traceback.print_exc()
