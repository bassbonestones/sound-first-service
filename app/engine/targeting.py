"""
Target capability selection and candidate pool building.
"""
import random
from typing import Callable, Dict, List, Set

from .config import DEFAULT_CONFIG, EngineConfig
from .eligibility import check_bitmask_eligibility
from .models import (
    Bucket,
    CapabilityProgress,
    MaterialCandidate,
    MaterialShelf,
    MaterialStatus,
)


def select_target_capabilities(
    capability_progress: List[CapabilityProgress],
    config: EngineConfig = None
) -> List[CapabilityProgress]:
    """
    Select target capabilities for this session.
    
    Prioritize:
    1. Highest progress_ratio (near unlock)
    2. Tie-break by difficulty_weight
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Filter to non-mastered capabilities
    candidates = [cp for cp in capability_progress if not cp.is_mastered]
    
    # Sort by progress ratio (descending), then difficulty weight (descending)
    candidates.sort(
        key=lambda cp: (cp.progress_ratio, cp.difficulty_weight),
        reverse=True
    )
    
    return candidates[:config.target_capability_count]


def build_candidate_pool(
    target_capabilities: List[CapabilityProgress],
    materials_by_teaches: Dict[int, List[int]],
    material_states: Dict[int, MaterialCandidate],
    user_masks: List[int],
    get_material_masks: Callable[[int], List[int]],
    config: EngineConfig = None
) -> List[MaterialCandidate]:
    """
    Build candidate pool by sampling from materials that teach target capabilities.
    
    Never score the full library - only score sampled candidates.
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    pool_ids: Set[int] = set()
    
    for cap in target_capabilities:
        # Get materials that teach this capability
        material_ids = materials_by_teaches.get(cap.capability_id, [])
        
        # Filter to eligible materials
        eligible_ids = []
        for mid in material_ids:
            material_masks = get_material_masks(mid)
            if check_bitmask_eligibility(user_masks, material_masks):
                eligible_ids.append(mid)
        
        # Sample up to candidates_per_capability
        if len(eligible_ids) > config.candidates_per_capability:
            sampled = random.sample(eligible_ids, config.candidates_per_capability)
        else:
            sampled = eligible_ids
        
        pool_ids.update(sampled)
    
    # Cap total pool size
    if len(pool_ids) > config.max_candidates_pool:
        pool_ids = set(random.sample(list(pool_ids), config.max_candidates_pool))
    
    # Convert to MaterialCandidate objects
    pool = []
    for mid in pool_ids:
        if mid in material_states:
            pool.append(material_states[mid])
        else:
            # Create default state if not tracked yet
            pool.append(MaterialCandidate(material_id=mid))
    
    return pool


def filter_candidates_by_bucket(
    candidates: List[MaterialCandidate],
    bucket: Bucket
) -> List[MaterialCandidate]:
    """Filter candidates to those belonging to a specific bucket."""
    result = []
    
    for c in candidates:
        if bucket == Bucket.NEW:
            # Eligible + never attempted
            if c.status == MaterialStatus.UNEXPLORED and c.attempt_count == 0:
                result.append(c)
        elif bucket == Bucket.IN_PROGRESS:
            # Eligible + attempted + not mastered
            if c.status == MaterialStatus.IN_PROGRESS:
                result.append(c)
        elif bucket == Bucket.MAINTENANCE:
            # Eligible + mastered + shelf=MAINTENANCE
            if c.status == MaterialStatus.MASTERED and c.shelf == MaterialShelf.MAINTENANCE:
                result.append(c)
    
    return result
