"""User endpoints for Sound First API."""
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import datetime

from app.db import get_db
from app.models.core import User, Material, PracticeSession, MiniSession, PracticeAttempt, CurriculumStep
from app.models.capability_schema import Capability, UserCapability, MaterialAnalysis
from app.curriculum import (
    JourneyMetrics,
    estimate_journey_stage,
    get_next_capability_to_introduce,
)
from app.spaced_repetition import build_sr_item_from_db, estimate_mastery_level

router = APIRouter(tags=["users"])


# --- Pydantic Models ---
class UserUpdateIn(BaseModel):
    day0_completed: Optional[bool] = None
    day0_stage: Optional[int] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None


class UserRangeIn(BaseModel):
    range_low: str  # e.g., "E3"
    range_high: str  # e.g., "C6"


# --- Constants ---
# Day 0 capabilities that all users learn
DAY0_BASE_CAPABILITIES = [
    "staff_basics",       # Stage 3: The Musical Staff
    "ledger_lines",       # Stage 3: The Musical Staff (ledger lines)
    "note_basics",        # Stage 4: What is a Note?
    "first_note",         # Stage 1: Play Your Note
    "accidental_raise_pitch",    # Stage 6: Sharps raise pitch
    "accidental_lower_pitch",    # Stage 6: Flats lower pitch
]

# Instruments that use bass clef (all others use treble)
BASS_CLEF_INSTRUMENTS = {
    "Tenor Trombone", "Bass Trombone", "Euphonium", "Tuba",
    "Bassoon", "Cello", "Double Bass", "Bass Voice",
    "trombone", "bass_trombone", "euphonium", "tuba",
    "bassoon", "cello", "double_bass", "bass_voice",
}


# --- Helper Functions ---
def grant_day0_capabilities(user, db: Session):
    """
    Grant all Day 0 capabilities to a user when they complete the first-note flow.
    
    This marks the user as having mastered:
    - staff_basics, ledger_lines, note_basics, first_note
    - accidental symbols (flat, natural, sharp)
    - their instrument's clef (treble or bass)
    """
    # Determine which clef to grant based on instrument
    user_instrument = user.instrument or ""
    clef_capability = "clef_bass" if user_instrument in BASS_CLEF_INSTRUMENTS else "clef_treble"
    
    # Full list of capabilities to grant
    capabilities_to_grant = DAY0_BASE_CAPABILITIES + [clef_capability]
    
    # Look up capability IDs
    caps = db.query(Capability).filter(Capability.name.in_(capabilities_to_grant)).all()
    cap_map = {c.name: c for c in caps}
    
    now = datetime.datetime.utcnow()
    granted = []
    
    for cap_name in capabilities_to_grant:
        cap = cap_map.get(cap_name)
        if not cap:
            print(f"[grant_day0_capabilities] Warning: Capability '{cap_name}' not found")
            continue
        
        # Check if already exists
        existing = db.query(UserCapability).filter_by(
            user_id=user.id,
            capability_id=cap.id
        ).first()
        
        if existing:
            # Update to mastered if not already
            if not existing.mastered_at:
                existing.mastered_at = now
                existing.is_active = True
                granted.append(cap_name)
        else:
            # Create new mastered capability
            user_cap = UserCapability(
                user_id=user.id,
                capability_id=cap.id,
                introduced_at=now,
                mastered_at=now,
                is_active=True,
                evidence_count=1,  # Day 0 completion counts as evidence
            )
            db.add(user_cap)
            granted.append(cap_name)
    
    print(f"[grant_day0_capabilities] Granted {len(granted)} capabilities to user {user.id}: {granted}")
    return granted


# --- Endpoints ---
@router.get("/users/{user_id}")
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "instrument": user.instrument,
        "resonant_note": user.resonant_note
    }


@router.get("/users/{user_id}/journey-stage")
def get_user_journey_stage(user_id: int, db: Session = Depends(get_db)):
    """
    Estimate user's journey stage based on practice history.
    
    INTERNAL USE: Per spec, users are never told their stage.
    This is for adaptive system behavior only.
    
    Returns stage 1-6 with name and contributing factors.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Gather metrics
    sessions = db.query(PracticeSession).filter_by(user_id=user_id).all()
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    
    # Calculate days since first session
    days_since_first = 0
    if sessions:
        first_session = min(s.started_at for s in sessions if s.started_at)
        if first_session:
            days_since_first = (datetime.datetime.now() - first_session).days
    
    # Calculate average rating (excluding nulls)
    ratings = [a.rating for a in attempts if a.rating is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
    
    # Calculate average fatigue
    fatigues = [a.fatigue for a in attempts if a.fatigue is not None]
    avg_fatigue = sum(fatigues) / len(fatigues) if fatigues else 3.0
    
    # Build SR items for mastery counts
    materials = db.query(Material).all()
    attempt_history = {}
    for a in attempts:
        if a.material_id not in attempt_history:
            attempt_history[a.material_id] = []
        attempt_history[a.material_id].append({
            "rating": a.rating,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        })
    
    mastered_count = 0
    familiar_count = 0
    stabilizing_count = 0
    learning_count = 0
    
    for m in materials:
        mat_attempts = attempt_history.get(m.id, [])
        if not mat_attempts:
            continue
        sr_item = build_sr_item_from_db(m.id, mat_attempts)
        mastery = estimate_mastery_level(sr_item)
        if mastery == "mastered":
            mastered_count += 1
        elif mastery == "familiar":
            familiar_count += 1
        elif mastery == "stabilizing":
            stabilizing_count += 1
        elif mastery in ("learning", "new"):
            learning_count += 1
    
    # Count unique keys practiced
    unique_keys = set()
    mini_sessions = db.query(MiniSession).join(PracticeSession).filter(
        PracticeSession.user_id == user_id
    ).all()
    for ms in mini_sessions:
        if ms.key:
            unique_keys.add(ms.key)
    
    # Count capabilities mastered (V2)
    cap_progress = db.query(UserCapability).filter(
        UserCapability.user_id == user_id,
        UserCapability.mastered_at.isnot(None)
    ).count()
    
    # Count self-directed sessions
    self_directed_count = len([s for s in sessions if s.practice_mode == "self_directed"])
    
    # Build metrics
    metrics = JourneyMetrics(
        total_sessions=len(sessions),
        total_attempts=len(attempts),
        days_since_first_session=days_since_first,
        average_rating=avg_rating,
        average_fatigue=avg_fatigue,
        mastered_count=mastered_count,
        familiar_count=familiar_count,
        stabilizing_count=stabilizing_count,
        learning_count=learning_count,
        unique_keys_practiced=len(unique_keys),
        capabilities_introduced=cap_progress,
        self_directed_sessions=self_directed_count,
    )
    
    # Estimate stage
    stage_num, stage_name, factors = estimate_journey_stage(metrics)
    
    return {
        "user_id": user_id,
        "stage": stage_num,
        "stage_name": stage_name,
        "factors": factors,
        "metrics": {
            "total_sessions": metrics.total_sessions,
            "total_attempts": metrics.total_attempts,
            "days_active": metrics.days_since_first_session,
            "average_rating": round(metrics.average_rating, 2),
            "mastered_count": metrics.mastered_count,
            "familiar_count": metrics.familiar_count,
            "stabilizing_count": metrics.stabilizing_count,
            "unique_keys": metrics.unique_keys_practiced,
            "capabilities_introduced": metrics.capabilities_introduced,
            "self_directed_sessions": metrics.self_directed_sessions,
        }
    }


@router.post("/users/{user_id}/reset")
def reset_user_data(user_id: int, db: Session = Depends(get_db)):
    """
    Reset all user data to start fresh.
    Clears: instrument, resonant_note, range, day0 progress, capabilities, 
            practice sessions, attempts, mini-sessions, etc.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Clear user profile data
    user.instrument = None
    user.resonant_note = None
    user.range_low = None
    user.range_high = None
    user.comfortable_capabilities = None
    user.max_melodic_interval = "M2"
    user.day0_completed = False
    user.day0_stage = 0
    
    # Reset capability bitmasks
    user.cap_mask_0 = 0
    user.cap_mask_1 = 0
    user.cap_mask_2 = 0
    user.cap_mask_3 = 0
    user.cap_mask_4 = 0
    user.cap_mask_5 = 0
    user.cap_mask_6 = 0
    user.cap_mask_7 = 0
    
    # Delete all practice attempts for this user
    db.query(PracticeAttempt).filter_by(user_id=user_id).delete()
    
    # Delete all curriculum steps, mini-sessions, and sessions for this user
    # First get all sessions
    sessions = db.query(PracticeSession).filter_by(user_id=user_id).all()
    for session in sessions:
        # Get mini-sessions for this session
        mini_sessions = db.query(MiniSession).filter_by(practice_session_id=session.id).all()
        for ms in mini_sessions:
            # Delete curriculum steps for this mini-session
            db.query(CurriculumStep).filter_by(mini_session_id=ms.id).delete()
        # Delete mini-sessions
        db.query(MiniSession).filter_by(practice_session_id=session.id).delete()
    
    # Delete sessions
    db.query(PracticeSession).filter_by(user_id=user_id).delete()
    
    # Delete user capability progress (V2)
    db.query(UserCapability).filter(UserCapability.user_id == user_id).delete()
    
    # Reset user's day0 status
    user = db.query(User).filter_by(id=user_id).first()
    if user:
        user.day0_completed = False
        user.day0_stage = 0
    
    db.commit()
    
    return {"status": "success", "message": "User data reset successfully"}


@router.patch("/users/{user_id}")
def update_user(user_id: int, data: UserUpdateIn = Body(...), db: Session = Depends(get_db)):
    """Update user fields (day0 progress, range, etc.)."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Track if day0 is being completed for the first time
    was_day0_completed = user.day0_completed
    
    if data.day0_completed is not None:
        user.day0_completed = data.day0_completed
    if data.day0_stage is not None:
        user.day0_stage = data.day0_stage
    if data.range_low is not None:
        user.range_low = data.range_low
    if data.range_high is not None:
        user.range_high = data.range_high
    
    # Grant Day 0 capabilities if:
    # 1. day0_completed is being set to true for the first time, OR
    # 2. day0_completed is true but user has no mastered capabilities (seeded user edge case)
    granted_capabilities = []
    if data.day0_completed:
        mastered_count = db.query(UserCapability).filter(
            UserCapability.user_id == user.id,
            UserCapability.mastered_at.isnot(None)
        ).count()
        
        if not was_day0_completed or mastered_count == 0:
            granted_capabilities = grant_day0_capabilities(user, db)
    
    db.commit()
    return {
        "status": "success",
        "user_id": user.id,
        "granted_capabilities": granted_capabilities
    }


@router.patch("/users/{user_id}/range")
def update_user_range(user_id: int, data: UserRangeIn = Body(...), db: Session = Depends(get_db)):
    """Update user's comfortable playing range."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.range_low = data.range_low
    user.range_high = data.range_high
    db.commit()
    return {"status": "success", "range_low": user.range_low, "range_high": user.range_high}


@router.get("/users/{user_id}/capability-progress")
def get_user_capability_progress(user_id: int, db: Session = Depends(get_db)):
    """
    Get user's progress on capability learning (V2).
    
    Returns stats on mastered vs in-progress capabilities.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all user capabilities (V2)
    user_caps = db.query(UserCapability).filter(UserCapability.user_id == user_id).all()
    
    # Get all capabilities (V2)
    all_caps = db.query(Capability).all()
    total_capabilities = len(all_caps)
    
    mastered_caps = [c for c in user_caps if c.mastered_at is not None]
    in_progress_caps = [c for c in user_caps if c.mastered_at is None]
    
    # Get most recent mastery date
    last_mastery = None
    if mastered_caps:
        mastery_dates = [c.mastered_at for c in mastered_caps if c.mastered_at]
        if mastery_dates:
            last_mastery = max(mastery_dates)
    
    return {
        "user_id": user_id,
        "total_capabilities": total_capabilities,
        "capabilities_mastered": len(mastered_caps),
        "capabilities_in_progress": len(in_progress_caps),
        "last_mastery": last_mastery.isoformat() if last_mastery else None,
        "mastered_capability_ids": [c.capability_id for c in mastered_caps]
    }


@router.get("/users/{user_id}/next-capability")
def get_next_capability_for_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get the next capability that should be introduced to the user (V2).
    
    Based on sequence order and user's current mastery.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's mastered capabilities (V2)
    mastered = db.query(UserCapability).filter(
        UserCapability.user_id == user_id,
        UserCapability.mastered_at.isnot(None)
    ).all()
    mastered_cap_ids = [m.capability_id for m in mastered]
    
    # Get names of mastered caps
    mastered_cap_names = []
    for cap_id in mastered_cap_ids:
        cap = db.query(Capability).filter_by(id=cap_id).first()
        if cap:
            mastered_cap_names.append(cap.name)
    
    # Get all capabilities ordered by domain and bit_index (V2)
    all_caps = db.query(Capability).order_by(Capability.domain, Capability.bit_index).all()
    
    # Build list for the logic function
    caps_list = []
    for cap in all_caps:
        caps_list.append({
            "id": cap.id,
            "name": cap.name,
            "display_name": cap.display_name,
            "explanation": cap.explanation,
            "domain": cap.domain
        })
    
    next_cap = get_next_capability_to_introduce(mastered_cap_names, caps_list)
    
    if not next_cap:
        return {"message": "All capabilities learned!", "next_capability": None}
    
    return {
        "next_capability": {
            "id": next_cap.get("id"),
            "name": next_cap.get("name"),
            "display_name": next_cap.get("display_name"),
            "domain": next_cap.get("domain")
        },
        "user_mastered_count": len(mastered_cap_names)
    }


@router.get("/users/{user_id}/eligible-materials")
def get_eligible_materials(user_id: int, db: Session = Depends(get_db)):
    """
    Get materials the user is eligible for based on their capabilities.
    
    Uses bitmask for fast O(1) per-material eligibility check.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's capability masks
    user_masks = [
        user.cap_mask_0 or 0,
        user.cap_mask_1 or 0,
        user.cap_mask_2 or 0,
        user.cap_mask_3 or 0,
        user.cap_mask_4 or 0,
        user.cap_mask_5 or 0,
        user.cap_mask_6 or 0,
        user.cap_mask_7 or 0,
    ]
    
    # Query materials using bitmask check
    # User has all required caps if: (material_mask & ~user_mask) == 0 for all masks
    materials = db.query(Material).filter(
        ((Material.req_cap_mask_0 or 0).op('&')(~user_masks[0])) == 0,
        ((Material.req_cap_mask_1 or 0).op('&')(~user_masks[1])) == 0,
        ((Material.req_cap_mask_2 or 0).op('&')(~user_masks[2])) == 0,
        ((Material.req_cap_mask_3 or 0).op('&')(~user_masks[3])) == 0,
        ((Material.req_cap_mask_4 or 0).op('&')(~user_masks[4])) == 0,
        ((Material.req_cap_mask_5 or 0).op('&')(~user_masks[5])) == 0,
        ((Material.req_cap_mask_6 or 0).op('&')(~user_masks[6])) == 0,
        ((Material.req_cap_mask_7 or 0).op('&')(~user_masks[7])) == 0,
    ).all()
    
    # Get analysis data for eligible materials
    material_ids = [m.id for m in materials]
    analyses = db.query(MaterialAnalysis).filter(
        MaterialAnalysis.material_id.in_(material_ids)
    ).all() if material_ids else []
    analysis_map = {a.material_id: a for a in analyses}
    
    return {
        "user_id": user_id,
        "eligible_count": len(materials),
        "materials": [
            {
                "id": m.id,
                "title": m.title,
                "allowed_keys": m.allowed_keys.split(",") if m.allowed_keys else [],
                "analysis": {
                    "range": f"{analysis_map[m.id].lowest_pitch} - {analysis_map[m.id].highest_pitch}" 
                        if m.id in analysis_map and analysis_map[m.id].lowest_pitch else None,
                    "chromatic_complexity": analysis_map[m.id].chromatic_complexity if m.id in analysis_map else None,
                    "measure_count": analysis_map[m.id].measure_count if m.id in analysis_map else None,
                } if m.id in analysis_map else None,
            }
            for m in materials
        ],
    }


@router.post("/users/{user_id}/capabilities/grant")
def grant_capability(
    user_id: int,
    capability_id: int = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Grant a capability to a user (mark as mastered).
    
    Updates both the normalized table and the user's bitmask.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    # Check if already granted
    existing = db.query(UserCapability).filter_by(
        user_id=user_id, capability_id=capability_id
    ).first()
    
    if existing:
        if existing.is_active:
            return {"message": "Capability already granted", "capability": cap.name}
        else:
            # Reactivate
            existing.is_active = True
            existing.deactivated_at = None
            existing.mastered_at = datetime.datetime.now()
    else:
        # Create new record
        user_cap = UserCapability(
            user_id=user_id,
            capability_id=capability_id,
            introduced_at=datetime.datetime.now(),
            mastered_at=datetime.datetime.now(),
            is_active=True,
        )
        db.add(user_cap)
    
    # Update bitmask
    if cap.bit_index is not None:
        bucket = cap.bit_index // 64
        bit_position = cap.bit_index % 64
        
        mask_attrs = ['cap_mask_0', 'cap_mask_1', 'cap_mask_2', 'cap_mask_3',
                      'cap_mask_4', 'cap_mask_5', 'cap_mask_6', 'cap_mask_7']
        
        current_mask = getattr(user, mask_attrs[bucket]) or 0
        new_mask = current_mask | (1 << bit_position)
        setattr(user, mask_attrs[bucket], new_mask)
    
    db.commit()
    
    return {"message": "Capability granted", "capability": cap.name}


@router.post("/users/{user_id}/capabilities/revoke")
def revoke_capability(
    user_id: int,
    capability_id: int = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Revoke a capability from a user (mark as no longer able).
    
    Updates both the normalized table and the user's bitmask.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    existing = db.query(UserCapability).filter_by(
        user_id=user_id, capability_id=capability_id
    ).first()
    
    if not existing or not existing.is_active:
        return {"message": "Capability not currently active", "capability": cap.name}
    
    # Deactivate
    existing.is_active = False
    existing.deactivated_at = datetime.datetime.now()
    
    # Update bitmask (clear the bit)
    if cap.bit_index is not None:
        bucket = cap.bit_index // 64
        bit_position = cap.bit_index % 64
        
        mask_attrs = ['cap_mask_0', 'cap_mask_1', 'cap_mask_2', 'cap_mask_3',
                      'cap_mask_4', 'cap_mask_5', 'cap_mask_6', 'cap_mask_7']
        
        current_mask = getattr(user, mask_attrs[bucket]) or 0
        new_mask = current_mask & ~(1 << bit_position)
        setattr(user, mask_attrs[bucket], new_mask)
    
    db.commit()
    
    return {"message": "Capability revoked", "capability": cap.name}
