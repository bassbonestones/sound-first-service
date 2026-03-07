"""
EMA and mastery calculation functions.
"""
from .config import DEFAULT_CONFIG, EngineConfig


def compute_ema(
    current_score: float,
    previous_ema: float,
    alpha: float = None,
    config: EngineConfig = None
) -> float:
    """
    Compute exponential moving average.
    
    EMA_new = alpha * current_score + (1 - alpha) * EMA_previous
    """
    if config is None:
        config = DEFAULT_CONFIG
    if alpha is None:
        alpha = config.ema_alpha
    
    return alpha * current_score + (1 - alpha) * previous_ema


def check_material_mastery(
    ema_score: float,
    attempt_count: int,
    config: EngineConfig = None
) -> bool:
    """
    Check if material is mastered based on EMA + minimum attempts gate.
    
    mastered = attempt_count >= MIN_ATTEMPTS AND ema_score >= MASTERY_THRESHOLD
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    return (
        attempt_count >= config.min_attempts_for_mastery
        and ema_score >= config.mastery_threshold
    )


def check_capability_mastery(
    evidence_count: int,
    required_count: int,
    distinct_materials_required: bool = False,
    distinct_material_count: int = 0
) -> bool:
    """
    Check if capability is mastered based on evidence profile.
    
    For simple count: evidence_count >= required_count
    For distinct materials: also check distinct_material_count >= required_count
    """
    if distinct_materials_required:
        return distinct_material_count >= required_count
    return evidence_count >= required_count
