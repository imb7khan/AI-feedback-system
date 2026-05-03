"""
Vector indexer for building and maintaining FAISS index from database rubrics.

This module provides functionality to:
- Build FAISS index from database rubrics
- Rebuild index when rubrics change
- Update index incrementally
- Manage index lifecycle and persistence
"""

import logging
from typing import List, Dict, Any, Optional
from django.db.models import QuerySet

from .vector_store import VectorStore
from .embedding_service import EmbeddingService
from .chunking_strategy import ChunkingStrategy, TextChunk
from .vector_config import get_config

logger = logging.getLogger(__name__)


class VectorIndexerError(Exception):
    """Custom exception for vector indexer errors."""
    pass


class VectorIndexer:
    """
    Indexer for building and maintaining FAISS index from database.

    Handles the complete pipeline from database to indexed vectors.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        chunking_strategy: Optional[ChunkingStrategy] = None,
        config=None
    ):
        """
        Initialize vector indexer.

        Args:
            vector_store: VectorStore instance (uses global if not provided)
            embedding_service: EmbeddingService instance (uses global if not provided)
            chunking_strategy: ChunkingStrategy instance (uses global if not provided)
            config: VectorConfig instance (uses default if not provided)
        """
        self.config = config or get_config()
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.chunking_strategy = chunking_strategy
        self._initialized = False

    def initialize(self) -> None:
        """Initialize indexer with required services."""
        if self.vector_store is None:
            from .vector_store import get_vector_store
            self.vector_store = get_vector_store()

        if self.embedding_service is None:
            from .embedding_service import get_embedding_service
            self.embedding_service = get_embedding_service()

        if self.chunking_strategy is None:
            from .chunking_strategy import get_chunking_strategy
            self.chunking_strategy = get_chunking_strategy()

        self._initialized = True
        logger.info("Vector indexer initialized")

    def build_index_from_database(
        self,
        rubric_queryset: Optional[QuerySet] = None,
        clear_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Build FAISS index from database rubrics.

        Args:
            rubric_queryset: QuerySet of rubrics to index (indexes all if not provided)
            clear_existing: Whether to clear existing index before building

        Returns:
            Dictionary with indexing statistics
        """
        if not self._initialized:
            self.initialize()

        try:
            # Import models here to avoid circular imports
            from .models import Rubric, RubricCriterion, RubricLevel

            # Get rubrics to index
            if rubric_queryset is None:
                rubric_queryset = Rubric.objects.all()

            rubrics = list(rubric_queryset)
            if not rubrics:
                logger.warning("No rubrics found to index")
                return {
                    "success": True,
                    "rubrics_indexed": 0,
                    "chunks_indexed": 0,
                    "message": "No rubrics to index"
                }

            logger.info(f"Building index from {len(rubrics)} rubrics")

            # Clear existing index if requested
            if clear_existing:
                self.vector_store.clear()
                logger.info("Cleared existing index")

            # Process each rubric
            all_chunks = []
            for rubric in rubrics:
                rubric_chunks = self._process_rubric(rubric)
                all_chunks.extend(rubric_chunks)

            if not all_chunks:
                logger.warning("No chunks generated from rubrics")
                return {
                    "success": True,
                    "rubrics_indexed": len(rubrics),
                    "chunks_indexed": 0,
                    "message": "No chunks generated"
                }

            logger.info(f"Generated {len(all_chunks)} chunks from {len(rubrics)} rubrics")

            # Generate embeddings for all chunks
            texts = [chunk.text for chunk in all_chunks]
            embeddings = self.embedding_service.generate_embeddings(texts)

            # Prepare metadata
            metadata_list = []
            for chunk in all_chunks:
                metadata = {
                    'chunk_id': chunk.chunk_id,
                    'text': chunk.text,
                    'source_type': chunk.source_type,
                    'source_id': chunk.source_id,
                    **chunk.metadata
                }
                metadata_list.append(metadata)

            # Train IVF index if needed
            if isinstance(self.vector_store.index, type(None)) or \
               (hasattr(self.vector_store.index, 'is_trained') and not self.vector_store.index.is_trained):
                if len(embeddings) >= self.config.nlist:
                    self.vector_store.train(embeddings)
                    logger.info("Trained IVF index")

            # Add vectors to index
            self.vector_store.add_vectors(embeddings, metadata_list)

            # Save index
            self.vector_store.save()

            stats = {
                "success": True,
                "rubrics_indexed": len(rubrics),
                "chunks_indexed": len(all_chunks),
                "index_stats": self.vector_store.get_stats()
            }

            logger.info(f"Index built successfully: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Failed to build index: {str(e)}")
            raise VectorIndexerError(f"Index building failed: {str(e)}")

    def _process_rubric(self, rubric) -> List[TextChunk]:
        """
        Process a single rubric into chunks.

        Args:
            rubric: Rubric model instance

        Returns:
            List of TextChunk objects
        """
        chunks = []

        # Chunk rubric name and description
        if rubric.name:
            name_chunks = self.chunking_strategy.chunk_text(
                rubric.name,
                source_type="rubric",
                source_id=rubric.id,
                metadata={"rubric_id": rubric.id, "field": "name"}
            )
            chunks.extend(name_chunks)

        if rubric.description:
            desc_chunks = self.chunking_strategy.chunk_text(
                rubric.description,
                source_type="rubric",
                source_id=rubric.id,
                metadata={"rubric_id": rubric.id, "field": "description"}
            )
            chunks.extend(desc_chunks)

        # Chunk criteria
        for category in rubric.categories.all():
            for criterion in category.criteria.all():
                criterion_chunks = self._process_criterion(criterion, rubric.id)
                chunks.extend(criterion_chunks)

        return chunks

    def _process_criterion(self, criterion, rubric_id: int) -> List[TextChunk]:
        """
        Process a single criterion into chunks.

        Args:
            criterion: RubricCriterion model instance
            rubric_id: Parent rubric ID

        Returns:
            List of TextChunk objects
        """
        chunks = []

        # Chunk criterion name and description
        if criterion.name:
            name_chunks = self.chunking_strategy.chunk_text(
                criterion.name,
                source_type="criterion",
                source_id=criterion.id,
                metadata={
                    "rubric_id": rubric_id,
                    "criterion_id": criterion.id,
                    "field": "name"
                }
            )
            chunks.extend(name_chunks)

        if criterion.description:
            desc_chunks = self.chunking_strategy.chunk_text(
                criterion.description,
                source_type="criterion",
                source_id=criterion.id,
                metadata={
                    "rubric_id": rubric_id,
                    "criterion_id": criterion.id,
                    "field": "description"
                }
            )
            chunks.extend(desc_chunks)

        # Chunk performance levels
        for level in criterion.levels.all():
            level_chunks = self._process_level(level, rubric_id, criterion.id)
            chunks.extend(level_chunks)

        return chunks

    def _process_level(self, level, rubric_id: int, criterion_id: int) -> List[TextChunk]:
        """
        Process a single performance level into chunks.

        Args:
            level: RubricLevel model instance
            rubric_id: Parent rubric ID
            criterion_id: Parent criterion ID

        Returns:
            List of TextChunk objects
        """
        chunks = []

        # Chunk level name and description
        if level.name:
            name_chunks = self.chunking_strategy.chunk_text(
                level.name,
                source_type="level",
                source_id=level.id,
                metadata={
                    "rubric_id": rubric_id,
                    "criterion_id": criterion_id,
                    "level_id": level.id,
                    "field": "name",
                    "score": level.score
                }
            )
            chunks.extend(name_chunks)

        if level.description:
            desc_chunks = self.chunking_strategy.chunk_text(
                level.description,
                source_type="level",
                source_id=level.id,
                metadata={
                    "rubric_id": rubric_id,
                    "criterion_id": criterion_id,
                    "level_id": level.id,
                    "field": "description",
                    "score": level.score
                }
            )
            chunks.extend(desc_chunks)

        return chunks

    def update_index_for_rubric(self, rubric_id: int) -> Dict[str, Any]:
        """
        Update index for a specific rubric.

        Args:
            rubric_id: ID of rubric to update

        Returns:
            Dictionary with update statistics
        """
        if not self._initialized:
            self.initialize()

        try:
            from .models import Rubric

            # Get rubric
            rubric = Rubric.objects.get(id=rubric_id)

            logger.info(f"Updating index for rubric {rubric_id}")

            # Process rubric
            chunks = self._process_rubric(rubric)

            if not chunks:
                logger.warning(f"No chunks generated for rubric {rubric_id}")
                return {
                    "success": True,
                    "rubric_id": rubric_id,
                    "chunks_indexed": 0,
                    "message": "No chunks generated"
                }

            # Generate embeddings
            texts = [chunk.text for chunk in chunks]
            embeddings = self.embedding_service.generate_embeddings(texts)

            # Prepare metadata
            metadata_list = []
            for chunk in chunks:
                metadata = {
                    'chunk_id': chunk.chunk_id,
                    'text': chunk.text,
                    'source_type': chunk.source_type,
                    'source_id': chunk.source_id,
                    **chunk.metadata
                }
                metadata_list.append(metadata)

            # Add vectors to index
            self.vector_store.add_vectors(embeddings, metadata_list)

            # Save index
            self.vector_store.save()

            stats = {
                "success": True,
                "rubric_id": rubric_id,
                "chunks_indexed": len(chunks),
                "index_stats": self.vector_store.get_stats()
            }

            logger.info(f"Index updated for rubric {rubric_id}: {stats}")
            return stats

        except Rubric.DoesNotExist:
            raise VectorIndexerError(f"Rubric {rubric_id} not found")
        except Exception as e:
            logger.error(f"Failed to update index for rubric {rubric_id}: {str(e)}")
            raise VectorIndexerError(f"Index update failed: {str(e)}")

    def rebuild_index(self) -> Dict[str, Any]:
        """
        Rebuild the entire index from scratch.

        Returns:
            Dictionary with rebuild statistics
        """
        logger.info("Rebuilding entire index")
        return self.build_index_from_database(clear_existing=True)

    def get_index_status(self) -> Dict[str, Any]:
        """
        Get current index status.

        Returns:
            Dictionary with index status information
        """
        if not self._initialized:
            self.initialize()

        vector_store_stats = self.vector_store.get_stats()
        embedding_cache_stats = self.embedding_service.get_cache_stats()

        # Get database statistics
        from .models import Rubric, RubricCriterion, RubricLevel

        db_stats = {
            "total_rubrics": Rubric.objects.count(),
            "total_criteria": RubricCriterion.objects.count(),
            "total_levels": RubricLevel.objects.count()
        }

        return {
            "vector_store": vector_store_stats,
            "embedding_cache": embedding_cache_stats,
            "database": db_stats,
            "config": {
                "index_type": self.config.index_type,
                "model_name": self.config.model_name,
                "chunk_size": self.config.chunk_size,
                "top_k": self.config.top_k
            }
        }


# Global vector indexer instance
_vector_indexer: VectorIndexer = None


def get_vector_indexer() -> VectorIndexer:
    """Get global vector indexer instance."""
    global _vector_indexer
    if _vector_indexer is None:
        _vector_indexer = VectorIndexer()
    return _vector_indexer


def reset_vector_indexer() -> None:
    """Reset global vector indexer instance."""
    global _vector_indexer
    _vector_indexer = None