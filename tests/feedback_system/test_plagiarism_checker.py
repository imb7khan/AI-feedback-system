"""
Test suite for plagiarism pattern detection.

This module tests the plagiarism checker heuristics and integration
with the feedback generation pipeline.
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assignment_feedback.settings')
django.setup()

import pytest
from unittest.mock import Mock, patch

from feedback_system.plagiarism_checker import (
    PlagiarismChecker,
    PlagiarismFlag,
    PlagiarismResult,
    get_plagiarism_checker,
    reset_plagiarism_checker
)


class TestPlagiarismChecker:
    """Test plagiarism checker functionality."""

    def test_checker_initialization(self):
        """Test checker initialization with default config."""
        reset_plagiarism_checker()
        checker = PlagiarismChecker()
        assert checker.enabled is True
        assert checker.config['repetition_phrase_length'] == 8
        assert checker.config['repetition_threshold'] == 2
        assert checker.config['style_shift_threshold'] == 2.0
        assert checker.config['lexical_overlap_threshold'] == 0.6

    def test_checker_initialization_with_custom_config(self):
        """Test checker initialization with custom config."""
        config = {
            'repetition_phrase_length': 10,
            'repetition_threshold': 3,
            'style_shift_threshold': 3.0
        }
        checker = PlagiarismChecker(config=config)
        assert checker.config['repetition_phrase_length'] == 10
        assert checker.config['repetition_threshold'] == 3
        assert checker.config['style_shift_threshold'] == 3.0

    def test_checker_disabled_via_env(self):
        """Test checker can be disabled via environment variable."""
        with patch.dict(os.environ, {'ENABLE_PLAGIARISM_CHECK': 'false'}):
            checker = PlagiarismChecker()
            assert checker.enabled is False

    def test_check_text_with_insufficient_paragraphs(self):
        """Test check with insufficient paragraphs."""
        checker = PlagiarismChecker()
        result = checker.check_text("Single paragraph text.", ["Single paragraph text."])
        assert result.risk_level == 'low'
        assert len(result.flags) == 0
        assert 'insufficient' in result.note.lower()

    def test_check_text_with_repetition_pattern(self):
        """Test detection of repeated phrases across paragraphs."""
        checker = PlagiarismChecker()

        text = """
        This is a very long phrase that appears multiple times in the essay.
        This is a very long phrase that appears multiple times in the essay.
        This is a very long phrase that appears multiple times in the essay.
        """

        paragraphs = [
            "This is a very long phrase that appears multiple times in the essay. First paragraph.",
            "This is a very long phrase that appears multiple times in the essay. Second paragraph.",
            "This is a very long phrase that appears multiple times in the essay. Third paragraph."
        ]

        result = checker.check_text(text, paragraphs)

        # Should detect repetition pattern
        repetition_flags = [f for f in result.flags if f.type == 'repetition_pattern']
        assert len(repetition_flags) > 0
        assert repetition_flags[0].confidence > 0.5
        assert len(repetition_flags[0].paragraph_indices) > 1

    def test_check_text_with_citation_style_shift(self):
        """Test detection of citation style shifts."""
        checker = PlagiarismChecker()

        text = """
        According to Smith (2020), climate change is real.
        As noted by Johnson 123, this is important.
        """

        paragraphs = [
            "According to Smith (2020), climate change is real. This uses APA style.",
            "As noted by Johnson 123, this is important. This uses MLA style."
        ]

        result = checker.check_text(text, paragraphs)

        # Should detect citation style shift
        citation_flags = [f for f in result.flags if f.type == 'citation_style_shift']
        assert len(citation_flags) > 0
        assert citation_flags[0].confidence > 0.5

    def test_check_text_with_writing_style_shift(self):
        """Test detection of writing style inconsistency."""
        checker = PlagiarismChecker()

        text = """
        This is a very short sentence. Another short one.
        This is an extremely long and complex sentence that contains many words and demonstrates a significant shift in writing style compared to the previous paragraph which was much simpler.
        """

        paragraphs = [
            "This is a very short sentence. Another short one. Simple style.",
            "This is an extremely long and complex sentence that contains many words and demonstrates a significant shift in writing style compared to the previous paragraph which was much simpler."
        ]

        result = checker.check_text(text, paragraphs)

        # Should detect writing style shift
        style_flags = [f for f in result.flags if f.type == 'writing_style_shift']
        assert len(style_flags) > 0
        assert style_flags[0].confidence > 0.5

    def test_check_text_with_patchwork_pattern(self):
        """Test detection of patchwork pattern (high overlap, weak transitions)."""
        checker = PlagiarismChecker()

        text = """
        Climate change is a serious problem affecting our planet.
        Climate change is a serious problem affecting our planet.
        """

        paragraphs = [
            "Climate change is a serious problem affecting our planet. First point.",
            "Climate change is a serious problem affecting our planet. Second point."
        ]

        result = checker.check_text(text, paragraphs)

        # Should detect patchwork pattern
        patchwork_flags = [f for f in result.flags if f.type == 'patchwork_pattern']
        assert len(patchwork_flags) > 0
        assert patchwork_flags[0].confidence > 0.5

    def test_check_text_with_corpus_overlap(self):
        """Test detection of corpus overlap."""
        checker = PlagiarismChecker()

        text = "Climate change is a serious problem affecting our planet."
        paragraphs = [text]

        corpus_texts = [
            "Climate change is a serious problem affecting our planet and requires immediate action."
        ]

        result = checker.check_text(text, paragraphs, corpus_texts)

        # Should detect corpus overlap
        corpus_flags = [f for f in result.flags if f.type == 'corpus_overlap']
        assert len(corpus_flags) > 0
        assert corpus_flags[0].confidence > 0.5

    def test_risk_level_calculation_low(self):
        """Test risk level calculation for low risk."""
        checker = PlagiarismChecker()
        result = checker.check_text("Simple text.", ["Simple text."])
        assert result.risk_level == 'low'

    def test_risk_level_calculation_medium(self):
        """Test risk level calculation for medium risk."""
        checker = PlagiarismChecker()

        text = """
        This is a repeated phrase that appears multiple times.
        This is a repeated phrase that appears multiple times.
        """

        paragraphs = [
            "This is a repeated phrase that appears multiple times. First.",
            "This is a repeated phrase that appears multiple times. Second."
        ]

        result = checker.check_text(text, paragraphs)
        # Should be at least medium risk due to repetition
        assert result.risk_level in ['medium', 'high']

    def test_to_dict_conversion(self):
        """Test conversion of PlagiarismResult to dictionary."""
        checker = PlagiarismChecker()

        flag = PlagiarismFlag(
            type='test_type',
            paragraph_indices=[0, 1],
            evidence='Test evidence',
            confidence=0.75
        )

        result = PlagiarismResult(
            risk_level='medium',
            flags=[flag],
            note='Test note'
        )

        result_dict = checker.to_dict(result)

        assert result_dict['risk_level'] == 'medium'
        assert len(result_dict['flags']) == 1
        assert result_dict['flags'][0]['type'] == 'test_type'
        assert result_dict['flags'][0]['paragraph_indices'] == [0, 1]
        assert result_dict['flags'][0]['evidence'] == 'Test evidence'
        assert result_dict['flags'][0]['confidence'] == 0.75
        assert result_dict['note'] == 'Test note'


class TestGlobalCheckerInstance:
    """Test global checker instance management."""

    def test_get_global_checker(self):
        """Test getting global checker instance."""
        reset_plagiarism_checker()
        checker1 = get_plagiarism_checker()
        checker2 = get_plagiarism_checker()
        assert checker1 is checker2  # Same instance

    def test_reset_global_checker(self):
        """Test resetting global checker instance."""
        checker1 = get_plagiarism_checker()
        reset_plagiarism_checker()
        checker2 = get_plagiarism_checker()
        assert checker1 is not checker2  # Different instances


class TestPlagiarismIntegration:
    """Test plagiarism checker integration with feedback pipeline."""

    def test_feedback_agent_includes_plagiarism_check(self):
        """Test that feedback agent includes plagiarism checking."""
        from feedback_system.feedback_agent import FeedbackGenerationAgent

        agent = FeedbackGenerationAgent()
        assert agent.plagiarism_checker is not None
        assert isinstance(agent.plagiarism_checker, PlagiarismChecker)

    def test_langchain_agent_includes_plagiarism_check(self):
        """Test that LangChain agent includes plagiarism checking."""
        from feedback_system.langchain_integration import LangChainFeedbackAgent

        agent = LangChainFeedbackAgent()
        assert agent.plagiarism_checker is not None
        assert isinstance(agent.plagiarism_checker, PlagiarismChecker)

    def test_plagiarism_results_in_final_output(self):
        """Test that plagiarism results are included in final output."""
        from feedback_system.plagiarism_checker import PlagiarismResult, PlagiarismFlag

        checker = PlagiarismChecker()

        flag = PlagiarismFlag(
            type='repetition_pattern',
            paragraph_indices=[0, 1],
            evidence='Test evidence',
            confidence=0.8
        )

        result = PlagiarismResult(
            risk_level='medium',
            flags=[flag],
            note='Test note'
        )

        result_dict = checker.to_dict(result)

        # Verify structure matches expected format
        assert 'risk_level' in result_dict
        assert 'flags' in result_dict
        assert 'note' in result_dict
        assert isinstance(result_dict['flags'], list)


def run_tests():
    """Run all plagiarism checker tests."""
    print("=" * 70)
    print("PLAGIARISM PATTERN DETECTION TESTS")
    print("=" * 70)
    print()

    # Run pytest programmatically
    import sys
    exit_code = pytest.main([__file__, '-v', '--tb=short'])
    sys.exit(exit_code)


if __name__ == '__main__':
    run_tests()
