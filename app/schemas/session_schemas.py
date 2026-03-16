"""Session-related Pydantic models."""
from pydantic import BaseModel, field_validator
from typing import Any, Dict, List, Optional
import datetime
import re


# Validation constants
MIN_RATING = 1
MAX_RATING = 5
MIN_FATIGUE = 0
MAX_FATIGUE = 10
MIN_DURATION_MINUTES = 1
MAX_DURATION_MINUTES = 180
# Note format: letter + optional accidental + octave (e.g., "C4", "F#3", "Bb5")
NOTE_PATTERN = re.compile(r"^[A-Ga-g][#b]?[0-9]$")


class OnboardingIn(BaseModel):
    user_id: int = 1
    instrument: str
    resonant_note: str
    range_low: Optional[str] = None  # e.g., "E3" - comfortable low note
    range_high: Optional[str] = None  # e.g., "C6" - comfortable high note
    comfortable_capabilities: List[str] = []

    @field_validator("resonant_note")
    @classmethod
    def validate_resonant_note(cls, v: str) -> str:
        """Validate resonant_note is a valid note format."""
        if not NOTE_PATTERN.match(v):
            raise ValueError(f"resonant_note must be a valid note (e.g., 'C4', 'F#3', 'Bb5'), got '{v}'")
        return v

    @field_validator("range_low", "range_high")
    @classmethod
    def validate_range_notes(cls, v: Optional[str]) -> Optional[str]:
        """Validate range notes are valid note format."""
        if v is not None and not NOTE_PATTERN.match(v):
            raise ValueError(f"Range note must be a valid note (e.g., 'E3', 'C6'), got '{v}'")
        return v


class SelfDirectedSessionIn(BaseModel):
    user_id: int = 1
    planned_duration_minutes: int = 30
    material_id: int
    focus_card_id: int
    goal_type: str

    @field_validator("planned_duration_minutes")
    @classmethod
    def validate_duration(cls, v: int) -> int:
        """Validate duration is within reasonable bounds."""
        if v < MIN_DURATION_MINUTES or v > MAX_DURATION_MINUTES:
            raise ValueError(f"planned_duration_minutes must be between {MIN_DURATION_MINUTES} and {MAX_DURATION_MINUTES}")
        return v


class PracticeAttemptIn(BaseModel):
    user_id: int
    material_id: int
    key: Optional[str] = None
    focus_card_id: Optional[int] = None
    rating: int
    fatigue: int
    timestamp: datetime.datetime

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: int) -> int:
        """Validate rating is within bounds (1-5)."""
        if v < MIN_RATING or v > MAX_RATING:
            raise ValueError(f"rating must be between {MIN_RATING} and {MAX_RATING}")
        return v

    @field_validator("fatigue")
    @classmethod
    def validate_fatigue(cls, v: int) -> int:
        """Validate fatigue is within bounds (0-10)."""
        if v < MIN_FATIGUE or v > MAX_FATIGUE:
            raise ValueError(f"fatigue must be between {MIN_FATIGUE} and {MAX_FATIGUE}")
        return v


class MiniSessionOut(BaseModel):
    """A mini-session can be either a material-based session or a teaching module lesson."""
    # Session type discriminator: "material" or "teaching_module"
    session_type: str = "material"
    
    # Material-based session fields (populated when session_type == "material")
    material_id: Optional[int] = None
    material_title: Optional[str] = None
    focus_card_id: Optional[int] = None
    focus_card_name: Optional[str] = None
    focus_card_description: str = ""
    focus_card_category: str = ""
    focus_card_attention_cue: str = ""
    focus_card_micro_cues: List[str] = []
    focus_card_prompts: Dict[str, Any] = {}
    goal_type: Optional[str] = None
    goal_label: Optional[str] = None
    show_notation: bool = False
    target_key: Optional[str] = None
    original_key_center: Optional[str] = None
    resolved_musicxml: Optional[str] = None
    starting_pitch: Optional[str] = None
    
    # Teaching module session fields (populated when session_type == "teaching_module")
    module_id: Optional[str] = None
    module_display_name: Optional[str] = None
    module_description: Optional[str] = None
    lesson_id: Optional[str] = None
    lesson_display_name: Optional[str] = None
    lesson_description: Optional[str] = None
    exercise_template_id: Optional[str] = None
    exercise_config: Optional[Dict[str, Any]] = None
    mastery_config: Optional[Dict[str, Any]] = None
    hints: Optional[List[str]] = None
    capability_name: Optional[str] = None


class PracticeSessionResponse(BaseModel):
    session_id: int
    user_id: int
    planned_duration_minutes: int
    generated_at: datetime.datetime
    mini_sessions: List[MiniSessionOut]
    user_resonant_note: Optional[str] = None  # User's first note for teaching modules


class FocusCardOut(BaseModel):
    id: int
    name: str
    description: str = ""
    category: str = ""
    attention_cue: str = ""
    micro_cues: List[str] = []
    prompts: Dict[str, Any] = {}

    class Config:
        from_attributes = True


class CurriculumStepOut(BaseModel):
    id: int
    step_index: int
    step_type: str
    instruction: str
    prompt: str = ""
    is_completed: bool = False
    rating: Optional[int] = None


class MiniSessionWithStepsOut(BaseModel):
    mini_session_id: int
    material_title: str
    focus_card_name: str
    focus_card_attention_cue: str
    goal_type: str
    goal_label: str
    target_key: str
    current_step_index: int
    is_completed: bool
    steps: List[CurriculumStepOut]


class StepCompleteIn(BaseModel):
    rating: Optional[int] = None
    notes: Optional[str] = None
    strain_detected: bool = False


# --- Response Models ---


class PracticeAttemptOut(BaseModel):
    """Practice attempt response."""
    status: str
    attempt_id: int


class PracticeAttemptDetailOut(BaseModel):
    """Practice attempt detail."""
    id: int
    material_id: int
    key: Optional[str] = None
    focus_card_id: Optional[int] = None
    rating: Optional[int] = None
    fatigue: Optional[int] = None
    timestamp: Optional[str] = None


class SessionCompleteOut(BaseModel):
    """Session completion response."""
    status: str
    session_id: int


class StepCompleteOut(BaseModel):
    """Step completion response with varying status."""
    status: str
    message: Optional[str] = None
    next_step_index: Optional[int] = None
    next_step_type: Optional[str] = None
    next_instruction: Optional[str] = None
    attempt_count: Optional[int] = None
    is_range_work: Optional[bool] = None


class SessionCompleteStatusOut(BaseModel):
    """Session complete status response."""
    status: str
    message: str
