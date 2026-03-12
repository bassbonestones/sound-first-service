"""
Interval utilities for Sound First — FACADE MODULE

This module re-exports all interval utilities from app.utils.interval_utils.
For new code, prefer importing directly from app.utils.

The actual implementation is in app/utils/interval_utils.py.
"""

# Re-export everything from the utils module
from app.utils.interval_utils import (
    INTERVAL_ORDER,
    INTERVAL_SEMITONES,
    INTERVAL_INDEX,
    DEFAULT_MAX_INTERVAL,
    INTERVAL_MILESTONES,
    interval_to_semitones,
    semitones_to_interval,
    can_play_interval,
    get_next_interval,
    get_previous_interval,
    get_intervals_up_to,
)

__all__ = [
    "INTERVAL_ORDER",
    "INTERVAL_SEMITONES",
    "INTERVAL_INDEX",
    "DEFAULT_MAX_INTERVAL",
    "INTERVAL_MILESTONES",
    "interval_to_semitones",
    "semitones_to_interval",
    "can_play_interval",
    "get_next_interval",
    "get_previous_interval",
    "get_intervals_up_to",
]
