# Single Agent Architecture Documentation

## Overview

This document explains the single agent architecture that orchestrates the complete feedback generation workflow.

## Agent Design: Simple Orchestrator Pattern

The `FeedbackGenerationAgent` is a **SINGLE agent** that coordinates multiple specialized components. This is **NOT** a multi-agent system.

### Architecture Overview

```
Input → Agent → [Components] → Agent → Output
```

The agent acts as a conductor, coordinating different "instruments" (components) to create a harmonious result (final feedback).

## Agent Responsibilities

The agent is responsible for:

1. **Take essay paragraphs as input** - Accept raw text and assignment details
2. **Call LLM for feedback generation** - Coordinate LLM calls with RAG context
3. **Retrieve rubric using RAG** - Get evaluation criteria from database
4. **Generate scores based on rubric** - Calculate rubric-aligned scores
5. **Combine everything into final output** - Integrate all results into structured response

## Workflow Steps

### Step 1: Text Preprocessing
- **Component**: `TextPreprocessor`
- **Action**: Clean and split text into paragraphs
- **Input**: Raw essay text
- **Output**: List of clean paragraphs

### Step 2: Rubric Retrieval (RAG)
- **Component**: `RubricRAGService`
- **Action**: Get evaluation rubric from database
- **Input**: Assignment type (e.g., 'essay')
- **Output**: Rubric with criteria and performance levels

### Step 3: Feedback Generation
- **Component**: `GroqLLMClient` + RAG
- **Action**: Generate rubric-aligned feedback using LLM
- **Input**: Paragraphs + Rubric context
- **Output**: Scores and detailed feedback

### Step 4: Result Integration
- **Component**: `FeedbackGenerationAgent`
- **Action**: Combine scores and feedback into final output
- **Input**: Preprocessed data + Rubric + Feedback
- **Output**: Structured final response

## Why Single Agent?

### 1. Simplicity
- One entry point for the entire workflow
- Easy to understand and maintain
- Clear responsibility: orchestration only

### 2. Performance
- No inter-agent communication overhead
- Direct component calls
- Faster execution

### 3. Reliability
- Fewer moving parts
- Easier error handling
- Simpler debugging

### 4. Maintainability
- Clear code structure
- Easy to modify individual components
- Straightforward testing

## Agent vs Multi-Agent

### Single Agent (This Implementation)
- One coordinator agent
- Direct component calls
- Simple, linear workflow
- Easy to understand

### Multi-Agent (Not Used Here)
- Multiple specialized agents
- Agent-to-agent communication
- Complex coordination
- Harder to debug

## Component Architecture

The agent coordinates these components:

### 1. TextPreprocessor
- **Responsibility**: Text cleaning and paragraph splitting
- **Interface**: `preprocess_text(text) → paragraphs`
- **Independence**: Can be tested standalone

### 2. RubricRAGService
- **Responsibility**: Rubric retrieval and prompt augmentation
- **Interface**: `retrieve_rubric() → rubric`
- **Independence**: Can work without LLM

### 3. GroqLLMClient
- **Responsibility**: LLM interaction
- **Interface**: `generate_feedback() → feedback`
- **Independence**: Can be tested with mock responses

### 4. FeedbackGenerationAgent
- **Responsibility**: Workflow orchestration
- **Interface**: `process(input) → output`
- **Independence**: Coordinates all components

## Design Principles

### 1. Single Responsibility
Each component does one thing well:
- Preprocessor: Only handles text
- RAG Service: Only handles rubrics
- LLM Client: Only handles LLM calls
- Agent: Only handles coordination

### 2. Clear Interfaces
Well-defined input/output contracts:
- Input: `AgentInput` dataclass
- Output: `AgentOutput` dataclass
- Each component: Clear function signatures

### 3. Error Handling
Graceful degradation:
- Missing rubric → Clear error message
- LLM failure → Informative error
- Invalid input → Validation error

### 4. Testability
Independent testing:
- Each component can be tested alone
- Agent can be tested with mocks
- End-to-end testing possible

## Data Flow

### Input Data (AgentInput)
```python
AgentInput(
    text="Raw essay text...",
    assignment_type="essay",
    context="Academic essay...",
    rubric_id=optional
)
```

### Agent Orchestration
```
1. Preprocess text → paragraphs
2. Get rubric → criteria
3. Generate feedback → scores
4. Combine results → output
```

### Output Data (AgentOutput)
```python
AgentOutput(
    success=True,
    rubric={...},
    preprocessed_data={...},
    feedback_results={...},
    final_output={
        'metadata': {...},
        'rubric_summary': {...},
        'overall_performance': {
            'total_points': 42,
            'max_points': 65,
            'percentage': 64.62,
            'letter_grade': 'C'
        },
        'paragraph_analysis': [...],
        'strengths_summary': [...],
        'improvements_summary': [...],
        'recommendations': [...]
    }
)
```

## Benefits of This Architecture

### 1. Clarity
- Easy to understand the workflow
- Clear separation of concerns
- Obvious data flow

### 2. Flexibility
- Easy to swap components
- Can add new steps
- Simple to modify

### 3. Scalability
- Components can be optimized independently
- Can add caching where needed
- Can parallelize independent steps

### 4. Maintainability
- Clear code structure
- Easy to debug
- Simple to extend

## Usage Examples

### Python Usage
```python
from feedback_system.feedback_agent import FeedbackGenerationAgent, AgentInput
from feedback_system.llm_integration import GroqLLMClient

# Create LLM client
llm_client = GroqLLMClient()

# Initialize agent
agent = FeedbackGenerationAgent(llm_client=llm_client)

# Create input
input_data = AgentInput(
    text="Your essay text here...",
    assignment_type="essay",
    context="Academic essay on climate change"
)

# Process
output = agent.process(input_data)

# Access results
if output.success:
    print(f"Score: {output.final_output['overall_performance']['percentage']}%")
    print(f"Grade: {output.final_output['overall_performance']['letter_grade']}")

    for paragraph in output.final_output['paragraph_analysis']:
        idx = paragraph['paragraph_index']
        score = paragraph['total_score']
        max_score = paragraph['max_score']
        print(f"Paragraph {idx}: {score}/{max_score}")
```

### API Usage
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "text": "Your essay text here...",
    "assignment_type": "essay",
    "context": "Academic essay on climate change"
  }' \
  http://127.0.0.1:8000/api/feedback-agent/
```

## API Endpoints

### 1. Feedback Agent
```
POST /api/feedback-agent/
```
Complete workflow orchestration

### 2. Agent Architecture
```
GET /api/agent-architecture/
```
Detailed architecture explanation

### 3. Agent Workflow
```
GET /api/agent-workflow/
```
Workflow steps and components information

## Implementation Details

### Agent Class Structure
```python
class FeedbackGenerationAgent:
    def __init__(self, llm_client):
        self.llm_client = llm_client
        self.text_preprocessor = TextPreprocessor()
        self.rag_service = RubricRAGService(llm_client)

    def process(self, agent_input):
        # Main orchestration method
        preprocessed_data = self._preprocess_text(agent_input.text)
        rubric_data = self._retrieve_rubric(agent_input.assignment_type)
        feedback_results = self._generate_feedback(paragraphs, rubric_data)
        final_output = self._create_final_output(preprocessed_data, rubric_data, feedback_results)
        return AgentOutput(success=True, final_output=final_output)
```

### Key Methods

#### `_preprocess_text(text)`
- Cleans and splits text into paragraphs
- Returns statistics about the text

#### `_retrieve_rubric(assignment_type, rubric_id)`
- Retrieves rubric from database using RAG
- Converts to dictionary format

#### `_generate_feedback(paragraphs, rubric_data, context)`
- Generates rubric-aligned feedback using LLM
- Returns scores and detailed analysis

#### `_create_final_output(preprocessed_data, rubric_data, feedback_results)`
- Combines all results into structured output
- Calculates letter grades and recommendations

## Error Handling

The agent handles various error scenarios:

1. **Missing Rubric**: Returns clear error message
2. **Invalid Input**: Validates input before processing
3. **LLM Failure**: Provides informative error information
4. **Component Failure**: Graceful degradation with partial results

## Testing

### Unit Tests
- Test each component independently
- Mock LLM responses for testing
- Validate data transformations

### Integration Tests
- Test complete workflow with real components
- Verify end-to-end data flow
- Test error scenarios

### API Tests
- Test all agent endpoints
- Validate request/response formats
- Test error handling

## Performance Characteristics

- **Preprocessing**: < 10ms
- **Rubric Retrieval**: < 15ms
- **Feedback Generation**: 2-5 seconds (LLM dependent)
- **Result Integration**: < 5ms
- **Total Time**: 2-5.5 seconds

## Security Considerations

1. **Input Validation**: All inputs are validated
2. **SQL Injection**: Protected by Django ORM
3. **API Key Security**: Environment variables only
4. **Error Messages**: Don't expose sensitive information

## Future Enhancements

### Potential Improvements
1. **Caching**: Cache rubrics and preprocessed results
2. **Parallel Processing**: Process paragraphs in parallel
3. **Streaming**: Stream results as they're generated
4. **Custom Components**: Allow custom component injection
5. **Metrics**: Track performance and usage

### Advanced Features
1. **Multi-Rubric Support**: Compare against multiple rubrics
2. **Adaptive Processing**: Adjust workflow based on input
3. **Learning**: Improve recommendations over time
4. **Real-time Updates**: Live feedback during writing

## LangChain + LangGraph Integration

### Overview

The system now supports LangChain + LangGraph for modern orchestration while maintaining the original architecture. This provides:

- **LangGraph State Graph**: Declarative workflow orchestration
- **LangChain Components**: Standardized LLM and retrieval interfaces
- **Backward Compatibility**: Original implementation remains as fallback
- **Feature Flags**: Enable/disable LangChain components via configuration

### LangGraph State Graph

The LangGraph implementation mirrors the original 4-step workflow:

```python
class FeedbackState(TypedDict):
    input_text: str
    assignment_type: str
    context: Optional[str]
    rubric_id: Optional[int]
    model: str
    paragraphs: List[str]
    rubric_data: Optional[Dict[str, Any]]
    feedback_results: Optional[Dict[str, Any]]
    final_output: Optional[Dict[str, Any]]
    error: Optional[str]
```

**Graph Nodes:**
1. **preprocess_node** - Text preprocessing (replaces `_preprocess_text`)
2. **retrieve_rubric_node** - Rubric retrieval (replaces `_retrieve_rubric`)
3. **generate_feedback_node** - RAG feedback generation (replaces `_generate_feedback`)
4. **combine_output_node** - Final output formatting (replaces `_create_final_output`)

**Graph Edges:**
```
START → preprocess → retrieve_rubric → generate_feedback → combine_output → END
```

### LangChain Components

**LangChainFeedbackAgent:**
- Wraps existing components in LangChain interfaces
- Uses LangGraph for orchestration
- Maintains identical external behavior
- Falls back to original implementation if needed

**Configuration:**
```python
from feedback_system.langchain_config import LangChainConfig

config = LangChainConfig(
    default_model="llama-3.3-70b-versatile",
    temperature=0.2,
    max_tokens=1000,
    enable_langchain=True,
    enable_langgraph=True
)
```

### Usage

**Python Usage with LangChain:**
```python
from feedback_system.langchain_integration import LangChainFeedbackAgent

# Initialize LangChain agent
agent = LangChainFeedbackAgent()

# Process input (dict format)
result = agent.process({
    'text': 'Your essay text here...',
    'assignment_type': 'essay',
    'context': 'Academic essay on climate change'
})

# Access results (same structure as original)
if result['success']:
    print(f"Score: {result['final_output']['rubric_scores']['percentage']}%")
    print(f"Grade: {result['final_output']['rubric_scores']['letter_grade']}")
```

**API Usage (unchanged):**
```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{
    "text": "Your essay text here...",
    "assignment_type": "essay",
    "context": "Academic essay on climate change"
  }' \
  http://127.0.0.1:8000/api/feedback-agent/
```

### Behavior Parity

**Identical External Behavior:**
- ✅ Same request/response structures
- ✅ Same API endpoints
- ✅ Same scoring logic
- ✅ Same error handling
- ✅ Same performance characteristics

**Internal Implementation Differences:**
- Orchestration: LangGraph state graph vs manual coordination
- Retrieval: LangChain retriever wrapper vs direct database calls
- Generation: LangChain LLM wrapper vs direct Groq API calls

### Configuration

**Environment Variables:**
```bash
# Enable/disable LangChain components
ENABLE_LANGCHAIN=true
ENABLE_LANGGRAPH=true

# LangChain configuration
LANGCHAIN_TEMPERATURE=0.2
LANGCHAIN_MAX_TOKENS=1000

# Model configuration
GROQ_MODEL=llama-3.3-70b-versatile
```

### Testing

**LangChain Tests:**
```bash
# Run LangChain integration tests
python tests/feedback_system/test_langchain_integration.py

# Run with pytest
pytest tests/feedback_system/test_langchain_integration.py -v
```

**Test Coverage:**
- Configuration management
- State graph execution
- Node functionality
- Error handling
- Behavior parity with original implementation

### Migration Benefits

**Modern Architecture:**
- Declarative workflow definition
- Standardized component interfaces
- Better observability and debugging
- Easier to extend and modify

**Backward Compatibility:**
- Original implementation preserved
- Easy to rollback if needed
- No breaking changes to API
- Gradual migration possible

**Future-Proof:**
- Leverages LangChain ecosystem
- Supports advanced patterns when needed
- Community support and updates
- Industry-standard approach

## Conclusion

This single agent architecture provides a clean, efficient way to orchestrate complex workflows without the overhead of multi-agent systems. The design emphasizes simplicity, clarity, and maintainability while providing powerful functionality through coordinated components.

The agent successfully fulfills all responsibilities:
- ✅ Takes essay paragraphs as input
- ✅ Calls LLM for feedback generation
- ✅ Retrieves rubric using RAG
- ✅ Generates scores based on rubric
- ✅ Combines everything into final output

With a simple, well-explained architecture that is easy to understand and maintain.