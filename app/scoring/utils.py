"""
Scoring Utilities — Normalization and Stage Derivation

Contains pure functions for score normalization and stage derivation.
"""

import math
from .models import DomainScores, DomainBands


def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp value to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def normalize_linear(value: float, low: float, high: float) -> float:
    """
    Linear normalization to [0, 1].
    
    Args:
        value: Raw value to normalize
        low: Value that maps to 0.0
        high: Value that maps to 1.0
    
    Returns:
        Normalized value in [0, 1]
    """
    if high <= low:
        return 0.0
    return clamp((value - low) / (high - low))


def normalize_sigmoid(value: float, midpoint: float, steepness: float = 1.0) -> float:
    """
    Sigmoid normalization centered at midpoint.
    
    Useful when difficulty increases non-linearly.
    """
    return 1.0 / (1.0 + math.exp(-steepness * (value - midpoint)))


# PROVISIONAL: Stage thresholds — calibrate after corpus analysis
STAGE_THRESHOLDS = [0.15, 0.30, 0.45, 0.60, 0.75, 0.90]


def score_to_stage(score: float) -> int:
    """
    Convert a 0.0-1.0 score to a 0-6 stage.
    
    PROVISIONAL thresholds:
        0.00-0.14 → Stage 0
        0.15-0.29 → Stage 1
        0.30-0.44 → Stage 2
        0.45-0.59 → Stage 3
        0.60-0.74 → Stage 4
        0.75-0.89 → Stage 5
        0.90-1.00 → Stage 6
    """
    score = clamp(score)
    for stage, threshold in enumerate(STAGE_THRESHOLDS):
        if score < threshold:
            return stage
    return 6


def derive_bands(scores: DomainScores) -> DomainBands:
    """Derive stage bands from domain scores."""
    return DomainBands(
        primary_stage=score_to_stage(scores['primary']),
        hazard_stage=score_to_stage(scores['hazard']),
        overall_stage=score_to_stage(scores['overall']),
    )
