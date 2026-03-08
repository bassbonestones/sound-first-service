"""
Interval Calculator

D2 — Interval Size Stage and related interval analysis functions.
Includes interval profile, local difficulty, velocity scores.
"""

from typing import Dict, List, Optional, Tuple
from collections import Counter

from .models import (
    NoteEvent,
    IntervalProfile,
    IntervalLocalDifficulty,
    INTERVAL_BUCKET_STEP,
    INTERVAL_BUCKET_SKIP,
    INTERVAL_BUCKET_LEAP,
    INTERVAL_BUCKET_LARGE,
    INTERVAL_BUCKET_EXTREME,
)


# =============================================================================
# WINDOWING CONSTANTS
# =============================================================================

INTERVAL_WINDOW_DURATION_QL = 16.0  # 4 measures of 4/4
INTERVAL_WINDOW_STEP_QL = 4.0       # 1 measure step
INTERVAL_WINDOW_MIN_PIECE_QL = 32.0 # 8 measures minimum for windowing

IVS_WINDOW_DURATION_QL = 16.0  # 4 measures of 4/4
IVS_WINDOW_STEP_QL = 4.0       # 1 measure step
IVS_WINDOW_MIN_PIECE_QL = 32.0 # 8 measures minimum for windowing


# =============================================================================
# D2 — INTERVAL SIZE STAGE
# =============================================================================

def calculate_interval_size_stage(
    interval_semitones: List[int],
) -> Tuple[int, Dict]:
    """
    Calculate D2 interval size stage (0-6) based on p90 interval.
    
    Args:
        interval_semitones: List of absolute melodic interval sizes in semitones
        
    Returns:
        Tuple of (stage, raw_metrics_dict)
    """
    if not interval_semitones:
        return 0, {"p90_interval": 0, "max_interval": 0, "interval_count": 0}
    
    # Calculate p90
    sorted_intervals = sorted(interval_semitones)
    p90_idx = int(len(sorted_intervals) * 0.90)
    p90_interval = sorted_intervals[min(p90_idx, len(sorted_intervals) - 1)]
    
    raw = {
        "p90_interval": p90_interval,
        "max_interval": max(interval_semitones),
        "mean_interval": sum(interval_semitones) / len(interval_semitones),
        "interval_count": len(interval_semitones),
    }
    
    # Stage determination based on p90
    if p90_interval <= 0:
        stage = 0  # Unison
    elif p90_interval <= 1:
        stage = 1  # Half step
    elif p90_interval <= 2:
        stage = 2  # Whole step
    elif p90_interval <= 4:
        stage = 3  # Thirds
    elif p90_interval <= 7:
        stage = 4  # Fourths/Fifths
    elif p90_interval <= 9:
        stage = 5  # Sixths
    else:
        stage = 6  # Sevenths/Octave+
    
    return stage, raw


# =============================================================================
# INTERVAL PROFILE
# =============================================================================

def calculate_interval_profile(
    interval_semitones: List[int],
) -> IntervalProfile:
    """
    Calculate comprehensive interval demand profile.
    
    Classifies intervals into buckets and computes percentiles to give
    a complete picture of interval texture and demand.
    
    Args:
        interval_semitones: List of absolute melodic interval sizes in semitones
        
    Returns:
        IntervalProfile with texture ratios and percentiles
    """
    if not interval_semitones:
        return IntervalProfile(
            total_intervals=0,
            step_ratio=1.0,  # Default to steps for empty
            skip_ratio=0.0,
            leap_ratio=0.0,
            large_leap_ratio=0.0,
            extreme_leap_ratio=0.0,
            interval_p50=0,
            interval_p75=0,
            interval_p90=0,
            interval_max=0,
        )
    
    total = len(interval_semitones)
    sorted_intervals = sorted(interval_semitones)
    
    # Count intervals by bucket
    steps = sum(1 for i in interval_semitones if i <= INTERVAL_BUCKET_STEP[1])
    skips = sum(1 for i in interval_semitones 
                if INTERVAL_BUCKET_SKIP[0] <= i <= INTERVAL_BUCKET_SKIP[1])
    leaps = sum(1 for i in interval_semitones 
                if INTERVAL_BUCKET_LEAP[0] <= i <= INTERVAL_BUCKET_LEAP[1])
    large_leaps = sum(1 for i in interval_semitones 
                      if INTERVAL_BUCKET_LARGE[0] <= i <= INTERVAL_BUCKET_LARGE[1])
    extreme_leaps = sum(1 for i in interval_semitones 
                        if i >= INTERVAL_BUCKET_EXTREME[0])
    
    # Calculate percentiles
    def percentile(sorted_list: List[int], p: float) -> int:
        idx = int(len(sorted_list) * p)
        return sorted_list[min(idx, len(sorted_list) - 1)]
    
    return IntervalProfile(
        total_intervals=total,
        step_ratio=steps / total,
        skip_ratio=skips / total,
        leap_ratio=leaps / total,
        large_leap_ratio=large_leaps / total,
        extreme_leap_ratio=extreme_leaps / total,
        interval_p50=percentile(sorted_intervals, 0.50),
        interval_p75=percentile(sorted_intervals, 0.75),
        interval_p90=percentile(sorted_intervals, 0.90),
        interval_max=max(interval_semitones),
    )


# =============================================================================
# LOCAL DIFFICULTY ANALYSIS
# =============================================================================

def calculate_interval_local_difficulty(
    interval_semitones: List[int],
    offsets: List[float],  # onset times of the SECOND note in each interval
    measure_numbers: List[int],  # measure number for each interval
) -> Optional[IntervalLocalDifficulty]:
    """
    Analyze local clustering of large/extreme leaps.
    
    Uses sliding windows to detect concentrated difficulty spikes.
    Also tracks which measures contain the most difficult intervals.
    
    Args:
        interval_semitones: List of absolute melodic interval sizes
        offsets: Onset times (quarterLength) of second note in each interval
        measure_numbers: Measure number where each interval occurs
        
    Returns:
        IntervalLocalDifficulty or None if piece is too short for windowing
    """
    if not interval_semitones or not offsets:
        return None
    
    # Check if piece is long enough for windowing
    total_duration = max(offsets) if offsets else 0
    if total_duration < INTERVAL_WINDOW_MIN_PIECE_QL:
        # For short pieces, still report measure-level stats
        large_by_measure = Counter()
        extreme_by_measure = Counter()
        
        for i, intv in enumerate(interval_semitones):
            meas = measure_numbers[i] if i < len(measure_numbers) else 1
            if INTERVAL_BUCKET_LARGE[0] <= intv <= INTERVAL_BUCKET_LARGE[1]:
                large_by_measure[meas] += 1
            elif intv >= INTERVAL_BUCKET_EXTREME[0]:
                extreme_by_measure[meas] += 1
        
        # Find hardest measures (by total large+extreme)
        combined = Counter()
        for m, c in large_by_measure.items():
            combined[m] += c
        for m, c in extreme_by_measure.items():
            combined[m] += c * 2  # Weight extreme more
        
        hardest = [m for m, _ in combined.most_common(3)]
        
        return IntervalLocalDifficulty(
            max_large_leaps_in_window=max(large_by_measure.values()) if large_by_measure else 0,
            max_extreme_leaps_in_window=max(extreme_by_measure.values()) if extreme_by_measure else 0,
            hardest_measure_numbers=hardest,
            window_count=0,  # Not enough for windowing
        )
    
    # Build windows and track leap counts
    window_large_counts = []
    window_extreme_counts = []
    window_start = 0.0
    
    while window_start + INTERVAL_WINDOW_DURATION_QL <= total_duration + INTERVAL_WINDOW_STEP_QL:
        window_end = window_start + INTERVAL_WINDOW_DURATION_QL
        
        # Find intervals in this window
        window_large = 0
        window_extreme = 0
        
        for i, off in enumerate(offsets):
            if window_start <= off < window_end:
                intv = interval_semitones[i]
                if INTERVAL_BUCKET_LARGE[0] <= intv <= INTERVAL_BUCKET_LARGE[1]:
                    window_large += 1
                elif intv >= INTERVAL_BUCKET_EXTREME[0]:
                    window_extreme += 1
        
        window_large_counts.append(window_large)
        window_extreme_counts.append(window_extreme)
        window_start += INTERVAL_WINDOW_STEP_QL
    
    # Track by measure for hardest_measure_numbers
    large_by_measure = Counter()
    extreme_by_measure = Counter()
    
    for i, intv in enumerate(interval_semitones):
        meas = measure_numbers[i] if i < len(measure_numbers) else 1
        if INTERVAL_BUCKET_LARGE[0] <= intv <= INTERVAL_BUCKET_LARGE[1]:
            large_by_measure[meas] += 1
        elif intv >= INTERVAL_BUCKET_EXTREME[0]:
            extreme_by_measure[meas] += 1
    
    # Find hardest measures
    combined = Counter()
    for m, c in large_by_measure.items():
        combined[m] += c
    for m, c in extreme_by_measure.items():
        combined[m] += c * 2  # Weight extreme more
    
    hardest = [m for m, _ in combined.most_common(3)]
    
    return IntervalLocalDifficulty(
        max_large_leaps_in_window=max(window_large_counts) if window_large_counts else 0,
        max_extreme_leaps_in_window=max(window_extreme_counts) if window_extreme_counts else 0,
        hardest_measure_numbers=hardest,
        window_count=len(window_large_counts),
    )


# =============================================================================
# SUSTAINED AND HAZARD STAGES
# =============================================================================

def calculate_interval_sustained_stage(
    profile: IntervalProfile,
) -> int:
    """
    Calculate interval sustained stage (0-6) for overall suitability.
    
    Primary driver: p75 interval (reflects "upper-normal demand")
    Modifier: bump +1 if large_leap_ratio > 0.15
    
    This stage answers: "Can a student reasonably live in this piece overall?"
    
    Args:
        profile: IntervalProfile with percentiles and ratios
        
    Returns:
        Stage 0-6
    """
    p75 = profile.interval_p75
    
    # Base stage from p75
    if p75 <= 0:
        stage = 0  # Unison
    elif p75 <= 1:
        stage = 1  # Half step
    elif p75 <= 2:
        stage = 2  # Whole step
    elif p75 <= 4:
        stage = 3  # Thirds
    elif p75 <= 7:
        stage = 4  # Fourths/Fifths
    elif p75 <= 9:
        stage = 5  # Sixths
    else:
        stage = 6  # Sevenths/Octave+
    
    # Bump up if many large leaps (>15%)
    if profile.large_leap_ratio > 0.15:
        stage = min(stage + 1, 6)
    
    return stage


def calculate_interval_hazard_stage(
    profile: IntervalProfile,
    local_difficulty: Optional[IntervalLocalDifficulty],
) -> int:
    """
    Calculate interval hazard stage (0-6) for peak danger.
    
    Primary driver: interval_max
    Modifier: bump +1 if max_extreme_leaps_in_window >= 2
    
    This stage answers: "Does this piece contain moments requiring scaffolding?"
    
    Args:
        profile: IntervalProfile with max interval
        local_difficulty: Optional local clustering analysis
        
    Returns:
        Stage 0-6
    """
    max_intv = profile.interval_max
    
    # Base stage from max interval (different thresholds than sustained)
    if max_intv <= 2:
        stage = 0  # Steps only
    elif max_intv <= 4:
        stage = 1  # Small skip
    elif max_intv <= 7:
        stage = 2  # Fourth/Fifth
    elif max_intv <= 11:
        stage = 3  # Up to major 7th
    elif max_intv <= 15:
        stage = 4  # Octave to 10th
    elif max_intv <= 20:
        stage = 5  # 10th to 13th
    else:
        stage = 6  # 14th+ (extreme)
    
    # Bump up if clustered extreme leaps
    if local_difficulty and local_difficulty.max_extreme_leaps_in_window >= 2:
        stage = min(stage + 1, 6)
    
    return stage


# =============================================================================
# INTERVAL VELOCITY SCORE (IVS)
# =============================================================================

def calculate_interval_velocity_score(
    note_events: List[NoteEvent],
    alpha: float = 1.0,
    beta: float = 1.5,
) -> Tuple[float, Dict]:
    """
    Calculate Interval Velocity Score (IVS).
    
    Intuition: Score increases when intervals are larger AND time
    between notes is smaller. A big leap on long notes is not as
    hard as the same leap in 16ths.
    
    Args:
        note_events: List of NoteEvent with pitch_midi, offset_ql
        alpha: Size exponent (default 1.0)
        beta: Speed exponent (default 1.5)
        
    Returns:
        Tuple of (IVS 0-1, raw_metrics_dict)
    """
    if len(note_events) < 2:
        return 0.0, {"interval_count": 0}
    
    contributions = []
    dt_ref = 1.0  # Reference: one quarter note
    
    for i in range(len(note_events) - 1):
        e1, e2 = note_events[i], note_events[i + 1]
        
        # Interval size (semitones)
        delta = abs(e2.pitch_midi - e1.pitch_midi)
        
        # Time between onsets
        dt = e2.offset_ql - e1.offset_ql
        if dt <= 0:
            continue
        
        # Normalize interval (cap at octave)
        size_norm = min(delta, 12) / 12
        
        # Normalize speed
        speed_norm = dt_ref / (dt_ref + dt)
        
        # Combined contribution
        contrib = (size_norm ** alpha) * (speed_norm ** beta)
        contributions.append(contrib)
    
    if not contributions:
        return 0.0, {"interval_count": 0}
    
    # Aggregate using mean + p90
    mean_contrib = sum(contributions) / len(contributions)
    sorted_contribs = sorted(contributions)
    p90_idx = int(len(sorted_contribs) * 0.90)
    p90_contrib = sorted_contribs[min(p90_idx, len(sorted_contribs) - 1)]
    
    ivs_raw = 0.7 * mean_contrib + 0.3 * p90_contrib
    ivs = max(0.0, min(1.0, ivs_raw))
    
    raw = {
        "interval_count": len(contributions),
        "mean_contrib": mean_contrib,
        "p90_contrib": p90_contrib,
        "ivs_raw": ivs_raw,
    }
    
    return ivs, raw


def calculate_interval_velocity_windowed(
    note_events: List[NoteEvent],
    alpha: float = 1.0,
    beta: float = 1.5,
) -> Tuple[Optional[float], Optional[float], Dict]:
    """
    Calculate windowed interval velocity score for longer pieces.
    
    Uses sliding windows to find peak IVS regions, solving
    the "mostly easy except one hard passage" problem.
    
    Args:
        note_events: List of NoteEvent with pitch_midi, offset_ql
        alpha: Size exponent (default 1.0)
        beta: Speed exponent (default 1.5)
        
    Returns:
        Tuple of (peak_score, p95_score, raw_metrics_dict)
        Returns (None, None, {}) if piece is too short for windowing
    """
    if len(note_events) < 2:
        return None, None, {"reason": "no_events"}
    
    # Calculate piece total duration from last note offset + duration
    total_duration = max(e.offset_ql + e.duration_ql for e in note_events)
    
    if total_duration < IVS_WINDOW_MIN_PIECE_QL:
        return None, None, {"reason": "piece_too_short", "duration_ql": total_duration}
    
    # Build windows
    window_scores = []
    window_start = 0.0
    
    while window_start + IVS_WINDOW_DURATION_QL <= total_duration + IVS_WINDOW_STEP_QL:
        window_end = window_start + IVS_WINDOW_DURATION_QL
        
        # Find notes in this window
        window_events = [
            e for e in note_events
            if window_start <= e.offset_ql < window_end
        ]
        
        if len(window_events) >= 2:
            # Calculate window IVS
            w_score, _ = calculate_interval_velocity_score(window_events, alpha, beta)
            window_scores.append(w_score)
        
        window_start += IVS_WINDOW_STEP_QL
    
    if not window_scores:
        return None, None, {"reason": "no_valid_windows"}
    
    # Calculate peak and p95
    sorted_scores = sorted(window_scores)
    peak = max(window_scores)
    
    # P95: 95th percentile
    p95_idx = int(len(sorted_scores) * 0.95)
    p95 = sorted_scores[min(p95_idx, len(sorted_scores) - 1)]
    
    raw = {
        "window_count": len(window_scores),
        "total_duration_ql": total_duration,
        "window_duration_ql": IVS_WINDOW_DURATION_QL,
        "window_step_ql": IVS_WINDOW_STEP_QL,
        "min_window_score": min(window_scores),
        "max_window_score": peak,
        "mean_window_score": sum(window_scores) / len(window_scores),
    }
    
    return peak, p95, raw
