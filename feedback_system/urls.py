from django.urls import path
from .views import (
    AssignmentSubmissionListCreateView,
    AssignmentSubmissionDetailView,
    TextExtractionView,
    TextPreprocessingView,
    FeedbackGenerationView
)
from .rubric_views import (
    RubricListCreateView,
    RubricDetailView,
    RubricCategoryListCreateView,
    RubricCategoryDetailView,
    RubricCriterionListCreateView,
    RubricCriterionDetailView,
    RubricLevelListCreateView,
    RubricLevelDetailView,
    RubricSearchView,
    RubricStatsView
)
from .rag_views import (
    RubricRAGFeedbackView,
    RAGExplanationView,
    RubricRetrievalView
)
from .agent_views import (
    FeedbackAgentView,
    AgentArchitectureView,
    AgentWorkflowView
)
from .pipeline_views import (
    CompletePipelineView,
    PipelineStatusView
)
from .vector_views import (
    build_vector_index,
    rebuild_vector_index,
    vector_index_status,
    test_vector_search,
    vector_debug_info,
    clear_vector_cache
)

app_name = 'feedback_system'

urlpatterns = [
    # Assignment submission endpoints
    path('submissions/', AssignmentSubmissionListCreateView.as_view(),
         name='submission-list-create'),
    path('submissions/<int:id>/', AssignmentSubmissionDetailView.as_view(),
         name='submission-detail'),

    # Text processing endpoints
    path('extract-text/', TextExtractionView.as_view(),
         name='extract-text'),
    path('preprocess-text/', TextPreprocessingView.as_view(),
         name='preprocess-text'),
    path('generate-feedback/', FeedbackGenerationView.as_view(),
         name='generate-feedback'),

    # Rubric endpoints
    path('rubrics/', RubricListCreateView.as_view(),
         name='rubric-list-create'),
    path('rubrics/<int:id>/', RubricDetailView.as_view(),
         name='rubric-detail'),
    path('rubrics/search/', RubricSearchView.as_view(),
         name='rubric-search'),
    path('rubrics/stats/', RubricStatsView.as_view(),
         name='rubric-stats'),

    # Rubric category endpoints
    path('rubrics/<int:rubric_id>/categories/', RubricCategoryListCreateView.as_view(),
         name='rubric-category-list-create'),
    path('categories/<int:id>/', RubricCategoryDetailView.as_view(),
         name='rubric-category-detail'),

    # Rubric criterion endpoints
    path('categories/<int:category_id>/criteria/', RubricCriterionListCreateView.as_view(),
         name='rubric-criterion-list-create'),
    path('criteria/<int:id>/', RubricCriterionDetailView.as_view(),
         name='rubric-criterion-detail'),

    # Rubric level endpoints
    path('criteria/<int:criterion_id>/levels/', RubricLevelListCreateView.as_view(),
         name='rubric-level-list-create'),
    path('levels/<int:id>/', RubricLevelDetailView.as_view(),
         name='rubric-level-detail'),

    # RAG endpoints
    path('rubric-rag-feedback/', RubricRAGFeedbackView.as_view(),
         name='rubric-rag-feedback'),
    path('rag-explanation/', RAGExplanationView.as_view(),
         name='rag-explanation'),
    path('rubric-retrieval/', RubricRetrievalView.as_view(),
         name='rubric-retrieval'),

    # Agent endpoints
    path('feedback-agent/', FeedbackAgentView.as_view(),
         name='feedback-agent'),
    path('agent-architecture/', AgentArchitectureView.as_view(),
         name='agent-architecture'),
    path('agent-workflow/', AgentWorkflowView.as_view(),
         name='agent-workflow'),

    # Complete pipeline endpoints
    path('complete-pipeline/', CompletePipelineView.as_view(),
         name='complete-pipeline'),
    path('pipeline-status/', PipelineStatusView.as_view(),
         name='pipeline-status'),

    # Vector RAG endpoints
    path('vector/build-index/', build_vector_index,
         name='build-vector-index'),
    path('vector/rebuild-index/', rebuild_vector_index,
         name='rebuild-vector-index'),
    path('vector/status/', vector_index_status,
         name='vector-index-status'),
    path('vector/test-search/', test_vector_search,
         name='test-vector-search'),
    path('vector/debug/', vector_debug_info,
         name='vector-debug-info'),
    path('vector/clear-cache/', clear_vector_cache,
         name='clear-vector-cache'),
]