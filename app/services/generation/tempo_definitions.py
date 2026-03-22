"""Tempo definitions and BPM ranges for rhythm types.

This module provides tempo bounds (min/max BPM) for each rhythm type.
These ranges represent musically appropriate tempos for practice:
- Minimum BPM: Slow enough for careful practice and learning
- Maximum BPM: Fast enough to challenge advanced players without being unmusical

The user always controls tempo at practice time within these bounds.
Ranges can be refined based on pedagogical feedback.
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple

from app.schemas.generation_schemas import RhythmType


@dataclass(frozen=True)
class TempoBounds:
    """Tempo range for a rhythm type.
    
    Attributes:
        min_bpm: Minimum tempo in beats per minute (quarter note = 1 beat)
        max_bpm: Maximum tempo in beats per minute
    """
    min_bpm: int
    max_bpm: int
    
    def __post_init__(self) -> None:
        """Validate bounds on creation."""
        if self.min_bpm < 20:
            raise ValueError(f"min_bpm must be >= 20, got {self.min_bpm}")
        if self.max_bpm > 400:
            raise ValueError(f"max_bpm must be <= 400, got {self.max_bpm}")
        if self.min_bpm > self.max_bpm:
            raise ValueError(
                f"min_bpm ({self.min_bpm}) cannot exceed max_bpm ({self.max_bpm})"
            )
    
    def contains(self, bpm: int) -> bool:
        """Check if a BPM value is within bounds."""
        return self.min_bpm <= bpm <= self.max_bpm
    
    def clamp(self, bpm: int) -> int:
        """Clamp a BPM value to within bounds."""
        return max(self.min_bpm, min(self.max_bpm, bpm))
    
    def as_tuple(self) -> Tuple[int, int]:
        """Return bounds as (min, max) tuple."""
        return (self.min_bpm, self.max_bpm)


# =============================================================================
# Tempo Bounds by Rhythm Category
# =============================================================================

# Sustained rhythms: Very slow focus on tone and intonation
_SUSTAINED_BOUNDS = TempoBounds(min_bpm=40, max_bpm=80)

# Quarter notes: Core pulse, wide tempo range
_QUARTER_BOUNDS = TempoBounds(min_bpm=40, max_bpm=200)

# Eighth notes: At max BPM (160), 8ths = 320 notes/min
_EIGHTH_BOUNDS = TempoBounds(min_bpm=40, max_bpm=160)

# Sixteenth notes: At max BPM (120), 16ths = 480 notes/min
_SIXTEENTH_BOUNDS = TempoBounds(min_bpm=40, max_bpm=120)

# Triplets: 3 notes per beat, moderate to fast
_TRIPLET_BOUNDS = TempoBounds(min_bpm=40, max_bpm=140)

# Swing: Jazz feel, similar to eighth notes
_SWING_BOUNDS = TempoBounds(min_bpm=40, max_bpm=160)

# Dotted rhythms: Need clarity at slower tempos
_DOTTED_BOUNDS = TempoBounds(min_bpm=40, max_bpm=140)

# Compound cells: Complex patterns need room to breathe
_COMPOUND_BOUNDS = TempoBounds(min_bpm=40, max_bpm=120)


# =============================================================================
# Rhythm Type to Tempo Bounds Mapping
# =============================================================================

TEMPO_BOUNDS: Dict[RhythmType, TempoBounds] = {
    # Sustained
    RhythmType.WHOLE_NOTES: _SUSTAINED_BOUNDS,
    RhythmType.HALF_NOTES: _SUSTAINED_BOUNDS,
    
    # Pulse
    RhythmType.QUARTER_NOTES: _QUARTER_BOUNDS,
    
    # Subdivisions
    RhythmType.EIGHTH_NOTES: _EIGHTH_BOUNDS,
    RhythmType.SIXTEENTH_NOTES: _SIXTEENTH_BOUNDS,
    
    # Triplets
    RhythmType.EIGHTH_TRIPLETS: _TRIPLET_BOUNDS,
    
    # Swing
    RhythmType.SWING_EIGHTHS: _SWING_BOUNDS,
    RhythmType.SCOTCH_SNAP: _DOTTED_BOUNDS,  # Similar complexity to dotted
    
    # Dotted
    RhythmType.DOTTED_QUARTER_EIGHTH: _DOTTED_BOUNDS,
    RhythmType.DOTTED_EIGHTH_SIXTEENTH: _DOTTED_BOUNDS,
    
    # Compound cells
    RhythmType.SIXTEENTH_EIGHTH_SIXTEENTH: _COMPOUND_BOUNDS,
    RhythmType.EIGHTH_SIXTEENTH_SIXTEENTH: _COMPOUND_BOUNDS,
    RhythmType.SIXTEENTH_SIXTEENTH_EIGHTH: _COMPOUND_BOUNDS,
    RhythmType.SYNCOPATED: _COMPOUND_BOUNDS,
}


def get_tempo_bounds(rhythm_type: RhythmType) -> TempoBounds:
    """Get the tempo bounds for a rhythm type.
    
    Args:
        rhythm_type: The rhythm type enum value.
        
    Returns:
        TempoBounds with min/max BPM for this rhythm.
        
    Raises:
        KeyError: If rhythm type is not mapped (should never happen).
    """
    if rhythm_type not in TEMPO_BOUNDS:
        raise KeyError(f"No tempo bounds defined for rhythm type: {rhythm_type}")
    return TEMPO_BOUNDS[rhythm_type]


def get_default_tempo(rhythm_type: RhythmType) -> int:
    """Get a sensible default starting tempo for a rhythm type.
    
    Returns a tempo that's comfortable for learning - typically
    closer to the minimum but not at the extreme.
    
    Args:
        rhythm_type: The rhythm type enum value.
        
    Returns:
        Default BPM as an integer.
    """
    bounds = get_tempo_bounds(rhythm_type)
    # Start at roughly 1/3 of the way through the range
    # This gives room to slow down and speed up
    range_span = bounds.max_bpm - bounds.min_bpm
    return bounds.min_bpm + int(range_span * 0.3)


def validate_tempo_for_rhythm(
    rhythm_type: RhythmType,
    tempo_bpm: int,
    clamp: bool = False,
) -> int:
    """Validate a tempo is appropriate for a rhythm type.
    
    Args:
        rhythm_type: The rhythm type enum value.
        tempo_bpm: The requested tempo in BPM.
        clamp: If True, clamp to valid range instead of raising.
        
    Returns:
        The validated (or clamped) tempo.
        
    Raises:
        ValueError: If tempo is out of range and clamp=False.
    """
    bounds = get_tempo_bounds(rhythm_type)
    
    if clamp:
        return bounds.clamp(tempo_bpm)
    
    if not bounds.contains(tempo_bpm):
        raise ValueError(
            f"Tempo {tempo_bpm} BPM is outside valid range for {rhythm_type.value}: "
            f"{bounds.min_bpm}-{bounds.max_bpm} BPM"
        )
    
    return tempo_bpm


def get_supported_rhythms_with_bounds() -> Dict[str, Dict[str, int]]:
    """Get all rhythm types with their tempo bounds.
    
    Returns:
        Dict mapping rhythm type values to their bounds:
        {"whole_notes": {"min_bpm": 40, "max_bpm": 80}, ...}
    """
    return {
        rhythm_type.value: {
            "min_bpm": bounds.min_bpm,
            "max_bpm": bounds.max_bpm,
        }
        for rhythm_type, bounds in TEMPO_BOUNDS.items()
    }


# =============================================================================
# Rhythm-Note Count Compatibility
# =============================================================================

# Maximum note counts for sustained rhythms
# These prevent unreasonably long exercises (e.g., 50 whole notes)
# Based on ~16 measures max in 4/4 time (64 beats)
MAX_NOTES_FOR_RHYTHM: Dict[RhythmType, int] = {
    RhythmType.WHOLE_NOTES: 16,      # 16 × 4 beats = 64 beats (16 measures)
    RhythmType.HALF_NOTES: 32,       # 32 × 2 beats = 64 beats (16 measures)
    # All other rhythms have no practical limit for typical exercises
}


def get_max_notes_for_rhythm(rhythm_type: RhythmType) -> int | None:
    """Get the maximum note count for a rhythm type.
    
    Args:
        rhythm_type: The rhythm type enum value.
        
    Returns:
        Maximum note count, or None if no limit applies.
    """
    return MAX_NOTES_FOR_RHYTHM.get(rhythm_type)


def validate_note_count_for_rhythm(
    rhythm_type: RhythmType,
    note_count: int,
) -> None:
    """Validate that note count is appropriate for rhythm type.
    
    Sustained rhythms (whole notes, half notes) have maximum note counts
    to prevent unreasonably long exercises.
    
    Args:
        rhythm_type: The rhythm type enum value.
        note_count: Number of notes in the exercise.
        
    Raises:
        ValueError: If note count exceeds limit for the rhythm type.
    """
    max_notes = get_max_notes_for_rhythm(rhythm_type)
    
    if max_notes is not None and note_count > max_notes:
        raise ValueError(
            f"{rhythm_type.value} rhythm is limited to {max_notes} notes, "
            f"but pattern generates {note_count} notes. "
            f"Use a faster rhythm (quarter_notes or faster) for complex patterns."
        )


def get_compatible_rhythms_for_note_count(note_count: int) -> List[RhythmType]:
    """Get all rhythm types compatible with a given note count.
    
    Args:
        note_count: Number of notes in the exercise.
        
    Returns:
        List of compatible RhythmType values.
    """
    compatible = []
    for rhythm_type in RhythmType:
        max_notes = get_max_notes_for_rhythm(rhythm_type)
        if max_notes is None or note_count <= max_notes:
            compatible.append(rhythm_type)
    return compatible
