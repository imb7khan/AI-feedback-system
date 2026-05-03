"""
Simple RAG (Retrieval-Augmented Generation) service for rubric-based feedback.

This module implements basic RAG by:
1. Retrieving rubrics from database storage
2. Injecting rubric criteria into LLM prompts
3. Using rubric for structured scoring and feedback

How RAG is being used:
- RETRIEVAL: Fetch rubric from PostgreSQL database based on assignment type
- AUGMENTATION: Inject rubric criteria, performance levels, and scoring guides into LLM prompts
- GENERATION: LLM generates feedback and scores based on the retrieved rubric context
"""

import logging
import re
from typing import List, Dict, Optional, Any
from django.db.models import Q

from .models import Rubric, RubricCategory, RubricCriterion, RubricLevel
from .llm_integration import GroqLLMClient, ParagraphFeedback, LLMIntegrationError

logger = logging.getLogger(__name__)


class RubricRAGService:
    """
    Vector-Enhanced RAG service for rubric-based feedback generation.

    This service demonstrates advanced RAG principles:
    - Retrieves relevant rubrics from database
    - Uses vector embeddings for semantic search of relevant criteria
    - Augments LLM prompts with rubric context
    - Generates rubric-aligned feedback and scores
    """

    def __init__(self, llm_client: Optional[GroqLLMClient] = None, use_vector_rag: bool = True):
        """
        Initialize RAG service.

        Args:
            llm_client: Optional LLM client (will create default if not provided)
            use_vector_rag: Whether to use vector-based retrieval (default: True)
        """
        self.llm_client = llm_client
        self.use_vector_rag = use_vector_rag
        self.vector_retriever = None
        self.vector_indexer = None

        # Initialize vector components if enabled
        if self.use_vector_rag:
            try:
                from .vector_retriever import get_vector_retriever
                from .vector_indexer import get_vector_indexer
                self.vector_retriever = get_vector_retriever()
                self.vector_indexer = get_vector_indexer()
                logger.info("Vector RAG components initialized")
            except ImportError as e:
                logger.warning(f"Vector RAG components not available: {str(e)}")
                self.use_vector_rag = False

    def retrieve_rubric(
        self,
        assignment_type: str,
        rubric_id: Optional[int] = None
    ) -> Optional[Rubric]:
        """
        RETRIEVAL: Retrieve relevant rubric from database.

        This is the "R" in RAG - we retrieve the rubric that will be used
        to guide the LLM's feedback generation.

        Args:
            assignment_type: Type of assignment (e.g., 'essay', 'research paper')
            rubric_id: Optional specific rubric ID (overrides assignment_type)

        Returns:
            Rubric object or None if not found
        """
        try:
            if rubric_id:
                # Retrieve specific rubric by ID
                rubric = Rubric.objects.filter(id=rubric_id, is_active=True).first()
                if rubric:
                    logger.info(f"Retrieved rubric by ID: {rubric.name}")
                    return rubric
                else:
                    logger.warning(f"Rubric with ID {rubric_id} not found")
                    return None

            # Retrieve rubric by assignment type
            rubric = Rubric.objects.filter(
                assignment_type__icontains=assignment_type,
                is_active=True
            ).first()

            if rubric:
                logger.info(f"Retrieved rubric for '{assignment_type}': {rubric.name}")
            else:
                logger.warning(f"No active rubric found for assignment type: {assignment_type}")

            return rubric

        except Exception as e:
            logger.error(f"Error retrieving rubric: {str(e)}")
            return None

    def format_rubric_for_prompt(self, rubric: Rubric) -> str:
        """
        Format rubric data for injection into LLM prompt.

        This is part of the "A" in RAG - we augment the prompt by formatting
        the retrieved rubric into a structure the LLM can understand and use.

        Args:
            rubric: Rubric object to format

        Returns:
            Formatted rubric string for LLM prompt
        """
        rubric_context = f"""
RUBRIC FOR SCORING: {rubric.name}
Assignment Type: {rubric.assignment_type}
Maximum Score: {rubric.max_score}

"""

        # Add categories and criteria
        for category in rubric.categories.all().order_by('order'):
            rubric_context += f"""
CATEGORY: {category.name} (Weight: {category.weight})
{category.description}

"""

            for criterion in category.criteria.all().order_by('order'):
                rubric_context += f"""
CRITERION: {criterion.name}
Description: {criterion.description}
Maximum Points: {criterion.max_points}

Performance Levels:
"""
                for level in criterion.levels.all().order_by('-score_range_max'):
                    rubric_context += f"""
- {level.level_name.upper()} ({level.score_range_min}-{level.score_range_max} points):
  {level.description}
"""

        rubric_context += """
SCORING INSTRUCTIONS:
- Evaluate each paragraph against ALL relevant criteria from the rubric
- Assign scores based on the performance level descriptions
- Provide specific feedback referencing the rubric criteria
- Consider the category weights when assessing overall quality
- Use the rubric language and terminology in your feedback
"""

        return rubric_context

    def generate_rubric_based_feedback(
        self,
        paragraph: str,
        paragraph_index: int,
        rubric: Rubric,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        GENERATION: Generate feedback using RAG approach.

        This is the "G" in RAG - we generate feedback that is informed by
        the retrieved rubric. The LLM uses the rubric context to provide
        structured, rubric-aligned scoring and feedback.

        Args:
            paragraph: Text to analyze
            paragraph_index: Index of the paragraph
            rubric: Retrieved rubric to use for scoring
            context: Optional additional context

        Returns:
            Dictionary with rubric-based feedback and scores
        """
        if not self.llm_client:
            raise LLMIntegrationError(
                "LLM client not initialized. Cannot generate feedback without LLM client."
            )

        try:
            # Step 1: Format rubric for prompt (Augmentation)
            rubric_context = self.format_rubric_for_prompt(rubric)

            # Step 2: Create RAG-enhanced prompt
            rag_prompt = self._create_rag_prompt(
                paragraph, paragraph_index, rubric_context, context
            )

            # Step 3: Send to LLM for generation
            response = self._send_rag_prompt(rag_prompt)

            # Step 4: Parse rubric-based response
            feedback_data = self._parse_rubric_response(
                response, paragraph, paragraph_index, rubric
            )

            logger.info(f"Generated RAG-based feedback for paragraph {paragraph_index}")
            return feedback_data

        except Exception as e:
            logger.error(f"Error generating RAG feedback: {str(e)}")
            raise LLMIntegrationError(f"RAG feedback generation failed: {str(e)}")

    def generate_document_rubric_feedback(
        self,
        paragraphs: List[str],
        assignment_type: str,
        rubric_id: Optional[int] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate rubric-based feedback for entire document using RAG.

        This demonstrates the complete RAG workflow:
        1. RETRIEVE: Get relevant rubric from database
        2. AUGMENT: Format rubric for LLM prompt
        3. GENERATE: Create rubric-aligned feedback for all paragraphs

        Args:
            paragraphs: List of paragraph texts
            assignment_type: Type of assignment
            rubric_id: Optional specific rubric ID
            context: Optional assignment context

        Returns:
            Dictionary with rubric information and paragraph feedback
        """
        try:
            # RETRIEVAL: Get rubric from database
            rubric = self.retrieve_rubric(assignment_type, rubric_id)

            if not rubric:
                raise LLMIntegrationError(
                    f"No active rubric found for assignment type: {assignment_type}"
                )

            # Generate feedback for each paragraph using RAG
            paragraph_feedback = []
            total_score = 0
            max_possible_score = 0

            for index, paragraph in enumerate(paragraphs):
                try:
                    feedback = self.generate_rubric_based_feedback(
                        paragraph, index, rubric, context
                    )
                    paragraph_feedback.append(feedback)

                    # Accumulate scores
                    if feedback.get('total_score'):
                        total_score += feedback['total_score']
                    if feedback.get('max_score'):
                        max_possible_score += feedback['max_score']

                except LLMIntegrationError as e:
                    logger.error(f"Failed to generate RAG feedback for paragraph {index}: {str(e)}")
                    # Continue with other paragraphs
                    paragraph_feedback.append({
                        'paragraph_index': index,
                        'error': str(e),
                        'total_score': 0,
                        'max_score': 0,
                        'criterion_scores': {}
                    })

            # Calculate overall statistics
            overall_percentage = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0

            return {
                'success': True,
                'rubric': {
                    'id': rubric.id,
                    'name': rubric.name,
                    'assignment_type': rubric.assignment_type,
                    'max_score': rubric.max_score,
                    'total_categories': rubric.get_total_categories(),
                    'total_criteria': rubric.get_total_criteria()
                },
                'overall_score': {
                    'total_points': total_score,
                    'max_points': max_possible_score,
                    'percentage': round(overall_percentage, 2)
                },
                'paragraph_feedback': paragraph_feedback,
                'total_paragraphs': len(paragraphs),
                'successful_feedback': len([f for f in paragraph_feedback if 'error' not in f])
            }

        except Exception as e:
            logger.error(f"Error in document RAG feedback: {str(e)}")
            raise LLMIntegrationError(f"Document RAG feedback failed: {str(e)}")

    def _create_rag_prompt(
        self,
        paragraph: str,
        paragraph_index: int,
        rubric_context: str,
        context: Optional[str] = None
    ) -> str:
        """
        Create RAG-enhanced prompt with rubric context.

        The prompt combines the retrieved rubric with the paragraph text,
        allowing the LLM to generate rubric-aligned feedback.

        Args:
            paragraph: Text to analyze
            paragraph_index: Index of the paragraph
            rubric_context: Formatted rubric information
            context: Optional additional context

        Returns:
            Complete RAG-enhanced prompt
        """
        prompt = f"""You are an expert writing tutor providing rubric-based feedback. Use the provided rubric to evaluate the following paragraph.

{rubric_context}

Paragraph {paragraph_index + 1} to Evaluate:
"{paragraph}"
"""

        if context:
            prompt += f"""
Assignment Context: {context}
"""

        prompt += """
Please evaluate this paragraph according to the rubric above and provide your response in the following format:

OVERALL_FEEDBACK: [Your overall assessment of the paragraph - 2-3 sentences]

CRITERION_SCORES:
- [Criterion Name]: [Score]/[Max Points] - [Brief justification]
- [Criterion Name]: [Score]/[Max Points] - [Brief justification]
- [Continue for all relevant criteria...]

TOTAL_SCORE: [Sum of all criterion scores]

MAX_SCORE: [Maximum possible score for this paragraph]

STRENGTHS:
- [Strength 1 - reference specific rubric criteria]
- [Strength 2 - reference specific rubric criteria]

IMPROVEMENTS:
- [Improvement 1 - reference specific rubric criteria and performance levels]
- [Improvement 2 - reference specific rubric criteria and performance levels]

RUBRIC_ALIGNMENT: [How well this paragraph meets the rubric expectations - reference specific performance levels]

Important:
- Base your evaluation specifically on the rubric criteria provided
- Use the exact criterion names from the rubric
- Reference the performance level descriptions in your feedback
- Assign scores that align with the performance level ranges
- Consider the category weights in your overall assessment
"""

        return prompt

    def _send_rag_prompt(self, prompt: str) -> str:
        """
        Send RAG-enhanced prompt to LLM.

        Args:
            prompt: RAG-enhanced prompt with rubric context

        Returns:
            LLM response
        """
        try:
            response = self.llm_client.client.chat.completions.create(
                model=self.llm_client.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert writing tutor specializing in rubric-based assessment. Always use the provided rubric criteria and performance levels to guide your evaluation and scoring."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=self.llm_client.temperature,
                max_tokens=1500,
                top_p=1,
                stream=False
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"RAG prompt error: {str(e)}")
            raise LLMIntegrationError(f"RAG LLM call failed: {str(e)}")

    def _parse_rubric_response(
        self,
        response: str,
        paragraph: str,
        paragraph_index: int,
        rubric: Rubric
    ) -> Dict[str, Any]:
        """
        Parse RAG-enhanced LLM response.

        Extracts structured scores and feedback that align with the rubric.

        Args:
            response: LLM response
            paragraph: Original paragraph text
            paragraph_index: Index of the paragraph
            rubric: Rubric used for evaluation

        Returns:
            Structured feedback dictionary
        """
        try:
            lines = response.split('\n')
            current_section = None

            result = {
                'paragraph_index': paragraph_index,
                'paragraph_text': paragraph,
                'overall_feedback': '',
                'criterion_scores': {},
                'total_score': 0,
                'max_score': 0,
                'strengths': [],
                'improvements': [],
                'rubric_alignment': ''
            }

            for line in lines:
                line = line.strip()

                if line.startswith("OVERALL_FEEDBACK:"):
                    current_section = "overall_feedback"
                    result['overall_feedback'] = line.replace("OVERALL_FEEDBACK:", "").strip()
                elif line.startswith("CRITERION_SCORES:"):
                    current_section = "criterion_scores"
                elif line.startswith("TOTAL_SCORE:"):
                    current_section = "total_score"
                    try:
                        result['total_score'] = int(line.replace("TOTAL_SCORE:", "").strip())
                    except ValueError:
                        pass
                elif line.startswith("MAX_SCORE:"):
                    current_section = "max_score"
                    try:
                        result['max_score'] = int(line.replace("MAX_SCORE:", "").strip())
                    except ValueError:
                        pass
                elif line.startswith("STRENGTHS:"):
                    current_section = "strengths"
                elif line.startswith("IMPROVEMENTS:"):
                    current_section = "improvements"
                elif line.startswith("RUBRIC_ALIGNMENT:"):
                    current_section = "rubric_alignment"
                    result['rubric_alignment'] = line.replace("RUBRIC_ALIGNMENT:", "").strip()
                elif line.startswith("-") and current_section:
                    item = line[1:].strip()
                    if current_section == "criterion_scores":
                        # Parse criterion score format: "Criterion Name: 8/10 - justification"
                        if ':' in item:
                            parts = item.split(':', 1)
                            criterion_name = parts[0].strip()
                            score_info = parts[1].strip() if len(parts) > 1 else ""
                            result['criterion_scores'][criterion_name] = score_info
                    elif current_section == "strengths":
                        result['strengths'].append(item)
                    elif current_section == "improvements":
                        result['improvements'].append(item)
                elif current_section == "overall_feedback" and line:
                    result['overall_feedback'] += " " + line
                elif current_section == "rubric_alignment" and line:
                    result['rubric_alignment'] += " " + line

            # Clean up text fields
            result['overall_feedback'] = result['overall_feedback'].strip()
            result['rubric_alignment'] = result['rubric_alignment'].strip()

            # Derive numeric totals from criterion scores when possible.
            # This prevents zero totals when the model omits TOTAL_SCORE/MAX_SCORE
            # but provides per-criterion entries like "8/10 - justification".
            parsed_total = 0
            parsed_max = 0
            for score_info in result['criterion_scores'].values():
                match = re.search(r'(\d+)\s*/\s*(\d+)', score_info)
                if match:
                    parsed_total += int(match.group(1))
                    parsed_max += int(match.group(2))

            if parsed_max > 0:
                result['total_score'] = parsed_total
                result['max_score'] = parsed_max

            return result

        except Exception as e:
            logger.error(f"Error parsing RUBRIC response: {str(e)}")
            # Return basic response if parsing fails
            return {
                'paragraph_index': paragraph_index,
                'paragraph_text': paragraph,
                'overall_feedback': response,
                'criterion_scores': {},
                'total_score': 0,
                'max_score': 0,
                'strengths': [],
                'improvements': [],
                'rubric_alignment': '',
                'parsing_error': str(e)
            }

    def retrieve_relevant_rubric_chunks(
        self,
        query: str,
        rubric_id: Optional[int] = None,
        k: Optional[int] = None
    ) -> Optional[str]:
        """
        VECTOR RETRIEVAL: Retrieve relevant rubric chunks using semantic search.

        This is the enhanced "R" in RAG - we use vector embeddings to find
        the most relevant rubric criteria and performance levels for the query.

        Args:
            query: Query text (e.g., paragraph content)
            rubric_id: Optional rubric ID to filter by
            k: Number of chunks to retrieve

        Returns:
            Formatted string with relevant rubric chunks, or None if vector RAG unavailable
        """
        if not self.use_vector_rag or not self.vector_retriever:
            logger.debug("Vector RAG not available, falling back to simple RAG")
            return None

        try:
            # Initialize retriever if needed
            if not self.vector_retriever._initialized:
                self.vector_retriever.initialize()

            # Retrieve relevant chunks
            results = self.vector_retriever.retrieve(
                query=query,
                k=k or 5,
                filter_rubric_id=rubric_id
            )

            if not results:
                logger.warning(f"No relevant rubric chunks found for query: {query[:50]}...")
                return None

            # Format results for prompt
            formatted_context = self.vector_retriever.format_results_for_prompt(
                results,
                max_results=5,
                include_metadata=True
            )

            logger.info(f"Retrieved {len(results)} relevant rubric chunks using vector search")
            return formatted_context

        except Exception as e:
            logger.error(f"Vector retrieval failed: {str(e)}")
            return None

    def format_vector_rubric_for_prompt(
        self,
        vector_context: str,
        rubric: Optional[Rubric] = None
    ) -> str:
        """
        Format vector-retrieved rubric context for LLM prompt.

        Args:
            vector_context: Formatted vector search results
            rubric: Optional rubric object for additional context

        Returns:
            Complete rubric context string
        """
        context = f"""
VECTOR-ENHANCED RUBRIC INFORMATION:
{vector_context}
"""

        # Add basic rubric info if available
        if rubric:
            context += f"""
BASIC RUBRIC INFO:
- Name: {rubric.name}
- Assignment Type: {rubric.assignment_type}
- Maximum Score: {rubric.max_score}
"""

        context += """
SCORING INSTRUCTIONS:
- Use the retrieved rubric information above to evaluate the paragraph
- Focus on criteria and performance levels that are most relevant to the content
- Assign scores based on the performance level descriptions
- Provide specific feedback referencing the rubric criteria
- Consider the relevance scores when weighting different criteria
"""

        return context

    def generate_vector_rubric_feedback(
        self,
        paragraph: str,
        paragraph_index: int,
        rubric: Optional[Rubric] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        VECTOR-ENHANCED GENERATION: Generate feedback using vector-based RAG.

        This combines vector retrieval with LLM generation for more targeted,
        relevant feedback based on semantic similarity.

        Args:
            paragraph: Text to analyze
            paragraph_index: Index of the paragraph
            rubric: Optional rubric object
            context: Optional additional context

        Returns:
            Dictionary with vector-based feedback and scores
        """
        if not self.llm_client:
            raise LLMIntegrationError(
                "LLM client not initialized. Cannot generate feedback without LLM client."
            )

        try:
            # Step 1: Vector retrieval of relevant rubric chunks
            vector_context = self.retrieve_relevant_rubric_chunks(
                query=paragraph,
                rubric_id=rubric.id if rubric else None
            )

            # Step 2: Fall back to simple RAG if vector retrieval fails
            if not vector_context and rubric:
                logger.info("Vector retrieval failed, falling back to simple RAG")
                rubric_context = self.format_rubric_for_prompt(rubric)
            elif vector_context:
                rubric_context = self.format_vector_rubric_for_prompt(vector_context, rubric)
            else:
                raise LLMIntegrationError("No rubric context available for feedback generation")

            # Step 3: Create vector-enhanced prompt
            vector_prompt = self._create_vector_rag_prompt(
                paragraph, paragraph_index, rubric_context, context
            )

            # Step 4: Send to LLM for generation
            response = self._send_rag_prompt(vector_prompt)

            # Step 5: Parse response
            feedback_data = self._parse_rubric_response(
                response, paragraph, paragraph_index, rubric
            )

            # Add vector RAG metadata
            feedback_data['retrieval_method'] = 'vector' if vector_context else 'simple'
            feedback_data['vector_chunks_used'] = len(vector_context.split('\n')) if vector_context else 0

            logger.info(f"Generated vector RAG feedback for paragraph {paragraph_index}")
            return feedback_data

        except Exception as e:
            logger.error(f"Error generating vector RAG feedback: {str(e)}")
            raise LLMIntegrationError(f"Vector RAG feedback generation failed: {str(e)}")

    def _create_vector_rag_prompt(
        self,
        paragraph: str,
        paragraph_index: int,
        rubric_context: str,
        context: Optional[str] = None
    ) -> str:
        """
        Create vector-enhanced RAG prompt with retrieved rubric context.

        Args:
            paragraph: Text to analyze
            paragraph_index: Index of the paragraph
            rubric_context: Formatted rubric information from vector search
            context: Optional additional context

        Returns:
            Complete vector-enhanced RAG prompt
        """
        prompt = f"""You are an expert writing tutor providing rubric-based feedback. Use the retrieved rubric information below to evaluate the following paragraph.

{rubric_context}

Paragraph {paragraph_index + 1} to Evaluate:
"{paragraph}"
"""

        if context:
            prompt += f"""
Assignment Context: {context}
"""

        prompt += """
Please evaluate this paragraph using the retrieved rubric information and provide your response in the following format:

OVERALL_FEEDBACK: [Your overall assessment of the paragraph - 2-3 sentences]

RELEVANT_CRITERIA:
- [Most relevant criterion 1 from retrieved info]: [How paragraph meets/exceeds this criterion]
- [Most relevant criterion 2 from retrieved info]: [How paragraph meets/exceeds this criterion]
- [Most relevant criterion 3 from retrieved info]: [How paragraph meets/exceeds this criterion]

TOTAL_SCORE: [Estimated score based on relevant criteria]

MAX_SCORE: [Maximum possible score]

STRENGTHS:
- [Strength 1 - based on retrieved rubric criteria]
- [Strength 2 - based on retrieved rubric criteria]

IMPROVEMENTS:
- [Improvement 1 - reference specific performance levels from retrieved info]
- [Improvement 2 - reference specific performance levels from retrieved info]

RUBRIC_ALIGNMENT: [How well this paragraph meets the retrieved rubric expectations]

Important:
- Focus on the criteria that are most relevant to this paragraph's content
- Use the specific criterion names and performance levels from the retrieved information
- Consider the relevance scores when prioritizing which criteria to address
- Provide specific, actionable feedback based on the rubric descriptions
"""

        return prompt

    def generate_document_vector_rubric_feedback(
        self,
        paragraphs: List[str],
        assignment_type: str,
        rubric_id: Optional[int] = None,
        context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate vector-enhanced rubric-based feedback for entire document.

        This demonstrates the complete vector RAG workflow:
        1. RETRIEVE: Get relevant rubric chunks using semantic search
        2. AUGMENT: Format retrieved chunks for LLM prompt
        3. GENERATE: Create targeted feedback for all paragraphs

        Args:
            paragraphs: List of paragraph texts
            assignment_type: Type of assignment
            rubric_id: Optional specific rubric ID
            context: Optional assignment context

        Returns:
            Dictionary with rubric information and paragraph feedback
        """
        try:
            # Get rubric (for basic info)
            rubric = self.retrieve_rubric(assignment_type, rubric_id)

            if not rubric:
                logger.warning(f"No rubric found for assignment type: {assignment_type}, using vector-only approach")

            # Generate feedback for each paragraph using vector RAG
            paragraph_feedback = []
            total_score = 0
            max_possible_score = 0

            for index, paragraph in enumerate(paragraphs):
                try:
                    feedback = self.generate_vector_rubric_feedback(
                        paragraph, index, rubric, context
                    )
                    paragraph_feedback.append(feedback)

                    # Accumulate scores
                    if feedback.get('total_score'):
                        total_score += feedback['total_score']
                    if feedback.get('max_score'):
                        max_possible_score += feedback['max_score']

                except LLMIntegrationError as e:
                    logger.error(f"Failed to generate vector RAG feedback for paragraph {index}: {str(e)}")
                    # Continue with other paragraphs
                    paragraph_feedback.append({
                        'paragraph_index': index,
                        'error': str(e),
                        'total_score': 0,
                        'max_score': 0,
                        'criterion_scores': {}
                    })

            # Calculate overall statistics
            overall_percentage = (total_score / max_possible_score * 100) if max_possible_score > 0 else 0

            result = {
                'success': True,
                'retrieval_method': 'vector',
                'paragraph_feedback': paragraph_feedback,
                'total_paragraphs': len(paragraphs),
                'successful_feedback': len([f for f in paragraph_feedback if 'error' not in f]),
                'overall_score': {
                    'total_points': total_score,
                    'max_points': max_possible_score,
                    'percentage': round(overall_percentage, 2)
                }
            }

            # Add rubric info if available
            if rubric:
                result['rubric'] = {
                    'id': rubric.id,
                    'name': rubric.name,
                    'assignment_type': rubric.assignment_type,
                    'max_score': rubric.max_score,
                    'total_categories': rubric.get_total_categories(),
                    'total_criteria': rubric.get_total_criteria()
                }

            return result

        except Exception as e:
            logger.error(f"Error in document vector RAG feedback: {str(e)}")
            raise LLMIntegrationError(f"Document vector RAG feedback failed: {str(e)}")


def explain_rag_usage():
    """
    Explain how RAG is being used in this system.

    This function provides a clear explanation of the RAG implementation
    for educational purposes and system documentation.
    """
    explanation = """
RAG (Retrieval-Augmented Generation) Implementation Explanation
==================================================================

HOW RAG IS BEING USED IN THIS SYSTEM:

1. RETRIEVAL (R):
   - What: Fetch rubrics from PostgreSQL database + semantic search
   - Where: RubricRAGService.retrieve_rubric() + retrieve_relevant_rubric_chunks()
   - Why: Get the evaluation criteria that will guide feedback
   - Example: Retrieve essay rubric when evaluating an essay, then find most relevant criteria

2. AUGMENTATION (A):
   - What: Format and inject rubric into LLM prompts
   - Where: RubricRAGService.format_rubric_for_prompt() + format_vector_rubric_for_prompt()
   - Why: Provide LLM with specific evaluation criteria and scoring guides
   - Example: Add "Thesis Statement: 9-10 points = clear, specific, compelling" to prompt

3. GENERATION (G):
   - What: LLM generates rubric-aligned feedback and scores
   - Where: RubricRAGService.generate_rubric_based_feedback() + generate_vector_rubric_feedback()
   - Why: Produce feedback that matches the rubric's expectations
   - Example: LLM scores thesis as 8/10 because it's clear but could be more specific

VECTOR-ENHANCED RAG VS SIMPLE RAG:

Simple RAG (fallback):
- Database: PostgreSQL (structured data)
- Retrieval: Simple queries by assignment type or ID
- No vector embeddings needed
- Direct database lookups

Vector-Enhanced RAG (primary):
- Vector Database: FAISS with sentence-transformers embeddings
- Retrieval: Semantic search for most relevant rubric content
- Embeddings: all-MiniLM-L6-v2 model (384 dimensions)
- Chunking: Configurable chunk size with overlap
- Similarity: Cosine similarity with configurable threshold

BENEFITS OF VECTOR-ENHANCED RAG:

1. Precision: Finds most relevant criteria for each paragraph
2. Context-Aware: Understands semantic meaning of content
3. Scalability: Handles large rubric collections efficiently
4. Flexibility: Works with any rubric structure
5. Performance: Fast semantic search with FAISS

VECTOR RAG WORKFLOW EXAMPLE:

Input: Student essay paragraph about climate change

Step 1 (VECTOR RETRIEVAL):
  Query: "climate change paragraph content"
  Vector Search: Find most similar rubric chunks
  Results: "Evidence Quality", "Scientific Accuracy", "Argument Strength"

Step 2 (AUGMENTATION):
  Format retrieved chunks:
  "Relevant Rubric Information:
   1. Evidence Quality (relevance: 0.92): Use credible, sufficient sources
   2. Scientific Accuracy (relevance: 0.88): Ensure factual correctness
   3. Argument Strength (relevance: 0.85): Build logical, compelling arguments"

Step 3 (GENERATION):
  LLM Response: "Evidence Quality: 8/10 - Good sources but need more quantity.
                Scientific Accuracy: 9/10 - All facts are correct and well-supported.
                Argument Strength: 7/10 - Logical flow but could be more compelling."

Output: Targeted feedback focusing on most relevant criteria

This vector-enhanced RAG approach provides precise, context-aware evaluation
by finding the most relevant rubric criteria for each paragraph.
"""

    return explanation
