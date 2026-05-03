from rest_framework import generics, views
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from django.core.files.uploadedfile import UploadedFile
import logging

from .models import AssignmentSubmission
from .serializers import AssignmentSubmissionSerializer
from .text_extraction import TextExtractor, TextExtractionError
from .text_preprocessing import TextPreprocessor
from .llm_integration import GroqLLMClient, LLMIntegrationError, ParagraphFeedback

logger = logging.getLogger(__name__)


class AssignmentSubmissionListCreateView(generics.ListCreateAPIView):
    """
    API view for listing and creating assignment submissions.
    GET: List all submissions
    POST: Upload new file and create submission
    """
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentSubmissionSerializer

    def create(self, request, *args, **kwargs):
        """Override create to handle file upload with custom response."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data,
            status=status.HTTP_201_CREATED,
            headers=headers
        )


class AssignmentSubmissionDetailView(generics.RetrieveAPIView):
    """
    API view for retrieving a specific assignment submission.
    GET: Get specific submission details
    """
    queryset = AssignmentSubmission.objects.all()
    serializer_class = AssignmentSubmissionSerializer
    lookup_field = 'id'


class TextExtractionView(views.APIView):
    """
    API view for extracting text from uploaded files.
    POST: Extract text from uploaded file
    """
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, *args, **kwargs):
        """
        Extract text from uploaded file.

        Request body should contain:
        - file: The file to extract text from

        Returns:
        - JSON response with extracted text or error message
        """
        try:
            # Get the uploaded file
            file_obj = request.FILES.get('file')

            if not file_obj:
                return Response(
                    {'error': 'No file provided. Please upload a file.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate file size (max 10MB)
            max_size = 10 * 1024 * 1024  # 10MB
            if file_obj.size > max_size:
                return Response(
                    {'error': 'File size exceeds 10MB limit.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Determine file type
            file_extension = file_obj.name.split('.')[-1].lower()
            file_type_map = {
                'pdf': 'pdf',
                'docx': 'docx',
                'txt': 'txt'
            }

            if file_extension not in file_type_map:
                return Response(
                    {'error': f'Unsupported file type: {file_extension}. '
                              f'Supported types: PDF, DOCX, TXT'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            file_type = file_type_map[file_extension]

            # Save file temporarily for extraction
            import tempfile
            import os

            # Create temporary file
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=f'.{file_extension}'
            ) as temp_file:
                # Write uploaded file content to temp file
                for chunk in file_obj.chunks():
                    temp_file.write(chunk)
                temp_path = temp_file.name

            try:
                # Extract text
                extracted_text = TextExtractor.extract_text(temp_path, file_type)

                # Clean up temporary file
                os.unlink(temp_path)

                # Return extracted text
                return Response({
                    'success': True,
                    'file_name': file_obj.name,
                    'file_type': file_type,
                    'text': extracted_text,
                    'text_length': len(extracted_text)
                }, status=status.HTTP_200_OK)

            except TextExtractionError as e:
                # Clean up temporary file if it exists
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

                logger.error(f"Text extraction error: {str(e)}")
                return Response(
                    {'error': f'Text extraction failed: {str(e)}'},
                    status=status.HTTP_422_UNPROCESSABLE_ENTITY
                )

        except Exception as e:
            logger.error(f"Unexpected error during text extraction: {str(e)}")
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class TextPreprocessingView(views.APIView):
    """
    API view for preprocessing extracted text into paragraphs.
    POST: Preprocess text into clean paragraphs
    """

    def post(self, request, *args, **kwargs):
        """
        Preprocess text into clean paragraphs.

        Request body should contain:
        - text: The text to preprocess

        Returns:
        - JSON response with preprocessed paragraphs and statistics
        """
        try:
            # Get the text from request
            text = request.data.get('text')

            if not text:
                return Response(
                    {'error': 'No text provided. Please provide text to preprocess.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not isinstance(text, str):
                return Response(
                    {'error': 'Text must be a string.'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Preprocess the text
            paragraphs = TextPreprocessor.preprocess_text(text)

            # Get statistics
            stats = TextPreprocessor.get_paragraph_stats(paragraphs)

            # Return preprocessed paragraphs
            return Response({
                'success': True,
                'paragraphs': paragraphs,
                'statistics': stats
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Unexpected error during text preprocessing: {str(e)}")
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class FeedbackGenerationView(views.APIView):
    """
    API view for generating AI feedback on assignment text.
    POST: Generate paragraph-level feedback using Groq LLM
    """

    def post(self, request, *args, **kwargs):
        """
        Generate feedback for assignment paragraphs.

        Request body should contain:
        - paragraphs: List of paragraph strings
        - context: Optional context about the assignment
        - model: Optional Groq model name (default: llama-3.3-70b-versatile)

        Returns:
        - JSON response with paragraph-level feedback
        """
        try:
            # Get paragraphs from request
            paragraphs = request.data.get('paragraphs')

            if not paragraphs:
                return Response(
                    {'error': 'No paragraphs provided. Please provide paragraphs to analyze.'},
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

            # Get optional parameters
            context = request.data.get('context')
            model = request.data.get('model', 'llama-3.3-70b-versatile')

            # Initialize Groq client
            try:
                llm_client = GroqLLMClient(model=model)
            except LLMIntegrationError as e:
                logger.error(f"Failed to initialize Groq client: {str(e)}")
                return Response(
                    {'error': f'Failed to initialize AI service: {str(e)}'},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )

            # Generate feedback for all paragraphs
            try:
                feedback_list = llm_client.generate_document_feedback(
                    paragraphs=paragraphs,
                    context=context
                )

                # Convert feedback objects to dictionaries
                feedback_data = []
                for feedback in feedback_list:
                    feedback_data.append({
                        'paragraph_index': feedback.paragraph_index,
                        'paragraph_text': feedback.paragraph_text,
                        'feedback': feedback.feedback,
                        'strengths': feedback.strengths,
                        'improvements': feedback.improvements,
                        'score': feedback.score
                    })

                # Calculate overall statistics
                total_paragraphs = len(feedback_data)
                successful_feedback = sum(1 for f in feedback_data if f['feedback'])
                avg_score = None
                scores = [f['score'] for f in feedback_data if f['score'] is not None]
                if scores:
                    avg_score = sum(scores) / len(scores)

                return Response({
                    'success': True,
                    'model': model,
                    'total_paragraphs': total_paragraphs,
                    'successful_feedback': successful_feedback,
                    'average_score': avg_score,
                    'feedback': feedback_data
                }, status=status.HTTP_200_OK)

            except LLMIntegrationError as e:
                logger.error(f"Error generating feedback: {str(e)}")
                return Response(
                    {'error': f'Failed to generate feedback: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        except Exception as e:
            logger.error(f"Unexpected error during feedback generation: {str(e)}")
            return Response(
                {'error': f'An unexpected error occurred: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
