from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean
from sqlalchemy.orm import relationship
from . import Base

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    instrument = Column(String, nullable=True)
    resonant_note = Column(String, nullable=True)
    comfortable_capabilities = Column(String, nullable=True)  # Comma-separated or JSON
    range_low = Column(String, nullable=True)  # e.g., "E3" for low comfortable note
    range_high = Column(String, nullable=True)  # e.g., "C6" for high comfortable note

class Capability(Base):
    """Musical literacy element with optional teaching content."""
    __tablename__ = 'capabilities'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    
    # Teaching content fields
    domain = Column(String, nullable=True)  # Category: clef, note_value, time_signature, key, articulation, dynamic, expression
    sequence_order = Column(Integer, nullable=True)  # Order for introduction (lower = earlier)
    display_name = Column(String, nullable=True)  # Human-readable name: "Triplets"
    explanation = Column(String, nullable=True)  # Teaching explanation text
    visual_example_url = Column(String, nullable=True)  # URL to notation image
    audio_example_url = Column(String, nullable=True)  # URL to audio demonstration
    
    # Quiz fields
    quiz_type = Column(String, nullable=True)  # visual_mc, listening_discrimination, tap_rhythm
    quiz_question = Column(String, nullable=True)  # The quiz question text
    quiz_options = Column(String, nullable=True)  # JSON array of options (for MC)
    quiz_answer = Column(String, nullable=True)  # Correct answer


class UserCapabilityProgress(Base):
    """Tracks which capabilities a user has been taught."""
    __tablename__ = 'user_capability_progress'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    capability_id = Column(Integer, ForeignKey('capabilities.id'), nullable=False)
    introduced_at = Column(DateTime, nullable=True)  # When the mini-lesson was shown
    quiz_passed = Column(Boolean, default=False)  # Whether quiz was passed
    times_refreshed = Column(Integer, default=0)  # How many times accessed via help menu


class UserCapability(Base):
    __tablename__ = 'user_capabilities'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    capability_id = Column(Integer, ForeignKey('capabilities.id'), nullable=False)

class UserRange(Base):
    __tablename__ = 'user_ranges'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    range_low = Column(String)
    range_high = Column(String)

class Material(Base):
    __tablename__ = 'materials'
    id = Column(Integer, primary_key=True)
    title = Column(String, nullable=False)
    allowed_keys = Column(String)  # Comma-separated or JSON
    required_capability_ids = Column(String)  # Comma-separated or JSON
    scaffolding_capability_ids = Column(String)  # Comma-separated or JSON
    musicxml_canonical = Column(String)  # TEXT
    original_key_center = Column(String, nullable=True)
    pitch_reference_type = Column(String)  # ENUM: TONAL | ANCHOR_INTERVAL | PITCH_CLASS
    pitch_ref_json = Column(String)  # JSONB as string
    spelling_policy = Column(String, default="from_key")

class FocusCard(Base):
    __tablename__ = 'focus_cards'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)
    description = Column(String, nullable=True)
    category = Column(String, nullable=True)
    attention_cue = Column(String, nullable=True)
    micro_cues = Column(String, nullable=True)  # JSON array as string
    prompts = Column(String, nullable=True)  # JSON object as string

class PracticeSession(Base):
    __tablename__ = 'practice_sessions'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)

class MiniSession(Base):
    __tablename__ = 'mini_sessions'
    id = Column(Integer, primary_key=True)
    practice_session_id = Column(Integer, ForeignKey('practice_sessions.id'), nullable=False)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    key = Column(String)
    focus_card_id = Column(Integer, ForeignKey('focus_cards.id'))
    goal_type = Column(String)
    current_step_index = Column(Integer, default=0)
    is_completed = Column(Boolean, default=False)
    attempt_count = Column(Integer, default=0)  # For range expansion - max 3 attempts
    strain_detected = Column(Boolean, default=False)


class CurriculumStep(Base):
    """Individual step within a mini-session following the ear-first doctrine."""
    __tablename__ = 'curriculum_steps'
    id = Column(Integer, primary_key=True)
    mini_session_id = Column(Integer, ForeignKey('mini_sessions.id'), nullable=False)
    step_index = Column(Integer, nullable=False)  # Order within the mini-session
    step_type = Column(String, nullable=False)  # LISTEN, SING, IMAGINE, PLAY, REFLECT, RECOVERY
    instruction = Column(String)  # What to do in this step
    prompt = Column(String)  # Focus card prompt for this step type
    is_completed = Column(Boolean, default=False)
    rating = Column(Integer, nullable=True)  # User's rating for REFLECT steps
    notes = Column(String, nullable=True)  # Optional user notes

class PracticeAttempt(Base):
    __tablename__ = 'practice_attempts'
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    material_id = Column(Integer, ForeignKey('materials.id'), nullable=False)
    key = Column(String)
    focus_card_id = Column(Integer, ForeignKey('focus_cards.id'))
    rating = Column(Integer)
    fatigue = Column(Integer)
    timestamp = Column(DateTime)
