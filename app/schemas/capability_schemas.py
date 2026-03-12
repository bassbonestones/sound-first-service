"""Capability-related Pydantic models."""
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict
import re


# Validation constants for capabilities
VALID_REQUIREMENT_TYPES = ["required", "learnable_in_context"]
VALID_MASTERY_TYPES = ["single", "any_of_pool", "multiple"]
MIN_RATING = 1
MAX_RATING = 5
MIN_DIFFICULTY_WEIGHT = 0.1
MAX_DIFFICULTY_WEIGHT = 10.0


class CapabilityCreateRequest(BaseModel):
    """Request model for creating a new capability."""
    name: str
    display_name: Optional[str] = None
    domain: str
    subdomain: Optional[str] = None
    requirement_type: str = "required"
    difficulty_tier: int = 1
    mastery_type: str = "single"
    mastery_count: int = 1
    evidence_required_count: int = 1
    evidence_distinct_materials: bool = False
    evidence_acceptance_threshold: int = 4
    difficulty_weight: float = 1.0
    prerequisite_ids: Optional[List[int]] = None
    soft_gate_requirements: Optional[Dict[str, float]] = None  # e.g., {"interval_velocity_score": 0.5}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate capability name is snake_case."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError("name must be snake_case (lowercase letters, numbers, underscores)")
        return v

    @field_validator("requirement_type")
    @classmethod
    def validate_requirement_type(cls, v: str) -> str:
        """Validate requirement_type against allowed values."""
        if v not in VALID_REQUIREMENT_TYPES:
            raise ValueError(f"requirement_type must be one of {VALID_REQUIREMENT_TYPES}")
        return v

    @field_validator("mastery_type")
    @classmethod
    def validate_mastery_type(cls, v: str) -> str:
        """Validate mastery_type against allowed values."""
        if v not in VALID_MASTERY_TYPES:
            raise ValueError(f"mastery_type must be one of {VALID_MASTERY_TYPES}")
        return v

    @field_validator("difficulty_tier")
    @classmethod
    def validate_difficulty_tier(cls, v: int) -> int:
        """Validate difficulty_tier is positive."""
        if v < 1:
            raise ValueError("difficulty_tier must be at least 1")
        return v

    @field_validator("evidence_acceptance_threshold")
    @classmethod
    def validate_evidence_threshold(cls, v: int) -> int:
        """Validate evidence_acceptance_threshold is a valid rating."""
        if v < MIN_RATING or v > MAX_RATING:
            raise ValueError(f"evidence_acceptance_threshold must be between {MIN_RATING} and {MAX_RATING}")
        return v

    @field_validator("difficulty_weight")
    @classmethod
    def validate_difficulty_weight(cls, v: float) -> float:
        """Validate difficulty_weight is within bounds."""
        if v < MIN_DIFFICULTY_WEIGHT or v > MAX_DIFFICULTY_WEIGHT:
            raise ValueError(f"difficulty_weight must be between {MIN_DIFFICULTY_WEIGHT} and {MAX_DIFFICULTY_WEIGHT}")
        return v


class ReorderCapabilitiesRequest(BaseModel):
    """Request model for reordering capabilities within a domain."""
    domain: str
    capability_ids: List[int]  # Ordered list of capability IDs


class RenameDomainRequest(BaseModel):
    """Request model for renaming a domain."""
    old_name: str
    new_name: str


class CapabilityUpdateRequest(BaseModel):
    """
    Request model for updating a capability.
    
    Note: id and bit_index are NOT editable via this endpoint.
    - id: Primary key, never changes
    - bit_index: Used for bitmask operations, changing could corrupt user progress
    """
    name: str
    display_name: Optional[str] = None
    domain: str
    subdomain: Optional[str] = None
    requirement_type: str = "required"
    difficulty_tier: int = 1
    mastery_type: str = "single"
    mastery_count: int = 1
    evidence_required_count: int = 1
    evidence_distinct_materials: bool = False
    evidence_acceptance_threshold: int = 4
    difficulty_weight: float = 1.0
    prerequisite_ids: Optional[List[int]] = None  # List of capability IDs, or None to skip update
    soft_gate_requirements: Optional[Dict[str, float]] = None  # e.g., {"interval_velocity_score": 0.5}

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate capability name is snake_case."""
        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError("name must be snake_case (lowercase letters, numbers, underscores)")
        return v

    @field_validator("requirement_type")
    @classmethod
    def validate_requirement_type(cls, v: str) -> str:
        """Validate requirement_type against allowed values."""
        if v not in VALID_REQUIREMENT_TYPES:
            raise ValueError(f"requirement_type must be one of {VALID_REQUIREMENT_TYPES}")
        return v

    @field_validator("mastery_type")
    @classmethod
    def validate_mastery_type(cls, v: str) -> str:
        """Validate mastery_type against allowed values."""
        if v not in VALID_MASTERY_TYPES:
            raise ValueError(f"mastery_type must be one of {VALID_MASTERY_TYPES}")
        return v

    @field_validator("difficulty_tier")
    @classmethod
    def validate_difficulty_tier(cls, v: int) -> int:
        """Validate difficulty_tier is positive."""
        if v < 1:
            raise ValueError("difficulty_tier must be at least 1")
        return v

    @field_validator("evidence_acceptance_threshold")
    @classmethod
    def validate_evidence_threshold(cls, v: int) -> int:
        """Validate evidence_acceptance_threshold is a valid rating."""
        if v < MIN_RATING or v > MAX_RATING:
            raise ValueError(f"evidence_acceptance_threshold must be between {MIN_RATING} and {MAX_RATING}")
        return v

    @field_validator("difficulty_weight")
    @classmethod
    def validate_difficulty_weight(cls, v: float) -> float:
        """Validate difficulty_weight is within bounds."""
        if v < MIN_DIFFICULTY_WEIGHT or v > MAX_DIFFICULTY_WEIGHT:
            raise ValueError(f"difficulty_weight must be between {MIN_DIFFICULTY_WEIGHT} and {MAX_DIFFICULTY_WEIGHT}")
        return v


# --- Response Models ---


class CapabilityBasicOut(BaseModel):
    """Basic capability info."""
    id: int
    name: str
    domain: Optional[str] = None


class CapabilityDetailOut(BaseModel):
    """Detailed capability info for v2 API."""
    id: int
    name: str
    display_name: Optional[str] = None
    domain: Optional[str] = None
    subdomain: Optional[str] = None
    requirement_type: Optional[str] = None
    bit_index: Optional[int] = None
    difficulty_tier: Optional[int] = None


class CapabilityHelpOut(BaseModel):
    """Capability for help menu."""
    id: int
    name: str
    display_name: str
    domain: Optional[str] = None
    has_lesson: bool = False


class MaterialHelpCapabilitiesOut(BaseModel):
    """Material help capabilities response."""
    material_id: int
    material_title: str
    capabilities: List[CapabilityHelpOut] = []


class DomainCountOut(BaseModel):
    """Domain with count."""
    domain: str
    count: int
