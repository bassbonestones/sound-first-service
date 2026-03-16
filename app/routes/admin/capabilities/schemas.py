"""Pydantic schemas and constants for capability admin endpoints."""
from pydantic import BaseModel
from typing import Any, Dict, List, Optional

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


# --- Response Models ---

class CapabilityArchiveResponse(BaseModel):
    """Response for archive/restore capability operation."""
    success: bool
    message: str
    capability_id: int
    is_active: bool


class CapabilityDeleteResponse(BaseModel):
    """Response for delete capability operation."""
    success: bool
    message: str
    capability_id: int
    shifted_count: int
    prereqs_cleaned: int
    domain_removed: bool
    domain: str


class CapabilityBasicInfo(BaseModel):
    """Basic capability info for response."""
    id: int
    name: str
    display_name: Optional[str]
    domain: str
    bit_index: int


class CapabilityCreateResponse(BaseModel):
    """Response for create capability operation."""
    success: bool
    message: str
    capability: CapabilityBasicInfo
    shifted_count: int


class PrerequisiteInfo(BaseModel):
    """Prerequisite name info."""
    id: int
    name: str
    domain: str


class CapabilityDetailResponse(BaseModel):
    """Detailed capability info for update response."""
    id: int
    name: str
    display_name: Optional[str]
    domain: str
    subdomain: Optional[str]
    bit_index: int
    requirement_type: str
    difficulty_tier: int
    difficulty_weight: float
    mastery_type: str
    mastery_count: int
    evidence_required_count: int
    evidence_distinct_materials: bool
    evidence_acceptance_threshold: int
    soft_gate_requirements: Optional[Dict[str, float]]
    prerequisite_names: List[PrerequisiteInfo]


class CapabilityUpdateResponse(BaseModel):
    """Response for update capability operation."""
    success: bool
    message: str
    capability: CapabilityDetailResponse


class DetectionRuleOptionsResponse(BaseModel):
    """Response for detection rule options."""
    types: List[str]
    sources: List[str]
    custom_functions: List[str]
    rule_schema: Dict[str, Dict[str, Any]]


class CapabilityListItem(BaseModel):
    """Capability item in list response."""
    id: int
    name: str
    display_name: Optional[str]
    domain: str
    subdomain: Optional[str]
    bit_index: Optional[int]
    requirement_type: Optional[str]
    difficulty_tier: Optional[int]
    difficulty_weight: Optional[float]
    mastery_type: Optional[str]
    mastery_count: Optional[int]
    evidence_required_count: Optional[int]
    evidence_distinct_materials: Optional[bool]
    evidence_acceptance_threshold: Optional[int]
    soft_gate_requirements: Optional[Dict[str, float]]
    detection_rule: Optional[Dict[str, Any]]
    is_active: bool
    is_global: bool
    prerequisite_ids: List[int]
    prerequisite_names: List[str]
    materials_requiring: int
    materials_teaching: int


class CapabilitiesListResponse(BaseModel):
    """Response for capabilities list."""
    capabilities: List[CapabilityListItem]
    count: int


class CapabilityGraphResponse(BaseModel):
    """Response for capability dependency graph."""
    capability: str
    depends_on: List[str]
    required_by: List[str]


class Day0CapabilitiesResponse(BaseModel):
    """Response for day0 capabilities list."""
    base_capabilities: List[str]
    clef_capabilities: List[str]
    all: List[str]


class ExportResponse(BaseModel):
    """Response for export operation."""
    success: bool
    message: str
    filename: str
    archived: Optional[str]
    detection_rules_preserved: int


class ReorderItem(BaseModel):
    """Item in reorder response."""
    id: int
    bit_index: int


class ReorderResponse(BaseModel):
    """Response for reorder operation."""
    success: bool
    message: str
    domain: str
    new_order: List[ReorderItem]


class RenameDomainResponse(BaseModel):
    """Response for rename domain operation."""
    success: bool
    message: str
    old_name: str
    new_name: str
    capabilities_updated: int
