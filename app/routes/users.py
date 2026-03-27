"""User endpoints for Sound First API."""
import datetime
import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Body, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.db import get_db
from app.models.core import User, Material
from app.models.capability_schema import Capability, UserCapability, MaterialAnalysis, UserInstrument
from app.curriculum import get_next_capability_to_introduce
from app.services import UserService
from app.schemas.user_schemas import (
    UserOut, JourneyStageOut, StatusMessageResponse, RangeUpdateOut,
    CapabilityProgressOut, NextCapabilityOut, EligibleMaterialsOut, MaterialForUser,
    MessageResponse, UserInstrumentsOut, InstrumentDetailOut, SelectInstrumentOut,
    Day0StatusOut, InstrumentCreateOut, InstrumentUpdateOut, InstrumentDeleteOut,
    UserUpdateOut
)

logger = logging.getLogger(__name__)

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
@router.get(
    "/users/{user_id}",
    response_model=UserOut,
    description="Get user details",
)
def get_user(user_id: int, db: DbSession = Depends(get_db)) -> Dict[str, Any]:
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


@router.get(
    "/users/{user_id}/journey-stage",
    response_model=JourneyStageOut,
    description="Estimate user's journey stage based on practice history",
)
def get_user_journey_stage(user_id: int, db: DbSession = Depends(get_db)) -> Dict[str, Any]:
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


@router.post(
    "/users/{user_id}/reset",
    response_model=StatusMessageResponse,
    description="Reset all user data to start fresh",
)
def reset_user_data(user_id: int, db: DbSession = Depends(get_db)) -> Dict[str, Any]:
    """Reset all user data to start fresh."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    UserService.reset_user_data(user, db)
    db.commit()
    
    return {"status": "success", "message": "User data reset successfully"}


@router.patch(
    "/users/{user_id}",
    response_model=UserUpdateOut,
    description="Update user fields (day0 progress, range)",
)
def update_user(user_id: int, data: UserUpdateIn = Body(...), db: DbSession = Depends(get_db)) -> Dict[str, Any]:
    """Update user fields (day0 progress, range, etc.)."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    was_day0_completed = user.day0_completed
    
    if data.day0_completed is not None:
        user.day0_completed = data.day0_completed  # type: ignore[assignment]
    if data.day0_stage is not None:
        user.day0_stage = data.day0_stage  # type: ignore[assignment]
    if data.range_low is not None:
        user.range_low = data.range_low  # type: ignore[assignment]
    if data.range_high is not None:
        user.range_high = data.range_high  # type: ignore[assignment]
    
    # Grant Day 0 capabilities if being completed for the first time
    granted_capabilities: List[str] = []
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


@router.patch(
    "/users/{user_id}/range",
    response_model=RangeUpdateOut,
    description="Update user's comfortable playing range",
)
def update_user_range(user_id: int, data: UserRangeIn = Body(...), db: DbSession = Depends(get_db)) -> Dict[str, Any]:
    """Update user's comfortable playing range."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.range_low = data.range_low  # type: ignore[assignment]
    user.range_high = data.range_high  # type: ignore[assignment]
    db.commit()
    return {"status": "success", "range_low": user.range_low, "range_high": user.range_high}


@router.get(
    "/users/{user_id}/capability-progress",
    response_model=CapabilityProgressOut,
    description="Get user's progress on capability learning",
)
def get_user_capability_progress(user_id: int, db: DbSession = Depends(get_db)) -> Dict[str, Any]:
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
            last_mastery = max(mastery_dates)  # type: ignore[type-var]
    
    return {
        "user_id": user_id,
        "total_capabilities": len(all_caps),
        "capabilities_mastered": len(mastered_caps),
        "capabilities_in_progress": len(in_progress_caps),
        "last_mastery": last_mastery.isoformat() if last_mastery else None,
        "mastered_capability_ids": [c.capability_id for c in mastered_caps]
    }


@router.get(
    "/users/{user_id}/next-capability",
    response_model=NextCapabilityOut,
    description="Get the next capability to introduce to the user",
)
def get_next_capability_for_user(user_id: int, db: DbSession = Depends(get_db)) -> Dict[str, Any]:
    """Get the next capability that should be introduced to the user."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get mastered capability names
    mastered = db.query(UserCapability).filter(
        UserCapability.user_id == user_id,
        UserCapability.mastered_at.isnot(None)
    ).all()
    
    mastered_cap_names: List[Any] = []
    for m in mastered:
        cap = db.query(Capability).filter_by(id=m.capability_id).first()
        if cap:
            mastered_cap_names.append(cap.name)
    
    # Get all capabilities ordered
    all_caps = db.query(Capability).order_by(Capability.domain, Capability.bit_index).all()
    caps_list: List[Dict[str, Any]] = [
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


@router.get(
    "/users/{user_id}/eligible-materials",
    response_model=EligibleMaterialsOut,
    description="Get materials user is eligible for based on capabilities",
)
def get_eligible_materials(user_id: int, db: DbSession = Depends(get_db)) -> EligibleMaterialsOut:
    """Get materials the user is eligible for based on their capabilities."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_masks = UserService.get_user_masks(user)
    
    # Query materials using bitmask check
    materials = db.query(Material).filter(
        (func.coalesce(Material.req_cap_mask_0, 0).op('&')(~user_masks[0])) == 0,
        (func.coalesce(Material.req_cap_mask_1, 0).op('&')(~user_masks[1])) == 0,
        (func.coalesce(Material.req_cap_mask_2, 0).op('&')(~user_masks[2])) == 0,
        (func.coalesce(Material.req_cap_mask_3, 0).op('&')(~user_masks[3])) == 0,
        (func.coalesce(Material.req_cap_mask_4, 0).op('&')(~user_masks[4])) == 0,
        (func.coalesce(Material.req_cap_mask_5, 0).op('&')(~user_masks[5])) == 0,
        (func.coalesce(Material.req_cap_mask_6, 0).op('&')(~user_masks[6])) == 0,
        (func.coalesce(Material.req_cap_mask_7, 0).op('&')(~user_masks[7])) == 0,
    ).all()
    
    material_ids = [m.id for m in materials]
    analyses = db.query(MaterialAnalysis).filter(
        MaterialAnalysis.material_id.in_(material_ids)
    ).all() if material_ids else []
    analysis_map = {a.material_id: a for a in analyses}
    
    return {  # type: ignore[return-value]
        "user_id": user_id,
        "total_eligible": len(materials),
        "eligible_materials": [
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


@router.post(
    "/users/{user_id}/capabilities/grant",
    response_model=MessageResponse,
    description="Grant a capability to a user (mark as mastered)",
)
def grant_capability(
    user_id: int,
    capability_id: int = Body(..., embed=True),
    db: DbSession = Depends(get_db)
) -> MessageResponse:
    """Grant a capability to a user (mark as mastered)."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    was_granted, message = UserService.grant_capability(user, cap, db)
    db.commit()
    
    return {"message": message, "capability": cap.name}  # type: ignore[return-value]


@router.post(
    "/users/{user_id}/capabilities/revoke",
    response_model=MessageResponse,
    description="Revoke a capability from a user",
)
def revoke_capability(
    user_id: int,
    capability_id: int = Body(..., embed=True),
    db: DbSession = Depends(get_db)
) -> MessageResponse:
    """Revoke a capability from a user."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    was_revoked, message = UserService.revoke_capability(user, cap, db)
    db.commit()
    
    return {"message": message, "capability": cap.name}  # type: ignore[return-value]


# ============================================
# User Instruments 
# ============================================

class InstrumentCreateIn(BaseModel):
    instrument_name: str
    clef: Optional[str] = None
    resonant_note: Optional[str] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None
    is_primary: Optional[bool] = False


class InstrumentUpdateIn(BaseModel):
    instrument_name: Optional[str] = None
    clef: Optional[str] = None
    resonant_note: Optional[str] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None
    is_primary: Optional[bool] = None
    day0_completed: Optional[bool] = None
    day0_stage: Optional[int] = None


@router.get(
    "/users/{user_id}/instruments",
    response_model=UserInstrumentsOut,
    description="Get all instruments for a user",
)
def list_user_instruments(user_id: int, db: DbSession = Depends(get_db)) -> UserInstrumentsOut:
    """Get all instruments for a user, including last selected instrument ID."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    instruments = db.query(UserInstrument).filter(
        UserInstrument.user_id == user_id
    ).order_by(UserInstrument.is_primary.desc(), UserInstrument.created_at).all()
    
    return {  # type: ignore[return-value]
        "user_id": user_id,
        "last_instrument_id": user.last_instrument_id,
        "instruments": [
            {
                "id": inst.id,
                "instrument_name": inst.instrument_name,
                "is_primary": inst.is_primary,
                "clef": inst.clef,
                "resonant_note": inst.resonant_note,
                "range_low": inst.range_low,
                "range_high": inst.range_high,
                "day0_completed": inst.day0_completed,
                "day0_stage": inst.day0_stage,
                "created_at": inst.created_at.isoformat() if inst.created_at else None,
                "last_practiced_at": inst.last_practiced_at.isoformat() if inst.last_practiced_at else None,
            }
            for inst in instruments
        ]
    }


class SelectInstrumentIn(BaseModel):
    instrument_id: int


@router.post(
    "/users/{user_id}/select-instrument",
    response_model=SelectInstrumentOut,
    description="Record user's current instrument selection",
)
def select_instrument(
    user_id: int,
    data: SelectInstrumentIn = Body(...),
    db: DbSession = Depends(get_db)
) -> SelectInstrumentOut:
    """
    Record the user's current instrument selection.
    
    This persists across sessions so the app can restore the last used instrument.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify the instrument exists and belongs to this user
    instrument = db.query(UserInstrument).filter(
        UserInstrument.id == data.instrument_id,
        UserInstrument.user_id == user_id
    ).first()
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    user.last_instrument_id = data.instrument_id  # type: ignore[assignment]
    db.commit()
    
    return {  # type: ignore[return-value]
        "status": "success",
        "last_instrument_id": data.instrument_id
    }


@router.get(
    "/users/{user_id}/day0-status",
    response_model=Day0StatusOut,
    description="Get Day 0 status including stages that can be skipped",
)
def get_day0_status(
    user_id: int,
    instrument_id: Optional[int] = None,
    db: DbSession = Depends(get_db)
) -> Day0StatusOut:
    """
    Get Day 0 status for a user, including which stages can be skipped.
    
    For a new instrument, global capabilities that are already mastered
    don't need to be re-taught. This returns which stages can be skipped.
    
    Stage-to-capability mapping:
    - Stages 0-2: first_note (instrument-specific, always show)
    - Stage 3: staff_basics, ledger_lines (global)
    - Stage 4: note_basics (global)
    - Stage 5: clef_bass/clef_treble (global, but instrument-dependent)
    - Stage 6: accidental_raise_pitch, accidental_lower_pitch (global)
    - Stage 7: summary (always show)
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's mastered global capabilities
    mastered_global_caps = set()
    user_caps = db.query(UserCapability, Capability).join(
        Capability, UserCapability.capability_id == Capability.id
    ).filter(
        UserCapability.user_id == user_id,
        UserCapability.instrument_id == None,  # Global only
        UserCapability.mastered_at != None,
        Capability.is_global == True
    ).all()
    
    for uc, cap in user_caps:
        mastered_global_caps.add(cap.name)
    
    # Determine which clef the instrument needs
    instrument_clef = None
    if instrument_id:
        instrument = db.query(UserInstrument).filter_by(id=instrument_id, user_id=user_id).first()
        if instrument:
            # Determine clef from instrument name
            bass_instruments = {"bass trombone", "tenor trombone", "trombone", "euphonium", "tuba", "bassoon", "cello", "double bass"}
            if instrument.instrument_name and instrument.instrument_name.lower() in bass_instruments:
                instrument_clef = "clef_bass"
            else:
                instrument_clef = "clef_treble"
    
    # Determine skippable stages
    skippable_stages = []
    
    # Stage 3: staff_basics AND ledger_lines
    if "staff_basics" in mastered_global_caps and "ledger_lines" in mastered_global_caps:
        skippable_stages.append(3)
    
    # Stage 4: note_basics
    if "note_basics" in mastered_global_caps:
        skippable_stages.append(4)
    
    # Stage 5: clef (check the specific clef needed for this instrument)
    if instrument_clef and instrument_clef in mastered_global_caps:
        skippable_stages.append(5)
    
    # Stage 6: accidentals (both must be mastered)
    if "accidental_raise_pitch" in mastered_global_caps and "accidental_lower_pitch" in mastered_global_caps:
        skippable_stages.append(6)
    
    return {  # type: ignore[return-value]
        "user_id": user_id,
        "instrument_id": instrument_id,
        "mastered_global_caps": list(mastered_global_caps),
        "skippable_stages": skippable_stages,
        "total_stages": 8,  # 0-7
        "effective_stages": 8 - len(skippable_stages)
    }


@router.post(
    "/users/{user_id}/instruments",
    response_model=InstrumentCreateOut,
    description="Add a new instrument for a user",
)
def create_user_instrument(
    user_id: int, 
    data: InstrumentCreateIn = Body(...), 
    db: DbSession = Depends(get_db)
) -> InstrumentCreateOut:
    """Add a new instrument for a user."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If this is being set as primary, unset any existing primary
    if data.is_primary:
        db.query(UserInstrument).filter(
            UserInstrument.user_id == user_id,
            UserInstrument.is_primary == True
        ).update({"is_primary": False})
    
    instrument = UserInstrument(
        user_id=user_id,
        instrument_name=data.instrument_name,
        clef=data.clef,
        resonant_note=data.resonant_note,
        range_low=data.range_low,
        range_high=data.range_high,
        is_primary=data.is_primary,
        day0_completed=False,
        day0_stage=0,
    )
    db.add(instrument)
    db.commit()
    db.refresh(instrument)
    
    # Auto-select newly created instrument
    user.last_instrument_id = instrument.id
    db.commit()
    
    return {  # type: ignore[return-value]
        "status": "success",
        "instrument": {
            "id": instrument.id,
            "instrument_name": instrument.instrument_name,
            "is_primary": instrument.is_primary,
            "clef": instrument.clef,
            "resonant_note": instrument.resonant_note,
            "range_low": instrument.range_low,
            "range_high": instrument.range_high,
            "day0_completed": instrument.day0_completed,
            "day0_stage": instrument.day0_stage,
        }
    }


@router.patch(
    "/users/{user_id}/instruments/{instrument_id}",
    response_model=InstrumentUpdateOut,
    description="Update an instrument for a user",
)
def update_user_instrument(
    user_id: int,
    instrument_id: int,
    data: InstrumentUpdateIn = Body(...),
    db: DbSession = Depends(get_db)
) -> InstrumentUpdateOut:
    """Update an instrument for a user."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    instrument = db.query(UserInstrument).filter(
        UserInstrument.id == instrument_id,
        UserInstrument.user_id == user_id
    ).first()
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    # Track if day0 is being completed
    was_day0_completed = instrument.day0_completed
    
    # If this is being set as primary, unset any existing primary
    if data.is_primary:
        db.query(UserInstrument).filter(
            UserInstrument.user_id == user_id,
            UserInstrument.is_primary == True,
            UserInstrument.id != instrument_id
        ).update({"is_primary": False})
    
    if data.instrument_name is not None:
        instrument.instrument_name = data.instrument_name  # type: ignore[assignment]
    if data.clef is not None:
        instrument.clef = data.clef  # type: ignore[assignment]
    if data.resonant_note is not None:
        instrument.resonant_note = data.resonant_note  # type: ignore[assignment]
    if data.range_low is not None:
        instrument.range_low = data.range_low  # type: ignore[assignment]
    if data.range_high is not None:
        instrument.range_high = data.range_high  # type: ignore[assignment]
    if data.is_primary is not None:
        instrument.is_primary = data.is_primary  # type: ignore[assignment]
    if data.day0_completed is not None:
        instrument.day0_completed = data.day0_completed  # type: ignore[assignment]
    if data.day0_stage is not None:
        instrument.day0_stage = data.day0_stage  # type: ignore[assignment]
    
    # Grant Day 0 capabilities if day0 is being completed for this instrument
    granted_capabilities: List[str] = []
    if data.day0_completed and not was_day0_completed:
        granted_capabilities = UserService.grant_day0_capabilities(
            user, 
            db, 
            instrument_id=instrument_id,
            instrument_name=str(instrument.instrument_name)
        )
        
        # Also update user-level day0_completed for backward compatibility
        if not user.day0_completed:
            user.day0_completed = True  # type: ignore[assignment]
    
    # Grant range_span capability based on new range (use UserService)
    range_span_granted: List[str] = []
    if instrument.range_low and instrument.range_high:
        range_span_granted = UserService.grant_range_span_capability(
            db, user_id, instrument_id, str(instrument.range_low), str(instrument.range_high)
        )
        if range_span_granted:
            granted_capabilities.extend(range_span_granted)
    
    db.commit()
    
    return {  # type: ignore[return-value]
        "status": "success",
        "granted_capabilities": granted_capabilities,
        "instrument": {
            "id": instrument.id,
            "instrument_name": instrument.instrument_name,
            "is_primary": instrument.is_primary,
            "clef": instrument.clef,
            "resonant_note": instrument.resonant_note,
            "range_low": instrument.range_low,
            "range_high": instrument.range_high,
            "day0_completed": instrument.day0_completed,
            "day0_stage": instrument.day0_stage,
        }
    }


@router.delete(
    "/users/{user_id}/instruments/{instrument_id}",
    response_model=InstrumentDeleteOut,
    description="Delete an instrument for a user",
)
def delete_user_instrument(
    user_id: int,
    instrument_id: int,
    db: DbSession = Depends(get_db)
) -> InstrumentDeleteOut:
    """Delete an instrument for a user."""
    instrument = db.query(UserInstrument).filter(
        UserInstrument.id == instrument_id,
        UserInstrument.user_id == user_id
    ).first()
    if not instrument:
        raise HTTPException(status_code=404, detail="Instrument not found")
    
    # Don't allow deleting the only instrument
    count = db.query(UserInstrument).filter(
        UserInstrument.user_id == user_id
    ).count()
    if count <= 1:
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete the only instrument. Add another instrument first."
        )
    
    # If deleting primary, make another instrument primary
    was_primary = instrument.is_primary
    instrument_name = instrument.instrument_name
    db.delete(instrument)
    
    if was_primary:
        # Make the most recently created instrument primary
        next_primary = db.query(UserInstrument).filter(
            UserInstrument.user_id == user_id
        ).order_by(UserInstrument.created_at.desc()).first()
        if next_primary:
            next_primary.is_primary = True  # type: ignore[assignment]
    
    db.commit()
    
    return {"status": "success", "message": f"Instrument '{instrument_name}' deleted"}  # type: ignore[return-value]
