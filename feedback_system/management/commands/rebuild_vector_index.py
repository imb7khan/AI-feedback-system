"""
Django management command for rebuilding FAISS vector index.

Usage:
    python manage.py rebuild_vector_index
"""

from django.core.management.base import BaseCommand, CommandError
import logging

from feedback_system.vector_indexer import get_vector_indexer, VectorIndexerError

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Rebuild FAISS vector index from scratch'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress information',
        )

    def handle(self, *args, **options):
        verbose = options.get('verbose', False)

        if verbose:
            self.stdout.write(self.style.SUCCESS('Rebuilding vector index...'))

        try:
            # Get vector indexer
            indexer = get_vector_indexer()
            indexer.initialize()

            # Rebuild index
            stats = indexer.rebuild_index()

            self.stdout.write(self.style.SUCCESS(
                f'Successfully rebuilt index: {stats["rubrics_indexed"]} rubrics, '
                f'{stats["chunks_indexed"]} chunks'
            ))

            # Show detailed stats if verbose
            if verbose:
                self.stdout.write('\nIndex Statistics:')
                index_stats = stats.get('index_stats', {})
                for key, value in index_stats.items():
                    self.stdout.write(f'  {key}: {value}')

        except VectorIndexerError as e:
            raise CommandError(f'Index rebuild failed: {str(e)}')
        except Exception as e:
            raise CommandError(f'Unexpected error: {str(e)}')