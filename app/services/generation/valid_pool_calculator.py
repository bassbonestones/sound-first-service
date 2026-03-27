"""Valid Pool Calculator for the generation engine.

Computes which generation parameters (scale types, arpeggio types, patterns,
rhythms, keys) are valid options given a user's mastered capabilities.

The practice session queries this upfront to know its possible pool, then
selects from that pool. This ensures generated content never requires
capabilities the user hasn't mastered.
"""

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, FrozenSet, List, Optional, Set, Tuple

from app.schemas.generation_schemas import (
    ArpeggioPattern,
    ArpeggioType,
    MusicalKey,
    RhythmType,
    ScalePattern,
    ScaleType,
)
from app.services.generation.arpeggio_definitions import ARPEGGIO_INTERVALS
from app.services.generation.scale_definitions import SCALE_INTERVALS, SCALE_SPELLINGS_IN_C
from app.services.generation.enharmonic_spelling import (
    KEY_ALTERATION_MAP,
    Accidental,
    get_spelling_from_map,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Note Spelling and Transposition
# =============================================================================

# Letter names in order (C=0, D=1, ... B=6)
LETTER_NAMES = ("C", "D", "E", "F", "G", "A", "B")

# Semitone value of each natural note
LETTER_SEMITONES: Dict[str, int] = {
    "C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11
}

# Accidental modifications in semitones
ACCIDENTAL_SEMITONES: Dict[str, int] = {
    "bb": -2, "b": -1, "": 0, "#": 1, "##": 2
}

# Key root notes (letter + accidental)
KEY_ROOTS: Dict[MusicalKey, str] = {
    MusicalKey.C: "C",
    MusicalKey.D_FLAT: "Db",
    MusicalKey.D: "D",
    MusicalKey.E_FLAT: "Eb",
    MusicalKey.E: "E",
    MusicalKey.F: "F",
    MusicalKey.G_FLAT: "Gb",
    MusicalKey.F_SHARP: "F#",
    MusicalKey.G: "G",
    MusicalKey.A_FLAT: "Ab",
    MusicalKey.G_SHARP: "G#",
    MusicalKey.A: "A",
    MusicalKey.B_FLAT: "Bb",
    MusicalKey.A_SHARP: "A#",
    MusicalKey.B: "B",
    MusicalKey.C_SHARP: "C#",
    MusicalKey.D_SHARP: "D#",
}

# Key signature fifths values (same as musicxml_output.py)
KEY_TO_FIFTHS: Dict[MusicalKey, int] = {
    MusicalKey.C: 0,
    MusicalKey.G: 1, MusicalKey.D: 2, MusicalKey.A: 3,
    MusicalKey.E: 4, MusicalKey.B: 5, MusicalKey.F_SHARP: 6,
    MusicalKey.C_SHARP: 7,
    MusicalKey.F: -1, MusicalKey.B_FLAT: -2, MusicalKey.E_FLAT: -3,
    MusicalKey.A_FLAT: -4, MusicalKey.D_FLAT: -5, MusicalKey.G_FLAT: -6,
    # Enharmonic equivalents - use nearest practical fifths
    MusicalKey.D_SHARP: 6,  # Treated like F#
    MusicalKey.G_SHARP: 6,  # Treated like F# (no practical 8 sharps)
    MusicalKey.A_SHARP: 6,  # Treated like F# (no practical 10 sharps)
}

# Major scale semitones from root (for computing alterations)
MAJOR_SCALE_SEMITONES = (0, 2, 4, 5, 7, 9, 11)


# =============================================================================
# Mode/Scale Key Signature Offsets
# =============================================================================
# When determining the key signature for a modal scale, we adjust from the
# root's major key signature. For example, A Mixolydian uses D major's key
# signature (not A major's), which is -1 fifth from A major.
# This matches the UI logic in generationNotation.ts MODE_FIFTHS_OFFSET.

SCALE_FIFTHS_OFFSET: Dict[ScaleType, int] = {
    # Church modes (diatonic)
    ScaleType.IONIAN: 0,       # Major scale - no offset
    ScaleType.DORIAN: -2,      # 2nd mode - down 2 fifths from parallel major
    ScaleType.PHRYGIAN: -4,    # 3rd mode - down 4 fifths
    ScaleType.LYDIAN: 1,       # 4th mode - up 1 fifth
    ScaleType.MIXOLYDIAN: -1,  # 5th mode - down 1 fifth
    ScaleType.AEOLIAN: -3,     # Natural minor (6th mode) - down 3 fifths
    ScaleType.LOCRIAN: -5,     # 7th mode - down 5 fifths
    
    # Pentatonic & Blues (based on parent scale)
    ScaleType.PENTATONIC_MAJOR: 0,   # Subset of major
    ScaleType.PENTATONIC_MINOR: -3,  # Subset of natural minor
    ScaleType.BLUES: -3,             # Based on minor pentatonic
    ScaleType.BLUES_MAJOR: 0,        # Based on major pentatonic
    
    # Harmonic minor modes
    ScaleType.HARMONIC_MINOR: -3,
    ScaleType.LOCRIAN_NAT6: -5,
    ScaleType.IONIAN_AUG: 0,
    ScaleType.DORIAN_SHARP4: -2,
    ScaleType.PHRYGIAN_DOMINANT: -4,
    ScaleType.LYDIAN_SHARP2: 1,
    ScaleType.SUPER_LOCRIAN_BB7: -5,
    
    # Melodic minor modes
    ScaleType.MELODIC_MINOR: -3,
    ScaleType.MELODIC_MINOR_CLASSICAL: -3,
    ScaleType.DORIAN_FLAT2: -2,
    ScaleType.LYDIAN_AUGMENTED: 1,
    ScaleType.LYDIAN_DOMINANT: 1,
    ScaleType.MIXOLYDIAN_FLAT6: -1,
    ScaleType.LOCRIAN_NAT2: -5,
    ScaleType.ALTERED: -5,
    
    # Harmonic major modes
    ScaleType.HARMONIC_MAJOR: 0,
    ScaleType.DORIAN_FLAT5: -2,
    ScaleType.PHRYGIAN_FLAT4: -4,
    ScaleType.LYDIAN_FLAT3: 1,
    ScaleType.MIXOLYDIAN_FLAT2: -1,
    ScaleType.LYDIAN_AUG_SHARP2: 1,
    ScaleType.LOCRIAN_DOUBLE_FLAT7: -5,
    
    # Bebop scales (use parent scale key signature)
    ScaleType.BEBOP_DOMINANT: -1,  # Based on mixolydian
    ScaleType.BEBOP_MAJOR: 0,      # Based on major
    ScaleType.BEBOP_DORIAN: -2,    # Based on dorian
    
    # Symmetric scales - no standard key signature, use parallel major
    # (whole_tone, diminished_hw, diminished_wh, chromatic - use default 0)
}


def _get_effective_key_fifths(key: MusicalKey, scale_type: ScaleType) -> int:
    """Get the effective key signature fifths for a scale in a key.
    
    Adjusts the key signature based on the mode. For example:
    - A Mixolydian uses D major key signature (2 sharps, not 3)
    - A Dorian uses G major key signature (1 sharp, not 3)
    
    Args:
        key: The musical key (root note)
        scale_type: The scale type (mode)
        
    Returns:
        Effective key signature in fifths (-7 to +7)
    """
    base_fifths = KEY_TO_FIFTHS.get(key, 0)
    offset = SCALE_FIFTHS_OFFSET.get(scale_type, 0)
    
    # Apply offset and clamp to valid range
    effective = base_fifths + offset
    return max(-7, min(7, effective))


def _parse_note(note: str) -> Tuple[str, str]:
    """Parse a note into letter and accidental.
    
    Args:
        note: Note name like "C", "F#", "Bb", "F##", "Bbb"
        
    Returns:
        Tuple of (letter, accidental) e.g., ("F", "##")
    """
    letter = note[0].upper()
    accidental = note[1:] if len(note) > 1 else ""
    return letter, accidental


def _note_to_semitone(note: str) -> int:
    """Convert a note name to semitone value (0-11).
    
    Args:
        note: Note name like "C", "F#", "Bb"
        
    Returns:
        Semitone value 0-11
    """
    letter, accidental = _parse_note(note)
    base = LETTER_SEMITONES[letter]
    modifier = ACCIDENTAL_SEMITONES.get(accidental, 0)
    return (base + modifier) % 12


def _transpose_note_for_key(note: str, key_root: str) -> str:
    """Transpose a note from key of C to another key, preserving letter relationships.
    
    DEPRECATED: Use _get_scale_degree_alteration_in_c and get_spelling_from_map instead.
    Keeping for backwards compatibility but the KEY_ALTERATION_MAP approach is preferred.
    
    When transposing to a new key, we keep the same letter name for each scale
    degree and adjust the accidental. For example:
    - C Lydian Dominant has F# as the 4th degree
    - In C# Lydian Dominant, the 4th should still be F-something
    - F# + 1 semitone = F##
    
    Args:
        note: Source note in key of C (e.g., "F#" for Lydian's #4)
        key_root: Target key root (e.g., "C#", "D", "Bb")
        
    Returns:
        Transposed note with correct spelling
    """
    # Parse the source note
    src_letter, src_accidental = _parse_note(note)
    src_semitone = _note_to_semitone(note)
    
    # Get the transposition interval from the key root
    transposition = _note_to_semitone(key_root)
    
    # Calculate target semitone
    target_semitone = (src_semitone + transposition) % 12
    
    # Keep the same letter name, adjust the accidental
    target_letter = src_letter
    target_natural_semitone = LETTER_SEMITONES[target_letter]
    
    # How much do we need to adjust from the natural note?
    needed_adjustment = (target_semitone - target_natural_semitone) % 12
    
    # Convert adjustment to accidental
    # Handle common cases cleanly
    if needed_adjustment == 0:
        target_accidental = ""
    elif needed_adjustment == 1:
        target_accidental = "#"
    elif needed_adjustment == 2:
        target_accidental = "##"
    elif needed_adjustment == 11:
        target_accidental = "b"
    elif needed_adjustment == 10:
        target_accidental = "bb"
    elif needed_adjustment == 3:
        # Could be ### or just move to different enharmonic - use x# (triple sharp rare)
        target_accidental = "###"
    elif needed_adjustment == 9:
        target_accidental = "bbb"
    else:
        # Very unusual intervals
        if needed_adjustment <= 6:
            target_accidental = "#" * needed_adjustment
        else:
            target_accidental = "b" * (12 - needed_adjustment)
    
    return target_letter + target_accidental


def _get_scale_degree_and_alteration_in_c(note: str) -> Tuple[int, int]:
    """Get the scale degree and alteration for a note in C major context.
    
    Uses the C spelling to determine which degree (0-6) and what alteration.
    For example:
    - "C" -> (0, 0) - degree 1, no alteration
    - "F#" -> (3, +1) - degree 4, raised
    - "Bb" -> (6, -1) - degree 7, lowered
    - "F##" -> (3, +2) - degree 4, double-raised
    
    Args:
        note: Note name in C (e.g., "C", "F#", "Bb", "F##")
        
    Returns:
        Tuple of (degree 0-6, alteration -2 to +2)
    """
    letter, accidental = _parse_note(note)
    
    # Map letter to scale degree
    letter_to_degree = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}
    degree = letter_to_degree[letter]
    
    # In C major, the diatonic pitches are: C=0, D=2, E=4, F=5, G=7, A=9, B=11
    # Alteration is difference between actual semitone and diatonic semitone
    actual_semitone = _note_to_semitone(note)
    diatonic_semitone = MAJOR_SCALE_SEMITONES[degree]
    
    # Calculate alteration (-2 to +2)
    alteration = (actual_semitone - diatonic_semitone)
    # Handle wraparound for edge cases
    if alteration > 6:
        alteration -= 12
    elif alteration < -6:
        alteration += 12
    
    return degree, alteration


def _get_scale_spellings_in_key(
    scale_type: ScaleType, 
    key: MusicalKey
) -> Tuple[str, ...]:
    """Get the note spellings for a scale in a specific key using KEY_ALTERATION_MAP.
    
    Uses the verified KEY_ALTERATION_MAP lookup to ensure correct enharmonic
    spellings. This is the same system used by the composer UI.
    
    Args:
        scale_type: The scale type
        key: The target key
        
    Returns:
        Tuple of note names for one octave of the scale
    """
    if scale_type not in SCALE_SPELLINGS_IN_C:
        return ()
    
    spellings_in_c = SCALE_SPELLINGS_IN_C[scale_type]
    
    if key == MusicalKey.C:
        return spellings_in_c
    
    # Get key_fifths for the target key
    key_fifths = KEY_TO_FIFTHS.get(key, 0)
    
    # Check if key_fifths is in the map (ranges -7 to +7)
    if key_fifths not in KEY_ALTERATION_MAP:
        # Fallback to old method for unsupported keys
        key_root = KEY_ROOTS.get(key, "C")
        return tuple(_transpose_note_for_key(note, key_root) for note in spellings_in_c)
    
    result = []
    for note in spellings_in_c:
        # Get degree and alteration from the C spelling
        degree, alteration = _get_scale_degree_and_alteration_in_c(note)
        
        # Look up the spelling in the target key
        try:
            spelling = get_spelling_from_map(key_fifths, degree, alteration)
            # Convert SpellingEntry to string
            acc_str = ""
            if spelling.accidental == Accidental.DOUBLE_FLAT:
                acc_str = "bb"
            elif spelling.accidental == Accidental.FLAT:
                acc_str = "b"
            elif spelling.accidental == Accidental.NATURAL:
                acc_str = ""  # Natural is implicit in simple naming
            elif spelling.accidental == Accidental.SHARP:
                acc_str = "#"
            elif spelling.accidental == Accidental.DOUBLE_SHARP:
                acc_str = "##"
            result.append(spelling.letter + acc_str)
        except KeyError:
            # Fallback if lookup fails
            key_root = KEY_ROOTS.get(key, "C")
            result.append(_transpose_note_for_key(note, key_root))
    
    return tuple(result)


def _accidental_to_capability(accidental: Optional[Accidental]) -> Set[str]:
    """Convert an Accidental enum to the required capability names.
    
    Args:
        accidental: The Accidental enum value (or None)
        
    Returns:
        Set of capability names required for this accidental
    """
    if accidental is None:
        return set()
    elif accidental == Accidental.FLAT:
        return {"accidental_flat_symbol"}
    elif accidental == Accidental.SHARP:
        return {"accidental_sharp_symbol"}
    elif accidental == Accidental.DOUBLE_FLAT:
        return {"accidental_flat_symbol", "double_flat_symbol"}
    elif accidental == Accidental.DOUBLE_SHARP:
        return {"accidental_sharp_symbol", "double_sharp_symbol"}
    elif accidental == Accidental.NATURAL:
        return {"accidental_natural_symbol"}
    return set()


def _analyze_accidentals(notes: Tuple[str, ...]) -> Set[str]:
    """Analyze what accidental types are present in a set of notes.
    
    Args:
        notes: Tuple of note names
        
    Returns:
        Set of accidental capability names required
    """
    capabilities: Set[str] = set()
    
    for note in notes:
        _, accidental = _parse_note(note)
        
        if accidental == "#":
            capabilities.add("accidental_sharp_symbol")
        elif accidental == "##":
            capabilities.add("accidental_sharp_symbol")
            capabilities.add("double_sharp_symbol")
        elif accidental == "b":
            capabilities.add("accidental_flat_symbol")
        elif accidental == "bb":
            capabilities.add("accidental_flat_symbol")
            capabilities.add("double_flat_symbol")
        # Natural notes with no accidental might still need natural signs
        # when they differ from the key signature
    
    return capabilities


def _get_key_signature_notes(key: MusicalKey) -> Dict[str, str]:
    """Get the accidentals for each letter in a key signature.
    
    Args:
        key: The musical key
        
    Returns:
        Dict mapping letter names to their accidental in this key signature
    """
    # Key signatures based on circle of fifths
    # Maps key to dict of {letter: accidental}
    key_signatures: Dict[MusicalKey, Dict[str, str]] = {
        MusicalKey.C: {},
        MusicalKey.G: {"F": "#"},
        MusicalKey.D: {"F": "#", "C": "#"},
        MusicalKey.A: {"F": "#", "C": "#", "G": "#"},
        MusicalKey.E: {"F": "#", "C": "#", "G": "#", "D": "#"},
        MusicalKey.B: {"F": "#", "C": "#", "G": "#", "D": "#", "A": "#"},
        MusicalKey.F_SHARP: {"F": "#", "C": "#", "G": "#", "D": "#", "A": "#", "E": "#"},
        MusicalKey.C_SHARP: {"F": "#", "C": "#", "G": "#", "D": "#", "A": "#", "E": "#", "B": "#"},
        MusicalKey.F: {"B": "b"},
        MusicalKey.B_FLAT: {"B": "b", "E": "b"},
        MusicalKey.E_FLAT: {"B": "b", "E": "b", "A": "b"},
        MusicalKey.A_FLAT: {"B": "b", "E": "b", "A": "b", "D": "b"},
        MusicalKey.D_FLAT: {"B": "b", "E": "b", "A": "b", "D": "b", "G": "b"},
        MusicalKey.G_FLAT: {"B": "b", "E": "b", "A": "b", "D": "b", "G": "b", "C": "b"},
        # Enharmonic sharp keys
        MusicalKey.D_SHARP: {"F": "#", "C": "#", "G": "#", "D": "#", "A": "#", "E": "#", "B": "#"},  # Same as Eb
        MusicalKey.G_SHARP: {"F": "#", "C": "#", "G": "#", "D": "#", "A": "#", "E": "#", "B": "#"},  # 8 sharps theoretical
        MusicalKey.A_SHARP: {"F": "#", "C": "#", "G": "#", "D": "#", "A": "#", "E": "#", "B": "#"},  # 10 sharps theoretical
    }
    return key_signatures.get(key, {})


def _needs_natural(note: str, key: MusicalKey) -> bool:
    """Check if a note needs a natural sign given the key signature.
    
    A natural is needed when the note's letter would normally have an
    accidental in the key signature, but the note is written without it.
    
    Args:
        note: Note name (e.g., "B" or "F")
        key: The musical key
        
    Returns:
        True if a natural symbol is needed
    """
    letter, accidental = _parse_note(note)
    key_sig = _get_key_signature_notes(key)
    
    # If this letter has an accidental in the key signature
    if letter in key_sig:
        key_accidental = key_sig[letter]
        # And the note doesn't have that accidental (or any accidental)
        if accidental == "" or accidental != key_accidental:
            # We need a natural (or other accidental) to cancel the key signature
            if accidental == "":
                return True
    
    return False


def get_scale_key_required_accidentals(
    scale_type: ScaleType, 
    key: MusicalKey
) -> FrozenSet[str]:
    """Get all accidental capabilities required for a scale in a specific key.
    
    Uses the MODE-ADJUSTED key signature to match how the notation is actually
    rendered. For example, A Mixolydian uses D major key signature (2 sharps),
    not A major key signature (3 sharps), so G natural doesn't need a natural sign.
    
    Detects:
    - Sharp symbols
    - Flat symbols  
    - Double sharp symbols
    - Double flat symbols
    - Natural symbols (when notes differ from the effective key signature)
    
    Args:
        scale_type: The scale type
        key: The target key
        
    Returns:
        Set of required accidental capability names
    """
    # Get the scale spellings in this key
    spellings = _get_scale_spellings_in_key(scale_type, key)
    
    if not spellings:
        return frozenset()
    
    # Get the EFFECTIVE key signature (accounting for mode)
    effective_fifths = _get_effective_key_fifths(key, scale_type)
    
    # Build what accidentals each letter has in the effective key signature
    # Positive fifths = sharps on F, C, G, D, A, E, B (in that order)
    # Negative fifths = flats on B, E, A, D, G, C, F (in that order) 
    effective_key_sig: Dict[str, str] = {}
    
    if effective_fifths > 0:
        sharp_order = ["F", "C", "G", "D", "A", "E", "B"]
        for i in range(min(effective_fifths, 7)):
            effective_key_sig[sharp_order[i]] = "#"
    elif effective_fifths < 0:
        flat_order = ["B", "E", "A", "D", "G", "C", "F"]
        for i in range(min(-effective_fifths, 7)):
            effective_key_sig[flat_order[i]] = "b"
    
    capabilities: Set[str] = set()
    
    # Automatically include sharp/flat based on key signature type
    # Sharp keys require knowing sharp symbols, flat keys require flat symbols
    if effective_fifths > 0:
        capabilities.add("accidental_sharp_symbol")
    elif effective_fifths < 0:
        capabilities.add("accidental_flat_symbol")
    
    # Detect same-letter collisions (e.g., Fb and F in Db Blues Major)
    # When two notes share a letter but have different accidentals,
    # cancellation accidentals are needed when they appear in sequence
    letter_accidentals: Dict[str, Set[str]] = {}
    for note in spellings:
        letter, accidental = _parse_note(note)
        if letter not in letter_accidentals:
            letter_accidentals[letter] = set()
        letter_accidentals[letter].add(accidental)
    
    # For letters with multiple accidentals, add cancellation capabilities
    for letter, accidentals in letter_accidentals.items():
        if len(accidentals) > 1:
            # Multiple accidentals on same letter - need cancellation
            for acc in accidentals:
                if acc == "":
                    # Natural cancels previous sharp/flat
                    capabilities.add("accidental_natural_symbol")
                elif acc == "#":
                    capabilities.add("accidental_sharp_symbol")
                elif acc == "##":
                    capabilities.add("accidental_sharp_symbol")
                    capabilities.add("double_sharp_symbol")
                elif acc == "b":
                    capabilities.add("accidental_flat_symbol")
                elif acc == "bb":
                    capabilities.add("accidental_flat_symbol")
                    capabilities.add("double_flat_symbol")
    
    for note in spellings:
        letter, accidental = _parse_note(note)
        key_accidental = effective_key_sig.get(letter, "")
        
        if accidental == key_accidental:
            # Note matches key signature - no written accidental needed
            continue
        
        # Accidental differs from key signature - need to write something
        if accidental == "":
            # Natural note but key sig has sharp/flat - need natural symbol
            if key_accidental:
                capabilities.add("accidental_natural_symbol")
        elif accidental == "#":
            capabilities.add("accidental_sharp_symbol")
        elif accidental == "##":
            capabilities.add("accidental_sharp_symbol")
            capabilities.add("double_sharp_symbol")
        elif accidental == "b":
            capabilities.add("accidental_flat_symbol")
        elif accidental == "bb":
            capabilities.add("accidental_flat_symbol")
            capabilities.add("double_flat_symbol")
    
    return frozenset(capabilities)


# Compound intervals (9th and beyond) - soft-gated per design
COMPOUND_INTERVAL_CAPABILITY = "interval_play_compound_9_plus"


# =============================================================================
# Interval to Capability Mapping
# =============================================================================
# Maps semitone intervals to capability names

SEMITONE_TO_CAPABILITY: Dict[int, str] = {
    1: "interval_play_minor_2",
    2: "interval_play_major_2",
    3: "interval_play_minor_3",
    4: "interval_play_major_3",
    5: "interval_play_perfect_4",
    6: "interval_play_augmented_4",  # Also tritone/diminished_5
    7: "interval_play_perfect_5",
    8: "interval_play_minor_6",
    9: "interval_play_major_6",
    10: "interval_play_minor_7",
    11: "interval_play_major_7",
    12: "interval_play_perfect_8",  # Octave
}


# =============================================================================
# Rhythm to Capability Mapping
# =============================================================================

RHYTHM_TO_CAPABILITIES: Dict[RhythmType, FrozenSet[str]] = {
    RhythmType.WHOLE_NOTES: frozenset({"rhythm_whole_notes"}),
    RhythmType.HALF_NOTES: frozenset({"rhythm_half_notes"}),
    RhythmType.QUARTER_NOTES: frozenset({"rhythm_quarter_notes"}),
    RhythmType.EIGHTH_NOTES: frozenset({"rhythm_eighth_notes"}),
    RhythmType.SIXTEENTH_NOTES: frozenset({"rhythm_sixteenth_notes"}),
    RhythmType.EIGHTH_TRIPLETS: frozenset({"rhythm_eighth_notes", "rhythm_triplets_eighth"}),
    RhythmType.SWING_EIGHTHS: frozenset({"rhythm_eighth_notes"}),
    RhythmType.SCOTCH_SNAP: frozenset({"rhythm_eighth_notes", "rhythm_sixteenth_notes"}),
    RhythmType.DOTTED_QUARTER_EIGHTH: frozenset({"rhythm_eighth_notes", "rhythm_dotted_quarter"}),
    RhythmType.DOTTED_EIGHTH_SIXTEENTH: frozenset({"rhythm_eighth_notes", "rhythm_sixteenth_notes", "rhythm_dotted_eighth"}),
    RhythmType.SIXTEENTH_EIGHTH_SIXTEENTH: frozenset({"rhythm_eighth_notes", "rhythm_sixteenth_notes", "rhythm_syncopation"}),
    RhythmType.EIGHTH_SIXTEENTH_SIXTEENTH: frozenset({"rhythm_eighth_notes", "rhythm_sixteenth_notes"}),
    RhythmType.SIXTEENTH_SIXTEENTH_EIGHTH: frozenset({"rhythm_eighth_notes", "rhythm_sixteenth_notes"}),
    RhythmType.SYNCOPATED: frozenset({"rhythm_quarter_notes", "rhythm_eighth_notes", "rhythm_syncopation"}),
}


# =============================================================================
# Key to Capability Mapping
# =============================================================================

# Keys requiring sharp symbol
SHARP_KEYS: FrozenSet[MusicalKey] = frozenset({
    MusicalKey.G,
    MusicalKey.D,
    MusicalKey.A,
    MusicalKey.E,
    MusicalKey.B,
    MusicalKey.F_SHARP,
    MusicalKey.C_SHARP,
    MusicalKey.D_SHARP,
    MusicalKey.G_SHARP,
    MusicalKey.A_SHARP,
})

# Keys requiring flat symbol
FLAT_KEYS: FrozenSet[MusicalKey] = frozenset({
    MusicalKey.F,
    MusicalKey.D_FLAT,
    MusicalKey.E_FLAT,
    MusicalKey.A_FLAT,
    MusicalKey.G_FLAT,
    MusicalKey.B_FLAT,
})

# C requires neither
NEUTRAL_KEYS: FrozenSet[MusicalKey] = frozenset({MusicalKey.C})


def get_key_required_capabilities(key: MusicalKey) -> FrozenSet[str]:
    """Get capability requirements for a key signature.
    
    Args:
        key: The target key.
        
    Returns:
        Set of required capability names (may be empty for C).
    """
    if key == MusicalKey.C:
        return frozenset()
    if key in SHARP_KEYS:
        return frozenset({"accidental_sharp_symbol"})
    if key in FLAT_KEYS:
        return frozenset({"accidental_flat_symbol"})
    return frozenset()


# =============================================================================
# Pattern Interval Computations
# =============================================================================
# Pre-compute which melodic intervals arise from each scale/arpeggio + pattern


def _compute_scale_cumulative(scale_intervals: Tuple[int, ...]) -> List[int]:
    """Convert step intervals to cumulative intervals from root.
    
    Example: [2, 2, 1] -> [0, 2, 4, 5]
    """
    cumulative = [0]
    for interval in scale_intervals:
        cumulative.append(cumulative[-1] + interval)
    return cumulative


def _compute_melodic_intervals_straight(scale_intervals: Tuple[int, ...]) -> Set[int]:
    """Compute melodic intervals for straight up/down patterns.
    
    For patterned exercises, the melodic intervals are just the step sizes.
    """
    return set(scale_intervals)


def _compute_melodic_intervals_in_nths(
    scale_intervals: Tuple[int, ...], 
    n: int,
) -> Set[int]:
    """Compute melodic intervals for 'in Nths' patterns (3rds, 4ths, etc.).
    
    Pattern structure: For 'in 4ths', play pairs (1,4), (2,5), (3,6), ...
    The output sequence is: 1-4-2-5-3-6-4-7-...
    
    The pattern extends above and below the octave, creating wraparound intervals.
    
    Melodic intervals include:
    1. Forward skip: from degree i to degree (i + n - 1) = nth interval
    2. Step-back: from degree (i + n - 1) back to degree (i + 1) = (n-2)th interval
    
    Args:
        scale_intervals: Step intervals of the scale.
        n: The interval degree (3 for 3rds, 4 for 4ths, etc.)
        
    Returns:
        Set of melodic intervals in semitones.
    """
    cumulative = _compute_scale_cumulative(scale_intervals)
    num_steps = len(scale_intervals)  # Number of step intervals (7 for diatonic)
    octave = 12
    intervals: Set[int] = set()
    
    skip = n - 1  # Number of scale degrees to skip (e.g., 2 for 3rds)
    step_back = n - 2  # Number of degrees in the step-back (e.g., 1 for 3rds)
    
    # Forward skip intervals (the "nth" intervals) - with wraparound
    for i in range(num_steps):
        target = i + skip
        if target < num_steps:
            interval = cumulative[target] - cumulative[i]
        else:
            target_in_cycle = target % num_steps
            interval = (cumulative[target_in_cycle] + octave) - cumulative[i]
        intervals.add(interval)
    
    # Step-back intervals (from end of one pair to start of next) - with wraparound
    # Going from degree (i + skip) back to degree (i + 1) spans (step_back) degrees
    if step_back > 0:
        for i in range(num_steps):
            # Step-back goes from position (i + skip) to position (i + 1)
            from_pos = (i + skip) % num_steps
            to_pos = (i + 1) % num_steps
            
            # Compute interval (may be negative if going down)
            if from_pos >= to_pos:
                interval = cumulative[from_pos] - cumulative[to_pos]
            else:
                # Wraps around: from_pos is in lower octave relative to to_pos
                interval = (cumulative[from_pos] + octave) - cumulative[to_pos]
            intervals.add(interval)
    else:
        # For "in 3rds", step_back = 1, so it's just single step intervals
        intervals.update(scale_intervals)
    
    return intervals


def _compute_melodic_intervals_groups(
    scale_intervals: Tuple[int, ...],
    group_size: int,
) -> Set[int]:
    """Compute melodic intervals for groups pattern.
    
    Pattern structure: For groups of 5, play overlapping groups:
    1-2-3-4-5, 2-3-4-5-6, 3-4-5-6-7, ...
    
    Output sequence: 1-2-3-4-5-2-3-4-5-6-3-4-5-6-7-...
    
    The pattern extends above and below the octave (by group_size - 2 notes),
    creating jump intervals that span across the octave boundary.
    
    Melodic intervals include:
    1. Step intervals (consecutive scale degrees within groups)
    2. Jump-back intervals (from last note of group n to first note of group n+1)
       The jump spans (group_size - 2) degrees
    3. Wraparound intervals that occur in the extended portions
    
    Args:
        scale_intervals: Step intervals of the scale.
        group_size: Number of notes in each group (e.g., 5 for groups of 5)
        
    Returns:
        Set of melodic intervals in semitones.
    """
    cumulative = _compute_scale_cumulative(scale_intervals)
    num_steps = len(scale_intervals)  # Number of step intervals (7 for diatonic)
    octave = 12  # Semitones in an octave
    intervals: Set[int] = set()
    
    # Step intervals within groups
    intervals.update(scale_intervals)
    
    # Jump-back intervals between groups
    # The jump spans (group_size - 2) degrees
    # We need to compute all possible spans INCLUDING wraparound positions
    jump_span = group_size - 2
    
    if jump_span > 0:
        # Compute intervals for all starting positions in the cyclic scale
        # The scale is cyclic with period = num_steps, but cumulative values
        # increase by 12 each octave
        for i in range(num_steps):
            # Target position may wrap around
            target = i + jump_span
            if target < num_steps:
                # Within same octave
                jump_interval = cumulative[target] - cumulative[i]
            else:
                # Wraps to next octave
                target_in_cycle = target % num_steps
                jump_interval = (cumulative[target_in_cycle] + octave) - cumulative[i]
            intervals.add(jump_interval)
    
    return intervals


def _compute_melodic_intervals_pyramid(scale_intervals: Tuple[int, ...]) -> Set[int]:
    """Compute melodic intervals for pyramid patterns.
    
    Pyramid patterns use stepwise motion going up and back down.
    """
    return set(scale_intervals)


def _compute_melodic_intervals_diatonic_triads(scale_intervals: Tuple[int, ...]) -> Set[int]:
    """Compute melodic intervals for diatonic triads pattern.
    
    Pattern: Plays triads on each scale degree sequentially.
    Output: root1-3rd1-5th1-root2-3rd2-5th2-...
    
    Melodic intervals:
    1. Within triads: root→3rd (3rd), 3rd→5th (3rd)
    2. Between triads: 5th of triad n → root of triad n+1 (spans 3 degrees backward)
    """
    cumulative = _compute_scale_cumulative(scale_intervals)
    num_steps = len(scale_intervals)  # 7 for diatonic
    octave = 12
    intervals: Set[int] = set()
    
    # Within-triad intervals: root→3rd (2 degrees) and 3rd→5th (2 degrees)
    for i in range(num_steps):
        # Root to 3rd (spans 2 degrees)
        target = (i + 2) % num_steps
        if target > i:
            interval = cumulative[target] - cumulative[i]
        else:
            interval = (cumulative[target] + octave) - cumulative[i]
        intervals.add(interval)
        
        # 3rd to 5th (spans 2 degrees from the 3rd position)
        # This is the same as another 2-degree span
        # Already covered above
    
    # Between-triad intervals: 5th of triad i → root of triad i+1
    # 5th of triad i is at position (i + 4), next root is at position (i + 1)
    # This spans 3 degrees backward (equivalent to 4 degrees forward in cyclic terms)
    for i in range(num_steps):
        fifth_pos = (i + 4) % num_steps
        next_root_pos = (i + 1) % num_steps
        
        # Interval from 5th to next root (going backward)
        if fifth_pos >= next_root_pos:
            interval = cumulative[fifth_pos] - cumulative[next_root_pos]
        else:
            interval = (cumulative[fifth_pos] + octave) - cumulative[next_root_pos]
        intervals.add(interval)
    
    return intervals


def _compute_melodic_intervals_diatonic_7ths(scale_intervals: Tuple[int, ...]) -> Set[int]:
    """Compute melodic intervals for diatonic 7th chords pattern.
    
    Pattern: Plays 7th chords on each scale degree sequentially.
    Output: root1-3rd1-5th1-7th1-root2-3rd2-5th2-7th2-...
    
    Melodic intervals:
    1. Within chords: root→3rd (2 deg), 3rd→5th (2 deg), 5th→7th (2 deg)
    2. Between chords: 7th of chord n → root of chord n+1 (spans 5 degrees backward)
    """
    cumulative = _compute_scale_cumulative(scale_intervals)
    num_steps = len(scale_intervals)  # 7 for diatonic
    octave = 12
    intervals: Set[int] = set()
    
    # Within-chord intervals: all spans of 2 degrees (3rds within the chord)
    for i in range(num_steps):
        target = (i + 2) % num_steps
        if target > i:
            interval = cumulative[target] - cumulative[i]
        else:
            interval = (cumulative[target] + octave) - cumulative[i]
        intervals.add(interval)
    
    # Between-chord intervals: 7th of chord i → root of chord i+1
    # 7th of chord i is at position (i + 6), next root is at position (i + 1)
    # This spans 5 degrees backward
    for i in range(num_steps):
        seventh_pos = (i + 6) % num_steps
        next_root_pos = (i + 1) % num_steps
        
        if seventh_pos >= next_root_pos:
            interval = cumulative[seventh_pos] - cumulative[next_root_pos]
        else:
            interval = (cumulative[seventh_pos] + octave) - cumulative[next_root_pos]
        intervals.add(interval)
    
    return intervals


def _compute_melodic_intervals_broken_chords(scale_intervals: Tuple[int, ...]) -> Set[int]:
    """Compute melodic intervals for broken chords pattern (1-5-3 pattern).
    
    Pattern: For each degree, plays root-5th-3rd-next_3rd pattern.
    Output: 1-5-3-next_degree_3rd-...
    
    Actual melodic intervals observed: step intervals + 3rds + 5ths + transitions
    """
    cumulative = _compute_scale_cumulative(scale_intervals)
    num_steps = len(scale_intervals)
    octave = 12
    intervals: Set[int] = set()
    
    # Include step intervals (appear in transitions)
    intervals.update(scale_intervals)
    
    # Within-chord intervals
    for i in range(num_steps):
        # Root to 5th (4 degrees span)
        fifth_pos = (i + 4) % num_steps
        if fifth_pos > i:
            intervals.add(cumulative[fifth_pos] - cumulative[i])
        else:
            intervals.add((cumulative[fifth_pos] + octave) - cumulative[i])
        
        # 5th to 3rd (2 degrees backward = 5 degrees forward in cycle)
        third_pos = (i + 2) % num_steps
        if fifth_pos >= third_pos:
            intervals.add(cumulative[fifth_pos] - cumulative[third_pos])
        else:
            intervals.add((cumulative[fifth_pos] + octave) - cumulative[third_pos])
        
        # 3rd to next pattern start or transition
        # This can be various intervals depending on the pattern
    
    return intervals


def _compute_arpeggio_melodic_intervals_straight(
    chord_intervals: Tuple[int, ...],
) -> Set[int]:
    """Compute melodic intervals for straight arpeggio patterns.
    
    Args:
        chord_intervals: Cumulative intervals from root (e.g., (0, 4, 7) for major triad)
    """
    intervals: Set[int] = set()
    
    # Melodic intervals between consecutive chord tones
    for i in range(len(chord_intervals) - 1):
        interval = chord_intervals[i + 1] - chord_intervals[i]
        intervals.add(interval)
    
    return intervals


def _compute_arpeggio_melodic_intervals_weaving(
    chord_intervals: Tuple[int, ...],
) -> Set[int]:
    """Compute melodic intervals for weaving arpeggio patterns.
    
    Weaving pattern: 1-2-3-2-3-4-3-4-5... (overlapping groups)
    """
    intervals: Set[int] = set()
    
    for i in range(len(chord_intervals) - 1):
        # Forward interval
        intervals.add(chord_intervals[i + 1] - chord_intervals[i])
    
    return intervals


def _compute_arpeggio_melodic_intervals_broken(
    chord_intervals: Tuple[int, ...],
) -> Set[int]:
    """Compute melodic intervals for broken (skip 1) arpeggio patterns.
    
    Skip 1 pattern: 1-3, 2-4, 3-5, etc.
    """
    intervals: Set[int] = set()
    
    # Intervals skipping one chord tone
    for i in range(len(chord_intervals) - 2):
        intervals.add(chord_intervals[i + 2] - chord_intervals[i])
    
    # Also includes stepwise intervals between pairs
    for i in range(len(chord_intervals) - 1):
        intervals.add(chord_intervals[i + 1] - chord_intervals[i])
    
    return intervals


def _compute_arpeggio_melodic_intervals_spread(
    chord_intervals: Tuple[int, ...],
) -> Set[int]:
    """Compute melodic intervals for spread voicing arpeggio patterns.
    
    Spread voicings like 1-7-3-5 with wider intervals.
    """
    intervals: Set[int] = set()
    
    if len(chord_intervals) >= 4:
        # 1 to 7 (drop octave, so it's actually 7 - 12 from root)
        # For now, include all possible chord tone combinations
        for i in range(len(chord_intervals)):
            for j in range(i + 1, len(chord_intervals)):
                intervals.add(chord_intervals[j] - chord_intervals[i])
    else:
        # Fallback to straight
        intervals = _compute_arpeggio_melodic_intervals_straight(chord_intervals)
    
    return intervals


def _compute_arpeggio_melodic_intervals_approach(
    chord_intervals: Tuple[int, ...],
) -> Set[int]:
    """Compute melodic intervals for approach note patterns.
    
    Chromatic approach: half step below, then chord tone.
    Includes m2 intervals.
    """
    intervals = _compute_arpeggio_melodic_intervals_straight(chord_intervals)
    intervals.add(1)  # Half step approach
    return intervals


def _compute_arpeggio_melodic_intervals_enclosure(
    chord_intervals: Tuple[int, ...],
) -> Set[int]:
    """Compute melodic intervals for enclosure patterns.
    
    Enclosure: half step above, half step below, then chord tone.
    """
    intervals = _compute_arpeggio_melodic_intervals_straight(chord_intervals)
    intervals.add(1)  # Half step enclosure movements
    intervals.add(2)  # Whole step (above to below enclosure)
    return intervals


def _compute_arpeggio_melodic_intervals_inversion(
    chord_intervals: Tuple[int, ...],
    inversion: int,
) -> Set[int]:
    """Compute melodic intervals for inverted arpeggios.
    
    Args:
        chord_intervals: Base chord intervals.
        inversion: 0=root, 1=1st inv, 2=2nd inv, 3=3rd inv
    """
    if inversion >= len(chord_intervals):
        inversion = 0
    
    # Rotate the chord intervals
    rotated = list(chord_intervals[inversion:]) + [
        i + 12 for i in chord_intervals[:inversion]
    ]
    # Normalize to start from 0
    base = rotated[0]
    normalized = tuple(i - base for i in rotated)
    
    return _compute_arpeggio_melodic_intervals_straight(normalized)


# =============================================================================
# Pre-computed Lookup Tables
# =============================================================================


@lru_cache(maxsize=1)
def _get_scale_pattern_intervals() -> Dict[Tuple[ScaleType, ScalePattern], FrozenSet[str]]:
    """Pre-compute all scale × pattern → required interval capabilities.
    
    Returns:
        Dict mapping (scale_type, pattern) to set of required capability names.
    """
    result: Dict[Tuple[ScaleType, ScalePattern], FrozenSet[str]] = {}
    
    for scale_type in ScaleType:
        if scale_type not in SCALE_INTERVALS:
            continue
        scale_intervals = SCALE_INTERVALS[scale_type]
        
        for pattern in ScalePattern:
            # Compute melodic intervals for this combination
            if pattern in {
                ScalePattern.STRAIGHT_UP,
                ScalePattern.STRAIGHT_DOWN,
                ScalePattern.STRAIGHT_UP_DOWN,
                ScalePattern.STRAIGHT_DOWN_UP,
            }:
                melodic_intervals = _compute_melodic_intervals_straight(scale_intervals)
            elif pattern == ScalePattern.PYRAMID_ASCEND or pattern == ScalePattern.PYRAMID_DESCEND:
                melodic_intervals = _compute_melodic_intervals_pyramid(scale_intervals)
            elif pattern == ScalePattern.IN_3RDS:
                melodic_intervals = _compute_melodic_intervals_in_nths(scale_intervals, 3)
            elif pattern == ScalePattern.IN_4THS:
                melodic_intervals = _compute_melodic_intervals_in_nths(scale_intervals, 4)
            elif pattern == ScalePattern.IN_5THS:
                melodic_intervals = _compute_melodic_intervals_in_nths(scale_intervals, 5)
            elif pattern == ScalePattern.IN_6THS:
                melodic_intervals = _compute_melodic_intervals_in_nths(scale_intervals, 6)
            elif pattern == ScalePattern.IN_7THS:
                melodic_intervals = _compute_melodic_intervals_in_nths(scale_intervals, 7)
            elif pattern == ScalePattern.IN_8THS:
                melodic_intervals = _compute_melodic_intervals_in_nths(scale_intervals, 8)
            elif pattern == ScalePattern.IN_OCTAVES:
                melodic_intervals = _compute_melodic_intervals_in_nths(scale_intervals, len(scale_intervals) + 1)
            elif pattern in {
                ScalePattern.IN_9THS, ScalePattern.IN_10THS, ScalePattern.IN_11THS,
                ScalePattern.IN_12THS, ScalePattern.IN_13THS,
            }:
                n = {
                    ScalePattern.IN_9THS: 9,
                    ScalePattern.IN_10THS: 10,
                    ScalePattern.IN_11THS: 11,
                    ScalePattern.IN_12THS: 12,
                    ScalePattern.IN_13THS: 13,
                }[pattern]
                melodic_intervals = _compute_melodic_intervals_in_nths(scale_intervals, n)
            elif pattern in {
                ScalePattern.GROUPS_OF_3, ScalePattern.GROUPS_OF_4,
                ScalePattern.GROUPS_OF_5, ScalePattern.GROUPS_OF_6,
                ScalePattern.GROUPS_OF_7, ScalePattern.GROUPS_OF_8,
                ScalePattern.GROUPS_OF_9, ScalePattern.GROUPS_OF_10,
                ScalePattern.GROUPS_OF_11, ScalePattern.GROUPS_OF_12,
            }:
                group_size = int(pattern.value.split("_")[-1])
                melodic_intervals = _compute_melodic_intervals_groups(scale_intervals, group_size)
            elif pattern == ScalePattern.BROKEN_THIRDS_NEIGHBOR:
                melodic_intervals = _compute_melodic_intervals_in_nths(scale_intervals, 3)
            elif pattern == ScalePattern.DIATONIC_TRIADS:
                melodic_intervals = _compute_melodic_intervals_diatonic_triads(scale_intervals)
            elif pattern == ScalePattern.DIATONIC_7THS:
                melodic_intervals = _compute_melodic_intervals_diatonic_7ths(scale_intervals)
            elif pattern == ScalePattern.BROKEN_CHORDS:
                melodic_intervals = _compute_melodic_intervals_broken_chords(scale_intervals)
            else:
                # Default fallback to straight
                melodic_intervals = _compute_melodic_intervals_straight(scale_intervals)
            
            # Map intervals to capability names
            capabilities: Set[str] = set()
            for semitones in melodic_intervals:
                if semitones == 0:
                    continue
                if semitones in SEMITONE_TO_CAPABILITY:
                    capabilities.add(SEMITONE_TO_CAPABILITY[semitones])
                elif semitones > 12:
                    capabilities.add(COMPOUND_INTERVAL_CAPABILITY)
            
            result[(scale_type, pattern)] = frozenset(capabilities)
    
    return result


@lru_cache(maxsize=1)
def _get_arpeggio_pattern_intervals() -> Dict[Tuple[ArpeggioType, ArpeggioPattern], FrozenSet[str]]:
    """Pre-compute all arpeggio × pattern → required interval capabilities.
    
    Returns:
        Dict mapping (arpeggio_type, pattern) to set of required capability names.
    """
    result: Dict[Tuple[ArpeggioType, ArpeggioPattern], FrozenSet[str]] = {}
    
    for arpeggio_type in ArpeggioType:
        if arpeggio_type not in ARPEGGIO_INTERVALS:
            continue
        chord_intervals = ARPEGGIO_INTERVALS[arpeggio_type]
        
        for pattern in ArpeggioPattern:
            # Compute melodic intervals for this combination
            if pattern in {
                ArpeggioPattern.STRAIGHT_UP,
                ArpeggioPattern.STRAIGHT_DOWN,
                ArpeggioPattern.STRAIGHT_UP_DOWN,
            }:
                melodic_intervals = _compute_arpeggio_melodic_intervals_straight(chord_intervals)
            elif pattern in {ArpeggioPattern.WEAVING_ASCEND, ArpeggioPattern.WEAVING_DESCEND}:
                melodic_intervals = _compute_arpeggio_melodic_intervals_weaving(chord_intervals)
            elif pattern == ArpeggioPattern.BROKEN_SKIP_1:
                melodic_intervals = _compute_arpeggio_melodic_intervals_broken(chord_intervals)
            elif pattern == ArpeggioPattern.INVERSION_ROOT:
                melodic_intervals = _compute_arpeggio_melodic_intervals_inversion(chord_intervals, 0)
            elif pattern == ArpeggioPattern.INVERSION_1ST:
                melodic_intervals = _compute_arpeggio_melodic_intervals_inversion(chord_intervals, 1)
            elif pattern == ArpeggioPattern.INVERSION_2ND:
                melodic_intervals = _compute_arpeggio_melodic_intervals_inversion(chord_intervals, 2)
            elif pattern == ArpeggioPattern.INVERSION_3RD:
                melodic_intervals = _compute_arpeggio_melodic_intervals_inversion(chord_intervals, 3)
            elif pattern == ArpeggioPattern.ROLLING_ALBERTI:
                melodic_intervals = _compute_arpeggio_melodic_intervals_straight(chord_intervals)
            elif pattern == ArpeggioPattern.SPREAD_VOICINGS:
                melodic_intervals = _compute_arpeggio_melodic_intervals_spread(chord_intervals)
            elif pattern == ArpeggioPattern.APPROACH_NOTES:
                melodic_intervals = _compute_arpeggio_melodic_intervals_approach(chord_intervals)
            elif pattern == ArpeggioPattern.ENCLOSURES:
                melodic_intervals = _compute_arpeggio_melodic_intervals_enclosure(chord_intervals)
            elif pattern in {
                ArpeggioPattern.DIATONIC_SEQUENCE,
                ArpeggioPattern.CIRCLE_4THS,
                ArpeggioPattern.CIRCLE_5THS,
            }:
                # These patterns move through chord progressions, include wider intervals
                melodic_intervals = _compute_arpeggio_melodic_intervals_straight(chord_intervals)
                melodic_intervals.add(5)  # P4 for circle progressions
                melodic_intervals.add(7)  # P5 for circle progressions
            else:
                melodic_intervals = _compute_arpeggio_melodic_intervals_straight(chord_intervals)
            
            # Map intervals to capability names
            capabilities: Set[str] = set()
            for semitones in melodic_intervals:
                if semitones == 0:
                    continue
                if semitones in SEMITONE_TO_CAPABILITY:
                    capabilities.add(SEMITONE_TO_CAPABILITY[semitones])
                elif semitones > 12:
                    capabilities.add(COMPOUND_INTERVAL_CAPABILITY)
            
            result[(arpeggio_type, pattern)] = frozenset(capabilities)
    
    return result


@lru_cache(maxsize=1)
def _get_learnable_in_context() -> FrozenSet[str]:
    """Load capabilities with requirement_type='learnable_in_context'.
    
    These capabilities are NOT gating factors - the system teaches them
    just-in-time when encountered.
    
    Returns:
        Set of capability names that are learnable in context.
    """
    resources_path = Path(__file__).parent.parent.parent / "resources" / "capabilities.json"
    
    try:
        with open(resources_path, "r") as f:
            data = json.load(f)
        
        learnable = {
            cap["name"]
            for cap in data.get("capabilities", [])
            if cap.get("requirement_type") == "learnable_in_context"
        }
        return frozenset(learnable)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to load capabilities.json: {e}")
        return frozenset()


# =============================================================================
# ValidPoolCalculator
# =============================================================================


class ValidPoolCalculator:
    """Calculates valid generation options based on user's capabilities.
    
    Given a set of user's mastered capabilities, computes which scale types,
    arpeggio types, patterns, rhythms, and keys are valid options for
    content generation.
    
    Example usage:
        calculator = ValidPoolCalculator()
        user_caps = {"interval_play_minor_2", "interval_play_major_2", ...}
        pool = calculator.get_full_valid_pool(user_caps)
    """
    
    def __init__(self) -> None:
        """Initialize the calculator with pre-computed lookup tables."""
        self._scale_pattern_intervals = _get_scale_pattern_intervals()
        self._arpeggio_pattern_intervals = _get_arpeggio_pattern_intervals()
        self._learnable_in_context = _get_learnable_in_context()
    
    def _user_has_required(
        self,
        user_caps: Set[str],
        required_caps: FrozenSet[str],
    ) -> bool:
        """Check if user has all required capabilities.
        
        Capabilities marked as 'learnable_in_context' are excluded from
        the gating check - they're taught just-in-time when encountered.
        
        Args:
            user_caps: Set of capability names the user has mastered.
            required_caps: Set of capability names required for the content.
            
        Returns:
            True if user has all gating (non-learnable) capabilities.
        """
        gating_required = required_caps - self._learnable_in_context
        return gating_required.issubset(user_caps)
    
    def get_valid_scale_types(self, user_caps: Set[str]) -> Set[ScaleType]:
        """Get scale types that can be used with at least one pattern.
        
        Args:
            user_caps: Set of capability names the user has mastered.
            
        Returns:
            Set of valid ScaleType values.
        """
        valid: Set[ScaleType] = set()
        
        for scale_type in ScaleType:
            # Check if any pattern is valid for this scale
            for pattern in ScalePattern:
                key = (scale_type, pattern)
                if key in self._scale_pattern_intervals:
                    required = self._scale_pattern_intervals[key]
                    if self._user_has_required(user_caps, required):
                        valid.add(scale_type)
                        break
        
        return valid
    
    def get_valid_arpeggio_types(self, user_caps: Set[str]) -> Set[ArpeggioType]:
        """Get arpeggio types that can be used with at least one pattern.
        
        Args:
            user_caps: Set of capability names the user has mastered.
            
        Returns:
            Set of valid ArpeggioType values.
        """
        valid: Set[ArpeggioType] = set()
        
        for arpeggio_type in ArpeggioType:
            # Check if any pattern is valid for this arpeggio
            for pattern in ArpeggioPattern:
                key = (arpeggio_type, pattern)
                if key in self._arpeggio_pattern_intervals:
                    required = self._arpeggio_pattern_intervals[key]
                    if self._user_has_required(user_caps, required):
                        valid.add(arpeggio_type)
                        break
        
        return valid
    
    def get_valid_patterns_for_scale(
        self,
        scale_type: ScaleType,
        user_caps: Set[str],
    ) -> Set[ScalePattern]:
        """Get valid patterns for a specific scale type.
        
        Args:
            scale_type: The scale type to check patterns for.
            user_caps: Set of capability names the user has mastered.
            
        Returns:
            Set of valid ScalePattern values.
        """
        valid: Set[ScalePattern] = set()
        
        for pattern in ScalePattern:
            key = (scale_type, pattern)
            if key in self._scale_pattern_intervals:
                required = self._scale_pattern_intervals[key]
                if self._user_has_required(user_caps, required):
                    valid.add(pattern)
        
        return valid
    
    def get_valid_patterns_for_arpeggio(
        self,
        arpeggio_type: ArpeggioType,
        user_caps: Set[str],
    ) -> Set[ArpeggioPattern]:
        """Get valid patterns for a specific arpeggio type.
        
        Args:
            arpeggio_type: The arpeggio type to check patterns for.
            user_caps: Set of capability names the user has mastered.
            
        Returns:
            Set of valid ArpeggioPattern values.
        """
        valid: Set[ArpeggioPattern] = set()
        
        for pattern in ArpeggioPattern:
            key = (arpeggio_type, pattern)
            if key in self._arpeggio_pattern_intervals:
                required = self._arpeggio_pattern_intervals[key]
                if self._user_has_required(user_caps, required):
                    valid.add(pattern)
        
        return valid
    
    def get_valid_rhythms(self, user_caps: Set[str]) -> Set[RhythmType]:
        """Get valid rhythm types based on user's capabilities.
        
        Args:
            user_caps: Set of capability names the user has mastered.
            
        Returns:
            Set of valid RhythmType values.
        """
        valid: Set[RhythmType] = set()
        
        for rhythm in RhythmType:
            if rhythm in RHYTHM_TO_CAPABILITIES:
                required = RHYTHM_TO_CAPABILITIES[rhythm]
                if self._user_has_required(user_caps, required):
                    valid.add(rhythm)
        
        return valid
    
    def get_valid_keys(self, user_caps: Set[str]) -> Set[MusicalKey]:
        """Get valid keys based on user's accidental capabilities.
        
        Args:
            user_caps: Set of capability names the user has mastered.
            
        Returns:
            Set of valid MusicalKey values.
        """
        valid: Set[MusicalKey] = set()
        
        for key in MusicalKey:
            required = get_key_required_capabilities(key)
            if self._user_has_required(user_caps, required):
                valid.add(key)
        
        return valid
    
    def get_required_capabilities_for_scale(
        self,
        scale_type: ScaleType,
        pattern: ScalePattern,
    ) -> FrozenSet[str]:
        """Get the capabilities required for a scale + pattern combination.
        
        Args:
            scale_type: The scale type.
            pattern: The pattern to apply.
            
        Returns:
            Set of required capability names.
        """
        key = (scale_type, pattern)
        return self._scale_pattern_intervals.get(key, frozenset())
    
    def get_required_capabilities_for_arpeggio(
        self,
        arpeggio_type: ArpeggioType,
        pattern: ArpeggioPattern,
    ) -> FrozenSet[str]:
        """Get the capabilities required for an arpeggio + pattern combination.
        
        Args:
            arpeggio_type: The arpeggio type.
            pattern: The pattern to apply.
            
        Returns:
            Set of required capability names.
        """
        key = (arpeggio_type, pattern)
        return self._arpeggio_pattern_intervals.get(key, frozenset())
    
    def get_required_capabilities_for_rhythm(
        self,
        rhythm: RhythmType,
    ) -> FrozenSet[str]:
        """Get the capabilities required for a rhythm type.
        
        Args:
            rhythm: The rhythm type.
            
        Returns:
            Set of required capability names.
        """
        return RHYTHM_TO_CAPABILITIES.get(rhythm, frozenset())
    
    def get_required_capabilities_for_key(
        self,
        key: MusicalKey,
    ) -> FrozenSet[str]:
        """Get the capabilities required for a key.
        
        DEPRECATED: Use get_required_accidentals_for_scale_in_key instead
        for accurate accidental detection.
        
        Args:
            key: The musical key.
            
        Returns:
            Set of required capability names.
        """
        return get_key_required_capabilities(key)
    
    def get_required_accidentals_for_scale_in_key(
        self,
        scale_type: ScaleType,
        key: MusicalKey,
    ) -> FrozenSet[str]:
        """Get accidental capabilities required for a scale in a specific key.
        
        This analyzes the actual note spellings to determine what accidentals
        are needed, including sharps, flats, double sharps, double flats,
        and naturals.
        
        Args:
            scale_type: The scale type.
            key: The musical key.
            
        Returns:
            Set of required accidental capability names.
        """
        return get_scale_key_required_accidentals(scale_type, key)
    
    def get_full_valid_pool(
        self,
        user_caps: Set[str],
    ) -> "ValidPool":
        """Get the complete valid pool of generation options.
        
        Args:
            user_caps: Set of capability names the user has mastered.
            
        Returns:
            ValidPool containing all valid options.
        """
        return ValidPool(
            scale_types=self.get_valid_scale_types(user_caps),
            arpeggio_types=self.get_valid_arpeggio_types(user_caps),
            rhythms=self.get_valid_rhythms(user_caps),
            keys=self.get_valid_keys(user_caps),
            scale_patterns={
                scale_type: self.get_valid_patterns_for_scale(scale_type, user_caps)
                for scale_type in self.get_valid_scale_types(user_caps)
            },
            arpeggio_patterns={
                arp_type: self.get_valid_patterns_for_arpeggio(arp_type, user_caps)
                for arp_type in self.get_valid_arpeggio_types(user_caps)
            },
        )


class ValidPool:
    """Container for valid generation options."""
    
    def __init__(
        self,
        scale_types: Set[ScaleType],
        arpeggio_types: Set[ArpeggioType],
        rhythms: Set[RhythmType],
        keys: Set[MusicalKey],
        scale_patterns: Dict[ScaleType, Set[ScalePattern]],
        arpeggio_patterns: Dict[ArpeggioType, Set[ArpeggioPattern]],
    ) -> None:
        self.scale_types = scale_types
        self.arpeggio_types = arpeggio_types
        self.rhythms = rhythms
        self.keys = keys
        self.scale_patterns = scale_patterns
        self.arpeggio_patterns = arpeggio_patterns
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response."""
        return {
            "scale_types": sorted([s.value for s in self.scale_types]),
            "arpeggio_types": sorted([a.value for a in self.arpeggio_types]),
            "rhythms": sorted([r.value for r in self.rhythms]),
            "keys": sorted([k.value for k in self.keys]),
            "scale_patterns": {
                scale_type.value: sorted([p.value for p in patterns])
                for scale_type, patterns in self.scale_patterns.items()
            },
            "arpeggio_patterns": {
                arp_type.value: sorted([p.value for p in patterns])
                for arp_type, patterns in self.arpeggio_patterns.items()
            },
        }


# Module-level singleton
_calculator: Optional[ValidPoolCalculator] = None


def get_valid_pool_calculator() -> ValidPoolCalculator:
    """Get the singleton ValidPoolCalculator instance."""
    global _calculator
    if _calculator is None:
        _calculator = ValidPoolCalculator()
    return _calculator
