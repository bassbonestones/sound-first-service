"""
Audio generation type definitions.

Includes error codes, error responses, and result types.
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional


class AudioErrorCode(str, Enum):
    """Error codes for audio generation failures."""
    MUSIC21_NOT_INSTALLED = "music21_not_installed"
    FLUIDSYNTH_NOT_INSTALLED = "fluidsynth_not_installed"
    SOUNDFONT_NOT_FOUND = "soundfont_not_found"
    INVALID_MUSICXML = "invalid_musicxml"
    TRANSPOSITION_FAILED = "transposition_failed"
    MIDI_CONVERSION_FAILED = "midi_conversion_failed"
    AUDIO_RENDER_FAILED = "audio_render_failed"
    FLUIDSYNTH_ERROR = "fluidsynth_error"
    TIMEOUT = "timeout"


@dataclass
class AudioError:
    """Structured error response for audio generation."""
    code: AudioErrorCode
    message: str
    detail: Optional[str] = None
    can_fallback: bool = False  # True if MIDI fallback is possible
    
    def to_dict(self) -> dict:
        return {
            "error": True,
            "code": self.code.value,
            "message": self.message,
            "detail": self.detail,
            "can_fallback": self.can_fallback,
        }


@dataclass
class AudioResult:
    """Result of audio generation."""
    success: bool
    data: Optional[bytes] = None
    content_type: str = "audio/wav"
    error: Optional[AudioError] = None
    is_fallback: bool = False  # True if returning MIDI instead of WAV
