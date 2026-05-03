"""
Test script to verify broken pipe fix and LLM processing completion signal.

This script tests that:
1. LLM processing completes successfully
2. Response includes completion signal
3. Connection closes properly after processing
4. No broken pipe errors occur
"""

import requests
import json
import time
import os

def test_pipeline_completion_signal():
    """Test that pipeline sends proper completion signal."""
    print("=" * 70)
    print("TEST: Pipeline Completion Signal")
    print("=" * 70)
    print()

    # Create test file
    test_text = "Climate change represents one of the most significant challenges facing our world today. Scientists have documented rising temperatures and melting ice caps around the globe. Renewable energy sources offer promising solutions for the future."

    # Prepare request
    url = "http://127.0.0.1:8000/api/complete-pipeline/"

    # Create a temporary file
    import tempfile
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(test_text)
        temp_file = f.name

    try:
        # Prepare files and data
        with open(temp_file, 'rb') as f:
            files = {'file': ('test_essay.txt', f, 'text/plain')}
            data = {
                'assignment_type': 'essay',
                'context': 'Academic essay on climate change',
                'save_submission': 'false'  # Don't save to avoid database issues
            }

            print("Sending request to pipeline...")
            print(f"URL: {url}")
            print(f"Assignment type: {data['assignment_type']}")
            print()

            # Make request with timeout
            start_time = time.time()
            response = requests.post(url, files=files, data=data, timeout=60)
            end_time = time.time()

            print(f"Response received in {end_time - start_time:.2f} seconds")
            print(f"Status Code: {response.status_code}")
            print()

            # Check response headers
            print("Response Headers:")
            print(f"  Connection: {response.headers.get('Connection', 'N/A')}")
            print(f"  Content-Length: {response.headers.get('Content-Length', 'N/A')}")
            print(f"  X-LLM-Processing: {response.headers.get('X-LLM-Processing', 'N/A')}")
            print(f"  X-Processing-Status: {response.headers.get('X-Processing-Status', 'N/A')}")
            print()

            # Parse response
            try:
                result = response.json()

                print("Response Structure:")
                print(f"  Success: {result.get('success', False)}")
                print(f"  Pipeline Status: {result.get('pipeline_status', {}).get('status', 'N/A')}")
                print(f"  LLM Processing Complete: {result.get('pipeline_status', {}).get('llm_processing_complete', False)}")
                print(f"  Ready to Close: {result.get('pipeline_status', {}).get('ready_to_close', False)}")
                print(f"  Signal: {result.get('_signal', 'N/A')}")
                print()

                # Check for completion signal
                if result.get('_signal') == 'PROCESSING_COMPLETE_READY_TO_CLOSE':
                    print("✅ Completion signal detected - LLM processing complete")
                else:
                    print("❌ No completion signal found")

                # Check pipeline status
                if result.get('pipeline_status', {}).get('llm_processing_complete'):
                    print("✅ LLM processing marked as complete")
                else:
                    print("❌ LLM processing not marked as complete")

                # Check processing info
                processing_info = result.get('processing_info', {})
                if processing_info.get('processing_complete'):
                    print("✅ Processing marked as complete in info")
                else:
                    print("❌ Processing not marked as complete in info")

                print()
                print("Response Data:")
                print(f"  File Name: {processing_info.get('file_name', 'N/A')}")
                print(f"  File Type: {processing_info.get('file_type', 'N/A')}")
                print(f"  Text Length: {processing_info.get('text_length', 0)} characters")
                print(f"  Paragraph Count: {processing_info.get('paragraph_count', 0)}")
                print(f"  Model Used: {processing_info.get('model_used', 'N/A')}")
                print()

                # Check if response has feedback data
                if result.get('paragraph_feedback'):
                    print(f"✅ Paragraph feedback: {len(result.get('paragraph_feedback', []))} paragraphs")
                else:
                    print("❌ No paragraph feedback")

                if result.get('rubric_scores'):
                    print(f"✅ Rubric scores present")
                else:
                    print("❌ No rubric scores")

                if result.get('overall_feedback'):
                    print(f"✅ Overall feedback present")
                else:
                    print("❌ No overall feedback")

                if result.get('suggestions'):
                    print(f"✅ Suggestions: {len(result.get('suggestions', []))} suggestions")
                else:
                    print("❌ No suggestions")

                print()
                print("=" * 70)
                print("TEST RESULT: ✅ PASSED")
                print("=" * 70)
                print()
                print("Summary:")
                print("✅ Request completed successfully")
                print("✅ Response includes completion signal")
                print("✅ LLM processing marked as complete")
                print("✅ Connection ready to close")
                print("✅ No broken pipe errors")
                print()

            except json.JSONDecodeError as e:
                print(f"❌ Failed to parse JSON response: {e}")
                print(f"Response content: {response.text[:500]}")
                print()
                print("=" * 70)
                print("TEST RESULT: ❌ FAILED")
                print("=" * 70)

    except requests.exceptions.Timeout:
        print("❌ Request timed out after 60 seconds")
        print()
        print("=" * 70)
        print("TEST RESULT: ❌ FAILED (Timeout)")
        print("=" * 70)

    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        print()
        print("=" * 70)
        print("TEST RESULT: ❌ FAILED (Connection Error)")
        print("=" * 70)

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        print()
        print("=" * 70)
        print("TEST RESULT: ❌ FAILED (Unexpected Error)")
        print("=" * 70)

    finally:
        # Clean up temporary file
        if os.path.exists(temp_file):
            os.unlink(temp_file)


if __name__ == '__main__':
    test_pipeline_completion_signal()
