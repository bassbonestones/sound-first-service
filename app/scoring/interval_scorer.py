"""
Interval Domain Scorer

Analyzes melodic interval complexity with facet-aware scoring.
"""

from typing import Dict, Any
from .models import DomainResult, DomainScores
from .utils import normalize_linear, clamp, derive_bands


# PROVISIONAL THRESHOLDS (widened for realistic pieces)
INTERVAL_STEP_SKIP_P75_LOW = 2      # minor 2nd
INTERVAL_STEP_SKIP_P75_HIGH = 12    # octave (was 7)
INTERVAL_SUSTAINED_LEAP_P90_LOW = 5 # P4
INTERVAL_SUSTAINED_LEAP_P90_HIGH = 19  # octave + 5th (was 15)
INTERVAL_EXTREME_LEAP_MAX_LOW = 12  # octave
INTERVAL_EXTREME_LEAP_MAX_HIGH = 36 # 3 octaves (was 24)
INTERVAL_CLUSTER_WINDOW_LOW = 1
INTERVAL_CLUSTER_WINDOW_HIGH = 8    # (was 5)


def analyze_interval_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze interval complexity with facet-aware scoring.
    
    Profile fields:
        interval_p50: int - median interval (semitones)
        interval_p75: int - 75th percentile interval
        interval_p90: int - 90th percentile interval
        interval_max: int - maximum interval
        step_ratio: float - proportion of steps (0-2 semitones)
        skip_ratio: float - proportion of skips (3-5 semitones)
        leap_ratio: float - proportion of leaps (6-11 semitones)
        large_leap_ratio: float - proportion of large leaps (12-17 semitones)
        extreme_leap_ratio: float - proportion of extreme leaps (18+ semitones)
        max_large_leaps_in_window: int - maximum large leaps in sliding window
        max_extreme_leaps_in_window: int - maximum extreme leaps in sliding window
    
    Facet scores:
        step_skip_complexity: complexity from step/skip patterns
        sustained_leap_complexity: typical leap demand (p75/p90)
        extreme_leap_hazard: danger from maximum intervals
        clustered_leap_hazard: danger from clustered leaps
    
    Domain scores:
        primary: sustained melodic difficulty
        hazard: extreme + clustered leap danger
        overall: blended interval difficulty
    """
    # Extract profile with defaults
    p50 = profile.get('interval_p50', 0)
    p75 = profile.get('interval_p75', 0)
    p90 = profile.get('interval_p90', 0)
    max_interval = profile.get('interval_max', 0)
    step_ratio = profile.get('step_ratio', 1.0)
    skip_ratio = profile.get('skip_ratio', 0.0)
    leap_ratio = profile.get('leap_ratio', 0.0)
    large_leap_ratio = profile.get('large_leap_ratio', 0.0)
    extreme_leap_ratio = profile.get('extreme_leap_ratio', 0.0)
    max_large_in_window = profile.get('max_large_leaps_in_window', 0)
    max_extreme_in_window = profile.get('max_extreme_leaps_in_window', 0)
    
    # Calculate facet scores
    step_skip_complexity = normalize_linear(p75, INTERVAL_STEP_SKIP_P75_LOW, INTERVAL_STEP_SKIP_P75_HIGH)
    
    sustained_leap_complexity = normalize_linear(p90, INTERVAL_SUSTAINED_LEAP_P90_LOW, INTERVAL_SUSTAINED_LEAP_P90_HIGH)
    # Modest boost if large leaps are frequent
    if large_leap_ratio > 0.05:
        sustained_leap_complexity = clamp(sustained_leap_complexity + large_leap_ratio)
    
    extreme_leap_hazard = normalize_linear(max_interval, INTERVAL_EXTREME_LEAP_MAX_LOW, INTERVAL_EXTREME_LEAP_MAX_HIGH)
    # Modest boost if extreme leaps exist at all
    if extreme_leap_ratio > 0:
        extreme_leap_hazard = clamp(extreme_leap_hazard + extreme_leap_ratio * 2)
    
    clustered_leap_hazard = normalize_linear(
        max_large_in_window + max_extreme_in_window,  # removed *2 multiplier
        INTERVAL_CLUSTER_WINDOW_LOW,
        INTERVAL_CLUSTER_WINDOW_HIGH
    )
    
    facet_scores = {
        'step_skip_complexity': round(step_skip_complexity, 4),
        'sustained_leap_complexity': round(sustained_leap_complexity, 4),
        'extreme_leap_hazard': round(extreme_leap_hazard, 4),
        'clustered_leap_hazard': round(clustered_leap_hazard, 4),
    }
    
    # Derive domain scores from facets
    primary = clamp(
        step_skip_complexity * 0.3 +
        sustained_leap_complexity * 0.7
    )
    
    hazard = clamp(
        extreme_leap_hazard * 0.6 +
        clustered_leap_hazard * 0.4
    )
    
    overall = clamp(primary * 0.6 + hazard * 0.4)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if extreme_leap_hazard > 0.5:
        flags.append('extreme_intervals_present')
    if clustered_leap_hazard > 0.6:
        flags.append('clustered_leaps_warning')
    if hazard > primary + 0.2:
        flags.append('interval_hazard_spike')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=1.0 if profile.get('total_intervals', 0) > 10 else 0.8,
    )
