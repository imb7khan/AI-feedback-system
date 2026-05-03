# LLM Integration Documentation

## Overview

This document describes the LLM integration using Groq for generating paragraph-level feedback on student assignments.

## Features

- **Paragraph-level feedback**: Generate detailed feedback for each paragraph
- **Structured output**: Consistent format with feedback, strengths, improvements, and scores
- **Multiple models**: Support for various Groq models (Llama3, Mixtral, Gemma)
- **Low temperature**: Set to 0.2 for consistent, reliable output
- **Error handling**: Comprehensive error handling and fallback mechanisms

## Setup

### 1. Install Dependencies

```bash
pip install groq
```

### 2. Set API Key

```bash
export GROQ_API_KEY="your-groq-api-key"
```

Or add to your environment configuration.

## API Endpoints

### POST /api/generate-feedback/

Generate AI feedback for assignment paragraphs.

**Request:**
```json
{
  "paragraphs": [
    "This is the first paragraph...",
    "This is the second paragraph..."
  ],
  "context": "Optional assignment context",
  "model": "llama-3.3-70b-versatile"
}
```

**Response:**
```json
{
  "success": true,
  "model": "llama-3.3-70b-versatile",
  "total_paragraphs": 2,
  "successful_feedback": 2,
  "average_score": 7.5,
  "feedback": [
    {
      "paragraph_index": 0,
      "paragraph_text": "This is the first paragraph...",
      "feedback": "Clear introduction with good structure...",
      "strengths": [
        "Clear topic introduction",
        "Good organization"
      ],
      "improvements": [
        "More engaging opening",
        "Add specific examples"
      ],
      "score": 7
    },
    {
      "paragraph_index": 1,
      "paragraph_text": "This is the second paragraph...",
      "feedback": "Well-developed argument with supporting points...",
      "strengths": [
        "Strong argument development",
        "Good use of evidence"
      ],
      "improvements": [
        "Better transitions between points",
        "More specific examples"
      ],
      "score": 8
    }
  ]
}
```

## Supported Models

- `llama-3.3-70b-versatile` (default) - Best quality, slower
- `llama3-8b-8192` - Faster, good quality
- `mixtral-8x7b-32768` - Good balance of speed and quality
- `gemma-7b-it` - Fastest, basic quality

## Complete Workflow

### 1. Upload and Extract Text

```bash
curl -X POST -F "file=@assignment.pdf" \
  http://127.0.0.1:8000/api/extract-text/
```

### 2. Preprocess Text

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"text":"extracted text here..."}' \
  http://127.0.0.1:8000/api/preprocess-text/
```

### 3. Generate Feedback

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "paragraphs": ["paragraph 1", "paragraph 2"],
    "context": "Essay assignment",
    "model": "llama-3.3-70b-versatile"
  }' \
  http://127.0.0.1:8000/api/generate-feedback/
```

## Code Structure

### LLM Integration Module (`feedback_system/llm_integration.py`)

**Key Classes:**

- `GroqLLMClient`: Main client for interacting with Groq API
- `ParagraphFeedback`: Data class for structured feedback
- `LLMIntegrationError`: Custom exception for LLM errors

**Key Methods:**

- `generate_paragraph_feedback()`: Generate feedback for single paragraph
- `generate_document_feedback()`: Generate feedback for all paragraphs
- `_create_paragraph_feedback_prompt()`: Create structured prompts
- `_parse_feedback_response()`: Parse LLM responses

### API View (`feedback_system/views.py`)

**FeedbackGenerationView**: Handles API requests for feedback generation

## Prompt Structure

The system uses structured prompts to ensure consistent output:

```
You are an expert writing tutor providing constructive feedback on student assignments. Analyze the following paragraph and provide specific, actionable feedback.

Paragraph {index}:
"{paragraph text}"

Assignment Context: {context}

Please provide feedback in the following format:

FEEDBACK: [Your overall feedback on this paragraph - 2-3 sentences]

STRENGTHS:
- [Strength 1]
- [Strength 2]
- [Strength 3]

IMPROVEMENTS:
- [Specific improvement suggestion 1]
- [Specific improvement suggestion 2]
- [Specific improvement suggestion 3]

SCORE: [1-10 rating for overall quality]
```

## Error Handling

The system handles various error scenarios:

1. **Missing API Key**: Returns 503 Service Unavailable
2. **Invalid Input**: Returns 400 Bad Request
3. **LLM Errors**: Returns 500 Internal Server Error
4. **Partial Failures**: Continues processing other paragraphs

## Configuration

### Temperature

Set to 0.2 for consistent, reliable output. Can be adjusted in `GroqLLMClient` class.

### Max Tokens

Set to 1000 for comprehensive feedback. Can be adjusted based on needs.

### Model Selection

Default model is `llama-3.3-70b-versatile`. Can be specified in API requests.

## Testing

### Unit Tests

```python
from feedback_system.llm_integration import GroqLLMClient

# Test with mock data
client = GroqLLMClient()
feedback = client.generate_paragraph_feedback(
    paragraph="Test paragraph",
    paragraph_index=0
)
```

### Integration Tests

```bash
# Test API endpoint
curl -X POST -H "Content-Type: application/json" \
  -d '{"paragraphs":["Test paragraph"]}' \
  http://127.0.0.1:8000/api/generate-feedback/
```

## Performance Considerations

- **Rate Limits**: Groq has rate limits, implement appropriate throttling
- **Batch Processing**: Process multiple paragraphs in parallel for efficiency
- **Caching**: Cache feedback for identical paragraphs
- **Timeout**: Set appropriate timeouts for API calls

## Security

- **API Key Security**: Never commit API keys to version control
- **Input Validation**: Validate all user inputs
- **Output Sanitization**: Sanitize LLM outputs before display
- **Rate Limiting**: Implement rate limiting to prevent abuse

## Future Enhancements

- **Streaming**: Implement streaming responses for real-time feedback
- **Custom Prompts**: Allow custom prompt templates
- **Feedback History**: Store and retrieve previous feedback
- **Quality Metrics**: Track feedback quality over time
- **Multi-language**: Support for feedback in multiple languages

## Troubleshooting

### Common Issues

1. **"API key not found"**: Set GROQ_API_KEY environment variable
2. **"Library not installed"**: Install groq package with pip
3. **"Rate limit exceeded"**: Implement rate limiting or upgrade plan
4. **"Invalid response format"**: Check LLM output parsing logic

### Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Examples

### Python Client Example

```python
import requests

# Generate feedback
response = requests.post(
    'http://127.0.0.1:8000/api/generate-feedback/',
    json={
        'paragraphs': [
            'This is a well-written paragraph...',
            'This paragraph needs improvement...'
        ],
        'context': 'Essay assignment',
        'model': 'llama-3.3-70b-versatile'
    }
)

feedback_data = response.json()
for feedback in feedback_data['feedback']:
    print(f"Paragraph {feedback['paragraph_index']}:")
    print(f"  Score: {feedback['score']}/10")
    print(f"  Feedback: {feedback['feedback']}")
    print(f"  Strengths: {', '.join(feedback['strengths'])}")
    print(f"  Improvements: {', '.join(feedback['improvements'])}")
    print()
```

### Complete Workflow Example

```python
import requests

# 1. Extract text from file
with open('assignment.pdf', 'rb') as f:
    extract_response = requests.post(
        'http://127.0.0.1:8000/api/extract-text/',
        files={'file': f}
    )
extracted_text = extract_response.json()['text']

# 2. Preprocess text
preprocess_response = requests.post(
    'http://127.0.0.1:8000/api/preprocess-text/',
    json={'text': extracted_text}
)
paragraphs = preprocess_response.json()['paragraphs']

# 3. Generate feedback
feedback_response = requests.post(
    'http://127.0.0.1:8000/api/generate-feedback/',
    json={
        'paragraphs': paragraphs,
        'context': 'Essay assignment',
        'model': 'llama-3.3-70b-versatile'
    }
)
feedback_data = feedback_response.json()

# 4. Process results
print(f"Generated feedback for {feedback_data['total_paragraphs']} paragraphs")
print(f"Average score: {feedback_data['average_score']}/10")
```

## Notes

- **No RAG**: This implementation does not include RAG (Retrieval-Augmented Generation)
- **No Agents**: This implementation does not include agent functionality
- **Simple Integration**: Focuses on direct LLM calls for feedback generation
- **Consistent Output**: Low temperature ensures consistent, reliable feedback