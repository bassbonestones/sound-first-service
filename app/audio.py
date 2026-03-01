"""
Audio generation module for Sound First.

Transforms MusicXML to audio via:
1. music21: Parse MusicXML, transpose to target key
2. Export to MIDI
3. FluidSynth: Render MIDI to WAV using instrument soundfont

Phase 1: Simple MIDI rendering with basic soundfonts
Phase 2: Higher quality soundfonts, better articulation
Phase 3: Offline caching for mobile playback
"""

import os
import io
import tempfile
import hashlib
from typing import Optional, Tuple, Dict
from pathlib import Path
from enum import Enum
from dataclasses import dataclass


# =============================================================================
# ERROR HANDLING
# =============================================================================

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

# music21 for MusicXML parsing and transposition
try:
    from music21 import converter, interval, pitch, stream, midi as m21midi
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

# Check if FluidSynth is available on the system path
import shutil
FLUIDSYNTH_AVAILABLE = shutil.which('fluidsynth') is not None


# =============================================================================
# CONFIGURATION
# =============================================================================

# Soundfont directory - will look for .sf2 files here
SOUNDFONT_DIR = Path(__file__).parent.parent / "soundfonts"

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

# Default soundfont (General MIDI compatible)
DEFAULT_SOUNDFONT = "GeneralUser_GS.sf2"

# Short-term cache for generated audio
# Key: (material_id, target_key, instrument) -> audio bytes
_audio_cache: Dict[Tuple[int, str, str], bytes] = {}
_cache_max_size = 10  # Keep last N generated audio files


# =============================================================================
# TRANSPOSITION
# =============================================================================

def get_transposition_interval(from_key: str, to_key: str) -> Optional[int]:
    """
    Calculate semitone interval between two keys.
    
    Returns the smallest interval (within -6 to +6 semitones).
    
    Args:
        from_key: Original key (e.g., "C major", "G minor")
        to_key: Target key (e.g., "Bb major", "D minor")
        
    Returns:
        Semitone interval (positive = up, negative = down)
    """
    if not MUSIC21_AVAILABLE:
        return None
    
    try:
        from music21 import key as m21key
        
        # Parse keys
        from_k = m21key.Key(from_key.replace(" major", "").replace(" minor", ""))
        to_k = m21key.Key(to_key.replace(" major", "").replace(" minor", ""))
        
        # Get tonic pitches
        from_pitch = from_k.tonic
        to_pitch = to_k.tonic
        
        # Calculate interval
        intvl = interval.Interval(from_pitch, to_pitch)
        semitones = intvl.semitones
        
        # Normalize to smallest interval (-6 to +6)
        while semitones > 6:
            semitones -= 12
        while semitones < -6:
            semitones += 12
            
        return semitones
    except Exception as e:
        print(f"Error calculating transposition: {e}")
        return None


def transpose_musicxml(musicxml_content: str, semitones: int) -> Optional[str]:
    """
    Transpose MusicXML content by given semitones.
    
    Args:
        musicxml_content: Raw MusicXML string
        semitones: Number of semitones to transpose (positive = up)
        
    Returns:
        Transposed MusicXML string, or None on error
    """
    if not MUSIC21_AVAILABLE:
        return None
    
    try:
        # Parse MusicXML
        score = converter.parse(musicxml_content)
        
        # Create transposition interval
        trans_interval = interval.Interval(semitones)
        
        # Transpose the score
        transposed = score.transpose(trans_interval)
        
        # Export back to MusicXML
        return transposed.write('musicxml').read_text()
    except Exception as e:
        print(f"Error transposing MusicXML: {e}")
        return None


# =============================================================================
# MIDI GENERATION
# =============================================================================

def musicxml_to_midi(musicxml_content: str, instrument: str = "piano") -> Optional[bytes]:
    """
    Convert MusicXML to MIDI bytes.
    
    Args:
        musicxml_content: Raw MusicXML string
        instrument: Instrument name for program change
        
    Returns:
        MIDI file bytes, or None on error
    """
    if not MUSIC21_AVAILABLE:
        return None
    
    try:
        from music21 import instrument as m21instrument
        
        # Parse MusicXML
        score = converter.parse(musicxml_content)
        
        # Normalize instrument name (handle spaces, case variations)
        norm_instrument = instrument.lower().replace(" ", "_").replace("-", "_")
        
        # Map instrument name to music21 instrument class
        instrument_map = {
            # Brass
            "trumpet": m21instrument.Trumpet,
            "trombone": m21instrument.Trombone,
            "bass_trombone": m21instrument.BassTrombone,
            "tenor_trombone": m21instrument.Trombone,
            "french_horn": m21instrument.Horn,
            "euphonium": m21instrument.Tuba,  # music21 doesn't have Euphonium
            "tuba": m21instrument.Tuba,
            # Woodwinds
            "flute": m21instrument.Flute,
            "clarinet": m21instrument.Clarinet,
            "oboe": m21instrument.Oboe,
            "bassoon": m21instrument.Bassoon,
            "saxophone": m21instrument.Saxophone,
            "alto_saxophone": m21instrument.AltoSaxophone,
            "tenor_saxophone": m21instrument.TenorSaxophone,
            "baritone_saxophone": m21instrument.BaritoneSaxophone,
            # Strings
            "violin": m21instrument.Violin,
            "viola": m21instrument.Viola,
            "cello": m21instrument.Violoncello,
            "double_bass": m21instrument.Contrabass,
            "guitar": m21instrument.AcousticGuitar,
            # Keyboard
            "piano": m21instrument.Piano,
            "organ": m21instrument.PipeOrgan,
            # Voice
            "voice": m21instrument.Vocalist,
            "voice_(general)": m21instrument.Vocalist,
            "soprano": m21instrument.Soprano,
            "alto": m21instrument.Alto,
            "tenor": m21instrument.Tenor,
            "bass_voice": m21instrument.Bass,
        }
        
        # Get instrument class (default to piano)
        InstrumentClass = instrument_map.get(norm_instrument, m21instrument.Piano)
        
        # Set instrument on all parts
        for part in score.parts:
            # Remove any existing instruments
            part.removeByClass(m21instrument.Instrument)
            # Insert new instrument at the beginning
            inst = InstrumentClass()
            part.insert(0, inst)
        
        # Write to MIDI
        midi_file = score.write('midi')
        with open(midi_file, 'rb') as f:
            return f.read()
    except Exception as e:
        print(f"Error converting to MIDI: {e}")
        return None


# =============================================================================
# AUDIO RENDERING
# =============================================================================

def get_soundfont_path(instrument: str = "piano") -> Optional[Path]:
    """
    Get path to soundfont file for instrument.
    
    Falls back to default General MIDI soundfont.
    """
    # Ensure soundfont directory exists
    SOUNDFONT_DIR.mkdir(exist_ok=True)
    
    # Look for instrument-specific soundfont first
    specific_sf = SOUNDFONT_DIR / f"{instrument.lower()}.sf2"
    if specific_sf.exists():
        return specific_sf
    
    # Fall back to default
    default_sf = SOUNDFONT_DIR / DEFAULT_SOUNDFONT
    if default_sf.exists():
        return default_sf
    
    # Look for any .sf2 file in the soundfonts directory
    sf2_files = list(SOUNDFONT_DIR.glob("*.sf2"))
    if sf2_files:
        return sf2_files[0]
    
    # Try common locations
    common_paths = [
        Path("/usr/share/sounds/sf2/FluidR3_GM.sf2"),
        Path("/usr/share/soundfonts/FluidR3_GM2-2.sf2"),
        Path("C:/soundfonts/GeneralUser_GS.sf2"),
        Path("C:/tools/fluidsynth/share/soundfonts"),
    ]
    for p in common_paths:
        if p.exists():
            if p.is_dir():
                sf2_in_dir = list(p.glob("*.sf2"))
                if sf2_in_dir:
                    return sf2_in_dir[0]
            else:
                return p
    
    return None


def midi_to_audio(midi_bytes: bytes, soundfont_path: Optional[Path] = None) -> Optional[bytes]:
    """
    Render MIDI to WAV audio using FluidSynth.
    
    Uses direct subprocess call or midi2audio library based on USE_DIRECT_FLUIDSYNTH config.
    Direct mode works better behind corporate firewalls.
    
    Args:
        midi_bytes: MIDI file content
        soundfont_path: Path to .sf2 soundfont file
        
    Returns:
        WAV audio bytes, or None on error
    """
    from app.config import USE_DIRECT_FLUIDSYNTH
    
    if soundfont_path is None:
        soundfont_path = get_soundfont_path()
    
    if soundfont_path is None or not soundfont_path.exists():
        print("No soundfont file found. Please add a .sf2 file to the soundfonts/ directory.")
        return None
    
    try:
        # Write MIDI to temp file
        with tempfile.NamedTemporaryFile(suffix='.mid', delete=False) as midi_tmp:
            midi_tmp.write(midi_bytes)
            midi_path = midi_tmp.name
        
        # Create output file path
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_tmp:
            wav_path = wav_tmp.name
        
        if USE_DIRECT_FLUIDSYNTH:
            # Direct subprocess call - works behind corporate firewalls
            import subprocess
            cmd = [
                'fluidsynth',
                '-ni',                      # Non-interactive mode
                '-F', wav_path,             # Output WAV file
                '-r', '44100',              # Sample rate
                str(soundfont_path),        # Soundfont
                midi_path                   # Input MIDI
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode != 0:
                print(f"FluidSynth error: {result.stderr}")
                return None
        else:
            # Use midi2audio library
            try:
                from midi2audio import FluidSynth
                fs = FluidSynth(str(soundfont_path))
                fs.midi_to_audio(midi_path, wav_path)
            except ImportError:
                print("midi2audio not installed. Run: pip install midi2audio")
                return None
        
        # Read WAV bytes
        with open(wav_path, 'rb') as f:
            wav_bytes = f.read()
        
        # Cleanup temp files
        os.unlink(midi_path)
        os.unlink(wav_path)
        
        return wav_bytes
    except Exception as e:
        print(f"Error rendering audio: {e}")
        return None


# =============================================================================
# HIGH-LEVEL API
# =============================================================================

def generate_audio_with_result(
    musicxml_content: str,
    original_key: str,
    target_key: str,
    instrument: str = "piano",
    material_id: Optional[int] = None,
) -> AudioResult:
    """
    Generate audio from MusicXML with detailed result.
    
    Returns AudioResult with success/error information.
    """
    # Check cache first
    cache_key = (material_id, target_key, instrument) if material_id else None
    if cache_key and cache_key in _audio_cache:
        return AudioResult(success=True, data=_audio_cache[cache_key], content_type="audio/wav")
    
    # Check music21
    if not MUSIC21_AVAILABLE:
        return AudioResult(
            success=False,
            error=AudioError(
                code=AudioErrorCode.MUSIC21_NOT_INSTALLED,
                message="Audio library not available",
                detail="music21 is required for audio generation. Install with: pip install music21",
                can_fallback=False
            )
        )
    
    # Validate MusicXML content
    if not musicxml_content or len(musicxml_content.strip()) < 10:
        return AudioResult(
            success=False,
            error=AudioError(
                code=AudioErrorCode.INVALID_MUSICXML,
                message="Invalid or empty notation content",
                detail="The material has no valid MusicXML notation",
                can_fallback=False
            )
        )
    
    # Calculate and apply transposition
    transposition_applied = False
    if original_key and target_key and original_key != target_key:
        semitones = get_transposition_interval(original_key, target_key)
        if semitones is None:
            # Couldn't parse keys - continue without transposition
            pass
        elif semitones != 0:
            transposed_xml = transpose_musicxml(musicxml_content, semitones)
            if transposed_xml:
                musicxml_content = transposed_xml
                transposition_applied = True
    
    # Convert to MIDI
    midi_bytes = musicxml_to_midi(musicxml_content, instrument)
    if not midi_bytes:
        return AudioResult(
            success=False,
            error=AudioError(
                code=AudioErrorCode.MIDI_CONVERSION_FAILED,
                message="Could not convert notation to MIDI",
                detail="The MusicXML content could not be parsed. Check notation syntax.",
                can_fallback=False
            )
        )
    
    # Check FluidSynth and soundfont
    soundfont = get_soundfont_path(instrument)
    
    if not FLUIDSYNTH_AVAILABLE:
        # Return MIDI as fallback
        return AudioResult(
            success=True,
            data=midi_bytes,
            content_type="audio/midi",
            is_fallback=True,
            error=AudioError(
                code=AudioErrorCode.FLUIDSYNTH_NOT_INSTALLED,
                message="Audio renderer not available - returning MIDI",
                detail="FluidSynth is not installed. Install it for WAV playback.",
                can_fallback=True
            )
        )
    
    if not soundfont:
        # Return MIDI as fallback
        return AudioResult(
            success=True,
            data=midi_bytes,
            content_type="audio/midi",
            is_fallback=True,
            error=AudioError(
                code=AudioErrorCode.SOUNDFONT_NOT_FOUND,
                message="Soundfont not found - returning MIDI",
                detail="Add a .sf2 file to soundfonts/ directory for WAV playback. See soundfonts/README.md",
                can_fallback=True
            )
        )
    
    # Render to WAV
    wav_bytes = midi_to_audio(midi_bytes, soundfont)
    if not wav_bytes:
        # Return MIDI as fallback
        return AudioResult(
            success=True,
            data=midi_bytes,
            content_type="audio/midi",
            is_fallback=True,
            error=AudioError(
                code=AudioErrorCode.AUDIO_RENDER_FAILED,
                message="Audio rendering failed - returning MIDI",
                detail="FluidSynth could not render audio. Check logs for details.",
                can_fallback=True
            )
        )
    
    # Cache successful result
    if cache_key:
        if len(_audio_cache) >= _cache_max_size:
            oldest = next(iter(_audio_cache))
            del _audio_cache[oldest]
        _audio_cache[cache_key] = wav_bytes
    
    return AudioResult(success=True, data=wav_bytes, content_type="audio/wav")


# =============================================================================
# SINGLE NOTE AUDIO GENERATION (Day 0)
# =============================================================================

# Cache for single-note audio
_single_note_cache: Dict[Tuple[str, str, int], bytes] = {}
_single_note_cache_max = 50


def generate_single_note_audio(
    note_name: str,
    instrument: str = "piano",
    duration_beats: int = 4,  # whole note = 4 beats
    octave: Optional[int] = None,
) -> AudioResult:
    """
    Generate audio for a single sustained note.
    
    Used for Day 0 first-note experience - plays a whole note for the user's
    resonant pitch so they can listen, sing, and match it.
    
    Args:
        note_name: Note name with optional octave (e.g., "Bb4", "F#3", "C")
                   If no octave, defaults based on instrument range.
        instrument: Instrument for soundfont rendering
        duration_beats: Duration in beats (4 = whole note in 4/4)
        octave: Override octave (useful if note_name has no octave)
    
    Returns:
        AudioResult with WAV audio (or MIDI fallback)
    """
    if not MUSIC21_AVAILABLE:
        return AudioResult(
            success=False,
            error=AudioError(
                code=AudioErrorCode.MUSIC21_NOT_INSTALLED,
                message="Audio library not installed",
                detail="music21 is required for audio generation",
                can_fallback=False
            )
        )
    
    try:
        from music21 import note, stream, tempo, meter
        
        # Parse the note name
        # Handle different formats: "Bb4", "F#3", "C5", "Eb"
        parsed_note = note_name.strip()
        
        # If octave provided separately, use it
        if octave is not None:
            # Strip any octave from the note name
            note_letter = ''.join(c for c in parsed_note if not c.isdigit())
            parsed_note = f"{note_letter}{octave}"
        elif not any(c.isdigit() for c in parsed_note):
            # No octave in note name, add default based on instrument
            default_octaves = {
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
            oct = default_octaves.get(instrument, 4)
            parsed_note = f"{parsed_note}{oct}"
        
        # Check cache
        cache_key = (parsed_note.lower(), instrument, duration_beats)
        if cache_key in _single_note_cache:
            return AudioResult(
                success=True,
                data=_single_note_cache[cache_key],
                content_type="audio/wav"
            )
        
        # Create a simple score with one whole note
        s = stream.Score()
        p = stream.Part()
        m = stream.Measure()
        
        # Set tempo (moderate, held note)
        m.insert(0, tempo.MetronomeMark(number=60))  # 60 BPM = 1 beat per second
        m.insert(0, meter.TimeSignature('4/4'))
        
        # Create the note
        n = note.Note(parsed_note)
        n.quarterLength = duration_beats  # whole note = 4 quarter beats
        m.append(n)
        
        # Add a rest to let the note ring out
        r = note.Rest()
        r.quarterLength = 1  # quarter rest buffer
        m.append(r)
        
        p.append(m)
        s.append(p)
        
        # Set instrument for proper MIDI program
        from music21 import instrument as m21instrument
        
        # Normalize instrument name (handle spaces, case variations)
        norm_instrument = instrument.lower().replace(" ", "_").replace("-", "_")
        
        instrument_map = {
            # Brass
            "trumpet": m21instrument.Trumpet,
            "trombone": m21instrument.Trombone,
            "bass_trombone": m21instrument.BassTrombone,
            "tenor_trombone": m21instrument.Trombone,
            "french_horn": m21instrument.Horn,
            "euphonium": m21instrument.Tuba,  # music21 doesn't have Euphonium, Tuba is closest
            "tuba": m21instrument.Tuba,
            # Woodwinds
            "flute": m21instrument.Flute,
            "clarinet": m21instrument.Clarinet,
            "oboe": m21instrument.Oboe,
            "bassoon": m21instrument.Bassoon,
            "saxophone": m21instrument.Saxophone,
            "alto_saxophone": m21instrument.AltoSaxophone,
            "tenor_saxophone": m21instrument.TenorSaxophone,
            "baritone_saxophone": m21instrument.BaritoneSaxophone,
            # Strings
            "violin": m21instrument.Violin,
            "viola": m21instrument.Viola,
            "cello": m21instrument.Violoncello,
            "double_bass": m21instrument.Contrabass,
            "guitar": m21instrument.AcousticGuitar,
            # Keyboard  
            "piano": m21instrument.Piano,
            "organ": m21instrument.PipeOrgan,
            # Voice
            "voice": m21instrument.Vocalist,
            "voice_(general)": m21instrument.Vocalist,
            "soprano": m21instrument.Soprano,
            "alto": m21instrument.Alto,
            "tenor": m21instrument.Tenor,
            "bass_voice": m21instrument.Bass,
            # Percussion
            "mallet_percussion": m21instrument.Vibraphone,
            "other": m21instrument.Piano,
        }
        
        # Check if instrument has custom MIDI program suffix (e.g., "synth_brass_62", "choir_52")
        custom_midi_program = None
        base_instrument = norm_instrument
        
        # Parse custom MIDI program from instrument name (format: name_XX where XX is MIDI program)
        import re
        midi_suffix_match = re.match(r'^(.+?)_(\d+)$', norm_instrument)
        if midi_suffix_match:
            base_instrument = midi_suffix_match.group(1)
            custom_midi_program = int(midi_suffix_match.group(2))
        
        InstrumentClass = instrument_map.get(base_instrument, m21instrument.Piano)
        
        for part in s.parts:
            part.removeByClass(m21instrument.Instrument)
            inst = InstrumentClass()
            # Apply custom MIDI program if specified from URL (e.g., synth_brass_62)
            if custom_midi_program is not None:
                inst.midiProgram = custom_midi_program
            part.insert(0, inst)
        
        # Export to MIDI bytes (use write() method which works correctly)
        midi_path = s.write('midi')
        with open(midi_path, 'rb') as f:
            midi_bytes = f.read()
        
        # Get soundfont
        soundfont = get_soundfont_path(instrument)
        if not soundfont:
            return AudioResult(
                success=True,
                data=midi_bytes,
                content_type="audio/midi",
                is_fallback=True,
                error=AudioError(
                    code=AudioErrorCode.SOUNDFONT_NOT_FOUND,
                    message="No soundfont available - returning MIDI",
                    detail=f"Download soundfont to {SOUNDFONT_DIR}",
                    can_fallback=True
                )
            )
        
        # Render to WAV
        wav_bytes = midi_to_audio(midi_bytes, soundfont)
        if not wav_bytes:
            return AudioResult(
                success=True,
                data=midi_bytes,
                content_type="audio/midi",
                is_fallback=True,
                error=AudioError(
                    code=AudioErrorCode.AUDIO_RENDER_FAILED,
                    message="Audio rendering failed - returning MIDI",
                    detail="FluidSynth could not render audio",
                    can_fallback=True
                )
            )
        
        # Cache successful result
        if len(_single_note_cache) >= _single_note_cache_max:
            oldest = next(iter(_single_note_cache))
            del _single_note_cache[oldest]
        _single_note_cache[cache_key] = wav_bytes
        
        return AudioResult(success=True, data=wav_bytes, content_type="audio/wav")
        
    except Exception as e:
        return AudioResult(
            success=False,
            error=AudioError(
                code=AudioErrorCode.MIDI_CONVERSION_FAILED,
                message=f"Failed to generate note audio: {str(e)}",
                detail=str(e),
                can_fallback=False
            )
        )


def generate_audio(
    musicxml_content: str,
    original_key: str,
    target_key: str,
    instrument: str = "piano",
    material_id: Optional[int] = None,
) -> Tuple[Optional[bytes], str]:
    """
    Generate audio from MusicXML, transposed to target key.
    
    Legacy API - use generate_audio_with_result for detailed errors.
    
    Returns:
        Tuple of (audio_bytes, content_type)
        audio_bytes is None if generation failed completely
        content_type is "audio/wav", "audio/midi", or "error: message"
    """
    result = generate_audio_with_result(
        musicxml_content, original_key, target_key, instrument, material_id
    )
    
    if result.success:
        return result.data, result.content_type
    else:
        error_msg = result.error.message if result.error else "Unknown error"
        return None, f"error: {error_msg}"


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
