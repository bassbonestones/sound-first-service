from sqlalchemy.ext.declarative import declarative_base
Base = declarative_base()
target_metadata = Base.metadata

from .core import *
from .capability_schema import (
    CapabilityV2,
    MaterialCapability,
    MaterialAnalysis,
    UserCapabilityV2,
    UserComplexityScores,
    # New adaptive engine models
    MaterialTeachesCapability,
    UserMaterialState,
    UserPitchFocusStats,
    UserCapabilityEvidenceEvent,
    Collection,
    CollectionMaterial,
    License,
    UserLicense,
)
