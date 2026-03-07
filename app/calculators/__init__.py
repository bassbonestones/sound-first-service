"""
Soft Gate Calculators Module

Modular calculator components for soft gate metrics computation.
Each domain calculator can be used independently or through the
main SoftGateCalculator orchestrator.

Re-exports:
    - SoftGateCalculator: Main orchestrator class (requires music21)
    - calculate_soft_gates: Convenience function for MusicXML
    - calculate_unified_domain_scores: Bridge to facet-aware scoring schema
    
    Dataclasses:
    - NoteEvent, IntervalProfile, IntervalLocalDifficulty, SoftGateMetrics
    
    Individual calculators (pure Python, no music21):
    - calculate_tonal_complexity_stage
    - calculate_interval_size_stage, calculate_interval_profile, etc.
    - calculate_rhythm_complexity_score, calculate_rhythm_complexity_windowed
    - calculate_range_usage_stage
    - calculate_density_metrics, calculate_tempo_difficulty_score
"""

# Dataclasses and constants
from .models import (
    NoteEvent,
    IntervalProfile,
    IntervalLocalDifficulty,
    SoftGateMetrics,
    INTERVAL_BUCKET_STEP,
    INTERVAL_BUCKET_SKIP,
    INTERVAL_BUCKET_LEAP,
    INTERVAL_BUCKET_LARGE,
    INTERVAL_BUCKET_EXTREME,
)

# Tonal calculator
from .tonal_calculator import calculate_tonal_complexity_stage

# Interval calculators
from .interval_calculator import (
    calculate_interval_size_stage,
    calculate_interval_profile,
    calculate_interval_local_difficulty,
    calculate_interval_sustained_stage,
    calculate_interval_hazard_stage,
    calculate_interval_velocity_score,
    calculate_interval_velocity_windowed,
    INTERVAL_WINDOW_DURATION_QL,
    INTERVAL_WINDOW_STEP_QL,
    INTERVAL_WINDOW_MIN_PIECE_QL,
    IVS_WINDOW_DURATION_QL,
    IVS_WINDOW_STEP_QL,
    IVS_WINDOW_MIN_PIECE_QL,
)

# Rhythm calculators
from .rhythm_calculator import (
    calculate_rhythm_complexity_score,
    calculate_rhythm_complexity_windowed,
    RHYTHM_WINDOW_DURATION_QL,
    RHYTHM_WINDOW_STEP_QL,
    RHYTHM_WINDOW_MIN_PIECE_QL,
)

# Range calculator
from .range_calculator import calculate_range_usage_stage

# Throughput calculators
from .throughput_calculator import (
    calculate_density_metrics,
    calculate_tempo_difficulty_score,
)

# Orchestrator (requires music21)
from .orchestrator import (
    SoftGateCalculator,
    calculate_soft_gates,
)

# Unified domain scorer (bridge to scoring schema)
from .unified_calculator import calculate_unified_domain_scores

__all__ = [
    # Dataclasses
    'NoteEvent',
    'IntervalProfile',
    'IntervalLocalDifficulty',
    'SoftGateMetrics',
    # Constants
    'INTERVAL_BUCKET_STEP',
    'INTERVAL_BUCKET_SKIP',
    'INTERVAL_BUCKET_LEAP',
    'INTERVAL_BUCKET_LARGE',
    'INTERVAL_BUCKET_EXTREME',
    'INTERVAL_WINDOW_DURATION_QL',
    'INTERVAL_WINDOW_STEP_QL',
    'INTERVAL_WINDOW_MIN_PIECE_QL',
    'IVS_WINDOW_DURATION_QL',
    'IVS_WINDOW_STEP_QL',
    'IVS_WINDOW_MIN_PIECE_QL',
    'RHYTHM_WINDOW_DURATION_QL',
    'RHYTHM_WINDOW_STEP_QL',
    'RHYTHM_WINDOW_MIN_PIECE_QL',
    # Tonal
    'calculate_tonal_complexity_stage',
    # Interval
    'calculate_interval_size_stage',
    'calculate_interval_profile',
    'calculate_interval_local_difficulty',
    'calculate_interval_sustained_stage',
    'calculate_interval_hazard_stage',
    'calculate_interval_velocity_score',
    'calculate_interval_velocity_windowed',
    # Rhythm
    'calculate_rhythm_complexity_score',
    'calculate_rhythm_complexity_windowed',
    # Range
    'calculate_range_usage_stage',
    # Throughput
    'calculate_density_metrics',
    'calculate_tempo_difficulty_score',
    # Orchestrator
    'SoftGateCalculator',
    'calculate_soft_gates',
    # Unified
    'calculate_unified_domain_scores',
]
