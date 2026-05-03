from django.contrib import admin
from .models import AssignmentSubmission


@admin.register(AssignmentSubmission)
class AssignmentSubmissionAdmin(admin.ModelAdmin):
    """Admin interface for AssignmentSubmission model."""

    list_display = ['id', 'original_filename', 'file_type',
                    'status', 'uploaded_at']
    list_filter = ['status', 'file_type', 'uploaded_at']
    search_fields = ['original_filename']
    readonly_fields = ['uploaded_at', 'feedback_data']
    ordering = ['-uploaded_at']

    fieldsets = (
        ('File Information', {
            'fields': ('file', 'original_filename', 'file_type')
        }),
        ('Status Information', {
            'fields': ('status', 'uploaded_at')
        }),
        ('Feedback Data', {
            'fields': ('feedback_data',),
            'classes': ('collapse',)
        }),
    )
