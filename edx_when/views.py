"""
Views for date-related REST APIs.
"""
from __future__ import absolute_import, unicode_literals

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class CourseDates(APIView):
    """
    Returns dates for a course.
    """

    authentication_classes = (SessionAuthentication, JwtAuthentication)
    permission_classes = (IsAuthenticated,)
