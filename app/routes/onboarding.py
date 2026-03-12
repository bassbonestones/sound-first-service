"""
Onboarding endpoints.

Handles user onboarding flow including instrument selection,
range configuration, and initial capability setup.
"""
from fastapi import APIRouter, Depends, Body, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.core import User
from app.schemas import OnboardingIn
from app.schemas.user_schemas import OnboardingOut, OnboardingSaveOut

router = APIRouter(tags=["onboarding"])


@router.get("/onboarding/{user_id}", response_model=OnboardingOut)
def get_onboarding(user_id: int, db: Session = Depends(get_db)) -> OnboardingOut:
    """
    Get onboarding status for a user.
    
    Returns the user's instrument, range, and comfort level settings
    configured during onboarding.
    
    Args:
        user_id: The user's ID
        db: Database session
    
    Returns:
        OnboardingOut with instrument, range, and capability settings
    
    Raises:
        HTTPException: 404 if user not found
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.id,
        "instrument": user.instrument,
        "resonant_note": user.resonant_note,
        "range_low": user.range_low,
        "range_high": user.range_high,
        "comfortable_capabilities": user.comfortable_capabilities.split(",") if user.comfortable_capabilities else [],
        "day0_completed": user.day0_completed if hasattr(user, 'day0_completed') else False,
        "day0_stage": user.day0_stage if hasattr(user, 'day0_stage') else 0,
    }


@router.post("/onboarding", response_model=OnboardingSaveOut)
def save_onboarding(data: OnboardingIn = Body(...), db: Session = Depends(get_db)) -> OnboardingSaveOut:
    """
    Save or update user onboarding data.
    
    Creates a new user if not exists, then updates instrument,
    range, and comfortable capabilities from onboarding flow.
    
    Args:
        data: OnboardingIn schema with user settings
        db: Database session
    
    Returns:
        OnboardingSaveOut with status and user_id
    """
    user = db.query(User).filter_by(id=data.user_id).first()
    if not user:
        # Create user if not exists
        user = User(id=data.user_id, email=f"user{data.user_id}@example.com")
        db.add(user)
    user.instrument = data.instrument
    user.resonant_note = data.resonant_note
    user.range_low = data.range_low
    user.range_high = data.range_high
    user.comfortable_capabilities = ",".join(data.comfortable_capabilities) if data.comfortable_capabilities else ""
    db.commit()
    return {"status": "success", "user_id": user.id}
