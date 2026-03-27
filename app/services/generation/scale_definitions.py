"""Scale interval definitions for the generation engine.

All scales are defined as interval patterns in semitones.
Scales are generated fresh from these patterns for each target key.
We do NOT store pre-computed pitches that get transposed.

This ensures deterministic enharmonic spelling because each pitch
is computed as (root_midi + accumulated_intervals), then spelled
using the KEY_ALTERATION_MAP for the target key.
"""
from typing import Dict, List, Optional, Tuple

from app.schemas.generation_schemas import ScaleType


# =============================================================================
# Scale Interval Patterns
# =============================================================================
# Each scale is defined by its ascending interval pattern in semitones.
# W (whole step) = 2 semitones, H (half step) = 1 semitone


# Major scale modes (all derived from same pattern, different starting points)
_MAJOR_INTERVALS = [2, 2, 1, 2, 2, 2, 1]  # W-W-H-W-W-W-H


def _rotate_intervals(intervals: List[int], steps: int) -> Tuple[int, ...]:
    """Rotate interval pattern to create mode starting on different degree."""
    rotated = intervals[steps:] + intervals[:steps]
    return tuple(rotated)


# Harmonic minor: W-H-W-W-H-A2-H (augmented 2nd = 3 semitones)
_HARMONIC_MINOR_INTERVALS = [2, 1, 2, 2, 1, 3, 1]

# Melodic minor (ascending): W-H-W-W-W-W-H
_MELODIC_MINOR_INTERVALS = [2, 1, 2, 2, 2, 2, 1]

# Natural minor (aeolian): W-H-W-W-H-W-W - used for classical melodic minor descending
_NATURAL_MINOR_INTERVALS = [2, 1, 2, 2, 1, 2, 2]

# Harmonic major: W-W-H-W-H-A2-H (major with b6)
_HARMONIC_MAJOR_INTERVALS = [2, 2, 1, 2, 1, 3, 1]


# =============================================================================
# Asymmetric Scales (different pitches ascending vs descending)
# =============================================================================
# These scales have different actual pitches when descending.
# They can only be used for straight up/down patterns, not interval patterns
# like 3rds, 4ths, etc. where direction changes unpredictably.

ASYMMETRIC_SCALES: set[ScaleType] = {
    ScaleType.MELODIC_MINOR_CLASSICAL,
}

# Descending intervals for asymmetric scales (when different from ascending)
SCALE_INTERVALS_DESCENDING: Dict[ScaleType, Tuple[int, ...]] = {
    # Classical melodic minor descends as natural minor
    ScaleType.MELODIC_MINOR_CLASSICAL: tuple(_NATURAL_MINOR_INTERVALS),
}

# Descending spellings for scales with different enharmonic spelling going down
# (same pitches, different note names - sharps up, flats down)
SCALE_SPELLINGS_DESCENDING_IN_C: Dict[ScaleType, Tuple[str, ...]] = {
    # Classical melodic minor descends as natural minor (b6, b7)
    ScaleType.MELODIC_MINOR_CLASSICAL: ("C", "D", "Eb", "F", "G", "Ab", "Bb"),
    # Chromatic scale: sharps ascending, flats descending
    ScaleType.CHROMATIC: ("C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"),
}

# Scales that use different spellings going down (but same pitches)
# These can be used for all exercises - only the notation changes
DIRECTION_AWARE_SPELLING_SCALES: set[ScaleType] = {
    ScaleType.CHROMATIC,
}

# Scales where accidentals should be maximally simplified for readability.
# This includes:
# - Double sharps/flats → single accidentals (F## → G, Bbb → A)
# - "White key" accidentals → naturals (E# → F, B# → C, Fb → E, Cb → B)
# These are symmetric or non-diatonic scales where strict letter-per-degree
# spelling isn't meaningful, and practical readability is more important.
SIMPLIFY_ACCIDENTALS_SCALES: set[ScaleType] = {
    ScaleType.WHOLE_TONE,      # 6-note symmetric scale, only 2 transpositions
    ScaleType.DIMINISHED_HW,   # 8-note symmetric scale, only 3 transpositions
    ScaleType.DIMINISHED_WH,   # 8-note symmetric scale, only 3 transpositions
}


SCALE_INTERVALS: Dict[ScaleType, Tuple[int, ...]] = {
    # Major scale modes
    ScaleType.IONIAN: tuple(_MAJOR_INTERVALS),  # 1st mode
    ScaleType.DORIAN: _rotate_intervals(_MAJOR_INTERVALS, 1),  # 2nd mode
    ScaleType.PHRYGIAN: _rotate_intervals(_MAJOR_INTERVALS, 2),  # 3rd mode
    ScaleType.LYDIAN: _rotate_intervals(_MAJOR_INTERVALS, 3),  # 4th mode
    ScaleType.MIXOLYDIAN: _rotate_intervals(_MAJOR_INTERVALS, 4),  # 5th mode
    ScaleType.AEOLIAN: _rotate_intervals(_MAJOR_INTERVALS, 5),  # 6th mode (natural minor)
    ScaleType.LOCRIAN: _rotate_intervals(_MAJOR_INTERVALS, 6),  # 7th mode
    
    # Harmonic minor modes
    ScaleType.HARMONIC_MINOR: tuple(_HARMONIC_MINOR_INTERVALS),
    ScaleType.LOCRIAN_NAT6: _rotate_intervals(_HARMONIC_MINOR_INTERVALS, 1),
    ScaleType.IONIAN_AUG: _rotate_intervals(_HARMONIC_MINOR_INTERVALS, 2),
    ScaleType.DORIAN_SHARP4: _rotate_intervals(_HARMONIC_MINOR_INTERVALS, 3),
    ScaleType.PHRYGIAN_DOMINANT: _rotate_intervals(_HARMONIC_MINOR_INTERVALS, 4),
    ScaleType.LYDIAN_SHARP2: _rotate_intervals(_HARMONIC_MINOR_INTERVALS, 5),
    ScaleType.SUPER_LOCRIAN_BB7: _rotate_intervals(_HARMONIC_MINOR_INTERVALS, 6),
    
    # Melodic minor modes
    ScaleType.MELODIC_MINOR: tuple(_MELODIC_MINOR_INTERVALS),
    ScaleType.MELODIC_MINOR_CLASSICAL: tuple(_MELODIC_MINOR_INTERVALS),  # Ascending same, descending different
    ScaleType.DORIAN_FLAT2: _rotate_intervals(_MELODIC_MINOR_INTERVALS, 1),
    ScaleType.LYDIAN_AUGMENTED: _rotate_intervals(_MELODIC_MINOR_INTERVALS, 2),
    ScaleType.LYDIAN_DOMINANT: _rotate_intervals(_MELODIC_MINOR_INTERVALS, 3),
    ScaleType.MIXOLYDIAN_FLAT6: _rotate_intervals(_MELODIC_MINOR_INTERVALS, 4),
    ScaleType.LOCRIAN_NAT2: _rotate_intervals(_MELODIC_MINOR_INTERVALS, 5),
    ScaleType.ALTERED: _rotate_intervals(_MELODIC_MINOR_INTERVALS, 6),
    
    # Harmonic major modes (W W H W H A2 H = major with b6)
    ScaleType.HARMONIC_MAJOR: tuple(_HARMONIC_MAJOR_INTERVALS),
    ScaleType.DORIAN_FLAT5: _rotate_intervals(_HARMONIC_MAJOR_INTERVALS, 1),
    ScaleType.PHRYGIAN_FLAT4: _rotate_intervals(_HARMONIC_MAJOR_INTERVALS, 2),
    ScaleType.LYDIAN_FLAT3: _rotate_intervals(_HARMONIC_MAJOR_INTERVALS, 3),
    ScaleType.MIXOLYDIAN_FLAT2: _rotate_intervals(_HARMONIC_MAJOR_INTERVALS, 4),
    ScaleType.LYDIAN_AUG_SHARP2: _rotate_intervals(_HARMONIC_MAJOR_INTERVALS, 5),
    ScaleType.LOCRIAN_DOUBLE_FLAT7: _rotate_intervals(_HARMONIC_MAJOR_INTERVALS, 6),
    
    # Pentatonic scales (5 notes per octave)
    ScaleType.PENTATONIC_MAJOR: (2, 2, 3, 2, 3),  # 1-2-3-5-6
    ScaleType.PENTATONIC_MINOR: (3, 2, 2, 3, 2),  # 1-b3-4-5-b7
    
    # Blues scales (pentatonic + blue note)
    ScaleType.BLUES: (3, 2, 1, 1, 3, 2),  # 1-b3-4-#4-5-b7 (minor pent + #4)
    ScaleType.BLUES_MAJOR: (2, 1, 1, 3, 2, 3),  # 1-2-b3-3-5-6 (major pent + b3)
    
    # Symmetric scales
    ScaleType.WHOLE_TONE: (2, 2, 2, 2, 2, 2),  # All whole steps (6 notes)
    ScaleType.DIMINISHED_HW: (1, 2, 1, 2, 1, 2, 1, 2),  # Half-whole (8 notes)
    ScaleType.DIMINISHED_WH: (2, 1, 2, 1, 2, 1, 2, 1),  # Whole-half (8 notes)
    ScaleType.CHROMATIC: (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1),  # All half steps
    
    # Bebop scales (8 notes - add passing tone for rhythmic alignment)
    ScaleType.BEBOP_DOMINANT: (2, 2, 1, 2, 2, 1, 1, 1),  # Mixolydian + natural 7
    ScaleType.BEBOP_MAJOR: (2, 2, 1, 2, 1, 1, 2, 1),  # Major + #5 passing
    ScaleType.BEBOP_DORIAN: (2, 1, 1, 1, 2, 2, 1, 2),  # Dorian + natural 3
}


# =============================================================================
# Scale Pitch Names in C (canonical spellings)
# =============================================================================
# Each scale is defined with its correct note spellings in C.
# These are transposed to other keys using the transposition system.
# Format: tuple of pitch names (without octave) for one octave of the scale.

SCALE_SPELLINGS_IN_C: Dict[ScaleType, Tuple[str, ...]] = {
    # Major scale modes
    ScaleType.IONIAN: ("C", "D", "E", "F", "G", "A", "B"),
    ScaleType.DORIAN: ("C", "D", "Eb", "F", "G", "A", "Bb"),
    ScaleType.PHRYGIAN: ("C", "Db", "Eb", "F", "G", "Ab", "Bb"),
    ScaleType.LYDIAN: ("C", "D", "E", "F#", "G", "A", "B"),
    ScaleType.MIXOLYDIAN: ("C", "D", "E", "F", "G", "A", "Bb"),
    ScaleType.AEOLIAN: ("C", "D", "Eb", "F", "G", "Ab", "Bb"),
    ScaleType.LOCRIAN: ("C", "Db", "Eb", "F", "Gb", "Ab", "Bb"),
    
    # Harmonic minor modes
    ScaleType.HARMONIC_MINOR: ("C", "D", "Eb", "F", "G", "Ab", "B"),
    ScaleType.LOCRIAN_NAT6: ("C", "Db", "Eb", "F", "Gb", "A", "Bb"),
    ScaleType.IONIAN_AUG: ("C", "D", "E", "F", "G#", "A", "B"),
    ScaleType.DORIAN_SHARP4: ("C", "D", "Eb", "F#", "G", "A", "Bb"),
    ScaleType.PHRYGIAN_DOMINANT: ("C", "Db", "E", "F", "G", "Ab", "Bb"),
    ScaleType.LYDIAN_SHARP2: ("C", "D#", "E", "F#", "G", "A", "B"),
    ScaleType.SUPER_LOCRIAN_BB7: ("C", "Db", "Eb", "Fb", "Gb", "Ab", "Bbb"),
    
    # Melodic minor modes
    ScaleType.MELODIC_MINOR: ("C", "D", "Eb", "F", "G", "A", "B"),
    ScaleType.MELODIC_MINOR_CLASSICAL: ("C", "D", "Eb", "F", "G", "A", "B"),  # Ascending (descending uses natural minor)
    ScaleType.DORIAN_FLAT2: ("C", "Db", "Eb", "F", "G", "A", "Bb"),
    ScaleType.LYDIAN_AUGMENTED: ("C", "D", "E", "F#", "G#", "A", "B"),
    ScaleType.LYDIAN_DOMINANT: ("C", "D", "E", "F#", "G", "A", "Bb"),
    ScaleType.MIXOLYDIAN_FLAT6: ("C", "D", "E", "F", "G", "Ab", "Bb"),
    ScaleType.LOCRIAN_NAT2: ("C", "D", "Eb", "F", "Gb", "Ab", "Bb"),
    ScaleType.ALTERED: ("C", "Db", "Eb", "Fb", "Gb", "Ab", "Bb"),
    
    # Harmonic major modes
    ScaleType.HARMONIC_MAJOR: ("C", "D", "E", "F", "G", "Ab", "B"),
    ScaleType.DORIAN_FLAT5: ("C", "D", "Eb", "F", "Gb", "A", "Bb"),
    ScaleType.PHRYGIAN_FLAT4: ("C", "Db", "Eb", "Fb", "G", "Ab", "Bb"),
    ScaleType.LYDIAN_FLAT3: ("C", "D", "Eb", "F#", "G", "A", "B"),
    ScaleType.MIXOLYDIAN_FLAT2: ("C", "Db", "E", "F", "G", "A", "Bb"),
    ScaleType.LYDIAN_AUG_SHARP2: ("C", "D#", "E", "F#", "G#", "A", "B"),
    ScaleType.LOCRIAN_DOUBLE_FLAT7: ("C", "Db", "Eb", "F", "Gb", "Ab", "Bbb"),
    
    # Pentatonic scales
    ScaleType.PENTATONIC_MAJOR: ("C", "D", "E", "G", "A"),
    ScaleType.PENTATONIC_MINOR: ("C", "Eb", "F", "G", "Bb"),
    
    # Blues scales - note: #4 not b5 for the "blue note"
    ScaleType.BLUES: ("C", "Eb", "F", "F#", "G", "Bb"),  # 1 b3 4 #4 5 b7
    ScaleType.BLUES_MAJOR: ("C", "D", "Eb", "E", "G", "A"),  # 1 2 b3 3 5 6
    
    # Symmetric scales
    ScaleType.WHOLE_TONE: ("C", "D", "E", "F#", "G#", "A#"),
    ScaleType.DIMINISHED_HW: ("C", "Db", "Eb", "E", "F#", "G", "A", "Bb"),
    ScaleType.DIMINISHED_WH: ("C", "D", "Eb", "F", "Gb", "Ab", "A", "B"),
    ScaleType.CHROMATIC: ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"),
    
    # Bebop scales
    ScaleType.BEBOP_DOMINANT: ("C", "D", "E", "F", "G", "A", "Bb", "B"),
    ScaleType.BEBOP_MAJOR: ("C", "D", "E", "F", "G", "G#", "A", "B"),
    ScaleType.BEBOP_DORIAN: ("C", "D", "Eb", "E", "F", "G", "A", "Bb"),
}


def get_scale_spellings(scale_type: ScaleType) -> Tuple[str, ...]:
    """Get the canonical pitch spellings for a scale in C.
    
    Args:
        scale_type: The scale type.
        
    Returns:
        Tuple of pitch names (without octave) in C.
        
    Raises:
        KeyError: If scale type not defined.
    """
    return SCALE_SPELLINGS_IN_C[scale_type]


# =============================================================================
# Pitch Name Transposition
# =============================================================================

# Mapping from pitch name to semitone offset from C
PITCH_NAME_TO_SEMITONE: Dict[str, int] = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4, "E#": 5, "F": 5, "F#": 6, "Gb": 6,
    "G": 7, "G#": 8, "Ab": 8, "A": 9, "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11, "B#": 0,
    # Double accidentals
    "Bbb": 9, "Cbb": 10, "Dbb": 0, "Ebb": 2, "Fbb": 3,
    "Gbb": 5, "Abb": 7,
    "C##": 2, "D##": 4, "E##": 6, "F##": 7, "G##": 9,
    "A##": 11, "B##": 1,
}

# Semitone to natural letter (for transposition reference)
SEMITONE_TO_LETTER: Dict[int, str] = {
    0: "C", 2: "D", 4: "E", 5: "F", 7: "G", 9: "A", 11: "B"
}

# Letter to semitone
LETTER_TO_SEMITONE: Dict[str, int] = {
    "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11
}

# Letter order for transposition
LETTER_ORDER = ["C", "D", "E", "F", "G", "A", "B"]

# Semitone interval to letter steps mapping
# Sharp preference: keeps same letter when possible (C+1=C#, not Db)
SEMITONE_TO_LETTER_STEPS_SHARP = {
    0: 0,   # unison
    1: 0,   # C# (keep letter)
    2: 1,   # D
    3: 1,   # D# (keep letter)
    4: 2,   # E
    5: 3,   # F
    6: 3,   # F# (keep letter)
    7: 4,   # G
    8: 4,   # G# (keep letter)
    9: 5,   # A
    10: 5,  # A# (keep letter)
    11: 6,  # B
}

# Flat preference: moves to next letter when possible (C+1=Db, not C#)
SEMITONE_TO_LETTER_STEPS_FLAT = {
    0: 0,   # unison
    1: 1,   # Db (advance letter)
    2: 1,   # D
    3: 2,   # Eb (advance letter)
    4: 2,   # E
    5: 3,   # F
    6: 4,   # Gb (advance letter)
    7: 4,   # G
    8: 5,   # Ab (advance letter)
    9: 5,   # A
    10: 6,  # Bb (advance letter)
    11: 6,  # B
}


def transpose_pitch_name(pitch_name: str, semitones: int, prefer_sharps: bool = True) -> str:
    """Transpose a pitch name by a number of semitones, preserving letter relationships.
    
    Each scale degree maps to the correct letter name, then the appropriate
    accidental is added (including double sharps/flats when needed).
    
    Args:
        pitch_name: Pitch name without octave (e.g., "C", "Eb", "F#").
        semitones: Number of semitones to transpose (positive = up).
        prefer_sharps: If True, use sharp spellings. If False, use flat spellings.
        
    Returns:
        Transposed pitch name with correct letter and accidental.
    """
    if semitones == 0:
        return pitch_name
    
    # Parse the pitch name
    if len(pitch_name) >= 2 and pitch_name[1] in "#b":
        letter = pitch_name[0]
    else:
        letter = pitch_name[0]
    
    # Get current semitone value
    current_semitone = PITCH_NAME_TO_SEMITONE.get(pitch_name, 0)
    
    # Calculate target semitone (mod 12 for pitch class)
    target_semitone = (current_semitone + semitones) % 12
    
    # Calculate semitone interval (mod 12)
    interval = semitones % 12
    if interval < 0:
        interval += 12
    
    # Get letter steps based on interval and sharp/flat preference
    letter_steps_map = SEMITONE_TO_LETTER_STEPS_SHARP if prefer_sharps else SEMITONE_TO_LETTER_STEPS_FLAT
    letter_steps = letter_steps_map[interval]
    
    # Calculate new letter
    letter_index = LETTER_ORDER.index(letter)
    new_letter_index = (letter_index + letter_steps) % 7
    new_letter = LETTER_ORDER[new_letter_index]
    
    # Calculate needed accidental
    natural_semitone = LETTER_TO_SEMITONE[new_letter]
    diff = (target_semitone - natural_semitone) % 12
    
    # Convert diff to accidental
    if diff == 0:
        return new_letter
    elif diff == 1:
        return new_letter + "#"
    elif diff == 2:
        return new_letter + "##"
    elif diff == 11:
        return new_letter + "b"
    elif diff == 10:
        return new_letter + "bb"
    else:
        # Shouldn't happen with correct letter step mapping
        return new_letter + ("#" if prefer_sharps else "b")


# Keys that use sharps (positive fifths in circle of fifths)
SHARP_KEYS = {"G", "D", "A", "E", "B", "F#", "C#"}

# Keys that use flats (negative fifths in circle of fifths)
FLAT_KEYS = {"F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"}


def key_prefers_sharps(key_name: str) -> bool:
    """Determine if a key signature prefers sharps over flats.
    
    Args:
        key_name: Key name like "C#", "Db", "G", etc.
        
    Returns:
        True if key uses sharps, False if it uses flats.
        C major returns True (neutral, but conventionally sharp-leaning).
    """
    return key_name in SHARP_KEYS or key_name == "C"


def simplify_accidental(pitch_name: str) -> str:
    """Simplify accidentals to their most readable enharmonic equivalent.
    
    For scales where practical readability is more important than
    strict letter-per-degree spelling (e.g., whole tone, diminished).
    
    Simplifies:
    - Double sharps/flats → naturals or single accidentals (F## → G, Bbb → A)
    - "White key" accidentals → naturals (E# → F, B# → C, Fb → E, Cb → B)
    
    Args:
        pitch_name: Pitch name possibly with accidental (e.g., "F##", "E#", "Cb")
        
    Returns:
        Simplified pitch name (e.g., "F##" -> "G", "E#" -> "F", "Cb" -> "B")
    """
    # Handle double sharps
    if "##" in pitch_name:
        letter = pitch_name[0]
        original_semitone = LETTER_TO_SEMITONE[letter]
        target_semitone = (original_semitone + 2) % 12
        # Find the simplest spelling for this semitone
        # Prefer naturals, then sharps
        for check_letter in LETTER_ORDER:
            if LETTER_TO_SEMITONE[check_letter] == target_semitone:
                return check_letter
        # Need a single accidental
        for check_letter in LETTER_ORDER:
            if (LETTER_TO_SEMITONE[check_letter] + 1) % 12 == target_semitone:
                return check_letter + "#"
            if (LETTER_TO_SEMITONE[check_letter] - 1) % 12 == target_semitone:
                return check_letter + "b"
    
    # Handle double flats
    elif "bb" in pitch_name:
        letter = pitch_name[0]
        original_semitone = LETTER_TO_SEMITONE[letter]
        target_semitone = (original_semitone - 2) % 12
        # Find the simplest spelling for this semitone
        for check_letter in LETTER_ORDER:
            if LETTER_TO_SEMITONE[check_letter] == target_semitone:
                return check_letter
        # Need a single accidental - prefer flats since we came from bb
        for check_letter in LETTER_ORDER:
            if (LETTER_TO_SEMITONE[check_letter] - 1) % 12 == target_semitone:
                return check_letter + "b"
            if (LETTER_TO_SEMITONE[check_letter] + 1) % 12 == target_semitone:
                return check_letter + "#"
    
    # Handle "white key" accidentals: E#→F, B#→C, Fb→E, Cb→B
    elif pitch_name == "E#":
        return "F"
    elif pitch_name == "B#":
        return "C"
    elif pitch_name == "Fb":
        return "E"
    elif pitch_name == "Cb":
        return "B"
    
    return pitch_name


def get_transposed_scale_spellings(
    scale_type: ScaleType, 
    key_semitones: int,
    key_name: Optional[str] = None,
) -> Tuple[str, ...]:
    """Get scale spellings transposed to a specific key.
    
    Args:
        scale_type: The scale type.
        key_semitones: Semitones from C (0=C, 1=C#/Db, 2=D, etc.).
        key_name: Optional key name (e.g., "C#", "Db") to determine
            sharp vs flat preference. If not provided, defaults to
            sharps for positive semitones, flats for enharmonic equivalents.
        
    Returns:
        Tuple of pitch names for the scale in the target key.
    """
    c_spellings = SCALE_SPELLINGS_IN_C[scale_type]
    
    # Determine sharp preference from key name if provided
    prefer_sharps = key_prefers_sharps(key_name) if key_name else True
    
    result = tuple(
        transpose_pitch_name(name, key_semitones, prefer_sharps) 
        for name in c_spellings
    )
    
    # For scales where practical readability is more important than strict
    # letter-per-degree spelling, simplify accidentals
    if scale_type in SIMPLIFY_ACCIDENTALS_SCALES:
        result = tuple(simplify_accidental(name) for name in result)
    
    return result


def get_scale_intervals(scale_type: ScaleType) -> Tuple[int, ...]:
    """Get the interval pattern for a scale type.
    
    Args:
        scale_type: The scale type enum value.
        
    Returns:
        Tuple of intervals in semitones (ascending).
        
    Raises:
        KeyError: If scale type is not defined.
    """
    return SCALE_INTERVALS[scale_type]


def get_scale_note_count(scale_type: ScaleType) -> int:
    """Get the number of unique notes in one octave of the scale.
    
    Args:
        scale_type: The scale type enum value.
        
    Returns:
        Number of notes per octave (e.g., 7 for diatonic, 5 for pentatonic).
    """
    return len(SCALE_INTERVALS[scale_type])


def scale_spans_octave(scale_type: ScaleType) -> bool:
    """Check if the scale's intervals sum to exactly 12 semitones (one octave).
    
    Some scales like chromatic or blues may have different totals.
    
    Args:
        scale_type: The scale type enum value.
        
    Returns:
        True if intervals sum to 12.
    """
    return sum(SCALE_INTERVALS[scale_type]) == 12


def is_asymmetric_scale(scale_type: ScaleType) -> bool:
    """Check if scale has different pitches ascending vs descending.
    
    Asymmetric scales (like classical melodic minor) use different
    intervals and pitches when descending. These scales cannot be
    used for pattern exercises (3rds, 4ths, etc.) where direction
    changes unpredictably.
    
    Args:
        scale_type: The scale type enum value.
        
    Returns:
        True if scale is asymmetric.
    """
    return scale_type in ASYMMETRIC_SCALES


def get_scale_intervals_descending(scale_type: ScaleType) -> Tuple[int, ...]:
    """Get descending intervals for a scale.
    
    For asymmetric scales, returns different intervals than ascending.
    For symmetric scales, returns the same as ascending.
    
    Args:
        scale_type: The scale type enum value.
        
    Returns:
        Tuple of intervals in semitones for descending.
    """
    if scale_type in SCALE_INTERVALS_DESCENDING:
        return SCALE_INTERVALS_DESCENDING[scale_type]
    return SCALE_INTERVALS[scale_type]


def get_transposed_scale_spellings_descending(
    scale_type: ScaleType, 
    key_semitones: int,
    key_name: Optional[str] = None,
) -> Tuple[str, ...]:
    """Get descending scale spellings transposed to a specific key.
    
    For asymmetric scales (like classical melodic minor), returns
    different spellings than ascending. For symmetric scales,
    returns the same as ascending.
    
    Args:
        scale_type: The scale type.
        key_semitones: Semitones from C (0=C, 1=C#/Db, 2=D, etc.).
        key_name: Optional key name to determine sharp vs flat preference.
        
    Returns:
        Tuple of pitch names for descending in the target key.
    """
    if scale_type in SCALE_SPELLINGS_DESCENDING_IN_C:
        c_spellings = SCALE_SPELLINGS_DESCENDING_IN_C[scale_type]
    else:
        c_spellings = SCALE_SPELLINGS_IN_C[scale_type]
    
    prefer_sharps = key_prefers_sharps(key_name) if key_name else True
    
    return tuple(
        transpose_pitch_name(name, key_semitones, prefer_sharps) 
        for name in c_spellings
    )


# =============================================================================
# Chromatic Spelling with Leading Tone Rule
# =============================================================================
# For chromatic passages, accidentals are determined by musical context:
# - Chromatic notes leading UP to a scale tone use sharps
# - Chromatic notes leading DOWN to a scale tone use flats
# This is based on voice-leading conventions in tonal music.


# Major scale pitch classes (semitones from root)
MAJOR_SCALE_PITCH_CLASSES = {0, 2, 4, 5, 7, 9, 11}  # 1, 2, 3, 4, 5, 6, 7

# Chromatic note resolution targets for leading tone spelling
# Maps pitch class -> (sharp_spelling, flat_spelling, sharp_target_letter, flat_target_letter)
# Sharp spelling is used when resolving up to sharp_target_letter
# Flat spelling is used when resolving down to flat_target_letter
CHROMATIC_RESOLUTION_MAP = {
    1: ("C#", "Db", "D", "C"),   # C#→D (up), Db→C (down)
    3: ("D#", "Eb", "E", "D"),   # D#→E (up), Eb→D (down)
    6: ("F#", "Gb", "G", "F"),   # F#→G (up), Gb→F (down)
    8: ("G#", "Ab", "A", "G"),   # G#→A (up), Ab→G (down)
    10: ("A#", "Bb", "B", "A"),  # A#→B (up), Bb→A (down)
}


def get_chromatic_pitch_names(
    midi_notes: List[int],
    key_name: str,
) -> List[str]:
    """Get pitch names for chromatic passages using leading tone rule.
    
    Determines sharp vs flat spelling based on where each chromatic note
    resolves. This follows standard voice-leading conventions:
    - Notes leading UP use sharps (e.g., F# leading to G)
    - Notes leading DOWN use flats (e.g., Eb leading to D)
    - Scale tones are spelled according to the key signature
    
    Resolution is octave-agnostic: we look at the letter name of the target
    note, not its absolute pitch. So D# leading to E5 or E3 both use D#.
    
    Groups of consecutive enharmonic notes (e.g., multiple D#/Eb across
    octaves) are all spelled the same based on where the group resolves.
    
    Args:
        midi_notes: List of MIDI note numbers.
        key_name: Key name (e.g., "C", "G", "Bb") to determine scale tones.
        
    Returns:
        List of pitch names with correct chromatic spelling.
    """
    from .enharmonic_spelling import midi_to_pitch_name_in_key
    
    if not midi_notes:
        return []
    
    # Map theoretical keys to practical enharmonic equivalents
    # These keys (D#, G#, A#) are enharmonically Eb, Ab, Bb
    ENHARMONIC_KEY_MAP = {
        "D#": "Eb", "d#": "Eb",
        "G#": "Ab", "g#": "Ab", 
        "A#": "Bb", "a#": "Bb",
    }
    effective_key = ENHARMONIC_KEY_MAP.get(key_name, key_name)
    
    # Get the key's root pitch class
    key_semitones = 0
    key_upper = key_name.upper() if len(key_name) == 1 else key_name[0].upper() + key_name[1:]
    for letter, semitone in LETTER_TO_SEMITONE.items():
        if key_upper.startswith(letter):
            key_semitones = semitone
            if len(key_upper) > 1:
                if key_upper[1] == '#':
                    key_semitones = (key_semitones + 1) % 12
                elif key_upper[1].lower() == 'b':
                    key_semitones = (key_semitones - 1) % 12
            break
    
    # Calculate which pitch classes are in the major scale for this key
    scale_pitch_classes = {(key_semitones + pc) % 12 for pc in MAJOR_SCALE_PITCH_CLASSES}
    
    # Helper to get letter name from MIDI note (for resolution target checking)
    def get_letter_from_midi(midi: int) -> str:
        """Get the natural letter name for a MIDI note's pitch class."""
        pc = midi % 12
        # Map pitch class to natural letter (or closest)
        PC_TO_LETTER = {
            0: "C", 1: "C", 2: "D", 3: "D", 4: "E", 5: "F",
            6: "F", 7: "G", 8: "G", 9: "A", 10: "A", 11: "B"
        }
        return PC_TO_LETTER[pc]
    
    # First pass: identify scale tones vs chromatic tones
    result: List[Optional[str]] = [None] * len(midi_notes)
    chromatic_groups = []  # List of (start_idx, end_idx, pitch_class) for groups
    
    i = 0
    while i < len(midi_notes):
        midi = midi_notes[i]
        pitch_class = midi % 12
        octave = (midi // 12) - 1
        
        # If it's a scale tone, use standard key-aware spelling
        if pitch_class in scale_pitch_classes:
            result[i] = midi_to_pitch_name_in_key(midi, effective_key)
            i += 1
            continue
        
        # It's a chromatic note - find the extent of consecutive enharmonic notes
        group_start = i
        group_pc = pitch_class
        while i < len(midi_notes) and (midi_notes[i] % 12) == group_pc:
            i += 1
        group_end = i  # exclusive
        
        chromatic_groups.append((group_start, group_end, group_pc))
    
    # Second pass: resolve each chromatic group based on the NEXT non-enharmonic note
    for group_start, group_end, group_pc in chromatic_groups:
        # Look ahead to find the resolution target
        resolution_target_letter = None
        for j in range(group_end, len(midi_notes)):
            target_pc = midi_notes[j] % 12
            if target_pc != group_pc:
                # Found a different note - get its letter
                # For chromatic notes, we need the "expected" letter based on pitch class
                # For scale tones, we can use the spelled result
                spelled = result[j]
                if spelled is not None:
                    resolution_target_letter = spelled[0]  # First char is letter
                else:
                    resolution_target_letter = get_letter_from_midi(midi_notes[j])
                break
        
        # If no resolution found ahead, look backward
        if resolution_target_letter is None:
            for j in range(group_start - 1, -1, -1):
                target_pc = midi_notes[j] % 12
                if target_pc != group_pc:
                    spelled = result[j]
                    if spelled is not None:
                        resolution_target_letter = spelled[0]
                    else:
                        resolution_target_letter = get_letter_from_midi(midi_notes[j])
                    break
        
        # Determine spelling based on resolution target
        if group_pc in CHROMATIC_RESOLUTION_MAP:
            sharp_name, flat_name, sharp_target, flat_target = CHROMATIC_RESOLUTION_MAP[group_pc]
            
            if resolution_target_letter == sharp_target:
                # Resolving up - use sharp
                chosen_name = sharp_name
            elif resolution_target_letter == flat_target:
                # Resolving down - use flat
                chosen_name = flat_name
            else:
                # Ambiguous - default to sharp
                chosen_name = sharp_name
        else:
            # Not a standard chromatic pitch class - use fallback
            midi = midi_notes[group_start]
            name = midi_to_pitch_name_in_key(midi, effective_key)
            chosen_name = ''.join(c for c in name if not c.isdigit())
        
        # Apply the chosen spelling to all notes in the group
        for idx in range(group_start, group_end):
            midi = midi_notes[idx]
            octave = (midi // 12) - 1
            result[idx] = f"{chosen_name}{octave}"
    
    # Filter out None values (should not happen if algorithm is correct)
    return [s for s in result if s is not None]
