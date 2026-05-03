"""
LLM integration module for generating feedback using Groq.

This module provides functionality to:
- Send prompts to Groq LLM
- Generate paragraph-level feedback
- Return structured feedback responses
"""

import os
import logging
from typing import List, Dict, Optional
from dataclasses import dataclass

try:
    from groq import Groq
except ImportError:
    Groq = None

logger = logging.getLogger(__name__)


@dataclass
class ParagraphFeedback:
    """Data class for paragraph-level feedback."""
    paragraph_index: int
    paragraph_text: str
    feedback: str
    strengths: List[str]
    improvements: List[str]
    score: Optional[int] = None


class LLMIntegrationError(Exception):
    """Custom exception for LLM integration errors."""
    pass


class GroqLLMClient:
    """
    Groq LLM client for generating feedback on student assignments.

    Uses low temperature for consistent, reliable feedback generation.
    """

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.3-70b-versatile"):
        """
        Initialize Groq LLM client.

        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env variable)
            model: Model to use for generation (default: llama-3.3-70b-versatile)
        """
        if Groq is None:
            raise LLMIntegrationError(
                "Groq library is not installed. "
                "Please install it using: pip install groq"
            )

        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        if not self.api_key:
            raise LLMIntegrationError(
                "Groq API key not found. "
                "Please set GROQ_API_KEY environment variable."
            )

        self.model = model
        self.client = Groq(api_key=self.api_key)
        self.temperature = 0.2  # Low temperature for consistent output

    def generate_paragraph_feedback(
        self,
        paragraph: str,
        paragraph_index: int,
        context: Optional[str] = None
    ) -> ParagraphFeedback:
        """
        Generate feedback for a single paragraph.

        Args:
            paragraph: The paragraph text to analyze
            paragraph_index: Index of the paragraph in the document
            context: Optional context about the assignment

        Returns:
            ParagraphFeedback object with detailed feedback
        """
        # Validate inputs
        if not paragraph or not isinstance(paragraph, str):
            raise ValueError("Paragraph must be a non-empty string")

        if not paragraph.strip():
            raise ValueError("Paragraph cannot be empty or whitespace only")

        if paragraph_index < 0:
            raise ValueError("Paragraph index must be non-negative")

        try:
            prompt = self._create_paragraph_feedback_prompt(
                paragraph, paragraph_index, context
            )
            response = self._send_prompt(prompt)
            feedback_data = self._parse_feedback_response(response, paragraph, paragraph_index)

            # Validate feedback data
            if not feedback_data.feedback or not feedback_data.feedback.strip():
                logger.warning(f"Empty feedback generated for paragraph {paragraph_index}, using fallback")
                feedback_data.feedback = "Analysis completed. See strengths and improvements for details."

            if not feedback_data.strengths:
                logger.warning(f"No strengths identified for paragraph {paragraph_index}")
                feedback_data.strengths = ["Basic structure present"]

            if not feedback_data.improvements:
                logger.warning(f"No improvements suggested for paragraph {paragraph_index}")
                feedback_data.improvements = ["Continue to refine and polish your writing"]

            if feedback_data.score is None:
                logger.warning(f"No score generated for paragraph {paragraph_index}, defaulting to 5")
                feedback_data.score = 5

            # Ensure score is in valid range
            feedback_data.score = max(1, min(10, feedback_data.score))

            logger.info(f"Generated feedback for paragraph {paragraph_index} (score: {feedback_data.score}/10)")
            return feedback_data

        except ValueError as e:
            logger.error(f"Validation error for paragraph {paragraph_index}: {str(e)}")
            raise LLMIntegrationError(f"Invalid input: {str(e)}")
        except Exception as e:
            logger.error(f"Error generating feedback for paragraph {paragraph_index}: {str(e)}")
            raise LLMIntegrationError(f"Failed to generate feedback: {str(e)}")

    def generate_document_feedback(
        self,
        paragraphs: List[str],
        context: Optional[str] = None
    ) -> List[ParagraphFeedback]:
        """
        Generate feedback for all paragraphs in a document.

        Args:
            paragraphs: List of paragraph texts
            context: Optional context about the assignment

        Returns:
            List of ParagraphFeedback objects
        """
        feedback_list = []

        for index, paragraph in enumerate(paragraphs):
            try:
                feedback = self.generate_paragraph_feedback(
                    paragraph, index, context
                )
                feedback_list.append(feedback)
            except LLMIntegrationError as e:
                logger.error(f"Failed to generate feedback for paragraph {index}: {str(e)}")
                # Continue with other paragraphs even if one fails
                feedback_list.append(self._create_error_feedback(paragraph, index, str(e)))

        return feedback_list

    def _create_paragraph_feedback_prompt(
        self,
        paragraph: str,
        paragraph_index: int,
        context: Optional[str] = None
    ) -> str:
        """
        Create a structured prompt for paragraph-level feedback.

        Args:
            paragraph: The paragraph text
            paragraph_index: Index of the paragraph
            context: Optional context about the assignment

        Returns:
            Structured prompt string
        """
        # Validate paragraph content
        if not paragraph or not paragraph.strip():
            raise ValueError("Paragraph text cannot be empty")

        # Truncate very long paragraphs to avoid token limits
        max_paragraph_length = 2000
        if len(paragraph) > max_paragraph_length:
            paragraph = paragraph[:max_paragraph_length] + "..."

        prompt = f"""You are an expert writing tutor providing constructive feedback on student assignments. Analyze the following paragraph and provide specific, actionable feedback.

Paragraph {paragraph_index + 1}:
"{paragraph}"

"""

        if context:
            prompt += f"Assignment Context: {context}\n\n"

        prompt += """Please provide feedback in the following format:

FEEDBACK: [Your overall feedback on this paragraph - 2-3 sentences maximum]

STRENGTHS:
- [Specific strength 1 - what makes this paragraph effective]
- [Specific strength 2 - another positive aspect]
- [Specific strength 3 - third strength if applicable]

IMPROVEMENTS:
- [Specific improvement suggestion 1 - actionable and specific]
- [Specific improvement suggestion 2 - another concrete suggestion]
- [Specific improvement suggestion 3 - third improvement if applicable]

SCORE: [1-10 rating for overall quality based on: clarity=3pts, coherence=3pts, content=4pts]

Scoring Guidelines:
- 9-10: Excellent - Clear, coherent, well-developed content
- 7-8: Good - Generally clear with minor issues
- 5-6: Fair - Some clarity or coherence issues
- 3-4: Poor - Significant issues with clarity and coherence
- 1-2: Very Poor - Major problems throughout

Important Instructions:
- Be specific and constructive in your feedback
- Focus on clarity, coherence, and content quality
- Provide actionable suggestions with examples
- Be encouraging but honest in assessment
- Consider academic writing standards
- If paragraph is excellent, specifically acknowledge what makes it strong
- If there are issues, provide specific examples of how to improve
- Ensure score matches the feedback provided
- Always provide exactly 3 strengths and 3 improvements (use "None applicable" if truly none)
"""

        return prompt

    def _send_prompt(self, prompt: str) -> str:
        """
        Send prompt to Groq LLM and get response.

        Args:
            prompt: The prompt to send

        Returns:
            LLM response text
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert writing tutor providing constructive, specific feedback on student writing. Always follow the requested format exactly and provide scores that match your feedback."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.temperature,
                max_tokens=1000,
                top_p=1,
                stream=False,
                timeout=30.0  # 30 second timeout
            )

            if not response.choices or not response.choices[0]:
                raise LLMIntegrationError("No response generated by LLM")

            return response.choices[0].message.content

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Groq API error: {error_msg}")

            # Handle specific error types
            if "timeout" in error_msg.lower():
                raise LLMIntegrationError("Request timed out. Please try again.")
            elif "rate limit" in error_msg.lower():
                raise LLMIntegrationError("Rate limit exceeded. Please wait and try again.")
            elif "authentication" in error_msg.lower() or "api key" in error_msg.lower():
                raise LLMIntegrationError("Authentication failed. Please check your API key.")
            elif "quota" in error_msg.lower():
                raise LLMIntegrationError("API quota exceeded. Please check your usage limits.")
            else:
                raise LLMIntegrationError(f"Failed to get response from Groq: {error_msg}")

    def _parse_feedback_response(
        self,
        response: str,
        paragraph: str,
        paragraph_index: int
    ) -> ParagraphFeedback:
        """
        Parse the LLM response into structured feedback.

        Args:
            response: Raw LLM response
            paragraph: Original paragraph text
            paragraph_index: Index of the paragraph

        Returns:
            ParagraphFeedback object
        """
        try:
            # Validate response
            if not response or not response.strip():
                raise ValueError("Empty response from LLM")

            # Extract feedback
            feedback = ""
            strengths = []
            improvements = []
            score = None

            lines = response.split('\n')
            current_section = None

            for line in lines:
                line = line.strip()

                if not line:
                    continue

                # Detect section headers
                if line.upper().startswith("FEEDBACK:"):
                    current_section = "feedback"
                    feedback = line.split(":", 1)[1].strip() if ":" in line else ""
                elif line.upper().startswith("STRENGTHS:"):
                    current_section = "strengths"
                elif line.upper().startswith("IMPROVEMENTS:"):
                    current_section = "improvements"
                elif line.upper().startswith("SCORE:"):
                    current_section = "score"
                    try:
                        score_str = line.split(":", 1)[1].strip() if ":" in line else ""
                        # Extract numeric score from string
                        import re
                        score_match = re.search(r'\d+', score_str)
                        if score_match:
                            score = int(score_match.group())
                    except (ValueError, AttributeError):
                        score = None
                elif line.startswith("-") and current_section:
                    item = line[1:].strip()
                    if item:  # Only add non-empty items
                        if current_section == "strengths":
                            strengths.append(item)
                        elif current_section == "improvements":
                            improvements.append(item)
                elif current_section == "feedback" and line and not line.startswith("-"):
                    # Append to feedback if it's not a list item
                    if feedback:
                        feedback += " " + line
                    else:
                        feedback = line

            # Clean up feedback
            feedback = feedback.strip()

            # Validate and provide fallbacks
            if not feedback:
                feedback = "Analysis completed based on paragraph content and structure."

            if not strengths:
                strengths = ["Basic paragraph structure present"]

            if not improvements:
                improvements = ["Continue to develop and refine your writing"]

            if score is None:
                score = 5  # Default to middle score

            # Ensure score is in valid range
            score = max(1, min(10, score))

            # Limit to 3 items each for consistency
            strengths = strengths[:3]
            improvements = improvements[:3]

            return ParagraphFeedback(
                paragraph_index=paragraph_index,
                paragraph_text=paragraph,
                feedback=feedback,
                strengths=strengths,
                improvements=improvements,
                score=score
            )

        except Exception as e:
            logger.error(f"Error parsing feedback response: {str(e)}")
            logger.debug(f"Response that failed to parse: {response[:500]}")
            # Return basic feedback if parsing fails
            return ParagraphFeedback(
                paragraph_index=paragraph_index,
                paragraph_text=paragraph,
                feedback="Unable to parse detailed feedback. Basic analysis completed.",
                strengths=["Paragraph structure present"],
                improvements=["Review for clarity and coherence"],
                score=5
            )

    def _create_error_feedback(
        self,
        paragraph: str,
        paragraph_index: int,
        error_message: str
    ) -> ParagraphFeedback:
        """
        Create error feedback when LLM generation fails.

        Args:
            paragraph: Original paragraph text
            paragraph_index: Index of the paragraph
            error_message: Error message

        Returns:
            ParagraphFeedback with error information
        """
        return ParagraphFeedback(
            paragraph_index=paragraph_index,
            paragraph_text=paragraph,
            feedback=f"Unable to generate feedback due to technical error: {error_message}",
            strengths=[],
            improvements=[],
            score=None
        )

    def get_supported_models(self) -> List[str]:
        """
        Get list of supported Groq models.

        Returns:
            List of model names
        """
        return [
            "llama-3.3-70b-versatile",
            "llama3-8b-8192",
            "mixtral-8x7b-32768",
            "gemma-7b-it"
        ]

    def set_model(self, model: str) -> None:
        """
        Change the model being used.

        Args:
            model: New model name
        """
        if model not in self.get_supported_models():
            raise LLMIntegrationError(f"Unsupported model: {model}")

        self.model = model
        logger.info(f"Model changed to {model}")