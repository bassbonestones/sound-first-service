"""
Teaching Module Schema for Sound First

Architecture:
- TeachingModule: Groups lessons to teach a single capability
- Lesson: One step within a module, uses an exercise template
- ExerciseTemplate: Reusable interaction pattern (defined in JSON, not DB)
- UserModuleProgress: Tracks user's progress through modules
- UserLessonProgress: Tracks user's progress through individual lessons

Key insight: "Specialized pedagogy, reusable delivery templates"
- Many capabilities → Many lesson definitions → Few reusable exercise templates → Shared UI components
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Float, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from . import Base


class TeachingModule(Base):
    """
    A structured teaching path for a single capability.
    
    Example: "Pulse Tracking" module teaches the pulse_tracking capability
    through 4 sequential lessons (tap_along, feel_beat_one, enter_on_one, internal_pulse).
    """
    __tablename__ = 'teaching_modules'
    
    id = Column(String, primary_key=True)  # e.g., "pulse_tracking_module"
    # capability_name is nullable for modules that don't unlock a capability (e.g., range expansion)
    capability_name = Column(String, ForeignKey('capabilities.name'), nullable=True)
    
    display_name = Column(String, nullable=False)  # e.g., "Feel the Pulse"
    description = Column(String, nullable=True)  # User-facing explanation
    icon = Column(String, nullable=True)  # Icon identifier for UI
    
    # Prerequisites (JSON array of capability names that must be learned)
    prerequisite_capability_names = Column(String, default='[]')  # e.g., '["pulse_tracking"]'
    
    # Completion requirements
    completion_type = Column(String, default='all_required')  # 'all_required' | 'any_n'
    completion_count = Column(Integer, nullable=True)  # For 'any_n' type
    
    # Metadata
    estimated_duration_minutes = Column(Integer, nullable=True)
    difficulty_tier = Column(Integer, default=1)  # 1=foundational, 2=intermediate, 3=advanced
    
    # Ordering for display
    display_order = Column(Integer, default=0)
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    lessons = relationship("Lesson", back_populates="module", order_by="Lesson.sequence_order")


class Lesson(Base):
    """
    A single lesson within a teaching module.
    
    Each lesson uses an exercise template with specific configuration.
    Example: "Up or Down? (Easy)" uses the "pitch_direction" template
    configured for P5/P4 intervals only.
    """
    __tablename__ = 'lessons'
    
    id = Column(String, primary_key=True)  # e.g., "pulse_L1_tap_along"
    module_id = Column(String, ForeignKey('teaching_modules.id'), nullable=False)
    
    display_name = Column(String, nullable=False)  # e.g., "Tap Along"
    description = Column(String, nullable=True)  # User-facing explanation
    
    # Exercise template (references JSON template file, not DB)
    exercise_template_id = Column(String, nullable=False)  # e.g., "tap_with_beat"
    
    # Template configuration (JSON)
    config_json = Column(String, default='{}')  # Template-specific parameters
    
    # Mastery requirements (JSON)
    mastery_json = Column(String, default='{}')  # e.g., {"correct_streak": 8, "min_accuracy": 0.80}
    
    # Feedback configuration (JSON)
    feedback_json = Column(String, nullable=True)  # Custom feedback messages
    
    # Hints (JSON array)
    hints_json = Column(String, nullable=True)  # e.g., '["Close your eyes", "Feel the pulse"]'
    
    # Ordering
    sequence_order = Column(Integer, nullable=False)  # Order within module
    
    # Requirements
    is_required = Column(Boolean, default=True)  # Must complete for module completion
    unlock_condition = Column(String, default='previous')  # 'always' | 'previous' | custom
    
    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    module = relationship("TeachingModule", back_populates="lessons")


class UserModuleProgress(Base):
    """
    Tracks a user's progress through a teaching module.
    """
    __tablename__ = 'user_module_progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    module_id = Column(String, ForeignKey('teaching_modules.id'), nullable=False)
    
    # Status: not_started → in_progress → completed
    status = Column(String, default='not_started')
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    last_activity_at = Column(DateTime, nullable=True)
    
    # Indexes for fast queries
    __table_args__ = (
        Index('ix_user_module_progress_user_module', 'user_id', 'module_id', unique=True),
        Index('ix_user_module_progress_user_status', 'user_id', 'status'),
    )


class UserLessonProgress(Base):
    """
    Tracks a user's progress through an individual lesson.
    """
    __tablename__ = 'user_lesson_progress'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    lesson_id = Column(String, ForeignKey('lessons.id'), nullable=False)
    
    # Status: locked → available → in_progress → mastered
    status = Column(String, default='locked')
    
    # Progress tracking
    attempts = Column(Integer, default=0)
    correct_count = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)  # Current consecutive correct
    best_streak = Column(Integer, default=0)  # Best ever streak
    best_accuracy = Column(Float, nullable=True)  # Best accuracy achieved
    
    # Multi-key tracking: JSON array of completed starting notes/keys
    # e.g., '["F3", "G3"]' for fragment exercises completed in different keys
    keys_completed_json = Column(String, default='[]')
    
    # Timestamps
    started_at = Column(DateTime, nullable=True)
    mastered_at = Column(DateTime, nullable=True)
    last_attempt_at = Column(DateTime, nullable=True)
    
    # Indexes for fast queries
    __table_args__ = (
        Index('ix_user_lesson_progress_user_lesson', 'user_id', 'lesson_id', unique=True),
        Index('ix_user_lesson_progress_user_status', 'user_id', 'status'),
    )
    
    @property
    def keys_completed(self):
        """Get list of completed keys."""
        import json
        try:
            return json.loads(self.keys_completed_json or '[]')
        except json.JSONDecodeError:
            return []
    
    @keys_completed.setter
    def keys_completed(self, value):
        """Set list of completed keys."""
        import json
        self.keys_completed_json = json.dumps(value)


class LessonAttempt(Base):
    """
    Records each attempt at a lesson exercise.
    Used for analytics and adaptive difficulty.
    """
    __tablename__ = 'lesson_attempts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    lesson_id = Column(String, ForeignKey('lessons.id'), nullable=False)
    
    # Result
    is_correct = Column(Boolean, nullable=False)
    
    # Timing (for rhythm exercises)
    timing_error_ms = Column(Integer, nullable=True)  # Entry timing error in milliseconds
    duration_error_ms = Column(Integer, nullable=True)  # Duration error in milliseconds
    
    # Pitch (for pitch exercises)
    expected_answer = Column(String, nullable=True)  # What was expected
    given_answer = Column(String, nullable=True)  # What user gave
    
    # Exercise parameters at time of attempt (JSON)
    exercise_params_json = Column(String, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Indexes
    __table_args__ = (
        Index('ix_lesson_attempts_user_lesson', 'user_id', 'lesson_id'),
        Index('ix_lesson_attempts_created', 'created_at'),
    )
