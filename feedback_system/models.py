from django.db import models
import os
from django.core.exceptions import ValidationError


def get_assignment_upload_path(instance, filename):
    """Generate upload path for assignment files based on submission ID."""
    return os.path.join('assignments', str(instance.id), filename)


class AssignmentSubmission(models.Model):
    """Model for storing student assignment submissions."""

    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    FILE_TYPE_CHOICES = [
        ('pdf', 'PDF'),
        ('docx', 'DOCX'),
        ('txt', 'Text'),
    ]

    id = models.AutoField(primary_key=True)
    file = models.FileField(upload_to=get_assignment_upload_path)
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    feedback_data = models.JSONField(null=True, blank=True)

    class Meta:
        ordering = ['-uploaded_at']

    def __str__(self):
        return f"{self.original_filename} - {self.status}"

    def save(self, *args, **kwargs):
        """Set file_type based on uploaded file extension."""
        if self.file:
            file_extension = self.file.name.split('.')[-1].lower()
            if file_extension == 'pdf':
                self.file_type = 'pdf'
            elif file_extension == 'docx':
                self.file_type = 'docx'
            elif file_extension == 'txt':
                self.file_type = 'txt'
            else:
                self.file_type = 'unknown'
        super().save(*args, **kwargs)


class Rubric(models.Model):
    """
    Model for defining assessment rubrics.

    A rubric contains multiple categories, each with criteria
    and performance levels for evaluating student work.
    """

    name = models.CharField(max_length=255, help_text="Name of the rubric")
    description = models.TextField(
        blank=True,
        help_text="Description of what this rubric evaluates"
    )
    assignment_type = models.CharField(
        max_length=100,
        blank=True,
        help_text="Type of assignment this rubric is for (e.g., 'essay', 'research paper')"
    )
    max_score = models.IntegerField(
        default=100,
        help_text="Maximum possible score for this rubric"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this rubric is active for use"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Rubrics"

    def __str__(self):
        return f"{self.name} ({self.assignment_type or 'General'})"

    def clean(self):
        """Validate rubric data."""
        if self.max_score <= 0:
            raise ValidationError("Max score must be greater than 0")

    def get_total_categories(self):
        """Get the total number of categories in this rubric."""
        return self.categories.count()

    def get_total_criteria(self):
        """Get the total number of criteria across all categories."""
        return sum(category.criteria.count() for category in self.categories.all())


class RubricCategory(models.Model):
    """
    Model for rubric categories (e.g., Argument, Evidence, Grammar).

    Each category contains multiple criteria for evaluation.
    """

    rubric = models.ForeignKey(
        Rubric,
        on_delete=models.CASCADE,
        related_name='categories',
        help_text="The rubric this category belongs to"
    )
    name = models.CharField(
        max_length=100,
        help_text="Name of the category (e.g., 'Argument', 'Evidence')"
    )
    description = models.TextField(
        blank=True,
        help_text="Description of what this category evaluates"
    )
    weight = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=1.00,
        help_text="Weight of this category in the overall rubric (0.00-1.00)"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order for this category"
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Rubric Categories"

    def __str__(self):
        return f"{self.rubric.name} - {self.name}"

    def clean(self):
        """Validate category data."""
        if self.weight < 0 or self.weight > 1:
            raise ValidationError("Weight must be between 0.00 and 1.00")


class RubricCriterion(models.Model):
    """
    Model for specific criteria within a rubric category.

    Each criterion defines what is being evaluated and has
    performance levels for scoring.
    """

    CATEGORY_CHOICES = [
        ('argument', 'Argument'),
        ('evidence', 'Evidence'),
        ('grammar', 'Grammar'),
        ('structure', 'Structure'),
        ('style', 'Style'),
        ('content', 'Content'),
        ('analysis', 'Analysis'),
        ('other', 'Other'),
    ]

    category = models.ForeignKey(
        RubricCategory,
        on_delete=models.CASCADE,
        related_name='criteria',
        help_text="The category this criterion belongs to"
    )
    name = models.CharField(
        max_length=200,
        help_text="Name of the criterion (e.g., 'Thesis clarity')"
    )
    description = models.TextField(
        help_text="Detailed description of what this criterion evaluates"
    )
    criterion_type = models.CharField(
        max_length=20,
        choices=CATEGORY_CHOICES,
        default='other',
        help_text="Type of criterion for categorization"
    )
    max_points = models.IntegerField(
        default=10,
        help_text="Maximum points for this criterion"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order for this criterion"
    )

    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = "Rubric Criteria"

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    def clean(self):
        """Validate criterion data."""
        if self.max_points <= 0:
            raise ValidationError("Max points must be greater than 0")


class RubricLevel(models.Model):
    """
    Model for performance levels within a criterion.

    Each level defines the score range and description for
    a specific level of performance (e.g., Excellent, Good, Fair, Poor).
    """

    LEVEL_CHOICES = [
        ('excellent', 'Excellent'),
        ('good', 'Good'),
        ('satisfactory', 'Satisfactory'),
        ('fair', 'Fair'),
        ('poor', 'Poor'),
        ('needs_improvement', 'Needs Improvement'),
    ]

    criterion = models.ForeignKey(
        RubricCriterion,
        on_delete=models.CASCADE,
        related_name='levels',
        help_text="The criterion this level belongs to"
    )
    level_name = models.CharField(
        max_length=50,
        choices=LEVEL_CHOICES,
        help_text="Name of the performance level"
    )
    score_range_min = models.IntegerField(
        help_text="Minimum score for this level"
    )
    score_range_max = models.IntegerField(
        help_text="Maximum score for this level"
    )
    description = models.TextField(
        help_text="Description of what constitutes this level of performance"
    )
    feedback_template = models.TextField(
        blank=True,
        help_text="Template for feedback at this level (use {criteria} as placeholder)"
    )
    order = models.IntegerField(
        default=0,
        help_text="Display order for this level"
    )

    class Meta:
        ordering = ['-score_range_max', 'order']
        verbose_name_plural = "Rubric Levels"

    def __str__(self):
        return f"{self.criterion.name} - {self.level_name} ({self.score_range_min}-{self.score_range_max})"

    def clean(self):
        """Validate level data."""
        if self.score_range_min < 0:
            raise ValidationError("Minimum score cannot be negative")
        if self.score_range_max <= self.score_range_min:
            raise ValidationError("Maximum score must be greater than minimum score")
        if self.score_range_max > self.criterion.max_points:
            raise ValidationError("Maximum score cannot exceed criterion max points")
