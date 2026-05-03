"""
Chunking strategy for breaking down rubric content into manageable pieces.

This module provides functionality to:
- Split text into chunks with configurable size and overlap
- Preserve context and meaning across chunk boundaries
- Handle different types of content (rubrics, criteria, descriptions)
- Support multiple chunking strategies
"""

import re
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .vector_config import get_config

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    """Represents a chunk of text with metadata."""
    text: str
    chunk_id: str
    source_type: str  # 'rubric', 'criterion', 'level', 'description'
    source_id: Optional[int] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ChunkingStrategy:
    """
    Strategy for chunking text into smaller, manageable pieces.

    Supports different chunking methods and preserves context.
    """

    def __init__(self, config=None):
        """
        Initialize chunking strategy.

        Args:
            config: VectorConfig instance (uses default if not provided)
        """
        self.config = config or get_config()
        self.chunk_size = self.config.chunk_size
        self.chunk_overlap = self.config.chunk_overlap
        self.min_chunk_size = self.config.min_chunk_size

    def chunk_text(
        self,
        text: str,
        source_type: str = "general",
        source_id: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[TextChunk]:
        """
        Split text into chunks with overlap.

        Args:
            text: Text to chunk
            source_type: Type of content (rubric, criterion, level, description)
            source_id: ID of the source item
            metadata: Additional metadata to include

        Returns:
            List of TextChunk objects
        """
        if not text or not isinstance(text, str):
            return []

        # Clean and normalize text
        text = self._clean_text(text)

        # If text is short enough, return as single chunk
        if len(text) <= self.chunk_size:
            return [TextChunk(
                text=text,
                chunk_id=self._generate_chunk_id(source_type, source_id, 0),
                source_type=source_type,
                source_id=source_id,
                metadata=metadata or {}
            )]

        # Split into chunks with overlap
        chunks = self._split_with_overlap(text)

        # Create TextChunk objects
        text_chunks = []
        for i, chunk_text in enumerate(chunks):
            if len(chunk_text) >= self.min_chunk_size:
                chunk = TextChunk(
                    text=chunk_text,
                    chunk_id=self._generate_chunk_id(source_type, source_id, i),
                    source_type=source_type,
                    source_id=source_id,
                    metadata=metadata or {}
                )
                text_chunks.append(chunk)

        logger.debug(f"Chunked text into {len(text_chunks)} chunks")
        return text_chunks

    def chunk_rubric(
        self,
        rubric_data: Dict[str, Any]
    ) -> List[TextChunk]:
        """
        Chunk rubric data into searchable pieces.

        Args:
            rubric_data: Dictionary containing rubric information

        Returns:
            List of TextChunk objects
        """
        chunks = []

        # Chunk rubric title and description
        if rubric_data.get('title'):
            title_chunks = self.chunk_text(
                rubric_data['title'],
                source_type="rubric",
                source_id=rubric_data.get('id'),
                metadata={"rubric_id": rubric_data.get('id'), "field": "title"}
            )
            chunks.extend(title_chunks)

        if rubric_data.get('description'):
            desc_chunks = self.chunk_text(
                rubric_data['description'],
                source_type="rubric",
                source_id=rubric_data.get('id'),
                metadata={"rubric_id": rubric_data.get('id'), "field": "description"}
            )
            chunks.extend(desc_chunks)

        # Chunk criteria
        for criterion in rubric_data.get('criteria', []):
            criterion_chunks = self.chunk_criterion(criterion, rubric_data.get('id'))
            chunks.extend(criterion_chunks)

        return chunks

    def chunk_criterion(
        self,
        criterion: Dict[str, Any],
        rubric_id: Optional[int] = None
    ) -> List[TextChunk]:
        """
        Chunk a single criterion.

        Args:
            criterion: Criterion dictionary
            rubric_id: Parent rubric ID

        Returns:
            List of TextChunk objects
        """
        chunks = []
        criterion_id = criterion.get('id')

        # Chunk criterion name and description
        if criterion.get('name'):
            name_chunks = self.chunk_text(
                criterion['name'],
                source_type="criterion",
                source_id=criterion_id,
                metadata={
                    "rubric_id": rubric_id,
                    "criterion_id": criterion_id,
                    "field": "name"
                }
            )
            chunks.extend(name_chunks)

        if criterion.get('description'):
            desc_chunks = self.chunk_text(
                criterion['description'],
                source_type="criterion",
                source_id=criterion_id,
                metadata={
                    "rubric_id": rubric_id,
                    "criterion_id": criterion_id,
                    "field": "description"
                }
            )
            chunks.extend(desc_chunks)

        # Chunk performance levels
        for level in criterion.get('levels', []):
            level_chunks = self.chunk_level(level, rubric_id, criterion_id)
            chunks.extend(level_chunks)

        return chunks

    def chunk_level(
        self,
        level: Dict[str, Any],
        rubric_id: Optional[int] = None,
        criterion_id: Optional[int] = None
    ) -> List[TextChunk]:
        """
        Chunk a performance level.

        Args:
            level: Level dictionary
            rubric_id: Parent rubric ID
            criterion_id: Parent criterion ID

        Returns:
            List of TextChunk objects
        """
        chunks = []
        level_id = level.get('id')

        # Chunk level name and description
        if level.get('name'):
            name_chunks = self.chunk_text(
                level['name'],
                source_type="level",
                source_id=level_id,
                metadata={
                    "rubric_id": rubric_id,
                    "criterion_id": criterion_id,
                    "level_id": level_id,
                    "field": "name",
                    "score": level.get('score')
                }
            )
            chunks.extend(name_chunks)

        if level.get('description'):
            desc_chunks = self.chunk_text(
                level['description'],
                source_type="level",
                source_id=level_id,
                metadata={
                    "rubric_id": rubric_id,
                    "criterion_id": criterion_id,
                    "level_id": level_id,
                    "field": "description",
                    "score": level.get('score')
                }
            )
            chunks.extend(desc_chunks)

        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean and normalize text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove leading/trailing whitespace
        text = text.strip()
        return text

    def _split_with_overlap(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            # Calculate end position
            end = start + self.chunk_size

            # If this is the last chunk, take all remaining text
            if end >= text_length:
                chunks.append(text[start:])
                break

            # Try to find a good break point (sentence boundary)
            chunk_text = text[start:end]

            # Look for sentence endings in the last 20% of the chunk
            break_point = self._find_break_point(chunk_text)

            if break_point > 0:
                # Adjust end to break point
                end = start + break_point
                chunk_text = text[start:end]

            chunks.append(chunk_text)

            # Move start position with overlap
            start = end - self.chunk_overlap

        return chunks

    def _find_break_point(self, text: str) -> int:
        """Find a good break point in text (sentence boundary)."""
        # Look for sentence endings in the last 20% of the text
        search_start = int(len(text) * 0.8)
        search_text = text[search_start:]

        # Look for period, exclamation, or question mark followed by space
        for i, char in enumerate(search_text):
            if char in '.!?':
                # Check if next character is space or end of string
                if i + 1 >= len(search_text) or search_text[i + 1] == ' ':
                    return search_start + i + 1

        # If no sentence boundary found, look for word boundary
        for i in range(len(search_text) - 1, 0, -1):
            if search_text[i] == ' ':
                return search_start + i

        # If no good break point found, return 0 (use original chunk)
        return 0

    def _generate_chunk_id(
        self,
        source_type: str,
        source_id: Optional[int],
        chunk_index: int
    ) -> str:
        """Generate unique chunk ID."""
        parts = [source_type]
        if source_id is not None:
            parts.append(str(source_id))
        parts.append(str(chunk_index))
        return "_".join(parts)

    def get_chunk_stats(self, chunks: List[TextChunk]) -> Dict[str, Any]:
        """Get statistics about chunks."""
        if not chunks:
            return {
                "total_chunks": 0,
                "total_length": 0,
                "avg_length": 0,
                "min_length": 0,
                "max_length": 0,
                "by_source_type": {}
            }

        lengths = [len(chunk.text) for chunk in chunks]
        by_source_type = {}

        for chunk in chunks:
            if chunk.source_type not in by_source_type:
                by_source_type[chunk.source_type] = 0
            by_source_type[chunk.source_type] += 1

        return {
            "total_chunks": len(chunks),
            "total_length": sum(lengths),
            "avg_length": sum(lengths) / len(lengths),
            "min_length": min(lengths),
            "max_length": max(lengths),
            "by_source_type": by_source_type
        }


# Global chunking strategy instance
_chunking_strategy: ChunkingStrategy = None


def get_chunking_strategy() -> ChunkingStrategy:
    """Get global chunking strategy instance."""
    global _chunking_strategy
    if _chunking_strategy is None:
        _chunking_strategy = ChunkingStrategy()
    return _chunking_strategy


def reset_chunking_strategy() -> None:
    """Reset global chunking strategy instance."""
    global _chunking_strategy
    _chunking_strategy = None