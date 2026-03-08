"""
Attempt Processing Handlers

Functions for recording practice attempts and updating related state.
"""

import json
from datetime import datetime
from typing import Optional, Dict
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.core import User, PracticeAttempt
from app.models.capability_schema import (
    Capability, MaterialTeachesCapability, MaterialAnalysis,
    UserCapability, UserMaterialState, UserPitchFocusStats,
    UserCapabilityEvidenceEvent, UserSoftGateState, UserComplexityScores
)
from app.practice_engine import (
    EngineConfig, MaterialCandidate, CapabilityProgress, MaterialStatus,
    AttemptResult, process_attempt, compute_ema
)
from app.scoring_functions import score_to_stage


def handle_record_attempt(
    db: Session,
    config: EngineConfig,
    user_id: int,
    material_id: int,
    rating: int,
    cap_progress_dict: Dict[int, CapabilityProgress],
    focus_card_id: Optional[int] = None,
    pitch_midi: Optional[int] = None,
    is_off_course: bool = False,
    key: Optional[str] = None,
    fatigue: Optional[int] = None
) -> AttemptResult:
    """
    Record a practice attempt and update all relevant stats.
    
    This is the core attempt processing logic.
    """
    now = datetime.now()
    
    # Get or create material state
    state = db.query(UserMaterialState).filter(
        and_(
            UserMaterialState.user_id == user_id,
            UserMaterialState.material_id == material_id
        )
    ).first()
    
    if not state:
        state = UserMaterialState(
            user_id=user_id,
            material_id=material_id,
            ema_score=0.0,
            attempt_count=0,
            status='UNEXPLORED',
            shelf='DEFAULT'
        )
        db.add(state)
    
    # Get teaches capabilities
    teaches = db.query(MaterialTeachesCapability.capability_id).filter(
        MaterialTeachesCapability.material_id == material_id
    ).all()
    teaches_ids = [t[0] for t in teaches]
    
    # Create MaterialCandidate for processing
    candidate = MaterialCandidate(
        material_id=material_id,
        ema_score=state.ema_score or 0.0,
        attempt_count=state.attempt_count or 0,
        status=MaterialStatus(state.status) if state.status else MaterialStatus.UNEXPLORED
    )
    
    # Process the attempt
    result = process_attempt(
        rating=rating,
        material_state=candidate,
        teaches_capability_ids=teaches_ids,
        capability_progress=cap_progress_dict,
        is_off_course=is_off_course,
        config=config
    )
    
    # Detect material mastery transition
    was_mastered = (candidate.status == MaterialStatus.MASTERED)
    is_now_mastered = (result.new_status == MaterialStatus.MASTERED)
    material_newly_mastered = is_now_mastered and not was_mastered
    
    # Update material state
    state.ema_score = result.new_ema
    state.attempt_count = result.new_attempt_count
    state.last_attempt_at = now
    state.status = result.new_status.value
    
    if is_off_course:
        state.manual_attempt_count = (state.manual_attempt_count or 0) + 1
    else:
        state.guided_attempt_count = (state.guided_attempt_count or 0) + 1
    
    # Record practice attempt
    attempt = PracticeAttempt(
        user_id=user_id,
        material_id=material_id,
        key=key,
        focus_card_id=focus_card_id,
        rating=rating,
        fatigue=fatigue,
        timestamp=now,
        is_off_course=is_off_course,
        was_eligible=not is_off_course
    )
    db.add(attempt)
    db.flush()
    
    # Update capability evidence
    update_capability_evidence(db, user_id, material_id, attempt.id, rating, 
                               result.capability_evidence_added, is_off_course, now)
    
    # Update capability mastery
    update_capability_mastery(db, user_id, result.capabilities_mastered, now)
    
    # Update user ability scores if material newly mastered
    if material_newly_mastered:
        update_user_ability_scores(db, user_id, material_id)
    
    # Update pitch/focus stats if provided
    if focus_card_id and pitch_midi:
        update_pitch_focus_stats(db, config, user_id, focus_card_id, pitch_midi, 
                                 rating, material_id, now)
    
    return result


def update_capability_evidence(
    db: Session,
    user_id: int,
    material_id: int,
    attempt_id: int,
    rating: int,
    capability_ids: list,
    is_off_course: bool,
    now: datetime
):
    """Update capability evidence from an attempt."""
    for cap_id in capability_ids:
        event = UserCapabilityEvidenceEvent(
            user_id=user_id,
            capability_id=cap_id,
            material_id=material_id,
            practice_attempt_id=attempt_id,
            rating=rating,
            credited_at=now,
            is_off_course=is_off_course
        )
        db.add(event)
        
        user_cap = db.query(UserCapability).filter(
            and_(
                UserCapability.user_id == user_id,
                UserCapability.capability_id == cap_id
            )
        ).first()
        
        if user_cap:
            user_cap.evidence_count = (user_cap.evidence_count or 0) + 1


def update_capability_mastery(db: Session, user_id: int, capability_ids: list, now: datetime):
    """Update mastery status for capabilities."""
    for cap_id in capability_ids:
        cap = db.query(Capability).get(cap_id)
        if not cap:
            continue
        
        # Check soft gate requirements
        if not check_soft_gate_requirements(db, user_id, cap):
            continue
        
        user_cap = db.query(UserCapability).filter(
            and_(
                UserCapability.user_id == user_id,
                UserCapability.capability_id == cap_id
            )
        ).first()
        
        if user_cap and not user_cap.mastered_at:
            user_cap.mastered_at = now
            
            if cap.bit_index is not None:
                set_user_capability_bit(db, user_id, cap.bit_index)


def check_soft_gate_requirements(db: Session, user_id: int, capability: Capability) -> bool:
    """Check if user meets soft gate requirements for a capability."""
    if not capability.soft_gate_requirements:
        return True
    
    try:
        requirements = json.loads(capability.soft_gate_requirements)
        if not isinstance(requirements, dict):
            return True
    except (json.JSONDecodeError, TypeError):
        return True
    
    for dimension_name, threshold in requirements.items():
        state = db.query(UserSoftGateState).filter(
            and_(
                UserSoftGateState.user_id == user_id,
                UserSoftGateState.dimension_name == dimension_name
            )
        ).first()
        
        comfortable_value = state.comfortable_value if state else 0.0
        if comfortable_value < threshold:
            return False
    
    return True


def set_user_capability_bit(db: Session, user_id: int, bit_index: int):
    """Set a capability bit on the user's mask."""
    user = db.query(User).get(user_id)
    if not user:
        return
    
    mask_idx = bit_index // 64
    bit_pos = bit_index % 64
    
    mask_attrs = [
        'cap_mask_0', 'cap_mask_1', 'cap_mask_2', 'cap_mask_3',
        'cap_mask_4', 'cap_mask_5', 'cap_mask_6', 'cap_mask_7'
    ]
    
    if 0 <= mask_idx < len(mask_attrs):
        current = getattr(user, mask_attrs[mask_idx]) or 0
        setattr(user, mask_attrs[mask_idx], current | (1 << bit_pos))


def update_user_ability_scores(db: Session, user_id: int, material_id: int):
    """Update user's unified ability scores when a material is mastered."""
    analysis = db.query(MaterialAnalysis).filter(
        MaterialAnalysis.material_id == material_id
    ).first()
    
    if not analysis:
        return
    
    scores = db.query(UserComplexityScores).filter(
        UserComplexityScores.user_id == user_id
    ).first()
    
    if not scores:
        scores = UserComplexityScores(user_id=user_id)
        db.add(scores)
    
    domains = [
        (analysis.interval_primary_score, 'interval_ability_score', 'interval_demonstrated_stage'),
        (analysis.rhythm_primary_score, 'rhythm_ability_score', 'rhythm_demonstrated_stage'),
        (analysis.tonal_primary_score, 'tonal_ability_score', 'tonal_demonstrated_stage'),
        (analysis.tempo_primary_score, 'tempo_ability_score', 'tempo_demonstrated_stage'),
        (analysis.range_primary_score, 'range_ability_score', 'range_demonstrated_stage'),
        (analysis.throughput_primary_score, 'throughput_ability_score', 'throughput_demonstrated_stage'),
    ]
    
    for material_score, ability_col, stage_col in domains:
        if material_score is None:
            continue
        
        current_ability = getattr(scores, ability_col) or 0.0
        new_ability = max(current_ability, material_score)
        
        if new_ability > current_ability:
            setattr(scores, ability_col, new_ability)
            setattr(scores, stage_col, score_to_stage(new_ability))
    
    scores.updated_at = datetime.now()


def update_pitch_focus_stats(
    db: Session,
    config: EngineConfig,
    user_id: int,
    focus_card_id: int,
    pitch_midi: int,
    rating: int,
    material_id: int,
    now: datetime
):
    """Update pitch/focus stats for material and global contexts."""
    contexts = [
        ('MATERIAL', material_id),
        ('GLOBAL', 0),
    ]
    
    for context_type, context_id in contexts:
        stat = db.query(UserPitchFocusStats).filter(
            and_(
                UserPitchFocusStats.user_id == user_id,
                UserPitchFocusStats.pitch_midi == pitch_midi,
                UserPitchFocusStats.focus_card_id == focus_card_id,
                UserPitchFocusStats.context_type == context_type,
                UserPitchFocusStats.context_id == context_id
            )
        ).first()
        
        if not stat:
            stat = UserPitchFocusStats(
                user_id=user_id,
                pitch_midi=pitch_midi,
                focus_card_id=focus_card_id,
                context_type=context_type,
                context_id=context_id,
                ema_score=0.0,
                attempt_count=0
            )
            db.add(stat)
        
        stat.ema_score = compute_ema(float(rating), stat.ema_score or 0.0, config=config)
        stat.attempt_count = (stat.attempt_count or 0) + 1
        stat.last_attempt_at = now


def pitch_name_to_midi(pitch_name: str) -> int:
    """Convert pitch name like 'C4' to MIDI number."""
    if not pitch_name:
        return 60
    
    note_map = {
        'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11
    }
    
    pitch_name = pitch_name.upper().strip()
    
    note = pitch_name[0]
    idx = 1
    accidental = 0
    
    while idx < len(pitch_name) and pitch_name[idx] in '#bB':
        if pitch_name[idx] == '#':
            accidental += 1
        elif pitch_name[idx].lower() == 'b':
            accidental -= 1
        idx += 1
    
    try:
        octave = int(pitch_name[idx:])
    except:
        octave = 4
    
    base = note_map.get(note, 0)
    return (octave + 1) * 12 + base + accidental
