"""User endpoints for Sound First API."""
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session as DbSession
from pydantic import BaseModel
from typing import List, Optional
import datetime

from app.db import get_db
from app.models.core import User, Material
from app.models.capability_schema import Capability, UserCapability, MaterialAnalysis
from app.curriculum import get_next_capability_to_introduce
from app.services import UserService

router = APIRouter(tags=["users"])


# --- Pydantic Models ---
class UserUpdateIn(BaseModel):
    day0_completed: Optional[bool] = None
    day0_stage: Optional[int] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None


class UserRangeIn(BaseModel):
    range_low: str
    range_high: str


# --- Endpoints ---
@router.get("/users/{user_id}")
def get_user(user_id: int, db: DbSession = Depends(get_db)):
    """Get user details."""
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
def get_user_journey_stage(user_id: int, db: DbSession = Depends(get_db)):
    """Estimate user's journey stage based on practice history."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = UserService.estimate_journey_stage(user_id, db)
    
    return {
        "user_id": user_id,
        "stage": result.stage,
        "stage_name": result.stage_name,
        "factors": result.factors,
        "metrics": result.metrics
    }


@router.post("/users/{user_id}/reset")
def reset_user_data(user_id: int, db: DbSession = Depends(get_db)):
    """Reset all user data to start fresh."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    UserService.reset_user_data(user, db)
    db.commit()
    
    return {"status": "success", "message": "User data reset successfully"}


@router.patch("/users/{user_id}")
def update_user(user_id: int, data: UserUpdateIn = Body(...), db: DbSession = Depends(get_db)):
    """Update user fields (day0 progress, range, etc.)."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    was_day0_completed = user.day0_completed
    
    if data.day0_completed is not None:
        user.day0_completed = data.day0_completed
    if data.day0_stage is not None:
        user.day0_stage = data.day0_stage
    if data.range_low is not None:
        user.range_low = data.range_low
    if data.range_high is not None:
        user.range_high = data.range_high
    
    # Grant Day 0 capabilities if being completed for the first time
    granted_capabilities = []
    if data.day0_completed:
        mastered_count = db.query(UserCapability).filter(
            UserCapability.user_id == user.id,
            UserCapability.mastered_at.isnot(None)
        ).count()
        
        if not was_day0_completed or mastered_count == 0:
            granted_capabilities = UserService.grant_day0_capabilities(user, db)
    
    db.commit()
    return {
        "status": "success",
        "user_id": user.id,
        "granted_capabilities": granted_capabilities
    }


@router.patch("/users/{user_id}/range")
def update_user_range(user_id: int, data: UserRangeIn = Body(...), db: DbSession = Depends(get_db)):
    """Update user's comfortable playing range."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.range_low = data.range_low
    user.range_high = data.range_high
    db.commit()
    return {"status": "success", "range_low": user.range_low, "range_high": user.range_high}


@router.get("/users/{user_id}/capability-progress")
def get_user_capability_progress(user_id: int, db: DbSession = Depends(get_db)):
    """Get user's progress on capability learning."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_caps = db.query(UserCapability).filter(UserCapability.user_id == user_id).all()
    all_caps = db.query(Capability).all()
    
    mastered_caps = [c for c in user_caps if c.mastered_at is not None]
    in_progress_caps = [c for c in user_caps if c.mastered_at is None]
    
    last_mastery = None
    if mastered_caps:
        mastery_dates = [c.mastered_at for c in mastered_caps if c.mastered_at]
        if mastery_dates:
            last_mastery = max(mastery_dates)
    
    return {
        "user_id": user_id,
        "total_capabilities": len(all_caps),
        "capabilities_mastered": len(mastered_caps),
        "capabilities_in_progress": len(in_progress_caps),
        "last_mastery": last_mastery.isoformat() if last_mastery else None,
        "mastered_capability_ids": [c.capability_id for c in mastered_caps]
    }


@router.get("/users/{user_id}/next-capability")
def get_next_capability_for_user(user_id: int, db: DbSession = Depends(get_db)):
    """Get the next capability that should be introduced to the user."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get mastered capability names
    mastered = db.query(UserCapability).filter(
        UserCapability.user_id == user_id,
        UserCapability.mastered_at.isnot(None)
    ).all()
    
    mastered_cap_names = []
    for m in mastered:
        cap = db.query(Capability).filter_by(id=m.capability_id).first()
        if cap:
            mastered_cap_names.append(cap.name)
    
    # Get all capabilities ordered
    all_caps = db.query(Capability).order_by(Capability.domain, Capability.bit_index).all()
    caps_list = [
        {
            "id": cap.id,
            "name": cap.name,
            "display_name": cap.display_name,
            "explanation": cap.explanation,
            "domain": cap.domain
        }
        for cap in all_caps
    ]
    
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
def get_eligible_materials(user_id: int, db: DbSession = Depends(get_db)):
    """Get materials the user is eligible for based on their capabilities."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_masks = UserService.get_user_masks(user)
    
    # Query materials using bitmask check
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
    db: DbSession = Depends(get_db)
):
    """Grant a capability to a user (mark as mastered)."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    was_granted, message = UserService.grant_capability(user, cap, db)
    db.commit()
    
    return {"message": message, "capability": cap.name}


@router.post("/users/{user_id}/capabilities/revoke")
def revoke_capability(
    user_id: int,
    capability_id: int = Body(..., embed=True),
    db: DbSession = Depends(get_db)
):
    """Revoke a capability from a user."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    was_revoked, message = UserService.revoke_capability(user, cap, db)
    db.commit()
    
    return {"message": message, "capability": cap.name}
