"""
MusicXML transposition utilities.

Functions for calculating transposition intervals and transposing MusicXML content.
"""

from typing import Optional

from .config import MUSIC21_AVAILABLE


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
        from music21 import key as m21key, interval
        
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
        from music21 import converter, interval
        
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
