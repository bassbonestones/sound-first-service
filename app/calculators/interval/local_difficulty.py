"""
Interval Local Difficulty Analysis

Sliding window analysis for detecting concentrated difficulty spikes.
"""

from typing import List, Optional
from collections import Counter

from app.calculators.models import (
    IntervalLocalDifficulty,
    INTERVAL_BUCKET_LARGE,
    INTERVAL_BUCKET_EXTREME,
)


# Windowing constants
INTERVAL_WINDOW_DURATION_QL = 16.0  # 4 measures of 4/4
INTERVAL_WINDOW_STEP_QL = 4.0       # 1 measure step
INTERVAL_WINDOW_MIN_PIECE_QL = 32.0 # 8 measures minimum for windowing


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
