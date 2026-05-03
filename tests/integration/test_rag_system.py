"""
Test script to demonstrate RAG functionality without requiring API keys.

This script shows how RAG works in the system:
1. RETRIEVAL: Get rubric from database
2. AUGMENTATION: Format rubric for LLM prompt
3. GENERATION: Show what the augmented prompt looks like
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assignment_feedback.settings')
django.setup()

from feedback_system.rubric_rag import RubricRAGService, explain_rag_usage
from feedback_system.models import Rubric


def test_rag_retrieval():
    """Test RAG Step 1: RETRIEVAL"""
    print("=" * 70)
    print("RAG STEP 1: RETRIEVAL - Get Rubric from Database")
    print("=" * 70)
    print()

    # Initialize RAG service (no LLM client needed for retrieval)
    rag_service = RubricRAGService()

    # Retrieve rubric for essay assignment
    rubric = rag_service.retrieve_rubric(assignment_type='essay')

    if rubric:
        print(f"✓ Successfully retrieved rubric: {rubric.name}")
        print(f"  Assignment Type: {rubric.assignment_type}")
        print(f"  Max Score: {rubric.max_score}")
        print(f"  Categories: {rubric.get_total_categories()}")
        print(f"  Criteria: {rubric.get_total_criteria()}")
        print()
        print("Categories and Criteria:")
        for category in rubric.categories.all().order_by('order'):
            print(f"  {category.name} (Weight: {category.weight})")
            for criterion in category.criteria.all().order_by('order'):
                print(f"    • {criterion.name} - Max: {criterion.max_points} points")
        print()
        return rubric
    else:
        print("✗ No rubric found for essay assignment type")
        return None


def test_rag_augmentation(rubric):
    """Test RAG Step 2: AUGMENTATION - Format rubric for prompt"""
    print("=" * 70)
    print("RAG STEP 2: AUGMENTATION - Format Rubric for LLM Prompt")
    print("=" * 70)
    print()

    if not rubric:
        print("✗ No rubric provided for augmentation test")
        return None

    # Initialize RAG service
    rag_service = RubricRAGService()

    # Format rubric for prompt
    rubric_context = rag_service.format_rubric_for_prompt(rubric)

    print("✓ Rubric formatted for LLM prompt")
    print(f"  Context length: {len(rubric_context)} characters")
    print()
    print("First 500 characters of formatted rubric:")
    print("-" * 70)
    print(rubric_context[:500] + "...")
    print("-" * 70)
    print()

    return rubric_context


def test_rag_generation_preview(rubric_context):
    """Test RAG Step 3: GENERATION - Show augmented prompt"""
    print("=" * 70)
    print("RAG STEP 3: GENERATION - Augmented LLM Prompt Preview")
    print("=" * 70)
    print()

    # Sample paragraph for evaluation
    sample_paragraph = """
    Climate change represents one of the most significant challenges facing humanity in the 21st century.
    The scientific evidence is overwhelming, with global temperatures rising at an unprecedented rate.
    This essay will examine the causes of climate change and propose comprehensive solutions.
    """

    # Initialize RAG service
    rag_service = RubricRAGService()

    # Create RAG-enhanced prompt (without sending to LLM)
    rag_prompt = rag_service._create_rag_prompt(
        paragraph=sample_paragraph.strip(),
        paragraph_index=0,
        rubric_context=rubric_context,
        context="Academic essay on climate change"
    )

    print("✓ RAG-enhanced prompt created")
    print(f"  Total prompt length: {len(rag_prompt)} characters")
    print()
    print("Prompt Structure:")
    print("-" * 70)
    print("1. System Instructions: Expert writing tutor with rubric specialization")
    print("2. Rubric Context: [Retrieved rubric criteria and performance levels]")
    print("3. Student Text: [Paragraph to evaluate]")
    print("4. Assignment Context: [Additional context if provided]")
    print("5. Output Format: Structured response with scores and feedback")
    print("-" * 70)
    print()
    print("First 800 characters of RAG-enhanced prompt:")
    print("-" * 70)
    print(rag_prompt[:800] + "...")
    print("-" * 70)
    print()

    return rag_prompt


def demonstrate_rag_workflow():
    """Demonstrate complete RAG workflow"""
    print()
    print("=" * 70)
    print("COMPLETE RAG WORKFLOW DEMONSTRATION")
    print("=" * 70)
    print()

    # Step 1: RETRIEVAL
    rubric = test_rag_retrieval()
    if not rubric:
        print("Cannot continue RAG workflow without rubric")
        return

    # Step 2: AUGMENTATION
    rubric_context = test_rag_augmentation(rubric)
    if not rubric_context:
        print("Cannot continue RAG workflow without rubric context")
        return

    # Step 3: GENERATION (preview)
    test_rag_generation_preview(rubric_context)

    print()
    print("=" * 70)
    print("RAG WORKFLOW SUMMARY")
    print("=" * 70)
    print()
    print("✓ Step 1 (RETRIEVAL): Rubric retrieved from database")
    print("✓ Step 2 (AUGMENTATION): Rubric formatted for LLM prompt")
    print("✓ Step 3 (GENERATION): RAG-enhanced prompt ready for LLM")
    print()
    print("HOW RAG IMPROVES FEEDBACK:")
    print("  • Consistency: Same rubric used for all evaluations")
    print("  • Transparency: Clear criteria and performance levels")
    print("  • Alignment: Feedback matches specific standards")
    print("  • Flexibility: Easy to update rubrics without code changes")
    print()
    print("NEXT STEPS (with API key):")
    print("  1. Set GROQ_API_KEY environment variable")
    print("  2. Call POST /api/rubric-rag-feedback/ with paragraphs")
    print("  3. Receive rubric-aligned scores and feedback")
    print()


def show_rag_explanation():
    """Show detailed RAG explanation"""
    print()
    print("=" * 70)
    print("DETAILED RAG EXPLANATION")
    print("=" * 70)
    print()

    explanation = explain_rag_usage()
    print(explanation)
    print()


def main():
    """Main test function"""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 15 + "RAG SYSTEM TEST SUITE" + " " * 30 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    try:
        # Show RAG explanation
        show_rag_explanation()

        # Demonstrate RAG workflow
        demonstrate_rag_workflow()

        print("=" * 70)
        print("✓ RAG SYSTEM TEST COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print()
        print("KEY TAKEAWAYS:")
        print("  1. RAG retrieves rubrics from database (not vector search)")
        print("  2. RAG augments prompts with specific evaluation criteria")
        print("  3. RAG generates rubric-aligned feedback and scores")
        print("  4. Simple RAG works well for structured data like rubrics")
        print("  5. No complex vector database needed for this use case")
        print()
        print("API ENDPOINTS AVAILABLE:")
        print("  • GET  /api/rag-explanation/ - Detailed RAG explanation")
        print("  • GET  /api/rubric-retrieval/?assignment_type=essay - Retrieve rubric")
        print("  • POST /api/rubric-rag-feedback/ - Generate RAG-based feedback")
        print()

    except Exception as e:
        print(f"✗ Error during RAG testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()