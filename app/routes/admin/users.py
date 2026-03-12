"""Admin user progression and diagnostics endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
import datetime
import random

from app.db import get_db
from app.schemas.admin_users_schemas import (
    UserProgressionResponse, SessionCandidatesResponse, DiagnosticSessionResponse,
    LastSessionDiagnosticsResponse, UserInfoUpdateResponse, AvailableCapabilitiesResponse,
    CapabilityAddResponse, CapabilityRemoveResponse, CapabilityToggleMasteryResponse,
    AllSoftGatesResponse, SoftGateUpdateResponse, UserResetResponse, GrantDay0Response,
)
from app.models.core import User, Material, FocusCard, PracticeSession, MiniSession, PracticeAttempt
from app.models.capability_schema import (
    Capability, UserCapability, SoftGateRule, UserSoftGateState,
    MaterialCapability, MaterialAnalysis, UserMaterialState, UserInstrument
)
from app.models.teaching_module import UserLessonProgress, UserModuleProgress
from app.curriculum import (
    filter_materials_by_capabilities,
    filter_materials_by_range,
    select_key_for_mini_session,
)
from app.services.user_service import UserService, DAY0_BASE_CAPABILITIES


router = APIRouter(tags=["admin-users"])


# ============ Pydantic Models for Edits ============

class UserInfoUpdate(BaseModel):
    """Update user basic info."""
    instrument: Optional[str] = None
    resonant_note: Optional[str] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None
    day0_completed: Optional[bool] = None
    day0_stage: Optional[int] = None


class SoftGateUpdate(BaseModel):
    """Update a single soft gate state."""
    comfortable_value: Optional[float] = None
    max_demonstrated_value: Optional[float] = None
    frontier_success_ema: Optional[float] = None
    frontier_attempt_count_since_last_promo: Optional[int] = None


class CapabilityAdd(BaseModel):
    """Add a capability to user."""
    capability_id: int
    mastered: bool = False
    instrument_id: Optional[int] = None  # None for global caps, set for instrument-specific


@router.get("/users/{user_id}/progression", response_model=UserProgressionResponse)
def admin_get_user_progression(user_id: int, instrument_id: Optional[int] = None, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get comprehensive user progression data.
    
    Args:
        user_id: User ID
        instrument_id: If provided, filters capabilities to show:
                       - Global capabilities (instrument_id IS NULL)
                       - Instrument-specific capabilities for this instrument
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Load user's instruments
    instruments = db.query(UserInstrument).filter(UserInstrument.user_id == user_id).all()
    
    # Build capability query
    cap_query = db.query(UserCapability, Capability).join(
        Capability, UserCapability.capability_id == Capability.id
    ).filter(UserCapability.user_id == user_id, UserCapability.is_active == True)
    
    # If instrument_id specified, filter to global + that instrument's caps
    if instrument_id is not None:
        from sqlalchemy import or_
        cap_query = cap_query.filter(
            or_(
                UserCapability.instrument_id == None,  # Global caps
                UserCapability.instrument_id == instrument_id  # This instrument's caps
            )
        )
    
    user_caps = cap_query.all()
    
    mastered = []
    introduced = []
    for user_cap, cap in user_caps:
        cap_data = {
            "id": cap.id, "name": cap.name, "display_name": cap.display_name, "domain": cap.domain,
            "introduced_at": user_cap.introduced_at.isoformat() if user_cap.introduced_at else None,
            "mastered_at": user_cap.mastered_at.isoformat() if user_cap.mastered_at else None,
            "evidence_count": user_cap.evidence_count,
            "is_global": cap.is_global if hasattr(cap, 'is_global') else True,
            "instrument_id": user_cap.instrument_id,
        }
        if user_cap.mastered_at:
            mastered.append(cap_data)
        else:
            introduced.append(cap_data)
    
    from datetime import timedelta
    recent_date = datetime.datetime.now() - timedelta(days=7)
    recent_promotions = [
        {"capability_name": c["name"], "promoted_at": c["mastered_at"]}
        for c in mastered if c["mastered_at"] and c["mastered_at"] > recent_date.isoformat()
    ]
    
    soft_gates = db.query(UserSoftGateState).filter_by(user_id=user_id).all()
    soft_gate_data = [{
        "dimension_name": sg.dimension_name, "comfortable_value": sg.comfortable_value,
        "max_demonstrated_value": sg.max_demonstrated_value, "frontier_success_ema": sg.frontier_success_ema,
        "frontier_attempt_count_since_last_promo": sg.frontier_attempt_count_since_last_promo,
    } for sg in soft_gates]
    
    materials_completed = db.query(UserMaterialState).filter_by(user_id=user_id, status="MASTERED").count()
    
    # Format instruments list
    instruments_data = [{
        "id": inst.id,
        "instrument_name": inst.instrument_name,
        "is_primary": inst.is_primary,
        "clef": inst.clef,
        "resonant_note": inst.resonant_note,
        "range_low": inst.range_low,
        "range_high": inst.range_high,
        "day0_completed": inst.day0_completed,
        "day0_stage": inst.day0_stage,
    } for inst in instruments]
    
    return {
        "user": {
            "id": user.id, "email": user.email, "instrument": user.instrument,
            "resonant_note": user.resonant_note, "range_low": user.range_low, "range_high": user.range_high,
            "day0_completed": getattr(user, "day0_completed", False), "day0_stage": getattr(user, "day0_stage", 0),
        },
        "instruments": instruments_data,
        "capabilities": {"mastered": mastered, "introduced": introduced, "recent_promotions": recent_promotions},
        "soft_gates": soft_gate_data,
        "journey": {"stage": "learning", "capabilities_mastered": len(mastered), "materials_completed": materials_completed},
    }


@router.get("/users/{user_id}/session-candidates", response_model=SessionCandidatesResponse)
def admin_get_session_candidates(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get the candidate pool of materials for the next session."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    materials = db.query(Material).all()
    mastered_caps = db.query(UserCapability).filter_by(user_id=user_id, is_active=True).filter(UserCapability.mastered_at != None).all()
    mastered_cap_ids = {uc.capability_id for uc in mastered_caps}
    
    soft_rules = {r.dimension_name: r for r in db.query(SoftGateRule).all()}
    soft_states = {s.dimension_name: s for s in db.query(UserSoftGateState).filter_by(user_id=user_id).all()}
    
    eligible_materials = []
    ineligible_sample = []
    
    for mat in materials:
        req_caps = db.query(MaterialCapability).filter_by(material_id=mat.id, is_required=True).all()
        missing_caps = [rc.capability_id for rc in req_caps if rc.capability_id not in mastered_cap_ids]
        
        if missing_caps:
            missing_names = db.query(Capability.name).filter(Capability.id.in_(missing_caps)).all()
            missing_names = [n[0] for n in missing_names]
            
            if len(ineligible_sample) < 20:
                ineligible_sample.append({"id": mat.id, "title": mat.title, "ineligibility_reason": f"Missing capabilities: {', '.join(missing_names[:3])}"})
            continue
        
        analysis = db.query(MaterialAnalysis).filter_by(material_id=mat.id).first()
        soft_failure = None
        
        if analysis:
            dimension_mapping = {
                "tonal_complexity_stage": analysis.tonal_complexity_stage,
                "interval_size_stage": analysis.interval_size_stage,
                "interval_sustained_stage": analysis.interval_sustained_stage,
                "interval_hazard_stage": analysis.interval_hazard_stage,
                "rhythm_complexity_stage": analysis.rhythm_complexity_stage,
                "range_usage_stage": analysis.range_usage_stage,
            }
            
            for dim_name, mat_value in dimension_mapping.items():
                if mat_value is None:
                    continue
                rule = soft_rules.get(dim_name)
                state = soft_states.get(dim_name)
                
                if rule:
                    comfort = state.comfortable_value if state else 0
                    max_allowed = comfort + rule.frontier_buffer
                    if mat_value > max_allowed:
                        soft_failure = f"{dim_name} too high ({mat_value} > {max_allowed})"
                        break
        
        if soft_failure:
            if len(ineligible_sample) < 20:
                ineligible_sample.append({"id": mat.id, "title": mat.title, "ineligibility_reason": soft_failure})
            continue
        
        eligible_materials.append({"id": mat.id, "title": mat.title, "eligibility_reason": "Passes all gates"})
    
    return {
        "user_id": user_id, "eligible_materials": eligible_materials, "eligible_count": len(eligible_materials),
        "ineligible_sample": ineligible_sample, "total_materials": len(materials),
    }


@router.post("/users/{user_id}/generate-diagnostic-session", response_model=DiagnosticSessionResponse)
def admin_generate_diagnostic_session(user_id: int, duration_minutes: int = 30, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Generate a practice session with detailed diagnostics."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    diagnostics = {
        "target_capabilities": [], "hard_gates": [], "soft_envelope_filters": [],
        "candidates_considered": 0, "candidate_ranking": [], "selection_reasons": [],
    }
    
    soft_states = db.query(UserSoftGateState).filter_by(user_id=user_id).all()
    soft_rules = db.query(SoftGateRule).all()
    
    for rule in soft_rules:
        state = next((s for s in soft_states if s.dimension_name == rule.dimension_name), None)
        comfort = state.comfortable_value if state else 0
        max_allowed = comfort + rule.frontier_buffer
        diagnostics["soft_envelope_filters"].append({
            "dimension": rule.dimension_name, "comfort": comfort, "max_allowed": max_allowed, "frontier_buffer": rule.frontier_buffer,
        })
    
    all_caps = db.query(Capability).order_by(Capability.bit_index).limit(10).all()
    diagnostics["target_capabilities"] = [{"name": c.name, "weight": c.difficulty_weight or 1.0} for c in all_caps]
    
    diagnostics["hard_gates"] = [
        "User must have mastered all required capabilities",
        "Material must be within user's pitch range",
        "Capability prerequisites must be met",
    ]
    
    try:
        eligible = filter_materials_by_capabilities(db.query(Material).all(), db, user_id)
        eligible = filter_materials_by_range(eligible, user.range_low, user.range_high)
        diagnostics["candidates_considered"] = len(eligible)
        
        for i, mat in enumerate(eligible[:10]):
            diagnostics["candidate_ranking"].append({"title": mat.title, "score": 1.0 - (i * 0.1), "reason": "Selected by standard algorithm"})
        
        practice_session = PracticeSession(user_id=user_id, started_at=datetime.datetime.now(), practice_mode="guided")
        db.add(practice_session)
        db.flush()
        
        mini_sessions_out = []
        focus_cards = db.query(FocusCard).all()
        
        for i, material in enumerate(eligible[:3]):
            focus_card = random.choice(focus_cards) if focus_cards else None
            target_key = select_key_for_mini_session(material, user, db)
            
            mini_session = MiniSession(
                practice_session_id=practice_session.id, material_id=material.id, key=target_key,
                focus_card_id=focus_card.id if focus_card else None, goal_type="Accuracy"
            )
            db.add(mini_session)
            db.flush()
            
            mini_sessions_out.append({
                "material_id": material.id, "material_title": material.title,
                "focus_card_id": focus_card.id if focus_card else None, "focus_card_name": focus_card.name if focus_card else "None",
                "goal_type": "Accuracy", "target_key": target_key,
            })
            diagnostics["selection_reasons"].append({"material": material.title, "reason": f"Ranked #{i+1} in candidate pool"})
        
        db.commit()
        
        return {
            "session": {"session_id": practice_session.id, "user_id": user_id, "planned_duration_minutes": duration_minutes, "mini_sessions": mini_sessions_out},
            "diagnostics": diagnostics,
        }
    except Exception as e:
        db.rollback()
        return {"session": None, "diagnostics": diagnostics, "error": str(e)}


@router.get("/users/{user_id}/last-session-diagnostics", response_model=LastSessionDiagnosticsResponse)
def admin_get_last_session_diagnostics(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get diagnostics for the user's last practice session."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    last_session = db.query(PracticeSession).filter_by(user_id=user_id).order_by(PracticeSession.started_at.desc()).first()
    
    if not last_session:
        return {"session": None, "diagnostics": {"message": "No sessions found"}}
    
    mini_sessions = db.query(MiniSession).filter_by(practice_session_id=last_session.id).all()
    
    mini_session_data = []
    for mini in mini_sessions:
        mat = db.query(Material).filter_by(id=mini.material_id).first()
        focus = db.query(FocusCard).filter_by(id=mini.focus_card_id).first() if mini.focus_card_id else None
        
        mini_session_data.append({
            "material_id": mini.material_id, "material_title": mat.title if mat else "Unknown",
            "target_key": mini.key, "focus_card_id": mini.focus_card_id, "focus_card_name": focus.name if focus else "None",
            "goal_type": mini.goal_type, "is_completed": mini.is_completed,
        })
    
    return {
        "session": {
            "session_id": last_session.id, "user_id": user_id,
            "started_at": last_session.started_at.isoformat() if last_session.started_at else None,
            "ended_at": last_session.ended_at.isoformat() if last_session.ended_at else None,
            "practice_mode": last_session.practice_mode, "mini_sessions": mini_session_data,
        },
        "diagnostics": {"message": "Retrieved from database (live diagnostics not available for past sessions)", "mini_session_count": len(mini_session_data)},
    }


# ============ User Edit Endpoints ============

@router.put("/users/{user_id}/info", response_model=UserInfoUpdateResponse)
def admin_update_user_info(user_id: int, update: UserInfoUpdate, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Update user basic information (range, resonant note, day0 status)."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    changes = []
    
    if update.instrument is not None:
        old = user.instrument
        user.instrument = update.instrument
        changes.append(f"instrument: {old} -> {update.instrument}")
    
    if update.resonant_note is not None:
        old = user.resonant_note
        user.resonant_note = update.resonant_note
        changes.append(f"resonant_note: {old} -> {update.resonant_note}")
    
    if update.range_low is not None:
        old = user.range_low
        user.range_low = update.range_low
        changes.append(f"range_low: {old} -> {update.range_low}")
    
    if update.range_high is not None:
        old = user.range_high
        user.range_high = update.range_high
        changes.append(f"range_high: {old} -> {update.range_high}")
    
    if update.day0_completed is not None:
        old = getattr(user, "day0_completed", None)
        user.day0_completed = update.day0_completed
        changes.append(f"day0_completed: {old} -> {update.day0_completed}")
    
    if update.day0_stage is not None:
        old = getattr(user, "day0_stage", None)
        user.day0_stage = update.day0_stage
        changes.append(f"day0_stage: {old} -> {update.day0_stage}")
    
    db.commit()
    
    return {"success": True, "changes": changes}


@router.get("/users/{user_id}/capabilities/available", response_model=AvailableCapabilitiesResponse)
def admin_get_available_capabilities(user_id: int, instrument_id: Optional[int] = None, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get all capabilities, marking which the user has.
    
    Args:
        user_id: User ID
        instrument_id: If provided, shows whether user has instrument-specific caps for this instrument
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    all_caps = db.query(Capability).order_by(Capability.domain, Capability.name).all()
    
    # Get user capabilities - for global caps check NULL instrument_id, for instrument-specific check the given instrument
    user_caps_query = db.query(UserCapability).filter_by(user_id=user_id, is_active=True)
    user_caps_list = user_caps_query.all()
    
    # Build lookup: for global caps key by (cap_id, None), for instrument-specific key by (cap_id, instrument_id)
    user_caps = {}
    for uc in user_caps_list:
        user_caps[(uc.capability_id, uc.instrument_id)] = uc
    
    result = []
    for cap in all_caps:
        is_global = cap.is_global if hasattr(cap, 'is_global') else True
        
        # For global caps, look for instrument_id=None; for instrument-specific, use provided instrument_id
        if is_global:
            user_cap = user_caps.get((cap.id, None))
        else:
            user_cap = user_caps.get((cap.id, instrument_id)) if instrument_id else None
        
        result.append({
            "id": cap.id,
            "name": cap.name,
            "display_name": cap.display_name,
            "domain": cap.domain,
            "is_global": is_global,
            "user_has": user_cap is not None,
            "mastered": user_cap.mastered_at is not None if user_cap else False,
            "evidence_count": user_cap.evidence_count if user_cap else 0,
        })
    
    return {"capabilities": result}


@router.post("/users/{user_id}/capabilities", response_model=CapabilityAddResponse)
def admin_add_user_capability(user_id: int, data: CapabilityAdd, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Add a capability to a user.
    
    For global capabilities (is_global=True), instrument_id should be None.
    For instrument-specific capabilities, instrument_id should be set.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cap = db.query(Capability).filter_by(id=data.capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    is_global = cap.is_global if hasattr(cap, 'is_global') else True
    
    # Determine the instrument_id to use
    # For global caps, always use None
    # For instrument-specific, use provided instrument_id (required)
    if is_global:
        target_instrument_id = None
    else:
        if data.instrument_id is None:
            raise HTTPException(
                status_code=400, 
                detail=f"Capability '{cap.name}' is instrument-specific. Please provide instrument_id."
            )
        target_instrument_id = data.instrument_id
    
    # Check if already exists with same instrument_id
    existing = db.query(UserCapability).filter_by(
        user_id=user_id, 
        capability_id=data.capability_id,
        instrument_id=target_instrument_id
    ).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            if data.mastered:
                existing.mastered_at = datetime.datetime.now()
            db.commit()
            return {"success": True, "message": "Capability reactivated"}
        else:
            return {"success": False, "message": "User already has this capability"}
    
    # Create new
    user_cap = UserCapability(
        user_id=user_id,
        capability_id=data.capability_id,
        instrument_id=target_instrument_id,
        is_active=True,
        introduced_at=datetime.datetime.now(),
        mastered_at=datetime.datetime.now() if data.mastered else None,
        evidence_count=1 if data.mastered else 0,
    )
    db.add(user_cap)
    db.commit()
    
    return {"success": True, "message": f"Added capability: {cap.name}"}


@router.delete("/users/{user_id}/capabilities/{capability_id}", response_model=CapabilityRemoveResponse)
def admin_remove_user_capability(
    user_id: int, 
    capability_id: int, 
    instrument_id: Optional[int] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Remove a capability from a user (soft delete).
    
    Args:
        user_id: User ID
        capability_id: Capability ID to remove
        instrument_id: For instrument-specific caps, specify which instrument record to remove
    """
    # Check if capability is global or instrument-specific
    cap = db.query(Capability).filter_by(id=capability_id).first()
    is_global = cap.is_global if cap and hasattr(cap, 'is_global') else True
    
    # Build query based on whether it's global or instrument-specific
    query = db.query(UserCapability).filter_by(user_id=user_id, capability_id=capability_id)
    if is_global:
        query = query.filter_by(instrument_id=None)
    elif instrument_id is not None:
        query = query.filter_by(instrument_id=instrument_id)
    
    user_cap = query.first()
    if not user_cap:
        raise HTTPException(status_code=404, detail="User capability not found")
    
    user_cap.is_active = False
    db.commit()
    
    return {"success": True, "message": "Capability removed"}


@router.put("/users/{user_id}/capabilities/{capability_id}/toggle-mastery", response_model=CapabilityToggleMasteryResponse)
def admin_toggle_capability_mastery(
    user_id: int, 
    capability_id: int, 
    instrument_id: Optional[int] = None,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Toggle mastery status of a capability.
    
    Args:
        user_id: User ID
        capability_id: Capability ID to toggle
        instrument_id: For instrument-specific caps, specify which instrument record to toggle
    """
    # Check if capability is global or instrument-specific
    cap = db.query(Capability).filter_by(id=capability_id).first()
    is_global = cap.is_global if cap and hasattr(cap, 'is_global') else True
    
    # Build query based on whether it's global or instrument-specific
    query = db.query(UserCapability).filter_by(user_id=user_id, capability_id=capability_id, is_active=True)
    if is_global:
        query = query.filter_by(instrument_id=None)
    elif instrument_id is not None:
        query = query.filter_by(instrument_id=instrument_id)
    
    user_cap = query.first()
    if not user_cap:
        raise HTTPException(status_code=404, detail="User capability not found")
    
    if user_cap.mastered_at:
        user_cap.mastered_at = None
        action = "unmastered"
    else:
        user_cap.mastered_at = datetime.datetime.now()
        action = "mastered"
    
    db.commit()
    
    return {"success": True, "action": action}


@router.get("/users/{user_id}/soft-gates/all", response_model=AllSoftGatesResponse)
def admin_get_all_soft_gates(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Get all soft gate dimensions with user values."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    rules = db.query(SoftGateRule).all()
    user_states = {s.dimension_name: s for s in db.query(UserSoftGateState).filter_by(user_id=user_id).all()}
    
    result = []
    for rule in rules:
        state = user_states.get(rule.dimension_name)
        result.append({
            "dimension_name": rule.dimension_name,
            "frontier_buffer": rule.frontier_buffer,
            "min_attempts": rule.min_attempts,
            "success_required_count": rule.success_required_count,
            "comfortable_value": state.comfortable_value if state else 0,
            "max_demonstrated_value": state.max_demonstrated_value if state else 0,
            "frontier_success_ema": state.frontier_success_ema if state else 0,
            "frontier_attempt_count_since_last_promo": state.frontier_attempt_count_since_last_promo if state else 0,
            "has_state": state is not None,
        })
    
    return {"soft_gates": result}


@router.put("/users/{user_id}/soft-gates/{dimension_name}", response_model=SoftGateUpdateResponse)
def admin_update_soft_gate(user_id: int, dimension_name: str, update: SoftGateUpdate, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Update a user's soft gate state."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    state = db.query(UserSoftGateState).filter_by(user_id=user_id, dimension_name=dimension_name).first()
    
    if not state:
        # Create new state
        state = UserSoftGateState(
            user_id=user_id,
            dimension_name=dimension_name,
            comfortable_value=update.comfortable_value or 0,
            max_demonstrated_value=update.max_demonstrated_value or 0,
            frontier_success_ema=update.frontier_success_ema or 0,
            frontier_attempt_count_since_last_promo=update.frontier_attempt_count_since_last_promo or 0,
        )
        db.add(state)
        db.commit()
        return {"success": True, "message": "Soft gate state created"}
    
    changes = []
    
    if update.comfortable_value is not None:
        old = state.comfortable_value
        state.comfortable_value = update.comfortable_value
        changes.append(f"comfortable_value: {old} -> {update.comfortable_value}")
    
    if update.max_demonstrated_value is not None:
        old = state.max_demonstrated_value
        state.max_demonstrated_value = update.max_demonstrated_value
        changes.append(f"max_demonstrated_value: {old} -> {update.max_demonstrated_value}")
    
    if update.frontier_success_ema is not None:
        old = state.frontier_success_ema
        state.frontier_success_ema = update.frontier_success_ema
        changes.append(f"frontier_success_ema: {old} -> {update.frontier_success_ema}")
    
    if update.frontier_attempt_count_since_last_promo is not None:
        old = state.frontier_attempt_count_since_last_promo
        state.frontier_attempt_count_since_last_promo = update.frontier_attempt_count_since_last_promo
        changes.append(f"frontier_attempt_count: {old} -> {update.frontier_attempt_count_since_last_promo}")
    
    db.commit()
    
    return {"success": True, "changes": changes}


@router.post("/users/{user_id}/reset", response_model=UserResetResponse)
def admin_reset_user(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Reset a user's progress completely.
    Clears: capabilities, soft gates, material states, practice history, module progress.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    deleted_counts = {}
    
    # Delete user capabilities
    count = db.query(UserCapability).filter_by(user_id=user_id).delete()
    deleted_counts["user_capabilities"] = count
    
    # Delete soft gate states
    count = db.query(UserSoftGateState).filter_by(user_id=user_id).delete()
    deleted_counts["soft_gate_states"] = count
    
    # Delete material states
    count = db.query(UserMaterialState).filter_by(user_id=user_id).delete()
    deleted_counts["material_states"] = count
    
    # Delete practice attempts
    count = db.query(PracticeAttempt).filter_by(user_id=user_id).delete()
    deleted_counts["practice_attempts"] = count
    
    # Delete mini sessions
    sessions = db.query(PracticeSession).filter_by(user_id=user_id).all()
    session_ids = [s.id for s in sessions]
    if session_ids:
        count = db.query(MiniSession).filter(MiniSession.practice_session_id.in_(session_ids)).delete(synchronize_session=False)
        deleted_counts["mini_sessions"] = count
    
    # Delete practice sessions
    count = db.query(PracticeSession).filter_by(user_id=user_id).delete()
    deleted_counts["practice_sessions"] = count
    
    # Delete module progress
    count = db.query(UserModuleProgress).filter_by(user_id=user_id).delete()
    deleted_counts["module_progress"] = count
    
    # Delete lesson progress
    count = db.query(UserLessonProgress).filter_by(user_id=user_id).delete()
    deleted_counts["lesson_progress"] = count
    
    # Reset user day0 status
    user.day0_completed = False
    user.day0_stage = 0
    
    db.commit()
    
    return {
        "success": True,
        "message": f"User {user_id} has been reset",
        "deleted_counts": deleted_counts,
    }


@router.post("/users/{user_id}/grant-day0-capabilities", response_model=GrantDay0Response)
def admin_grant_day0_capabilities(user_id: int, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Grant all Day 0 capabilities to a user.
    This includes: staff_basics, ledger_lines, note_basics, first_note,
    accidental_raise_pitch, accidental_lower_pitch, and the appropriate clef.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Use the UserService to grant day 0 capabilities
    granted = UserService.grant_day0_capabilities(user, db)
    
    db.commit()
    
    # Get full list of day 0 capability names for reference
    clef = UserService.get_clef_capability(user.instrument)
    all_day0 = DAY0_BASE_CAPABILITIES + [clef]
    
    return {
        "success": True,
        "granted": granted,
        "all_day0_capabilities": all_day0,
        "message": f"Granted {len(granted)} Day 0 capabilities"
    }
