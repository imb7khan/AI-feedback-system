"""
Serializers for rubric models.

Provides JSON serialization for rubric, categories, criteria, and levels.
"""

from rest_framework import serializers
from .models import Rubric, RubricCategory, RubricCriterion, RubricLevel


class RubricLevelSerializer(serializers.ModelSerializer):
    """Serializer for rubric performance levels."""

    class Meta:
        model = RubricLevel
        fields = [
            'id',
            'level_name',
            'score_range_min',
            'score_range_max',
            'description',
            'feedback_template',
            'order'
        ]


class RubricCriterionSerializer(serializers.ModelSerializer):
    """Serializer for rubric criteria with nested levels."""

    levels = RubricLevelSerializer(many=True, read_only=True)

    class Meta:
        model = RubricCriterion
        fields = [
            'id',
            'name',
            'description',
            'criterion_type',
            'max_points',
            'order',
            'levels'
        ]


class RubricCategorySerializer(serializers.ModelSerializer):
    """Serializer for rubric categories with nested criteria."""

    criteria = RubricCriterionSerializer(many=True, read_only=True)

    class Meta:
        model = RubricCategory
        fields = [
            'id',
            'name',
            'description',
            'weight',
            'order',
            'criteria'
        ]


class RubricSerializer(serializers.ModelSerializer):
    """Serializer for rubrics with nested categories."""

    categories = RubricCategorySerializer(many=True, read_only=True)
    total_categories = serializers.SerializerMethodField()
    total_criteria = serializers.SerializerMethodField()

    class Meta:
        model = Rubric
        fields = [
            'id',
            'name',
            'description',
            'assignment_type',
            'max_score',
            'is_active',
            'created_at',
            'updated_at',
            'categories',
            'total_categories',
            'total_criteria'
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_total_categories(self, obj):
        """Get total number of categories."""
        return obj.get_total_categories()

    def get_total_criteria(self, obj):
        """Get total number of criteria."""
        return obj.get_total_criteria()


class RubricListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for rubric list views."""

    total_categories = serializers.SerializerMethodField()
    total_criteria = serializers.SerializerMethodField()

    class Meta:
        model = Rubric
        fields = [
            'id',
            'name',
            'description',
            'assignment_type',
            'max_score',
            'is_active',
            'total_categories',
            'total_criteria'
        ]

    def get_total_categories(self, obj):
        """Get total number of categories."""
        return obj.get_total_categories()

    def get_total_criteria(self, obj):
        """Get total number of criteria."""
        return obj.get_total_criteria()


class RubricCategoryCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating rubric categories."""

    class Meta:
        model = RubricCategory
        fields = [
            'id',
            'rubric',
            'name',
            'description',
            'weight',
            'order'
        ]


class RubricCriterionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating rubric criteria."""

    class Meta:
        model = RubricCriterion
        fields = [
            'id',
            'category',
            'name',
            'description',
            'criterion_type',
            'max_points',
            'order'
        ]


class RubricLevelCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating rubric levels."""

    class Meta:
        model = RubricLevel
        fields = [
            'id',
            'criterion',
            'level_name',
            'score_range_min',
            'score_range_max',
            'description',
            'feedback_template',
            'order'
        ]