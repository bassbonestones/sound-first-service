"""
Interval Profile Calculation

Comprehensive interval demand profile with bucket classification.
"""

from typing import List
from collections import Counter

from app.calculators.models import (
    IntervalProfile,
    INTERVAL_BUCKET_STEP,
    INTERVAL_BUCKET_SKIP,
    INTERVAL_BUCKET_LEAP,
    INTERVAL_BUCKET_LARGE,
    INTERVAL_BUCKET_EXTREME,
)


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
        IntervalProfile dataclass with all statistics
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
