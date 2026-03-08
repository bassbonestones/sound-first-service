"""Teaching Module Pydantic schemas."""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


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


class LessonMastery(BaseModel):
    """Mastery criteria for a lesson."""
    correct_streak: int = 8
    min_accuracy: Optional[float] = None  # 0.0 to 1.0
    max_attempts: Optional[int] = None


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
    capability_name: str
    display_name: str
    description: Optional[str] = None
    icon: Optional[str] = None
    estimated_duration_minutes: Optional[int] = None
    difficulty_tier: int = 1


class ModuleSummary(ModuleBase):
    """Module summary for list views."""
    lesson_count: int
    prerequisite_module_ids: List[str] = []


class ModuleDetail(ModuleBase):
    """Full module details including lessons."""
    prerequisite_module_ids: List[str] = []
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
