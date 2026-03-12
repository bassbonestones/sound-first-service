"""Teaching Module Pydantic schemas."""
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# Validation constants
MIN_BPM = 20
MAX_BPM = 300
MIN_DIFFICULTY_TIER = 1
MAX_DIFFICULTY_TIER = 10


class ModuleStatus(str, Enum):
    """Status of a user's progress through a module."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class LessonStatus(str, Enum):
    """Status of a user's progress through a lesson."""
    LOCKED = "locked"
    AVAILABLE = "available"
    IN_PROGRESS = "in_progress"
    MASTERED = "mastered"


# ============ Exercise Templates ============

class ExerciseTemplateInfo(BaseModel):
    """Information about an exercise template."""
    id: str
    display_name: str
    description: Optional[str] = None
    interaction_type: str  # listen_and_choose, call_and_response, etc.
    required_components: List[str]
    configurable_params: Dict[str, Any]


# ============ Lessons ============

class LessonConfig(BaseModel):
    """Configuration for a lesson's exercise template."""
    # Common configs
    bpm: Optional[int] = 60
    count_in_beats: Optional[int] = 4
    use_first_note: Optional[bool] = True
    
    # Pitch exercise configs
    allowed_answers: Optional[List[str]] = None  # ["up", "down", "same"]
    interval_pool: Optional[List[str]] = None  # ["P5", "P4", "M3"]
    sequence_length: Optional[int] = None
    
    # Rhythm exercise configs
    beats_per_measure: Optional[int] = None
    exercise_measures: Optional[int] = None
    target_beat: Optional[int] = None  # Which beat to enter on
    
    # Additional params stored as dict
    extra: Optional[Dict[str, Any]] = None

    @field_validator("bpm")
    @classmethod
    def validate_bpm(cls, v: Optional[int]) -> Optional[int]:
        """Validate BPM is within reasonable bounds."""
        if v is not None and (v < MIN_BPM or v > MAX_BPM):
            raise ValueError(f"bpm must be between {MIN_BPM} and {MAX_BPM}")
        return v

    @field_validator("count_in_beats")
    @classmethod
    def validate_count_in(cls, v: Optional[int]) -> Optional[int]:
        """Validate count_in_beats is positive."""
        if v is not None and v < 1:
            raise ValueError("count_in_beats must be at least 1")
        return v

    @field_validator("sequence_length", "beats_per_measure", "exercise_measures", "target_beat")
    @classmethod
    def validate_positive_ints(cls, v: Optional[int]) -> Optional[int]:
        """Validate integers are positive if provided."""
        if v is not None and v < 1:
            raise ValueError("Value must be at least 1")
        return v


class LessonMastery(BaseModel):
    """Mastery criteria for a lesson."""
    correct_streak: int = 8
    min_accuracy: Optional[float] = None  # 0.0 to 1.0
    max_attempts: Optional[int] = None
    keys_required: int = 1  # Number of different starting keys/notes required for mastery

    @field_validator("correct_streak")
    @classmethod
    def validate_streak(cls, v: int) -> int:
        """Validate correct_streak is positive."""
        if v < 1:
            raise ValueError("correct_streak must be at least 1")
        return v

    @field_validator("min_accuracy")
    @classmethod
    def validate_accuracy(cls, v: Optional[float]) -> Optional[float]:
        """Validate accuracy is between 0 and 1."""
        if v is not None and (v < 0.0 or v > 1.0):
            raise ValueError("min_accuracy must be between 0.0 and 1.0")
        return v

    @field_validator("max_attempts", "keys_required")
    @classmethod
    def validate_positive_ints(cls, v: Optional[int]) -> Optional[int]:
        """Validate integers are positive if provided."""
        if v is not None and v < 1:
            raise ValueError("Value must be at least 1")
        return v


class LessonBase(BaseModel):
    """Base lesson information."""
    id: str
    display_name: str
    description: Optional[str] = None
    exercise_template_id: str
    sequence_order: int
    is_required: bool = True


class LessonDetail(LessonBase):
    """Full lesson details including config."""
    config: LessonConfig
    mastery: LessonMastery
    hints: Optional[List[str]] = None


class LessonWithProgress(LessonBase):
    """Lesson with user's progress."""
    status: LessonStatus
    attempts: int = 0
    current_streak: int = 0
    best_streak: int = 0
    best_accuracy: Optional[float] = None


# ============ Modules ============

class ModuleBase(BaseModel):
    """Base module information."""
    id: str
    capability_name: Optional[str] = None  # Optional for modules that don't unlock a capability
    display_name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    difficulty_tier: int = 1

    @field_validator("difficulty_tier")
    @classmethod
    def validate_difficulty_tier(cls, v: int) -> int:
        """Validate difficulty_tier is within bounds."""
        if v < MIN_DIFFICULTY_TIER or v > MAX_DIFFICULTY_TIER:
            raise ValueError(f"difficulty_tier must be between {MIN_DIFFICULTY_TIER} and {MAX_DIFFICULTY_TIER}")
        return v

    @field_validator("estimated_duration_minutes")
    @classmethod
    def validate_duration(cls, v: Optional[int]) -> Optional[int]:
        """Validate duration is positive if provided."""
        if v is not None and v < 1:
            raise ValueError("estimated_duration_minutes must be at least 1")
        return v


class ModuleSummary(ModuleBase):
    """Module summary for list views."""
    lesson_count: int
    prerequisite_capability_names: List[str] = []


class ModuleDetail(ModuleBase):
    """Full module details including lessons."""
    prerequisite_capability_names: List[str] = []
    lessons: List[LessonDetail]
    completion_type: str = "all_required"
    completion_count: Optional[int] = None


class ModuleWithProgress(ModuleSummary):
    """Module with user's progress."""
    status: ModuleStatus
    lessons_completed: int = 0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# ============ Progress Tracking ============

class UserModuleProgressOut(BaseModel):
    """User's progress through a module."""
    module_id: str
    status: ModuleStatus
    lessons_completed: int
    total_lessons: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class UserLessonProgressOut(BaseModel):
    """User's progress through a lesson."""
    lesson_id: str
    status: LessonStatus
    attempts: int
    correct_count: int
    current_streak: int
    best_streak: int
    best_accuracy: Optional[float] = None
    keys_completed: List[str] = []  # List of completed starting notes/keys
    keys_required: int = 1  # Number of keys required for full mastery
    mastered_at: Optional[datetime] = None


# ============ Lesson Attempts ============

class LessonAttemptCreate(BaseModel):
    """Create a new lesson attempt."""
    lesson_id: str
    is_correct: bool
    timing_error_ms: Optional[int] = None
    duration_error_ms: Optional[int] = None
    expected_answer: Optional[str] = None
    given_answer: Optional[str] = None
    exercise_params: Optional[Dict[str, Any]] = None


class LessonAttemptOut(BaseModel):
    """Lesson attempt response."""
    id: int
    lesson_id: str
    is_correct: bool
    timing_error_ms: Optional[int] = None
    duration_error_ms: Optional[int] = None
    expected_answer: Optional[str] = None
    given_answer: Optional[str] = None
    created_at: datetime


class LessonAttemptResult(BaseModel):
    """Result after recording a lesson attempt."""
    attempt: LessonAttemptOut
    lesson_progress: UserLessonProgressOut
    lesson_mastered: bool = False
    module_completed: bool = False
    capability_unlocked: Optional[str] = None


# ============ API Requests ============

class StartModuleRequest(BaseModel):
    """Request to start a module."""
    module_id: str


class StartLessonRequest(BaseModel):
    """Request to start a lesson."""
    lesson_id: str


# ============ Exercise Generation ============

class GeneratedExercise(BaseModel):
    """A generated exercise for the mobile app."""
    exercise_template_id: str
    lesson_id: str
    
    # What to play/show
    model_notes: Optional[List[Dict[str, Any]]] = None  # [{pitch: "C4", duration_beats: 4}]
    model_rhythm: Optional[List[Dict[str, Any]]] = None  # [{type: "note", duration_beats: 1}]
    
    # For multiple choice
    choices: Optional[List[str]] = None
    correct_answer: Optional[str] = None
    
    # Timing
    bpm: int = 60
    count_in_beats: int = 4
    
    # Instructions
    instruction_text: str
    
    # Feedback
    feedback_correct: List[str]
    feedback_incorrect: List[str]


class ExerciseResultSubmit(BaseModel):
    """Submit result from completing an exercise."""
    lesson_id: str
    is_correct: bool
    response_time_ms: Optional[int] = None
    timing_error_ms: Optional[int] = None
    duration_error_ms: Optional[int] = None
    given_answer: Optional[str] = None


class LessonCompleteOut(BaseModel):
    """Response from marking a lesson complete."""
    status: str
    lesson_id: str
    lesson_mastered: bool
    keys_completed: List[str] = []
    keys_required: int
    module_completed: bool
    capability_unlocked: Optional[str] = None
