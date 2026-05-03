"""
Django management command for checking vector index status.

Usage:
    python manage.py vector_index_status
"""

from django.core.management.base import BaseCommand
import json

from feedback_system.vector_indexer import get_vector_indexer
from feedback_system.vector_retriever import get_vector_retriever
from feedback_system.embedding_service import get_embedding_service


class Command(BaseCommand):
    help = 'Check vector index status and statistics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output as JSON',
        )

    def handle(self, *args, **options):
        json_output = options.get('json', False)

        try:
            # Get services
            indexer = get_vector_indexer()
            retriever = get_vector_retriever()
            embedding_service = get_embedding_service()

            # Initialize services
            indexer.initialize()
            retriever.initialize()

            # Get status
            status = indexer.get_index_status()

            if json_output:
                self.stdout.write(json.dumps(status, indent=2))
            else:
                self.stdout.write(self.style.SUCCESS('Vector Index Status'))
                self.stdout.write('=' * 50)

                # Vector store stats
                vs_stats = status.get('vector_store', {})
                self.stdout.write(f'\nVector Store:')
                self.stdout.write(f'  Initialized: {vs_stats.get("initialized", False)}')
                self.stdout.write(f'  Total Vectors: {vs_stats.get("total_vectors", 0)}')
                self.stdout.write(f'  Dimension: {vs_stats.get("dimension", 0)}')
                self.stdout.write(f'  Index Type: {vs_stats.get("index_type", "N/A")}')
                self.stdout.write(f'  Is Trained: {vs_stats.get("is_trained", "N/A")}')
                self.stdout.write(f'  Metadata Count: {vs_stats.get("metadata_count", 0)}')

                # Database stats
                db_stats = status.get('database', {})
                self.stdout.write(f'\nDatabase:')
                self.stdout.write(f'  Total Rubrics: {db_stats.get("total_rubrics", 0)}')
                self.stdout.write(f'  Total Criteria: {db_stats.get("total_criteria", 0)}')
                self.stdout.write(f'  Total Levels: {db_stats.get("total_levels", 0)}')

                # Config
                config = status.get('config', {})
                self.stdout.write(f'\nConfiguration:')
                self.stdout.write(f'  Index Type: {config.get("index_type", "N/A")}')
                self.stdout.write(f'  Model Name: {config.get("model_name", "N/A")}')
                self.stdout.write(f'  Chunk Size: {config.get("chunk_size", 0)}')
                self.stdout.write(f'  Top K: {config.get("top_k", 0)}')

                # Embedding cache
                cache_stats = status.get('embedding_cache', {})
                self.stdout.write(f'\nEmbedding Cache:')
                self.stdout.write(f'  Enabled: {cache_stats.get("enabled", False)}')
                self.stdout.write(f'  Entries: {cache_stats.get("entries", 0)}')
                self.stdout.write(f'  Model: {cache_stats.get("model_name", "N/A")}')
                self.stdout.write(f'  Dimension: {cache_stats.get("dimension", 0)}')

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error getting status: {str(e)}'))