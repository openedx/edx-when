"""
Django admin support for edx-when.
"""

from django.contrib import admin

from .models import ContentDate, DatePolicy, UserDate


@admin.register(ContentDate)
class ContentDateAdmin(admin.ModelAdmin):
    """Admin config for ContentDate."""

    list_display = [
        'course_id',
        'location',
        'field',
        'policy',
        'active',
    ]
    list_filter = ['active']
    search_fields = ['course_id', 'location']
    ordering = ['course_id', 'policy']

    raw_id_fields = ['policy']  # dropdown of dates is not helpful

    # Specified just to control ordering
    fields = ['course_id', 'location', 'field', 'policy', 'active']


@admin.register(DatePolicy)
class DatePolicyAdmin(admin.ModelAdmin):
    """Admin config for DatePolicy."""

    search_fields = ['abs_date', 'rel_date']


@admin.register(UserDate)
class UserDateAdmin(admin.ModelAdmin):
    """Admin config for UserDate."""

    list_display = [
        'user',
        '_course_id',
        '_location',
        '_field',
        '_date',
    ]
    search_fields = ['user__username', 'content_date__course_id', 'content_date__location']
    ordering = ['user', 'content_date__course_id', 'content_date__policy']

    raw_id_fields = ['content_date', 'user']
    exclude = ['actor']

    def _course_id(self, obj):
        return obj.content_date.course_id

    def _location(self, obj):
        return obj.content_date.location

    def _field(self, obj):
        return obj.content_date.field

    def _date(self, obj):
        return obj.abs_date or obj.rel_date

    def save_model(self, request, obj, form, change):
        """Make sure that we record who last changed the model."""
        obj.actor = request.user
        super().save_model(request, obj, form, change)
