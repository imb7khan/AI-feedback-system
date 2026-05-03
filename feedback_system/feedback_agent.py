"""
Single Agent for orchestrating the complete feedback generation workflow.

This agent coordinates:
- Text preprocessing
- Rubric retrieval (RAG)
- LLM feedback generation
- Score calculation
- Final output combination

Architecture: Simple orchestrator pattern with clear separation of concerns.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .text_preprocessing import TextPreprocessor
from .rubric_rag import RubricRAGService
from .llm_integration import GroqLLMClient, LLMIntegrationError
from .plagiarism_checker import PlagiarismChecker, get_plagiarism_checker

logger = logging.getLogger(__name__)


@dataclass
class AgentInput:
    """Input data for the feedback generation agent."""
    text: str
    assignment_type: str
    context: Optional[str] = None
    rubric_id: Optional[int] = None
    model: str = "llama-3.3-70b-versatile"


@dataclass
class AgentOutput:
    """Output data from the feedback generation agent."""
    success: bool
    rubric: Dict[str, Any]
    preprocessed_data: Dict[str, Any]
    feedback_results: Dict[str, Any]
    final_output: Dict[str, Any]
    error_message: Optional[str] = None


class FeedbackGenerationAgent:
    """
    Single agent that orchestrates the complete feedback generation workflow.

    This agent demonstrates a simple, clean architecture where one agent
    coordinates multiple specialized components without complex multi-agent
    interactions.

    Architecture:
    1. Input Processing: Preprocess text into paragraphs
    2. Context Retrieval: Get rubric using RAG
    3. Content Generation: Call LLM with rubric context
    4. Result Integration: Combine scores and feedback
    5. Output Formatting: Create final structured response

    Design Principles:
    - Single Responsibility: Each component has one clear purpose
    - Clear Interfaces: Well-defined input/output contracts
    - Error Handling: Graceful degradation with informative errors
    - Testability: Each step can be tested independently
    """

    def __init__(self, llm_client: Optional[GroqLLMClient] = None):
        """
        Initialize the feedback generation agent.

        Args:
            llm_client: Optional LLM client (will create default if not provided)
        """
        self.llm_client = llm_client
        self.text_preprocessor = TextPreprocessor()
        self.rag_service = RubricRAGService(llm_client=llm_client)
        self.plagiarism_checker = get_plagiarism_checker()

        logger.info("FeedbackGenerationAgent initialized")

    def process(self, agent_input: AgentInput) -> AgentOutput:
        """
        Main orchestration method - coordinates the complete workflow.

        This is the single entry point that orchestrates all components:
        1. Preprocess text into paragraphs
        2. Retrieve rubric using RAG
        3. Generate feedback using LLM
        4. Combine results into final output

        Args:
            agent_input: Input data containing text and assignment details

        Returns:
            AgentOutput with complete feedback and scores
        """
        try:
            logger.info(f"Starting feedback generation for {agent_input.assignment_type}")

            # Step 1: Preprocess text
            preprocessed_data = self._preprocess_text(agent_input.text)

            # Step 1.5: Check for plagiarism patterns
            plagiarism_result = self._check_plagiarism_patterns(
                agent_input.text,
                preprocessed_data['paragraphs']
            )

            # Step 2: Retrieve rubric (RAG)
            rubric_data = self._retrieve_rubric(
                agent_input.assignment_type,
                agent_input.rubric_id
            )

            if not rubric_data:
                return AgentOutput(
                    success=False,
                    rubric={},
                    preprocessed_data=preprocessed_data,
                    feedback_results={},
                    final_output={},
                    error_message="No rubric found for the given assignment type"
                )

            # Step 3: Generate feedback using RAG
            feedback_results = self._generate_feedback(
                preprocessed_data['paragraphs'],
                rubric_data,
                agent_input.context
            )

            # Step 4: Combine everything into final output
            final_output = self._create_final_output(
                preprocessed_data,
                rubric_data,
                feedback_results,
                plagiarism_result
            )

            logger.info("Feedback generation completed successfully")

            return AgentOutput(
                success=True,
                rubric=rubric_data,
                preprocessed_data=preprocessed_data,
                feedback_results=feedback_results,
                final_output=final_output
            )

        except Exception as e:
            logger.error(f"Error in agent processing: {str(e)}")
            return AgentOutput(
                success=False,
                rubric={},
                preprocessed_data={},
                feedback_results={},
                final_output={},
                error_message=f"Processing failed: {str(e)}"
            )

    def _preprocess_text(self, text: str) -> Dict[str, Any]:
        """
        Step 1: Preprocess text into paragraphs.

        Args:
            text: Raw text to preprocess

        Returns:
            Dictionary with preprocessed paragraphs and statistics
        """
        logger.info("Step 1: Preprocessing text")

        paragraphs = self.text_preprocessor.preprocess_text(text)
        stats = self.text_preprocessor.get_paragraph_stats(paragraphs)

        return {
            'paragraphs': paragraphs,
            'statistics': stats,
            'original_text_length': len(text)
        }

    def _check_plagiarism_patterns(
        self,
        full_text: str,
        paragraphs: List[str]
    ) -> Any:
        """
        Step 1.5: Check for plagiarism patterns.

        Args:
            full_text: Complete essay text
            paragraphs: List of preprocessed paragraphs

        Returns:
            PlagiarismResult with risk level and flags
        """
        logger.info("Step 1.5: Checking plagiarism patterns")

        try:
            result = self.plagiarism_checker.check_text(full_text, paragraphs)
            logger.info(f"Plagiarism check completed: {result.risk_level} risk level")
            return result
        except Exception as e:
            logger.error(f"Error in plagiarism check: {str(e)}")
            # Return low risk result on error to avoid breaking the pipeline
            from .plagiarism_checker import PlagiarismResult
            return PlagiarismResult(
                risk_level='low',
                flags=[],
                note='Plagiarism check failed, defaulting to low risk'
            )

    def _retrieve_rubric(
        self,
        assignment_type: str,
        rubric_id: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Step 2: Retrieve rubric using RAG.

        Args:
            assignment_type: Type of assignment
            rubric_id: Optional specific rubric ID

        Returns:
            Dictionary with rubric information or None if not found
        """
        logger.info("Step 2: Retrieving rubric (RAG)")

        rubric = self.rag_service.retrieve_rubric(assignment_type, rubric_id)

        if not rubric:
            logger.warning(f"No rubric found for {assignment_type}")
            return None

        # Convert rubric to dictionary format
        rubric_data = {
            'id': rubric.id,
            'name': rubric.name,
            'description': rubric.description,
            'assignment_type': rubric.assignment_type,
            'max_score': rubric.max_score,
            'is_active': rubric.is_active,
            'total_categories': rubric.get_total_categories(),
            'total_criteria': rubric.get_total_criteria(),
            'categories': []
        }

        for category in rubric.categories.all().order_by('order'):
            category_data = {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'weight': str(category.weight),
                'criteria': []
            }

            for criterion in category.criteria.all().order_by('order'):
                criterion_data = {
                    'id': criterion.id,
                    'name': criterion.name,
                    'description': criterion.description,
                    'criterion_type': criterion.criterion_type,
                    'max_points': criterion.max_points
                }
                category_data['criteria'].append(criterion_data)

            rubric_data['categories'].append(category_data)

        logger.info(f"Retrieved rubric: {rubric.name}")
        return rubric_data

    def _generate_feedback(
        self,
        paragraphs: List[str],
        rubric_data: Dict[str, Any],
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Step 3: Generate feedback using RAG-enhanced LLM calls.

        Args:
            paragraphs: List of preprocessed paragraphs
            rubric_data: Retrieved rubric information
            context: Optional additional context

        Returns:
            Dictionary with feedback results and scores
        """
        logger.info("Step 3: Generating feedback with RAG")

        if not self.llm_client:
            raise LLMIntegrationError(
                "LLM client not initialized. Cannot generate feedback without LLM."
            )

        try:
            # Import here to avoid circular dependency
            from .models import Rubric

            # Get the actual Rubric model instance
            rubric = Rubric.objects.get(id=rubric_data['id'])

            # Generate RAG-based feedback
            feedback_result = self.rag_service.generate_document_rubric_feedback(
                paragraphs=paragraphs,
                assignment_type=rubric_data['assignment_type'],
                rubric_id=rubric_data['id'],
                context=context
            )

            return feedback_result

        except Exception as e:
            logger.error(f"Error generating feedback: {str(e)}")
            raise LLMIntegrationError(f"Feedback generation failed: {str(e)}")

    def _create_final_output(
        self,
        preprocessed_data: Dict[str, Any],
        rubric_data: Dict[str, Any],
        feedback_results: Dict[str, Any],
        plagiarism_result: Any = None
    ) -> Dict[str, Any]:
        """
        Step 4: Combine everything into final structured output.

        Args:
            preprocessed_data: Preprocessed text information
            rubric_data: Retrieved rubric information
            feedback_results: Generated feedback and scores

        Returns:
            Final structured output combining all components
        """
        logger.info("Step 4: Creating final output")

        # Extract rubric scores from feedback results
        overall_score_data = feedback_results.get('overall_score', {})
        total_points = overall_score_data.get('total_points', 0)
        max_points = overall_score_data.get('max_points', 0)
        percentage = overall_score_data.get('percentage', 0)

        # Create paragraph feedback array
        paragraph_feedback = []
        all_strengths = []
        all_improvements = []

        for feedback in feedback_results.get('paragraph_feedback', []):
            paragraph_data = {
                'paragraph_index': feedback.get('paragraph_index'),
                'text': feedback.get('paragraph_text', '')[:100] + '...',
                'overall_feedback': feedback.get('overall_feedback', ''),
                'rubric_scores': feedback.get('criterion_scores', {}),
                'total_score': feedback.get('total_score', 0),
                'max_score': feedback.get('max_score', 0),
                'strengths': feedback.get('strengths', []),
                'improvements': feedback.get('improvements', [])
            }

            paragraph_feedback.append(paragraph_data)

            # Collect strengths and improvements
            all_strengths.extend(feedback.get('strengths', []))
            all_improvements.extend(feedback.get('improvements', []))

        # Remove duplicates
        all_strengths = list(set(all_strengths))
        all_improvements = list(set(all_improvements))

        # Create rubric scores object
        rubric_scores = {
            'total_points': total_points,
            'max_points': max_points,
            'percentage': round(percentage, 2) if isinstance(percentage, float) else percentage,
            'letter_grade': self._calculate_letter_grade(percentage)
        }

        # Create overall feedback object
        overall_feedback = {
            'summary': f"Overall performance: {rubric_scores['letter_grade']} grade ({rubric_scores['percentage']}%)",
            'key_strengths': all_strengths[:3],  # Top 3 strengths
            'key_improvements': all_improvements[:3]  # Top 3 improvements
        }

        # Generate suggestions
        suggestions = self._generate_recommendations(percentage, all_improvements, plagiarism_result)

        # Create final output with required structure
        final_output = {
            'paragraph_feedback': paragraph_feedback,
            'rubric_scores': rubric_scores,
            'overall_feedback': overall_feedback,
            'suggestions': suggestions
        }

        # Add plagiarism results if available
        if plagiarism_result:
            final_output['plagiarism_analysis'] = self.plagiarism_checker.to_dict(plagiarism_result)

        return final_output

    def _calculate_letter_grade(self, percentage: float) -> str:
        """Calculate letter grade from percentage."""
        if percentage >= 90:
            return 'A'
        elif percentage >= 80:
            return 'B'
        elif percentage >= 70:
            return 'C'
        elif percentage >= 60:
            return 'D'
        else:
            return 'F'

    def _generate_recommendations(
        self,
        percentage: float,
        improvements: List[str],
        plagiarism_result: Any = None
    ) -> List[str]:
        """Generate actionable recommendations based on performance."""
        recommendations = []

        if percentage < 70:
            recommendations.append("Consider reviewing the rubric criteria more carefully before writing")
            recommendations.append("Focus on addressing the specific performance level descriptions")

        if percentage >= 70 and percentage < 85:
            recommendations.append("Good foundation! Focus on the specific improvement areas identified")
            recommendations.append("Review the 'Good' vs 'Excellent' performance level differences")

        if percentage >= 85:
            recommendations.append("Excellent work! Review the minor improvement areas for perfection")
            recommendations.append("Consider how to elevate from 'Good' to 'Excellent' in all criteria")

        # Add specific recommendations based on common issues
        improvement_text = ' '.join(improvements).lower()
        if 'thesis' in improvement_text:
            recommendations.append("Work on making your thesis statement more specific and compelling")
        if 'evidence' in improvement_text:
            recommendations.append("Incorporate more relevant and credible evidence to support your arguments")
        if 'grammar' in improvement_text or 'style' in improvement_text:
            recommendations.append("Review your work for grammar, mechanics, and academic tone")

        # Add academic integrity suggestions if plagiarism risk is medium/high
        if plagiarism_result and plagiarism_result.risk_level in ['medium', 'high']:
            recommendations.append("Review your work to ensure all sources are properly cited and attributed")
            recommendations.append("Consider using quotation marks for direct quotes and paraphrasing appropriately")
            if plagiarism_result.risk_level == 'high':
                recommendations.append("Please review academic integrity guidelines and ensure proper attribution of all sources")

        return recommendations[:5]  # Limit to top 5 recommendations

    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format."""
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'

    def get_workflow_summary(self) -> Dict[str, Any]:
        """
        Get summary of the agent's workflow and capabilities.

        Returns:
            Dictionary with workflow information
        """
        return {
            'agent_name': 'FeedbackGenerationAgent',
            'agent_type': 'Single Orchestrator Agent',
            'workflow_steps': [
                {
                    'step': 1,
                    'name': 'Text Preprocessing',
                    'description': 'Split text into clean paragraphs',
                    'component': 'TextPreprocessor'
                },
                {
                    'step': 2,
                    'name': 'Rubric Retrieval (RAG)',
                    'description': 'Get evaluation rubric from database',
                    'component': 'RubricRAGService'
                },
                {
                    'step': 3,
                    'name': 'Feedback Generation',
                    'description': 'Generate rubric-aligned feedback using LLM',
                    'component': 'GroqLLMClient + RAG'
                },
                {
                    'step': 4,
                    'name': 'Result Integration',
                    'description': 'Combine scores and feedback into final output',
                    'component': 'FeedbackGenerationAgent'
                }
            ],
            'architecture': 'Simple Orchestrator Pattern',
            'design_principles': [
                'Single Responsibility - Each component has one clear purpose',
                'Clear Interfaces - Well-defined input/output contracts',
                'Error Handling - Graceful degradation with informative errors',
                'Testability - Each step can be tested independently'
            ],
            'components': [
                'TextPreprocessor - Text cleaning and paragraph splitting',
                'RubricRAGService - Rubric retrieval and prompt augmentation',
                'GroqLLMClient - LLM interaction for feedback generation',
                'FeedbackGenerationAgent - Workflow orchestration'
            ]
        }


def explain_agent_architecture():
    """
    Explain the agent architecture clearly.

    This function provides a comprehensive explanation of how the
    single agent orchestrates the complete workflow.
    """
    explanation = """
SINGLE AGENT ARCHITECTURE EXPLANATION
=====================================

AGENT DESIGN: Simple Orchestrator Pattern
------------------------------------------

The FeedbackGenerationAgent is a SINGLE agent that coordinates
multiple specialized components. This is NOT a multi-agent system.

ARCHITECTURE OVERVIEW:
    Input → Agent → [Components] → Agent → Output

The agent acts as a conductor, coordinating different "instruments"
(components) to create a harmonious result (final feedback).

WORKFLOW STEPS:
---------------

Step 1: TEXT PREPROCESSING
    Component: TextPreprocessor
    Action: Clean and split text into paragraphs
    Input: Raw essay text
    Output: List of clean paragraphs

Step 2: RUBRIC RETRIEVAL (RAG)
    Component: RubricRAGService
    Action: Get rubric from database
    Input: Assignment type (e.g., 'essay')
    Output: Rubric with criteria and performance levels

Step 3: FEEDBACK GENERATION
    Component: GroqLLMClient + RAG
    Action: Generate rubric-aligned feedback
    Input: Paragraphs + Rubric context
    Output: Scores and detailed feedback

Step 4: RESULT INTEGRATION
    Component: FeedbackGenerationAgent
    Action: Combine everything into final output
    Input: Preprocessed data + Rubric + Feedback
    Output: Structured final response

WHY SINGLE AGENT?
-----------------

1. SIMPLICITY
   - One entry point for the entire workflow
   - Easy to understand and maintain
   - Clear responsibility: orchestration only

2. PERFORMANCE
   - No inter-agent communication overhead
   - Direct component calls
   - Faster execution

3. RELIABILITY
   - Fewer moving parts
   - Easier error handling
   - Simpler debugging

4. MAINTAINABILITY
   - Clear code structure
   - Easy to modify individual components
   - Straightforward testing

AGENT vs MULTI-AGENT:
---------------------

SINGLE AGENT (This Implementation):
    • One coordinator agent
    • Direct component calls
    • Simple, linear workflow
    • Easy to understand

MULTI-AGENT (Not Used Here):
    • Multiple specialized agents
    • Agent-to-agent communication
    • Complex coordination
    • Harder to debug

COMPONENT ARCHITECTURE:
----------------------

The agent coordinates these components:

1. TextPreprocessor
   - Responsibility: Text cleaning and paragraph splitting
   - Interface: preprocess_text(text) → paragraphs
   - Independence: Can be tested standalone

2. RubricRAGService
   - Responsibility: Rubric retrieval and prompt augmentation
   - Interface: retrieve_rubric() → rubric
   - Independence: Can work without LLM

3. GroqLLMClient
   - Responsibility: LLM interaction
   - Interface: generate_feedback() → feedback
   - Independence: Can be tested with mock responses

4. FeedbackGenerationAgent
   - Responsibility: Workflow orchestration
   - Interface: process(input) → output
   - Independence: Coordinates all components

DESIGN PRINCIPLES:
------------------

1. SINGLE RESPONSIBILITY
   Each component does one thing well:
   - Preprocessor: Only handles text
   - RAG Service: Only handles rubrics
   - LLM Client: Only handles LLM calls
   - Agent: Only handles coordination

2. CLEAR INTERFACES
   Well-defined input/output contracts:
   - Input: AgentInput dataclass
   - Output: AgentOutput dataclass
   - Each component: Clear function signatures

3. ERROR HANDLING
   Graceful degradation:
   - Missing rubric → Clear error message
   - LLM failure → Informative error
   - Invalid input → Validation error

4. TESTABILITY
   Independent testing:
   - Each component can be tested alone
   - Agent can be tested with mocks
   - End-to-end testing possible

DATA FLOW:
-----------

Input Data (AgentInput):
    • text: "Raw essay text..."
    • assignment_type: "essay"
    • context: "Academic essay..."
    • rubric_id: optional

    ↓

Agent Orchestration:
    1. Preprocess text → paragraphs
    2. Get rubric → criteria
    3. Generate feedback → scores
    4. Combine results → output

    ↓

Output Data (AgentOutput):
    • success: true/false
    • rubric: {...}
    • preprocessed_data: {...}
    • feedback_results: {...}
    • final_output: {...}

BENEFITS OF THIS ARCHITECTURE:
------------------------------

1. CLARITY
   - Easy to understand the workflow
   - Clear separation of concerns
   - Obvious data flow

2. FLEXIBILITY
   - Easy to swap components
   - Can add new steps
   - Simple to modify

3. SCALABILITY
   - Components can be optimized independently
   - Can add caching where needed
   - Can parallelize independent steps

4. MAINTAINABILITY
   - Clear code structure
   - Easy to debug
   - Simple to extend

EXAMPLE USAGE:
--------------

# Initialize agent
agent = FeedbackGenerationAgent()

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
        print(f"Paragraph {paragraph['paragraph_index']}: {paragraph['total_score']}/{paragraph['max_score']}")

This single agent architecture provides a clean, efficient way to
orchestrate complex workflows without the overhead of multi-agent systems.
"""

    return explanation