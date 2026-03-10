from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table, Boolean, BigInteger
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
    
    # Interval tracking (replaces 24 individual interval capabilities)
    # Stores widest interval mastered, e.g., "P5" = perfect 5th in both directions
    # Intervals are taught in both directions before expanding
    max_melodic_interval = Column(String, nullable=True, default='M2')  # Start with major 2nd
    
    # Day 0 first-note experience tracking
    day0_completed = Column(Boolean, default=False)  # Whether user has completed Day 0 flow
    day0_stage = Column(Integer, default=0)  # Current stage in Day 0 (0-6)
    
    # Last selected instrument (persists across sessions)
    last_instrument_id = Column(Integer, ForeignKey('user_instruments.id'), nullable=True)
    
    # Bitmask columns for fast capability eligibility checks (8 x 64-bit = 512 capabilities max)
    cap_mask_0 = Column(BigInteger, default=0)  # capabilities 0-63
    cap_mask_1 = Column(BigInteger, default=0)  # capabilities 64-127
    cap_mask_2 = Column(BigInteger, default=0)  # capabilities 128-191
    cap_mask_3 = Column(BigInteger, default=0)  # capabilities 192-255
    cap_mask_4 = Column(BigInteger, default=0)  # capabilities 256-319
    cap_mask_5 = Column(BigInteger, default=0)  # capabilities 320-383
    cap_mask_6 = Column(BigInteger, default=0)  # capabilities 384-447
    cap_mask_7 = Column(BigInteger, default=0)  # capabilities 448-511

# Note: V1 Capability models have been retired.
# Use Capability and UserCapability from capability_schema.py instead.

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
    required_capability_ids = Column(String)  # Comma-separated or JSON (legacy, use material_capabilities)
    scaffolding_capability_ids = Column(String)  # Comma-separated or JSON
    musicxml_canonical = Column(String)  # TEXT
    original_key_center = Column(String, nullable=True)
    pitch_reference_type = Column(String)  # ENUM: TONAL | ANCHOR_INTERVAL | PITCH_CLASS
    pitch_ref_json = Column(String)  # JSONB as string
    spelling_policy = Column(String, default="from_key")
    
    # Bitmask columns for fast capability eligibility checks
    req_cap_mask_0 = Column(BigInteger, default=0)  # required capabilities 0-63
    req_cap_mask_1 = Column(BigInteger, default=0)  # required capabilities 64-127
    req_cap_mask_2 = Column(BigInteger, default=0)  # required capabilities 128-191
    req_cap_mask_3 = Column(BigInteger, default=0)  # required capabilities 192-255
    req_cap_mask_4 = Column(BigInteger, default=0)  # required capabilities 256-319
    req_cap_mask_5 = Column(BigInteger, default=0)  # required capabilities 320-383
    req_cap_mask_6 = Column(BigInteger, default=0)  # required capabilities 384-447
    req_cap_mask_7 = Column(BigInteger, default=0)  # required capabilities 448-511

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
    practice_mode = Column(String, default="guided")  # "guided" or "self_directed"

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
    
    # Off-course practice tracking
    is_off_course = Column(Boolean, default=False)  # True = manual practice of locked material
    was_eligible = Column(Boolean, default=True)  # False if material was not eligible at time of attempt
