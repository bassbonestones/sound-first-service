"""Session-related Pydantic models."""
from pydantic import BaseModel
from typing import List, Optional
import datetime


class OnboardingIn(BaseModel):
    user_id: int = 1
    instrument: str
    resonant_note: str
    range_low: Optional[str] = None  # e.g., "E3" - comfortable low note
    range_high: Optional[str] = None  # e.g., "C6" - comfortable high note
    comfortable_capabilities: List[str] = []


class SelfDirectedSessionIn(BaseModel):
    user_id: int = 1
    planned_duration_minutes: int = 30
    material_id: int
    focus_card_id: int
    goal_type: str


class PracticeAttemptIn(BaseModel):
    user_id: int
    material_id: int
    key: Optional[str] = None
    focus_card_id: Optional[int] = None
    rating: int
    fatigue: int
    timestamp: datetime.datetime


class MiniSessionOut(BaseModel):
    material_id: int
    material_title: str
    focus_card_id: int
    focus_card_name: str
    focus_card_description: str = ""
    focus_card_category: str = ""
    focus_card_attention_cue: str = ""
    focus_card_micro_cues: List[str] = []
    focus_card_prompts: dict = {}
    goal_type: str
    goal_label: str
    show_notation: bool
    target_key: str = None
    original_key_center: str = None
    resolved_musicxml: str = None
    starting_pitch: str = None


class PracticeSessionResponse(BaseModel):
    session_id: int
    user_id: int
    planned_duration_minutes: int
    generated_at: datetime.datetime
    mini_sessions: List[MiniSessionOut]


class FocusCardOut(BaseModel):
    id: int
    name: str
    description: str = ""
    category: str = ""
    attention_cue: str = ""
    micro_cues: List[str] = []
    prompts: dict = {}

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
