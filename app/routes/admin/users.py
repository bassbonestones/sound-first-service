"""Admin user progression and diagnostics endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import datetime
import random

from app.db import get_db
from app.models.core import User, Material, FocusCard, PracticeSession, MiniSession
from app.models.capability_schema import (
    Capability, UserCapability, SoftGateRule, UserSoftGateState,
    MaterialCapability, MaterialAnalysis, UserMaterialState
)
from app.curriculum import (
    filter_materials_by_capabilities,
    filter_materials_by_range,
    select_key_for_mini_session,
)


router = APIRouter(tags=["admin-users"])


@router.get("/users/{user_id}/progression")
def admin_get_user_progression(user_id: int, db: Session = Depends(get_db)):
    """Get comprehensive user progression data."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_caps = db.query(UserCapability, Capability).join(
        Capability, UserCapability.capability_id == Capability.id
    ).filter(UserCapability.user_id == user_id, UserCapability.is_active == True).all()
    
    mastered = []
    introduced = []
    for user_cap, cap in user_caps:
        cap_data = {
            "id": cap.id, "name": cap.name, "display_name": cap.display_name, "domain": cap.domain,
            "introduced_at": user_cap.introduced_at.isoformat() if user_cap.introduced_at else None,
            "mastered_at": user_cap.mastered_at.isoformat() if user_cap.mastered_at else None,
            "evidence_count": user_cap.evidence_count,
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
    
    return {
        "user": {
            "id": user.id, "email": user.email, "instrument": user.instrument,
            "resonant_note": user.resonant_note, "range_low": user.range_low, "range_high": user.range_high,
            "day0_completed": getattr(user, "day0_completed", False), "day0_stage": getattr(user, "day0_stage", 0),
        },
        "capabilities": {"mastered": mastered, "introduced": introduced, "recent_promotions": recent_promotions},
        "soft_gates": soft_gate_data,
        "journey": {"stage": "learning", "capabilities_mastered": len(mastered), "materials_completed": materials_completed},
    }


@router.get("/users/{user_id}/session-candidates")
def admin_get_session_candidates(user_id: int, db: Session = Depends(get_db)):
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


@router.post("/users/{user_id}/generate-diagnostic-session")
def admin_generate_diagnostic_session(user_id: int, duration_minutes: int = 30, db: Session = Depends(get_db)):
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


@router.get("/users/{user_id}/last-session-diagnostics")
def admin_get_last_session_diagnostics(user_id: int, db: Session = Depends(get_db)):
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
