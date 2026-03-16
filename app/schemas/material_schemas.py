"""Material-related Pydantic models."""
from pydantic import BaseModel, field_validator
from typing import Any, Dict, List, Optional
import re


# Key format: letter + optional accidental (e.g., "C", "F#", "Bb")
KEY_PATTERN = re.compile(r"^[A-Ga-g][#b]?$")
# Valid metrics for analysis
VALID_METRICS = ["capabilities", "soft_gates", "range"]


class MaterialUpload(BaseModel):
    """Input model for material upload."""
    title: str
    musicxml_content: str
    original_key_center: Optional[str] = None
    allowed_keys: Optional[List[str]] = None  # If not provided, will default to common keys

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        """Validate title is not empty."""
        if not v or not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()

    @field_validator("original_key_center")
    @classmethod
    def validate_key_center(cls, v: Optional[str]) -> Optional[str]:
        """Validate key center is a valid key format."""
        if v is not None and not KEY_PATTERN.match(v):
            raise ValueError(f"original_key_center must be a valid key (e.g., 'C', 'F#', 'Bb'), got '{v}'")
        return v

    @field_validator("allowed_keys")
    @classmethod
    def validate_allowed_keys(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate all allowed keys are valid key formats."""
        if v is not None:
            invalid_keys = [k for k in v if not KEY_PATTERN.match(k)]
            if invalid_keys:
                raise ValueError(f"Invalid key format(s): {invalid_keys}. Keys must be like 'C', 'F#', 'Bb'")
        return v


class MaterialAnalysisResponse(BaseModel):
    """Response model for material analysis."""
    material_id: int
    title: str
    extracted_capabilities: List[str]
    range_analysis: Optional[Dict[str, Any]]
    chromatic_complexity: float
    measure_count: int
    warnings: List[str] = []


class BatchIngestionRequest(BaseModel):
    """Request model for batch material ingestion."""
    analyze_missing_only: bool = True
    overwrite: bool = False
    specific_files: Optional[List[str]] = None
    specific_metrics: Optional[List[str]] = None  # ["capabilities", "soft_gates"]

    @field_validator("specific_metrics")
    @classmethod
    def validate_metrics(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate metrics are valid options."""
        if v is not None:
            invalid_metrics = [m for m in v if m not in VALID_METRICS]
            if invalid_metrics:
                raise ValueError(f"Invalid metric(s): {invalid_metrics}. Valid options: {VALID_METRICS}")
        return v


class BatchIngestionResponse(BaseModel):
    """Response model for batch ingestion."""
    files_scanned: int
    files_analyzed: int
    files_skipped: int
    orphans_removed: int
    errors: List[str]
    analyzed_materials: List[str]


class ReanalyzeRequest(BaseModel):
    """Request model for selective re-analysis."""
    metrics: Optional[List[str]] = None  # ["capabilities", "soft_gates", "range"]
    # If None, re-analyzes everything

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate metrics are valid options."""
        if v is not None:
            invalid_metrics = [m for m in v if m not in VALID_METRICS]
            if invalid_metrics:
                raise ValueError(f"Invalid metric(s): {invalid_metrics}. Valid options: {VALID_METRICS}")
        return v


class ReanalyzeResponse(BaseModel):
    """Response model for re-analysis."""
    material_id: int
    title: str
    metrics_updated: List[str]
    capabilities_count: Optional[int] = None
    soft_gates: Optional[Dict[str, Any]] = None
    range_analysis: Optional[Dict[str, Any]] = None


class BatchReanalyzeRequest(BaseModel):
    """Request model for batch re-analysis."""
    metrics: Optional[List[str]] = None
    material_ids: Optional[List[int]] = None  # If None, re-analyzes all

    @field_validator("metrics")
    @classmethod
    def validate_metrics(cls, v: Optional[List[str]]) -> Optional[List[str]]:
        """Validate metrics are valid options."""
        if v is not None:
            invalid_metrics = [m for m in v if m not in VALID_METRICS]
            if invalid_metrics:
                raise ValueError(f"Invalid metric(s): {invalid_metrics}. Valid options: {VALID_METRICS}")
        return v


class BatchReanalyzeResponse(BaseModel):
    """Response model for batch re-analysis."""
    total_materials: int
    materials_updated: int
    materials_failed: int
    errors: List[str]


# --- New Response Models ---


class MaterialBasicOut(BaseModel):
    """Basic material info."""
    id: int
    title: str
    allowed_keys: List[str] = []
    original_key_center: Optional[str] = None
    pitch_reference_type: Optional[str] = None


class PitchDensityOut(BaseModel):
    """Pitch density values."""
    low: Optional[float] = None
    mid: Optional[float] = None
    high: Optional[float] = None


class MaterialAnalysisDetailOut(BaseModel):
    """Material analysis detail."""
    lowest_pitch: Optional[str] = None
    highest_pitch: Optional[str] = None
    range_semitones: Optional[int] = None
    pitch_density: Optional[PitchDensityOut] = None
    chromatic_complexity: Optional[float] = None
    tempo_marking: Optional[str] = None
    tempo_bpm: Optional[int] = None
    measure_count: Optional[int] = None


class CapabilityInMaterial(BaseModel):
    """Capability info for material."""
    id: int
    name: str
    display_name: Optional[str] = None
    domain: Optional[str] = None


class MaterialFullAnalysisOut(BaseModel):
    """Full material analysis response."""
    material_id: int
    title: str
    capabilities: List[CapabilityInMaterial] = []
    analysis: Optional[MaterialAnalysisDetailOut] = None


class ExportMessageOut(BaseModel):
    """Export message response."""
    message: str
    path: str


class RangeAnalysisOut(BaseModel):
    """Range analysis details."""
    lowest_pitch: Optional[str] = None
    highest_pitch: Optional[str] = None
    range_semitones: Optional[int] = None
    pitch_density: Optional[PitchDensityOut] = None


class AnalysisPreviewOut(BaseModel):
    """Response model for material analysis preview (without saving)."""
    title: str
    capabilities: List[str]
    capabilities_by_domain: Dict[str, Any]
    capability_count: int
    range_analysis: Optional[Dict[str, Any]] = None
    chromatic_complexity: Optional[float] = None
    measure_count: int
    tempo_bpm: Optional[int] = None
    tempo_marking: Optional[str] = None
    tempo_profile: Optional[Dict[str, Any]] = None
    soft_gates: Dict[str, Any]
    unified_scores: Dict[str, Any]
    detailed_extraction: Dict[str, Any]
