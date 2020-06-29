Change Log
----------

..
   All enhancements and patches to edx_when will be documented
   in this file.  It adheres to the structure of http://keepachangelog.com/ ,
   but in reStructuredText instead of Markdown (for ease of incorporation into
   Sphinx documentation and the PyPI description).

   This project adheres to Semantic Versioning (http://semver.org/).

.. There should always be an "Unreleased" section for changes pending release.

Unreleased
~~~~~~~~~~

[1.2.9] - 2020-06-30
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Don't return due dates for enrollments originally created too close to the
course end to allow for finishing the course in time.

[1.2.8] - 2020-06-17
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Don't return due dates for enrollments created after course end

[1.2.4] - 2020-06-01
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Updates function in API for finding learners with a specific Schedule
that has an assignment on a given day, to also be inclusive of absolute
date schedules (everyone active in the course without an override).

[1.2.3] - 2020-04-30
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Dropped support for Django versions below 2.2
* Added support for python 3.8

[1.1.4] - 2019-03-30
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Drop the active index from ContentDate. It has low cardinality and Aurora was
  doing a lot of extra work to try to do an intersect query with that and
  the course_id index, when using the latter by itself would be far more
  efficient.


[1.1.3] - 2019-03-25
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

* Use memcache to cache ContentDate information in get_dates_for_course


[0.1.0] - 2019-03-04
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Added
_____

* First release on PyPI.
