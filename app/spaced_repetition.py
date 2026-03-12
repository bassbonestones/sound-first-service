"""
Spaced Repetition Algorithm for Sound First — FACADE MODULE

This module re-exports all spaced repetition functionality from
app.services.spaced_repetition for backwards compatibility.

The actual implementation is in app/services/spaced_repetition.py.

For new code, prefer importing directly from app.services.
"""

# Re-export everything from the services module
from app.services.spaced_repetition import (
    DEFAULT_EASE_FACTOR,
    MIN_EASE_FACTOR,
    DEFAULT_INTERVAL,
    SpacedRepetitionItem,
    rating_to_quality,
    calculate_new_interval,
    update_item_after_review,
    prioritize_materials,
    get_review_stats,
    estimate_mastery_level,
    get_capability_weight_adjustment,
    build_sr_item_from_db,
    select_materials_with_sr,
)

__all__ = [
    "DEFAULT_EASE_FACTOR",
    "MIN_EASE_FACTOR",
    "DEFAULT_INTERVAL",
    "SpacedRepetitionItem",
    "rating_to_quality",
    "calculate_new_interval",
    "update_item_after_review",
    "prioritize_materials",
    "get_review_stats",
    "estimate_mastery_level",
    "get_capability_weight_adjustment",
    "build_sr_item_from_db",
    "select_materials_with_sr",
]
