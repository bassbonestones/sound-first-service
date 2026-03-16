"""
Audio rendering backends.

Provides multiple rendering methods for generating audio:
- Pure sine wave tones (for pitch training)
- SFZ/sfizz rendering (high-quality sampled instruments)
- MuseScore rendering (professional quality)
"""

import logging
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from app.config import MUSESCORE_PATH

from .config import (
    MUSIC21_AVAILABLE,
    SFIZZ_RENDER_AVAILABLE,
    SOUNDFONT_DIR,
    SFZ_INSTRUMENTS,
)

logger = logging.getLogger(__name__)


# =============================================================================
# PURE TONE RENDERING (Best for Pitch Training)
# =============================================================================

def render_pure_tone(
    note_name: str,
    duration_seconds: float = 3.0,
    sample_rate: int = 44100,
    amplitude: float = 0.8,
    attack_time: float = 0.05,
    release_time: float = 0.1,
) -> Optional[bytes]:
    """
    Render a pure sine wave tone - ideal for pitch training.
    
    No vibrato, no harmonics, just a clean stable frequency.
    Includes soft attack/release to avoid clicks.
    
    Args:
        note_name: Note with octave (e.g., "Bb3", "F4")
        duration_seconds: How long to play
        sample_rate: Audio sample rate
        amplitude: Volume (0.0 to 1.0)
        attack_time: Fade-in duration in seconds
        release_time: Fade-out duration in seconds
        
    Returns:
        WAV audio bytes, or None on error
    """
    try:
        import numpy as np
        import wave
        import io
        
        if not MUSIC21_AVAILABLE:
            logger.warning("music21 required for note parsing")
            return None
        
        from music21 import pitch as m21pitch
        p = m21pitch.Pitch(note_name)
        frequency = p.frequency
        
        # Generate time array
        total_samples = int(sample_rate * duration_seconds)
        t = np.linspace(0, duration_seconds, total_samples, dtype=np.float32)
        
        # Generate pure sine wave
        wave_data = amplitude * np.sin(2 * np.pi * frequency * t)
        
        # Apply envelope (attack and release)
        envelope = np.ones(total_samples, dtype=np.float32)
        
        # Attack ramp
        attack_samples = int(attack_time * sample_rate)
        if attack_samples > 0:
            envelope[:attack_samples] = np.linspace(0, 1, attack_samples)
        
        # Release ramp
        release_samples = int(release_time * sample_rate)
        if release_samples > 0:
            envelope[-release_samples:] = np.linspace(1, 0, release_samples)
        
        wave_data = wave_data * envelope
        
        # Convert to 16-bit PCM
        pcm = (wave_data * 32767).astype(np.int16)
        
        # Write to WAV (mono)
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())
        
        wav_bytes = wav_buffer.getvalue()
        logger.debug(f"Pure tone rendered {len(wav_bytes)} bytes for {note_name} ({frequency:.2f} Hz)")
        return wav_bytes
        
    except Exception as e:
        logger.error(f"Error rendering pure tone: {e}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# SFZ RENDERING (High Quality Samples via sfizz)
# =============================================================================

def get_sfz_path(instrument: str) -> Optional[Path]:
    """Get path to SFZ file for instrument, if available."""
    norm_instrument = instrument.lower().replace(" ", "_").replace("-", "_")
    if norm_instrument in SFZ_INSTRUMENTS:
        sfz_path = SOUNDFONT_DIR / SFZ_INSTRUMENTS[norm_instrument]
        if sfz_path.exists():
            return sfz_path
    return None


def render_note_with_sfizz(
    note_name: str,
    duration_seconds: float = 3.0,
    velocity: int = 100,
    sample_rate: int = 44100,
    sfz_path: Optional[Path] = None,
    instrument: str = "trombone"
) -> Optional[bytes]:
    """
    Render a single note using sfizz_render CLI (SFZ sampler).
    
    This provides much higher audio quality than SF2 soundfonts
    by using real multi-sampled instrument recordings with proper looping.
    
    Args:
        note_name: Note with octave (e.g., "Bb3", "F4")
        duration_seconds: How long to render
        velocity: MIDI velocity (1-127)
        sample_rate: Audio sample rate
        sfz_path: Path to SFZ file (auto-detected if None)
        instrument: Instrument name for SFZ lookup
        
    Returns:
        WAV audio bytes, or None on error
    """
    if not SFIZZ_RENDER_AVAILABLE:
        logger.warning("sfizz_render CLI not available")
        return None
    
    # Get SFZ path
    if sfz_path is None:
        sfz_path = get_sfz_path(instrument)
    if sfz_path is None:
        logger.warning(f"No SFZ file found for {instrument}")
        return None
    
    if not MUSIC21_AVAILABLE:
        logger.warning("music21 required for MIDI generation")
        return None
    
    try:
        from music21 import note, stream, tempo, meter
        
        # Create a simple MIDI file with one sustained note
        s = stream.Score()
        p = stream.Part()  # type: ignore[no-untyped-call]
        m = stream.Measure()
        
        # Set tempo (60 BPM = 1 beat per second)
        m.insert(0, tempo.MetronomeMark(number=60))  # type: ignore[no-untyped-call]
        m.insert(0, meter.TimeSignature('4/4'))  # type: ignore[no-untyped-call, attr-defined]
        
        # Create the note
        n = note.Note(note_name)
        n.quarterLength = duration_seconds  # Duration in beats (at 60BPM = seconds)
        n.volume.velocity = velocity
        m.append(n)  # type: ignore[no-untyped-call]
        
        # Add silence at end for release
        from music21 import note as m21note
        rest = m21note.Rest()
        rest.quarterLength = 1.0  # 1 second of silence for release
        m.append(rest)  # type: ignore[no-untyped-call]
        
        p.append(m)  # type: ignore[no-untyped-call]
        s.append(p)  # type: ignore[no-untyped-call]
        
        # Write MIDI to temp file
        midi_path = s.write('midi')  # type: ignore[no-untyped-call]
        
        # Create output WAV path
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_tmp:
            wav_path = wav_tmp.name
        
        # Call sfizz_render
        cmd = [
            'sfizz_render',
            '--sfz', str(sfz_path),
            '--midi', str(midi_path),
            '--wav', wav_path,
            '-s', str(sample_rate),
        ]
        
        logger.debug(f"Running sfizz_render: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        
        if result.returncode != 0:
            logger.error(f"sfizz_render error: {result.stderr}")
            os.unlink(midi_path)
            if os.path.exists(wav_path):
                os.unlink(wav_path)
            return None
        
        # Check if output file was created
        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            logger.error("sfizz_render did not create output file")
            os.unlink(midi_path)
            return None
        
        # Read WAV bytes
        with open(wav_path, 'rb') as f:
            wav_bytes = f.read()
        
        # Cleanup temp files
        os.unlink(midi_path)
        os.unlink(wav_path)
        
        logger.debug(f"sfizz_render produced {len(wav_bytes)} bytes for {note_name}")
        return wav_bytes
        
    except subprocess.TimeoutExpired:
        logger.error("sfizz_render timed out")
        return None
    except Exception as e:
        logger.error(f"Error rendering with sfizz: {e}")
        import traceback
        traceback.print_exc()
        return None


# =============================================================================
# MUSESCORE RENDERING (Professional Quality)
# =============================================================================

def get_musescore_path() -> Optional[str]:
    """Get the MuseScore executable path."""
    if Path(MUSESCORE_PATH).exists():
        return MUSESCORE_PATH
    # Try common locations
    common_paths = [
        "/Applications/MuseScore 4.app/Contents/MacOS/mscore",
        "/usr/bin/mscore",
        "/usr/local/bin/mscore",
        shutil.which("mscore"),
    ]
    for p in common_paths:
        if p and Path(p).exists():
            return p
    return None


def musicxml_to_wav_musescore(musicxml_content: str, timeout: int = 60) -> Optional[bytes]:
    """
    Render MusicXML to WAV using MuseScore.
    
    This provides professional-quality audio using Muse Sounds
    if available on the system.
    
    Args:
        musicxml_content: Raw MusicXML string
        timeout: Maximum seconds to wait for rendering
        
    Returns:
        WAV audio bytes, or None on error
    """
    mscore_path = get_musescore_path()
    if not mscore_path:
        logger.warning("MuseScore not found")
        return None
    
    try:
        # Write MusicXML to temp file
        with tempfile.NamedTemporaryFile(suffix='.musicxml', delete=False, mode='w') as xml_tmp:
            xml_tmp.write(musicxml_content)
            xml_path = xml_tmp.name
        
        # Create output WAV path
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as wav_tmp:
            wav_path = wav_tmp.name
        
        # Call MuseScore for export
        cmd = [
            mscore_path,
            '-o', wav_path,
            xml_path
        ]
        
        logger.debug(f"Running MuseScore: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        
        # Cleanup input
        os.unlink(xml_path)
        
        if result.returncode != 0:
            logger.error(f"MuseScore error: {result.stderr}")
            if os.path.exists(wav_path):
                os.unlink(wav_path)
            return None
        
        # Check if output was created
        if not os.path.exists(wav_path) or os.path.getsize(wav_path) == 0:
            logger.error("MuseScore did not create output file")
            return None
        
        # Read WAV bytes
        with open(wav_path, 'rb') as f:
            wav_bytes = f.read()
        
        # Cleanup output
        os.unlink(wav_path)
        
        logger.debug(f"MuseScore rendered {len(wav_bytes)} bytes")
        return wav_bytes
        
    except subprocess.TimeoutExpired:
        logger.error(f"MuseScore timed out after {timeout}s")
        return None
    except Exception as e:
        logger.error(f"Error rendering with MuseScore: {e}")
        import traceback
        traceback.print_exc()
        return None
