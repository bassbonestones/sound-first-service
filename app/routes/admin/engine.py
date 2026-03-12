"""Admin engine settings endpoints - configure session generation weights."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Optional, List, Any
from sqlalchemy.orm import Session

from app.db import get_db
from app import session_config


router = APIRouter(tags=["admin-engine"])


class EngineConfigResponse(BaseModel):
    """Current engine configuration."""
    capability_weights: Dict[str, float]
    difficulty_weights: Dict[str, float]
    novelty_reinforcement: Dict[str, float]
    fatigue_modifiers: Dict[int, Dict[str, float]]
    intensity_weights: Dict[str, float]
    time_budgets: Dict[str, float]
    anti_repetition: Dict[str, int]
    notation_shown_percentage: float
    teaching_module_time_per_lesson: float
    wrap_up_threshold_minutes: float


class EngineConfigUpdate(BaseModel):
    """Partial update to engine configuration."""
    capability_weights: Optional[Dict[str, float]] = None
    difficulty_weights: Optional[Dict[str, float]] = None
    novelty_reinforcement: Optional[Dict[str, float]] = None
    intensity_weights: Optional[Dict[str, float]] = None
    time_budgets: Optional[Dict[str, float]] = None
    notation_shown_percentage: Optional[float] = None
    wrap_up_threshold_minutes: Optional[float] = None


class EngineUpdateResponse(BaseModel):
    """Response for engine config update."""
    success: bool
    changes_applied: List[str]
    note: str


class EngineResetResponse(BaseModel):
    """Response for engine config reset."""
    success: bool
    message: str


@router.get("/engine/config", response_model=EngineConfigResponse)
def get_engine_config() -> EngineConfigResponse:
    """Get current session engine configuration."""
    return EngineConfigResponse(
        capability_weights=session_config.CAPABILITY_WEIGHTS,
        difficulty_weights=session_config.DIFFICULTY_WEIGHTS,
        novelty_reinforcement=session_config.NOVELTY_REINFORCEMENT,
        fatigue_modifiers=session_config.FATIGUE_CAPABILITY_MODIFIERS,
        intensity_weights=session_config.INTENSITY_WEIGHTS,
        time_budgets=session_config.AVG_MINI_SESSION_MINUTES,
        anti_repetition={
            "max_capability_streak": session_config.MAX_CAPABILITY_STREAK,
            "max_material_repeats_per_session": session_config.MAX_MATERIAL_REPEATS_PER_SESSION,
            "max_key_repeats_per_mini_session": session_config.MAX_KEY_REPEATS_PER_MINI_SESSION,
        },
        notation_shown_percentage=session_config.NOTES_SHOWN_PERCENTAGE,
        teaching_module_time_per_lesson=5.0,  # From sessions.py MODULE_LESSON_DURATION
        wrap_up_threshold_minutes=session_config.WRAP_UP_THRESHOLD_MINUTES,
    )


@router.put("/engine/config", response_model=EngineUpdateResponse)
def update_engine_config(update: EngineConfigUpdate) -> Dict[str, Any]:
    """
    Update engine configuration.
    
    Note: Changes are applied in-memory and will reset on server restart.
    For persistent changes, update the session_config.py file.
    """
    changes = []
    
    if update.capability_weights:
        for key, value in update.capability_weights.items():
            if key in session_config.CAPABILITY_WEIGHTS:
                old_val = session_config.CAPABILITY_WEIGHTS[key]
                session_config.CAPABILITY_WEIGHTS[key] = value
                changes.append(f"capability_weights.{key}: {old_val} -> {value}")
    
    if update.difficulty_weights:
        for key, value in update.difficulty_weights.items():
            if key in session_config.DIFFICULTY_WEIGHTS:
                old_val = session_config.DIFFICULTY_WEIGHTS[key]
                session_config.DIFFICULTY_WEIGHTS[key] = value
                changes.append(f"difficulty_weights.{key}: {old_val} -> {value}")
    
    if update.novelty_reinforcement:
        for key, value in update.novelty_reinforcement.items():
            if key in session_config.NOVELTY_REINFORCEMENT:
                old_val = session_config.NOVELTY_REINFORCEMENT[key]
                session_config.NOVELTY_REINFORCEMENT[key] = value
                changes.append(f"novelty_reinforcement.{key}: {old_val} -> {value}")
    
    if update.intensity_weights:
        for key, value in update.intensity_weights.items():
            if key in session_config.INTENSITY_WEIGHTS:
                old_val = session_config.INTENSITY_WEIGHTS[key]
                session_config.INTENSITY_WEIGHTS[key] = value
                changes.append(f"intensity_weights.{key}: {old_val} -> {value}")
    
    if update.time_budgets:
        for key, value in update.time_budgets.items():
            if key in session_config.AVG_MINI_SESSION_MINUTES:
                old_val = session_config.AVG_MINI_SESSION_MINUTES[key]
                session_config.AVG_MINI_SESSION_MINUTES[key] = value
                changes.append(f"time_budgets.{key}: {old_val} -> {value}")
    
    if update.notation_shown_percentage is not None:
        old_val = session_config.NOTES_SHOWN_PERCENTAGE
        session_config.NOTES_SHOWN_PERCENTAGE = update.notation_shown_percentage
        changes.append(f"notation_shown_percentage: {old_val} -> {update.notation_shown_percentage}")
    
    if update.wrap_up_threshold_minutes is not None:
        old_val = session_config.WRAP_UP_THRESHOLD_MINUTES
        session_config.WRAP_UP_THRESHOLD_MINUTES = update.wrap_up_threshold_minutes
        changes.append(f"wrap_up_threshold_minutes: {old_val} -> {update.wrap_up_threshold_minutes}")
    
    return {
        "success": True,
        "changes_applied": changes,
        "note": "Changes are in-memory only and will reset on server restart"
    }


@router.post("/engine/reset", response_model=EngineResetResponse)
def reset_engine_config() -> Dict[str, Any]:
    """Reset engine configuration to default values."""
    # Reset to original defaults
    session_config.CAPABILITY_WEIGHTS.update({
        "repertoire_fluency": 0.30,
        "technique": 0.20,
        "range_expansion": 0.10,
        "rhythm": 0.15,
        "ear_training": 0.15,
        "articulation": 0.10,
    })
    
    session_config.DIFFICULTY_WEIGHTS.update({
        "easy": 0.50,
        "medium": 0.35,
        "hard": 0.15,
    })
    
    session_config.NOVELTY_REINFORCEMENT.update({
        "novelty": 0.20,
        "reinforcement": 0.80,
    })
    
    session_config.INTENSITY_WEIGHTS.update({
        "small": 0.40,
        "medium": 0.45,
        "large": 0.15,
    })
    
    session_config.AVG_MINI_SESSION_MINUTES.update({
        "repertoire_fluency": 5.0,
        "technique": 4.0,
        "range_expansion": 3.0,
        "rhythm": 4.0,
        "ear_training": 3.0,
        "articulation": 4.0,
        "default": 4.0,
    })
    
    session_config.NOTES_SHOWN_PERCENTAGE = 0.20
    session_config.WRAP_UP_THRESHOLD_MINUTES = 3.0
    
    return {"success": True, "message": "Engine configuration reset to defaults"}
