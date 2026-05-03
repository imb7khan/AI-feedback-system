# Vector-Enhanced RAG System for Assignment Feedback

## Overview

This system implements a production-ready vector-embedding RAG (Retrieval-Augmented Generation) pipeline for AI-powered assignment feedback. It upgrades the previous simple database-based RAG to use FAISS vector database with semantic search capabilities.

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   Student       │         │  Vector RAG     │         │   Groq LLM      │
│   Assignment    │────────►│   System        │────────►│   (Feedback)    │
│                 │         │                 │         │                 │
└─────────────────┘         └─────────────────┘         └─────────────────┘
                                   │
                                   ▼
                          ┌─────────────────┐
                          │  FAISS Vector   │
                          │  Database      │
                          │  (Local)        │
                          └─────────────────┘
```

## Components

### 1. Vector Configuration (`vector_config.py`)
- Centralized configuration management
- Support for multiple FAISS index types (Flat, IVF, HNSW)
- Configurable chunking and retrieval parameters
- Environment variable overrides

### 2. Embedding Service (`embedding_service.py`)
- Sentence-transformers integration (all-MiniLM-L6-v2)
- Batch processing for efficiency
- Embedding caching to avoid recomputation
- 384-dimensional embeddings

### 3. Chunking Strategy (`chunking_strategy.py`)
- Intelligent text chunking with overlap
- Preserves context across chunk boundaries
- Handles different content types (rubrics, criteria, levels)
- Configurable chunk sizes

### 4. Vector Store (`vector_store.py`)
- FAISS integration for efficient similarity search
- Support for multiple index types:
  - `IndexFlatL2`: Exact L2 distance search
  - `IndexIVFFlat`: Faster search with clustering
  - `IndexHNSW`: Approximate nearest neighbor search
- Metadata management
- Index persistence and loading

### 5. Vector Retriever (`vector_retriever.py`)
- Semantic search with relevance scoring
- Advanced filtering (by rubric, criterion, type)
- Multiple query combination strategies
- Result formatting for LLM prompts

### 6. Vector Indexer (`vector_indexer.py`)
- Automated index building from database
- Incremental updates for specific rubrics
- Complete rebuild capability
- Index status monitoring

### 7. Enhanced RAG Service (`rubric_rag.py`)
- Vector-enhanced retrieval with fallback to simple RAG
- Context-aware feedback generation
- Rubric-aligned scoring
- Performance tracking

## Installation

### Prerequisites
- Python 3.8+
- Django 4.2+
- PostgreSQL database

### Install Dependencies

```bash
# Install vector RAG dependencies
pip install -r vector_requirements.txt

# Or install individually
pip install faiss-cpu sentence-transformers numpy
```

### Configuration

Set up environment variables:

```bash
# Vector RAG Configuration
export VECTOR_INDEX_TYPE="IndexFlatL2"  # or IndexIVFFlat, IndexHNSW
export VECTOR_MODEL_NAME="sentence-transformers/all-MiniLM-L6-v2"
export VECTOR_DEVICE="cpu"  # or "cuda" if GPU available
export VECTOR_TOP_K="5"
export VECTOR_SIMILARITY_THRESHOLD="0.7"
export VECTOR_INDEX_DIR="vector_index"
export VECTOR_CACHE_DIR="vector_cache"
```

## Usage

### Building the Vector Index

#### Using Django Management Commands

```bash
# Build initial index from all rubrics
python manage.py build_vector_index

# Build index for specific rubric
python manage.py build_vector_index --rubric-id 1

# Rebuild entire index from scratch
python manage.py rebuild_vector_index

# Check index status
python manage.py vector_index_status

# Build with verbose output
python manage.py build_vector_index --verbose
```

#### Using API Endpoints

```bash
# Build index
curl -X POST http://localhost:8000/api/vector/build-index/

# Build for specific rubric
curl -X POST http://localhost:8000/api/vector/build-index/ \
  -H "Content-Type: application/json" \
  -d '{"rubric_id": 1, "clear": false}'

# Rebuild index
curl -X POST http://localhost:8000/api/vector/rebuild-index/

# Get index status
curl http://localhost:8000/api/vector/status/

# Test vector search
curl -X POST http://localhost:8000/api/vector/test-search/ \
  -H "Content-Type: application/json" \
  -d '{"query": "evidence quality", "k": 3}'

# Get debug information
curl http://localhost:8000/api/vector/debug/

# Clear embedding cache
curl -X POST http://localhost:8000/api/vector/clear-cache/
```

### Using Vector RAG in Code

```python
from feedback_system.rubric_rag import RubricRAGService
from feedback_system.llm_integration import GroqLLMClient

# Initialize services
llm_client = GroqLLMClient()
rag_service = RubricRAGService(llm_client=llm_client, use_vector_rag=True)

# Generate feedback for a paragraph
paragraph = "The evidence provided in this essay is compelling and well-supported."
feedback = rag_service.generate_vector_rubric_feedback(
    paragraph=paragraph,
    paragraph_index=0,
    rubric_id=1
)

print(feedback)
```

### Using Vector Components Directly

```python
from feedback_system.vector_retriever import get_vector_retriever
from feedback_system.embedding_service import get_embedding_service

# Get retriever
retriever = get_vector_retriever()
retriever.initialize()

# Search for relevant rubric content
query = "evidence quality in academic writing"
results = retriever.retrieve(query, k=5)

# Format results for LLM prompt
formatted_context = retriever.format_results_for_prompt(results)
print(formatted_context)
```

## Configuration Options

### Index Types

#### IndexFlatL2 (Default)
- **Use case**: Small to medium datasets (< 10K vectors)
- **Pros**: Exact search, simple to use
- **Cons**: Linear search time

#### IndexIVFFlat
- **Use case**: Medium to large datasets (10K - 1M vectors)
- **Pros**: Faster search with clustering
- **Cons**: Requires training, approximate search

#### IndexHNSW
- **Use case**: Large datasets (> 1M vectors)
- **Pros**: Very fast search, good recall
- **Cons**: More memory intensive, complex

### Chunking Parameters

```python
chunk_size = 200          # Maximum characters per chunk
chunk_overlap = 50        # Overlap between chunks
min_chunk_size = 50       # Minimum chunk size to keep
```

### Retrieval Parameters

```python
top_k = 5                 # Number of results to retrieve
similarity_threshold = 0.7  # Minimum similarity score
```

## Performance

### Index Building
- **Small rubrics** (< 10): < 5 seconds
- **Medium rubrics** (10-100): < 30 seconds
- **Large rubrics** (100+): < 2 minutes

### Search Performance
- **IndexFlatL2**: ~1-5ms per query
- **IndexIVFFlat**: ~0.5-2ms per query
- **IndexHNSW**: ~0.1-1ms per query

### Memory Usage
- **IndexFlatL2**: ~4MB per 10K vectors
- **IndexIVFFlat**: ~4MB per 10K vectors + overhead
- **IndexHNSW**: ~8MB per 10K vectors

## Testing

### Run All Tests

```bash
python tests/feedback_system/test_vector_rag.py
```

### Run Specific Test Classes

```bash
python -m unittest feedback_system.tests.test_vector_rag.TestVectorConfig
python -m unittest feedback_system.tests.test_vector_rag.TestChunkingStrategy
python -m unittest feedback_system.tests.test_vector_rag.TestVectorStore
```

### Test Coverage

- ✅ Vector configuration management
- ✅ Text chunking strategies
- ✅ FAISS vector store operations
- ✅ Embedding generation and caching
- ✅ Vector retrieval and filtering
- ✅ Index building and updating
- ✅ Vector RAG integration

## Troubleshooting

### Common Issues

#### Index Not Found
```bash
# Solution: Build the index
python manage.py build_vector_index
```

#### FAISS Import Error
```bash
# Solution: Install FAISS
pip install faiss-cpu
```

#### Sentence-Transformers Import Error
```bash
# Solution: Install sentence-transformers
pip install sentence-transformers
```

#### Memory Issues
```bash
# Solution: Use smaller batch size or switch to IndexIVFFlat
export VECTOR_INDEX_TYPE="IndexIVFFlat"
```

#### Slow Search
```bash
# Solution: Switch to faster index type
export VECTOR_INDEX_TYPE="IndexHNSW"
```

## API Reference

### Management Commands

| Command | Description |
|---------|-------------|
| `build_vector_index` | Build or update vector index |
| `rebuild_vector_index` | Rebuild index from scratch |
| `vector_index_status` | Check index status and statistics |

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/vector/build-index/` | POST | Build or update index |
| `/api/vector/rebuild-index/` | POST | Rebuild index |
| `/api/vector/status/` | GET | Get index status |
| `/api/vector/test-search/` | POST | Test vector search |
| `/api/vector/debug/` | GET | Get debug information |
| `/api/vector/clear-cache/` | POST | Clear embedding cache |

## Best Practices

### 1. Index Building
- Build index after rubric changes
- Use `--rubric-id` for incremental updates
- Rebuild index periodically for consistency

### 2. Configuration
- Use `IndexFlatL2` for small datasets
- Use `IndexIVFFlat` for medium datasets
- Use `IndexHNSW` for large datasets

### 3. Chunking
- Adjust `chunk_size` based on content length
- Use `chunk_overlap` to preserve context
- Set `min_chunk_size` to filter small chunks

### 4. Retrieval
- Adjust `top_k` based on needs
- Use `similarity_threshold` to filter results
- Leverage metadata filters for precision

### 5. Performance
- Enable embedding caching for repeated queries
- Use batch processing for multiple texts
- Monitor index size and rebuild if needed

## Migration from Simple RAG

### Before (Simple RAG)
```python
# Simple database query
rubric = Rubric.objects.filter(assignment_type='essay').first()
feedback = rag_service.generate_rubric_based_feedback(paragraph, rubric)
```

### After (Vector RAG)
```python
# Vector-enhanced retrieval
rag_service = RubricRAGService(use_vector_rag=True)
feedback = rag_service.generate_vector_rubric_feedback(paragraph, rubric_id=1)
```

### Benefits
- ✅ Semantic search for relevant criteria
- ✅ Context-aware feedback generation
- ✅ Better scalability for large rubric collections
- ✅ Improved precision and relevance

## Contributing

When contributing to the vector RAG system:

1. Add tests for new features
2. Update documentation
3. Follow existing code style
4. Test with different index types
5. Monitor performance impact

## License

This project is part of the AI Assignment Feedback System.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review test cases for examples
3. Check API documentation
4. Examine debug information

## Changelog

### Version 1.0.0 (Current)
- ✅ Initial vector RAG implementation
- ✅ FAISS integration with multiple index types
- ✅ Sentence-transformers embeddings
- ✅ Comprehensive chunking strategies
- ✅ Management commands for index operations
- ✅ REST API for vector operations
- ✅ Complete test suite
- ✅ Production-ready configuration