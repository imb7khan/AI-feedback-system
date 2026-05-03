from rest_framework import serializers
from .models import AssignmentSubmission


class AssignmentSubmissionSerializer(serializers.ModelSerializer):
    """Serializer for AssignmentSubmission model."""

    class Meta:
        model = AssignmentSubmission
        fields = ['id', 'file', 'file_type', 'original_filename',
                  'uploaded_at', 'status', 'feedback_data']
        read_only_fields = ['id', 'uploaded_at', 'status', 'feedback_data']

    def validate_file(self, value):
        """Validate uploaded file size and type."""
        # Check file size (max 10MB)
        max_size = 10 * 1024 * 1024  # 10MB
        if value.size > max_size:
            raise serializers.ValidationError(
                "File size exceeds 10MB limit."
            )

        # Check file type
        allowed_extensions = ['pdf', 'docx', 'txt']
        file_extension = value.name.split('.')[-1].lower()
        if file_extension not in allowed_extensions:
            raise serializers.ValidationError(
                f"File type '{file_extension}' not allowed. "
                f"Allowed types: {', '.join(allowed_extensions)}"
            )

        return value

    def create(self, validated_data):
        """Create assignment submission with original filename."""
        file = validated_data.get('file')
        validated_data['original_filename'] = file.name
        return super().create(validated_data)