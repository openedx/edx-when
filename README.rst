edx-when
=============================

|pypi-badge| |CI| |codecov-badge| |doc-badge| |pyversions-badge|
|license-badge|

Overview
--------

edx-when is designed to be the central source of dates for the LMS.
This repository is deployed to PyPI and designed to be installed and imported by an installation of edx-platform.
As part of being integrated into edx-platform, edx-when shares the **same** database as the rest of the platform.
It is written to by Studio when a Course is published
(via https://github.com/edx/edx-platform/blob/master/openedx/core/djangoapps/course_date_signals/handlers.py)
and then the LMS reads from it in several locations.
This repo contains start, end, and due dates for Courses and offers the
functionality to have both absolute and relative dates.

License
-------

The code in this repository is licensed under the AGPL 3.0 unless
otherwise noted.

Please see ``LICENSE.txt`` for details.

How To Contribute
-----------------

Contributions are very welcome.

Please read `How To Contribute <https://github.com/edx/edx-platform/blob/master/CONTRIBUTING.rst>`_ for details.

Even though they were written with ``edx-platform`` in mind, the guidelines
should be followed for Open edX code in general.

PR description template should be automatically applied if you are sending PR from github interface; otherwise you
can find it it at `PULL_REQUEST_TEMPLATE.md <https://github.com/edx/edx-when/blob/master/.github/PULL_REQUEST_TEMPLATE.md>`_

Issue report template should be automatically applied if you are sending it from github UI as well; otherwise you
can find it at `ISSUE_TEMPLATE.md <https://github.com/edx/edx-when/blob/master/.github/ISSUE_TEMPLATE.md>`_

Reporting Security Issues
-------------------------

Please do not report security issues in public. Please email security@edx.org.

Getting Help
------------

Have a question about this repository, or about Open edX in general?  Please
refer to this `list of resources`_ if you need any assistance.

.. _list of resources: https://open.edx.org/getting-help


.. |pypi-badge| image:: https://img.shields.io/pypi/v/edx-when.svg
    :target: https://pypi.python.org/pypi/edx-when/
    :alt: PyPI

.. |CI| image:: https://github.com/edx/edx-when/workflows/Python%20CI/badge.svg?branch=master
    :target: https://github.com/edx/edx-when/actions?query=workflow%3A%22Python+CI%22
    :alt: CI

.. |codecov-badge| image:: http://codecov.io/github/edx/edx-when/coverage.svg?branch=master
    :target: http://codecov.io/github/edx/edx-when?branch=master
    :alt: Codecov

.. |doc-badge| image:: https://readthedocs.org/projects/edx-when/badge/?version=latest
    :target: http://edx-when.readthedocs.io/en/latest/
    :alt: Documentation

.. |pyversions-badge| image:: https://img.shields.io/pypi/pyversions/edx-when.svg
    :target: https://pypi.python.org/pypi/edx-when/
    :alt: Supported Python versions

.. |license-badge| image:: https://img.shields.io/github/license/edx/edx-when.svg
    :target: https://github.com/edx/edx-when/blob/master/LICENSE.txt
    :alt: License
