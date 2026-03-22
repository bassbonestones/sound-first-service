"""Enharmonic spelling for proper note names in any key.

This module provides a comprehensive lookup table for determining the correct
enharmonic spelling of any pitch in any key signature. Instead of naive
"use sharps" or "use flats" logic, it uses scale-degree-aware spelling.

The KEY_ALTERATION_MAP is verified for all 15 key signatures (-7 to +7)
and handles:
- All 7 scale degrees (0-6)
- All 5 alterations (-2 to +2): double-lowered, lowered, diatonic, raised, double-raised

Source: Ported from sound-first-mobile/src/features/composer/utils/pitchUtils.ts
Based on key_alteration_map.md (manually verified)
"""

from typing import Optional, NamedTuple
from enum import Enum


# =============================================================================
# Types
# =============================================================================

class Accidental(str, Enum):
    """Accidental types for note spelling."""
    DOUBLE_FLAT = "double-flat"
    FLAT = "flat"
    NATURAL = "natural"
    SHARP = "sharp"
    DOUBLE_SHARP = "double-sharp"


class SpellingEntry(NamedTuple):
    """A note spelling: letter name + accidental."""
    letter: str  # "A" through "G"
    accidental: Optional[Accidental]


# =============================================================================
# Key Alteration Map
# =============================================================================
# Structure: KEY_ALTERATION_MAP[key_fifths][degree][alteration] = SpellingEntry
# - key_fifths: -7 (Cb) to +7 (C#)
# - degree: 0-6 (scale degrees 1-7)
# - alteration: -2 to +2 (double-lowered to double-raised)

KEY_ALTERATION_MAP: dict[int, list[dict[int, SpellingEntry]]] = {
    # Cb Major (7 flats)
    -7: [
        {  # Degree 0 (tonic Cb)
            -2: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("C", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("C", Accidental.FLAT),
            1: SpellingEntry("C", Accidental.NATURAL),
            2: SpellingEntry("C", Accidental.SHARP),
        },
        {  # Degree 1 (Db)
            -2: SpellingEntry("C", Accidental.FLAT),
            -1: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("D", Accidental.FLAT),
            1: SpellingEntry("D", Accidental.NATURAL),
            2: SpellingEntry("D", Accidental.SHARP),
        },
        {  # Degree 2 (Eb)
            -2: SpellingEntry("D", Accidental.FLAT),
            -1: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("E", Accidental.FLAT),
            1: SpellingEntry("E", Accidental.NATURAL),
            2: SpellingEntry("E", Accidental.SHARP),
        },
        {  # Degree 3 (Fb)
            -2: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("F", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("F", Accidental.FLAT),
            1: SpellingEntry("F", Accidental.NATURAL),
            2: SpellingEntry("F", Accidental.SHARP),
        },
        {  # Degree 4 (Gb)
            -2: SpellingEntry("F", Accidental.FLAT),
            -1: SpellingEntry("G", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("G", Accidental.FLAT),
            1: SpellingEntry("G", Accidental.NATURAL),
            2: SpellingEntry("G", Accidental.SHARP),
        },
        {  # Degree 5 (Ab)
            -2: SpellingEntry("G", Accidental.FLAT),
            -1: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("A", Accidental.FLAT),
            1: SpellingEntry("A", Accidental.NATURAL),
            2: SpellingEntry("A", Accidental.SHARP),
        },
        {  # Degree 6 (Bb)
            -2: SpellingEntry("A", Accidental.FLAT),
            -1: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("B", Accidental.FLAT),
            1: SpellingEntry("B", Accidental.NATURAL),
            2: SpellingEntry("B", Accidental.SHARP),
        },
    ],
    # Gb Major (6 flats)
    -6: [
        {  # Degree 0 (Gb)
            -2: SpellingEntry("F", Accidental.FLAT),
            -1: SpellingEntry("G", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("G", Accidental.FLAT),
            1: SpellingEntry("G", Accidental.NATURAL),
            2: SpellingEntry("G", Accidental.SHARP),
        },
        {  # Degree 1 (Ab)
            -2: SpellingEntry("G", Accidental.FLAT),
            -1: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("A", Accidental.FLAT),
            1: SpellingEntry("A", Accidental.NATURAL),
            2: SpellingEntry("A", Accidental.SHARP),
        },
        {  # Degree 2 (Bb)
            -2: SpellingEntry("A", Accidental.FLAT),
            -1: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("B", Accidental.FLAT),
            1: SpellingEntry("B", Accidental.NATURAL),
            2: SpellingEntry("B", Accidental.SHARP),
        },
        {  # Degree 3 (Cb)
            -2: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("C", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("C", Accidental.FLAT),
            1: SpellingEntry("C", Accidental.NATURAL),
            2: SpellingEntry("C", Accidental.SHARP),
        },
        {  # Degree 4 (Db)
            -2: SpellingEntry("C", Accidental.FLAT),
            -1: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("D", Accidental.FLAT),
            1: SpellingEntry("D", Accidental.NATURAL),
            2: SpellingEntry("D", Accidental.SHARP),
        },
        {  # Degree 5 (Eb)
            -2: SpellingEntry("D", Accidental.FLAT),
            -1: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("E", Accidental.FLAT),
            1: SpellingEntry("E", Accidental.NATURAL),
            2: SpellingEntry("E", Accidental.SHARP),
        },
        {  # Degree 6 (F - natural in Gb major)
            -2: SpellingEntry("F", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("F", Accidental.FLAT),
            0: SpellingEntry("F", None),
            1: SpellingEntry("F", Accidental.SHARP),
            2: SpellingEntry("F", Accidental.DOUBLE_SHARP),
        },
    ],
    # Db Major (5 flats)
    -5: [
        {  # Degree 0 (Db)
            -2: SpellingEntry("C", Accidental.FLAT),
            -1: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("D", Accidental.FLAT),
            1: SpellingEntry("D", Accidental.NATURAL),
            2: SpellingEntry("D", Accidental.SHARP),
        },
        {  # Degree 1 (Eb)
            -2: SpellingEntry("D", Accidental.FLAT),
            -1: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("E", Accidental.FLAT),
            1: SpellingEntry("E", Accidental.NATURAL),
            2: SpellingEntry("E", Accidental.SHARP),
        },
        {  # Degree 2 (F)
            -2: SpellingEntry("F", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("F", Accidental.FLAT),
            0: SpellingEntry("F", None),
            1: SpellingEntry("F", Accidental.SHARP),
            2: SpellingEntry("F", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 3 (Gb)
            -2: SpellingEntry("F", Accidental.FLAT),
            -1: SpellingEntry("G", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("G", Accidental.FLAT),
            1: SpellingEntry("G", Accidental.NATURAL),
            2: SpellingEntry("G", Accidental.SHARP),
        },
        {  # Degree 4 (Ab)
            -2: SpellingEntry("G", Accidental.FLAT),
            -1: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("A", Accidental.FLAT),
            1: SpellingEntry("A", Accidental.NATURAL),
            2: SpellingEntry("A", Accidental.SHARP),
        },
        {  # Degree 5 (Bb)
            -2: SpellingEntry("A", Accidental.FLAT),
            -1: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("B", Accidental.FLAT),
            1: SpellingEntry("B", Accidental.NATURAL),
            2: SpellingEntry("B", Accidental.SHARP),
        },
        {  # Degree 6 (C)
            -2: SpellingEntry("C", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("C", Accidental.FLAT),
            0: SpellingEntry("C", None),
            1: SpellingEntry("C", Accidental.SHARP),
            2: SpellingEntry("C", Accidental.DOUBLE_SHARP),
        },
    ],
    # Ab Major (4 flats)
    -4: [
        {  # Degree 0 (Ab)
            -2: SpellingEntry("G", Accidental.FLAT),
            -1: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("A", Accidental.FLAT),
            1: SpellingEntry("A", Accidental.NATURAL),
            2: SpellingEntry("A", Accidental.SHARP),
        },
        {  # Degree 1 (Bb)
            -2: SpellingEntry("A", Accidental.FLAT),
            -1: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("B", Accidental.FLAT),
            1: SpellingEntry("B", Accidental.NATURAL),
            2: SpellingEntry("B", Accidental.SHARP),
        },
        {  # Degree 2 (C)
            -2: SpellingEntry("C", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("C", Accidental.FLAT),
            0: SpellingEntry("C", None),
            1: SpellingEntry("C", Accidental.SHARP),
            2: SpellingEntry("C", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 3 (Db)
            -2: SpellingEntry("C", Accidental.FLAT),
            -1: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("D", Accidental.FLAT),
            1: SpellingEntry("D", Accidental.NATURAL),
            2: SpellingEntry("D", Accidental.SHARP),
        },
        {  # Degree 4 (Eb)
            -2: SpellingEntry("D", Accidental.FLAT),
            -1: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("E", Accidental.FLAT),
            1: SpellingEntry("E", Accidental.NATURAL),
            2: SpellingEntry("E", Accidental.SHARP),
        },
        {  # Degree 5 (F)
            -2: SpellingEntry("F", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("F", Accidental.FLAT),
            0: SpellingEntry("F", None),
            1: SpellingEntry("F", Accidental.SHARP),
            2: SpellingEntry("F", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 6 (G)
            -2: SpellingEntry("G", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("G", Accidental.FLAT),
            0: SpellingEntry("G", None),
            1: SpellingEntry("G", Accidental.SHARP),
            2: SpellingEntry("G", Accidental.DOUBLE_SHARP),
        },
    ],
    # Eb Major (3 flats)
    -3: [
        {  # Degree 0 (Eb)
            -2: SpellingEntry("D", Accidental.FLAT),
            -1: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("E", Accidental.FLAT),
            1: SpellingEntry("E", Accidental.NATURAL),
            2: SpellingEntry("E", Accidental.SHARP),
        },
        {  # Degree 1 (F)
            -2: SpellingEntry("F", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("F", Accidental.FLAT),
            0: SpellingEntry("F", None),
            1: SpellingEntry("F", Accidental.SHARP),
            2: SpellingEntry("F", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 2 (G)
            -2: SpellingEntry("G", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("G", Accidental.FLAT),
            0: SpellingEntry("G", None),
            1: SpellingEntry("G", Accidental.SHARP),
            2: SpellingEntry("G", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 3 (Ab)
            -2: SpellingEntry("G", Accidental.FLAT),
            -1: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("A", Accidental.FLAT),
            1: SpellingEntry("A", Accidental.NATURAL),
            2: SpellingEntry("A", Accidental.SHARP),
        },
        {  # Degree 4 (Bb)
            -2: SpellingEntry("A", Accidental.FLAT),
            -1: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("B", Accidental.FLAT),
            1: SpellingEntry("B", Accidental.NATURAL),
            2: SpellingEntry("B", Accidental.SHARP),
        },
        {  # Degree 5 (C)
            -2: SpellingEntry("C", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("C", Accidental.FLAT),
            0: SpellingEntry("C", None),
            1: SpellingEntry("C", Accidental.SHARP),
            2: SpellingEntry("C", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 6 (D)
            -2: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("D", Accidental.FLAT),
            0: SpellingEntry("D", None),
            1: SpellingEntry("D", Accidental.SHARP),
            2: SpellingEntry("D", Accidental.DOUBLE_SHARP),
        },
    ],
    # Bb Major (2 flats)
    -2: [
        {  # Degree 0 (Bb)
            -2: SpellingEntry("A", Accidental.FLAT),
            -1: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("B", Accidental.FLAT),
            1: SpellingEntry("B", Accidental.NATURAL),
            2: SpellingEntry("B", Accidental.SHARP),
        },
        {  # Degree 1 (C)
            -2: SpellingEntry("C", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("C", Accidental.FLAT),
            0: SpellingEntry("C", None),
            1: SpellingEntry("C", Accidental.SHARP),
            2: SpellingEntry("C", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 2 (D)
            -2: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("D", Accidental.FLAT),
            0: SpellingEntry("D", None),
            1: SpellingEntry("D", Accidental.SHARP),
            2: SpellingEntry("D", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 3 (Eb)
            -2: SpellingEntry("D", Accidental.FLAT),
            -1: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("E", Accidental.FLAT),
            1: SpellingEntry("E", Accidental.NATURAL),
            2: SpellingEntry("E", Accidental.SHARP),
        },
        {  # Degree 4 (F)
            -2: SpellingEntry("F", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("F", Accidental.FLAT),
            0: SpellingEntry("F", None),
            1: SpellingEntry("F", Accidental.SHARP),
            2: SpellingEntry("F", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 5 (G)
            -2: SpellingEntry("G", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("G", Accidental.FLAT),
            0: SpellingEntry("G", None),
            1: SpellingEntry("G", Accidental.SHARP),
            2: SpellingEntry("G", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 6 (A)
            -2: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("A", Accidental.FLAT),
            0: SpellingEntry("A", None),
            1: SpellingEntry("A", Accidental.SHARP),
            2: SpellingEntry("A", Accidental.DOUBLE_SHARP),
        },
    ],
    # F Major (1 flat)
    -1: [
        {  # Degree 0 (F)
            -2: SpellingEntry("F", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("F", Accidental.FLAT),
            0: SpellingEntry("F", None),
            1: SpellingEntry("F", Accidental.SHARP),
            2: SpellingEntry("F", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 1 (G)
            -2: SpellingEntry("G", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("G", Accidental.FLAT),
            0: SpellingEntry("G", None),
            1: SpellingEntry("G", Accidental.SHARP),
            2: SpellingEntry("G", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 2 (A)
            -2: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("A", Accidental.FLAT),
            0: SpellingEntry("A", None),
            1: SpellingEntry("A", Accidental.SHARP),
            2: SpellingEntry("A", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 3 (Bb)
            -2: SpellingEntry("A", Accidental.FLAT),
            -1: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            0: SpellingEntry("B", Accidental.FLAT),
            1: SpellingEntry("B", Accidental.NATURAL),
            2: SpellingEntry("B", Accidental.SHARP),
        },
        {  # Degree 4 (C)
            -2: SpellingEntry("C", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("C", Accidental.FLAT),
            0: SpellingEntry("C", None),
            1: SpellingEntry("C", Accidental.SHARP),
            2: SpellingEntry("C", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 5 (D)
            -2: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("D", Accidental.FLAT),
            0: SpellingEntry("D", None),
            1: SpellingEntry("D", Accidental.SHARP),
            2: SpellingEntry("D", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 6 (E)
            -2: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("E", Accidental.FLAT),
            0: SpellingEntry("E", None),
            1: SpellingEntry("E", Accidental.SHARP),
            2: SpellingEntry("E", Accidental.DOUBLE_SHARP),
        },
    ],
    # C Major (no sharps or flats)
    0: [
        {  # Degree 0 (C)
            -2: SpellingEntry("C", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("C", Accidental.FLAT),
            0: SpellingEntry("C", None),
            1: SpellingEntry("C", Accidental.SHARP),
            2: SpellingEntry("C", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 1 (D)
            -2: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("D", Accidental.FLAT),
            0: SpellingEntry("D", None),
            1: SpellingEntry("D", Accidental.SHARP),
            2: SpellingEntry("D", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 2 (E)
            -2: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("E", Accidental.FLAT),
            0: SpellingEntry("E", None),
            1: SpellingEntry("E", Accidental.SHARP),
            2: SpellingEntry("E", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 3 (F)
            -2: SpellingEntry("F", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("F", Accidental.FLAT),
            0: SpellingEntry("F", None),
            1: SpellingEntry("F", Accidental.SHARP),
            2: SpellingEntry("F", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 4 (G)
            -2: SpellingEntry("G", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("G", Accidental.FLAT),
            0: SpellingEntry("G", None),
            1: SpellingEntry("G", Accidental.SHARP),
            2: SpellingEntry("G", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 5 (A)
            -2: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("A", Accidental.FLAT),
            0: SpellingEntry("A", None),
            1: SpellingEntry("A", Accidental.SHARP),
            2: SpellingEntry("A", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 6 (B)
            -2: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("B", Accidental.FLAT),
            0: SpellingEntry("B", None),
            1: SpellingEntry("B", Accidental.SHARP),
            2: SpellingEntry("B", Accidental.DOUBLE_SHARP),
        },
    ],
    # G Major (1 sharp)
    1: [
        {  # Degree 0 (G)
            -2: SpellingEntry("G", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("G", Accidental.FLAT),
            0: SpellingEntry("G", None),
            1: SpellingEntry("G", Accidental.SHARP),
            2: SpellingEntry("G", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 1 (A)
            -2: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("A", Accidental.FLAT),
            0: SpellingEntry("A", None),
            1: SpellingEntry("A", Accidental.SHARP),
            2: SpellingEntry("A", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 2 (B)
            -2: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("B", Accidental.FLAT),
            0: SpellingEntry("B", None),
            1: SpellingEntry("B", Accidental.SHARP),
            2: SpellingEntry("B", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 3 (C)
            -2: SpellingEntry("C", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("C", Accidental.FLAT),
            0: SpellingEntry("C", None),
            1: SpellingEntry("C", Accidental.SHARP),
            2: SpellingEntry("C", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 4 (D)
            -2: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("D", Accidental.FLAT),
            0: SpellingEntry("D", None),
            1: SpellingEntry("D", Accidental.SHARP),
            2: SpellingEntry("D", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 5 (E)
            -2: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("E", Accidental.FLAT),
            0: SpellingEntry("E", None),
            1: SpellingEntry("E", Accidental.SHARP),
            2: SpellingEntry("E", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 6 (F#)
            -2: SpellingEntry("F", Accidental.FLAT),
            -1: SpellingEntry("F", Accidental.NATURAL),
            0: SpellingEntry("F", Accidental.SHARP),
            1: SpellingEntry("F", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("G", Accidental.SHARP),
        },
    ],
    # D Major (2 sharps)
    2: [
        {  # Degree 0 (D)
            -2: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("D", Accidental.FLAT),
            0: SpellingEntry("D", None),
            1: SpellingEntry("D", Accidental.SHARP),
            2: SpellingEntry("D", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 1 (E)
            -2: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("E", Accidental.FLAT),
            0: SpellingEntry("E", None),
            1: SpellingEntry("E", Accidental.SHARP),
            2: SpellingEntry("E", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 2 (F#)
            -2: SpellingEntry("F", Accidental.FLAT),
            -1: SpellingEntry("F", Accidental.NATURAL),
            0: SpellingEntry("F", Accidental.SHARP),
            1: SpellingEntry("F", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("G", Accidental.SHARP),
        },
        {  # Degree 3 (G)
            -2: SpellingEntry("G", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("G", Accidental.FLAT),
            0: SpellingEntry("G", None),
            1: SpellingEntry("G", Accidental.SHARP),
            2: SpellingEntry("G", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 4 (A)
            -2: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("A", Accidental.FLAT),
            0: SpellingEntry("A", None),
            1: SpellingEntry("A", Accidental.SHARP),
            2: SpellingEntry("A", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 5 (B)
            -2: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("B", Accidental.FLAT),
            0: SpellingEntry("B", None),
            1: SpellingEntry("B", Accidental.SHARP),
            2: SpellingEntry("B", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 6 (C#)
            -2: SpellingEntry("C", Accidental.FLAT),
            -1: SpellingEntry("C", Accidental.NATURAL),
            0: SpellingEntry("C", Accidental.SHARP),
            1: SpellingEntry("C", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("D", Accidental.SHARP),
        },
    ],
    # A Major (3 sharps)
    3: [
        {  # Degree 0 (A)
            -2: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("A", Accidental.FLAT),
            0: SpellingEntry("A", None),
            1: SpellingEntry("A", Accidental.SHARP),
            2: SpellingEntry("A", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 1 (B)
            -2: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("B", Accidental.FLAT),
            0: SpellingEntry("B", None),
            1: SpellingEntry("B", Accidental.SHARP),
            2: SpellingEntry("B", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 2 (C#)
            -2: SpellingEntry("C", Accidental.FLAT),
            -1: SpellingEntry("C", Accidental.NATURAL),
            0: SpellingEntry("C", Accidental.SHARP),
            1: SpellingEntry("C", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("D", Accidental.SHARP),
        },
        {  # Degree 3 (D)
            -2: SpellingEntry("D", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("D", Accidental.FLAT),
            0: SpellingEntry("D", None),
            1: SpellingEntry("D", Accidental.SHARP),
            2: SpellingEntry("D", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 4 (E)
            -2: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("E", Accidental.FLAT),
            0: SpellingEntry("E", None),
            1: SpellingEntry("E", Accidental.SHARP),
            2: SpellingEntry("E", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 5 (F#)
            -2: SpellingEntry("F", Accidental.FLAT),
            -1: SpellingEntry("F", Accidental.NATURAL),
            0: SpellingEntry("F", Accidental.SHARP),
            1: SpellingEntry("F", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("G", Accidental.SHARP),
        },
        {  # Degree 6 (G#)
            -2: SpellingEntry("G", Accidental.FLAT),
            -1: SpellingEntry("G", Accidental.NATURAL),
            0: SpellingEntry("G", Accidental.SHARP),
            1: SpellingEntry("G", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("A", Accidental.SHARP),
        },
    ],
    # E Major (4 sharps)
    4: [
        {  # Degree 0 (E)
            -2: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("E", Accidental.FLAT),
            0: SpellingEntry("E", None),
            1: SpellingEntry("E", Accidental.SHARP),
            2: SpellingEntry("E", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 1 (F#)
            -2: SpellingEntry("F", Accidental.FLAT),
            -1: SpellingEntry("F", Accidental.NATURAL),
            0: SpellingEntry("F", Accidental.SHARP),
            1: SpellingEntry("F", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("G", Accidental.SHARP),
        },
        {  # Degree 2 (G#)
            -2: SpellingEntry("G", Accidental.FLAT),
            -1: SpellingEntry("G", Accidental.NATURAL),
            0: SpellingEntry("G", Accidental.SHARP),
            1: SpellingEntry("G", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("A", Accidental.SHARP),
        },
        {  # Degree 3 (A)
            -2: SpellingEntry("A", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("A", Accidental.FLAT),
            0: SpellingEntry("A", None),
            1: SpellingEntry("A", Accidental.SHARP),
            2: SpellingEntry("A", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 4 (B)
            -2: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("B", Accidental.FLAT),
            0: SpellingEntry("B", None),
            1: SpellingEntry("B", Accidental.SHARP),
            2: SpellingEntry("B", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 5 (C#)
            -2: SpellingEntry("C", Accidental.FLAT),
            -1: SpellingEntry("C", Accidental.NATURAL),
            0: SpellingEntry("C", Accidental.SHARP),
            1: SpellingEntry("C", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("D", Accidental.SHARP),
        },
        {  # Degree 6 (D#)
            -2: SpellingEntry("D", Accidental.FLAT),
            -1: SpellingEntry("D", Accidental.NATURAL),
            0: SpellingEntry("D", Accidental.SHARP),
            1: SpellingEntry("D", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("E", Accidental.SHARP),
        },
    ],
    # B Major (5 sharps)
    5: [
        {  # Degree 0 (B)
            -2: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("B", Accidental.FLAT),
            0: SpellingEntry("B", None),
            1: SpellingEntry("B", Accidental.SHARP),
            2: SpellingEntry("B", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 1 (C#)
            -2: SpellingEntry("C", Accidental.FLAT),
            -1: SpellingEntry("C", Accidental.NATURAL),
            0: SpellingEntry("C", Accidental.SHARP),
            1: SpellingEntry("C", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("D", Accidental.SHARP),
        },
        {  # Degree 2 (D#)
            -2: SpellingEntry("D", Accidental.FLAT),
            -1: SpellingEntry("D", Accidental.NATURAL),
            0: SpellingEntry("D", Accidental.SHARP),
            1: SpellingEntry("D", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("E", Accidental.SHARP),
        },
        {  # Degree 3 (E)
            -2: SpellingEntry("E", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("E", Accidental.FLAT),
            0: SpellingEntry("E", None),
            1: SpellingEntry("E", Accidental.SHARP),
            2: SpellingEntry("E", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 4 (F#)
            -2: SpellingEntry("F", Accidental.FLAT),
            -1: SpellingEntry("F", Accidental.NATURAL),
            0: SpellingEntry("F", Accidental.SHARP),
            1: SpellingEntry("F", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("G", Accidental.SHARP),
        },
        {  # Degree 5 (G#)
            -2: SpellingEntry("G", Accidental.FLAT),
            -1: SpellingEntry("G", Accidental.NATURAL),
            0: SpellingEntry("G", Accidental.SHARP),
            1: SpellingEntry("G", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("A", Accidental.SHARP),
        },
        {  # Degree 6 (A#)
            -2: SpellingEntry("A", Accidental.FLAT),
            -1: SpellingEntry("A", Accidental.NATURAL),
            0: SpellingEntry("A", Accidental.SHARP),
            1: SpellingEntry("A", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("B", Accidental.SHARP),
        },
    ],
    # F# Major (6 sharps)
    6: [
        {  # Degree 0 (F#)
            -2: SpellingEntry("F", Accidental.FLAT),
            -1: SpellingEntry("F", Accidental.NATURAL),
            0: SpellingEntry("F", Accidental.SHARP),
            1: SpellingEntry("F", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("G", Accidental.SHARP),
        },
        {  # Degree 1 (G#)
            -2: SpellingEntry("G", Accidental.FLAT),
            -1: SpellingEntry("G", Accidental.NATURAL),
            0: SpellingEntry("G", Accidental.SHARP),
            1: SpellingEntry("G", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("A", Accidental.SHARP),
        },
        {  # Degree 2 (A#)
            -2: SpellingEntry("A", Accidental.FLAT),
            -1: SpellingEntry("A", Accidental.NATURAL),
            0: SpellingEntry("A", Accidental.SHARP),
            1: SpellingEntry("A", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("B", Accidental.SHARP),
        },
        {  # Degree 3 (B)
            -2: SpellingEntry("B", Accidental.DOUBLE_FLAT),
            -1: SpellingEntry("B", Accidental.FLAT),
            0: SpellingEntry("B", None),
            1: SpellingEntry("B", Accidental.SHARP),
            2: SpellingEntry("B", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 4 (C#)
            -2: SpellingEntry("C", Accidental.FLAT),
            -1: SpellingEntry("C", Accidental.NATURAL),
            0: SpellingEntry("C", Accidental.SHARP),
            1: SpellingEntry("C", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("D", Accidental.SHARP),
        },
        {  # Degree 5 (D#)
            -2: SpellingEntry("D", Accidental.FLAT),
            -1: SpellingEntry("D", Accidental.NATURAL),
            0: SpellingEntry("D", Accidental.SHARP),
            1: SpellingEntry("D", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("E", Accidental.SHARP),
        },
        {  # Degree 6 (E#)
            -2: SpellingEntry("E", Accidental.FLAT),
            -1: SpellingEntry("E", Accidental.NATURAL),
            0: SpellingEntry("E", Accidental.SHARP),
            1: SpellingEntry("E", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("F", Accidental.DOUBLE_SHARP),
        },
    ],
    # C# Major (7 sharps)
    7: [
        {  # Degree 0 (C#)
            -2: SpellingEntry("C", Accidental.FLAT),
            -1: SpellingEntry("C", Accidental.NATURAL),
            0: SpellingEntry("C", Accidental.SHARP),
            1: SpellingEntry("C", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("D", Accidental.SHARP),
        },
        {  # Degree 1 (D#)
            -2: SpellingEntry("D", Accidental.FLAT),
            -1: SpellingEntry("D", Accidental.NATURAL),
            0: SpellingEntry("D", Accidental.SHARP),
            1: SpellingEntry("D", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("E", Accidental.SHARP),
        },
        {  # Degree 2 (E#)
            -2: SpellingEntry("E", Accidental.FLAT),
            -1: SpellingEntry("E", Accidental.NATURAL),
            0: SpellingEntry("E", Accidental.SHARP),
            1: SpellingEntry("E", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("F", Accidental.DOUBLE_SHARP),
        },
        {  # Degree 3 (F#)
            -2: SpellingEntry("F", Accidental.FLAT),
            -1: SpellingEntry("F", Accidental.NATURAL),
            0: SpellingEntry("F", Accidental.SHARP),
            1: SpellingEntry("F", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("G", Accidental.SHARP),
        },
        {  # Degree 4 (G#)
            -2: SpellingEntry("G", Accidental.FLAT),
            -1: SpellingEntry("G", Accidental.NATURAL),
            0: SpellingEntry("G", Accidental.SHARP),
            1: SpellingEntry("G", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("A", Accidental.SHARP),
        },
        {  # Degree 5 (A#)
            -2: SpellingEntry("A", Accidental.FLAT),
            -1: SpellingEntry("A", Accidental.NATURAL),
            0: SpellingEntry("A", Accidental.SHARP),
            1: SpellingEntry("A", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("B", Accidental.SHARP),
        },
        {  # Degree 6 (B#)
            -2: SpellingEntry("B", Accidental.FLAT),
            -1: SpellingEntry("B", Accidental.NATURAL),
            0: SpellingEntry("B", Accidental.SHARP),
            1: SpellingEntry("B", Accidental.DOUBLE_SHARP),
            2: SpellingEntry("C", Accidental.DOUBLE_SHARP),
        },
    ],
}


# =============================================================================
# Key Signature Utilities
# =============================================================================

# MusicalKey enum value -> fifths value mapping
KEY_TO_FIFTHS: dict[str, int] = {
    "C": 0,
    "G": 1,
    "D": 2,
    "A": 3,
    "E": 4,
    "B": 5,
    "F#": 6,
    "Gb": -6,
    "Db": -5,
    "Ab": -4,
    "Eb": -3,
    "Bb": -2,
    "F": -1,
    "C#": 7,
}

# Letter to pitch class
LETTER_TO_PITCH_CLASS: dict[str, int] = {
    "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11
}

# Major scale intervals: W-W-H-W-W-W-H (0, 2, 4, 5, 7, 9, 11)
MAJOR_SCALE_INTERVALS = (0, 2, 4, 5, 7, 9, 11)


def accidental_to_semitone_offset(accidental: Optional[Accidental]) -> int:
    """Get semitone offset for an accidental."""
    if accidental is None:
        return 0
    if accidental == Accidental.DOUBLE_FLAT:
        return -2
    if accidental == Accidental.FLAT:
        return -1
    if accidental == Accidental.NATURAL:
        return 0
    if accidental == Accidental.SHARP:
        return 1
    if accidental == Accidental.DOUBLE_SHARP:
        return 2
    return 0


def _spelling_to_pitch_class(spelling: SpellingEntry) -> int:
    """Compute pitch class (0-11) from a spelling entry."""
    letter_pc = LETTER_TO_PITCH_CLASS[spelling.letter]
    offset = accidental_to_semitone_offset(spelling.accidental)
    return (letter_pc + offset) % 12


def _accidental_complexity(accidental: Optional[Accidental]) -> int:
    """Score accidental complexity (lower is simpler/preferred).
    
    Natural/none = 0, single sharp/flat = 1, double = 2
    """
    if accidental is None or accidental == Accidental.NATURAL:
        return 0
    if accidental in (Accidental.SHARP, Accidental.FLAT):
        return 1
    return 2  # double sharp/flat


def _build_reverse_lookup() -> dict[int, dict[int, tuple[int, int]]]:
    """Build reverse lookup from KEY_ALTERATION_MAP.
    
    For each pitch class in each key, determine the best (degree, alteration)
    by examining all possibilities in the map and picking the one with
    the simplest spelling (prefer natural > single accidental > double).
    
    This ensures we use the map's verified spellings and pick the most
    conventional one when multiple options exist for the same pitch.
    """
    lookup: dict[int, dict[int, tuple[int, int]]] = {}
    
    for key_fifths, degrees in KEY_ALTERATION_MAP.items():
        # Collect all (degree, alteration, spelling) for each pitch class
        pitch_options: dict[int, list[tuple[int, int, SpellingEntry]]] = {}
        
        for degree in range(7):
            for alteration in [-2, -1, 0, 1, 2]:
                spelling = degrees[degree][alteration]
                pitch_class = _spelling_to_pitch_class(spelling)
                
                if pitch_class not in pitch_options:
                    pitch_options[pitch_class] = []
                pitch_options[pitch_class].append((degree, alteration, spelling))
        
        # For each pitch class, pick the best option
        key_lookup: dict[int, tuple[int, int]] = {}
        for pitch_class, options in pitch_options.items():
            # Sort by: alteration 0 first, then accidental complexity, then |alteration|
            def sort_key(opt: tuple[int, int, SpellingEntry]) -> tuple[int, int, int]:
                degree, alteration, spelling = opt
                is_diatonic = 0 if alteration == 0 else 1
                complexity = _accidental_complexity(spelling.accidental)
                return (is_diatonic, complexity, abs(alteration))
            
            options.sort(key=sort_key)
            best_degree, best_alt, _ = options[0]
            key_lookup[pitch_class] = (best_degree, best_alt)
        
        lookup[key_fifths] = key_lookup
    
    return lookup


# Pre-build the reverse lookup at module load time
PITCH_CLASS_LOOKUP: dict[int, dict[int, tuple[int, int]]] = _build_reverse_lookup()


def key_to_fifths(key: str) -> int:
    """Convert a key name to its fifths value.
    
    Args:
        key: Key name like "C", "F#", "Bb", etc.
        
    Returns:
        Number of fifths in the key signature (-7 to +7).
        
    Raises:
        ValueError: If key is not recognized.
    """
    if key not in KEY_TO_FIFTHS:
        raise ValueError(f"Unknown key: {key}")
    return KEY_TO_FIFTHS[key]


def key_to_semitone(key_fifths: int) -> int:
    """Get the semitone (pitch class) of the root note for a key.
    
    Args:
        key_fifths: Key signature in fifths (-7 to +7).
        
    Returns:
        Semitone of root (0=C, 1=C#/Db, ... 11=B).
    """
    # Circle of fifths: each fifth adds 7 semitones (mod 12)
    return (key_fifths * 7 % 12 + 12) % 12


def get_scale_degree_pitches(key_fifths: int) -> tuple[int, ...]:
    """Get the pitch classes for each scale degree in a key.
    
    This is EXACTLY how the UI computes it:
    - Get the tonic pitch class from key_fifths
    - Apply major scale intervals to get diatonic pitches
    
    Args:
        key_fifths: Key signature in fifths.
        
    Returns:
        Tuple of 7 pitch classes (0-11) for degrees 0-6.
    """
    tonic = key_to_semitone(key_fifths)
    return tuple((tonic + interval) % 12 for interval in MAJOR_SCALE_INTERVALS)


def get_scale_degree_and_alteration(
    midi_note: int,
    key_fifths: int,
) -> tuple[int, int]:
    """Look up scale degree and alteration from the pre-built map lookup.
    
    Uses PITCH_CLASS_LOOKUP which is derived directly from KEY_ALTERATION_MAP.
    The map is the source of truth for correct spellings.
    
    Args:
        midi_note: MIDI note number (0-127).
        key_fifths: Key signature in fifths.
        
    Returns:
        Tuple of (degree 0-6, alteration -2 to +2).
        
    Raises:
        ValueError: If pitch class not found in lookup.
    """
    pitch_class = midi_note % 12
    key_lookup = PITCH_CLASS_LOOKUP.get(key_fifths)
    
    if key_lookup is None:
        raise ValueError(f"Unknown key fifths: {key_fifths}")
    
    result = key_lookup.get(pitch_class)
    if result is None:
        raise ValueError(
            f"Cannot determine scale degree for pitch class {pitch_class} in key {key_fifths}"
        )
    
    return result


def get_spelling_from_map(
    key_fifths: int,
    degree: int,
    alteration: int,
) -> SpellingEntry:
    """Look up the correct spelling for a scale degree and alteration.
    
    Args:
        key_fifths: Key signature in fifths (-7 to +7).
        degree: Scale degree (0-6).
        alteration: Alteration from diatonic (-2 to +2).
        
    Returns:
        SpellingEntry with letter and accidental.
        
    Raises:
        KeyError: If lookup fails (invalid key/degree/alteration).
    """
    key_map = KEY_ALTERATION_MAP.get(key_fifths)
    if key_map is None:
        raise KeyError(f"Invalid key fifths: {key_fifths}")
    
    if degree < 0 or degree > 6:
        raise KeyError(f"Invalid degree: {degree}")
    
    degree_map = key_map[degree]
    if alteration not in degree_map:
        raise KeyError(f"Invalid alteration: {alteration}")
    
    return degree_map[alteration]


def spelling_to_pitch_name(
    spelling: SpellingEntry,
    octave: int,
) -> str:
    """Convert a SpellingEntry to a pitch name string.
    
    Args:
        spelling: The letter and accidental.
        octave: The octave number.
        
    Returns:
        String like "C4", "F#5", "Bb3", "Abb2".
    """
    letter = spelling.letter
    acc = spelling.accidental
    
    if acc is None:
        acc_str = ""
    elif acc == Accidental.DOUBLE_FLAT:
        acc_str = "bb"
    elif acc == Accidental.FLAT:
        acc_str = "b"
    elif acc == Accidental.NATURAL:
        acc_str = ""  # Natural sign usually omitted in simple naming
    elif acc == Accidental.SHARP:
        acc_str = "#"
    elif acc == Accidental.DOUBLE_SHARP:
        acc_str = "##"
    else:
        acc_str = ""
    
    return f"{letter}{acc_str}{octave}"


def midi_to_pitch_name_in_key(
    midi_note: int,
    key: str,
) -> str:
    """Convert MIDI note to properly spelled pitch name in a key.
    
    This is the main function for correct enharmonic spelling.
    Instead of just "use sharps" or "use flats", it determines
    the scale degree and returns the correct spelling for that
    degree in the given key.
    
    Args:
        midi_note: MIDI note number (0-127).
        key: Key name like "C", "F#", "Bb", etc.
        
    Returns:
        Pitch name with octave like "C4", "F#5", "Eb3".
        
    Examples:
        >>> midi_to_pitch_name_in_key(66, "G")  # F# in G major
        "F#4"
        >>> midi_to_pitch_name_in_key(65, "G")  # F natural (lowered 7th)
        "F4"
        >>> midi_to_pitch_name_in_key(70, "Bb")  # Bb (tonic)
        "Bb4"
    """
    key_fifths = key_to_fifths(key)
    degree, alteration = get_scale_degree_and_alteration(midi_note, key_fifths)
    spelling = get_spelling_from_map(key_fifths, degree, alteration)
    
    # Calculate octave from MIDI, accounting for accidentals
    # Base octave from MIDI
    octave = (midi_note // 12) - 1
    
    # Adjust for enharmonics that cross octave boundaries
    # e.g., Cb4 is really B3 in MIDI terms
    letter_pitch_class = LETTER_TO_PITCH_CLASS[spelling.letter]
    acc_offset = accidental_to_semitone_offset(spelling.accidental)
    expected_pitch_class = (letter_pitch_class + acc_offset) % 12
    actual_pitch_class = midi_note % 12
    
    # If there's a mismatch due to octave boundary, adjust
    if expected_pitch_class != actual_pitch_class:
        if (expected_pitch_class - actual_pitch_class) % 12 == 1:
            octave -= 1
        elif (actual_pitch_class - expected_pitch_class) % 12 == 1:
            octave += 1
    
    return spelling_to_pitch_name(spelling, octave)
