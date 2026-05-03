"""
Configuration module for vector RAG system using FAISS.

This module provides centralized configuration for:
- FAISS index settings
- Embedding model configuration
- Chunking strategies
- Storage paths and file management
"""

import os
from pathlib import Path
from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class VectorConfig:
    """Configuration for vector RAG system."""

    # FAISS Index Configuration
    index_type: str = "IndexFlatL2"  # Options: IndexFlatL2, IndexIVFFlat, IndexHNSW
    embedding_dimension: int = 384  # all-MiniLM-L6-v2 produces 384-dimensional embeddings
    metric_type: str = "L2"  # Options: L2, IP (Inner Product), COSINE

    # IVF Index Configuration (for IndexIVFFlat)
    nlist: int = 100  # Number of clusters for IVF index
    nprobe: int = 10  # Number of clusters to search

    # HNSW Index Configuration (for IndexHNSW)
    M: int = 16  # Number of connections per node
    efConstruction: int = 64  # Size of dynamic candidate list during construction
    efSearch: int = 32  # Size of dynamic candidate list during search

    # Embedding Model Configuration
    model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    device: str = "cpu"  # Options: cpu, cuda
    batch_size: int = 32
    normalize_embeddings: bool = True

    # Chunking Configuration
    chunk_size: int = 200  # Maximum characters per chunk
    chunk_overlap: int = 50  # Overlap between chunks
    min_chunk_size: int = 50  # Minimum chunk size to keep

    # Retrieval Configuration
    top_k: int = 5  # Number of results to retrieve
    similarity_threshold: float = 0.7  # Minimum similarity score

    # Storage Configuration
    index_dir: Path = field(default_factory=lambda: Path("vector_index"))
    index_file: str = "rubric_index.faiss"
    metadata_file: str = "rubric_metadata.json"

    # Caching Configuration
    enable_cache: bool = True
    cache_dir: Path = field(default_factory=lambda: Path("vector_cache"))

    # Performance Configuration
    max_concurrent_requests: int = 10
    timeout: int = 30  # seconds

    def __post_init__(self):
        """Initialize paths and validate configuration."""
        # Ensure paths are Path objects
        if isinstance(self.index_dir, str):
            self.index_dir = Path(self.index_dir)
        if isinstance(self.cache_dir, str):
            self.cache_dir = Path(self.cache_dir)

        # Create directories if they don't exist
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Validate configuration
        self._validate_config()

    def _validate_config(self) -> None:
        """Validate configuration settings."""
        valid_index_types = ["IndexFlatL2", "IndexIVFFlat", "IndexHNSW"]
        if self.index_type not in valid_index_types:
            raise ValueError(
                f"Invalid index_type: {self.index_type}. "
                f"Must be one of: {', '.join(valid_index_types)}"
            )

        valid_metrics = ["L2", "IP", "COSINE"]
        if self.metric_type not in valid_metrics:
            raise ValueError(
                f"Invalid metric_type: {self.metric_type}. "
                f"Must be one of: {', '.join(valid_metrics)}"
            )

        if self.chunk_size <= 0:
            raise ValueError("chunk_size must be positive")

        if self.chunk_overlap < 0 or self.chunk_overlap >= self.chunk_size:
            raise ValueError("chunk_overlap must be non-negative and less than chunk_size")

        if self.top_k <= 0:
            raise ValueError("top_k must be positive")

        if not 0 <= self.similarity_threshold <= 1:
            raise ValueError("similarity_threshold must be between 0 and 1")

    def get_index_path(self) -> Path:
        """Get full path to FAISS index file."""
        return self.index_dir / self.index_file

    def get_metadata_path(self) -> Path:
        """Get full path to metadata file."""
        return self.index_dir / self.metadata_file

    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary."""
        return {
            "index_type": self.index_type,
            "embedding_dimension": self.embedding_dimension,
            "metric_type": self.metric_type,
            "nlist": self.nlist,
            "nprobe": self.nprobe,
            "M": self.M,
            "efConstruction": self.efConstruction,
            "efSearch": self.efSearch,
            "model_name": self.model_name,
            "device": self.device,
            "batch_size": self.batch_size,
            "normalize_embeddings": self.normalize_embeddings,
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.chunk_overlap,
            "min_chunk_size": self.min_chunk_size,
            "top_k": self.top_k,
            "similarity_threshold": self.similarity_threshold,
            "index_dir": str(self.index_dir),
            "index_file": self.index_file,
            "metadata_file": self.metadata_file,
            "enable_cache": self.enable_cache,
            "cache_dir": str(self.cache_dir),
            "max_concurrent_requests": self.max_concurrent_requests,
            "timeout": self.timeout,
        }

    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "VectorConfig":
        """Create configuration from dictionary."""
        # Convert string paths back to Path objects
        if "index_dir" in config_dict and isinstance(config_dict["index_dir"], str):
            config_dict["index_dir"] = Path(config_dict["index_dir"])
        if "cache_dir" in config_dict and isinstance(config_dict["cache_dir"], str):
            config_dict["cache_dir"] = Path(config_dict["cache_dir"])

        return cls(**config_dict)


# Global configuration instance
_config: VectorConfig = None


def get_config() -> VectorConfig:
    """Get global configuration instance."""
    global _config
    if _config is None:
        _config = VectorConfig()
    return _config


def set_config(config: VectorConfig) -> None:
    """Set global configuration instance."""
    global _config
    _config = config


def reset_config() -> None:
    """Reset configuration to default."""
    global _config
    _config = None


# Environment variable overrides
def load_config_from_env() -> VectorConfig:
    """Load configuration with environment variable overrides."""
    config = VectorConfig()

    # Override with environment variables if present
    if os.getenv("VECTOR_INDEX_TYPE"):
        config.index_type = os.getenv("VECTOR_INDEX_TYPE")

    if os.getenv("VECTOR_MODEL_NAME"):
        config.model_name = os.getenv("VECTOR_MODEL_NAME")

    if os.getenv("VECTOR_DEVICE"):
        config.device = os.getenv("VECTOR_DEVICE")

    if os.getenv("VECTOR_TOP_K"):
        config.top_k = int(os.getenv("VECTOR_TOP_K"))

    if os.getenv("VECTOR_SIMILARITY_THRESHOLD"):
        config.similarity_threshold = float(os.getenv("VECTOR_SIMILARITY_THRESHOLD"))

    if os.getenv("VECTOR_INDEX_DIR"):
        config.index_dir = Path(os.getenv("VECTOR_INDEX_DIR"))

    if os.getenv("VECTOR_CACHE_DIR"):
        config.cache_dir = Path(os.getenv("VECTOR_CACHE_DIR"))

    return config