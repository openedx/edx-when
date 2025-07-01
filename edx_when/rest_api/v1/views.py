"""
Views for the edx-when REST API v1.
"""

from edx_rest_framework_extensions.auth.jwt.authentication import JwtAuthentication
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response

from edx_when.api import get_user_dates


class UserDatesView(APIView):
    """
    View to handle user dates.
    """

    authentication_classes = (SessionAuthentication, JwtAuthentication)
    permission_classes = (IsAuthenticated,)

    def get(self, request, *args, **kwargs):
        """
        **Use Cases**

            Request user dates for a specific course.

        **Example Requests**

            GET /api/edx_when/v1/user-dates/{course_id}

        **Parameters:**

            block_types: (optional, str) Comma-separated list of block types to filter the dates.
            block_keys: (optional, str) Comma-separated list of block keys to filter the dates.
            date_types: (optional, str) Comma-separated list of date types to filter the dates.

        **Response Values**

            Body consists of the following fields:

            * user_dates: (dict) A dictionary containing user-specific dates for the course.
                * The keys are date identifiers and the values are the corresponding date values.

        **Returns**

            * 200 on success with user dates.
            * 401 if the user is not authenticated.
            * 403 if the user does not have permission to access the course.
        """

        course_id = kwargs.get('course_id')
        block_types = request.query_params.get('block_types', '').split(',')
        block_keys = request.query_params.get('block_keys', '').split(',')
        date_types = request.query_params.get('date_types', '').split(',')

        user_dates = get_user_dates(
            course_id,
            request.user.id,
            block_types=block_types if block_types != [''] else None,
            block_keys=block_keys if block_keys != [''] else None,
            date_types=date_types if date_types != [''] else None
        )
        return Response({str(key[0]): value for key, value in user_dates.items()})
