"""Pydantic schemas and constants for capability admin endpoints."""
from pydantic import BaseModel
from typing import List, Optional, Dict

from app.capability_registry import CUSTOM_DETECTORS


# --- Constants ---

# Detection rule type enum for dropdown
DETECTION_TYPES = ["element", "value_match", "compound", "interval", "text_match", "time_signature", "range", "custom"]

# Valid sources for value_match/text_match
DETECTION_SOURCES = ["notes", "dynamics", "tempos", "expressions", "articulations", "clefs", "key_signatures", "time_signatures", "intervals", "ornaments", "rests"]

# Custom detection functions (populated from capability_registry)
CUSTOM_DETECTION_FUNCTIONS = list(CUSTOM_DETECTORS.keys())

# Validation constants
VALID_REQUIREMENT_TYPES = ["required", "learnable_in_context"]
VALID_MASTERY_TYPES = ["single", "any_of_pool", "multiple"]
MIN_RATING = 1
MAX_RATING = 5
MIN_DIFFICULTY_WEIGHT = 0.1
MAX_DIFFICULTY_WEIGHT = 10.0


# --- Pydantic Models ---

class DetectionRuleConfig(BaseModel):
    """Detection rule configuration."""
    type: str  # element, value_match, compound, interval, text_match, time_signature, range, custom
    # For element type
    element_class: Optional[str] = None  # e.g., "music21.articulations.Staccato"
    # For value_match type
    source: Optional[str] = None  # notes, dynamics, etc.
    field: Optional[str] = None  # e.g., "type", "value"
    eq: Optional[str] = None  # exact match value
    gte: Optional[float] = None  # >= comparison
    lte: Optional[float] = None  # <= comparison
    contains: Optional[str] = None  # substring match
    # For interval type
    quality: Optional[str] = None  # e.g., "M3", "P5", "m2"
    melodic: Optional[bool] = True  # True for melodic, False for harmonic
    # For time_signature type
    numerator: Optional[int] = None
    denominator: Optional[int] = None
    # For range type
    min_semitones: Optional[int] = None
    max_semitones: Optional[int] = None
    # For custom type
    function: Optional[str] = None  # custom function name


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
    is_global: bool = True  # True = same for all instruments, False = per-instrument
    prerequisite_ids: Optional[List[int]] = None
    soft_gate_requirements: Optional[Dict[str, float]] = None
    detection_rule: Optional[DetectionRuleConfig] = None


class ReorderCapabilitiesRequest(BaseModel):
    """Request model for reordering capabilities within a domain."""
    domain: str
    capability_ids: List[int]


class RenameDomainRequest(BaseModel):
    """Request model for renaming a domain."""
    old_name: str
    new_name: str


class CapabilityUpdateRequest(BaseModel):
    """Request model for updating a capability."""
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
    is_global: bool = True  # True = same for all instruments, False = per-instrument
    prerequisite_ids: Optional[List[int]] = None
    soft_gate_requirements: Optional[Dict[str, float]] = None
    detection_rule: Optional[DetectionRuleConfig] = None
