"""Pydantic schema exports.

Provides all request/response schemas for API endpoints including
sessions, users, materials, capabilities, and teaching modules.
"""
from .session_schemas import (
    OnboardingIn,
    SelfDirectedSessionIn,
    PracticeAttemptIn,
    MiniSessionOut,
    PracticeSessionResponse,
    FocusCardOut,
    CurriculumStepOut,
    MiniSessionWithStepsOut,
    StepCompleteIn,
)

from .material_schemas import (
    MaterialUpload,
    MaterialAnalysisResponse,
    BatchIngestionRequest,
    BatchIngestionResponse,
    ReanalyzeRequest,
    ReanalyzeResponse,
    BatchReanalyzeRequest,
    BatchReanalyzeResponse,
    AnalysisPreviewOut,
)

from .user_schemas import (
    UserUpdateIn,
    UserRangeIn,
    ClientLogIn,
    ConfigUpdateIn,
    QuizResultIn,
)

from .capability_schemas import (
    CapabilityCreateRequest,
    ReorderCapabilitiesRequest,
    RenameDomainRequest,
    CapabilityUpdateRequest,
)

from .admin_schemas import (
    FocusCardCreate,
    FocusCardUpdate,
    SoftGateRuleUpdate,
    SoftGateRuleCreate,
    UserSoftGateStateUpdate,
    UserSoftGateStateReset,
)

from .generation_schemas import (
    GenerationType,
    ScaleType,
    ArpeggioType,
    ScalePattern,
    ArpeggioPattern,
    RhythmType,
    DynamicType,
    ArticulationType,
    MusicalKey,
    CANONICAL_KEYS,
    RangeSpec,
    GenerationRequest,
    PitchEvent,
    GenerationResponse,
    GenerationPreview,
)

from .teaching_module_schemas import (
    ModuleStatus,
    LessonStatus,
    ExerciseTemplateInfo,
    LessonConfig,
    LessonMastery,
    LessonBase,
    LessonDetail,
    LessonWithProgress,
    ModuleBase,
    ModuleSummary,
    ModuleDetail,
    ModuleWithProgress,
    UserModuleProgressOut,
    UserLessonProgressOut,
    LessonAttemptCreate,
    LessonAttemptOut,
    LessonAttemptResult,
    StartModuleRequest,
    StartLessonRequest,
    GeneratedExercise,
    ExerciseResultSubmit,
)

__all__ = [
    # Session schemas
    "OnboardingIn",
    "SelfDirectedSessionIn",
    "PracticeAttemptIn",
    "MiniSessionOut",
    "PracticeSessionResponse",
    "FocusCardOut",
    "CurriculumStepOut",
    "MiniSessionWithStepsOut",
    "StepCompleteIn",
    # Material schemas
    "MaterialUpload",
    "MaterialAnalysisResponse",
    "BatchIngestionRequest",
    "BatchIngestionResponse",
    "ReanalyzeRequest",
    "ReanalyzeResponse",
    "BatchReanalyzeRequest",
    "BatchReanalyzeResponse",
    # User schemas
    "UserUpdateIn",
    "UserRangeIn",
    "ClientLogIn",
    "ConfigUpdateIn",
    "QuizResultIn",
    # Capability schemas
    "CapabilityCreateRequest",
    "ReorderCapabilitiesRequest",
    "RenameDomainRequest",
    "CapabilityUpdateRequest",
    # Admin schemas
    "FocusCardCreate",
    "FocusCardUpdate",
    "SoftGateRuleUpdate",
    "SoftGateRuleCreate",
    "UserSoftGateStateUpdate",
    "UserSoftGateStateReset",
    # Generation schemas
    "GenerationType",
    "ScaleType",
    "ArpeggioType",
    "ScalePattern",
    "ArpeggioPattern",
    "RhythmType",
    "DynamicType",
    "ArticulationType",
    "MusicalKey",
    "CANONICAL_KEYS",
    "RangeSpec",
    "GenerationRequest",
    "PitchEvent",
    "GenerationResponse",
    "GenerationPreview",
]
