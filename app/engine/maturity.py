"""
Maturity calculation and bucket weight functions.
"""
import random
from typing import Dict

from .config import DEFAULT_CONFIG, EngineConfig
from .models import Bucket


def compute_material_maturity(
    mastered_difficulty_sum: float,
    total_difficulty_sum: float
) -> float:
    """
    Compute material maturity as difficulty-weighted ratio.
    
    mat_maturity = Σ difficulty_index(mastered) / Σ difficulty_index(eligible)
    """
    if total_difficulty_sum == 0:
        return 0.0
    return mastered_difficulty_sum / total_difficulty_sum


def compute_capability_maturity(
    mastered_weight_sum: float,
    total_weight_sum: float
) -> float:
    """
    Compute capability maturity as difficulty-weighted ratio.
    
    cap_maturity = Σ difficulty_weight(mastered) / Σ difficulty_weight(eligible)
    """
    if total_weight_sum == 0:
        return 0.0
    return mastered_weight_sum / total_weight_sum


def compute_combined_maturity(
    cap_maturity: float,
    mat_maturity: float,
    config: EngineConfig = None
) -> float:
    """
    Compute combined maturity score.
    
    maturity = 0.6 * cap_maturity + 0.4 * mat_maturity
    Clamped to [0, 1].
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    maturity = (
        config.maturity_cap_weight * cap_maturity
        + config.maturity_mat_weight * mat_maturity
    )
    return max(0.0, min(1.0, maturity))


def compute_bucket_weights(
    maturity: float,
    config: EngineConfig = None
) -> Dict[Bucket, float]:
    """
    Compute bucket weights based on maturity.
    
    Early learners: more IN_PROGRESS + NEW
    Advanced learners: more MAINTENANCE
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Base curves (tunable)
    w_in_progress = 0.65 - 0.30 * maturity  # 0.65 -> 0.35
    w_maintenance = 0.10 + 0.35 * maturity  # 0.10 -> 0.45
    w_new = 1.0 - w_in_progress - w_maintenance
    
    # Apply minimums
    w_new = max(w_new, config.min_bucket_new)
    w_in_progress = max(w_in_progress, config.min_bucket_in_progress)
    w_maintenance = max(w_maintenance, config.min_bucket_maintenance)
    
    # Normalize to sum to 1
    total = w_new + w_in_progress + w_maintenance
    
    return {
        Bucket.NEW: w_new / total,
        Bucket.IN_PROGRESS: w_in_progress / total,
        Bucket.MAINTENANCE: w_maintenance / total,
    }


def sample_bucket(weights: Dict[Bucket, float]) -> Bucket:
    """Randomly sample a bucket based on weights."""
    r = random.random()
    cumulative = 0.0
    for bucket, weight in weights.items():
        cumulative += weight
        if r < cumulative:
            return bucket
    return Bucket.IN_PROGRESS  # Fallback
