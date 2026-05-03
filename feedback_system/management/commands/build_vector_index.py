"""
Django management command for building FAISS vector index from database rubrics.

Usage:
    python manage.py build_vector_index
    python manage.py build_vector_index --rubric-id 1
    python manage.py build_vector_index --clear
"""

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
import logging

from feedback_system.vector_indexer import get_vector_indexer, VectorIndexerError
from feedback_system.models import Rubric

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Build FAISS vector index from database rubrics'

    def add_arguments(self, parser):
        parser.add_argument(
            '--rubric-id',
            type=int,
            help='Build index for specific rubric only',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing index before building',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed progress information',
        )

    def handle(self, *args, **options):
        rubric_id = options.get('rubric_id')
        clear = options.get('clear', True)
        verbose = options.get('verbose', False)

        if verbose:
            self.stdout.write(self.style.SUCCESS('Starting vector index build...'))

        try:
            # Get vector indexer
            indexer = get_vector_indexer()
            indexer.initialize()

            # Build index
            if rubric_id:
                # Update specific rubric
                if verbose:
                    self.stdout.write(f'Building index for rubric {rubric_id}...')

                stats = indexer.update_index_for_rubric(rubric_id)

                self.stdout.write(self.style.SUCCESS(
                    f'Successfully indexed rubric {rubric_id}: {stats["chunks_indexed"]} chunks'
                ))
            else:
                # Build full index
                if verbose:
                    self.stdout.write('Building full vector index...')

                stats = indexer.build_index_from_database(clear_existing=clear)

                self.stdout.write(self.style.SUCCESS(
                    f'Successfully built index: {stats["rubrics_indexed"]} rubrics, '
                    f'{stats["chunks_indexed"]} chunks'
                ))

            # Show detailed stats if verbose
            if verbose:
                self.stdout.write('\nIndex Statistics:')
                index_stats = stats.get('index_stats', {})
                for key, value in index_stats.items():
                    self.stdout.write(f'  {key}: {value}')

        except Rubric.DoesNotExist:
            raise CommandError(f'Rubric with ID {rubric_id} not found')
        except VectorIndexerError as e:
            raise CommandError(f'Index build failed: {str(e)}')
        except Exception as e:
            raise CommandError(f'Unexpected error: {str(e)}')