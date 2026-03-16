"""
Data Loading Helpers

Functions for loading user state, material state, and capability progress from the database.
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any, cast
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.core import Material, FocusCard
from app.models.capability_schema import (
    Capability, MaterialTeachesCapability, MaterialAnalysis,
    UserCapability, UserMaterialState, UserPitchFocusStats, UserComplexityScores
)
from app.practice_engine import (
    MaterialCandidate, CapabilityProgress, MaterialStatus, MaterialShelf
)


def load_user_material_states(db: Session, user_id: int) -> Dict[int, MaterialCandidate]:
    """Load all material states for a user."""
    states = db.query(UserMaterialState).filter(
        UserMaterialState.user_id == user_id
    ).all()
    
    result = {}
    for s in states:
        teaches = db.query(MaterialTeachesCapability.capability_id).filter(
            MaterialTeachesCapability.material_id == s.material_id
        ).all()
        
        analysis = db.query(MaterialAnalysis).filter(
            MaterialAnalysis.material_id == s.material_id
        ).first()
        
        primary_scores: Dict[str, float] = {}
        hazard_scores: Dict[str, float] = {}
        hazard_flags: List[str] = []
        overall_score: Optional[float] = None
        interaction_bonus = 0.0
        difficulty_index = 0.5
        
        if analysis:
            difficulty_index = float(analysis.difficulty_index or 0.5)
            overall_score = float(analysis.overall_score) if analysis.overall_score else None
            interaction_bonus = float(analysis.interaction_bonus or 0.0)
            
            # Build primary_scores, only including non-None values
            score_mapping = [
                ('interval', analysis.interval_primary_score),
                ('rhythm', analysis.rhythm_primary_score),
                ('tonal', analysis.tonal_primary_score),
                ('tempo', analysis.tempo_primary_score),
                ('range', analysis.range_primary_score),
                ('throughput', analysis.throughput_primary_score),
            ]
            for domain, score in score_mapping:
                if score is not None:
                    primary_scores[domain] = float(score)
            
            hazard_scores, hazard_flags = extract_hazard_data(analysis)
        
        result[int(s.material_id)] = MaterialCandidate(
            material_id=int(s.material_id),
            teaches_capabilities=[t[0] for t in teaches],
            difficulty_index=difficulty_index,
            ema_score=float(s.ema_score or 0.0),
            attempt_count=int(s.attempt_count or 0),
            last_attempt_at=s.last_attempt_at,  # type: ignore[arg-type]
            status=MaterialStatus(s.status) if s.status else MaterialStatus.UNEXPLORED,
            shelf=MaterialShelf(s.shelf) if s.shelf else MaterialShelf.DEFAULT,
            overall_score=overall_score,
            primary_scores=primary_scores,
            hazard_scores=hazard_scores,
            interaction_bonus=interaction_bonus,
            hazard_flags=hazard_flags,
        )
    
    return result


def extract_hazard_data(analysis: MaterialAnalysis) -> Tuple[Dict[str, float], List[str]]:
    """Extract hazard scores and flags from analysis JSON columns."""
    hazard_scores: Dict[str, float] = {}
    hazard_flags: List[str] = []
    
    domain_columns = [
        ('interval', analysis.interval_analysis_json),
        ('rhythm', analysis.rhythm_analysis_json),
        ('tonal', analysis.tonal_analysis_json),
        ('tempo', analysis.tempo_analysis_json),
        ('range', analysis.range_analysis_json),
        ('throughput', analysis.throughput_analysis_json),
    ]
    
    for domain, json_str in domain_columns:
        if not json_str:
            continue
        try:
            data = json.loads(cast(str, json_str))
            scores = data.get('scores', {})
            hazard = scores.get('hazard')
            if hazard is not None:
                hazard_scores[domain] = float(hazard)
            
            flags = data.get('flags', [])
            for flag in flags:
                hazard_flags.append(f"{domain}:{flag}")
        except (json.JSONDecodeError, TypeError):
            continue
    
    return hazard_scores, hazard_flags


def load_capability_progress(db: Session, user_id: int, instrument_id: Optional[int] = None) -> List[CapabilityProgress]:
    """Load capability progress for a user, optionally filtered by instrument.
    
    For global capabilities (is_global=True), looks for UserCapability records where instrument_id IS NULL.
    For instrument-specific capabilities (is_global=False), looks for records matching the given instrument_id.
    
    Args:
        db: Database session
        user_id: User ID
        instrument_id: Optional instrument ID. If provided, includes instrument-specific caps for that instrument.
                       If None, only global capabilities are considered.
    """
    capabilities = db.query(Capability).all()
    
    # Build map of capability_id -> UserCapability
    # For global caps: look for UserCapability where instrument_id IS NULL
    # For instrument-specific caps: look for UserCapability where instrument_id matches
    
    user_caps = db.query(UserCapability).filter(
        UserCapability.user_id == user_id
    ).all()
    
    # Build lookup: (capability_id, instrument_id or None) -> UserCapability
    user_cap_map: Dict[Tuple[int, Optional[int]], Any] = {}
    for uc in user_caps:
        if uc.instrument_id is None:
            # Global capability record
            user_cap_map[(int(uc.capability_id), None)] = uc
        else:
            # Instrument-specific capability record
            user_cap_map[(int(uc.capability_id), int(uc.instrument_id))] = uc
    
    result = []
    for cap in capabilities:
        # Determine which UserCapability to use based on whether cap is global
        is_global = cap.is_global if cap.is_global is not None else True
        cap_id = int(cap.id)
        
        if is_global:
            # Look for global record (instrument_id=None)
            uc = user_cap_map.get((cap_id, None))  # type: ignore[assignment]
        else:
            # Look for instrument-specific record
            uc = user_cap_map.get((cap_id, instrument_id)) if instrument_id else None  # type: ignore[assignment]
        
        result.append(CapabilityProgress(
            capability_id=cap_id,
            evidence_count=int(uc.evidence_count) if uc else 0,
            required_count=int(cap.evidence_required_count or 1),
            is_mastered=uc.mastered_at is not None if uc else False,
            difficulty_weight=float(cap.difficulty_weight or 1.0),
        ))
    
    return result


def load_materials_by_teaches(db: Session) -> Dict[int, List[int]]:
    """Build index of materials by capability they teach."""
    teaches = db.query(MaterialTeachesCapability).all()
    
    result: Dict[int, List[int]] = {}
    for t in teaches:
        cap_id = int(t.capability_id)
        if cap_id not in result:
            result[cap_id] = []
        result[cap_id].append(int(t.material_id))
    
    return result


def load_user_ability_scores(db: Session, user_id: int) -> Dict[str, float]:
    """Get user's unified ability scores for eligibility checking."""
    scores = db.query(UserComplexityScores).filter(
        UserComplexityScores.user_id == user_id
    ).first()
    
    if not scores:
        return {
            'interval': 0.0,
            'rhythm': 0.0,
            'tonal': 0.0,
            'tempo': 0.0,
            'range': 0.0,
            'throughput': 0.0,
        }
    
    return {
        'interval': float(scores.interval_ability_score or 0.0),
        'rhythm': float(scores.rhythm_ability_score or 0.0),
        'tonal': float(scores.tonal_ability_score or 0.0),
        'tempo': float(scores.tempo_ability_score or 0.0),
        'range': float(scores.range_ability_score or 0.0),
        'throughput': float(scores.throughput_ability_score or 0.0),
    }


def load_pitch_focus_stats(
    db: Session,
    user_id: int, 
    material_id: Optional[int] = None
) -> Dict[Tuple[int, int], Tuple[float, Optional[datetime]]]:
    """Load pitch/focus stats for a user."""
    query = db.query(UserPitchFocusStats).filter(
        UserPitchFocusStats.user_id == user_id
    )
    
    if material_id:
        query = query.filter(
            and_(
                UserPitchFocusStats.context_type == 'MATERIAL',
                UserPitchFocusStats.context_id == material_id
            )
        )
    else:
        query = query.filter(UserPitchFocusStats.context_type == 'GLOBAL')
    
    stats = query.all()
    
    return {
        (int(s.pitch_midi), int(s.focus_card_id)): (float(s.ema_score or 0.0), s.last_attempt_at)  # type: ignore[misc]
        for s in stats
    }


def load_focus_card_ids(db: Session) -> List[int]:
    """Get all focus card IDs."""
    cards = db.query(FocusCard.id).all()
    return [c[0] for c in cards]
