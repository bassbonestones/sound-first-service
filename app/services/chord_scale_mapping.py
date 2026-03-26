"""Chord-to-Scale Mapping Service.

Maps chord symbols to compatible scales for improvisation and practice.
Each chord type has primary and secondary scale recommendations.
Handles alterations (b9, #9, #11, b13) to adjust scale suggestions.

Usage:
    from app.services.chord_scale_mapping import get_scales_for_chord

    # Get compatible scales for a chord
    result = get_scales_for_chord("Cmaj7")
    # Returns: ChordScaleMapping with primary and secondary scales

    # Handle alterations
    result = get_scales_for_chord("C7#11")
    # Returns: Lydian Dominant as primary (due to #11)
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Tuple

from app.schemas.generation_schemas import ScaleType


# =============================================================================
# Types
# =============================================================================


class ChordCategory(str, Enum):
    """Categories of chord types for scale mapping."""

    MAJOR = "major"
    MAJOR_7 = "major_7"
    DOMINANT = "dominant"
    MINOR = "minor"
    MINOR_7 = "minor_7"
    MINOR_MAJOR_7 = "minor_major_7"
    HALF_DIMINISHED = "half_diminished"
    DIMINISHED = "diminished"
    AUGMENTED = "augmented"
    SUSPENDED = "suspended"


@dataclass
class ScaleRecommendation:
    """A single scale recommendation with context."""

    scale: ScaleType
    name: str  # Human-readable name
    reason: str  # Why this scale works
    avoid_notes: List[int] = field(default_factory=list)  # Scale degrees to use carefully


@dataclass
class ChordScaleMapping:
    """Complete scale mapping for a chord."""

    chord_symbol: str
    chord_category: ChordCategory
    primary_scales: List[ScaleRecommendation]  # First choices
    secondary_scales: List[ScaleRecommendation]  # Alternative options
    alterations_applied: List[str]  # Any alterations detected (b9, #11, etc.)
    root: Optional[str] = None  # Root note of the chord
    bass_note: Optional[str] = None  # For slash chords (C/E -> bass_note="E")
    warnings: List[str] = field(default_factory=list)  # Validation warnings

    @property
    def alterations(self) -> List[str]:
        """Alias for alterations_applied."""
        return self.alterations_applied

    @property
    def has_warnings(self) -> bool:
        """Check if there are any validation warnings."""
        return len(self.warnings) > 0


# =============================================================================
# Base Chord-to-Scale Mappings
# =============================================================================
# These are the default mappings before applying alteration modifiers.

# Major triads and maj7
_MAJOR_SCALES: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.IONIAN,
        name="Major (Ionian)",
        reason="Root mode of major scale, full consonance with maj7",
        avoid_notes=[4],  # 4th can clash with major 3rd
    ),
    ScaleRecommendation(
        scale=ScaleType.LYDIAN,
        name="Lydian",
        reason="No avoid notes, #4 adds brightness without tension",
    ),
    ScaleRecommendation(
        scale=ScaleType.PENTATONIC_MAJOR,
        name="Major Pentatonic",
        reason="Consonant, safe choice - no avoid notes",
    ),
]

_MAJOR_SECONDARY: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.BEBOP_MAJOR,
        name="Bebop Major",
        reason="Adds chromatic passing tone for rhythmic alignment",
    ),
    ScaleRecommendation(
        scale=ScaleType.BLUES_MAJOR,
        name="Major Blues",
        reason="Adds bluesy b3 passing tone",
    ),
]

# Minor triads and m7
_MINOR_SCALES: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.DORIAN,
        name="Dorian",
        reason="Default choice for m7, natural 6 is consonant",
    ),
    ScaleRecommendation(
        scale=ScaleType.AEOLIAN,
        name="Natural Minor (Aeolian)",
        reason="Works well over minor, darker sound with b6",
        avoid_notes=[6],  # b6 can be tense
    ),
    ScaleRecommendation(
        scale=ScaleType.PENTATONIC_MINOR,
        name="Minor Pentatonic",
        reason="Safe, consonant - no avoid notes",
    ),
]

_MINOR_SECONDARY: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.BLUES,
        name="Blues Scale",
        reason="Adds blue note (#4/b5) for expressiveness",
    ),
    ScaleRecommendation(
        scale=ScaleType.PHRYGIAN,
        name="Phrygian",
        reason="Spanish/exotic flavor with b2",
        avoid_notes=[2],  # b2 is tense
    ),
    ScaleRecommendation(
        scale=ScaleType.BEBOP_DORIAN,
        name="Bebop Dorian",
        reason="Adds chromatic major 3rd passing tone",
    ),
]

# Dominant 7
_DOMINANT_SCALES: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.MIXOLYDIAN,
        name="Mixolydian",
        reason="Default for dominant 7, natural fit",
        avoid_notes=[4],  # 4th clashes with 3rd
    ),
    ScaleRecommendation(
        scale=ScaleType.BEBOP_DOMINANT,
        name="Bebop Dominant",
        reason="Adds natural 7 passing tone, rhythmic alignment",
    ),
]

_DOMINANT_SECONDARY: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.BLUES,
        name="Blues Scale",
        reason="Blues inflection, especially for blues progressions",
    ),
    ScaleRecommendation(
        scale=ScaleType.PENTATONIC_MINOR,
        name="Minor Pentatonic",
        reason="Works over dominant for bluesy sound",
    ),
    ScaleRecommendation(
        scale=ScaleType.LYDIAN_DOMINANT,
        name="Lydian Dominant",
        reason="Use when chord has #11",
    ),
]

# Dominant 7 with alterations (b9, #9, b13, alt)
_ALTERED_DOMINANT_SCALES: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.ALTERED,
        name="Altered (Super Locrian)",
        reason="Contains all altered tones: b9, #9, b5/#11, b13",
    ),
    ScaleRecommendation(
        scale=ScaleType.DIMINISHED_HW,
        name="Half-Whole Diminished",
        reason="Works for b9/#9 alterations, symmetric pattern",
    ),
]

# Dominant 7#11 specifically
_LYDIAN_DOMINANT_SCALES: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.LYDIAN_DOMINANT,
        name="Lydian Dominant",
        reason="Contains #11 with dominant 7th function",
    ),
]

# Minor-Major 7
_MINOR_MAJOR_SCALES: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.MELODIC_MINOR,
        name="Melodic Minor",
        reason="Natural choice - minor with natural 7",
    ),
    ScaleRecommendation(
        scale=ScaleType.HARMONIC_MINOR,
        name="Harmonic Minor",
        reason="Traditional classical color",
    ),
]

# Half-diminished (m7b5)
_HALF_DIM_SCALES: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.LOCRIAN_NAT2,
        name="Locrian ♮2 (6th mode melodic minor)",
        reason="Locrian with raised 2nd - more melodic",
    ),
    ScaleRecommendation(
        scale=ScaleType.LOCRIAN,
        name="Locrian",
        reason="Traditional choice, has b2 tension",
        avoid_notes=[2],  # b2 is very tense
    ),
]

# Diminished (dim7)
_DIMINISHED_SCALES: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.DIMINISHED_WH,
        name="Whole-Half Diminished",
        reason="Symmetric scale built on dim7 chord tones",
    ),
]

# Augmented
_AUGMENTED_SCALES: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.WHOLE_TONE,
        name="Whole Tone",
        reason="Contains augmented triad, no half steps",
    ),
    ScaleRecommendation(
        scale=ScaleType.LYDIAN_AUGMENTED,
        name="Lydian Augmented",
        reason="Melodic minor mode with #5",
    ),
]

# Suspended chords
_SUSPENDED_SCALES: List[ScaleRecommendation] = [
    ScaleRecommendation(
        scale=ScaleType.MIXOLYDIAN,
        name="Mixolydian",
        reason="Works well, sus4 is natural 4th of scale",
    ),
    ScaleRecommendation(
        scale=ScaleType.DORIAN,
        name="Dorian",
        reason="Modal flavor for sus chords",
    ),
    ScaleRecommendation(
        scale=ScaleType.PENTATONIC_MAJOR,
        name="Major Pentatonic",
        reason="Safe, avoids 3rd entirely",
    ),
]


# =============================================================================
# Chord Quality Detection
# =============================================================================

# Map from common chord quality strings to categories
_QUALITY_TO_CATEGORY: dict[str, ChordCategory] = {
    # Major
    "major": ChordCategory.MAJOR,
    "": ChordCategory.MAJOR,  # Just root = major
    # Major 7
    "maj7": ChordCategory.MAJOR_7,
    "M7": ChordCategory.MAJOR_7,
    "Δ7": ChordCategory.MAJOR_7,
    "Δ": ChordCategory.MAJOR_7,
    "maj9": ChordCategory.MAJOR_7,
    "maj11": ChordCategory.MAJOR_7,
    "maj13": ChordCategory.MAJOR_7,
    "6": ChordCategory.MAJOR_7,  # 6 chords function as major
    "6/9": ChordCategory.MAJOR_7,
    "add9": ChordCategory.MAJOR,
    "add11": ChordCategory.MAJOR,
    # Dominant - basic
    "7": ChordCategory.DOMINANT,
    "dom7": ChordCategory.DOMINANT,
    "9": ChordCategory.DOMINANT,
    "11": ChordCategory.DOMINANT,
    "13": ChordCategory.DOMINANT,
    # Dominant - compound altered (13b9, 13#11, etc.)
    "7b9": ChordCategory.DOMINANT,
    "7#9": ChordCategory.DOMINANT,
    "7b5": ChordCategory.DOMINANT,
    "7#5": ChordCategory.DOMINANT,
    "7#11": ChordCategory.DOMINANT,
    "7b13": ChordCategory.DOMINANT,
    "9b5": ChordCategory.DOMINANT,
    "9#5": ChordCategory.DOMINANT,
    "9#11": ChordCategory.DOMINANT,
    "9b13": ChordCategory.DOMINANT,
    "13b5": ChordCategory.DOMINANT,
    "13#11": ChordCategory.DOMINANT,
    "13b9": ChordCategory.DOMINANT,
    "13#9": ChordCategory.DOMINANT,
    "7b9b5": ChordCategory.DOMINANT,
    "7#9b5": ChordCategory.DOMINANT,
    "7b9#5": ChordCategory.DOMINANT,
    "7#9#5": ChordCategory.DOMINANT,
    "7b9#11": ChordCategory.DOMINANT,
    "7#9#11": ChordCategory.DOMINANT,
    "7b9b13": ChordCategory.DOMINANT,
    "7#9b13": ChordCategory.DOMINANT,
    "7#11b13": ChordCategory.DOMINANT,
    # Suspended dominants
    "7sus4": ChordCategory.SUSPENDED,
    "7sus2": ChordCategory.SUSPENDED,
    "7sus": ChordCategory.SUSPENDED,
    "9sus4": ChordCategory.SUSPENDED,
    "9sus": ChordCategory.SUSPENDED,
    "13sus4": ChordCategory.SUSPENDED,
    "13sus": ChordCategory.SUSPENDED,
    # Minor
    "m": ChordCategory.MINOR,
    "min": ChordCategory.MINOR,
    "-": ChordCategory.MINOR,
    "minor": ChordCategory.MINOR,
    # Minor 7
    "m7": ChordCategory.MINOR_7,
    "min7": ChordCategory.MINOR_7,
    "-7": ChordCategory.MINOR_7,
    "m9": ChordCategory.MINOR_7,
    "m11": ChordCategory.MINOR_7,
    "m13": ChordCategory.MINOR_7,
    "m6": ChordCategory.MINOR_7,
    "m6/9": ChordCategory.MINOR_7,
    "madd9": ChordCategory.MINOR,
    "madd11": ChordCategory.MINOR,
    # Minor-Major 7
    "mMaj7": ChordCategory.MINOR_MAJOR_7,
    "m/Maj7": ChordCategory.MINOR_MAJOR_7,
    "m(Maj7)": ChordCategory.MINOR_MAJOR_7,
    "-Δ7": ChordCategory.MINOR_MAJOR_7,
    "-Δ": ChordCategory.MINOR_MAJOR_7,
    "mMaj9": ChordCategory.MINOR_MAJOR_7,
    "minMaj7": ChordCategory.MINOR_MAJOR_7,
    # Half-diminished
    "m7b5": ChordCategory.HALF_DIMINISHED,
    "ø": ChordCategory.HALF_DIMINISHED,
    "ø7": ChordCategory.HALF_DIMINISHED,
    "half-dim": ChordCategory.HALF_DIMINISHED,
    "-7b5": ChordCategory.HALF_DIMINISHED,
    "min7b5": ChordCategory.HALF_DIMINISHED,
    # Diminished
    "dim": ChordCategory.DIMINISHED,
    "dim7": ChordCategory.DIMINISHED,
    "°": ChordCategory.DIMINISHED,
    "°7": ChordCategory.DIMINISHED,
    "o": ChordCategory.DIMINISHED,
    "o7": ChordCategory.DIMINISHED,
    # Augmented
    "aug": ChordCategory.AUGMENTED,
    "+": ChordCategory.AUGMENTED,
    "aug7": ChordCategory.AUGMENTED,
    "+7": ChordCategory.AUGMENTED,
    "augMaj7": ChordCategory.AUGMENTED,
    "+Maj7": ChordCategory.AUGMENTED,
    "aug9": ChordCategory.AUGMENTED,
    "+9": ChordCategory.AUGMENTED,
    # Suspended
    "sus": ChordCategory.SUSPENDED,
    "sus4": ChordCategory.SUSPENDED,
    "sus2": ChordCategory.SUSPENDED,
    "add4": ChordCategory.SUSPENDED,  # Often functions like sus
}

# Qualities that imply specific alterations (even without parentheses)
_QUALITY_IMPLIED_ALTERATIONS: dict[str, List[str]] = {
    "7b9": ["b9"],
    "7#9": ["#9"],
    "7b5": ["b5"],
    "7#5": ["#5"],
    "7#11": ["#11"],
    "7b13": ["b13"],
    "9b5": ["b5"],
    "9#5": ["#5"],
    "9#11": ["#11"],
    "9b13": ["b13"],
    "13b5": ["b5"],
    "13#11": ["#11"],
    "13b9": ["b9"],
    "13#9": ["#9"],
    "7b9b5": ["b9", "b5"],
    "7#9b5": ["#9", "b5"],
    "7b9#5": ["b9", "#5"],
    "7#9#5": ["#9", "#5"],
    "7b9#11": ["b9", "#11"],
    "7#9#11": ["#9", "#11"],
    "7b9b13": ["b9", "b13"],
    "7#9b13": ["#9", "b13"],
    "7#11b13": ["#11", "b13"],
}

# Alterations that affect scale choice
_ALTERED_EXTENSIONS = frozenset({"b9", "#9", "b5", "#5", "b13", "alt"})
_SHARP_11_EXTENSIONS = frozenset({"#11"})

# All recognized alterations (for validation)
_VALID_ALTERATIONS = frozenset({
    "b9", "#9", "b5", "#5", "b11", "#11", "b13", "#13",
    "add9", "add11", "add13", "alt", "no3", "no5",
})

# Conflicting alteration pairs - these can't coexist
_CONFLICTING_ALTERATIONS: List[Tuple[str, str]] = [
    ("b9", "#9"),    # Can't have both flat and sharp 9
    ("b5", "#5"),    # Can't have both flat and sharp 5
    ("b13", "#13"),  # Can't have both flat and sharp 13
    ("b11", "#11"),  # Can't have both flat and sharp 11
]


@dataclass
class ChordParseResult:
    """Result of parsing a chord symbol."""
    root: str
    quality: str
    alterations: List[str]
    bass_note: Optional[str]
    warnings: List[str] = field(default_factory=list)


def _validate_alterations(alterations: List[str]) -> List[str]:
    """Validate alterations and return warnings.

    Args:
        alterations: List of alteration strings

    Returns:
        List of warning messages (empty if no issues)
    """
    warnings = []

    # Check for unrecognized alterations
    for alt in alterations:
        if alt not in _VALID_ALTERATIONS:
            warnings.append(f"Unrecognized alteration '{alt}' (will be ignored)")

    # Check for conflicting alterations
    alt_set = set(alterations)
    for alt1, alt2 in _CONFLICTING_ALTERATIONS:
        if alt1 in alt_set and alt2 in alt_set:
            warnings.append(f"Conflicting alterations: {alt1} and {alt2} cannot coexist")

    return warnings


def _parse_chord_symbol(symbol: str) -> Tuple[str, str, List[str], Optional[str]]:
    """Parse chord symbol into root, quality, alterations, and bass note.

    Args:
        symbol: Chord symbol like "Cmaj7", "G7#11", "Dm7b5", "C/E", "Dm7/G"

    Returns:
        Tuple of (root, quality_string, list_of_alterations, bass_note_or_None)
    """
    if not symbol:
        return ("C", "", [], None)

    # Check for slash chords first (C/E, Dm7/G)
    bass_note: Optional[str] = None
    if "/" in symbol:
        # Find the last "/" that indicates bass note (not 6/9)
        # We need to be careful: "6/9" is a quality, not a slash chord
        slash_idx = symbol.rfind("/")
        potential_bass = symbol[slash_idx + 1:]
        
        # Check if this is a bass note (single letter + optional accidental)
        # vs a quality like "9" in "6/9"
        if potential_bass and potential_bass[0].upper() in "ABCDEFG":
            # It's a bass note
            bass_letter = potential_bass[0].upper()
            bass_acc = ""
            if len(potential_bass) > 1 and potential_bass[1] in "#b":
                bass_acc = potential_bass[1]
            bass_note = bass_letter + bass_acc
            symbol = symbol[:slash_idx]

    # Extract root (letter + optional accidental)
    root = symbol[0].upper()
    remainder = symbol[1:]

    if remainder and remainder[0] in "#b":
        root += remainder[0]
        remainder = remainder[1:]

    # Find alterations in parentheses or at end
    alterations: List[str] = []
    quality = remainder

    # Check for parenthesized alterations: C7(b9), Cmaj7(#11)
    if "(" in quality and ")" in quality:
        paren_start = quality.index("(")
        paren_end = quality.rindex(")")
        paren_content = quality[paren_start + 1 : paren_end]
        quality = quality[:paren_start] + quality[paren_end + 1 :]

        # Split parenthesized content by comma or space
        for part in paren_content.replace(",", " ").split():
            part = part.strip()
            if part:
                alterations.append(part)

    # Check if quality has implied alterations (e.g., "13b9" implies b9)
    if quality in _QUALITY_IMPLIED_ALTERATIONS:
        alterations.extend(_QUALITY_IMPLIED_ALTERATIONS[quality])
    else:
        # Check for inline alterations: C7b9, C7#11
        for alt in ["#11", "b13", "#9", "b9", "#5", "b5"]:
            if alt in quality and quality not in _QUALITY_TO_CATEGORY:
                # Only extract if not a recognized compound quality
                idx = quality.find(alt)
                # Make sure it's not part of a known quality like "7#9"
                full_quality = quality[:idx] + alt
                if full_quality not in _QUALITY_TO_CATEGORY:
                    alterations.append(alt)
                    quality = quality[:idx] + quality[idx + len(alt) :]

    # Detect "alt" suffix
    if quality.endswith("alt"):
        alterations.append("alt")
        quality = quality[:-3]

    return (root, quality.strip(), alterations, bass_note)


def _get_base_mapping(category: ChordCategory) -> Tuple[List[ScaleRecommendation], List[ScaleRecommendation]]:
    """Get primary and secondary scale lists for a chord category."""
    match category:
        case ChordCategory.MAJOR:
            return (_MAJOR_SCALES[:2], _MAJOR_SECONDARY)  # Ionian, Lydian
        case ChordCategory.MAJOR_7:
            return (_MAJOR_SCALES, _MAJOR_SECONDARY)  # All major scales
        case ChordCategory.MINOR:
            return (_MINOR_SCALES[:2], _MINOR_SECONDARY)  # Dorian, Aeolian
        case ChordCategory.MINOR_7:
            return (_MINOR_SCALES, _MINOR_SECONDARY)  # All minor scales
        case ChordCategory.MINOR_MAJOR_7:
            return (_MINOR_MAJOR_SCALES, _MINOR_SCALES[:1])  # Melodic/Harmonic minor
        case ChordCategory.DOMINANT:
            return (_DOMINANT_SCALES, _DOMINANT_SECONDARY)
        case ChordCategory.HALF_DIMINISHED:
            return (_HALF_DIM_SCALES, [])
        case ChordCategory.DIMINISHED:
            return (_DIMINISHED_SCALES, [])
        case ChordCategory.AUGMENTED:
            return (_AUGMENTED_SCALES, [])
        case ChordCategory.SUSPENDED:
            return (_SUSPENDED_SCALES, [])
        case _:
            # Default to major if unknown
            return (_MAJOR_SCALES[:1], [])


# =============================================================================
# Public API
# =============================================================================


def get_scales_for_chord(
    chord_symbol: str,
) -> ChordScaleMapping:
    """Get compatible scales for a chord symbol.

    Args:
        chord_symbol: Chord symbol like "Cmaj7", "G7#11", "Dm7b5", "C/E"

    Returns:
        ChordScaleMapping with primary and secondary scale recommendations.

    Examples:
        >>> get_scales_for_chord("Cmaj7")
        ChordScaleMapping(primary=[Ionian, Lydian, ...], ...)

        >>> get_scales_for_chord("G7#11")
        ChordScaleMapping(primary=[Lydian Dominant], ...)

        >>> get_scales_for_chord("C7alt")
        ChordScaleMapping(primary=[Altered, Half-Whole Dim], ...)

        >>> get_scales_for_chord("C/Eb")
        ChordScaleMapping(primary=[...], bass_note="Eb", ...)
    """
    root, quality, alterations, bass_note = _parse_chord_symbol(chord_symbol)

    # Validate alterations
    warnings = _validate_alterations(alterations)

    # Determine chord category
    category = _QUALITY_TO_CATEGORY.get(quality, ChordCategory.MAJOR)

    # Get base mapping
    primary, secondary = _get_base_mapping(category)

    # Apply alteration modifiers (only use recognized alterations)
    recognized_alts = [a for a in alterations if a in _VALID_ALTERATIONS]
    has_altered = any(alt in _ALTERED_EXTENSIONS for alt in recognized_alts)
    has_sharp_11 = any(alt in _SHARP_11_EXTENSIONS for alt in recognized_alts)

    if category == ChordCategory.DOMINANT:
        if has_altered:
            # Altered dominants get altered scale as primary
            primary = _ALTERED_DOMINANT_SCALES
            secondary = _DOMINANT_SCALES  # Normal dominant as secondary
        elif has_sharp_11:
            # #11 gets Lydian Dominant
            primary = _LYDIAN_DOMINANT_SCALES
            secondary = _DOMINANT_SCALES + _DOMINANT_SECONDARY

    return ChordScaleMapping(
        chord_symbol=chord_symbol,
        chord_category=category,
        primary_scales=list(primary),
        secondary_scales=list(secondary),
        alterations_applied=alterations,
        root=root,
        bass_note=bass_note,
        warnings=warnings,
    )


def get_all_categories() -> List[ChordCategory]:
    """Get all supported chord categories."""
    return list(ChordCategory)


def get_scale_for_chord_simple(chord_symbol: str) -> ScaleType:
    """Get the single best scale for a chord.

    Convenience function that returns just the top primary scale.

    Args:
        chord_symbol: Chord symbol like "Cmaj7", "G7", "Dm7"

    Returns:
        The best matching ScaleType.
    """
    mapping = get_scales_for_chord(chord_symbol)
    if mapping.primary_scales:
        return mapping.primary_scales[0].scale
    return ScaleType.IONIAN  # Fallback
