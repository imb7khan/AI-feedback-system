"""
JSON schema validator for enforcing strict JSON output.

This module ensures all agent responses comply with the required JSON structure:
- paragraph_feedback
- rubric_scores
- overall_feedback
- suggestions
"""

import json
import logging
from typing import Dict, Any, List
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class JSONValidationResult:
    """Result of JSON validation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]


class JSONValidator:
    """
    Validates JSON structure against required schema.

    Ensures strict compliance with the required output format.
    """

    REQUIRED_FIELDS = {
        'paragraph_feedback': list,
        'rubric_scores': dict,
        'overall_feedback': dict,
        'suggestions': list
    }

    PARAGRAPH_FEEDBACK_FIELDS = {
        'paragraph_index': int,
        'text': str,
        'overall_feedback': str,
        'rubric_scores': dict,
        'total_score': (int, float),
        'max_score': (int, float),
        'strengths': list,
        'improvements': list
    }

    RUBRIC_SCORES_FIELDS = {
        'total_points': (int, float),
        'max_points': (int, float),
        'percentage': (int, float),
        'letter_grade': str
    }

    OVERALL_FEEDBACK_FIELDS = {
        'summary': str,
        'key_strengths': list,
        'key_improvements': list
    }

    @staticmethod
    def validate_structure(data: Dict[str, Any]) -> JSONValidationResult:
        """
        Validate that data matches required JSON structure.

        Args:
            data: Dictionary to validate

        Returns:
            JSONValidationResult with validation status
        """
        errors = []
        warnings = []

        # Check required top-level fields
        for field, field_type in JSONValidator.REQUIRED_FIELDS.items():
            if field not in data:
                errors.append(f"Missing required field: {field}")
            elif not isinstance(data[field], field_type):
                errors.append(f"Field '{field}' must be {field_type.__name__}, got {type(data[field]).__name__}")

        # Validate paragraph_feedback structure
        if 'paragraph_feedback' in data:
            for i, paragraph in enumerate(data['paragraph_feedback']):
                para_errors = JSONValidator._validate_paragraph_feedback(paragraph, i)
                errors.extend(para_errors)

        # Validate rubric_scores structure
        if 'rubric_scores' in data:
            score_errors = JSONValidator._validate_rubric_scores(data['rubric_scores'])
            errors.extend(score_errors)

        # Validate overall_feedback structure
        if 'overall_feedback' in data:
            feedback_errors = JSONValidator._validate_overall_feedback(data['overall_feedback'])
            errors.extend(feedback_errors)

        # Validate suggestions structure
        if 'suggestions' in data:
            if not isinstance(data['suggestions'], list):
                errors.append("suggestions must be a list")
            else:
                for i, suggestion in enumerate(data['suggestions']):
                    if not isinstance(suggestion, str):
                        errors.append(f"suggestion[{i}] must be a string, got {type(suggestion).__name__}")

        # Check for unexpected fields (warnings only)
        expected_fields = set(JSONValidator.REQUIRED_FIELDS.keys())
        actual_fields = set(data.keys())
        unexpected_fields = actual_fields - expected_fields

        if unexpected_fields:
            warnings.append(f"Unexpected fields found: {', '.join(unexpected_fields)}")

        is_valid = len(errors) == 0

        return JSONValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings
        )

    @staticmethod
    def _validate_paragraph_feedback(paragraph: Dict[str, Any], index: int) -> List[str]:
        """Validate paragraph feedback structure."""
        errors = []

        for field, field_type in JSONValidator.PARAGRAPH_FEEDBACK_FIELDS.items():
            if field not in paragraph:
                errors.append(f"paragraph_feedback[{index}]: Missing field '{field}'")
            elif not isinstance(paragraph[field], field_type):
                actual_type = type(paragraph[field]).__name__
                expected_type = field_type.__name__ if isinstance(field_type, type) else f"one of {field_type}"
                errors.append(f"paragraph_feedback[{index}].{field}: Expected {expected_type}, got {actual_type}")

        return errors

    @staticmethod
    def _validate_rubric_scores(scores: Dict[str, Any]) -> List[str]:
        """Validate rubric scores structure."""
        errors = []

        for field, field_type in JSONValidator.RUBRIC_SCORES_FIELDS.items():
            if field not in scores:
                errors.append(f"rubric_scores: Missing field '{field}'")
            elif not isinstance(scores[field], field_type):
                actual_type = type(scores[field]).__name__
                expected_type = field_type.__name__ if isinstance(field_type, type) else f"one of {field_type}"
                errors.append(f"rubric_scores.{field}: Expected {expected_type}, got {actual_type}")

        # Validate percentage range
        if 'percentage' in scores:
            percentage = scores['percentage']
            if not (0 <= percentage <= 100):
                errors.append(f"rubric_scores.percentage: Must be between 0 and 100, got {percentage}")

        # Validate letter grade
        if 'letter_grade' in scores:
            valid_grades = ['A', 'B', 'C', 'D', 'F']
            if scores['letter_grade'] not in valid_grades:
                errors.append(f"rubric_scores.letter_grade: Must be one of {valid_grades}, got {scores['letter_grade']}")

        return errors

    @staticmethod
    def _validate_overall_feedback(feedback: Dict[str, Any]) -> List[str]:
        """Validate overall feedback structure."""
        errors = []

        for field, field_type in JSONValidator.OVERALL_FEEDBACK_FIELDS.items():
            if field not in feedback:
                errors.append(f"overall_feedback: Missing field '{field}'")
            elif not isinstance(feedback[field], field_type):
                actual_type = type(feedback[field]).__name__
                expected_type = field_type.__name__ if isinstance(field_type, type) else f"one of {field_type}"
                errors.append(f"overall_feedback.{field}: Expected {expected_type}, got {actual_type}")

        return errors

    @staticmethod
    def ensure_json_serializable(data: Any) -> Dict[str, Any]:
        """
        Ensure data is JSON serializable.

        Args:
            data: Data to check

        Returns:
            JSON-serializable dictionary

        Raises:
            TypeError: If data contains non-serializable types
        """
        try:
            # Try to serialize to JSON
            json.dumps(data)
            return data
        except TypeError as e:
            logger.error(f"Data contains non-JSON-serializable types: {str(e)}")
            raise TypeError(f"Data contains non-JSON-serializable types: {str(e)}")

    @staticmethod
    def format_json_response(data: Dict[str, Any], indent: int = 2) -> str:
        """
        Format data as strict JSON string.

        Args:
            data: Data to format
            indent: JSON indentation level

        Returns:
            Formatted JSON string
        """
        # Ensure data is serializable
        JSONValidator.ensure_json_serializable(data)

        # Format as JSON
        return json.dumps(data, indent=indent, ensure_ascii=False)

    @staticmethod
    def validate_and_format(data: Dict[str, Any]) -> tuple[str, JSONValidationResult]:
        """
        Validate and format data as JSON.

        Args:
            data: Data to validate and format

        Returns:
            Tuple of (formatted_json_string, validation_result)
        """
        # Validate structure
        validation_result = JSONValidator.validate_structure(data)

        # Format as JSON
        json_string = JSONValidator.format_json_response(data)

        return json_string, validation_result