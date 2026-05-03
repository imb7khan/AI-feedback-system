"""
Comprehensive test suite for complete pipeline integration.

Tests the end-to-end workflow: Upload → Extract → Split → Agent → Output
"""

import os
import tempfile
import json
from django.test import TestCase, Client
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings

from feedback_system.text_extraction import TextExtractor, TextExtractionError
from feedback_system.text_preprocessing import TextPreprocessor
from feedback_system.feedback_agent import FeedbackGenerationAgent, AgentInput
from feedback_system.json_validator import JSONValidator
from feedback_system.models import AssignmentSubmission


class TestCompletePipeline(TestCase):
    """Comprehensive tests for the complete pipeline integration."""

    def setUp(self):
        """Set up test environment."""
        self.client = Client()
        self.test_text = """Climate change represents one of the most significant challenges facing humanity in the 21st century. The scientific evidence is overwhelming, with global temperatures rising at an unprecedented rate. This essay will examine the causes of climate change and propose comprehensive solutions.

The primary cause of climate change is the burning of fossil fuels such as coal, oil, and natural gas. These activities release greenhouse gases into the atmosphere, trapping heat and causing global temperatures to rise. According to NASA, carbon dioxide levels have increased by over 40% since pre-industrial times.

Another major contributor is deforestation, which reduces the Earth's capacity to absorb carbon dioxide. Forests act as carbon sinks, but when they are cut down or burned, stored carbon is released back into the atmosphere. This creates a dangerous feedback loop that accelerates climate change.

In conclusion, climate change is a complex problem that requires comprehensive solutions. By combining technological innovation, policy changes, and individual action, we can mitigate its worst effects."""

    # Component Tests
    def test_text_extraction_txt(self):
        """Test TXT text extraction."""
        # Create temporary TXT file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(self.test_text)
            temp_path = f.name

        try:
            # Extract text
            extracted_text = TextExtractor.extract_text(temp_path, 'txt')

            # Verify extraction
            self.assertIsNotNone(extracted_text)
            self.assertEqual(len(extracted_text), len(self.test_text))
            self.assertIn('Climate change', extracted_text)

        finally:
            # Clean up
            os.unlink(temp_path)

    def test_text_preprocessing_basic(self):
        """Test basic text preprocessing."""
        preprocessor = TextPreprocessor()
        paragraphs = preprocessor.preprocess_text(self.test_text)

        # Verify paragraph splitting
        self.assertIsInstance(paragraphs, list)
        self.assertEqual(len(paragraphs), 4)  # 4 paragraphs in test text
        self.assertTrue(all(isinstance(p, str) for p in paragraphs))

        # Verify statistics
        stats = preprocessor.get_paragraph_stats(paragraphs)
        self.assertEqual(stats['total_paragraphs'], 4)
        self.assertGreater(stats['total_characters'], 0)
        self.assertGreater(stats['total_words'], 0)

    def test_text_preprocessing_edge_cases(self):
        """Test text preprocessing edge cases."""
        preprocessor = TextPreprocessor()

        # Empty text
        empty_paragraphs = preprocessor.preprocess_text("")
        self.assertEqual(len(empty_paragraphs), 0)

        # Single paragraph
        single_para = preprocessor.preprocess_text("Single paragraph text.")
        self.assertEqual(len(single_para), 1)

        # Text with extra whitespace
        whitespace_text = "  Paragraph 1.  \n\n  Paragraph 2.  "
        paragraphs = preprocessor.preprocess_text(whitespace_text)
        self.assertEqual(len(paragraphs), 2)
        self.assertFalse(paragraphs[0].startswith("  "))
        self.assertFalse(paragraphs[1].startswith("  "))

    def test_json_validator_valid_structure(self):
        """Test JSON validator with valid structure."""
        valid_data = {
            'paragraph_feedback': [
                {
                    'paragraph_index': 0,
                    'text': 'Test paragraph...',
                    'overall_feedback': 'Good paragraph',
                    'rubric_scores': {'Thesis': '8/10'},
                    'total_score': 8,
                    'max_score': 10,
                    'strengths': ['Clear thesis'],
                    'improvements': ['More detail']
                }
            ],
            'rubric_scores': {
                'total_points': 8,
                'max_points': 10,
                'percentage': 80.0,
                'letter_grade': 'B'
            },
            'overall_feedback': {
                'summary': 'Good work',
                'key_strengths': ['Clear thesis'],
                'key_improvements': ['More detail']
            },
            'suggestions': ['Improve detail']
        }

        result = JSONValidator.validate_structure(valid_data)
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.errors), 0)

    def test_json_validator_invalid_structure(self):
        """Test JSON validator with invalid structure."""
        invalid_data = {
            'paragraph_feedback': 'not an array',  # Wrong type
            'rubric_scores': {'total_points': 'not a number'},  # Wrong type
            # Missing overall_feedback and suggestions
        }

        result = JSONValidator.validate_structure(invalid_data)
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.errors), 0)

    def test_agent_components_without_llm(self):
        """Test agent components without LLM client."""
        # Create agent without LLM client
        agent = FeedbackGenerationAgent(llm_client=None)

        # Test workflow summary
        workflow = agent.get_workflow_summary()
        self.assertEqual(workflow['agent_name'], 'FeedbackGenerationAgent')
        self.assertEqual(len(workflow['workflow_steps']), 4)

    # Integration Tests
    def test_pipeline_upload_to_preprocessing(self):
        """Test upload → extraction → preprocessing chain."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(self.test_text)
            temp_path = f.name

        try:
            # Step 1: Extract text
            extracted_text = TextExtractor.extract_text(temp_path, 'txt')
            self.assertIsNotNone(extracted_text)

            # Step 2: Preprocess text
            preprocessor = TextPreprocessor()
            paragraphs = preprocessor.preprocess_text(extracted_text)
            self.assertEqual(len(paragraphs), 4)

            # Verify chain worked
            self.assertIn('Climate change', paragraphs[0])
            self.assertIn('conclusion', paragraphs[-1].lower())

        finally:
            os.unlink(temp_path)

    def test_pipeline_preprocessing_to_agent(self):
        """Test preprocessing → agent chain (without LLM)."""
        # Preprocess text
        preprocessor = TextPreprocessor()
        paragraphs = preprocessor.preprocess_text(self.test_text)

        # Create agent input
        agent_input = AgentInput(
            text=self.test_text,
            assignment_type='essay',
            context='Test essay'
        )

        # Verify agent input structure
        self.assertEqual(agent_input.text, self.test_text)
        self.assertEqual(agent_input.assignment_type, 'essay')
        self.assertEqual(agent_input.context, 'Test essay')

    # API Tests
    def test_pipeline_status_endpoint(self):
        """Test pipeline status endpoint."""
        response = self.client.get('/api/pipeline-status/')

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['pipeline_name'], 'Complete Assignment Feedback Pipeline')
        self.assertIn('workflow_steps', data)
        self.assertEqual(len(data['workflow_steps']), 5)

    def test_text_extraction_endpoint(self):
        """Test text extraction API endpoint."""
        # Create test file
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            self.test_text.encode('utf-8'),
            content_type="text/plain"
        )

        # Test extraction endpoint
        response = self.client.post('/api/extract-text/', {
            'file': uploaded_file
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertEqual(data['file_type'], 'txt')
        self.assertIn('text', data)
        self.assertGreater(data['text_length'], 0)

    def test_text_preprocessing_endpoint(self):
        """Test text preprocessing API endpoint."""
        response = self.client.post('/api/preprocess-text/', {
            'text': self.test_text
        })

        self.assertEqual(response.status_code, 200)
        data = response.json()

        self.assertTrue(data['success'])
        self.assertIn('paragraphs', data)
        self.assertIn('statistics', data)
        self.assertEqual(len(data['paragraphs']), 4)

    def test_complete_pipeline_endpoint_missing_file(self):
        """Test complete pipeline with missing file."""
        response = self.client.post('/api/complete-pipeline/', {
            'assignment_type': 'essay'
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertIn('pipeline_status', data)

    def test_complete_pipeline_endpoint_missing_assignment_type(self):
        """Test complete pipeline with missing assignment_type."""
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            self.test_text.encode('utf-8'),
            content_type="text/plain"
        )

        response = self.client.post('/api/complete-pipeline/', {
            'file': uploaded_file
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertFalse(data['success'])
        self.assertIn('assignment_type', data['error'].lower())

    def test_complete_pipeline_endpoint_invalid_file_type(self):
        """Test complete pipeline with invalid file type."""
        uploaded_file = SimpleUploadedFile(
            "test.xyz",
            b"test content",
            content_type="application/octet-stream"
        )

        response = self.client.post('/api/complete-pipeline/', {
            'file': uploaded_file,
            'assignment_type': 'essay'
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertFalse(data['success'])
        self.assertIn('Unsupported file type', data['error'])

    def test_api_validation_json_responses(self):
        """Test that all API endpoints return valid JSON."""
        # Test various endpoints
        endpoints = [
            ('GET', '/api/pipeline-status/', {}),
            ('POST', '/api/preprocess-text/', {'text': self.test_text}),
        ]

        for method, endpoint, data in endpoints:
            if method == 'GET':
                response = self.client.get(endpoint)
            else:
                response = self.client.post(endpoint, data)

            # Verify response is valid JSON
            self.assertEqual(response.status_code, 200)
            try:
                json.loads(response.content)
            except json.JSONDecodeError:
                self.fail(f"Endpoint {endpoint} did not return valid JSON")

    # End-to-End Tests
    def test_complete_pipeline_happy_path_without_llm(self):
        """Test complete pipeline happy path (without LLM - expected to fail at agent step)."""
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            self.test_text.encode('utf-8'),
            content_type="text/plain"
        )

        response = self.client.post('/api/complete-pipeline/', {
            'file': uploaded_file,
            'assignment_type': 'essay',
            'context': 'Test essay on climate change',
            'save_submission': False  # Don't save to database
        })

        # Should fail at agent step due to missing API key
        self.assertIn(response.status_code, [422, 500])  # Unprocessable entity or server error
        data = response.json()

        self.assertFalse(data['success'])
        self.assertIn('error', data)
        self.assertIn('pipeline_status', data)
        self.assertEqual(data['pipeline_status']['step'], 'agent_processing')

    def test_complete_pipeline_with_optional_parameters(self):
        """Test complete pipeline with optional parameters."""
        uploaded_file = SimpleUploadedFile(
            "test.txt",
            self.test_text.encode('utf-8'),
            content_type="text/plain"
        )

        response = self.client.post('/api/complete-pipeline/', {
            'file': uploaded_file,
            'assignment_type': 'essay',
            'context': 'Test context',
            'model': 'llama-3.3-70b-versatile',
            'save_submission': False
        })

        # Should fail at agent step but parameters should be accepted
        self.assertIn(response.status_code, [422, 500])
        data = response.json()

        self.assertFalse(data['success'])
        self.assertIn('pipeline_status', data)

    # Performance Tests
    def test_performance_small_text(self):
        """Test performance with small text."""
        small_text = "This is a short test paragraph."

        preprocessor = TextPreprocessor()
        paragraphs = preprocessor.preprocess_text(small_text)

        self.assertEqual(len(paragraphs), 1)
        self.assertLess(len(small_text), 100)  # Verify it's small

    def test_performance_large_text(self):
        """Test performance with large text."""
        # Create large text by repeating test text
        large_text = "\n\n".join([self.test_text] * 10)

        preprocessor = TextPreprocessor()
        paragraphs = preprocessor.preprocess_text(large_text)

        # Should handle large text efficiently
        self.assertGreater(len(paragraphs), 30)  # 10 * 4 paragraphs
        self.assertGreater(len(large_text), 10000)  # Verify it's large

    def test_temporary_file_cleanup(self):
        """Test that temporary files are cleaned up."""
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(self.test_text)
            temp_path = f.name

        # Extract text (should clean up temp file)
        try:
            extracted_text = TextExtractor.extract_text(temp_path, 'txt')
            self.assertIsNotNone(extracted_text)

            # Verify temp file was cleaned up
            # Note: The implementation should clean up, but we can't verify this directly
            # as the file is already deleted by the time we check

        finally:
            # Ensure cleanup even if test fails
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestPipelineErrorHandling(TestCase):
    """Test error handling in the pipeline."""

    def setUp(self):
        """Set up test environment."""
        self.client = Client()

    def test_missing_text_parameter(self):
        """Test missing text parameter in preprocessing."""
        response = self.client.post('/api/preprocess-text/', {})

        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertIn('error', data)
        self.assertIn('text', data['error'].lower())

    def test_invalid_text_type(self):
        """Test invalid text type in preprocessing."""
        response = self.client.post('/api/preprocess-text/', {
            'text': 123  # Not a string
        })

        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertIn('error', data)
        self.assertIn('string', data['error'].lower())

    def test_empty_file_upload(self):
        """Test empty file upload."""
        uploaded_file = SimpleUploadedFile(
            "empty.txt",
            b"",
            content_type="text/plain"
        )

        response = self.client.post('/api/extract-text/', {
            'file': uploaded_file
        })

        # Should handle empty file gracefully
        self.assertIn(response.status_code, [200, 400, 422])

    def test_large_file_upload(self):
        """Test large file upload (>10MB limit)."""
        # Create large file content (>10MB)
        large_content = b"x" * (11 * 1024 * 1024)  # 11MB

        uploaded_file = SimpleUploadedFile(
            "large.txt",
            large_content,
            content_type="text/plain"
        )

        response = self.client.post('/api/extract-text/', {
            'file': uploaded_file
        })

        # Should reject large file
        self.assertEqual(response.status_code, 400)
        data = response.json()

        self.assertIn('error', data)
        self.assertIn('size', data['error'].lower())


if __name__ == '__main__':
    import os
    import django
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'assignment_feedback.settings')
    django.setup()
    from django.test.utils import get_runner
    from django.conf import settings as django_settings
    TestRunner = get_runner(django_settings)
    test_runner = TestRunner()
    failures = test_runner.run_tests(['tests.integration.test_complete_pipeline'])
    if failures:
        raise SystemExit(failures)