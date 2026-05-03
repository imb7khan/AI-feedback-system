"""
End-to-end pipeline views for complete assignment feedback workflow.

This module provides unified API endpoints that connect all components:
Upload → Extract → Split → Agent → Output
"""

from rest_framework import views
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.renderers import JSONRenderer
from django.http import StreamingHttpResponse
import logging
import tempfile
import os
import json
import time

from .models import AssignmentSubmission
from .serializers import AssignmentSubmissionSerializer
from .text_extraction import TextExtractor, TextExtractionError
from .text_preprocessing import TextPreprocessor
from .feedback_agent import FeedbackGenerationAgent, AgentInput, AgentOutput
from .llm_integration import GroqLLMClient, LLMIntegrationError
from .json_validator import JSONValidator

logger = logging.getLogger(__name__)


class StreamingJSONRenderer(JSONRenderer):
    """
    Custom JSON renderer that handles large responses more efficiently
    to prevent broken pipe errors.
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        """Render data with optimized JSON handling."""
        try:
            # Use separators to reduce response size
            return json.dumps(
                data,
                cls=self.encoder_class,
                ensure_ascii=False,
                separators=(',', ':')  # Compact JSON format
            ).encode('utf-8')
        except (TypeError, ValueError) as e:
            logger.error(f"JSON rendering error: {str(e)}")
            return json.dumps({'error': 'Failed to render response'}).encode('utf-8')


class CompletePipelineView(views.APIView):
    """
    End-to-end pipeline for complete assignment feedback workflow.

    This endpoint handles the complete workflow:
    1. Upload file
    2. Extract text
    3. Split into paragraphs
    4. Process with agent
    5. Return structured output

    POST /api/complete-pipeline/
    """
    parser_classes = [MultiPartParser, FormParser]
    renderer_classes = [StreamingJSONRenderer]

    def post(self, request, *args, **kwargs):
        """
        Process complete assignment feedback pipeline.

        Request body should contain:
        - file: The assignment file (PDF, DOCX, TXT)
        - assignment_type: Type of assignment (e.g., 'essay', 'research paper')
        - context: Optional additional context about the assignment
        - rubric_id: Optional specific rubric ID
        - model: Optional Groq model name (default: llama-3.3-70b-versatile)
        - save_submission: Optional boolean to save submission (default: true)

        Returns:
        - Complete feedback with scores, analysis, and recommendations
        """
        try:
            # Step 1: Upload and validate file
            logger.info("Step 1: Upload and validate file")
            file_obj = request.FILES.get('file')

            if not file_obj:
                return Response({
                    'success': False,
                    'error': 'No file provided. Please upload a file.',
                    'pipeline_status': {
                        'step': 'upload',
                        'status': 'failed',
                        'message': 'File upload failed'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            # Validate file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file_obj.size > max_size:
                return Response({
                    'success': False,
                    'error': 'File size exceeds 10MB limit.',
                    'pipeline_status': {
                        'step': 'upload',
                        'status': 'failed',
                        'message': 'File size validation failed'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            # Determine file type
            file_extension = file_obj.name.split('.')[-1].lower()
            file_type_map = {
                'pdf': 'pdf',
                'docx': 'docx',
                'txt': 'txt'
            }

            if file_extension not in file_type_map:
                return Response({
                    'success': False,
                    'error': f'Unsupported file type: {file_extension}. '
                             f'Supported types: PDF, DOCX, TXT',
                    'pipeline_status': {
                        'step': 'upload',
                        'status': 'failed',
                        'message': 'File type validation failed'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            file_type = file_type_map[file_extension]

            # Get assignment parameters
            assignment_type = request.data.get('assignment_type')
            if not assignment_type:
                return Response({
                    'success': False,
                    'error': 'assignment_type is required. Specify the type of assignment (e.g., "essay").',
                    'pipeline_status': {
                        'step': 'upload',
                        'status': 'failed',
                        'message': 'Missing assignment_type parameter'
                    }
                }, status=status.HTTP_400_BAD_REQUEST)

            context = request.data.get('context')
            rubric_id = request.data.get('rubric_id')
            model = request.data.get('model', 'llama-3.3-70b-versatile')
            save_submission_raw = request.data.get('save_submission', True)
            if isinstance(save_submission_raw, str):
                save_submission = save_submission_raw.strip().lower() in ('1', 'true', 'yes', 'on')
            else:
                save_submission = bool(save_submission_raw)

            # Step 2: Extract text from file
            logger.info("Step 2: Extract text from file")

            # Save file temporarily for extraction
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=f'.{file_extension}'
            ) as temp_file:
                # Write uploaded file content to temp file
                for chunk in file_obj.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            try:
                extracted_text = TextExtractor.extract_text(temp_path, file_type)

                if not extracted_text or len(extracted_text.strip()) == 0:
                    return Response({
                        'success': False,
                        'error': 'No text could be extracted from the file.',
                        'pipeline_status': {
                            'step': 'extraction',
                            'status': 'failed',
                            'message': 'Text extraction returned empty result'
                        }
                    }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

                logger.info(f"Extracted {len(extracted_text)} characters from file")

            except TextExtractionError as e:
                # Clean up temporary file if it exists
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

                logger.error(f"Text extraction error: {str(e)}")
                return Response({
                    'success': False,
                    'error': f'Text extraction failed: {str(e)}',
                    'pipeline_status': {
                        'step': 'extraction',
                        'status': 'failed',
                        'message': str(e)
                    }
                }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

            finally:
                # Clean up temporary file
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

            # Step 3: Split text into paragraphs
            logger.info("Step 3: Split text into paragraphs")

            try:
                text_preprocessor = TextPreprocessor()
                paragraphs = text_preprocessor.preprocess_text(extracted_text)
                stats = text_preprocessor.get_paragraph_stats(paragraphs)

                if not paragraphs:
                    return Response({
                        'success': False,
                        'error': 'No paragraphs could be created from the extracted text.',
                        'pipeline_status': {
                            'step': 'preprocessing',
                            'status': 'failed',
                            'message': 'Paragraph splitting returned empty result'
                        }
                    }, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

                logger.info(f"Created {len(paragraphs)} paragraphs")

            except Exception as e:
                logger.error(f"Text preprocessing error: {str(e)}")
                return Response({
                    'success': False,
                    'error': f'Text preprocessing failed: {str(e)}',
                    'pipeline_status': {
                        'step': 'preprocessing',
                        'status': 'failed',
                        'message': str(e)
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Step 4: Process with agent
            logger.info("Step 4: Process with agent")

            try:
                # Initialize LLM client with extended timeout
                llm_client = GroqLLMClient(model=model)

                # Initialize agent
                agent = FeedbackGenerationAgent(llm_client=llm_client)

                # Create agent input
                agent_input = AgentInput(
                    text=extracted_text,
                    assignment_type=assignment_type,
                    context=context,
                    rubric_id=rubric_id,
                    model=model
                )

                logger.info("Starting agent processing (this may take 1-2 minutes)...")

                # Process using agent (thread-safe: avoid signal-based timeout,
                # which crashes under Django's threaded request handling).
                agent_output = agent.process(agent_input)

                if not agent_output.success:
                    error_response = {
                        'success': False,
                        'error': agent_output.error_message,
                        'pipeline_status': {
                            'step': 'agent_processing',
                            'status': 'failed',
                            'message': agent_output.error_message
                        }
                    }
                    # Validate error response format
                    JSONValidator.ensure_json_serializable(error_response)
                    return Response(error_response, status=status.HTTP_422_UNPROCESSABLE_ENTITY)

                logger.info("Agent processing completed successfully")

            except LLMIntegrationError as e:
                logger.error(f"Error in agent processing: {str(e)}")
                error_response = {
                    'success': False,
                    'error': f'Agent processing failed: {str(e)}',
                    'pipeline_status': {
                        'step': 'agent_processing',
                        'status': 'failed',
                        'message': str(e)
                    }
                }
                JSONValidator.ensure_json_serializable(error_response)
                return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # Step 5: Validate and format output
            logger.info("Step 5: Validate and format output")

            try:
                # Validate final output structure
                validation_result = JSONValidator.validate_structure(agent_output.final_output)

                if not validation_result.is_valid:
                    logger.error(f"JSON validation failed: {validation_result.errors}")
                    return Response({
                        'success': False,
                        'error': 'Invalid response format',
                        'pipeline_status': {
                            'step': 'output_validation',
                            'status': 'failed',
                            'message': 'JSON structure validation failed'
                        },
                        'validation_errors': validation_result.errors
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

                # Save submission if requested
                submission_id = None
                if save_submission:
                    try:
                        # Create submission with correct model fields
                        # Don't store full extracted_text to avoid large JSON objects
                        submission = AssignmentSubmission.objects.create(
                            file=file_obj,
                            file_type=file_type,
                            original_filename=file_obj.name,
                            status='completed',
                            feedback_data={
                                'assignment_type': assignment_type,
                                'text_length': len(extracted_text),
                                'context': context,
                                'rubric_id': rubric_id,
                                'model': model,
                                'paragraph_count': len(paragraphs),
                                'processing_result': agent_output.final_output
                            }
                        )
                        submission_id = submission.id
                        logger.info(f"Saved submission with ID: {submission_id}")
                    except Exception as e:
                        logger.warning(f"Failed to save submission: {str(e)}")
                        # Continue without saving submission

                # Create optimized final response to prevent broken pipe
                # Truncate long text fields to reduce response size
                optimized_feedback = []
                for feedback in agent_output.final_output.get('paragraph_feedback', []):
                    paragraph_text = feedback.get('paragraph_text') or feedback.get('text', '')
                    optimized_feedback.append({
                        'paragraph_index': feedback.get('paragraph_index'),
                        'text': paragraph_text[:200] + '...' if len(paragraph_text) > 200 else paragraph_text,
                        'overall_feedback': feedback.get('overall_feedback', ''),
                        'total_score': feedback.get('total_score', 0),
                        'max_score': feedback.get('max_score', 0),
                        'strengths': feedback.get('strengths', [])[:3],  # Limit to top 3
                        'improvements': feedback.get('improvements', [])[:3]  # Limit to top 3
                    })

                final_response = {
                    'success': True,
                    'pipeline_status': {
                        'step': 'complete',
                        'status': 'success',
                        'message': 'All pipeline steps completed successfully',
                        'llm_processing_complete': True,
                        'ready_to_close': True
                    },
                    'processing_info': {
                        'file_name': file_obj.name,
                        'file_type': file_type,
                        'assignment_type': assignment_type,
                        'text_length': len(extracted_text),
                        'paragraph_count': len(paragraphs),
                        'model_used': model,
                        'submission_id': submission_id,
                        'processing_complete': True
                    },
                    'paragraph_feedback': optimized_feedback,
                    'rubric_scores': agent_output.final_output.get('rubric_scores', {}),
                    'overall_feedback': agent_output.final_output.get('overall_feedback', {}),
                    'suggestions': agent_output.final_output.get('suggestions', [])[:5],  # Limit to top 5
                    'plagiarism_analysis': agent_output.final_output.get('plagiarism_analysis'),
                    '_signal': 'PROCESSING_COMPLETE_READY_TO_CLOSE',
                    '_response_size': 'optimized'
                }

                # Ensure JSON serializable and send response
                JSONValidator.ensure_json_serializable(final_response)

                logger.info("Pipeline completed successfully, sending response")

                # Use regular Response instead of StreamingHttpResponse for better compatibility
                # The optimized response size should prevent timeout issues
                return Response(final_response, status=status.HTTP_200_OK)

            except Exception as e:
                logger.error(f"Error in output formatting: {str(e)}")
                return Response({
                    'success': False,
                    'error': f'Output formatting failed: {str(e)}',
                    'pipeline_status': {
                        'step': 'output_validation',
                        'status': 'failed',
                        'message': str(e)
                    }
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        except Exception as e:
            logger.error(f"Unexpected error in pipeline: {str(e)}")
            return Response({
                'success': False,
                'error': f'An unexpected error occurred: {str(e)}',
                'pipeline_status': {
                    'step': 'unknown',
                    'status': 'failed',
                    'message': 'Unexpected error during pipeline execution'
                }
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class PipelineStatusView(views.APIView):
    """
    API view for getting pipeline status and information.

    GET /api/pipeline-status/
    """

    def get(self, request, *args, **kwargs):
        """
        Get pipeline status and capabilities.

        Returns:
        - Pipeline information and available features
        """
        try:
            pipeline_info = {
                'success': True,
                'pipeline_name': 'Complete Assignment Feedback Pipeline',
                'version': '1.0.0',
                'description': 'End-to-end workflow for automated assignment feedback generation',
                'workflow_steps': [
                    {
                        'step': 1,
                        'name': 'Upload & Validate',
                        'description': 'Upload file and validate format/size',
                        'supported_formats': ['PDF', 'DOCX', 'TXT'],
                        'max_file_size': '10MB'
                    },
                    {
                        'step': 2,
                        'name': 'Extract Text',
                        'description': 'Extract text content from uploaded file',
                        'extraction_libraries': ['PyPDF2', 'python-docx']
                    },
                    {
                        'step': 3,
                        'name': 'Split Paragraphs',
                        'description': 'Split extracted text into clean paragraphs',
                        'preprocessing_features': ['Whitespace cleaning', 'Paragraph detection']
                    },
                    {
                        'step': 4,
                        'name': 'Agent Processing',
                        'description': 'Process paragraphs with AI agent for feedback generation',
                        'agent_type': 'Single Orchestrator Agent',
                        'llm_provider': 'Groq',
                        'supported_models': ['llama-3.3-70b-versatile', 'mixtral-8x7b-32768', 'gemma-7b-it']
                    },
                    {
                        'step': 5,
                        'name': 'Output Generation',
                        'description': 'Generate structured JSON output with scores and feedback',
                        'output_format': 'Strict JSON',
                        'validation': 'Schema-based validation'
                    }
                ],
                'features': {
                    'file_upload': True,
                    'text_extraction': True,
                    'paragraph_splitting': True,
                    'rubric_retrieval': True,
                    'ai_feedback': True,
                    'score_calculation': True,
                    'json_validation': True,
                    'submission_storage': True
                },
                'api_endpoints': {
                    'complete_pipeline': '/api/complete-pipeline/',
                    'pipeline_status': '/api/pipeline-status/',
                    'feedback_agent': '/api/feedback-agent/',
                    'text_extraction': '/api/extract-text/',
                    'text_preprocessing': '/api/preprocess-text/',
                    'rubric_management': '/api/rubrics/'
                },
                'requirements': {
                    'file': 'Required (PDF, DOCX, or TXT)',
                    'assignment_type': 'Required (e.g., "essay", "research paper")',
                    'context': 'Optional (additional assignment context)',
                    'rubric_id': 'Optional (specific rubric to use)',
                    'model': 'Optional (default: llama-3.3-70b-versatile)',
                    'save_submission': 'Optional (default: true)'
                },
                'output_structure': {
                    'paragraph_feedback': 'Array of paragraph-level feedback',
                    'rubric_scores': 'Overall scoring information',
                    'overall_feedback': 'Summary assessment',
                    'suggestions': 'Actionable recommendations'
                }
            }

            # Ensure JSON serializable
            JSONValidator.ensure_json_serializable(pipeline_info)

            return Response(pipeline_info, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting pipeline status: {str(e)}")
            error_response = {
                'success': False,
                'error': f'Failed to get pipeline status: {str(e)}'
            }
            JSONValidator.ensure_json_serializable(error_response)
            return Response(error_response, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
