"""
LangChain configuration for feedback generation system.

This module provides configuration settings for LangChain components
while maintaining compatibility with existing system behavior.
"""

import os
from typing import Optional
from dataclasses import dataclass

@dataclass
class LangChainConfig:
    """Configuration for LangChain integration."""

    # Model configuration
    default_model: str = "llama-3.3-70b-versatile"
    temperature: float = 0.2
    max_tokens: int = 1000

    # RAG configuration
    use_vector_rag: bool = True
    similarity_threshold: float = 0.7
    top_k: int = 5

    # Graph configuration
    max_retries: int = 3
    timeout: int = 30

    # Feature flags
    enable_langchain: bool = True
    enable_langgraph: bool = True

    @classmethod
    def from_env(cls) -> 'LangChainConfig':
        """Create configuration from environment variables."""
        return cls(
            default_model=os.getenv('GROQ_MODEL', cls.default_model),
            temperature=float(os.getenv('LANGCHAIN_TEMPERATURE', cls.temperature)),
            max_tokens=int(os.getenv('LANGCHAIN_MAX_TOKENS', cls.max_tokens)),
            use_vector_rag=os.getenv('USE_VECTOR_RAG', 'true').lower() == 'true',
            similarity_threshold=float(os.getenv('SIMILARITY_THRESHOLD', cls.similarity_threshold)),
            top_k=int(os.getenv('TOP_K', cls.top_k)),
            enable_langchain=os.getenv('ENABLE_LANGCHAIN', 'true').lower() == 'true',
            enable_langgraph=os.getenv('ENABLE_LANGGRAPH', 'true').lower() == 'true',
        )

# Global configuration instance
_config: Optional[LangChainConfig] = None

def get_config() -> LangChainConfig:
    """Get global LangChain configuration instance."""
    global _config
    if _config is None:
        _config = LangChainConfig.from_env()
    return _config

def reset_config() -> None:
    """Reset global configuration instance."""
    global _config
    _config = None