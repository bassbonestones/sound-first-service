"""
Audio generation module for Sound First.

Transforms MusicXML to audio via:
1. music21: Parse MusicXML, transpose to target key
2. Export to MIDI
3. FluidSynth: Render MIDI to WAV using instrument soundfont

Usage:
    from app.audio import generate_audio_with_result, generate_single_note_audio
    
    # Generate audio from MusicXML
    result = generate_audio_with_result(musicxml, original_key, target_key, instrument)
    
    # Generate single note audio
    result = generate_single_note_audio("Bb3", "trombone", duration_beats=3)
"""

# Re-export types
from .types import AudioErrorCode, AudioError, AudioResult

# Re-export configuration
from .config import (
    MUSIC21_AVAILABLE,
    FLUIDSYNTH_AVAILABLE,
    SFIZZ_RENDER_AVAILABLE,
    MUSESCORE_AVAILABLE,
    SOUNDFONT_DIR,
    INSTRUMENT_PROGRAMS,
    SFZ_INSTRUMENTS,
    DEFAULT_OCTAVES,
    clear_audio_cache,
    get_cache_stats,
)

# Re-export transposition
from .transposition import get_transposition_interval, transpose_musicxml

# Re-export converters
from .converters import musicxml_to_midi, midi_to_audio, get_soundfont_path

# Re-export renderers
from .renderers import (
    render_pure_tone,
    render_note_with_sfizz,
    get_sfz_path,
    get_musescore_path,
    musicxml_to_wav_musescore,
)

# Re-export generators
from .generators import (
    generate_audio_with_result,
    generate_single_note_audio,
    generate_audio,
)

__all__ = [
    # Types
    "AudioErrorCode",
    "AudioError",
    "AudioResult",
    # Configuration
    "MUSIC21_AVAILABLE",
    "FLUIDSYNTH_AVAILABLE",
    "SFIZZ_RENDER_AVAILABLE",
    "MUSESCORE_AVAILABLE",
    "SOUNDFONT_DIR",
    "INSTRUMENT_PROGRAMS",
    "SFZ_INSTRUMENTS",
    "DEFAULT_OCTAVES",
    "clear_audio_cache",
    "get_cache_stats",
    # Transposition
    "get_transposition_interval",
    "transpose_musicxml",
    # Converters
    "musicxml_to_midi",
    "midi_to_audio",
    "get_soundfont_path",
    # Renderers
    "render_pure_tone",
    "render_note_with_sfizz",
    "get_sfz_path",
    "get_musescore_path",
    "musicxml_to_wav_musescore",
    # Generators
    "generate_audio_with_result",
    "generate_single_note_audio",
    "generate_audio",
]
