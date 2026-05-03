"""
Text preprocessing module for cleaning and structuring extracted text.

This module provides functionality to:
- Split text into paragraphs
- Clean unnecessary whitespace
- Return structured paragraph lists
"""

import re
import logging
from typing import List

logger = logging.getLogger(__name__)


class TextPreprocessor:
    """
    Text preprocessor for cleaning and structuring extracted text.

    Focuses on simple, reliable text processing without AI or NLP.
    """

    @staticmethod
    def preprocess_text(text: str) -> List[str]:
        """
        Preprocess text by splitting into clean paragraphs.

        Args:
            text: Raw extracted text

        Returns:
            List of clean, non-empty paragraphs
        """
        if not text or not isinstance(text, str):
            return []

        # Clean the text first
        cleaned_text = TextPreprocessor._clean_text(text)

        # Split into paragraphs
        paragraphs = TextPreprocessor._split_into_paragraphs(cleaned_text)

        # Filter out empty paragraphs
        filtered_paragraphs = [p for p in paragraphs if p.strip()]

        logger.info(f"Preprocessed text: {len(filtered_paragraphs)} paragraphs")

        return filtered_paragraphs

    @staticmethod
    def _clean_text(text: str) -> str:
        """
        Clean text by normalizing whitespace and removing artifacts.

        Args:
            text: Raw text to clean

        Returns:
            Cleaned text
        """
        # Normalize line endings to \n
        text = text.replace('\r\n', '\n').replace('\r', '\n')

        # Remove excessive whitespace between words
        text = re.sub(r'[ \t]+', ' ', text)

        # Remove multiple consecutive newlines (more than 2)
        text = re.sub(r'\n{3,}', '\n\n', text)

        # Remove leading/trailing whitespace from entire text
        text = text.strip()

        return text

    @staticmethod
    def _split_into_paragraphs(text: str) -> List[str]:
        """
        Split text into paragraphs based on double newlines.

        Args:
            text: Cleaned text

        Returns:
            List of paragraph strings
        """
        # Split by double newlines (paragraph separator)
        paragraphs = text.split('\n\n')

        # Clean each paragraph
        cleaned_paragraphs = []
        for paragraph in paragraphs:
            # Remove leading/trailing whitespace
            cleaned = paragraph.strip()

            # Remove single newlines within paragraphs (join lines)
            cleaned = ' '.join(cleaned.split())

            if cleaned:  # Only add non-empty paragraphs
                cleaned_paragraphs.append(cleaned)

        return cleaned_paragraphs

    @staticmethod
    def get_paragraph_stats(paragraphs: List[str]) -> dict:
        """
        Get statistics about preprocessed paragraphs.

        Args:
            paragraphs: List of paragraphs

        Returns:
            Dictionary with paragraph statistics
        """
        if not paragraphs:
            return {
                'total_paragraphs': 0,
                'total_characters': 0,
                'total_words': 0,
                'avg_paragraph_length': 0,
                'min_paragraph_length': 0,
                'max_paragraph_length': 0
            }

        total_chars = sum(len(p) for p in paragraphs)
        total_words = sum(len(p.split()) for p in paragraphs)
        paragraph_lengths = [len(p) for p in paragraphs]

        return {
            'total_paragraphs': len(paragraphs),
            'total_characters': total_chars,
            'total_words': total_words,
            'avg_paragraph_length': sum(paragraph_lengths) / len(paragraphs),
            'min_paragraph_length': min(paragraph_lengths),
            'max_paragraph_length': max(paragraph_lengths)
        }

    @staticmethod
    def merge_paragraphs(paragraphs: List[str], separator: str = '\n\n') -> str:
        """
        Merge paragraphs back into a single text string.

        Args:
            paragraphs: List of paragraphs to merge
            separator: String to use between paragraphs

        Returns:
            Merged text string
        """
        return separator.join(paragraphs)