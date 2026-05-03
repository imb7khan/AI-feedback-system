"""
LangChain + LangGraph integration for feedback generation system.

This module provides LangChain components and LangGraph orchestration
while maintaining compatibility with existing system behavior.
"""

import logging
from typing import List, Dict, Any, Optional, TypedDict, Annotated
from dataclasses import dataclass

from .text_preprocessing import TextPreprocessor
from .rubric_rag import RubricRAGService
from .llm_integration import GroqLLMClient, LLMIntegrationError
from .langchain_config import get_config
from .plagiarism_checker import PlagiarismChecker, get_plagiarism_checker

logger = logging.getLogger(__name__)

# Try to import LangChain components
try:
    from langchain_groq import ChatGroq
    from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
    from langchain_core.prompts import ChatPromptTemplate
    from langchain_core.output_parsers import StrOutputParser
    from langgraph.graph import StateGraph, END
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger.warning("LangChain not available. Using fallback implementation.")


class FeedbackState(TypedDict):
    """State schema for LangGraph feedback generation."""
    input_text: str
    assignment_type: str
    context: Optional[str]
    rubric_id: Optional[int]
    model: str
    paragraphs: List[str]
    rubric_data: Optional[Dict[str, Any]]
    feedback_results: Optional[Dict[str, Any]]
    plagiarism_result: Optional[Any]
    final_output: Optional[Dict[str, Any]]
    error: Optional[str]


class LangChainFeedbackAgent:
    """
    LangChain + LangGraph based feedback generation agent.

    This agent uses LangGraph for orchestration and LangChain components
    for retrieval and generation while maintaining identical external behavior
    to the original FeedbackGenerationAgent.
    """

    def __init__(
        self,
        llm_client: Optional[GroqLLMClient] = None,
        rag_service: Optional[RubricRAGService] = None,
        config: Optional[Any] = None
    ):
        """
        Initialize LangChain feedback agent.

        Args:
            llm_client: Optional LLM client (will create default if not provided)
            rag_service: Optional RAG service (will create default if not provided)
            config: Optional LangChain configuration
        """
        self.config = config or get_config()
        self.llm_client = llm_client or GroqLLMClient(model=self.config.default_model)
        self.rag_service = rag_service or RubricRAGService(llm_client=self.llm_client)
        self.text_preprocessor = TextPreprocessor()
        self.plagiarism_checker = get_plagiarism_checker()

        # Initialize LangChain components if available
        self.langchain_llm = None
        self.graph = None

        if LANGCHAIN_AVAILABLE and self.config.enable_langchain:
            self._initialize_langchain_components()

        logger.info("LangChainFeedbackAgent initialized")

    def _initialize_langchain_components(self):
        """Initialize LangChain LLM and LangGraph components."""
        try:
            # Initialize LangChain LLM wrapper
            self.langchain_llm = ChatGroq(
                model=self.config.default_model,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                api_key=self.llm_client.api_key
            )
            logger.info("LangChain LLM initialized")

            # Create LangGraph state graph
            if self.config.enable_langgraph:
                # Compile graph before execution; compiled graph exposes .invoke()
                self.graph = self._create_feedback_graph().compile()
                logger.info("LangGraph state graph created")

        except Exception as e:
            logger.error(f"Failed to initialize LangChain components: {str(e)}")
            self.langchain_llm = None
            self.graph = None

    def _create_feedback_graph(self) -> Any:
        """
        Create LangGraph state graph for feedback generation.

        The graph mirrors the existing 4-step workflow:
        1. Preprocess text
        2. Retrieve rubric
        3. Generate feedback
        4. Combine output

        Returns:
            LangGraph StateGraph instance
        """
        # Create state graph
        graph = StateGraph(FeedbackState)

        # Add nodes
        graph.add_node("preprocess", self._preprocess_node)
        graph.add_node("check_plagiarism", self._check_plagiarism_node)
        graph.add_node("retrieve_rubric", self._retrieve_rubric_node)
        graph.add_node("generate_feedback", self._generate_feedback_node)
        graph.add_node("combine_output", self._combine_output_node)

        # Add edges
        graph.set_entry_point("preprocess")
        graph.add_edge("preprocess", "check_plagiarism")
        graph.add_edge("check_plagiarism", "retrieve_rubric")
        graph.add_edge("retrieve_rubric", "generate_feedback")
        graph.add_edge("generate_feedback", "combine_output")
        graph.add_edge("combine_output", END)

        return graph

    def _preprocess_node(self, state: FeedbackState) -> FeedbackState:
        """
        Preprocess text into paragraphs.

        Args:
            state: Current state with input text

        Returns:
            Updated state with preprocessed paragraphs
        """
        try:
            logger.info("LangGraph: Preprocessing text")

            paragraphs = self.text_preprocessor.preprocess_text(state['input_text'])
            stats = self.text_preprocessor.get_paragraph_stats(paragraphs)

            state['paragraphs'] = paragraphs
            state['error'] = None

            logger.info(f"LangGraph: Preprocessed {len(paragraphs)} paragraphs")
            return state

        except Exception as e:
            logger.error(f"LangGraph: Preprocessing failed: {str(e)}")
            state['error'] = f"Preprocessing failed: {str(e)}"
            return state

    def _check_plagiarism_node(self, state: FeedbackState) -> FeedbackState:
        """
        Check for plagiarism patterns.

        Args:
            state: Current state with preprocessed paragraphs

        Returns:
            Updated state with plagiarism analysis results
        """
        try:
            logger.info("LangGraph: Checking plagiarism patterns")

            plagiarism_result = self.plagiarism_checker.check_text(
                state['input_text'],
                state['paragraphs']
            )

            state['plagiarism_result'] = plagiarism_result
            state['error'] = None

            logger.info(f"LangGraph: Plagiarism check completed: {plagiarism_result.risk_level} risk level")
            return state

        except Exception as e:
            logger.error(f"LangGraph: Plagiarism check failed: {str(e)}")
            # Return low risk result on error to avoid breaking the pipeline
            from .plagiarism_checker import PlagiarismResult
            state['plagiarism_result'] = PlagiarismResult(
                risk_level='low',
                flags=[],
                note='Plagiarism check failed, defaulting to low risk'
            )
            return state

    def _retrieve_rubric_node(self, state: FeedbackState) -> FeedbackState:
        """
        Retrieve rubric using RAG.

        Args:
            state: Current state with assignment type

        Returns:
            Updated state with retrieved rubric data
        """
        try:
            logger.info("LangGraph: Retrieving rubric (RAG)")

            rubric = self.rag_service.retrieve_rubric(
                state['assignment_type'],
                state.get('rubric_id')
            )

            if not rubric:
                state['error'] = f"No rubric found for {state['assignment_type']}"
                return state

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

            state['rubric_data'] = rubric_data
            state['error'] = None

            logger.info(f"LangGraph: Retrieved rubric: {rubric.name}")
            return state

        except Exception as e:
            logger.error(f"LangGraph: Rubric retrieval failed: {str(e)}")
            state['error'] = f"Rubric retrieval failed: {str(e)}"
            return state

    def _generate_feedback_node(self, state: FeedbackState) -> FeedbackState:
        """
        Generate feedback using RAG-enhanced LLM.

        Args:
            state: Current state with paragraphs and rubric

        Returns:
            Updated state with feedback results
        """
        try:
            logger.info("LangGraph: Generating feedback with RAG")

            if not state['rubric_data']:
                state['error'] = "No rubric data available for feedback generation"
                return state

            # Generate RAG-based feedback using existing service
            from .models import Rubric
            rubric = Rubric.objects.get(id=state['rubric_data']['id'])

            feedback_result = self.rag_service.generate_document_rubric_feedback(
                paragraphs=state['paragraphs'],
                assignment_type=state['assignment_type'],
                rubric_id=state['rubric_data']['id'],
                context=state.get('context')
            )

            state['feedback_results'] = feedback_result
            state['error'] = None

            logger.info("LangGraph: Feedback generation completed")
            return state

        except Exception as e:
            logger.error(f"LangGraph: Feedback generation failed: {str(e)}")
            state['error'] = f"Feedback generation failed: {str(e)}"
            return state

    def _combine_output_node(self, state: FeedbackState) -> FeedbackState:
        """
        Combine results into final structured output.

        Args:
            state: Current state with feedback results

        Returns:
            Updated state with final output
        """
        try:
            logger.info("LangGraph: Creating final output")

            if not state['feedback_results']:
                state['error'] = "No feedback results available"
                return state

            # Extract rubric scores from feedback results
            overall_score_data = state['feedback_results'].get('overall_score', {})
            total_points = overall_score_data.get('total_points', 0)
            max_points = overall_score_data.get('max_points', 0)
            percentage = overall_score_data.get('percentage', 0)

            # Create paragraph feedback array
            paragraph_feedback = []
            all_strengths = []
            all_improvements = []

            for feedback in state['feedback_results'].get('paragraph_feedback', []):
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
            suggestions = self._generate_recommendations(percentage, all_improvements, state.get('plagiarism_result'))

            # Create final output with required structure
            final_output = {
                'paragraph_feedback': paragraph_feedback,
                'rubric_scores': rubric_scores,
                'overall_feedback': overall_feedback,
                'suggestions': suggestions
            }

            # Add plagiarism results if available
            if state.get('plagiarism_result'):
                final_output['plagiarism_analysis'] = self.plagiarism_checker.to_dict(state['plagiarism_result'])

            state['final_output'] = final_output
            state['error'] = None

            logger.info("LangGraph: Final output created")
            return state

        except Exception as e:
            logger.error(f"LangGraph: Output combination failed: {str(e)}")
            state['error'] = f"Output combination failed: {str(e)}"
            return state

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
            recommendations.append("Review grammar and writing style for clarity and professionalism")

        # Add academic integrity suggestions if plagiarism risk is medium/high
        if plagiarism_result and plagiarism_result.risk_level in ['medium', 'high']:
            recommendations.append("Review your work to ensure all sources are properly cited and attributed")
            recommendations.append("Consider using quotation marks for direct quotes and paraphrasing appropriately")
            if plagiarism_result.risk_level == 'high':
                recommendations.append("Please review academic integrity guidelines and ensure proper attribution of all sources")

        return recommendations[:5]  # Limit to top 5 recommendations

    def process(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main orchestration method using LangGraph.

        This method provides the same external interface as the original
        FeedbackGenerationAgent.process() but uses LangGraph internally.

        Args:
            agent_input: Input data containing text and assignment details

        Returns:
            Dictionary with complete feedback and scores (same structure as original)
        """
        try:
            logger.info(f"Starting LangChain feedback generation for {agent_input.get('assignment_type')}")

            # Use LangGraph if available and enabled
            if self.graph and self.config.enable_langgraph:
                return self._process_with_langgraph(agent_input)
            else:
                # Fallback to original implementation
                logger.info("Using fallback implementation (LangGraph not available)")
                return self._process_with_fallback(agent_input)

        except Exception as e:
            logger.error(f"Error in LangChain agent processing: {str(e)}")
            return {
                'success': False,
                'rubric': {},
                'preprocessed_data': {},
                'feedback_results': {},
                'final_output': {},
                'error_message': f"Processing failed: {str(e)}"
            }

    def _process_with_langgraph(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process using LangGraph state graph."""
        try:
            # Initialize state
            initial_state: FeedbackState = {
                'input_text': agent_input.get('text', ''),
                'assignment_type': agent_input.get('assignment_type', ''),
                'context': agent_input.get('context'),
                'rubric_id': agent_input.get('rubric_id'),
                'model': agent_input.get('model', self.config.default_model),
                'paragraphs': [],
                'rubric_data': None,
                'feedback_results': None,
                'plagiarism_result': None,
                'final_output': None,
                'error': None
            }

            # Compile and execute graph
            compiled_graph = self.graph.compile()
            final_state = compiled_graph.invoke(initial_state)

            # Check for errors
            if final_state.get('error'):
                return {
                    'success': False,
                    'rubric': final_state.get('rubric_data', {}),
                    'preprocessed_data': {'paragraphs': final_state.get('paragraphs', [])},
                    'feedback_results': {},
                    'final_output': {},
                    'error_message': final_state.get('error')
                }

            # Return results in same format as original
            return {
                'success': True,
                'rubric': final_state.get('rubric_data', {}),
                'preprocessed_data': {
                    'paragraphs': final_state.get('paragraphs', []),
                    'statistics': self.text_preprocessor.get_paragraph_stats(final_state.get('paragraphs', [])),
                    'original_text_length': len(agent_input.get('text', ''))
                },
                'feedback_results': final_state.get('feedback_results', {}),
                'final_output': final_state.get('final_output', {})
            }

        except Exception as e:
            logger.error(f"LangGraph execution failed: {str(e)}")
            return {
                'success': False,
                'rubric': {},
                'preprocessed_data': {},
                'feedback_results': {},
                'final_output': {},
                'error_message': f"LangGraph execution failed: {str(e)}"
            }

    def _process_with_fallback(self, agent_input: Dict[str, Any]) -> Dict[str, Any]:
        """Process using original implementation as fallback."""
        try:
            # Import original agent
            from .feedback_agent import FeedbackGenerationAgent, AgentInput

            # Create original agent input
            original_input = AgentInput(
                text=agent_input.get('text', ''),
                assignment_type=agent_input.get('assignment_type', ''),
                context=agent_input.get('context'),
                rubric_id=agent_input.get('rubric_id'),
                model=agent_input.get('model', self.config.default_model)
            )

            # Create and use original agent
            original_agent = FeedbackGenerationAgent(llm_client=self.llm_client)
            original_output = original_agent.process(original_input)

            # Convert to dictionary format
            return {
                'success': original_output.success,
                'rubric': original_output.rubric,
                'preprocessed_data': original_output.preprocessed_data,
                'feedback_results': original_output.feedback_results,
                'final_output': original_output.final_output,
                'error_message': original_output.error_message
            }

        except Exception as e:
            logger.error(f"Fallback processing failed: {str(e)}")
            return {
                'success': False,
                'rubric': {},
                'preprocessed_data': {},
                'feedback_results': {},
                'final_output': {},
                'error_message': f"Fallback processing failed: {str(e)}"
            }


# Global agent instance
_langchain_agent: Optional[LangChainFeedbackAgent] = None

def get_langchain_agent() -> Optional[LangChainFeedbackAgent]:
    """Get global LangChain feedback agent instance."""
    global _langchain_agent
    if _langchain_agent is None:
        try:
            _langchain_agent = LangChainFeedbackAgent()
            logger.info("Global LangChain agent created")
        except Exception as e:
            logger.error(f"Failed to create LangChain agent: {str(e)}")
            _langchain_agent = None
    return _langchain_agent

def reset_langchain_agent() -> None:
    """Reset global LangChain agent instance."""
    global _langchain_agent
    _langchain_agent = None
