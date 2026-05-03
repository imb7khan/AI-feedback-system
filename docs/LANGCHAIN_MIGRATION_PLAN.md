# LangChain + LangGraph Migration Plan

## Context

Migrate existing Django project from custom orchestration to LangChain + LangGraph while preserving all existing behavior, API contracts, and response structures.

## Current Architecture Analysis

### Existing Components
1. **FeedbackGenerationAgent** - Main orchestrator with 4-step workflow
2. **TextPreprocessor** - Text preprocessing into paragraphs
3. **RubricRAGService** - RAG retrieval and generation
4. **GroqLLMClient** - LLM integration with Groq API

### Current Workflow
```
Input → Preprocess → Retrieve Rubric (RAG) → Generate Feedback → Combine Output → Response
```

### Current Steps
1. **Preprocess**: Split text into paragraphs
2. **Retrieve**: Get rubric from database (RAG)
3. **Generate**: RAG-enhanced LLM feedback generation
4. **Combine**: Aggregate scores and format final output

## Migration Strategy

### Approach: Minimal, Behavior-First Migration

**Principle:** Replace internals while keeping external behavior identical.

### LangGraph State Graph Design

**State Schema:**
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
1. **preprocess_node** - Text preprocessing (replaces _preprocess_text)
2. **retrieve_rubric_node** - Rubric retrieval (replaces _retrieve_rubric)
3. **generate_feedback_node** - RAG feedback generation (replaces _generate_feedback)
4. **combine_output_node** - Final output formatting (replaces _create_final_output)

**Graph Edges:**
```
START → preprocess → retrieve_rubric → generate_feedback → combine_output → END
```

### LangChain Components

**Retrieval Chain:**
- Use existing RubricRAGService as retriever
- Wrap in LangChain Retrieval interface
- Keep database retrieval logic unchanged

**Generation Chain:**
- Use existing GroqLLMClient as LLM
- Wrap in LangChain LLM interface
- Keep prompt formatting logic unchanged

## Implementation Plan

### Phase 1: Dependencies and Setup

**Files to Create:**
1. `feedback_system/langchain_integration.py` - LangChain/LangGraph integration
2. `feedback_system/langchain_config.py` - LangChain configuration

**Dependencies to Add:**
```bash
pip install langchain langchain-community langchain-groq
```

### Phase 2: LangGraph State Graph

**File:** `feedback_system/langchain_integration.py`

**Components:**
1. `FeedbackState` - State schema
2. `create_feedback_graph()` - LangGraph graph builder
3. `LangChainFeedbackAgent` - Wrapper agent class

### Phase 3: LangChain Components

**File:** `feedback_system/langchain_integration.py`

**Components:**
1. `RubricRetriever` - LangChain retriever wrapper
2. `GroqLLM` - LangChain LLM wrapper
3. `FeedbackChain` - LangChain chain for feedback generation

### Phase 4: API Integration

**Files to Modify:**
1. `feedback_system/agent_views.py` - Update to use LangChain agent
2. `feedback_system/feedback_agent.py` - Keep as fallback, add LangChain option

**Changes:**
- Add LangChain agent initialization option
- Keep existing API contracts unchanged
- Maintain backward compatibility

### Phase 5: Testing

**Files to Create:**
1. `tests/feedback_system/test_langchain_integration.py` - LangChain tests
2. `test_langchain_migration.py` - Migration validation tests

**Test Coverage:**
- State graph execution
- LangChain component integration
- API endpoint behavior
- Response structure validation
- Error handling parity

### Phase 6: Documentation Updates

**Files to Update:**
1. `AGENT_ARCHITECTURE_DOCUMENTATION.md` - Update architecture description
2. `RAG_SYSTEM_DOCUMENTATION.md` - Update RAG implementation details
3. `COMPLETE_PROJECT_SUMMARY.md` - Update project summary
4. `FINAL_PROJECT_STATUS.md` - Update final status
5. Create `LANGCHAIN_MIGRATION.md` - Migration documentation

## File-by-File Change List

### New Files (3)
1. `feedback_system/langchain_integration.py` - LangChain/LangGraph integration
2. `feedback_system/langchain_config.py` - LangChain configuration
3. `tests/feedback_system/test_langchain_integration.py` - LangChain tests

### Modified Files (2)
1. `feedback_system/agent_views.py` - Add LangChain agent option
2. `feedback_system/feedback_agent.py` - Add LangChain compatibility layer

### Documentation Updates (5)
1. `AGENT_ARCHITECTURE_DOCUMENTATION.md` - Architecture update
2. `RAG_SYSTEM_DOCUMENTATION.md` - RAG implementation update
3. `COMPLETE_PROJECT_SUMMARY.md` - Project summary update
4. `FINAL_PROJECT_STATUS.md` - Final status update
5. `LANGCHAIN_MIGRATION.md` - New migration documentation

## Behavior Parity Notes

### Exactly Same Behavior

**API Contracts:**
- Request/response structures unchanged
- Endpoint signatures unchanged
- Error handling behavior preserved

**Scoring Logic:**
- Rubric-based scoring semantics identical
- Letter grade calculation unchanged
- Score aggregation logic preserved

**Response Structure:**
- JSON response format unchanged
- Field names and types preserved
- Nested structure maintained

**Error Handling:**
- Error messages equivalent
- Fallback behavior preserved
- Validation logic unchanged

### Implementation Differences (Internal Only)

**Orchestration:**
- Old: Custom Python orchestration
- New: LangGraph state graph
- External behavior: Identical

**Retrieval:**
- Old: Direct database calls
- New: LangChain retriever wrapper
- External behavior: Identical

**Generation:**
- Old: Direct Groq API calls
- New: LangChain LLM wrapper
- External behavior: Identical

## Unavoidable Differences

### None Expected

With proper implementation, there should be no unavoidable differences in external behavior. All changes are internal implementation details.

## Risk Mitigation

### Backward Compatibility
- Keep existing FeedbackGenerationAgent as fallback
- Add feature flag to switch between implementations
- Maintain identical API contracts

### Testing Strategy
- Comprehensive regression testing
- API endpoint behavior validation
- Response structure verification
- Error handling parity checks

### Rollback Plan
- Keep original implementation intact
- Easy to disable LangChain integration
- No database changes required
- No breaking changes to API

## Success Criteria

### Functional Requirements
- ✅ All existing API endpoints work identically
- ✅ Request/response structures unchanged
- ✅ Scoring logic semantics preserved
- ✅ Error handling behavior equivalent

### Technical Requirements
- ✅ LangGraph state graph mirrors existing workflow
- ✅ LangChain components wrap existing functionality
- ✅ No database schema changes
- ✅ No new dependencies beyond LangChain packages

### Quality Requirements
- ✅ Code is clean and readable
- ✅ Changes are minimal and focused
- ✅ Documentation is accurate and updated
- ✅ Tests pass and provide good coverage

## Implementation Order

1. **Dependencies** - Install LangChain packages
2. **Configuration** - Create LangChain config
3. **Integration** - Implement LangChain/LangGraph components
4. **API Updates** - Update API views to use LangChain
5. **Testing** - Create and run comprehensive tests
6. **Documentation** - Update all relevant documentation
7. **Validation** - Verify behavior parity and rollback capability

## Estimated Complexity

- **Low Risk**: Internal implementation changes only
- **Medium Effort**: LangChain/LangGraph learning curve
- **High Value**: Modern architecture with future benefits
- **Short Timeline**: Focused, minimal changes

## Next Steps

1. Review and approve this migration plan
2. Install required dependencies
3. Implement LangChain integration
4. Test thoroughly
5. Update documentation
6. Validate behavior parity
7. Deploy with monitoring