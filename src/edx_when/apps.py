"""
edx_when Django application initialization.
"""

from django.apps import AppConfig


class EdxWhenConfig(AppConfig):
    """
    Configuration for the edx_when Django application.
    """

    name = 'edx_when'
    verbose_name = "edX When"
    plugin_app = {
        'url_config': {
            'lms.djangoapp': {
                'namespace': 'edx_when',
                'regex': '^api/',
                'relative_path': 'urls',
            },
        }
    }
