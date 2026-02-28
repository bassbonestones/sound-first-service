from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Table
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

class Capability(Base):
    __tablename__ = 'capabilities'
    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True, nullable=False)

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
