"""Capability-related Pydantic models."""
from pydantic import BaseModel
from typing import List, Optional, Dict


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


# Validation constants for capabilities
VALID_REQUIREMENT_TYPES = ["required", "learnable_in_context"]
VALID_MASTERY_TYPES = ["single", "any_of_pool", "multiple"]
MIN_RATING = 1
MAX_RATING = 5
MIN_DIFFICULTY_WEIGHT = 0.1
MAX_DIFFICULTY_WEIGHT = 10.0
