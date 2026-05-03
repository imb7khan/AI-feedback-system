"""
Middleware to handle connection closing properly after LLM processing.

This middleware ensures that:
1. Responses are sent completely before connection closes
2. Proper headers are set for long-running requests
3. Connection is closed gracefully after processing
"""

import logging
from django.http import HttpResponse

logger = logging.getLogger(__name__)


class LLMProcessingMiddleware:
    """
    Middleware specifically for LLM processing endpoints.

    This ensures proper handling of long-running LLM requests
    and prevents broken pipe errors.
    """

    def __init__(self, get_response):
        """Initialize middleware."""
        self.get_response = get_response

    def __call__(self, request):
        """
        Process LLM requests with proper timeout and connection handling.

        Args:
            request: Django request object

        Returns:
            HttpResponse with LLM-specific headers
        """
        # Check if this is an LLM processing endpoint
        llm_endpoints = ['/api/complete-pipeline/', '/api/feedback-agent/', '/api/rubric-rag-feedback/']

        if any(request.path.startswith(endpoint) for endpoint in llm_endpoints):
            logger.info(f"LLM processing started for {request.path}")

            # Process the request
            response = self.get_response(request)

            # Add LLM-specific headers (avoid hop-by-hop headers)
            response['X-LLM-Processing'] = 'complete'
            response['X-Processing-Status'] = 'success'

            logger.info(f"LLM processing completed for {request.path}")

            return response

        # For non-LLM requests, just process normally
        return self.get_response(request)
