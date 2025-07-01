"""
URLs for edx_when.
"""

from django.urls import include, path


app_name = 'edx_when'

urlpatterns = [
    path('edx_when/v1/', include('edx_when.rest_api.v1.urls'), name='v1'),
]
