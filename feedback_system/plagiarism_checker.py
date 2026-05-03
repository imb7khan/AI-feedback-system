"""
Minimal plagiarism-pattern detection module.

This module provides lightweight heuristic pattern-flagging for potential plagiarism.
This is NOT full internet plagiarism detection - it's local pattern analysis only.

Heuristics implemented:
- Repetition patterns (repeated long phrases, sentence templates)
- Citation/style anomalies (sudden citation style shifts)
- Writing-style inconsistency (abrupt shifts in sentence length/complexity)
- Suspicious patchwork pattern (high lexical overlap with weak transitions)
- Optional local corpus check (compare against stored submissions)
"""

import os
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class PlagiarismFlag:
    """Represents a plagiarism pattern flag."""
    type: str
    paragraph_indices: List[int]
    evidence: str
    confidence: float  # 0.0 to 1.0


@dataclass
class PlagiarismResult:
    """Result of plagiarism pattern analysis."""
    risk_level: str  # 'low', 'medium', 'high'
    flags: List[PlagiarismFlag]
    note: str


class PlagiarismChecker:
    """
    Minimal plagiarism-pattern detector using local heuristics.

    This checker analyzes text for patterns that MAY indicate plagiarism,
    but does not provide definitive proof. Results should be used as
    guidance for further review, not as conclusive evidence.
    """

    # Configuration defaults
    DEFAULT_CONFIG = {
        'repetition_phrase_length': 8,  # Minimum words for repeated phrase
        'repetition_threshold': 2,  # Minimum occurrences to flag
        'style_shift_threshold': 2.0,  # Standard deviations for style shift
        'lexical_overlap_threshold': 0.6,  # 60% overlap for patchwork
        'corpus_overlap_threshold': 0.7,  # 70% overlap for corpus check
        'min_paragraphs_for_analysis': 2,  # Need at least 2 paragraphs
    }

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize plagiarism checker.

        Args:
            config: Optional configuration overrides
        """
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self.enabled = os.getenv('ENABLE_PLAGIARISM_CHECK', 'true').lower() == 'true'

        if not self.enabled:
            logger.info("Plagiarism checker disabled via configuration")

    def check_text(
        self,
        full_text: str,
        paragraphs: List[str],
        corpus_texts: Optional[List[str]] = None
    ) -> PlagiarismResult:
        """
        Check text for plagiarism patterns.

        Args:
            full_text: Complete essay text
            paragraphs: List of preprocessed paragraphs
            corpus_texts: Optional list of prior submission texts for comparison

        Returns:
            PlagiarismResult with risk level and flags
        """
        if not self.enabled:
            return PlagiarismResult(
                risk_level='low',
                flags=[],
                note='Plagiarism checking disabled'
            )

        if len(paragraphs) < self.config['min_paragraphs_for_analysis']:
            return PlagiarismResult(
                risk_level='low',
                flags=[],
                note='Insufficient content for analysis'
            )

        flags = []

        # Run all heuristic checks
        flags.extend(self._check_repetition_patterns(paragraphs))
        flags.extend(self._check_citation_style_anomalies(paragraphs))
        flags.extend(self._check_writing_style_inconsistency(paragraphs))
        flags.extend(self._check_patchwork_pattern(paragraphs))

        # Optional corpus check
        if corpus_texts:
            flags.extend(self._check_corpus_overlap(full_text, corpus_texts))

        # Determine overall risk level
        risk_level = self._calculate_risk_level(flags)

        return PlagiarismResult(
            risk_level=risk_level,
            flags=flags,
            note='Heuristic pattern detection only, not definitive plagiarism proof'
        )

    def _check_repetition_patterns(self, paragraphs: List[str]) -> List[PlagiarismFlag]:
        """Check for unusually repeated long phrases across paragraphs."""
        flags = []
        phrase_length = self.config['repetition_phrase_length']
        threshold = self.config['repetition_threshold']

        # Extract phrases from all paragraphs
        all_phrases = []
        for para_idx, paragraph in enumerate(paragraphs):
            words = paragraph.split()
            for i in range(len(words) - phrase_length + 1):
                phrase = ' '.join(words[i:i + phrase_length]).lower()
                all_phrases.append((phrase, para_idx))

        # Count phrase occurrences
        phrase_counts = Counter(phrase for phrase, _ in all_phrases)

        # Find repeated phrases
        for phrase, count in phrase_counts.items():
            if count >= threshold:
                # Find which paragraphs contain this phrase
                paragraph_indices = sorted(set(
                    idx for phr, idx in all_phrases if phr == phrase
                ))

                if len(paragraph_indices) > 1:  # Must be in different paragraphs
                    confidence = min(0.9, 0.5 + (count - threshold) * 0.1)
                    flags.append(PlagiarismFlag(
                        type='repetition_pattern',
                        paragraph_indices=paragraph_indices,
                        evidence=f'Phrase "{phrase[:50]}..." repeated {count} times across paragraphs',
                        confidence=confidence
                    ))

        return flags

    def _check_citation_style_anomalies(self, paragraphs: List[str]) -> List[PlagiarismFlag]:
        """Check for sudden citation style shifts within the essay."""
        flags = []

        # Common citation patterns
        citation_patterns = {
            'APA': r'\(\w+, \d{4}\)',  # (Smith, 2020)
            'MLA': r'\(\w+ \d+\)',  # (Smith 123)
            'Chicago': r'\[\d+\]',  # [1]
            'Harvard': r'\(\w+, \d{4}, p\.\d+\)',  # (Smith, 2020, p.15)
        }

        # Detect citation styles in each paragraph
        paragraph_styles = []
        for para_idx, paragraph in enumerate(paragraphs):
            styles_found = []
            for style_name, pattern in citation_patterns.items():
                if re.search(pattern, paragraph):
                    styles_found.append(style_name)
            paragraph_styles.append((para_idx, styles_found))

        # Check for style shifts
        for i in range(len(paragraph_styles) - 1):
            current_idx, current_styles = paragraph_styles[i]
            next_idx, next_styles = paragraph_styles[i + 1]

            # If both have citations but different styles
            if current_styles and next_styles:
                if set(current_styles) != set(next_styles):
                    flags.append(PlagiarismFlag(
                        type='citation_style_shift',
                        paragraph_indices=[current_idx, next_idx],
                        evidence=f'Citation style changed from {current_styles} to {next_styles}',
                        confidence=0.7
                    ))

        return flags

    def _check_writing_style_inconsistency(self, paragraphs: List[str]) -> List[PlagiarismFlag]:
        """Check for abrupt shifts in sentence length/complexity between adjacent paragraphs."""
        flags = []

        # Calculate sentence complexity metrics for each paragraph
        paragraph_metrics = []
        for para_idx, paragraph in enumerate(paragraphs):
            sentences = re.split(r'[.!?]+', paragraph)
            sentences = [s.strip() for s in sentences if s.strip()]

            if not sentences:
                continue

            # Average sentence length (words)
            avg_length = sum(len(s.split()) for s in sentences) / len(sentences)

            # Average words per sentence (complexity)
            avg_words = sum(len(s.split()) for s in sentences) / len(sentences)

            paragraph_metrics.append({
                'index': para_idx,
                'avg_length': avg_length,
                'avg_words': avg_words
            })

        # Check for abrupt shifts between adjacent paragraphs
        threshold = self.config['style_shift_threshold']
        for i in range(len(paragraph_metrics) - 1):
            current = paragraph_metrics[i]
            next_para = paragraph_metrics[i + 1]

            # Calculate relative difference
            length_diff = abs(current['avg_length'] - next_para['avg_length'])
            words_diff = abs(current['avg_words'] - next_para['avg_words'])

            # Use average as baseline for relative comparison
            avg_baseline = (current['avg_length'] + next_para['avg_length']) / 2
            relative_diff = length_diff / avg_baseline if avg_baseline > 0 else 0

            if relative_diff > threshold:
                flags.append(PlagiarismFlag(
                    type='writing_style_shift',
                    paragraph_indices=[current['index'], next_para['index']],
                    evidence=f' abrupt shift in sentence complexity (diff: {relative_diff:.2f}x)',
                    confidence=min(0.8, 0.5 + relative_diff * 0.1)
                ))

        return flags

    def _check_patchwork_pattern(self, paragraphs: List[str]) -> List[PlagiarismFlag]:
        """Check for high lexical overlap between paragraphs with weak transitions."""
        flags = []
        threshold = self.config['lexical_overlap_threshold']

        # Calculate word overlap between adjacent paragraphs
        for i in range(len(paragraphs) - 1):
            current_words = set(paragraphs[i].lower().split())
            next_words = set(paragraphs[i + 1].lower().split())

            if not current_words or not next_words:
                continue

            # Calculate Jaccard similarity
            intersection = current_words & next_words
            union = current_words | next_words
            overlap = len(intersection) / len(union) if union else 0

            # Check for weak transitions (few transition words)
            transition_words = {'however', 'therefore', 'thus', 'consequently', 'furthermore',
                             'moreover', 'in addition', 'on the other hand', 'nevertheless',
                             'meanwhile', 'subsequently', 'finally', 'in conclusion'}

            has_transition = any(word in transition_words for word in
                              paragraphs[i + 1].lower().split())

            # High overlap but no transition words = suspicious
            if overlap > threshold and not has_transition:
                flags.append(PlagiarismFlag(
                    type='patchwork_pattern',
                    paragraph_indices=[i, i + 1],
                    evidence=f'High lexical overlap ({overlap:.1%}) without clear transition',
                    confidence=min(0.85, 0.6 + overlap * 0.2)
                ))

        return flags

    def _check_corpus_overlap(
        self,
        full_text: str,
        corpus_texts: List[str]
    ) -> List[PlagiarismFlag]:
        """Check for high n-gram overlap against stored corpus texts."""
        flags = []
        threshold = self.config['corpus_overlap_threshold']

        if not corpus_texts:
            return flags

        # Tokenize current text
        current_words = set(full_text.lower().split())

        # Check against each corpus text
        for corpus_idx, corpus_text in enumerate(corpus_texts):
            corpus_words = set(corpus_text.lower().split())

            if not corpus_words:
                continue

            # Calculate overlap
            intersection = current_words & corpus_words
            union = current_words | corpus_words
            overlap = len(intersection) / len(union) if union else 0

            if overlap > threshold:
                flags.append(PlagiarismFlag(
                    type='corpus_overlap',
                    paragraph_indices=[],  # Applies to entire document
                    evidence=f'High overlap ({overlap:.1%}) with stored submission #{corpus_idx + 1}',
                    confidence=min(0.95, 0.7 + overlap * 0.2)
                ))

        return flags

    def _calculate_risk_level(self, flags: List[PlagiarismFlag]) -> str:
        """Calculate overall risk level based on flags."""
        if not flags:
            return 'low'

        # Count high-confidence flags
        high_confidence = sum(1 for flag in flags if flag.confidence >= 0.8)
        medium_confidence = sum(1 for flag in flags if 0.6 <= flag.confidence < 0.8)

        # Risk calculation
        if high_confidence >= 2 or (high_confidence >= 1 and medium_confidence >= 2):
            return 'high'
        elif high_confidence >= 1 or medium_confidence >= 2:
            return 'medium'
        else:
            return 'low'

    def to_dict(self, result: PlagiarismResult) -> Dict[str, Any]:
        """Convert PlagiarismResult to dictionary for JSON serialization."""
        return {
            'risk_level': result.risk_level,
            'flags': [
                {
                    'type': flag.type,
                    'paragraph_indices': flag.paragraph_indices,
                    'evidence': flag.evidence,
                    'confidence': round(flag.confidence, 2)
                }
                for flag in result.flags
            ],
            'note': result.note
        }


# Global checker instance
_plagiarism_checker: Optional[PlagiarismChecker] = None


def get_plagiarism_checker() -> PlagiarismChecker:
    """Get global plagiarism checker instance."""
    global _plagiarism_checker
    if _plagiarism_checker is None:
        _plagiarism_checker = PlagiarismChecker()
        logger.info("Global plagiarism checker created")
    return _plagiarism_checker


def reset_plagiarism_checker() -> None:
    """Reset global plagiarism checker instance."""
    global _plagiarism_checker
    _plagiarism_checker = None
