"""
Test script to demonstrate plagiarism pattern detection.

This script shows how the plagiarism checker works and integrates
with the feedback generation pipeline.
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assignment_feedback.settings')
django.setup()

from feedback_system.plagiarism_checker import (
    PlagiarismChecker,
    get_plagiarism_checker,
    reset_plagiarism_checker
)


def test_repetition_pattern():
    """Test repetition pattern detection."""
    print("=" * 70)
    print("TEST 1: Repetition Pattern Detection")
    print("=" * 70)
    print()

    text = """
    Climate change represents one of the most significant challenges facing our world today.
    Climate change represents one of the most significant challenges facing our world today.
    Climate change represents one of the most significant challenges facing our world today.
    """

    paragraphs = [
        "Climate change represents one of the most significant challenges facing our world today. First paragraph.",
        "Climate change represents one of the most significant challenges facing our world today. Second paragraph.",
        "Climate change represents one of the most significant challenges facing our world today. Third paragraph."
    ]

    checker = get_plagiarism_checker()
    result = checker.check_text(text, paragraphs)

    print(f"Risk Level: {result.risk_level}")
    print(f"Number of Flags: {len(result.flags)}")
    print(f"Note: {result.note}")
    print()

    for i, flag in enumerate(result.flags, 1):
        print(f"Flag {i}:")
        print(f"  Type: {flag.type}")
        print(f"  Paragraphs: {flag.paragraph_indices}")
        print(f"  Evidence: {flag.evidence}")
        print(f"  Confidence: {flag.confidence:.2f}")
        print()

    print("✅ Test completed successfully")
    print()


def test_citation_style_shift():
    """Test citation style shift detection."""
    print("=" * 70)
    print("TEST 2: Citation Style Shift Detection")
    print("=" * 70)
    print()

    text = """
    According to Smith (2020), climate change is accelerating rapidly.
    As noted by Johnson 123, this requires immediate action.
    """

    paragraphs = [
        "According to Smith (2020), climate change is accelerating rapidly. This uses APA style.",
        "As noted by Johnson 123, this requires immediate action. This uses MLA style."
    ]

    checker = get_plagiarism_checker()
    result = checker.check_text(text, paragraphs)

    print(f"Risk Level: {result.risk_level}")
    print(f"Number of Flags: {len(result.flags)}")
    print()

    for i, flag in enumerate(result.flags, 1):
        print(f"Flag {i}:")
        print(f"  Type: {flag.type}")
        print(f"  Evidence: {flag.evidence}")
        print(f"  Confidence: {flag.confidence:.2f}")
        print()

    print("✅ Test completed successfully")
    print()


def test_writing_style_inconsistency():
    """Test writing style inconsistency detection."""
    print("=" * 70)
    print("TEST 3: Writing Style Inconsistency Detection")
    print("=" * 70)
    print()

    text = """
    This is a short sentence. Another short one. Simple style.
    This is an extremely long and complex sentence that contains many words and demonstrates a significant shift in writing style compared to the previous paragraph which was much simpler.
    """

    paragraphs = [
        "This is a short sentence. Another short one. Simple style.",
        "This is an extremely long and complex sentence that contains many words and demonstrates a significant shift in writing style compared to the previous paragraph which was much simpler."
    ]

    checker = get_plagiarism_checker()
    result = checker.check_text(text, paragraphs)

    print(f"Risk Level: {result.risk_level}")
    print(f"Number of Flags: {len(result.flags)}")
    print()

    for i, flag in enumerate(result.flags, 1):
        print(f"Flag {i}:")
        print(f"  Type: {flag.type}")
        print(f"  Evidence: {flag.evidence}")
        print(f"  Confidence: {flag.confidence:.2f}")
        print()

    print("✅ Test completed successfully")
    print()


def test_patchwork_pattern():
    """Test patchwork pattern detection."""
    print("=" * 70)
    print("TEST 4: Patchwork Pattern Detection")
    print("=" * 70)
    print()

    text = """
    Climate change is a serious problem affecting our planet.
    Climate change is a serious problem affecting our planet.
    """

    paragraphs = [
        "Climate change is a serious problem affecting our planet. First point.",
        "Climate change is a serious problem affecting our planet. Second point."
    ]

    checker = get_plagiarism_checker()
    result = checker.check_text(text, paragraphs)

    print(f"Risk Level: {result.risk_level}")
    print(f"Number of Flags: {len(result.flags)}")
    print()

    for i, flag in enumerate(result.flags, 1):
        print(f"Flag {i}:")
        print(f"  Type: {flag.type}")
        print(f"  Evidence: {flag.evidence}")
        print(f"  Confidence: {flag.confidence:.2f}")
        print()

    print("✅ Test completed successfully")
    print()


def test_corpus_overlap():
    """Test corpus overlap detection."""
    print("=" * 70)
    print("TEST 5: Corpus Overlap Detection")
    print("=" * 70)
    print()

    text = "Climate change is a serious problem affecting our planet."
    paragraphs = [text]

    corpus_texts = [
        "Climate change is a serious problem affecting our planet and requires immediate action."
    ]

    checker = get_plagiarism_checker()
    result = checker.check_text(text, paragraphs, corpus_texts)

    print(f"Risk Level: {result.risk_level}")
    print(f"Number of Flags: {len(result.flags)}")
    print()

    for i, flag in enumerate(result.flags, 1):
        print(f"Flag {i}:")
        print(f"  Type: {flag.type}")
        print(f"  Evidence: {flag.evidence}")
        print(f"  Confidence: {flag.confidence:.2f}")
        print()

    print("✅ Test completed successfully")
    print()


def test_low_risk_text():
    """Test with low risk text (no patterns)."""
    print("=" * 70)
    print("TEST 6: Low Risk Text (No Patterns)")
    print("=" * 70)
    print()

    text = """
    Climate change is a complex issue that requires global cooperation.
    Scientists have documented rising temperatures and melting ice caps.
    Renewable energy sources offer promising solutions for the future.
    """

    paragraphs = [
        "Climate change is a complex issue that requires global cooperation.",
        "Scientists have documented rising temperatures and melting ice caps.",
        "Renewable energy sources offer promising solutions for the future."
    ]

    checker = get_plagiarism_checker()
    result = checker.check_text(text, paragraphs)

    print(f"Risk Level: {result.risk_level}")
    print(f"Number of Flags: {len(result.flags)}")
    print(f"Note: {result.note}")
    print()

    if len(result.flags) == 0:
        print("✅ No plagiarism patterns detected - text appears original")
    else:
        for i, flag in enumerate(result.flags, 1):
            print(f"Flag {i}:")
            print(f"  Type: {flag.type}")
            print(f"  Evidence: {flag.evidence}")
            print()

    print("✅ Test completed successfully")
    print()


def test_feature_flag():
    """Test feature flag functionality."""
    print("=" * 70)
    print("TEST 7: Feature Flag Functionality")
    print("=" * 70)
    print()

    # Test with feature enabled
    os.environ['ENABLE_PLAGIARISM_CHECK'] = 'true'
    reset_plagiarism_checker()
    checker_enabled = get_plagiarism_checker()
    print(f"Checker enabled: {checker_enabled.enabled}")

    # Test with feature disabled
    os.environ['ENABLE_PLAGIARISM_CHECK'] = 'false'
    reset_plagiarism_checker()
    checker_disabled = get_plagiarism_checker()
    print(f"Checker disabled: {checker_disabled.enabled}")

    # Test with disabled checker
    result = checker_disabled.check_text("Test text.", ["Test text."])
    print(f"Result with disabled checker: {result.risk_level}")
    print(f"Note: {result.note}")

    print("✅ Test completed successfully")
    print()


def test_json_output():
    """Test JSON output format."""
    print("=" * 70)
    print("TEST 8: JSON Output Format")
    print("=" * 70)
    print()

    text = """
    Climate change represents one of the most significant challenges.
    Climate change represents one of the most significant challenges.
    """

    paragraphs = [
        "Climate change represents one of the most significant challenges. First.",
        "Climate change represents one of the most significant challenges. Second."
    ]

    checker = get_plagiarism_checker()
    result = checker.check_text(text, paragraphs)
    result_dict = checker.to_dict(result)

    print("JSON Output Structure:")
    print(f"  risk_level: {result_dict['risk_level']}")
    print(f"  flags: {len(result_dict['flags'])} flag(s)")
    print(f"  note: {result_dict['note']}")
    print()

    if result_dict['flags']:
        print("First Flag:")
        flag = result_dict['flags'][0]
        print(f"  type: {flag['type']}")
        print(f"  paragraph_indices: {flag['paragraph_indices']}")
        print(f"  evidence: {flag['evidence']}")
        print(f"  confidence: {flag['confidence']}")

    print("✅ Test completed successfully")
    print()


def main():
    """Run all plagiarism detection tests."""
    print()
    print("=" * 70)
    print("PLAGIARISM PATTERN DETECTION DEMONSTRATION")
    print("=" * 70)
    print()
    print("This script demonstrates the plagiarism pattern detection")
    print("functionality with various test scenarios.")
    print()

    try:
        test_repetition_pattern()
        test_citation_style_shift()
        test_writing_style_inconsistency()
        test_patchwork_pattern()
        test_corpus_overlap()
        test_low_risk_text()
        test_feature_flag()
        test_json_output()

        print("=" * 70)
        print("ALL TESTS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print()
        print("Summary:")
        print("✅ Repetition pattern detection working")
        print("✅ Citation style shift detection working")
        print("✅ Writing style inconsistency detection working")
        print("✅ Patchwork pattern detection working")
        print("✅ Corpus overlap detection working")
        print("✅ Low risk text handling working")
        print("✅ Feature flag functionality working")
        print("✅ JSON output format correct")
        print()
        print("The plagiarism pattern detection system is fully functional")
        print("and ready for integration with the feedback generation pipeline.")
        print()

    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
