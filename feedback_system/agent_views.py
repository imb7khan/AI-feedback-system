"""
API view for the single feedback generation agent.

This endpoint provides a simple interface to the agent that orchestrates
the complete workflow: text preprocessing, rubric retrieval, LLM feedback,
and result integration.
"""

from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
import logging
import json

from .feedback_agent import (
    FeedbackGenerationAgent,
    AgentInput,
    AgentOutput,
    explain_agent_architecture
)
from .langchain_integration import LangChainFeedbackAgent, get_langchain_agent
from .llm_integration import LLMIntegrationError
from .json_validator import JSONValidator

logger = logging.getLogger(__name__)


class FeedbackAgentView(views.APIView):
    """
    API view for the single feedback generation agent.

    This endpoint demonstrates the simple orchestrator agent pattern:
    - Takes essay paragraphs as input
    - Coordinates all workflow components
    - Returns comprehensive feedback and scores

    POST /api/feedback-agent/
    """

    def post(self, request, *args, **kwargs):
        """
        Process feedback generation using the single agent.

        Request body should contain:
        - text: The essay text to analyze
        - assignment_type: Type of assignment (e.g., 'essay', 'research paper')
        - context: Optional additional context about the assignment
        - rubric_id: Optional specific rubric ID
        - model: Optional Groq model name (default: llama-3.3-70b-versatile)

        Returns:
        - Complete feedback with scores, analysis, and recommendations
        """
        try:
            # Get required parameters
            text = request.data.get('text')
            assignment_type = request.data.get('assignment_type')

            if not text:
                return Response(
                    {'error': 'No text provided. Please provide essay text to analyze.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not assignment_type:
                return Response(
                    {'error': 'assignment_type is required. Specify the type of assignment (e.g., "essay").'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get optional parameters
            context = request.data.get('context')
            rubric_id = request.data.get('rubric_id')
            model = request.data.get('model', 'llama-3.3-70b-versatile')

            # Try to use LangChain agent first
            try:
                langchain_agent = get_langchain_agent()
                if langchain_agent:
                    logger.info("Using LangChain agent for feedback generation")
                    agent_input_dict = {
                        'text': text,
                        'assignment_type': assignment_type,
                        'context': context,
                        'rubric_id': rubric_id,
                        'model': model
                    }
                    result = langchain_agent.process(agent_input_dict)

                    if result.get('success'):
                        # Return final_output directly (same structure as original)
                        return Response(result['final_output'], status=status.HTTP_200_OK)
                    else:
                        error_response = {
                            'success': False,
                            'error': result.get('error_message', 'LangChain agent processing failed')
                        }
                        JSONValidator.ensure_json_serializable(error_response)
                        return Response(error_response, status=status.HTTP_422_UNPROCESSABLE_ENTITY)
            except Exception as e:
                logger.warning(f"LangChain agent failed, falling back to original agent: {str(e)}")

            # Fallback to original agent
            logger.info("Using original FeedbackGenerationAgent")
            try:
                from .llm_integration import GroqLLMClient
                llm_client = GroqLLMClient(model=model)
                agent = FeedbackGenerationAgent(llm_client=llm_client)
            except LLMIntegrationError as e:
                logger.error(f"Failed to initialize agent: {str(e)}")
                return Response(
                    {'error': f'Failed to initialize AI service: {str(e)}'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            # Create agent input
            agent_input = AgentInput(
                text=text,
                assignment_type=assignment_type,
                context=context,
                rubric_id=rubric_id,
                model=model
            )

            # Process using agent
            try:
                agent_output = agent.process(agent_input)

                if not agent_output.success:
                    error_response = {
                        'success': False,
                        'error': agent_output.error_message
                    }
                    # Validate error response format
                    JSONValidator.ensure_json_serializable(error_response)
                    return Response(error_response, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

                # Validate final output structure
                validation_result = JSONValidator.validate_structure(agent_output.final_output)

                if not validation_result.is_valid:
                    logger.error(f"JSON validation failed: {validation_result.errors}")
                    return Response({
                        'success': False,
                        'error': 'Invalid response format',
                        'validation_errors': validation_result.errors
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # Return strict JSON response
                return Response(agent_output.final_output, status=status.HTTP_200_OK)

            except LLMIntegrationError as e:
                logger.error(f"Error in agent processing: {str(e)}")
                error_response = {
                    'success': False,
                    'error': f'Agent processing failed: {str(e)}'
                }
                JSONValidator.ensure_json_serializable(error_response)
                return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Unexpected error in agent endpoint: {str(e)}")
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AgentArchitectureView(views.APIView):
    """
    API view for explaining the agent architecture.

    GET /api/agent-architecture/
    """

    def get(self, request, *args, **kwargs):
        """
        Get detailed explanation of the agent architecture.

        Returns:
        - Comprehensive explanation of the single agent design
        """
        try:
            explanation = explain_agent_architecture()

            response_data = {
                'success': True,
                'architecture_explanation': explanation
            }

            # Ensure JSON serializable
            JSONValidator.ensure_json_serializable(response_data)

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating architecture explanation: {str(e)}")
            error_response = {
                'success': False,
                'error': f'Failed to generate explanation: {str(e)}'
            }
            JSONValidator.ensure_json_serializable(error_response)
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AgentWorkflowView(views.APIView):
    """
    API view for getting agent workflow information.

    GET /api/agent-workflow/
    """

    def get(self, request, *args, **kwargs):
        """
        Get summary of the agent's workflow and capabilities.

        Returns:
        - Workflow steps, components, and design principles
        """
        try:
            # Initialize agent (without LLM client for workflow info)
            agent = FeedbackGenerationAgent()

            workflow_summary = agent.get_workflow_summary()

            response_data = {
                'success': True,
                'workflow_summary': workflow_summary
            }

            # Ensure JSON serializable
            JSONValidator.ensure_json_serializable(response_data)

            return Response(response_data, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting workflow summary: {str(e)}")
            error_response = {
                'success': False,
                'error': f'Failed to get workflow summary: {str(e)}'
            }
            JSONValidator.ensure_json_serializable(error_response)
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)