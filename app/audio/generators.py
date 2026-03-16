"""
High-level audio generation functions.

Main API for generating audio from MusicXML or single notes.
"""

import logging
from typing import Optional, Tuple

from .types import AudioResult, AudioError, AudioErrorCode
from .config import (
    MUSIC21_AVAILABLE,
    FLUIDSYNTH_AVAILABLE,
    SFIZZ_RENDER_AVAILABLE,
    SOUNDFONT_DIR,
    DEFAULT_OCTAVES,
    get_audio_cache,
    get_single_note_cache,
    _cache_max_size,
    _single_note_cache_max,
)
from .transposition import get_transposition_interval, transpose_musicxml
from .converters import musicxml_to_midi, midi_to_audio, get_soundfont_path
from .renderers import render_note_with_sfizz, get_sfz_path

logger = logging.getLogger(__name__)


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
    _audio_cache = get_audio_cache()
    
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
    
    # Check if transposition is needed
    xml_to_render = musicxml_content
    if original_key and target_key and original_key != target_key:
        semitones = get_transposition_interval(original_key, target_key)
        if semitones is None:
            return AudioResult(
                success=False,
                error=AudioError(
                    code=AudioErrorCode.TRANSPOSITION_FAILED,
                    message="Could not calculate transposition",
                    detail=f"Failed to transpose from {original_key} to {target_key}",
                    can_fallback=True
                )
            )
        
        if semitones != 0:
            transposed = transpose_musicxml(musicxml_content, semitones)
            if transposed is None:
                return AudioResult(
                    success=False,
                    error=AudioError(
                        code=AudioErrorCode.TRANSPOSITION_FAILED,
                        message="Transposition failed",
                        detail=f"Could not transpose by {semitones} semitones",
                        can_fallback=True
                    )
                )
            xml_to_render = transposed
    
    # Convert to MIDI
    midi_bytes = musicxml_to_midi(xml_to_render, instrument)
    if not midi_bytes:
        return AudioResult(
            success=False,
            error=AudioError(
                code=AudioErrorCode.MIDI_CONVERSION_FAILED,
                message="Could not convert to MIDI",
                detail="music21 failed to export MIDI. Check MusicXML validity.",
                can_fallback=False
            )
        )
    
    # Check FluidSynth availability
    if not FLUIDSYNTH_AVAILABLE:
        return AudioResult(
            success=True,
            data=midi_bytes,
            content_type="audio/midi",
            is_fallback=True,
            error=AudioError(
                code=AudioErrorCode.FLUIDSYNTH_NOT_INSTALLED,
                message="Audio renderer not available - returning MIDI",
                detail="Install FluidSynth for audio playback: brew install fluid-synth",
                can_fallback=True
            )
        )
    
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
                detail=f"Download a .sf2 soundfont to {SOUNDFONT_DIR}",
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


def generate_single_note_audio(
    note_name: str,
    instrument: str = "piano",
    duration_beats: int = 3,  # 3 beats at 60 BPM = 3 seconds
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
    _single_note_cache = get_single_note_cache()
    
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
            oct = DEFAULT_OCTAVES.get(instrument, 4)
            parsed_note = f"{parsed_note}{oct}"
        
        # Check cache
        cache_key = (parsed_note.lower(), instrument, duration_beats)
        if cache_key in _single_note_cache:
            return AudioResult(
                success=True,
                data=_single_note_cache[cache_key],
                content_type="audio/wav"
            )
        
        # Try SFZ rendering first (higher quality)
        sfz_path = get_sfz_path(instrument)
        if sfz_path and SFIZZ_RENDER_AVAILABLE:
            logger.debug(f"Using sfizz_render for {instrument}: {sfz_path}")
            wav_bytes = render_note_with_sfizz(
                note_name=parsed_note,
                duration_seconds=float(duration_beats),
                velocity=100,
                sfz_path=sfz_path,
                instrument=instrument
            )
            if wav_bytes:
                # Cache and return
                if len(_single_note_cache) >= _single_note_cache_max:
                    oldest = next(iter(_single_note_cache))
                    del _single_note_cache[oldest]
                _single_note_cache[cache_key] = wav_bytes
                return AudioResult(
                    success=True,
                    data=wav_bytes,
                    content_type="audio/wav"
                )
        
        # Fall back to standard MIDI rendering
        # Create a simple score with one whole note
        s = stream.Score()
        p = stream.Part()  # type: ignore[no-untyped-call]
        m = stream.Measure()
        
        # Set tempo (60 BPM = 1 beat per second)
        m.insert(0, tempo.MetronomeMark(number=60))  # type: ignore[no-untyped-call]
        m.insert(0, meter.TimeSignature('4/4'))  # type: ignore[no-untyped-call, attr-defined]
        
        # Create the note
        n = note.Note(parsed_note)
        n.quarterLength = duration_beats
        m.append(n)  # type: ignore[no-untyped-call]
        
        p.append(m)  # type: ignore[no-untyped-call]
        s.append(p)  # type: ignore[no-untyped-call]
        
        # Write to MIDI
        midi_file = s.write('midi')  # type: ignore[no-untyped-call]
        with open(midi_file, 'rb') as f:
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
