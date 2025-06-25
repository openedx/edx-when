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

    def ready(self):
        """
        Perform any necessary initialization when the application is ready.
        This method is called when Django starts up and the application is loaded.
        """
        # Import signal handlers or other initialization code here if needed
        from .signals import handlers
