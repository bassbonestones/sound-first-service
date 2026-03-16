"""
Data Models for Soft Gate Calculation

Contains dataclasses and constants used across calculator modules.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Any


# =============================================================================
# INTERVAL BUCKET BOUNDARIES (semitones)
# =============================================================================

INTERVAL_BUCKET_STEP = (0, 2)       # Steps: 0-2 semitones
INTERVAL_BUCKET_SKIP = (3, 5)       # Skips: 3-5 semitones
INTERVAL_BUCKET_LEAP = (6, 11)      # Leaps: 6-11 semitones
INTERVAL_BUCKET_LARGE = (12, 17)    # Large leaps: 12-17 semitones (octave to octave+P5)
INTERVAL_BUCKET_EXTREME = (18, 999) # Extreme leaps: 18+ semitones (1.5+ octaves)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class NoteEvent:
    """Preprocessed note event for IVS calculation."""
    pitch_midi: int
    duration_ql: float  # quarterLength
    offset_ql: float  # onset time


@dataclass
class IntervalProfile:
    """
    Comprehensive interval demand profile for a piece.
    
    Captures texture (what the piece is mostly made of), sustained demand
    (overall interval challenge), and raw percentiles.
    """
    total_intervals: int
    
    # Texture ratios (sum to 1.0)
    step_ratio: float      # 0-2 semitones
    skip_ratio: float      # 3-5 semitones
    leap_ratio: float      # 6-11 semitones
    large_leap_ratio: float    # 12-17 semitones
    extreme_leap_ratio: float  # 18+ semitones
    
    # Percentiles (in semitones)
    interval_p50: int
    interval_p75: int
    interval_p90: int
    interval_max: int


@dataclass
class IntervalLocalDifficulty:
    """
    Local clustering analysis for interval difficulty.
    
    Detects whether hard leaps are concentrated into spike moments
    or spread throughout the piece.
    """
    max_large_leaps_in_window: int      # 12-17st leaps in hardest window
    max_extreme_leaps_in_window: int    # 18+st leaps in hardest window
    hardest_measure_numbers: List[int]  # Up to 3 measures with most difficulty
    window_count: int                   # Total windows analyzed


@dataclass
class SoftGateMetrics:
    """Complete soft gate metrics for a material."""
    # Staged dimensions
    tonal_complexity_stage: int  # 0-5
    interval_size_stage: int  # 0-6 (DEPRECATED - use legacy_interval_size_stage)
    rhythm_complexity_score: float  # 0.0-1.0 (global score)
    range_usage_stage: int  # 0-6
    
    # NEW: Interval profile stages
    interval_sustained_stage: int = 0  # 0-6, p75-driven, for assignment
    interval_hazard_stage: int = 0     # 0-6, max-driven, for warnings
    legacy_interval_size_stage: int = 0  # max(sustained, hazard) for backward compat
    
    # NEW: Interval profile data
    interval_profile: Optional[IntervalProfile] = None
    interval_local_difficulty: Optional[IntervalLocalDifficulty] = None
    
    # Windowed rhythm complexity (for pieces >= 32 qL)
    rhythm_complexity_peak: Optional[float] = None  # max window score
    rhythm_complexity_p95: Optional[float] = None   # 95th percentile window score
    
    # Continuous metrics
    density_notes_per_second: float = 0.0
    note_density_per_measure: float = 0.0
    peak_notes_per_second: float = 0.0  # Max NPS in any measure
    throughput_volatility: float = 0.0  # Std dev / mean of per-measure NPS
    tempo_difficulty_score: Optional[float] = None  # 0-1, None if no tempo specified
    interval_velocity_score: float = 0.0  # 0-1 (global score)
    
    # Windowed interval velocity (for pieces >= 32 qL)
    interval_velocity_peak: Optional[float] = None  # max window IVS
    interval_velocity_p95: Optional[float] = None   # 95th percentile window IVS
    
    # Additional analysis
    unique_pitch_count: int = 0  # 0-12
    largest_interval_semitones: int = 0
    tessitura_span_semitones: int = 0  # p10-p90 pitch range (working range)
    
    # Raw intermediate values (for debugging/tuning)
    raw_metrics: Optional[Dict[str, Any]] = None
