"""
Attempt processing and stats update functions.
"""
from typing import Dict, List, Tuple

from .config import DEFAULT_CONFIG, EngineConfig
from .ema import check_material_mastery, compute_ema
from .models import AttemptResult, CapabilityProgress, MaterialCandidate, MaterialStatus


def process_attempt(
    rating: int,
    material_state: MaterialCandidate,
    teaches_capability_ids: List[int],
    capability_progress: Dict[int, CapabilityProgress],
    is_off_course: bool = False,
    config: EngineConfig = None
) -> AttemptResult:
    """
    Process a practice attempt and return updates.
    
    Updates:
    1. Material EMA and attempt count
    2. Material status
    3. Capability evidence (if not off-course)
    4. Capability mastery
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Update EMA
    new_ema = compute_ema(float(rating), material_state.ema_score, config=config)
    new_attempt_count = material_state.attempt_count + 1
    
    # Update status
    if check_material_mastery(new_ema, new_attempt_count, config):
        new_status = MaterialStatus.MASTERED
    elif new_attempt_count > 0:
        new_status = MaterialStatus.IN_PROGRESS
    else:
        new_status = MaterialStatus.UNEXPLORED
    
    result = AttemptResult(
        new_ema=new_ema,
        new_attempt_count=new_attempt_count,
        new_status=new_status
    )
    
    # Update capability evidence (only if not off-course)
    if not is_off_course:
        for cap_id in teaches_capability_ids:
            cp = capability_progress.get(cap_id)
            if cp and not cp.is_mastered:
                # Check if rating meets acceptance threshold
                # (Using default threshold of 4 if not specified)
                if rating >= 4:
                    result.capability_evidence_added.append(cap_id)
                    
                    # Check if this tips the capability to mastered
                    new_evidence = cp.evidence_count + 1
                    if new_evidence >= cp.required_count:
                        result.capabilities_mastered.append(cap_id)
    
    return result


def update_pitch_focus_stats(
    pitch_midi: int,
    focus_card_id: int,
    rating: int,
    current_ema: float,
    current_attempts: int,
    config: EngineConfig = None
) -> Tuple[float, int]:
    """
    Update pitch/focus stats after an attempt.
    
    Returns (new_ema, new_attempt_count).
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    new_ema = compute_ema(float(rating), current_ema, config=config)
    new_attempts = current_attempts + 1
    
    return new_ema, new_attempts
