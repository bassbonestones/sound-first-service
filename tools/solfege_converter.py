#!/usr/bin/env python3
"""
Solfège Converter for MusicXML.

Converts MusicXML lyrics to movable-do solfège syllables based on the key.
Supports chromatic alterations (di, ra, ri, me, fi, si, le, li, te).

Usage:
    from tools.solfege_converter import convert_to_solfege
    solfege_xml = convert_to_solfege(musicxml_content)
"""

from __future__ import annotations

import logging
from typing import Optional

try:
    from music21 import converter, key as m21_key, note as m21_note, stream
except ImportError:
    raise ImportError("music21 is required. Install it with: pip install music21")

logger = logging.getLogger(__name__)


# Movable do solfège syllables for diatonic scale degrees (0-based)
# Scale degrees: 0=do, 1=re, 2=mi, 3=fa, 4=sol, 5=la, 6=ti
DIATONIC_SOLFEGE = ["do", "re", "mi", "fa", "sol", "la", "ti"]

# Chromatic alterations for movable do
# Key: (scale_degree, alteration) where alteration is semitones from diatonic
# Raised: +1 semitone (sharp/natural in flat keys)
# Lowered: -1 semitone (flat/natural in sharp keys)
CHROMATIC_SOLFEGE = {
    # Raised syllables (sharped)
    (0, 1): "di",   # raised do
    (1, 1): "ri",   # raised re
    (3, 1): "fi",   # raised fa
    (4, 1): "si",   # raised sol
    (5, 1): "li",   # raised la
    # Lowered syllables (flatted)
    (1, -1): "ra",  # lowered re
    (2, -1): "me",  # lowered mi (same as raised re enharmonically)
    (4, -1): "se",  # lowered sol
    (5, -1): "le",  # lowered la
    (6, -1): "te",  # lowered ti
}


def get_scale_degree_and_alteration(
    pitch: m21_note.Pitch,
    tonic: m21_note.Pitch,
    mode: str = "major"
) -> tuple[int, int]:
    """
    Calculate the scale degree and chromatic alteration of a pitch.
    
    Args:
        pitch: The pitch to analyze
        tonic: The tonic pitch of the key
        mode: "major" or "minor"
        
    Returns:
        Tuple of (scale_degree 0-6, alteration in semitones)
    """
    # Get the pitch class interval from tonic (in semitones)
    # pitch.pitchClass gives 0-11, tonic.pitchClass gives 0-11
    interval_semitones = (pitch.pitchClass - tonic.pitchClass) % 12
    
    # Define the expected semitones for each diatonic scale degree
    if mode == "major":
        # Major scale: W W H W W W H = 0, 2, 4, 5, 7, 9, 11
        diatonic_semitones = [0, 2, 4, 5, 7, 9, 11]
    else:
        # Natural minor: W H W W H W W = 0, 2, 3, 5, 7, 8, 10
        diatonic_semitones = [0, 2, 3, 5, 7, 8, 10]
    
    # Find the closest diatonic scale degree
    best_degree = 0
    best_alteration = interval_semitones  # Default to treating as chromatic
    
    for degree, expected in enumerate(diatonic_semitones):
        alteration = interval_semitones - expected
        # Normalize alteration to -1, 0, or 1 (closest)
        if alteration > 6:
            alteration -= 12
        elif alteration < -6:
            alteration += 12
        
        if abs(alteration) <= 1:
            if abs(alteration) < abs(best_alteration):
                best_degree = degree
                best_alteration = alteration
    
    return best_degree, best_alteration


def pitch_to_solfege(
    pitch: m21_note.Pitch,
    tonic: m21_note.Pitch,
    mode: str = "major"
) -> str:
    """
    Convert a pitch to its solfège syllable using movable do.
    
    Args:
        pitch: The pitch to convert
        tonic: The tonic pitch of the key
        mode: "major" or "minor"
        
    Returns:
        Solfège syllable (e.g., "do", "re", "fi", "te")
    """
    degree, alteration = get_scale_degree_and_alteration(pitch, tonic, mode)
    
    # Check for chromatic alteration
    if alteration != 0:
        chromatic_key = (degree, alteration)
        if chromatic_key in CHROMATIC_SOLFEGE:
            return CHROMATIC_SOLFEGE[chromatic_key]
        else:
            # Unknown chromatic - just return the diatonic with marker
            base = DIATONIC_SOLFEGE[degree]
            if alteration > 0:
                return f"{base}↑"
            else:
                return f"{base}↓"
    
    return DIATONIC_SOLFEGE[degree]


def convert_to_solfege(
    musicxml_content: str,
    override_key: Optional[str] = None
) -> str:
    """
    Convert MusicXML to a version with solfège syllables as lyrics.
    
    Removes any existing lyrics and replaces them with movable-do solfège
    syllables based on the key of the piece.
    
    Args:
        musicxml_content: Raw MusicXML string
        override_key: Optional key override (e.g., "G", "F#m", "Bb")
        
    Returns:
        Modified MusicXML string with solfège as lyrics
    """
    try:
        score = converter.parse(musicxml_content)
    except Exception as e:
        logger.error(f"Failed to parse MusicXML: {e}")
        raise ValueError(f"Failed to parse MusicXML: {e}")
    
    # Determine the key - priority: override > key signature > analysis
    key_obj = None
    
    if override_key:
        # Parse the override key
        key_str = override_key
        is_minor = key_str.endswith("m") or key_str.endswith("min")
        base_key = key_str.rstrip("min").rstrip("m")
        
        # Normalize for music21
        if is_minor:
            tonic_name = base_key.lower()
        else:
            tonic_name = base_key.upper()
        
        # Handle flats (b -> -)
        if len(tonic_name) > 1 and tonic_name[1] == 'b':
            tonic_name = tonic_name[0] + '-'
        
        try:
            key_obj = m21_key.Key(tonic_name)
        except Exception:
            key_obj = None
    
    if key_obj is None:
        # Try to get key signature from the score first
        key_sigs = list(score.flatten().getElementsByClass(m21_key.KeySignature))
        if key_sigs:
            # Use the first key signature
            ks = key_sigs[0]
            # Convert key signature to key (assume major for now)
            key_obj = ks.asKey('major')
            logger.debug(f"Using key signature: {key_obj}")
    
    if key_obj is None:
        # Fall back to analysis
        key_obj = score.analyze('key')
        if key_obj is None:
            key_obj = m21_key.Key('C')
    
    tonic = key_obj.tonic
    mode = "minor" if key_obj.mode == "minor" else "major"
    
    logger.debug(f"Using key: {key_obj}, tonic: {tonic}, mode: {mode}")
    
    # Remove existing lyrics from all notes
    for n in score.recurse().notes:
        if isinstance(n, m21_note.Note):
            n.lyrics = []
    
    # Add solfège syllables as lyrics
    for n in score.recurse().notes:
        if isinstance(n, m21_note.Note):
            solfege = pitch_to_solfege(n.pitch, tonic, mode)
            lyric = m21_note.Lyric(text=solfege, syllabic="single")
            n.lyrics.append(lyric)
    
    # Convert back to MusicXML
    try:
        solfege_xml = score.write("musicxml").read_text(encoding="utf-8")
    except Exception:
        # Fallback for older music21 versions
        import tempfile
        from pathlib import Path
        with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as f:
            temp_path = Path(f.name)
        score.write("musicxml", fp=str(temp_path))
        solfege_xml = temp_path.read_text(encoding="utf-8")
        temp_path.unlink()
    
    return solfege_xml


if __name__ == "__main__":
    # Test with a simple example
    import sys
    
    if len(sys.argv) > 1:
        from pathlib import Path
        input_file = Path(sys.argv[1])
        content = input_file.read_text(encoding="utf-8")
        result = convert_to_solfege(content)
        print(result)
    else:
        print("Usage: python -m tools.solfege_converter <musicxml_file>")
