"""Soft Gate Predictor for Generated Content.

Computes predicted soft gate scores (interval stages, rhythm complexity, tonal
complexity) for generated exercises based on scale, pattern, rhythm, and key
parameters. This enables the practice session engine to select content that
appropriately stretches the user.

Key insight: We already compute melodic intervals for scale+pattern combinations
in valid_pool_calculator.py. We can reuse these intervals to compute interval
stages using the same thresholds as the material analyzer.
"""

from dataclasses import dataclass
from typing import Callable, Dict, FrozenSet, List, Optional, Set, Tuple

from app.schemas.generation_schemas import (
    ArpeggioPattern,
    ArpeggioType,
    GenerationRequest,
    GenerationType,
    MusicalKey,
    RhythmType,
    ScalePattern,
    ScaleType,
)
from app.services.generation.scale_definitions import SCALE_INTERVALS
from app.services.generation.arpeggio_definitions import ARPEGGIO_INTERVALS
from app.services.generation.valid_pool_calculator import (
    KEY_TO_FIFTHS,
    _compute_melodic_intervals_straight,
    _compute_melodic_intervals_in_nths,
    _compute_melodic_intervals_groups,
    _compute_melodic_intervals_pyramid,
    _compute_melodic_intervals_diatonic_triads,
    _compute_melodic_intervals_diatonic_7ths,
    _compute_melodic_intervals_broken_chords,
)


# =============================================================================
# Data Model
# =============================================================================

@dataclass(frozen=True)
class PredictedSoftGates:
    """Predicted soft gate metrics for generated content.
    
    These metrics help the practice session engine select content
    that appropriately stretches the user across multiple dimensions.
    """
    # Interval dimensions (from scale + pattern)
    interval_sustained_stage: int  # 0-6, based on p75 of melodic intervals
    interval_hazard_stage: int     # 0-6, based on max melodic interval
    
    # Rhythm dimension (from rhythm type)
    rhythm_complexity_score: float  # 0.0-1.0
    
    # Tonal dimension (from key)
    tonal_complexity_stage: int    # 0-5
    accidental_count: int          # Number of accidentals in key signature
    
    # Additional context
    max_interval_semitones: int
    interval_p75_semitones: int


# =============================================================================
# Rhythm Complexity Mapping
# =============================================================================

# Maps each RhythmType to a predicted rhythm complexity score (0-1)
# Based on subdivision difficulty, irregularity, and cognitive load
RHYTHM_COMPLEXITY_MAP: Dict[RhythmType, float] = {
    RhythmType.WHOLE_NOTES: 0.05,
    RhythmType.HALF_NOTES: 0.10,
    RhythmType.QUARTER_NOTES: 0.20,
    RhythmType.EIGHTH_NOTES: 0.40,
    RhythmType.SIXTEENTH_NOTES: 0.60,
    RhythmType.EIGHTH_TRIPLETS: 0.55,
    RhythmType.SWING_EIGHTHS: 0.45,
    RhythmType.SCOTCH_SNAP: 0.55,
    RhythmType.DOTTED_QUARTER_EIGHTH: 0.50,
    RhythmType.DOTTED_EIGHTH_SIXTEENTH: 0.55,
    RhythmType.SIXTEENTH_EIGHTH_SIXTEENTH: 0.65,
    RhythmType.EIGHTH_SIXTEENTH_SIXTEENTH: 0.60,
    RhythmType.SIXTEENTH_SIXTEENTH_EIGHTH: 0.60,
    RhythmType.SYNCOPATED: 0.60,
}


# =============================================================================
# Tonal Complexity Mapping
# =============================================================================

# Maps key fifths value to (accidental_count, tonal_stage)
# Stage based on cognitive load of reading accidentals
KEY_TO_TONAL_INFO: Dict[int, Tuple[int, int]] = {
    # C major: 0 accidentals, stage 2 (basic diatonic)
    0: (0, 2),
    # 1 accidental: stage 2
    1: (1, 2),   # G
    -1: (1, 2),  # F
    # 2 accidentals: stage 3
    2: (2, 3),   # D
    -2: (2, 3),  # Bb
    # 3 accidentals: stage 3
    3: (3, 3),   # A
    -3: (3, 3),  # Eb
    # 4 accidentals: stage 4
    4: (4, 4),   # E
    -4: (4, 4),  # Ab
    # 5 accidentals: stage 4
    5: (5, 4),   # B
    -5: (5, 4),  # Db
    # 6 accidentals: stage 5
    6: (6, 5),   # F#/Gb
    -6: (6, 5),
    # 7 accidentals: stage 5
    7: (7, 5),   # C#/Cb
    -7: (7, 5),
}

# Scale types that inherently add tonal complexity
CHROMATIC_SCALE_TYPES: FrozenSet[ScaleType] = frozenset({
    ScaleType.CHROMATIC,
})

# Scale types with blue notes (add +1 to tonal stage)
BLUES_SCALE_TYPES: FrozenSet[ScaleType] = frozenset({
    ScaleType.BLUES,
    ScaleType.BLUES_MAJOR,
})


# =============================================================================
# Interval Stage Thresholds
# =============================================================================

# Sustained stage thresholds (based on p75 interval in semitones)
# Same thresholds as app/calculators/interval/stages.py
SUSTAINED_P75_THRESHOLDS: List[Tuple[int, int]] = [
    (0, 0),   # p75 <= 0: unison
    (1, 1),   # p75 <= 1: half step
    (2, 2),   # p75 <= 2: whole step
    (4, 3),   # p75 <= 4: thirds
    (7, 4),   # p75 <= 7: fourths/fifths
    (9, 5),   # p75 <= 9: sixths
]
# Default stage 6 for p75 > 9

# Hazard stage thresholds (based on max interval in semitones)
HAZARD_MAX_THRESHOLDS: List[Tuple[int, int]] = [
    (2, 0),   # max <= 2: steps only
    (4, 1),   # max <= 4: small skip
    (7, 2),   # max <= 7: fourth/fifth
    (11, 3),  # max <= 11: major 7th
    (15, 4),  # max <= 15: octave to 10th
    (20, 5),  # max <= 20: 10th to 13th
]
# Default stage 6 for max > 20


# =============================================================================
# Interval Calculation Functions
# =============================================================================

def _get_melodic_intervals_for_scale_pattern(
    scale_type: ScaleType,
    pattern: ScalePattern,
) -> Set[int]:
    """Get all unique melodic intervals for a scale pattern.
    
    Args:
        scale_type: The scale type (e.g., IONIAN, DORIAN)
        pattern: The scale pattern (e.g., STRAIGHT_UP_DOWN, IN_3RDS)
        
    Returns:
        Set of melodic interval sizes in semitones
    """
    if scale_type not in SCALE_INTERVALS:
        return set()
    
    scale_intervals = SCALE_INTERVALS[scale_type]
    
    # Map pattern to computation function
    # This mirrors the logic in valid_pool_calculator.py
    if pattern in (ScalePattern.STRAIGHT_UP, ScalePattern.STRAIGHT_DOWN, 
                   ScalePattern.STRAIGHT_UP_DOWN, ScalePattern.STRAIGHT_DOWN_UP):
        return _compute_melodic_intervals_straight(scale_intervals)
    
    elif pattern in (ScalePattern.PYRAMID_ASCEND, ScalePattern.PYRAMID_DESCEND):
        return _compute_melodic_intervals_pyramid(scale_intervals)
    
    elif pattern == ScalePattern.IN_3RDS:
        return _compute_melodic_intervals_in_nths(scale_intervals, 3)
    
    elif pattern == ScalePattern.IN_4THS:
        return _compute_melodic_intervals_in_nths(scale_intervals, 4)
    
    elif pattern == ScalePattern.IN_5THS:
        return _compute_melodic_intervals_in_nths(scale_intervals, 5)
    
    elif pattern == ScalePattern.IN_6THS:
        return _compute_melodic_intervals_in_nths(scale_intervals, 6)
    
    elif pattern == ScalePattern.IN_7THS:
        return _compute_melodic_intervals_in_nths(scale_intervals, 7)
    
    elif pattern == ScalePattern.IN_8THS:
        # For octatonic scales (8 notes)
        return _compute_melodic_intervals_in_nths(scale_intervals, 8)
    
    elif pattern == ScalePattern.IN_OCTAVES:
        return _compute_melodic_intervals_in_nths(scale_intervals, len(scale_intervals) + 1)
    
    # Extended intervals for chromatic scale
    elif pattern == ScalePattern.IN_9THS:
        return _compute_melodic_intervals_in_nths(scale_intervals, 9)
    
    elif pattern == ScalePattern.IN_10THS:
        return _compute_melodic_intervals_in_nths(scale_intervals, 10)
    
    elif pattern == ScalePattern.IN_11THS:
        return _compute_melodic_intervals_in_nths(scale_intervals, 11)
    
    elif pattern == ScalePattern.IN_12THS:
        return _compute_melodic_intervals_in_nths(scale_intervals, 12)
    
    elif pattern == ScalePattern.IN_13THS:
        return _compute_melodic_intervals_in_nths(scale_intervals, 13)
    
    elif pattern in (ScalePattern.GROUPS_OF_3, ScalePattern.GROUPS_OF_4,
                     ScalePattern.GROUPS_OF_5, ScalePattern.GROUPS_OF_6,
                     ScalePattern.GROUPS_OF_7, ScalePattern.GROUPS_OF_8,
                     ScalePattern.GROUPS_OF_9, ScalePattern.GROUPS_OF_10,
                     ScalePattern.GROUPS_OF_11, ScalePattern.GROUPS_OF_12):
        group_size = int(pattern.value.split("_")[-1])
        return _compute_melodic_intervals_groups(scale_intervals, group_size)
    
    elif pattern == ScalePattern.BROKEN_THIRDS_NEIGHBOR:
        # 1-3-4-2 pattern - involves 2nds and 3rds
        return _compute_melodic_intervals_in_nths(scale_intervals, 3)
    
    elif pattern == ScalePattern.DIATONIC_TRIADS:
        return _compute_melodic_intervals_diatonic_triads(scale_intervals)
    
    elif pattern == ScalePattern.DIATONIC_7THS:
        return _compute_melodic_intervals_diatonic_7ths(scale_intervals)
    
    elif pattern == ScalePattern.BROKEN_CHORDS:
        return _compute_melodic_intervals_broken_chords(scale_intervals)
    
    # Default to straight pattern
    return _compute_melodic_intervals_straight(scale_intervals)


def _get_melodic_intervals_for_arpeggio_pattern(
    arpeggio_type: ArpeggioType,
    pattern: ArpeggioPattern,
) -> Set[int]:
    """Get all unique melodic intervals for an arpeggio pattern.
    
    Args:
        arpeggio_type: The arpeggio type (e.g., MAJOR_TRIAD, DOMINANT_7TH)
        pattern: The arpeggio pattern (e.g., STRAIGHT_UP_DOWN, WEAVING)
        
    Returns:
        Set of melodic interval sizes in semitones
    """
    if arpeggio_type not in ARPEGGIO_INTERVALS:
        return set()
    
    arp_intervals = ARPEGGIO_INTERVALS[arpeggio_type]
    
    # For arpeggios, we compute intervals between adjacent chord tones
    # We'll use the straight computation as the approximation
    return _compute_melodic_intervals_straight(arp_intervals)


# =============================================================================
# Stage Calculation Functions
# =============================================================================

def _estimate_p75_from_intervals(intervals: Set[int]) -> int:
    """Estimate p75 interval from a set of unique intervals.
    
    For generated scale patterns, we don't have the full distribution,
    but we can estimate p75 from the unique values. The assumption is
    that in most scale patterns, the intervals appear with roughly
    equal frequency.
    
    Args:
        intervals: Set of unique interval sizes in semitones
        
    Returns:
        Estimated p75 interval in semitones
    """
    if not intervals:
        return 0
    
    sorted_intervals = sorted(intervals)
    n = len(sorted_intervals)
    
    if n == 1:
        return sorted_intervals[0]
    
    # Use 75th percentile index (rounded up)
    p75_idx = min(int(n * 0.75), n - 1)
    return sorted_intervals[p75_idx]


def _calculate_sustained_stage(p75_semitones: int, large_leap_ratio: float = 0.0) -> int:
    """Calculate interval sustained stage from p75 interval.
    
    Uses the same thresholds as app/calculators/interval/stages.py.
    
    Args:
        p75_semitones: The 75th percentile interval in semitones
        large_leap_ratio: Ratio of large leaps (12-17 semitones)
        
    Returns:
        Stage 0-6
    """
    stage = 6  # Default
    for threshold, s in SUSTAINED_P75_THRESHOLDS:
        if p75_semitones <= threshold:
            stage = s
            break
    
    # Modifier: +1 if many large leaps
    if large_leap_ratio > 0.15:
        stage = min(stage + 1, 6)
    
    return stage


def _calculate_hazard_stage(max_semitones: int, extreme_leap_count: int = 0) -> int:
    """Calculate interval hazard stage from max interval.
    
    Uses the same thresholds as app/calculators/interval/stages.py.
    
    Args:
        max_semitones: The maximum interval in semitones
        extreme_leap_count: Count of extreme leaps (18+ semitones) in window
        
    Returns:
        Stage 0-6
    """
    stage = 6  # Default
    for threshold, s in HAZARD_MAX_THRESHOLDS:
        if max_semitones <= threshold:
            stage = s
            break
    
    # Modifier: +1 if multiple extreme leaps
    if extreme_leap_count >= 2:
        stage = min(stage + 1, 6)
    
    return stage


# =============================================================================
# Main Prediction Functions
# =============================================================================

def get_rhythm_complexity(rhythm: RhythmType) -> float:
    """Get the predicted rhythm complexity score for a rhythm type.
    
    Args:
        rhythm: The rhythm type
        
    Returns:
        Complexity score from 0.0 to 1.0
    """
    return RHYTHM_COMPLEXITY_MAP.get(rhythm, 0.40)


def get_tonal_complexity(
    key: MusicalKey,
    scale_type: Optional[ScaleType] = None,
) -> Tuple[int, int]:
    """Get the tonal complexity stage and accidental count for a key.
    
    Args:
        key: The musical key
        scale_type: Optional scale type for additional complexity modifiers
        
    Returns:
        Tuple of (accidental_count, tonal_stage)
    """
    fifths = KEY_TO_FIFTHS.get(key, 0)
    accidentals, stage = KEY_TO_TONAL_INFO.get(fifths, (0, 2))
    
    # Apply scale type modifiers
    if scale_type is not None:
        if scale_type in CHROMATIC_SCALE_TYPES:
            stage = 5  # Chromatic always gets highest complexity
        elif scale_type in BLUES_SCALE_TYPES:
            stage = min(stage + 1, 5)  # Blues adds +1 due to blue notes
    
    return accidentals, stage


def predict_soft_gates(request: GenerationRequest) -> PredictedSoftGates:
    """Predict soft gate metrics for a generation request.
    
    This function computes predicted complexity metrics for generated
    content, enabling the practice session engine to select appropriate
    exercises for the user's current level.
    
    Args:
        request: The generation request with type, definition, pattern, etc.
        
    Returns:
        PredictedSoftGates with all predicted metrics
    """
    # Get melodic intervals based on content type
    intervals: Set[int] = set()
    scale_type: Optional[ScaleType] = None
    
    if request.content_type == GenerationType.SCALE:
        try:
            scale_type = ScaleType(request.definition)
            scale_pattern = ScalePattern(request.pattern) if request.pattern else ScalePattern.STRAIGHT_UP_DOWN
            intervals = _get_melodic_intervals_for_scale_pattern(scale_type, scale_pattern)
        except ValueError:
            pass
    
    elif request.content_type == GenerationType.ARPEGGIO:
        try:
            arpeggio_type = ArpeggioType(request.definition)
            arpeggio_pattern = ArpeggioPattern(request.pattern) if request.pattern else ArpeggioPattern.STRAIGHT_UP_DOWN
            intervals = _get_melodic_intervals_for_arpeggio_pattern(arpeggio_type, arpeggio_pattern)
        except ValueError:
            pass
    
    # Calculate interval metrics
    max_interval = max(intervals) if intervals else 0
    p75_interval = _estimate_p75_from_intervals(intervals)
    
    # Calculate interval stages
    interval_sustained = _calculate_sustained_stage(p75_interval)
    interval_hazard = _calculate_hazard_stage(max_interval)
    
    # Get rhythm complexity
    rhythm_complexity = get_rhythm_complexity(request.rhythm)
    
    # Get tonal complexity
    accidentals, tonal_stage = get_tonal_complexity(request.key, scale_type)
    
    return PredictedSoftGates(
        interval_sustained_stage=interval_sustained,
        interval_hazard_stage=interval_hazard,
        rhythm_complexity_score=rhythm_complexity,
        tonal_complexity_stage=tonal_stage,
        accidental_count=accidentals,
        max_interval_semitones=max_interval,
        interval_p75_semitones=p75_interval,
    )


# =============================================================================
# Singleton Access
# =============================================================================

SoftGatePredictorFn = Callable[[GenerationRequest], PredictedSoftGates]


def get_soft_gate_predictor_function() -> SoftGatePredictorFn:
    """Get the soft gate prediction function.
    
    Returns:
        The predict_soft_gates function for use by other modules.
    """
    return predict_soft_gates
