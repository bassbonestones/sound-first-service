from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
target_metadata = Base.metadata

from .core import *
from .capability_schema import (
    Capability,
    MaterialCapability,
    MaterialAnalysis,
    UserInstrument,
    UserCapability,
    UserComplexityScores,
    # Adaptive engine models
    MaterialTeachesCapability,
    UserMaterialState,
    UserPitchFocusStats,
    UserCapabilityEvidenceEvent,
    Collection,
    CollectionMaterial,
    License,
    UserLicense,
    # Soft gate system
    SoftGateRule,
    UserSoftGateState,
)
from .teaching_module import (
    TeachingModule,
    Lesson,
    UserModuleProgress,
    UserLessonProgress,
    LessonAttempt,
)
