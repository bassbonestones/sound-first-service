"""SQLAlchemy models package.

Contains all database models for users, materials, sessions, capabilities,
teaching modules, and related entities.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 declarative base class."""
    pass


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
