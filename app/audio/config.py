"""
Audio module configuration.

Contains availability checks, paths, instrument mappings, and cache settings.
"""

import shutil
from pathlib import Path
from typing import Dict, Tuple

# music21 for MusicXML parsing and transposition
try:
    from music21 import converter, interval, pitch, stream, midi as m21midi
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

# Check if FluidSynth is available on the system path
FLUIDSYNTH_AVAILABLE = shutil.which('fluidsynth') is not None

# Check if sfizz_render CLI is available (for high-quality SFZ instrument rendering)
SFIZZ_RENDER_AVAILABLE = shutil.which('sfizz_render') is not None

# MuseScore availability
from app.config import USE_MUSESCORE, MUSESCORE_PATH


def check_musescore_available() -> bool:
    """Check if MuseScore is available and configured."""
    if not USE_MUSESCORE:
        return False
    if Path(MUSESCORE_PATH).exists():
        return True
    # Try common locations
    common_paths = [
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "/usr/bin/mscore",
        "/usr/local/bin/mscore",
        shutil.which("mscore"),
    ]
    for p in common_paths:
        if p and Path(p).exists():
            return True
    return False


MUSESCORE_AVAILABLE = check_musescore_available()


# =============================================================================
# PATHS AND DEFAULTS
# =============================================================================

# Soundfont directory - will look for .sf2 files here
SOUNDFONT_DIR = Path(__file__).parent.parent.parent / "soundfonts"

# Default soundfont (General MIDI compatible)
# FluidR3_GM has cleaner, straighter tones than Timbres of Heaven
DEFAULT_SOUNDFONT = "FluidR3_GM.sf2"


# =============================================================================
# INSTRUMENT MAPPINGS
# =============================================================================

# Instrument to MIDI program mapping
# General MIDI program numbers (0-indexed)
INSTRUMENT_PROGRAMS = {
    "trumpet": 56,      # Trumpet
    "trombone": 57,     # Trombone
    "french_horn": 60,  # French Horn
    "tuba": 58,         # Tuba
    "flute": 73,        # Flute
    "clarinet": 71,     # Clarinet
    "oboe": 68,         # Oboe
    "bassoon": 70,      # Bassoon
    "saxophone": 65,    # Alto Sax
    "piano": 0,         # Acoustic Grand Piano
    "voice": 52,        # Choir Aahs (for singing reference)
}

# SFZ instruments - higher quality than SF2 soundfonts
# Maps instrument names to SFZ file paths (relative to SOUNDFONT_DIR)
# Uses sfizz_render CLI for proper loop/sustain support
SFZ_INSTRUMENTS = {
    "trombone": "Virtual-Playing-Orchestra3/Brass/trombone-SEC-sustain.sfz",
    "bass_trombone": "Virtual-Playing-Orchestra3/Brass/bass-trombone-SOLO-sustain.sfz",
}

# Default octaves for instruments when note has no octave
DEFAULT_OCTAVES = {
    "trumpet": 4,
    "trombone": 3,
    "french_horn": 3,
    "tuba": 2,
    "flute": 5,
    "clarinet": 4,
    "oboe": 4,
    "bassoon": 3,
    "saxophone": 4,
    "piano": 4,
    "voice": 4,
}


# =============================================================================
# CACHES
# =============================================================================

# Short-term cache for generated audio
# Key: (material_id, target_key, instrument) -> audio bytes
_audio_cache: Dict[Tuple[int, str, str], bytes] = {}
_cache_max_size = 10  # Keep last N generated audio files

# Cache for single-note audio
_single_note_cache: Dict[Tuple[str, str, int], bytes] = {}
_single_note_cache_max = 50


def get_audio_cache() -> Dict[Tuple[int, str, str], bytes]:
    """Get the audio cache dictionary."""
    return _audio_cache


def get_single_note_cache() -> Dict[Tuple[str, str, int], bytes]:
    """Get the single note cache dictionary."""
    return _single_note_cache


def clear_audio_cache():
    """Clear all cached audio."""
    _audio_cache.clear()


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return {
        "cached_items": len(_audio_cache),
        "max_size": _cache_max_size,
        "cache_keys": list(_audio_cache.keys()),
    }
