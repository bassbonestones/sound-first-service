"""
Candidate scoring and ranking functions.
"""
import math
from datetime import datetime
from typing import Dict, List, Optional

from .config import DEFAULT_CONFIG, EngineConfig
from .models import Bucket, CapabilityProgress, MaterialCandidate, MaterialStatus


def compute_fatigue_penalty(
    last_attempt_at: Optional[datetime],
    now: Optional[datetime] = None,
    config: Optional[EngineConfig] = None
) -> float:
    """
    Compute soft fatigue penalty based on recency.
    
    fatiguePenalty = exp(-daysSince / FATIGUE_TAU_DAYS)
    Returns 0 if never attempted.
    """
    if config is None:
        config = DEFAULT_CONFIG
    if now is None:
        now = datetime.now()
    
    if last_attempt_at is None:
        return 0.0
    
    days_since = (now - last_attempt_at).total_seconds() / 86400
    return math.exp(-days_since / config.fatigue_tau_days)


def compute_progress_value(
    candidate: MaterialCandidate,
    capability_progress: Dict[int, CapabilityProgress]
) -> float:
    """
    Compute progress value for a material.
    
    progressValue = max(progress_ratio(cap)) for caps the material teaches
    """
    if not candidate.teaches_capabilities:
        return 0.0
    
    max_progress = 0.0
    for cap_id in candidate.teaches_capabilities:
        cp = capability_progress.get(cap_id)
        if cp and not cp.is_mastered:
            max_progress = max(max_progress, cp.progress_ratio)
    
    return max_progress


def compute_maintenance_value(candidate: MaterialCandidate) -> float:
    """
    Compute maintenance value (prefer weaker mastered items).
    
    maintenanceValue = 1 - normalized_ema
    Where EMA is normalized to 0-1 (from 1-5 scale).
    """
    # Normalize EMA from 1-5 scale to 0-1
    normalized_ema = (candidate.ema_score - 1.0) / 4.0
    normalized_ema = max(0.0, min(1.0, normalized_ema))
    return 1.0 - normalized_ema


def compute_novelty_value(candidate: MaterialCandidate) -> float:
    """Return 1 if unexplored, 0 otherwise."""
    if candidate.status == MaterialStatus.UNEXPLORED:
        return 1.0
    return 0.0


def compute_difficulty_match_value(
    candidate: MaterialCandidate,
    user_maturity: float,
    config: Optional[EngineConfig] = None
) -> float:
    """
    Compute difficulty match value using unified scoring (Phase 6).
    
    Prefer materials whose overall_score aligns with user's maturity level.
    A perfect match is when material difficulty = user maturity.
    
    Returns 0-1 where 1 = perfect match.
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    if candidate.overall_score is None:
        # Fallback to difficulty_index if unified scoring not available
        material_difficulty = candidate.difficulty_index
    else:
        material_difficulty = candidate.overall_score
    
    # Compute how well difficulty matches user maturity
    # Smaller gap = better match
    gap = abs(material_difficulty - user_maturity)
    match_value = max(0.0, 1.0 - gap)
    
    return match_value


def score_candidate(
    candidate: MaterialCandidate,
    bucket: Bucket,
    capability_progress: Dict[int, CapabilityProgress],
    now: Optional[datetime] = None,
    config: Optional[EngineConfig] = None,
    user_maturity: float = 0.5
) -> float:
    """
    Score a candidate based on its bucket.
    
    Base formulas:
    NEW: 1.0*progressValue + 0.5*noveltyValue - 0.3*fatiguePenalty
    IN_PROGRESS: 1.0*progressValue + 0.8*maintenanceValue - 0.3*fatiguePenalty
    MAINTENANCE: 0.6*maintenanceValue + 0.3*progressValue - 0.3*fatiguePenalty
    
    Plus unified scoring bonus (Phase 6):
    + ranking_overall_score_weight * difficultyMatchValue
    + ranking_interaction_bonus_weight * interactionBonus
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    progress_val = compute_progress_value(candidate, capability_progress)
    maintenance_val = compute_maintenance_value(candidate)
    novelty_val = compute_novelty_value(candidate)
    fatigue_pen = compute_fatigue_penalty(candidate.last_attempt_at, now, config)
    
    # Base score by bucket
    if bucket == Bucket.NEW:
        base_score = 1.0 * progress_val + 0.5 * novelty_val - 0.3 * fatigue_pen
    elif bucket == Bucket.IN_PROGRESS:
        base_score = 1.0 * progress_val + 0.8 * maintenance_val - 0.3 * fatigue_pen
    else:  # MAINTENANCE
        base_score = 0.6 * maintenance_val + 0.3 * progress_val - 0.3 * fatigue_pen
    
    # Add unified scoring bonus (Phase 6)
    difficulty_match = compute_difficulty_match_value(candidate, user_maturity, config)
    unified_bonus = (
        config.ranking_overall_score_weight * difficulty_match
        + config.ranking_interaction_bonus_weight * candidate.interaction_bonus
    )
    
    return base_score + unified_bonus


def rank_candidates(
    candidates: List[MaterialCandidate],
    bucket: Bucket,
    capability_progress: Dict[int, CapabilityProgress],
    now: Optional[datetime] = None,
    config: Optional[EngineConfig] = None,
    user_maturity: float = 0.5
) -> List[MaterialCandidate]:
    """Rank candidates by score within a bucket."""
    scored = [
        (c, score_candidate(c, bucket, capability_progress, now, config, user_maturity))
        for c in candidates
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored]
