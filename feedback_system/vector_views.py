"""
API views for vector RAG system management and debugging.

This module provides REST API endpoints for:
- Building and rebuilding vector index
- Checking index status
- Testing vector search
- Debug information
"""

import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
import json

from .vector_indexer import get_vector_indexer, VectorIndexerError
from .vector_retriever import get_vector_retriever
from .vector_store import VectorStoreError
from .embedding_service import EmbeddingServiceError

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def build_vector_index(request):
    """
    Build or update vector index.

    POST /api/vector/build-index/
    Body: {
        "rubric_id": int (optional),
        "clear": bool (optional, default: true)
    }
    """
    try:
        # Parse request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            data = {}

        rubric_id = data.get('rubric_id')
        clear = data.get('clear', True)

        # Get indexer
        indexer = get_vector_indexer()
        indexer.initialize()

        # Build index
        if rubric_id:
            stats = indexer.update_index_for_rubric(rubric_id)
        else:
            stats = indexer.build_index_from_database(clear_existing=clear)

        return JsonResponse({
            'success': True,
            'message': 'Index built successfully',
            'stats': stats
        })

    except VectorIndexerError as e:
        logger.error(f'Index build error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f'Unexpected error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def rebuild_vector_index(request):
    """
    Rebuild vector index from scratch.

    POST /api/vector/rebuild-index/
    """
    try:
        # Get indexer
        indexer = get_vector_indexer()
        indexer.initialize()

        # Rebuild index
        stats = indexer.rebuild_index()

        return JsonResponse({
            'success': True,
            'message': 'Index rebuilt successfully',
            'stats': stats
        })

    except VectorIndexerError as e:
        logger.error(f'Index rebuild error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f'Unexpected error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)


@require_http_methods(["GET"])
def vector_index_status(request):
    """
    Get vector index status and statistics.

    GET /api/vector/status/
    """
    try:
        # Get indexer
        indexer = get_vector_indexer()
        indexer.initialize()

        # Get status
        status = indexer.get_index_status()

        return JsonResponse({
            'success': True,
            'status': status
        })

    except Exception as e:
        logger.error(f'Error getting status: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def test_vector_search(request):
    """
    Test vector search with a query.

    POST /api/vector/test-search/
    Body: {
        "query": str,
        "k": int (optional, default: 5),
        "rubric_id": int (optional),
        "criterion_id": int (optional),
        "source_type": str (optional)
    }
    """
    try:
        # Parse request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({
                'success': False,
                'error': 'Invalid JSON in request body'
            }, status=400)

        query = data.get('query')
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'Query is required'
            }, status=400)

        k = data.get('k', 5)
        rubric_id = data.get('rubric_id')
        criterion_id = data.get('criterion_id')
        source_type = data.get('source_type')

        # Get retriever
        retriever = get_vector_retriever()
        retriever.initialize()

        # Perform search
        results = retriever.retrieve(
            query=query,
            k=k,
            filter_rubric_id=rubric_id,
            filter_criterion_id=criterion_id,
            filter_source_type=source_type
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'chunk_id': result.chunk_id,
                'text': result.text,
                'score': result.score,
                'distance': result.distance,
                'rubric_id': result.rubric_id,
                'criterion_id': result.criterion_id,
                'level_id': result.level_id,
                'source_type': result.source_type,
                'metadata': result.metadata
            })

        return JsonResponse({
            'success': True,
            'query': query,
            'results_count': len(formatted_results),
            'results': formatted_results
        })

    except (VectorStoreError, EmbeddingServiceError) as e:
        logger.error(f'Search error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f'Unexpected error: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)


@require_http_methods(["GET"])
def vector_debug_info(request):
    """
    Get debug information about vector RAG system.

    GET /api/vector/debug/
    """
    try:
        # Get services
        indexer = get_vector_indexer()
        retriever = get_vector_retriever()
        embedding_service = get_embedding_service()

        # Initialize services
        indexer.initialize()
        retriever.initialize()

        # Get debug info
        debug_info = {
            'indexer': {
                'initialized': indexer._initialized,
                'config': {
                    'index_type': indexer.config.index_type,
                    'model_name': indexer.config.model_name,
                    'chunk_size': indexer.config.chunk_size,
                    'top_k': indexer.config.top_k
                }
            },
            'retriever': {
                'initialized': retriever._initialized,
                'stats': retriever.get_retrieval_stats()
            },
            'embedding_service': {
                'cache_stats': embedding_service.get_cache_stats(),
                'model_name': embedding_service.model_name,
                'dimension': embedding_service.get_embedding_dimension()
            }
        }

        return JsonResponse({
            'success': True,
            'debug_info': debug_info
        })

    except Exception as e:
        logger.error(f'Error getting debug info: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_vector_cache(request):
    """
    Clear embedding cache.

    POST /api/vector/clear-cache/
    """
    try:
        # Get embedding service
        embedding_service = get_embedding_service()

        # Clear cache
        embedding_service.clear_cache()

        return JsonResponse({
            'success': True,
            'message': 'Embedding cache cleared'
        })

    except Exception as e:
        logger.error(f'Error clearing cache: {str(e)}')
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)