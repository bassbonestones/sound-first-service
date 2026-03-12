"""User-related Pydantic models."""
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re


# Note format: letter + optional accidental + octave (e.g., "C4", "F#3", "Bb5")
NOTE_PATTERN = re.compile(r"^[A-Ga-g][#b]?[0-9]$")


# --- Request Models ---


class UserUpdateIn(BaseModel):
    day0_completed: Optional[bool] = None
    day0_stage: Optional[int] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None


class UserRangeIn(BaseModel):
    range_low: str  # e.g., "E3"
    range_high: str  # e.g., "C6"

    @field_validator("range_low", "range_high")
    @classmethod
    def validate_note_format(cls, v: str) -> str:
        """Validate note is a valid format."""
        if not NOTE_PATTERN.match(v):
            raise ValueError(f"Note must be a valid format (e.g., 'E3', 'C6', 'F#4'), got '{v}'")
        return v


class ClientLogIn(BaseModel):
    event: str
    data: dict
    timestamp: Optional[str] = None


class ConfigUpdateIn(BaseModel):
    capability_weights: Optional[dict] = None
    difficulty_weights: Optional[dict] = None
    novelty_reinforcement: Optional[dict] = None


class QuizResultIn(BaseModel):
    user_id: int
    passed: bool
    answer_given: Optional[str] = None


# --- Response Models ---


class MessageResponse(BaseModel):
    """Generic message response."""
    message: str
    capability: Optional[str] = None


class StatusMessageResponse(BaseModel):
    """Generic status + message response."""
    status: str
    message: Optional[str] = None


class UserOut(BaseModel):
    """User details response."""
    id: int
    email: Optional[str] = None
    name: Optional[str] = None
    instrument: Optional[str] = None
    resonant_note: Optional[str] = None


class JourneyStageFactors(BaseModel):
    """Factors used to determine journey stage."""
    mastered_capabilities_count: int
    total_mastered_value: float
    mastered_to_total_ratio: float


class JourneyStageMetrics(BaseModel):
    """Metrics for journey stage determination."""
    total_practice_sessions: int
    days_practiced: int


class JourneyStageOut(BaseModel):
    """User journey stage response."""
    user_id: int
    stage: int
    stage_name: str
    factors: Dict[str, Any]
    metrics: Dict[str, Any]


class RangeUpdateOut(BaseModel):
    """Range update response."""
    status: str
    range_low: str
    range_high: str


class CapabilityProgressOut(BaseModel):
    """User capability progress response."""
    user_id: int
    total_capabilities: int
    capabilities_mastered: int
    capabilities_in_progress: int
    last_mastery: Optional[str] = None
    mastered_capability_ids: List[int] = []


class CapabilityInfo(BaseModel):
    """Basic capability information."""
    id: int
    name: str
    display_name: Optional[str] = None
    explanation: Optional[str] = None
    domain: Optional[str] = None


class NextCapabilityOut(BaseModel):
    """Next capability recommendation response."""
    next_capability: Optional[CapabilityInfo] = None
    message: Optional[str] = None


class MaterialForUser(BaseModel):
    """Material eligible for user."""
    id: int
    title: str
    difficulty: Optional[int] = None
    domain: Optional[str] = None
    source: Optional[str] = None


class EligibleMaterialsOut(BaseModel):
    """Eligible materials for user response."""
    user_id: int
    eligible_materials: List[MaterialForUser] = []
    total_eligible: int


class InstrumentDetailOut(BaseModel):
    """Detailed instrument info."""
    id: int
    instrument_name: str
    is_primary: bool
    clef: Optional[str] = None
    resonant_note: Optional[str] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None
    day0_completed: Optional[bool] = None
    day0_stage: Optional[int] = None
    created_at: Optional[str] = None
    last_practiced_at: Optional[str] = None


class UserInstrumentsOut(BaseModel):
    """User instruments list response."""
    user_id: int
    last_instrument_id: Optional[int] = None
    instruments: List[InstrumentDetailOut] = []


class SelectInstrumentOut(BaseModel):
    """Instrument selection response."""
    status: str
    last_instrument_id: int


class Day0StatusOut(BaseModel):
    """Day 0 status response."""
    user_id: int
    instrument_id: Optional[int] = None
    mastered_global_caps: List[str] = []
    skippable_stages: List[int] = []
    total_stages: int = 8
    effective_stages: int


class InstrumentCreateOut(BaseModel):
    """Create instrument response."""
    status: str
    instrument: InstrumentDetailOut


class InstrumentUpdateOut(BaseModel):
    """Update instrument response."""
    status: str
    granted_capabilities: List[str] = []
    instrument: InstrumentDetailOut


class InstrumentDeleteOut(BaseModel):
    """Delete instrument response."""
    status: str
    message: str


class UserUpdateOut(BaseModel):
    """User update response."""
    status: str
    user_id: int
    granted_capabilities: List[str] = []


# --- Config Response Models ---


class DbPoolStatus(BaseModel):
    """Database connection pool status."""
    pool_size: int
    checked_in: int
    checked_out: int
    overflow: int
    error: Optional[str] = None


class HealthCheckOut(BaseModel):
    """Health check response with database status."""
    status: str
    database: DbPoolStatus


class LoggedOut(BaseModel):
    """Client log response."""
    status: str


class SessionConfigOut(BaseModel):
    """Session config response."""
    capability_weights: Dict[str, Any]
    difficulty_weights: Dict[str, Any]
    novelty_reinforcement: Dict[str, Any]
    avg_mini_session_minutes: Dict[str, Any]
    wrap_up_threshold_minutes: int
    keys_per_intensity: Dict[str, Any]


class ConfigUpdateOut(BaseModel):
    """Config update response."""
    status: str
    updated: List[str] = []


class OnboardingOut(BaseModel):
    """Onboarding status response."""
    user_id: int
    instrument: Optional[str] = None
    resonant_note: Optional[str] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None
    comfortable_capabilities: List[str] = []
    day0_completed: bool = False
    day0_stage: int = 0


class OnboardingSaveOut(BaseModel):
    """Onboarding save response."""
    status: str
    user_id: int


class CacheStats(BaseModel):
    """Cache stats."""
    cached_items: Optional[int] = None
    max_size: Optional[int] = None
    cache_keys: Optional[List[str]] = None
    hits: Optional[int] = None
    misses: Optional[int] = None
    size: Optional[int] = None
    hit_rate: Optional[float] = None


class AudioStatusOut(BaseModel):
    """Audio status response."""
    music21_available: bool
    fluidsynth_available: bool
    use_direct_fluidsynth: bool
    soundfont_found: bool
    soundfont_path: Optional[str] = None
    can_render_audio: bool
    can_render_midi: bool
    cache: CacheStats
