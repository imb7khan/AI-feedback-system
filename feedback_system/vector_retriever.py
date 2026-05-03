"""
Vector retriever for semantic search with relevance scoring.

This module provides functionality to:
- Perform semantic search on indexed content
- Rank results by relevance
- Support different search strategies
- Filter and refine search results
"""

import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass

from .vector_store import VectorStore, SearchResult
from .embedding_service import EmbeddingService
from .vector_config import get_config

logger = logging.getLogger(__name__)


@dataclass
class RetrievalResult:
    """Enhanced result with additional metadata."""
    chunk_id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    distance: float
    rubric_id: Optional[int] = None
    criterion_id: Optional[int] = None
    level_id: Optional[int] = None
    source_type: str = ""


class VectorRetriever:
    """
    Retriever for semantic search with advanced filtering and ranking.

    Provides flexible search capabilities with relevance scoring.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        config=None
    ):
        """
        Initialize vector retriever.

        Args:
            vector_store: VectorStore instance (uses global if not provided)
            embedding_service: EmbeddingService instance (uses global if not provided)
            config: VectorConfig instance (uses default if not provided)
        """
        self.config = config or get_config()
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self._initialized = False

    def initialize(self) -> None:
        """Initialize retriever with required services."""
        if self.vector_store is None:
            from .vector_store import get_vector_store
            self.vector_store = get_vector_store()

        if self.embedding_service is None:
            from .embedding_service import get_embedding_service
            self.embedding_service = get_embedding_service()

        self._initialized = True
        logger.info("Vector retriever initialized")

    def retrieve(
        self,
        query: str,
        k: Optional[int] = None,
        filter_rubric_id: Optional[int] = None,
        filter_criterion_id: Optional[int] = None,
        filter_source_type: Optional[str] = None,
        min_score: Optional[float] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: Search query text
            k: Number of results to return
            filter_rubric_id: Filter by rubric ID
            filter_criterion_id: Filter by criterion ID
            filter_source_type: Filter by source type
            min_score: Minimum similarity score

        Returns:
            List of RetrievalResult objects
        """
        if not self._initialized:
            self.initialize()

        if not query or not isinstance(query, str):
            raise ValueError("Query must be a non-empty string")

        # Generate query embedding
        try:
            query_embedding = self.embedding_service.generate_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {str(e)}")
            raise

        # Build metadata filter
        filter_metadata = {}
        if filter_rubric_id is not None:
            filter_metadata['rubric_id'] = filter_rubric_id
        if filter_criterion_id is not None:
            filter_metadata['criterion_id'] = filter_criterion_id
        if filter_source_type is not None:
            filter_metadata['source_type'] = filter_source_type

        # Search vector store
        try:
            search_results = self.vector_store.search(
                query_embedding=query_embedding,
                k=k or self.config.top_k,
                filter_metadata=filter_metadata if filter_metadata else None
            )
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise

        # Convert to retrieval results and apply score filter
        retrieval_results = []
        min_score = min_score or self.config.similarity_threshold

        for result in search_results:
            if result.score >= min_score:
                retrieval_result = RetrievalResult(
                    chunk_id=result.chunk_id,
                    text=result.text,
                    score=result.score,
                    metadata=result.metadata,
                    distance=result.distance,
                    rubric_id=result.metadata.get('rubric_id'),
                    criterion_id=result.metadata.get('criterion_id'),
                    level_id=result.metadata.get('level_id'),
                    source_type=result.metadata.get('source_type', '')
                )
                retrieval_results.append(retrieval_result)

        logger.debug(f"Retrieved {len(retrieval_results)} results for query: {query[:50]}...")
        return retrieval_results

    def retrieve_by_rubric(
        self,
        query: str,
        rubric_id: int,
        k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve chunks for a specific rubric.

        Args:
            query: Search query text
            rubric_id: Rubric ID to filter by
            k: Number of results to return

        Returns:
            List of RetrievalResult objects
        """
        return self.retrieve(
            query=query,
            k=k,
            filter_rubric_id=rubric_id
        )

    def retrieve_by_criterion(
        self,
        query: str,
        criterion_id: int,
        k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve chunks for a specific criterion.

        Args:
            query: Search query text
            criterion_id: Criterion ID to filter by
            k: Number of results to return

        Returns:
            List of RetrievalResult objects
        """
        return self.retrieve(
            query=query,
            k=k,
            filter_criterion_id=criterion_id
        )

    def retrieve_by_type(
        self,
        query: str,
        source_type: str,
        k: Optional[int] = None
    ) -> List[RetrievalResult]:
        """
        Retrieve chunks by source type.

        Args:
            query: Search query text
            source_type: Source type to filter by
            k: Number of results to return

        Returns:
            List of RetrievalResult objects
        """
        return self.retrieve(
            query=query,
            k=k,
            filter_source_type=source_type
        )

    def retrieve_multiple(
        self,
        queries: List[str],
        k: Optional[int] = None,
        combine_strategy: str = "average"
    ) -> List[RetrievalResult]:
        """
        Retrieve results for multiple queries and combine them.

        Args:
            queries: List of query strings
            k: Number of results per query
            combine_strategy: Strategy for combining results ("average", "max", "union")

        Returns:
            List of combined RetrievalResult objects
        """
        if not queries:
            return []

        # Retrieve results for each query
        all_results = []
        for query in queries:
            results = self.retrieve(query, k=k)
            all_results.extend(results)

        if not all_results:
            return []

        # Combine results based on strategy
        if combine_strategy == "union":
            # Return all unique results
            seen = set()
            unique_results = []
            for result in all_results:
                if result.chunk_id not in seen:
                    seen.add(result.chunk_id)
                    unique_results.append(result)
            return unique_results

        elif combine_strategy == "average":
            # Average scores for duplicate chunks
            chunk_scores = {}
            chunk_data = {}

            for result in all_results:
                if result.chunk_id not in chunk_scores:
                    chunk_scores[result.chunk_id] = []
                    chunk_data[result.chunk_id] = result
                chunk_scores[result.chunk_id].append(result.score)

            # Calculate average scores
            combined_results = []
            for chunk_id, scores in chunk_scores.items():
                result = chunk_data[chunk_id]
                result.score = sum(scores) / len(scores)
                combined_results.append(result)

            # Sort by score
            combined_results.sort(key=lambda x: x.score, reverse=True)
            return combined_results

        elif combine_strategy == "max":
            # Keep maximum score for duplicate chunks
            chunk_max_scores = {}
            chunk_data = {}

            for result in all_results:
                if result.chunk_id not in chunk_max_scores or result.score > chunk_max_scores[result.chunk_id]:
                    chunk_max_scores[result.chunk_id] = result.score
                    chunk_data[result.chunk_id] = result

            combined_results = list(chunk_data.values())
            combined_results.sort(key=lambda x: x.score, reverse=True)
            return combined_results

        else:
            raise ValueError(f"Unknown combine strategy: {combine_strategy}")

    def format_results_for_prompt(
        self,
        results: List[RetrievalResult],
        max_results: Optional[int] = None,
        include_metadata: bool = False
    ) -> str:
        """
        Format retrieval results for LLM prompt.

        Args:
            results: List of RetrievalResult objects
            max_results: Maximum number of results to include
            include_metadata: Whether to include metadata in output

        Returns:
            Formatted string for prompt
        """
        if not results:
            return "No relevant rubric information found."

        max_results = max_results or len(results)
        results = results[:max_results]

        formatted_lines = ["Relevant Rubric Information:"]
        formatted_lines.append("")

        for i, result in enumerate(results, 1):
            formatted_lines.append(f"{i}. {result.text}")

            if include_metadata:
                metadata_parts = []
                if result.rubric_id:
                    metadata_parts.append(f"Rubric ID: {result.rubric_id}")
                if result.criterion_id:
                    metadata_parts.append(f"Criterion ID: {result.criterion_id}")
                if result.level_id:
                    metadata_parts.append(f"Level ID: {result.level_id}")
                if result.source_type:
                    metadata_parts.append(f"Type: {result.source_type}")

                if metadata_parts:
                    formatted_lines.append(f"   ({', '.join(metadata_parts)})")

            formatted_lines.append(f"   Relevance: {result.score:.2f}")
            formatted_lines.append("")

        return "\n".join(formatted_lines)

    def get_retrieval_stats(self) -> Dict[str, Any]:
        """Get statistics about the retriever."""
        vector_store_stats = self.vector_store.get_stats() if self.vector_store else {}
        embedding_service_stats = self.embedding_service.get_cache_stats() if self.embedding_service else {}

        return {
            "initialized": self._initialized,
            "vector_store": vector_store_stats,
            "embedding_service": embedding_service_stats,
            "config": {
                "top_k": self.config.top_k,
                "similarity_threshold": self.config.similarity_threshold
            }
        }


# Global vector retriever instance
_vector_retriever: VectorRetriever = None


def get_vector_retriever() -> VectorRetriever:
    """Get global vector retriever instance."""
    global _vector_retriever
    if _vector_retriever is None:
        _vector_retriever = VectorRetriever()
    return _vector_retriever


def reset_vector_retriever() -> None:
    """Reset global vector retriever instance."""
    global _vector_retriever
    _vector_retriever = None