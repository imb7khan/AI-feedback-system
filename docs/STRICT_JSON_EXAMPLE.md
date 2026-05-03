# Strict JSON Output Example

## Overview

This document provides the exact JSON structure that the agent returns, ensuring strict compliance with the required format.

## Required JSON Structure

### Top-Level Fields

```json
{
  "paragraph_feedback": [...],
  "rubric_scores": {...},
  "overall_feedback": {...},
  "suggestions": [...]
}
```

## Complete Example Response

```json
{
  "paragraph_feedback": [
    {
      "paragraph_index": 0,
      "text": "Climate change represents one of the most significant challenges facing humanity in the 21st century...",
      "overall_feedback": "Clear introduction with strong thesis statement that establishes the main argument effectively.",
      "rubric_scores": {
        "Thesis Statement": "8/10 - Clear but could be more specific",
        "Argument Development": "7/10 - Good development but needs more depth"
      },
      "total_score": 15,
      "max_score": 25,
      "strengths": [
        "Clear thesis statement",
        "Good organization",
        "Strong opening"
      ],
      "improvements": [
        "More specific examples",
        "Deeper analysis",
        "Better transitions"
      ]
    },
    {
      "paragraph_index": 1,
      "text": "The scientific evidence is overwhelming, with global temperatures rising at an unprecedented rate...",
      "overall_feedback": "Well-supported paragraph with relevant evidence, though integration could be stronger.",
      "rubric_scores": {
        "Evidence Quality": "7/10 - Good sources but need more quantity",
        "Evidence Integration": "6/10 - Present but not well analyzed"
      },
      "total_score": 13,
      "max_score": 20,
      "strengths": [
        "Relevant evidence",
        "Credible sources",
        "Good topic sentences"
      ],
      "improvements": [
        "More evidence quantity",
        "Better analysis",
        "Stronger connections"
      ]
    },
    {
      "paragraph_index": 2,
      "text": "This essay will examine the causes of climate change and propose comprehensive solutions...",
      "overall_feedback": "Effective conclusion that summarizes main points and provides forward-looking perspective.",
      "rubric_scores": {
        "Argument Development": "8/10 - Good flow and logical progression",
        "Writing Style": "7/10 - Clear but could be more engaging"
      },
      "total_score": 15,
      "max_score": 20,
      "strengths": [
        "Logical flow",
        "Clear summary",
        "Good conclusion"
      ],
      "improvements": [
        "More engaging tone",
        "Stronger closing statement",
        "Better transitions"
      ]
    }
  ],
  "rubric_scores": {
    "total_points": 43,
    "max_points": 65,
    "percentage": 66.15,
    "letter_grade": "C"
  },
  "overall_feedback": {
    "summary": "Overall performance: C grade (66.15%)",
    "key_strengths": [
      "Clear thesis statement",
      "Good organization",
      "Logical flow"
    ],
    "key_improvements": [
      "More specific examples",
      "Deeper analysis",
      "Better transitions"
    ]
  },
  "suggestions": [
    "Good foundation! Focus on the specific improvement areas identified",
    "Review the 'Good' vs 'Excellent' performance level differences",
    "Work on making your thesis statement more specific and compelling",
    "Incorporate more relevant and credible evidence to support your arguments",
    "Review your work for grammar, mechanics, and academic tone"
  ]
}
```

## Field Specifications

### paragraph_feedback (Array)

**Type:** Array of objects

**Fields:**
- `paragraph_index` (integer): Zero-based index of the paragraph
- `text` (string): First 100 characters of the paragraph text
- `overall_feedback` (string): Overall assessment of the paragraph
- `rubric_scores` (object): Scores for each rubric criterion
- `total_score` (number): Total score for this paragraph
- `max_score` (number): Maximum possible score for this paragraph
- `strengths` (array): List of strengths identified
- `improvements` (array): List of improvements needed

**Example:**
```json
{
  "paragraph_index": 0,
  "text": "Climate change represents one of the most significant challenges...",
  "overall_feedback": "Clear introduction with strong thesis statement...",
  "rubric_scores": {
    "Thesis Statement": "8/10 - Clear but could be more specific",
    "Argument Development": "7/10 - Good development but needs more depth"
  },
  "total_score": 15,
  "max_score": 25,
  "strengths": ["Clear thesis statement", "Good organization"],
  "improvements": ["More specific examples", "Deeper analysis"]
}
```

### rubric_scores (Object)

**Type:** Object with score information

**Fields:**
- `total_points` (number): Total points earned across all paragraphs
- `max_points` (number): Maximum possible points
- `percentage` (number): Percentage score (0-100)
- `letter_grade` (string): Letter grade (A, B, C, D, F)

**Example:**
```json
{
  "total_points": 43,
  "max_points": 65,
  "percentage": 66.15,
  "letter_grade": "C"
}
```

### overall_feedback (Object)

**Type:** Object with overall assessment

**Fields:**
- `summary` (string): Overall performance summary
- `key_strengths` (array): Top 3 strengths across all paragraphs
- `key_improvements` (array): Top 3 improvements needed

**Example:**
```json
{
  "summary": "Overall performance: C grade (66.15%)",
  "key_strengths": [
    "Clear thesis statement",
    "Good organization",
    "Logical flow"
  ],
  "key_improvements": [
    "More specific examples",
    "Deeper analysis",
    "Better transitions"
  ]
}
```

### suggestions (Array)

**Type:** Array of strings

**Fields:**
- Array of actionable suggestions for improvement

**Example:**
```json
[
  "Good foundation! Focus on the specific improvement areas identified",
  "Review the 'Good' vs 'Excellent' performance level differences",
  "Work on making your thesis statement more specific and compelling"
]
```

## Data Types

### Strict Type Enforcement

- **Integers**: Used for counts, indices, scores
- **Floats**: Used for percentages (rounded to 2 decimal places)
- **Strings**: Used for text content, descriptions
- **Arrays**: Used for lists of items
- **Objects**: Used for structured data

### No Mixed Types

- Numbers are never strings (e.g., `"15"` is invalid, `15` is valid)
- Booleans are not used in this structure
- Null values are not allowed in required fields
- All arrays contain homogeneous types

## Validation Rules

### Required Fields

All four top-level fields are required:
- `paragraph_feedback` - Must be an array
- `rubric_scores` - Must be an object
- `overall_feedback` - Must be an object
- `suggestions` - Must be an array

### Value Constraints

- `paragraph_index`: Must be >= 0
- `total_score`: Must be >= 0
- `max_score`: Must be > 0
- `percentage`: Must be between 0 and 100
- `letter_grade`: Must be one of ['A', 'B', 'C', 'D', 'F']

### String Constraints

- `text`: Maximum 100 characters (truncated with "...")
- `overall_feedback`: No length limit, but should be concise
- `summary`: Should be 1-2 sentences
- All strings must be valid UTF-8

## Error Response Format

### Validation Errors

```json
{
  "success": false,
  "error": "Invalid response format",
  "validation_errors": [
    "Missing required field: paragraph_feedback",
    "rubric_scores.percentage: Must be between 0 and 100, got 105"
  ]
}
```

### Processing Errors

```json
{
  "success": false,
  "error": "Agent processing failed: No rubric found for the given assignment type"
}
```

## API Usage

### Request Format

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "text": "Your essay text here...",
    "assignment_type": "essay",
    "context": "Academic essay on climate change"
  }' \
  http://127.0.0.1:8000/api/feedback-agent/
```

### Response Format

The response will always be valid JSON with the exact structure shown above.

### Content-Type

All responses have `Content-Type: application/json`

## Testing JSON Output

### Python Example

```python
import json
import requests

response = requests.post(
    'http://127.0.0.1:8000/api/feedback-agent/',
    json={
        'text': 'Your essay text here...',
        'assignment_type': 'essay'
    }
)

# Parse JSON
data = response.json()

# Validate structure
assert 'paragraph_feedback' in data
assert 'rubric_scores' in data
assert 'overall_feedback' in data
assert 'suggestions' in data

# Access data
for paragraph in data['paragraph_feedback']:
    print(f"Paragraph {paragraph['paragraph_index']}: {paragraph['total_score']}/{paragraph['max_score']}")

print(f"Overall: {data['rubric_scores']['letter_grade']} ({data['rubric_scores']['percentage']}%)")
```

### Command Line Example

```bash
# Pretty print JSON response
curl -X POST -H "Content-Type: application/json" \
  -d '{"text":"Test text","assignment_type":"essay"}' \
  http://127.0.0.1:8000/api/feedback-agent/ | jq .

# Validate JSON
curl -X POST -H "Content-Type: application/json" \
  -d '{"text":"Test text","assignment_type":"essay"}' \
  http://127.0.0.1:8000/api/feedback-agent/ | python3 -m json.tool > /dev/null
echo $?  # Should be 0 if valid JSON
```

## Compliance Checklist

- ✅ Strict JSON format
- ✅ No random text outside JSON
- ✅ Paragraph feedback included
- ✅ Rubric scores included
- ✅ Overall feedback included
- ✅ Suggestions included
- ✅ All required fields present
- ✅ Correct data types
- ✅ Valid UTF-8 encoding
- ✅ No trailing commas
- ✅ Proper escaping of special characters
- ✅ Consistent field naming
- ✅ No null values in required fields

## Notes

- All responses are guaranteed to be valid JSON
- No additional text or formatting outside the JSON
- Content-Type is always application/json
- Responses can be parsed by any JSON parser
- Structure is validated before returning
- Error responses also follow JSON format