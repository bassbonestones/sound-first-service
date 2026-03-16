"""
Eligibility checking functions for material selection.
"""
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

from .config import DEFAULT_CONFIG, EngineConfig
from .models import Bucket

if TYPE_CHECKING:
    from .models import MaterialCandidate


def check_bitmask_eligibility(
    user_masks: List[int],
    material_masks: List[int]
) -> bool:
    """
    Fast O(1) check for capability eligibility using bitmasks.
    
    Returns True if every required capability bit is set in user's mask.
    """
    for i in range(min(len(user_masks), len(material_masks))):
        # If any required bit is NOT in user's mask, not eligible
        if (material_masks[i] & ~user_masks[i]) != 0:
            return False
    return True


def check_content_dimension_eligibility(
    material_stages: Dict[str, int],
    user_max_stages: Dict[str, int]
) -> bool:
    """
    Check if material's content dimensions are within user's caps.
    
    material_stages: e.g., {'rhythm_complexity_stage': 3, 'range_usage_stage': 2}
    user_max_stages: e.g., {'rhythm_complexity_stage': 4, 'range_usage_stage': 3}
    """
    for dimension, stage in material_stages.items():
        if stage is None:
            continue
        max_stage = user_max_stages.get(dimension)
        if max_stage is not None and stage > max_stage:
            return False
    return True


def is_material_eligible(
    user_masks: List[int],
    material_masks: List[int],
    material_stages: Optional[Dict[str, int]] = None,
    user_max_stages: Optional[Dict[str, int]] = None,
    has_license: bool = True
) -> bool:
    """
    Single source of truth for material eligibility (guided mode).
    
    Checks:
    1. License/access
    2. Capability bitmasks
    3. Content dimension caps
    """
    if not has_license:
        return False
    
    if not check_bitmask_eligibility(user_masks, material_masks):
        return False
    
    if material_stages and user_max_stages:
        if not check_content_dimension_eligibility(material_stages, user_max_stages):
            return False
    
    return True


def check_unified_score_eligibility(
    material_candidate: 'MaterialCandidate',
    user_ability_scores: Dict[str, float],
    bucket: Optional['Bucket'] = None,
    config: Optional[EngineConfig] = None
) -> Tuple[bool, List[str]]:
    """
    Check eligibility based on unified scoring (Phase 6).
    
    Returns:
        (is_eligible, list_of_blocking_reasons)
    
    Checks:
    1. Primary score delta: material's primary scores should not exceed
       user's ability scores by more than max_primary_score_delta.
    2. Hazard cap: material's hazard scores should not exceed max_hazard_score
       (relaxed for maintenance bucket).
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    if not config.use_unified_score_eligibility:
        return True, []
    
    blocking_reasons = []
    
    # Get hazard tolerance (relaxed for maintenance)
    if bucket == Bucket.MAINTENANCE:
        hazard_cap = config.hazard_tolerance_maintenance
    else:
        hazard_cap = config.max_hazard_score
    
    # Check primary score deltas
    for domain, material_score in material_candidate.primary_scores.items():
        if material_score is None:
            continue
        
        user_score = user_ability_scores.get(domain, 0.0)
        delta = material_score - user_score
        
        if delta > config.max_primary_score_delta:
            blocking_reasons.append(
                f"{domain}_too_hard: material={material_score:.2f}, user={user_score:.2f}, delta={delta:.2f}"
            )
    
    # Check hazard scores
    for domain, hazard_score in material_candidate.hazard_scores.items():
        if hazard_score is None:
            continue
        
        if hazard_score > hazard_cap:
            blocking_reasons.append(
                f"{domain}_hazard_too_high: {hazard_score:.2f} > {hazard_cap:.2f}"
            )
    
    return len(blocking_reasons) == 0, blocking_reasons


def get_hazard_warnings(
    material_candidate: 'MaterialCandidate',
    config: Optional[EngineConfig] = None
) -> List[str]:
    """
    Get hazard warnings for a material (informational, not blocking).
    
    Returns flags and high hazard scores that teachers/UI should surface.
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    warnings = list(material_candidate.hazard_flags)  # Copy existing flags
    
    # Add warnings for moderately high hazard scores
    warn_threshold = config.max_hazard_score * 0.8  # 80% of blocking threshold
    for domain, hazard_score in material_candidate.hazard_scores.items():
        if hazard_score is None:
            continue
        if hazard_score >= warn_threshold:
            warnings.append(f"{domain}_elevated_hazard: {hazard_score:.2f}")
    
    return warnings
