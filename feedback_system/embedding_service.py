"""
Embedding service for generating vector embeddings using sentence-transformers.

This module provides functionality to:
- Generate embeddings for text using sentence-transformers
- Batch process multiple texts efficiently
- Cache embeddings to avoid recomputation
- Support different embedding models
"""

import os
import logging
import hashlib
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from .vector_config import get_config

logger = logging.getLogger(__name__)

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
except ImportError:
    SentenceTransformer = None
    np = None


@dataclass
class EmbeddingResult:
    """Result of embedding generation."""
    embeddings: List[List[float]]
    model_name: str
    dimension: int
    processing_time: float


class EmbeddingServiceError(Exception):
    """Custom exception for embedding service errors."""
    pass


class EmbeddingService:
    """
    Service for generating text embeddings using sentence-transformers.

    Supports caching, batch processing, and multiple models.
    """

    def __init__(self, model_name: Optional[str] = None, config=None):
        """
        Initialize embedding service.

        Args:
            model_name: Name of the sentence-transformers model
            config: VectorConfig instance (uses default if not provided)
        """
        if SentenceTransformer is None:
            raise EmbeddingServiceError(
                "sentence-transformers library is not installed. "
                "Please install it using: pip install sentence-transformers"
            )

        if np is None:
            raise EmbeddingServiceError(
                "numpy library is not installed. "
                "Please install it using: pip install numpy"
            )

        self.config = config or get_config()
        self.model_name = model_name or self.config.model_name
        self.model = None
        self._cache: Dict[str, List[float]] = {}

        # Load model
        self._load_model()

    def _load_model(self) -> None:
        """Load the sentence-transformers model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(
                self.model_name,
                device=self.config.device
            )
            logger.info(f"Model loaded successfully. Dimension: {self.model.get_sentence_embedding_dimension()}")
        except Exception as e:
            raise EmbeddingServiceError(f"Failed to load model {self.model_name}: {str(e)}")

    def generate_embedding(
        self,
        text: str,
        normalize: Optional[bool] = None
    ) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed
            normalize: Whether to normalize embeddings (uses config default if not provided)

        Returns:
            Embedding vector as list of floats
        """
        if not text or not isinstance(text, str):
            raise ValueError("Text must be a non-empty string")

        # Check cache
        cache_key = self._get_cache_key(text)
        if cache_key in self._cache:
            logger.debug(f"Cache hit for text: {text[:50]}...")
            return self._cache[cache_key]

        # Generate embedding
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=normalize if normalize is not None else self.config.normalize_embeddings
            )

            # Convert to list
            embedding_list = embedding.tolist()

            # Cache result
            if self.config.enable_cache:
                self._cache[cache_key] = embedding_list

            return embedding_list

        except Exception as e:
            raise EmbeddingServiceError(f"Failed to generate embedding: {str(e)}")

    def generate_embeddings(
        self,
        texts: List[str],
        normalize: Optional[bool] = None,
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed
            normalize: Whether to normalize embeddings
            batch_size: Batch size for processing (uses config default if not provided)

        Returns:
            List of embedding vectors
        """
        if not texts:
            return []

        if not isinstance(texts, list):
            raise ValueError("texts must be a list")

        # Validate all texts
        for i, text in enumerate(texts):
            if not text or not isinstance(text, str):
                raise ValueError(f"Text at index {i} must be a non-empty string")

        # Check cache for each text
        uncached_texts = []
        uncached_indices = []
        embeddings = [None] * len(texts)

        for i, text in enumerate(texts):
            cache_key = self._get_cache_key(text)
            if cache_key in self._cache:
                embeddings[i] = self._cache[cache_key]
            else:
                uncached_texts.append(text)
                uncached_indices.append(i)

        # Generate embeddings for uncached texts
        if uncached_texts:
            try:
                batch_embeddings = self.model.encode(
                    uncached_texts,
                    batch_size=batch_size or self.config.batch_size,
                    convert_to_numpy=True,
                    normalize_embeddings=normalize if normalize is not None else self.config.normalize_embeddings,
                    show_progress_bar=False
                )

                # Assign embeddings to correct positions
                for idx, embedding in zip(uncached_indices, batch_embeddings):
                    embedding_list = embedding.tolist()
                    embeddings[idx] = embedding_list

                    # Cache result
                    if self.config.enable_cache:
                        cache_key = self._get_cache_key(texts[idx])
                        self._cache[cache_key] = embedding_list

            except Exception as e:
                raise EmbeddingServiceError(f"Failed to generate batch embeddings: {str(e)}")

        return embeddings

    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model."""
        return self.model.get_sentence_embedding_dimension()

    def _get_cache_key(self, text: str) -> str:
        """Generate cache key for text."""
        # Use hash of text + model name
        content = f"{self.model_name}:{text}"
        return hashlib.md5(content.encode()).hexdigest()

    def clear_cache(self) -> None:
        """Clear the embedding cache."""
        self._cache.clear()
        logger.info("Embedding cache cleared")

    def save_cache(self, cache_path: Optional[Path] = None) -> None:
        """
        Save cache to disk.

        Args:
            cache_path: Path to save cache (uses config default if not provided)
        """
        if not self.config.enable_cache:
            logger.warning("Caching is disabled, cannot save cache")
            return

        cache_path = cache_path or self.config.cache_dir / "embedding_cache.json"

        try:
            with open(cache_path, 'w') as f:
                json.dump(self._cache, f)
            logger.info(f"Cache saved to {cache_path}")
        except Exception as e:
            logger.error(f"Failed to save cache: {str(e)}")

    def load_cache(self, cache_path: Optional[Path] = None) -> None:
        """
        Load cache from disk.

        Args:
            cache_path: Path to load cache from (uses config default if not provided)
        """
        if not self.config.enable_cache:
            logger.warning("Caching is disabled, cannot load cache")
            return

        cache_path = cache_path or self.config.cache_dir / "embedding_cache.json"

        if not cache_path.exists():
            logger.info(f"Cache file not found: {cache_path}")
            return

        try:
            with open(cache_path, 'r') as f:
                self._cache = json.load(f)
            logger.info(f"Cache loaded from {cache_path} ({len(self._cache)} entries)")
        except Exception as e:
            logger.error(f"Failed to load cache: {str(e)}")

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "enabled": self.config.enable_cache,
            "entries": len(self._cache),
            "model_name": self.model_name,
            "dimension": self.get_embedding_dimension()
        }


# Global embedding service instance
_embedding_service: EmbeddingService = None


def get_embedding_service() -> EmbeddingService:
    """Get global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def reset_embedding_service() -> None:
    """Reset global embedding service instance."""
    global _embedding_service
    _embedding_service = None