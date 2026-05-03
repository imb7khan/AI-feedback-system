"""
Vector store implementation using FAISS for efficient similarity search.

This module provides functionality to:
- Store and search vector embeddings using FAISS
- Support different FAISS index types (Flat, IVF, HNSW)
- Manage metadata associated with vectors
- Handle index persistence and loading
"""

import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

from .vector_config import get_config

logger = logging.getLogger(__name__)

try:
    import faiss
    import numpy as np
except ImportError:
    faiss = None
    np = None


@dataclass
class SearchResult:
    """Result of a vector search."""
    chunk_id: str
    text: str
    score: float
    metadata: Dict[str, Any]
    distance: float


class VectorStoreError(Exception):
    """Custom exception for vector store errors."""
    pass


class VectorStore:
    """
    FAISS-based vector store for efficient similarity search.

    Supports multiple index types and metadata management.
    """

    def __init__(self, config=None):
        """
        Initialize vector store.

        Args:
            config: VectorConfig instance (uses default if not provided)
        """
        if faiss is None:
            raise VectorStoreError(
                "FAISS library is not installed. "
                "Please install it using: pip install faiss-cpu"
            )

        if np is None:
            raise VectorStoreError(
                "numpy library is not installed. "
                "Please install it using: pip install numpy"
            )

        self.config = config or get_config()
        self.index = None
        self.metadata: List[Dict[str, Any]] = []
        self.dimension = self.config.embedding_dimension
        self._initialized = False

    def initialize_index(self) -> None:
        """Initialize FAISS index based on configuration."""
        try:
            index_type = self.config.index_type

            if index_type == "IndexFlatL2":
                # Basic L2 distance index
                self.index = faiss.IndexFlatL2(self.dimension)
                logger.info(f"Initialized IndexFlatL2 with dimension {self.dimension}")

            elif index_type == "IndexIVFFlat":
                # IVF index for faster search on large datasets
                quantizer = faiss.IndexFlatL2(self.dimension)
                self.index = faiss.IndexIVFFlat(
                    quantizer,
                    self.dimension,
                    self.config.nlist,
                    faiss.METRIC_L2
                )
                logger.info(
                    f"Initialized IndexIVFFlat with dimension {self.dimension}, "
                    f"nlist={self.config.nlist}"
                )

            elif index_type == "IndexHNSW":
                # HNSW index for approximate nearest neighbor search
                self.index = faiss.IndexHNSW(self.dimension, self.config.M)
                self.index.hnsw.efConstruction = self.config.efConstruction
                logger.info(
                    f"Initialized IndexHNSW with dimension {self.dimension}, "
                    f"M={self.config.M}, efConstruction={self.config.efConstruction}"
                )

            else:
                raise VectorStoreError(f"Unsupported index type: {index_type}")

            self._initialized = True

        except Exception as e:
            raise VectorStoreError(f"Failed to initialize index: {str(e)}")

    def add_vectors(
        self,
        embeddings: List[List[float]],
        metadata_list: List[Dict[str, Any]]
    ) -> None:
        """
        Add vectors to the index.

        Args:
            embeddings: List of embedding vectors
            metadata_list: List of metadata dictionaries for each vector
        """
        if not self._initialized:
            self.initialize_index()

        if len(embeddings) != len(metadata_list):
            raise ValueError("Number of embeddings must match number of metadata entries")

        if not embeddings:
            logger.warning("No embeddings to add")
            return

        try:
            # Convert to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)

            # Add to index
            self.index.add(embeddings_array)

            # Store metadata
            self.metadata.extend(metadata_list)

            logger.info(f"Added {len(embeddings)} vectors to index. Total: {self.index.ntotal}")

        except Exception as e:
            raise VectorStoreError(f"Failed to add vectors: {str(e)}")

    def search(
        self,
        query_embedding: List[float],
        k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
        """
        Search for similar vectors.

        Args:
            query_embedding: Query embedding vector
            k: Number of results to return (uses config default if not provided)
            filter_metadata: Optional metadata filter

        Returns:
            List of SearchResult objects
        """
        if not self._initialized:
            raise VectorStoreError("Index not initialized")

        if self.index.ntotal == 0:
            logger.warning("Index is empty, no results to return")
            return []

        k = k or self.config.top_k

        try:
            # Convert query to numpy array
            query_array = np.array([query_embedding], dtype=np.float32)

            # Set search parameters for IVF index
            if isinstance(self.index, faiss.IndexIVFFlat):
                if not self.index.is_trained:
                    raise VectorStoreError("IVF index not trained. Call train() first.")
                self.index.nprobe = self.config.nprobe

            # Set search parameters for HNSW index
            if isinstance(self.index, faiss.IndexHNSW):
                self.index.hnsw.efSearch = self.config.efSearch

            # Search
            distances, indices = self.index.search(query_array, k)

            # Convert to results
            results = []
            for dist, idx in zip(distances[0], indices[0]):
                if idx >= 0 and idx < len(self.metadata):
                    metadata = self.metadata[idx]

                    # Apply metadata filter if provided
                    if filter_metadata and not self._matches_filter(metadata, filter_metadata):
                        continue

                    # Calculate similarity score (convert distance to similarity)
                    similarity = self._distance_to_similarity(dist)

                    # Apply similarity threshold
                    if similarity < self.config.similarity_threshold:
                        continue

                    result = SearchResult(
                        chunk_id=metadata.get('chunk_id', ''),
                        text=metadata.get('text', ''),
                        score=similarity,
                        metadata=metadata,
                        distance=float(dist)
                    )
                    results.append(result)

            logger.debug(f"Search returned {len(results)} results")
            return results

        except Exception as e:
            raise VectorStoreError(f"Search failed: {str(e)}")

    def train(self, embeddings: List[List[float]]) -> None:
        """
        Train IVF index (required for IndexIVFFlat).

        Args:
            embeddings: Training embeddings
        """
        if not isinstance(self.index, faiss.IndexIVFFlat):
            logger.warning("Training only required for IVF index")
            return

        if self.index.is_trained:
            logger.info("IVF index already trained")
            return

        try:
            embeddings_array = np.array(embeddings, dtype=np.float32)
            self.index.train(embeddings_array)
            logger.info(f"IVF index trained with {len(embeddings)} vectors")
        except Exception as e:
            raise VectorStoreError(f"Failed to train index: {str(e)}")

    def save(self, index_path: Optional[Path] = None, metadata_path: Optional[Path] = None) -> None:
        """
        Save index and metadata to disk.

        Args:
            index_path: Path to save index (uses config default if not provided)
            metadata_path: Path to save metadata (uses config default if not provided)
        """
        if not self._initialized:
            raise VectorStoreError("Index not initialized")

        index_path = index_path or self.config.get_index_path()
        metadata_path = metadata_path or self.config.get_metadata_path()

        try:
            # Save index
            faiss.write_index(self.index, str(index_path))
            logger.info(f"Index saved to {index_path}")

            # Save metadata
            with open(metadata_path, 'w') as f:
                json.dump(self.metadata, f, indent=2)
            logger.info(f"Metadata saved to {metadata_path}")

        except Exception as e:
            raise VectorStoreError(f"Failed to save index: {str(e)}")

    def load(self, index_path: Optional[Path] = None, metadata_path: Optional[Path] = None) -> None:
        """
        Load index and metadata from disk.

        Args:
            index_path: Path to load index from (uses config default if not provided)
            metadata_path: Path to load metadata from (uses config default if not provided)
        """
        index_path = index_path or self.config.get_index_path()
        metadata_path = metadata_path or self.config.get_metadata_path()

        if not index_path.exists():
            raise VectorStoreError(f"Index file not found: {index_path}")

        if not metadata_path.exists():
            raise VectorStoreError(f"Metadata file not found: {metadata_path}")

        try:
            # Load index
            self.index = faiss.read_index(str(index_path))
            logger.info(f"Index loaded from {index_path}")

            # Load metadata
            with open(metadata_path, 'r') as f:
                self.metadata = json.load(f)
            logger.info(f"Metadata loaded from {metadata_path} ({len(self.metadata)} entries)")

            self._initialized = True

        except Exception as e:
            raise VectorStoreError(f"Failed to load index: {str(e)}")

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the vector store."""
        if not self._initialized:
            return {
                "initialized": False,
                "total_vectors": 0,
                "dimension": self.dimension,
                "index_type": self.config.index_type
            }

        return {
            "initialized": True,
            "total_vectors": self.index.ntotal,
            "dimension": self.dimension,
            "index_type": self.config.index_type,
            "is_trained": self.index.is_trained if hasattr(self.index, 'is_trained') else None,
            "metadata_count": len(self.metadata)
        }

    def _distance_to_similarity(self, distance: float) -> float:
        """Convert distance to similarity score."""
        # For L2 distance, convert to similarity using exponential decay
        # This gives a score between 0 and 1
        return np.exp(-distance)

    def _matches_filter(self, metadata: Dict[str, Any], filter_dict: Dict[str, Any]) -> bool:
        """Check if metadata matches filter criteria."""
        for key, value in filter_dict.items():
            if key not in metadata:
                return False
            if metadata[key] != value:
                return False
        return True

    def clear(self) -> None:
        """Clear the index and metadata."""
        if self._initialized:
            self.index.reset()
        self.metadata = []
        logger.info("Vector store cleared")


# Global vector store instance
_vector_store: VectorStore = None


def get_vector_store() -> VectorStore:
    """Get global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def reset_vector_store() -> None:
    """Reset global vector store instance."""
    global _vector_store
    _vector_store = None