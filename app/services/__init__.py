"""
Services layer for Sound First backend.

Provides business logic separated from routes and database models.
Routes should delegate to services for complex operations.
"""

# Material ingestion (from services/)
from .material_ingestion_service import (
    MaterialEntry,
    IngestionResult,
    MaterialIngestionService,
    ingest_materials,
    export_materials_json,
)

# Material analysis (from services/)
from .material_analysis_service import (
    AnalysisResult,
    MaterialAnalysisService,
    get_analysis_service,
)

# Material management (from services/)
from .material_service import (
    UploadResult,
    ReanalyzeResult,
    BatchReanalyzeResult,
    MaterialService,
    get_material_service,
)

# Session generation (from services/)
from .session_service import (
    MiniSessionData,
    SessionState,
    SessionService,
    get_session_service,
    GOAL_LABEL_MAP,
)

# User management (from services/)
from .user_service import (
    JourneyStageResult,
    UserService,
    get_user_service,
    DAY0_BASE_CAPABILITIES,
    BASS_CLEF_INSTRUMENTS,
    RANGE_SPAN_CAPS,
)

# History and analytics (from services/)
from .history_service import (
    HistorySummary,
    MaterialHistoryData,
    TimelineDayData,
    FocusCardHistoryData,
    HistoryService,
    get_history_service,
)

# Practice engine (from services/engine/)
from .engine import (
    PracticeEngineService,
)

# Spaced repetition (from services/)
from .spaced_repetition import (
    DEFAULT_EASE_FACTOR,
    MIN_EASE_FACTOR,
    DEFAULT_INTERVAL,
    SpacedRepetitionItem,
    rating_to_quality,
    calculate_new_interval,
    update_item_after_review,
    prioritize_materials,
    get_review_stats,
    estimate_mastery_level,
    get_capability_weight_adjustment,
    build_sr_item_from_db,
    select_materials_with_sr,
)

__all__ = [
    # Material ingestion
    "MaterialEntry",
    "IngestionResult",
    "MaterialIngestionService",
    "ingest_materials",
    "export_materials_json",
    # Material analysis
    "AnalysisResult",
    "MaterialAnalysisService",
    "get_analysis_service",
    # Material management
    "UploadResult",
    "ReanalyzeResult",
    "BatchReanalyzeResult",
    "MaterialService",
    "get_material_service",
    # Session generation
    "MiniSessionData",
    "SessionState",
    "SessionService",
    "get_session_service",
    "GOAL_LABEL_MAP",
    # User management
    "JourneyStageResult",
    "UserService",
    "get_user_service",
    "DAY0_BASE_CAPABILITIES",
    "BASS_CLEF_INSTRUMENTS",
    "RANGE_SPAN_CAPS",
    # History and analytics
    "HistorySummary",
    "MaterialHistoryData",
    "TimelineDayData",
    "FocusCardHistoryData",
    "HistoryService",
    "get_history_service",
    # Practice engine
    "PracticeEngineService",
    # Spaced repetition
    "DEFAULT_EASE_FACTOR",
    "MIN_EASE_FACTOR",
    "DEFAULT_INTERVAL",
    "SpacedRepetitionItem",
    "rating_to_quality",
    "calculate_new_interval",
    "update_item_after_review",
    "prioritize_materials",
    "get_review_stats",
    "estimate_mastery_level",
    "get_capability_weight_adjustment",
    "build_sr_item_from_db",
    "select_materials_with_sr",
]
