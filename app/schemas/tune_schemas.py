"""Tune-related Pydantic models for user-composed tunes.

Schemas for CRUD operations on tunes, including chord progressions support.
"""
from pydantic import BaseModel, field_validator
from typing import List, Optional, Dict, Any
from datetime import datetime


# =============================================================================
# Nested Types (matching mobile TypeScript types)
# =============================================================================

class TimeSignature(BaseModel):
    """Time signature configuration."""
    beats: int
    beatUnit: int

    @field_validator("beats")
    @classmethod
    def validate_beats(cls, v: int) -> int:
        if v < 1 or v > 16:
            raise ValueError("beats must be between 1 and 16")
        return v

    @field_validator("beatUnit")
    @classmethod
    def validate_beat_unit(cls, v: int) -> int:
        valid_units = [1, 2, 4, 8, 16]
        if v not in valid_units:
            raise ValueError(f"beatUnit must be one of {valid_units}")
        return v


class ChordSymbol(BaseModel):
    """A chord symbol at a specific position in the score."""
    id: str
    symbol: str  # e.g., "Cmaj7", "Dm7b5", "G7#9"
    beatPosition: float  # Position within measure (0 = beat 1)
    measureIndex: int


class ChordProgression(BaseModel):
    """A named chord progression containing chord symbols."""
    id: str
    name: str
    isDefault: bool = False
    isAutoInferred: Optional[bool] = None
    isSystemDefined: Optional[bool] = None
    chords: List[ChordSymbol] = []


class DisplaySettings(BaseModel):
    """Score display settings."""
    showChordSymbols: bool = True
    activeProgressionId: Optional[str] = None


class PlaybackSettings(BaseModel):
    """Score playback settings."""
    accompanimentStyle: Optional[str] = None
    accompanimentVolume: Optional[float] = None


# =============================================================================
# CRUD Schemas
# =============================================================================

class TuneCreate(BaseModel):
    """Input model for creating a new tune."""
    title: str
    clef: str = "treble"
    key_signature: int = 0
    time_signature: TimeSignature = TimeSignature(beats=4, beatUnit=4)
    tempo: int = 120
    measures_json: str  # JSON string of measures array
    chord_progressions: List[ChordProgression] = []
    display_settings: DisplaySettings = DisplaySettings()
    playback_settings: PlaybackSettings = PlaybackSettings()
    imported_from: Optional[str] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip()

    @field_validator("clef")
    @classmethod
    def validate_clef(cls, v: str) -> str:
        if v not in ("treble", "bass"):
            raise ValueError("clef must be 'treble' or 'bass'")
        return v

    @field_validator("key_signature")
    @classmethod
    def validate_key_signature(cls, v: int) -> int:
        if v < -7 or v > 7:
            raise ValueError("key_signature must be between -7 and 7")
        return v

    @field_validator("tempo")
    @classmethod
    def validate_tempo(cls, v: int) -> int:
        if v < 20 or v > 400:
            raise ValueError("tempo must be between 20 and 400 BPM")
        return v


class TuneUpdate(BaseModel):
    """Input model for updating an existing tune."""
    title: Optional[str] = None
    clef: Optional[str] = None
    key_signature: Optional[int] = None
    time_signature: Optional[TimeSignature] = None
    tempo: Optional[int] = None
    measures_json: Optional[str] = None
    chord_progressions: Optional[List[ChordProgression]] = None
    display_settings: Optional[DisplaySettings] = None
    playback_settings: Optional[PlaybackSettings] = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not v.strip():
            raise ValueError("title cannot be empty")
        return v.strip() if v else v

    @field_validator("clef")
    @classmethod
    def validate_clef(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("treble", "bass"):
            raise ValueError("clef must be 'treble' or 'bass'")
        return v

    @field_validator("key_signature")
    @classmethod
    def validate_key_signature(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < -7 or v > 7):
            raise ValueError("key_signature must be between -7 and 7")
        return v

    @field_validator("tempo")
    @classmethod
    def validate_tempo(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and (v < 20 or v > 400):
            raise ValueError("tempo must be between 20 and 400 BPM")
        return v


class TuneResponse(BaseModel):
    """Response model for a single tune."""
    id: int
    user_id: int
    title: str
    clef: str
    key_signature: int
    time_signature: TimeSignature
    tempo: int
    measures_json: str
    chord_progressions: List[ChordProgression]
    display_settings: DisplaySettings
    playback_settings: PlaybackSettings
    imported_from: Optional[str]
    created_at: datetime
    updated_at: datetime
    is_archived: bool

    class Config:
        from_attributes = True


class TuneListItem(BaseModel):
    """Response model for tune list (without full measures data)."""
    id: int
    title: str
    clef: str
    key_signature: int
    tempo: int
    measure_count: int
    has_chord_progressions: bool
    imported_from: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TuneListResponse(BaseModel):
    """Response model for listing user's tunes."""
    tunes: List[TuneListItem]
    total_count: int
