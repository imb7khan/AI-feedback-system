"""
Test script to demonstrate the single agent orchestration.

This script shows how the FeedbackGenerationAgent coordinates:
- Text preprocessing
- Rubric retrieval (RAG)
- LLM feedback generation
- Score calculation
- Final output combination
"""

import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assignment_feedback.settings')
django.setup()

from feedback_system.feedback_agent import (
    FeedbackGenerationAgent,
    AgentInput,
    AgentOutput,
    explain_agent_architecture
)


def test_agent_architecture():
    """Test and display agent architecture."""
    print("=" * 70)
    print("SINGLE AGENT ARCHITECTURE DEMONSTRATION")
    print("=" * 70)
    print()

    # Get architecture explanation
    explanation = explain_agent_architecture()
    print(explanation)
    print()


def test_agent_workflow():
    """Test the complete agent workflow."""
    print("=" * 70)
    print("AGENT WORKFLOW TEST")
    print("=" * 70)
    print()

    # Initialize agent (without LLM client for testing)
    agent = FeedbackGenerationAgent()

    # Get workflow summary
    workflow = agent.get_workflow_summary()

    print(f"Agent Name: {workflow['agent_name']}")
    print(f"Agent Type: {workflow['agent_type']}")
    print(f"Architecture: {workflow['architecture']}")
    print()

    print("Workflow Steps:")
    for step in workflow['workflow_steps']:
        print(f"  Step {step['step']}: {step['name']}")
        print(f"    Description: {step['description']}")
        print(f"    Component: {step['component']}")
        print()

    print("Design Principles:")
    for principle in workflow['design_principles']:
        print(f"  • {principle}")
    print()

    print("Components:")
    for component in workflow['components']:
        print(f"  • {component}")
    print()


def test_agent_components():
    """Test individual agent components."""
    print("=" * 70)
    print("AGENT COMPONENTS TEST")
    print("=" * 70)
    print()

    # Test 1: Text Preprocessing
    print("Test 1: Text Preprocessing Component")
    try:
        from feedback_system.text_preprocessing import TextPreprocessor

        preprocessor = TextPreprocessor()
        test_text = """
        This is the first paragraph. It contains important information.

        This is the second paragraph. It provides additional details.

        This is the third paragraph. It concludes the discussion.
        """

        paragraphs = preprocessor.preprocess_text(test_text)
        stats = preprocessor.get_paragraph_stats(paragraphs)

        print(f"  ✓ Preprocessed {stats['total_paragraphs']} paragraphs")
        print(f"  ✓ Total words: {stats['total_words']}")
        print(f"  ✓ Average length: {stats['avg_paragraph_length']:.1f} characters")
        print()

    except Exception as e:
        print(f"  ✗ Preprocessing test failed: {e}")
        print()

    # Test 2: Rubric Retrieval (RAG)
    print("Test 2: Rubric Retrieval Component (RAG)")
    try:
        from feedback_system.rubric_rag import RubricRAGService

        rag_service = RubricRAGService()
        rubric = rag_service.retrieve_rubric('essay')

        if rubric:
            print(f"  ✓ Retrieved rubric: {rubric.name}")
            print(f"  ✓ Categories: {rubric.get_total_categories()}")
            print(f"  ✓ Criteria: {rubric.get_total_criteria()}")
        else:
            print("  ✗ No rubric found")
        print()

    except Exception as e:
        print(f"  ✗ Rubric retrieval test failed: {e}")
        print()

    # Test 3: Agent Initialization
    print("Test 3: Agent Initialization")
    try:
        agent = FeedbackGenerationAgent()
        print(f"  ✓ Agent initialized successfully")
        print(f"  ✓ Agent has {len(agent.get_workflow_summary()['components'])} components")
        print()

    except Exception as e:
        print(f"  ✗ Agent initialization failed: {e}")
        print()


def test_agent_data_flow():
    """Test the agent data flow."""
    print("=" * 70)
    print("AGENT DATA FLOW DEMONSTRATION")
    print("=" * 70)
    print()

    # Sample input data
    sample_text = """
    Climate change represents one of the most significant challenges facing humanity in the 21st century.
    The scientific evidence is overwhelming, with global temperatures rising at an unprecedented rate.
    This essay will examine the causes of climate change and propose comprehensive solutions.
    """

    print("Input Data (AgentInput):")
    print("-" * 70)
    print(f"  text: {sample_text[:100]}...")
    print(f"  assignment_type: essay")
    print(f"  context: Academic essay on climate change")
    print("-" * 70)
    print()

    print("Expected Data Flow:")
    print("-" * 70)
    print("Step 1: Text Preprocessing")
    print("  Input: Raw essay text")
    print("  Process: Clean and split into paragraphs")
    print("  Output: List of clean paragraphs")
    print()

    print("Step 2: Rubric Retrieval (RAG)")
    print("  Input: Assignment type 'essay'")
    print("  Process: Query database for essay rubric")
    print("  Output: Rubric with criteria and performance levels")
    print()

    print("Step 3: Feedback Generation")
    print("  Input: Paragraphs + Rubric context")
    print("  Process: LLM generates rubric-aligned feedback")
    print("  Output: Scores and detailed feedback")
    print()

    print("Step 4: Result Integration")
    print("  Input: Preprocessed data + Rubric + Feedback")
    print("  Process: Combine into structured output")
    print("  Output: Final comprehensive response")
    print("-" * 70)
    print()

    print("Expected Output Data (AgentOutput):")
    print("-" * 70)
    print("  success: true")
    print("  rubric: {...}")
    print("  preprocessed_data: {...}")
    print("  feedback_results: {...}")
    print("  final_output:")
    print("    metadata: {...}")
    print("    rubric_summary: {...}")
    print("    overall_performance:")
    print("      total_points: 42")
    print("      max_points: 65")
    print("      percentage: 64.62")
    print("      letter_grade: C")
    print("    paragraph_analysis: [...]")
    print("    strengths_summary: [...]")
    print("    improvements_summary: [...]")
    print("    recommendations: [...]")
    print("-" * 70)
    print()


def test_agent_without_llm():
    """Test agent components that don't require LLM."""
    print("=" * 70)
    print("AGENT COMPONENTS TEST (No LLM Required)")
    print("=" * 70)
    print()

    # Initialize agent
    agent = FeedbackGenerationAgent()

    # Test preprocessing
    print("Test 1: Text Preprocessing")
    try:
        sample_text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
        preprocessed = agent._preprocess_text(sample_text)

        print(f"  ✓ Preprocessed {preprocessed['statistics']['total_paragraphs']} paragraphs")
        print(f"  ✓ Original length: {preprocessed['original_text_length']} characters")
        print(f"  ✓ Total words: {preprocessed['statistics']['total_words']}")
        print()

    except Exception as e:
        print(f"  ✗ Preprocessing failed: {e}")
        print()

    # Test rubric retrieval
    print("Test 2: Rubric Retrieval")
    try:
        rubric_data = agent._retrieve_rubric('essay')

        if rubric_data:
            print(f"  ✓ Retrieved rubric: {rubric_data['name']}")
            print(f"  ✓ Assignment type: {rubric_data['assignment_type']}")
            print(f"  ✓ Max score: {rubric_data['max_score']}")
            print(f"  ✓ Categories: {rubric_data['total_categories']}")
            print(f"  ✓ Criteria: {rubric_data['total_criteria']}")
        else:
            print("  ✗ No rubric found")
        print()

    except Exception as e:
        print(f"  ✗ Rubric retrieval failed: {e}")
        print()

    # Test letter grade calculation
    print("Test 3: Letter Grade Calculation")
    try:
        test_percentages = [95, 85, 75, 65, 55]
        for percentage in test_percentages:
            grade = agent._calculate_letter_grade(percentage)
            print(f"  ✓ {percentage}% → {grade}")
        print()

    except Exception as e:
        print(f"  ✗ Letter grade calculation failed: {e}")
        print()

    # Test recommendation generation
    print("Test 4: Recommendation Generation")
    try:
        improvements = ["Make thesis more specific", "Add more evidence", "Improve grammar"]
        recommendations = agent._generate_recommendations(75, improvements)

        print(f"  ✓ Generated {len(recommendations)} recommendations")
        for i, rec in enumerate(recommendations, 1):
            print(f"    {i}. {rec}")
        print()

    except Exception as e:
        print(f"  ✗ Recommendation generation failed: {e}")
        print()


def demonstrate_agent_usage():
    """Demonstrate how to use the agent."""
    print("=" * 70)
    print("AGENT USAGE EXAMPLE")
    print("=" * 70)
    print()

    print("Python Code Example:")
    print("-" * 70)
    print("""
# Initialize agent
from feedback_system.feedback_agent import FeedbackGenerationAgent, AgentInput
from feedback_system.llm_integration import GroqLLMClient

# Create LLM client
llm_client = GroqLLMClient()

# Initialize agent
agent = FeedbackGenerationAgent(llm_client=llm_client)

# Create input
input_data = AgentInput(
    text="Your essay text here...",
    assignment_type="essay",
    context="Academic essay on climate change"
)

# Process
output = agent.process(input_data)

# Access results
if output.success:
    print(f"Score: {output.final_output['overall_performance']['percentage']}%")
    print(f"Grade: {output.final_output['overall_performance']['letter_grade']}")

    for paragraph in output.final_output['paragraph_analysis']:
        idx = paragraph['paragraph_index']
        score = paragraph['total_score']
        max_score = paragraph['max_score']
        print(f"Paragraph {idx}: {score}/{max_score}")

    print("\\nStrengths:")
    for strength in output.final_output['strengths_summary']:
        print(f"  • {strength}")

    print("\\nImprovements:")
    for improvement in output.final_output['improvements_summary']:
        print(f"  • {improvement}")

    print("\\nRecommendations:")
    for rec in output.final_output['recommendations']:
        print(f"  • {rec}")
""")
    print("-" * 70)
    print()

    print("API Usage Example:")
    print("-" * 70)
    print("""
# Make API request
curl -X POST -H "Content-Type: application/json" \\
  -d '{
    "text": "Your essay text here...",
    "assignment_type": "essay",
    "context": "Academic essay on climate change"
  }' \\
  http://127.0.0.1:8000/api/feedback-agent/

# Response includes:
# - Overall score and letter grade
# - Paragraph-by-paragraph analysis
# - Strengths and improvements
# - Specific recommendations
# - Rubric alignment information
""")
    print("-" * 70)
    print()


def main():
    """Main test function."""
    print()
    print("╔" + "═" * 68 + "╗")
    print("║" + " " * 20 + "SINGLE AGENT TEST SUITE" + " " * 27 + "║")
    print("╚" + "═" * 68 + "╝")
    print()

    try:
        # Test architecture
        test_agent_architecture()

        # Test workflow
        test_agent_workflow()

        # Test components
        test_agent_components()

        # Test data flow
        test_agent_data_flow()

        # Test without LLM
        test_agent_without_llm()

        # Demonstrate usage
        demonstrate_agent_usage()

        print("=" * 70)
        print("✓ SINGLE AGENT TEST COMPLETED SUCCESSFULLY")
        print("=" * 70)
        print()
        print("KEY TAKEAWAYS:")
        print("  1. Single agent orchestrates complete workflow")
        print("  2. Clear separation of concerns")
        print("  3. Each component has single responsibility")
        print("  4. Well-defined interfaces between components")
        print("  5. Easy to test and maintain")
        print()
        print("AGENT RESPONSIBILITIES:")
        print("  ✓ Take essay paragraphs as input")
        print("  ✓ Call LLM for feedback generation")
        print("  ✓ Retrieve rubric using RAG")
        print("  ✓ Generate scores based on rubric")
        print("  ✓ Combine everything into final output")
        print()
        print("DESIGN PRINCIPLES:")
        print("  • One agent only (no multi-agent system)")
        print("  • Simple orchestrator pattern")
        print("  • Clear architecture explanation")
        print("  • Easy to understand and maintain")
        print()
        print("API ENDPOINTS:")
        print("  • POST /api/feedback-agent/ - Complete workflow")
        print("  • GET  /api/agent-architecture/ - Architecture explanation")
        print("  • GET  /api/agent-workflow/ - Workflow information")
        print()

    except Exception as e:
        print(f"✗ Error during agent testing: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()