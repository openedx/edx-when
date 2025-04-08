"""
These settings are here to use during tests, because django requires them.

In a real-world use case, apps in this project are installed into other
Django applications, so these settings will not be used.
"""
import os
from os.path import abspath, dirname, join


def root(*args):
    """
    Get the absolute path of the given path relative to the project root.
    """
    return join(abspath(dirname(__file__)), *args)


DATABASES = {
    'default': {
        'ENGINE': os.getenv('DB_ENGINE', 'django.db.backends.sqlite3'),
        'NAME': os.getenv('DB_NAME', 'default.db'),
        'USER': os.getenv('DB_USER', ''),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', ''),
        'PORT': os.getenv('DB_PORT', ''),
    }
}

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'edx_when',
    'tests.test_models_app',
)

JWT_AUTH = {
    'JWT_AUTH_COOKIE': 'edx-jwt-cookie'
}

LOCALE_PATHS = [
    root('edx_when', 'conf', 'locale'),
]

ROOT_URLCONF = 'edx_when.urls'

SECRET_KEY = 'insecure-secret-key'

COURSE_ID_PATTERN = ''
