"""
Audio format converters.

Functions for converting MusicXML to MIDI and MIDI to audio.
"""

import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

from .config import (
    MUSIC21_AVAILABLE,
    SOUNDFONT_DIR,
    DEFAULT_SOUNDFONT,
)

logger = logging.getLogger(__name__)


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
        from music21 import converter, instrument as m21instrument
        
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
        for part in score.parts:  # type: ignore[union-attr]
            # Remove any existing instruments
            part.removeByClass(m21instrument.Instrument)
            # Insert new instrument at the beginning
            inst = InstrumentClass()  # type: ignore[no-untyped-call]
            part.insert(0, inst)
        
        # Write to MIDI
        midi_file = score.write('midi')  # type: ignore[no-untyped-call]
        with open(midi_file, 'rb') as f:
            return f.read()
    except Exception as e:
        logger.error(f"Error converting to MIDI: {e}")
        return None


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
        logger.warning("No soundfont file found. Please add a .sf2 file to the soundfonts/ directory.")
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
                logger.error(f"FluidSynth error: {result.stderr}")
                return None
        else:
            # Use midi2audio library
            try:
                from midi2audio import FluidSynth
                fs = FluidSynth(str(soundfont_path))
                fs.midi_to_audio(midi_path, wav_path)
            except ImportError:
                logger.warning("midi2audio not installed. Run: pip install midi2audio")
                return None
        
        # Read WAV bytes
        with open(wav_path, 'rb') as f:
            wav_bytes = f.read()
        
        # Cleanup temp files
        os.unlink(midi_path)
        os.unlink(wav_path)
        
        return wav_bytes
    except Exception as e:
        logger.error(f"Error rendering audio: {e}")
        return None
