# Schema exports for easy imports
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
]
