"""
Views for rubric API endpoints.

Provides CRUD operations for rubrics, categories, criteria, and levels.
"""

from rest_framework import generics, views
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Q
import logging

from .models import Rubric, RubricCategory, RubricCriterion, RubricLevel
from .rubric_serializers import (
    RubricSerializer,
    RubricListSerializer,
    RubricCategorySerializer,
    RubricCriterionSerializer,
    RubricLevelSerializer,
    RubricCategoryCreateSerializer,
    RubricCriterionCreateSerializer,
    RubricLevelCreateSerializer
)

logger = logging.getLogger(__name__)


class RubricListCreateView(generics.ListCreateAPIView):
    """
    API view for listing and creating rubrics.
    GET: List all rubrics
    POST: Create new rubric
    """

    queryset = Rubric.objects.all()
    permission_classes = []

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'POST':
            return RubricSerializer
        return RubricListSerializer

    def get_queryset(self):
        """Filter rubrics based on query parameters."""
        queryset = Rubric.objects.all()

        # Filter by assignment type
        assignment_type = self.request.query_params.get('assignment_type')
        if assignment_type:
            queryset = queryset.filter(assignment_type__icontains=assignment_type)

        # Filter by active status
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')

        # Search by name
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(description__icontains=search)
            )

        return queryset


class RubricDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for retrieving, updating, and deleting specific rubrics.
    GET: Get specific rubric details
    PUT: Update rubric
    DELETE: Delete rubric
    """

    queryset = Rubric.objects.all()
    serializer_class = RubricSerializer
    lookup_field = 'id'


class RubricCategoryListCreateView(generics.ListCreateAPIView):
    """
    API view for listing and creating rubric categories.
    GET: List all categories for a rubric
    POST: Create new category
    """

    serializer_class = RubricCategorySerializer
    permission_classes = []

    def get_queryset(self):
        """Filter categories by rubric."""
        rubric_id = self.kwargs.get('rubric_id')
        return RubricCategory.objects.filter(rubric_id=rubric_id)

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'POST':
            return RubricCategoryCreateSerializer
        return RubricCategorySerializer


class RubricCategoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for retrieving, updating, and deleting specific categories.
    GET: Get specific category details
    PUT: Update category
    DELETE: Delete category
    """

    queryset = RubricCategory.objects.all()
    serializer_class = RubricCategorySerializer
    lookup_field = 'id'


class RubricCriterionListCreateView(generics.ListCreateAPIView):
    """
    API view for listing and creating rubric criteria.
    GET: List all criteria for a category
    POST: Create new criterion
    """

    serializer_class = RubricCriterionSerializer
    permission_classes = []

    def get_queryset(self):
        """Filter criteria by category."""
        category_id = self.kwargs.get('category_id')
        return RubricCriterion.objects.filter(category_id=category_id)

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'POST':
            return RubricCriterionCreateSerializer
        return RubricCriterionSerializer


class RubricCriterionDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for retrieving, updating, and deleting specific criteria.
    GET: Get specific criterion details
    PUT: Update criterion
    DELETE: Delete criterion
    """

    queryset = RubricCriterion.objects.all()
    serializer_class = RubricCriterionSerializer
    lookup_field = 'id'


class RubricLevelListCreateView(generics.ListCreateAPIView):
    """
    API view for listing and creating rubric levels.
    GET: List all levels for a criterion
    POST: Create new level
    """

    serializer_class = RubricLevelSerializer
    permission_classes = []

    def get_queryset(self):
        """Filter levels by criterion."""
        criterion_id = self.kwargs.get('criterion_id')
        return RubricLevel.objects.filter(criterion_id=criterion_id)

    def get_serializer_class(self):
        """Return appropriate serializer based on request method."""
        if self.request.method == 'POST':
            return RubricLevelCreateSerializer
        return RubricLevelSerializer


class RubricLevelDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    API view for retrieving, updating, and deleting specific levels.
    GET: Get specific level details
    PUT: Update level
    DELETE: Delete level
    """

    queryset = RubricLevel.objects.all()
    serializer_class = RubricLevelSerializer
    lookup_field = 'id'


class RubricSearchView(views.APIView):
    """
    API view for searching rubrics by various criteria.
    POST: Search rubrics with filters
    """

    def post(self, request, *args, **kwargs):
        """
        Search rubrics based on provided filters.

        Request body can contain:
        - assignment_type: Filter by assignment type
        - is_active: Filter by active status
        - search: Search in name and description
        - min_categories: Minimum number of categories
        - max_categories: Maximum number of categories
        """
        try:
            queryset = Rubric.objects.all()

            # Get filters from request
            assignment_type = request.data.get('assignment_type')
            is_active = request.data.get('is_active')
            search = request.data.get('search')
            min_categories = request.data.get('min_categories')
            max_categories = request.data.get('max_categories')

            # Apply filters
            if assignment_type:
                queryset = queryset.filter(assignment_type__icontains=assignment_type)

            if is_active is not None:
                queryset = queryset.filter(is_active=is_active)

            if search:
                queryset = queryset.filter(
                    Q(name__icontains=search) |
                    Q(description__icontains=search)
                )

            # Filter by category count
            if min_categories is not None or max_categories is not None:
                rubric_ids = []
                for rubric in queryset:
                    cat_count = rubric.get_total_categories()
                    if min_categories and cat_count < min_categories:
                        continue
                    if max_categories and cat_count > max_categories:
                        continue
                    rubric_ids.append(rubric.id)
                queryset = queryset.filter(id__in=rubric_ids)

            # Serialize results
            serializer = RubricListSerializer(queryset, many=True)

            return Response({
                'success': True,
                'count': len(serializer.data),
                'results': serializer.data
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error searching rubrics: {str(e)}")
            return Response(
                {'error': f'Search failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class RubricStatsView(views.APIView):
    """
    API view for getting rubric statistics.
    GET: Get statistics about rubrics
    """

    def get(self, request, *args, **kwargs):
        """
        Get statistics about rubrics in the system.

        Returns:
        - Total rubrics
        - Active rubrics
        - Total categories
        - Total criteria
        - Total levels
        - Rubrics by assignment type
        """
        try:
            total_rubrics = Rubric.objects.count()
            active_rubrics = Rubric.objects.filter(is_active=True).count()

            total_categories = RubricCategory.objects.count()
            total_criteria = RubricCriterion.objects.count()
            total_levels = RubricLevel.objects.count()

            # Get rubrics by assignment type
            assignment_types = {}
            for rubric in Rubric.objects.all():
                assignment_type = rubric.assignment_type or 'General'
                assignment_types[assignment_type] = assignment_types.get(assignment_type, 0) + 1

            return Response({
                'success': True,
                'statistics': {
                    'total_rubrics': total_rubrics,
                    'active_rubrics': active_rubrics,
                    'total_categories': total_categories,
                    'total_criteria': total_criteria,
                    'total_levels': total_levels,
                    'assignment_types': assignment_types
                }
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error getting rubric statistics: {str(e)}")
            return Response(
                {'error': f'Failed to get statistics: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )