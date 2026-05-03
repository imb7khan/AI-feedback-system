"""
Comprehensive test suite for vector RAG system.

This module provides unit and integration tests for:
- Vector configuration
- Embedding service
- Chunking strategy
- Vector store
- Vector retriever
- Vector indexer
- Vector RAG integration
"""

import os
import sys
import django
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile
import shutil

# Setup Django (project root = tests/feedback_system -> tests -> repo root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assignment_feedback.settings')
django.setup()

from feedback_system.vector_config import VectorConfig, get_config, set_config
from feedback_system.chunking_strategy import ChunkingStrategy, TextChunk
from feedback_system.vector_store import VectorStore, SearchResult
from feedback_system.embedding_service import EmbeddingService
from feedback_system.vector_retriever import VectorRetriever, RetrievalResult
from feedback_system.vector_indexer import VectorIndexer


class TestVectorConfig(unittest.TestCase):
    """Test vector configuration management."""

    def setUp(self):
        """Set up test configuration."""
        self.temp_dir = tempfile.mkdtemp()
        self.config = VectorConfig(
            index_dir=Path(self.temp_dir),
            cache_dir=Path(self.temp_dir)
        )

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_config_initialization(self):
        """Test configuration initialization."""
        self.assertEqual(self.config.index_type, "IndexFlatL2")
        self.assertEqual(self.config.embedding_dimension, 384)
        self.assertEqual(self.config.chunk_size, 200)
        self.assertEqual(self.config.top_k, 5)

    def test_config_validation(self):
        """Test configuration validation."""
        # Valid config
        self.config._validate_config()

        # Invalid index type
        with self.assertRaises(ValueError):
            invalid_config = VectorConfig(index_type="InvalidIndex")
            invalid_config._validate_config()

        # Invalid chunk size
        with self.assertRaises(ValueError):
            invalid_config = VectorConfig(chunk_size=0)
            invalid_config._validate_config()

    def test_config_paths(self):
        """Test configuration path methods."""
        index_path = self.config.get_index_path()
        metadata_path = self.config.get_metadata_path()

        self.assertTrue(index_path.exists())
        self.assertTrue(metadata_path.parent.exists())

    def test_config_serialization(self):
        """Test configuration to/from dict."""
        config_dict = self.config.to_dict()
        new_config = VectorConfig.from_dict(config_dict)

        self.assertEqual(new_config.index_type, self.config.index_type)
        self.assertEqual(new_config.chunk_size, self.config.chunk_size)
        self.assertEqual(new_config.top_k, self.config.top_k)


class TestChunkingStrategy(unittest.TestCase):
    """Test text chunking strategy."""

    def setUp(self):
        """Set up chunking strategy."""
        self.chunker = ChunkingStrategy()

    def test_short_text_single_chunk(self):
        """Test that short text becomes single chunk."""
        text = "This is a short text."
        chunks = self.chunker.chunk_text(text)

        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, text)

    def test_long_text_multiple_chunks(self):
        """Test that long text is split into multiple chunks."""
        text = "This is a longer text that should be split into multiple chunks. " * 10
        chunks = self.chunker.chunk_text(text)

        self.assertGreater(len(chunks), 1)
        self.assertTrue(all(len(chunk.text) <= self.chunker.chunk_size + 50 for chunk in chunks))

    def test_chunk_overlap(self):
        """Test that chunks have overlap."""
        text = "This is a text that should have overlap between chunks. " * 10
        chunks = self.chunker.chunk_text(text)

        if len(chunks) > 1:
            # Check that consecutive chunks have some overlap
            first_chunk_end = chunks[0].text[-50:]
            second_chunk_start = chunks[1].text[:50]
            # They should share some content
            self.assertTrue(
                any(word in second_chunk_start for word in first_chunk_end.split())
            )

    def test_chunk_metadata(self):
        """Test that chunks have correct metadata."""
        text = "Test text for metadata."
        chunks = self.chunker.chunk_text(
            text,
            source_type="test",
            source_id=123,
            metadata={"key": "value"}
        )

        self.assertEqual(chunks[0].source_type, "test")
        self.assertEqual(chunks[0].source_id, 123)
        self.assertEqual(chunks[0].metadata["key"], "value")

    def test_empty_text(self):
        """Test handling of empty text."""
        chunks = self.chunker.chunk_text("")
        self.assertEqual(len(chunks), 0)

    def test_chunk_stats(self):
        """Test chunk statistics."""
        text = "Test text for statistics. " * 10
        chunks = self.chunker.chunk_text(text)
        stats = self.chunker.get_chunk_stats(chunks)

        self.assertEqual(stats["total_chunks"], len(chunks))
        self.assertGreater(stats["total_length"], 0)
        self.assertGreater(stats["avg_length"], 0)


class TestVectorStore(unittest.TestCase):
    """Test FAISS vector store."""

    def setUp(self):
        """Set up vector store."""
        self.temp_dir = tempfile.mkdtemp()
        from feedback_system.vector_config import VectorConfig
        config = VectorConfig(
            index_dir=Path(self.temp_dir),
            cache_dir=Path(self.temp_dir)
        )
        self.store = VectorStore(config)
        self.store.initialize_index()

    def tearDown(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_index_initialization(self):
        """Test index initialization."""
        self.assertIsNotNone(self.store.index)
        self.assertTrue(self.store._initialized)

    def test_add_vectors(self):
        """Test adding vectors to index."""
        embeddings = [[0.1, 0.2, 0.3] * 128]  # 384 dimensions
        metadata = [{"chunk_id": "test_1", "text": "Test text"}]

        self.store.add_vectors(embeddings, metadata)

        self.assertEqual(self.store.index.ntotal, 1)
        self.assertEqual(len(self.store.metadata), 1)

    def test_search_vectors(self):
        """Test searching vectors."""
        # Add some vectors
        embeddings = [
            [0.1, 0.2, 0.3] * 128,
            [0.4, 0.5, 0.6] * 128,
            [0.7, 0.8, 0.9] * 128
        ]
        metadata = [
            {"chunk_id": "test_1", "text": "First text"},
            {"chunk_id": "test_2", "text": "Second text"},
            {"chunk_id": "test_3", "text": "Third text"}
        ]

        self.store.add_vectors(embeddings, metadata)

        # Search
        query = [0.1, 0.2, 0.3] * 128
        results = self.store.search(query, k=2)

        self.assertLessEqual(len(results), 2)
        self.assertTrue(all(isinstance(r, SearchResult) for r in results))

    def test_save_and_load(self):
        """Test saving and loading index."""
        # Add vectors
        embeddings = [[0.1, 0.2, 0.3] * 128]
        metadata = [{"chunk_id": "test_1", "text": "Test text"}]

        self.store.add_vectors(embeddings, metadata)

        # Save
        self.store.save()

        # Create new store and load
        new_store = VectorStore(self.store.config)
        new_store.load()

        self.assertEqual(new_store.index.ntotal, 1)
        self.assertEqual(len(new_store.metadata), 1)

    def test_store_stats(self):
        """Test store statistics."""
        stats = self.store.get_stats()

        self.assertTrue(stats["initialized"])
        self.assertEqual(stats["dimension"], 384)
        self.assertEqual(stats["total_vectors"], 0)


class TestEmbeddingService(unittest.TestCase):
    """Test embedding service."""

    def setUp(self):
        """Set up embedding service."""
        try:
            self.service = EmbeddingService()
        except Exception as e:
            self.skipTest(f"Embedding service not available: {e}")

    def test_single_embedding(self):
        """Test generating single embedding."""
        text = "This is a test text."
        embedding = self.service.generate_embedding(text)

        self.assertEqual(len(embedding), 384)
        self.assertTrue(all(isinstance(x, float) for x in embedding))

    def test_batch_embeddings(self):
        """Test generating batch embeddings."""
        texts = ["First text", "Second text", "Third text"]
        embeddings = self.service.generate_embeddings(texts)

        self.assertEqual(len(embeddings), 3)
        self.assertTrue(all(len(emb) == 384 for emb in embeddings))

    def test_embedding_dimension(self):
        """Test embedding dimension."""
        dimension = self.service.get_embedding_dimension()
        self.assertEqual(dimension, 384)

    def test_cache_functionality(self):
        """Test embedding caching."""
        text = "Cached text"

        # First call
        embedding1 = self.service.generate_embedding(text)

        # Second call (should use cache)
        embedding2 = self.service.generate_embedding(text)

        self.assertEqual(embedding1, embedding2)

    def test_cache_stats(self):
        """Test cache statistics."""
        stats = self.service.get_cache_stats()

        self.assertIn("enabled", stats)
        self.assertIn("entries", stats)
        self.assertIn("model_name", stats)


class TestVectorRetriever(unittest.TestCase):
    """Test vector retriever."""

    def setUp(self):
        """Set up vector retriever."""
        try:
            self.temp_dir = tempfile.mkdtemp()
            from feedback_system.vector_config import VectorConfig
            config = VectorConfig(
                index_dir=Path(self.temp_dir),
                cache_dir=Path(self.temp_dir)
            )

            self.store = VectorStore(config)
            self.store.initialize_index()

            self.embedding_service = EmbeddingService()
            self.retriever = VectorRetriever(
                vector_store=self.store,
                embedding_service=self.embedding_service
            )
            self.retriever.initialize()

            # Add some test data
            embeddings = [
                self.embedding_service.generate_embedding("Test text about evidence"),
                self.embedding_service.generate_embedding("Test text about arguments"),
                self.embedding_service.generate_embedding("Test text about grammar")
            ]
            metadata = [
                {"chunk_id": "ev_1", "text": "Evidence quality criteria", "rubric_id": 1},
                {"chunk_id": "arg_1", "text": "Argument strength criteria", "rubric_id": 1},
                {"chunk_id": "gram_1", "text": "Grammar and style criteria", "rubric_id": 1}
            ]
            self.store.add_vectors(embeddings, metadata)

        except Exception as e:
            self.skipTest(f"Vector retriever not available: {e}")

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_retrieve(self):
        """Test basic retrieval."""
        query = "evidence and arguments"
        results = self.retriever.retrieve(query, k=2)

        self.assertLessEqual(len(results), 2)
        self.assertTrue(all(isinstance(r, RetrievalResult) for r in results))

    def test_retrieve_with_filter(self):
        """Test retrieval with metadata filter."""
        query = "evidence"
        results = self.retriever.retrieve(
            query,
            k=5,
            filter_rubric_id=1
        )

        self.assertTrue(all(r.rubric_id == 1 for r in results))

    def test_format_results(self):
        """Test formatting results for prompt."""
        query = "evidence"
        results = self.retriever.retrieve(query, k=2)

        formatted = self.retriever.format_results_for_prompt(results)

        self.assertIn("Relevant Rubric Information", formatted)
        self.assertGreater(len(formatted), 0)

    def test_retriever_stats(self):
        """Test retriever statistics."""
        stats = self.retriever.get_retrieval_stats()

        self.assertTrue(stats["initialized"])
        self.assertIn("vector_store", stats)
        self.assertIn("embedding_service", stats)


class TestVectorIndexer(unittest.TestCase):
    """Test vector indexer."""

    def setUp(self):
        """Set up vector indexer."""
        try:
            self.temp_dir = tempfile.mkdtemp()
            from feedback_system.vector_config import VectorConfig
            config = VectorConfig(
                index_dir=Path(self.temp_dir),
                cache_dir=Path(self.temp_dir)
            )

            self.store = VectorStore(config)
            self.store.initialize_index()

            self.embedding_service = EmbeddingService()
            self.chunker = ChunkingStrategy()

            self.indexer = VectorIndexer(
                vector_store=self.store,
                embedding_service=self.embedding_service,
                chunking_strategy=self.chunker
            )
            self.indexer.initialize()

        except Exception as e:
            self.skipTest(f"Vector indexer not available: {e}")

    def tearDown(self):
        """Clean up temporary directory."""
        if hasattr(self, 'temp_dir'):
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_process_rubric(self):
        """Test processing rubric into chunks."""
        # Create mock rubric
        rubric = Mock()
        rubric.id = 1
        rubric.title = "Test Rubric"
        rubric.description = "Test description"

        # Create mock criterion
        criterion = Mock()
        criterion.id = 1
        criterion.name = "Evidence"
        criterion.description = "Evidence quality"
        criterion.levels.all.return_value = []

        rubric.criteria.all.return_value = [criterion]

        # Process rubric
        chunks = self.indexer._process_rubric(rubric)

        self.assertGreater(len(chunks), 0)
        self.assertTrue(all(isinstance(c, TextChunk) for c in chunks))

    def test_index_status(self):
        """Test getting index status."""
        status = self.indexer.get_index_status()

        self.assertIn("vector_store", status)
        self.assertIn("database", status)
        self.assertIn("config", status)


class TestVectorRAGIntegration(unittest.TestCase):
    """Integration tests for vector RAG system."""

    def setUp(self):
        """Set up integration test."""
        try:
            from feedback_system.rubric_rag import RubricRAGService
            from feedback_system.llm_integration import GroqLLMClient

            # Skip if no API key
            if not os.getenv("GROQ_API_KEY"):
                self.skipTest("GROQ_API_KEY not set")

            self.rag_service = RubricRAGService(use_vector_rag=True)

        except Exception as e:
            self.skipTest(f"Vector RAG integration not available: {e}")

    def test_vector_rag_initialization(self):
        """Test vector RAG service initialization."""
        self.assertIsNotNone(self.rag_service)
        self.assertTrue(self.rag_service.use_vector_rag)

    def test_vector_retrieval(self):
        """Test vector retrieval functionality."""
        query = "evidence quality in academic writing"
        result = self.rag_service.retrieve_relevant_rubric_chunks(query)

        # Result may be None if index is not built
        if result is not None:
            self.assertIn("Relevant Rubric Information", result)


def run_tests():
    """Run all tests."""
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestVectorConfig))
    suite.addTests(loader.loadTestsFromTestCase(TestChunkingStrategy))
    suite.addTests(loader.loadTestsFromTestCase(TestVectorStore))
    suite.addTests(loader.loadTestsFromTestCase(TestEmbeddingService))
    suite.addTests(loader.loadTestsFromTestCase(TestVectorRetriever))
    suite.addTests(loader.loadTestsFromTestCase(TestVectorIndexer))
    suite.addTests(loader.loadTestsFromTestCase(TestVectorRAGIntegration))

    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Return exit code
    return 0 if result.wasSuccessful() else 1


if __name__ == '__main__':
    sys.exit(run_tests())