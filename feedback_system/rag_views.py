"""
API view for RAG-based rubric feedback generation.

This endpoint demonstrates simple RAG by retrieving rubrics from the database
and using them to generate structured feedback and scores.
"""

from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
import logging

from .rubric_rag import RubricRAGService, explain_rag_usage
from .llm_integration import LLMIntegrationError

logger = logging.getLogger(__name__)


class RubricRAGFeedbackView(views.APIView):
    """
    API view for generating RAG-based rubric feedback.

    This endpoint demonstrates simple RAG:
    1. Retrieves rubric from database
    2. Injects rubric into LLM prompt
    3. Generates rubric-aligned feedback and scores

    POST /api/rubric-rag-feedback/
    """

    def post(self, request, *args, **kwargs):
        """
        Generate RAG-based feedback using retrieved rubrics.

        Request body should contain:
        - paragraphs: List of paragraph strings to evaluate
        - assignment_type: Type of assignment (e.g., 'essay', 'research paper')
        - rubric_id: Optional specific rubric ID (overrides assignment_type)
        - context: Optional additional context about the assignment
        - model: Optional Groq model name (default: llama-3.3-70b-versatile)

        Returns:
        - JSON response with rubric information and structured feedback
        """
        try:
            # Get paragraphs from request
            paragraphs = request.data.get('paragraphs')

            if not paragraphs:
                return Response(
                    {'error': 'No paragraphs provided. Please provide paragraphs to evaluate.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not isinstance(paragraphs, list):
                return Response(
                    {'error': 'Paragraphs must be a list of strings.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate paragraphs
            if not all(isinstance(p, str) for p in paragraphs):
                return Response(
                    {'error': 'All paragraphs must be strings.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get required parameters
            assignment_type = request.data.get('assignment_type')
            if not assignment_type:
                return Response(
                    {'error': 'assignment_type is required. Specify the type of assignment (e.g., "essay").'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Get optional parameters
            rubric_id = request.data.get('rubric_id')
            context = request.data.get('context')
            model = request.data.get('model', 'llama-3.3-70b-versatile')

            # Initialize RAG service
            try:
                from .llm_integration import GroqLLMClient
                llm_client = GroqLLMClient(model=model)
                rag_service = RubricRAGService(llm_client=llm_client)
            except LLMIntegrationError as e:
                logger.error(f"Failed to initialize RAG service: {str(e)}")
                return Response(
                    {'error': f'Failed to initialize AI service: {str(e)}'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            # Generate RAG-based feedback
            try:
                feedback_result = rag_service.generate_document_rubric_feedback(
                    paragraphs=paragraphs,
                    assignment_type=assignment_type,
                    rubric_id=rubric_id,
                    context=context
                )

                return Response(feedback_result, status=status.HTTP_200_OK)

            except LLMIntegrationError as e:
                logger.error(f"Error generating RAG feedback: {str(e)}")
                return Response(
                    {'error': f'Failed to generate RAG feedback: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Unexpected error in RAG feedback generation: {str(e)}")
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RAGExplanationView(views.APIView):
    """
    API view for explaining how RAG is being used.

    GET /api/rag-explanation/
    """

    def get(self, request, *args, **kwargs):
        """
        Get explanation of RAG usage in this system.

        Returns:
        - Detailed explanation of RAG implementation
        """
        try:
            explanation = explain_rag_usage()

            return Response({
                'success': True,
                'explanation': explanation
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error generating RAG explanation: {str(e)}")
            return Response(
                {'error': f'Failed to generate explanation: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RubricRetrievalView(views.APIView):
    """
    API view for demonstrating rubric retrieval (RAG Step 1).

    GET /api/rubric-retrieval/?assignment_type=essay
    """

    def get(self, request, *args, **kwargs):
        """
        Retrieve rubric for given assignment type.

        Query parameters:
        - assignment_type: Type of assignment (required)
        - rubric_id: Optional specific rubric ID

        Returns:
        - Retrieved rubric information
        """
        try:
            assignment_type = request.query_params.get('assignment_type')
            rubric_id = request.query_params.get('rubric_id')

            if not assignment_type and not rubric_id:
                return Response(
                    {'error': 'Either assignment_type or rubric_id parameter is required.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Initialize RAG service
            rag_service = RubricRAGService()

            # Retrieve rubric
            rubric = rag_service.retrieve_rubric(
                assignment_type=assignment_type or '',
                rubric_id=rubric_id
            )

            if not rubric:
                return Response(
                    {'error': 'No rubric found for the given parameters.'},
                    status=status.HTTP_404_NOT_FOUND
                )

            # Format rubric for display
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
                        'max_points': criterion.max_points,
                        'performance_levels': []
                    }

                    for level in criterion.levels.all().order_by('-score_range_max'):
                        level_data = {
                            'level_name': level.level_name,
                            'score_range': f"{level.score_range_min}-{level.score_range_max}",
                            'description': level.description
                        }
                        criterion_data['performance_levels'].append(level_data)

                    category_data['criteria'].append(criterion_data)

                rubric_data['categories'].append(category_data)

            return Response({
                'success': True,
                'message': 'Rubric retrieved successfully (RAG Step 1: RETRIEVAL)',
                'rubric': rubric_data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error retrieving rubric: {str(e)}")
            return Response(
                {'error': f'Failed to retrieve rubric: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )