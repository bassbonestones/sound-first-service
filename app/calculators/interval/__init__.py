"""
Interval Calculator Package

D2 — Interval Size Stage and related interval analysis functions.
"""

from .stages import (
    calculate_interval_size_stage,
    calculate_interval_sustained_stage,
    calculate_interval_hazard_stage,
)
from .profile import (
    calculate_interval_profile,
)
from .local_difficulty import (
    calculate_interval_local_difficulty,
    INTERVAL_WINDOW_DURATION_QL,
    INTERVAL_WINDOW_STEP_QL,
    INTERVAL_WINDOW_MIN_PIECE_QL,
)
from .velocity import (
    calculate_interval_velocity_score,
    calculate_interval_velocity_windowed,
    IVS_WINDOW_DURATION_QL,
    IVS_WINDOW_STEP_QL,
    IVS_WINDOW_MIN_PIECE_QL,
)

__all__ = [
    # Stage calculations
    'calculate_interval_size_stage',
    'calculate_interval_sustained_stage',
    'calculate_interval_hazard_stage',
    # Profile
    'calculate_interval_profile',
    # Local difficulty
    'calculate_interval_local_difficulty',
    'INTERVAL_WINDOW_DURATION_QL',
    'INTERVAL_WINDOW_STEP_QL',
    'INTERVAL_WINDOW_MIN_PIECE_QL',
    # Velocity
    'calculate_interval_velocity_score',
    'calculate_interval_velocity_windowed',
    'IVS_WINDOW_DURATION_QL',
    'IVS_WINDOW_STEP_QL',
    'IVS_WINDOW_MIN_PIECE_QL',
]
