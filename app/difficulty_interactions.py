"""
Difficulty Interactions for Sound First — Facade Module

This module re-exports all interaction functionality from the app.scoring package.
All implementation has been moved to app/scoring/interactions.py for better organization.

See app/scoring/interactions.py for full documentation.
"""

# Re-export everything from the scoring.interactions module
from app.scoring.interactions import (
    # Configuration
    INTERACTION_CONFIG,
    MAX_INTERACTION_BONUS,
    DEFAULT_DOMAIN_WEIGHTS,
    # Types
    InteractionResult,
    # Functions
    calculate_interaction_bonus,
    get_interaction_flags,
    has_interaction_hazard,
    calculate_composite_difficulty,
    analyze_hazards,
)

__all__ = [
    'INTERACTION_CONFIG',
    'MAX_INTERACTION_BONUS',
    'DEFAULT_DOMAIN_WEIGHTS',
    'InteractionResult',
    'calculate_interaction_bonus',
    'get_interaction_flags',
    'has_interaction_hazard',
    'calculate_composite_difficulty',
    'analyze_hazards',
]
