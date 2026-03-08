"""
Interval Stage Calculations

D2 — Interval Size Stage and related stage derivation functions.
"""

from typing import Dict, List, Optional, Tuple

from app.calculators.models import (
    IntervalProfile,
    IntervalLocalDifficulty,
)


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
