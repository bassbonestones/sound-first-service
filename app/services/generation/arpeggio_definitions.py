"""Arpeggio interval definitions for the generation engine.

All arpeggios are defined as intervals from the root in semitones.
Content is authored starting from C (MIDI 60 = C4 as reference).
Transposition happens at the output stage.
"""
from typing import Dict, Tuple

from app.schemas.generation_schemas import ArpeggioType


# =============================================================================
# Arpeggio Interval Patterns
# =============================================================================
# Each arpeggio is defined by its chord tones as intervals from root in semitones.
# These are NOT sequential intervals (like scales) but cumulative from root.

ARPEGGIO_INTERVALS: Dict[ArpeggioType, Tuple[int, ...]] = {
    # Triads (root + intervals)
    # Note: These are intervals FROM root, not sequential
    ArpeggioType.MAJOR: (0, 4, 7),  # 1-3-5 (root, M3, P5)
    ArpeggioType.MINOR: (0, 3, 7),  # 1-b3-5 (root, m3, P5)
    ArpeggioType.AUGMENTED: (0, 4, 8),  # 1-3-#5
    ArpeggioType.DIMINISHED: (0, 3, 6),  # 1-b3-b5
    ArpeggioType.SUS4: (0, 5, 7),  # 1-4-5
    ArpeggioType.SUS2: (0, 2, 7),  # 1-2-5
    
    # Seventh chords
    ArpeggioType.MAJOR_7: (0, 4, 7, 11),  # 1-3-5-7
    ArpeggioType.DOMINANT_7: (0, 4, 7, 10),  # 1-3-5-b7
    ArpeggioType.MINOR_7: (0, 3, 7, 10),  # 1-b3-5-b7
    ArpeggioType.MINOR_MAJOR_7: (0, 3, 7, 11),  # 1-b3-5-7
    ArpeggioType.HALF_DIMINISHED: (0, 3, 6, 10),  # 1-b3-b5-b7 (m7b5)
    ArpeggioType.DIMINISHED_7: (0, 3, 6, 9),  # 1-b3-b5-bb7 (dim7)
    ArpeggioType.AUGMENTED_MAJOR_7: (0, 4, 8, 11),  # 1-3-#5-7
    ArpeggioType.AUGMENTED_7: (0, 4, 8, 10),  # 1-3-#5-b7
    ArpeggioType.DOMINANT_7_SUS4: (0, 5, 7, 10),  # 1-4-5-b7
    
    # Extended chords (9ths)
    ArpeggioType.MAJOR_9: (0, 4, 7, 11, 14),  # 1-3-5-7-9
    ArpeggioType.DOMINANT_9: (0, 4, 7, 10, 14),  # 1-3-5-b7-9
    ArpeggioType.MINOR_9: (0, 3, 7, 10, 14),  # 1-b3-5-b7-9
    
    # Extended chords (11ths)
    ArpeggioType.MAJOR_11: (0, 4, 7, 11, 14, 17),  # 1-3-5-7-9-11
    ArpeggioType.DOMINANT_11: (0, 4, 7, 10, 14, 17),  # 1-3-5-b7-9-11
    ArpeggioType.MINOR_11: (0, 3, 7, 10, 14, 17),  # 1-b3-5-b7-9-11
    
    # Extended chords (13ths)
    ArpeggioType.MAJOR_13: (0, 4, 7, 11, 14, 17, 21),  # 1-3-5-7-9-11-13
    ArpeggioType.DOMINANT_13: (0, 4, 7, 10, 14, 17, 21),  # 1-3-5-b7-9-11-13
    
    # Altered dominants
    ArpeggioType.DOMINANT_7_FLAT9: (0, 4, 7, 10, 13),  # 1-3-5-b7-b9
    ArpeggioType.DOMINANT_7_SHARP9: (0, 4, 7, 10, 15),  # 1-3-5-b7-#9
    ArpeggioType.DOMINANT_7_SHARP11: (0, 4, 7, 10, 14, 18),  # 1-3-5-b7-9-#11
    ArpeggioType.DOMINANT_7_FLAT13: (0, 4, 7, 10, 14, 20),  # 1-3-5-b7-9-b13
    ArpeggioType.ALTERED: (0, 4, 6, 10, 13, 15),  # 1-3-b5-b7-b9-#9 (common voicing)
}


def get_arpeggio_intervals(arpeggio_type: ArpeggioType) -> Tuple[int, ...]:
    """Get the interval pattern for an arpeggio type.
    
    Args:
        arpeggio_type: The arpeggio type enum value.
        
    Returns:
        Tuple of intervals from root in semitones.
        
    Raises:
        KeyError: If arpeggio type is not defined.
    """
    return ARPEGGIO_INTERVALS[arpeggio_type]


def get_arpeggio_note_count(arpeggio_type: ArpeggioType) -> int:
    """Get the number of notes in one occurrence of the arpeggio.
    
    Args:
        arpeggio_type: The arpeggio type enum value.
        
    Returns:
        Number of chord tones (e.g., 3 for triads, 4 for 7ths).
    """
    return len(ARPEGGIO_INTERVALS[arpeggio_type])


def get_arpeggio_span_semitones(arpeggio_type: ArpeggioType) -> int:
    """Get the span from root to highest chord tone in semitones.
    
    Args:
        arpeggio_type: The arpeggio type enum value.
        
    Returns:
        Semitone span (e.g., 7 for triad, 11 for maj7).
    """
    intervals = ARPEGGIO_INTERVALS[arpeggio_type]
    return intervals[-1] if intervals else 0
