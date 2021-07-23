#!/usr/bin/env python
# pylint: disable=useless-suppression
"""
Package metadata for edx_when.
"""

import os
import re
import sys

from setuptools import setup


def get_version(*file_paths):
    """
    Extract the version string from the file at the given relative path fragments.
    """
    filename = os.path.join(os.path.dirname(__file__), *file_paths)
    with open(filename) as version_file:
        version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]",
                                  version_file.read(), re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError('Unable to find version string.')


def load_requirements(*requirements_paths):
    """
    Load all requirements from the specified requirements files.

    Returns:
        list: Requirements file relative path strings
    """
    requirements = set()
    for path in requirements_paths:
        with open(path) as req_file:
            requirements.update(
                line.split('#')[0].strip() for line in req_file.readlines()
                if is_requirement(line.strip())
            )
    return list(requirements)


def is_requirement(line):
    """
    Return True if the requirement line is a package requirement.

    Returns:
        bool: True if the line is not blank, a comment, a URL, or an included file
    """
    return not (
        line == '' or
        line.startswith('-r') or
        line.startswith('#') or
        line.startswith('-e') or
        line.startswith('git+') or
        line.startswith('-c')
    )


VERSION = get_version('edx_when', '__init__.py')

if sys.argv[-1] == 'tag':
    print("Tagging the version on github:")
    os.system("git tag -a %s -m 'version %s'" % (VERSION, VERSION))
    os.system("git push --tags")
    sys.exit()

with open(os.path.join(os.path.dirname(__file__), 'README.rst')) as readme_file:
    README = readme_file.read()
with open(os.path.join(os.path.dirname(__file__), 'CHANGELOG.rst')) as changelog_file:
    CHANGELOG = changelog_file.read()

setup(
    name='edx-when',
    version=VERSION,
    description="""Your project description goes here""",
    long_description=README + '\n\n' + CHANGELOG,
    author='edX',
    author_email='oscm@edx.org',
    url='https://github.com/edx/edx-when',
    packages=[
        'edx_when',
    ],
    include_package_data=True,
    install_requires=load_requirements('requirements/base.in'),
    license="AGPL 3.0",
    zip_safe=False,
    keywords='Django edx',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU Affero General Public License v3 or later (AGPLv3+)',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.8',
    ],
    entry_points={
        'lms.djangoapp': [
            "edx_when = edx_when.apps:EdxWhenConfig",
        ],
        'cms.djangoapp': [
            "edx_when = edx_when.apps:EdxWhenConfig",
        ],
        'openedx.block_structure_transformer': [
            'load_date_data = edx_when.field_data:DateOverrideTransformer'
        ],

    },

)
