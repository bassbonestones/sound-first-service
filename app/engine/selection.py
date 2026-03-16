"""
End-to-end material selection.
"""
from datetime import datetime
from typing import Callable, Dict, List, Optional

from .config import DEFAULT_CONFIG, EngineConfig
from .eligibility import get_hazard_warnings
from .maturity import compute_bucket_weights, compute_capability_maturity, sample_bucket
from .models import Bucket, CapabilityProgress, MaterialCandidate, SessionMaterial
from .ranking import rank_candidates
from .targeting import build_candidate_pool, filter_candidates_by_bucket, select_target_capabilities


def select_material(
    user_masks: List[int],
    capability_progress: List[CapabilityProgress],
    materials_by_teaches: Dict[int, List[int]],
    material_states: Dict[int, MaterialCandidate],
    get_material_masks: Callable[[int], List[int]],
    maturity: Optional[float] = None,
    config: Optional[EngineConfig] = None
) -> Optional[SessionMaterial]:
    """
    End-to-end material selection for a session.
    
    1. Compute maturity (if not provided)
    2. Compute bucket weights
    3. Select target capabilities
    4. Build candidate pool
    5. Sample bucket
    6. Filter candidates by bucket
    7. Rank and select
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Convert to dict for easier lookup
    cap_progress_dict = {cp.capability_id: cp for cp in capability_progress}
    
    # Compute maturity if not provided
    if maturity is None:
        mastered_weight = sum(cp.difficulty_weight for cp in capability_progress if cp.is_mastered)
        total_weight = sum(cp.difficulty_weight for cp in capability_progress)
        maturity = compute_capability_maturity(mastered_weight, total_weight)
    
    # Compute bucket weights
    bucket_weights = compute_bucket_weights(maturity, config)
    
    # Select target capabilities
    targets = select_target_capabilities(capability_progress, config)
    if not targets:
        return None
    
    # Build candidate pool
    pool = build_candidate_pool(
        targets,
        materials_by_teaches,
        material_states,
        user_masks,
        get_material_masks,
        config
    )
    
    if not pool:
        return None
    
    # Try buckets in weighted order
    now = datetime.now()
    for _ in range(3):  # Try up to 3 buckets
        bucket = sample_bucket(bucket_weights)
        candidates = filter_candidates_by_bucket(pool, bucket)
        
        if candidates:
            ranked = rank_candidates(candidates, bucket, cap_progress_dict, now, config, maturity)
            if ranked:
                selected = ranked[0]
                return SessionMaterial(
                    material_id=selected.material_id,
                    bucket=bucket,
                    hazard_warnings=get_hazard_warnings(selected, config),
                    overall_score=selected.overall_score,
                    interaction_bonus=selected.interaction_bonus,
                )
    
    # Fallback: pick anything from pool
    if pool:
        selected = pool[0]
        return SessionMaterial(
            material_id=selected.material_id,
            bucket=Bucket.IN_PROGRESS,
            hazard_warnings=get_hazard_warnings(selected, config),
            overall_score=selected.overall_score,
            interaction_bonus=selected.interaction_bonus,
        )
    
    return None
