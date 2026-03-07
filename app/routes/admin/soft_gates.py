"""Admin soft gate rules and user state endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from pathlib import Path
import datetime
import json

from app.db import get_db
from app.models.core import User
from app.models.capability_schema import SoftGateRule, UserSoftGateState


router = APIRouter(tags=["admin-soft-gates"])


# --- Pydantic Models ---
class SoftGateRuleUpdate(BaseModel):
    dimension_name: Optional[str] = None
    frontier_buffer: Optional[float] = None
    promotion_step: Optional[float] = None
    min_attempts: Optional[int] = None
    success_rating_threshold: Optional[int] = None
    success_required_count: Optional[int] = None
    success_window_count: Optional[int] = None
    decay_halflife_days: Optional[float] = None


class SoftGateRuleCreate(BaseModel):
    dimension_name: str
    frontier_buffer: float
    promotion_step: float
    min_attempts: int
    success_rating_threshold: int = 4
    success_required_count: int
    success_window_count: Optional[int] = None
    decay_halflife_days: Optional[float] = None


class UserSoftGateStateUpdate(BaseModel):
    comfortable_value: Optional[float] = None
    max_demonstrated_value: Optional[float] = None
    frontier_success_ema: Optional[float] = None
    frontier_attempt_count_since_last_promo: Optional[int] = None


class UserSoftGateStateReset(BaseModel):
    user_id: int
    dimension_names: Optional[List[str]] = None


# --- Soft Gate Rules Endpoints ---
@router.get("/soft-gate-rules")
def admin_get_soft_gate_rules(db: Session = Depends(get_db)):
    """Get all soft gate rules."""
    rules = db.query(SoftGateRule).all()
    return [{
        "id": r.id, "dimension_name": r.dimension_name, "frontier_buffer": r.frontier_buffer,
        "promotion_step": r.promotion_step, "min_attempts": r.min_attempts, "success_rating_threshold": r.success_rating_threshold,
        "success_required_count": r.success_required_count, "success_window_count": r.success_window_count, "decay_halflife_days": r.decay_halflife_days,
    } for r in rules]


@router.post("/soft-gate-rules")
def admin_create_soft_gate_rule(data: SoftGateRuleCreate, db: Session = Depends(get_db)):
    """Create a new soft gate rule."""
    existing = db.query(SoftGateRule).filter_by(dimension_name=data.dimension_name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Rule for dimension '{data.dimension_name}' already exists")
    
    rule = SoftGateRule(
        dimension_name=data.dimension_name, frontier_buffer=data.frontier_buffer, promotion_step=data.promotion_step,
        min_attempts=data.min_attempts, success_rating_threshold=data.success_rating_threshold,
        success_required_count=data.success_required_count, success_window_count=data.success_window_count, decay_halflife_days=data.decay_halflife_days,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return {
        "id": rule.id, "dimension_name": rule.dimension_name, "frontier_buffer": rule.frontier_buffer,
        "promotion_step": rule.promotion_step, "min_attempts": rule.min_attempts, "success_rating_threshold": rule.success_rating_threshold,
        "success_required_count": rule.success_required_count, "success_window_count": rule.success_window_count, "decay_halflife_days": rule.decay_halflife_days,
    }


@router.put("/soft-gate-rules/{rule_id}")
def admin_update_soft_gate_rule(rule_id: int, data: SoftGateRuleUpdate, db: Session = Depends(get_db)):
    """Update a soft gate rule."""
    rule = db.query(SoftGateRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Soft gate rule not found")
    
    if data.dimension_name is not None and data.dimension_name != rule.dimension_name:
        existing = db.query(SoftGateRule).filter_by(dimension_name=data.dimension_name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Rule for dimension '{data.dimension_name}' already exists")
        rule.dimension_name = data.dimension_name
    
    if data.frontier_buffer is not None:
        rule.frontier_buffer = data.frontier_buffer
    if data.promotion_step is not None:
        rule.promotion_step = data.promotion_step
    if data.min_attempts is not None:
        rule.min_attempts = data.min_attempts
    if data.success_rating_threshold is not None:
        rule.success_rating_threshold = data.success_rating_threshold
    if data.success_required_count is not None:
        rule.success_required_count = data.success_required_count
    if data.success_window_count is not None:
        rule.success_window_count = data.success_window_count
    if data.decay_halflife_days is not None:
        rule.decay_halflife_days = data.decay_halflife_days
    
    db.commit()
    
    return {
        "id": rule.id, "dimension_name": rule.dimension_name, "frontier_buffer": rule.frontier_buffer,
        "promotion_step": rule.promotion_step, "min_attempts": rule.min_attempts, "success_rating_threshold": rule.success_rating_threshold,
        "success_required_count": rule.success_required_count, "success_window_count": rule.success_window_count, "decay_halflife_days": rule.decay_halflife_days,
    }


@router.delete("/soft-gate-rules/{rule_id}")
def admin_delete_soft_gate_rule(rule_id: int, db: Session = Depends(get_db)):
    """Delete a soft gate rule."""
    rule = db.query(SoftGateRule).filter_by(id=rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Soft gate rule not found")
    
    dimension_name = rule.dimension_name
    db.delete(rule)
    db.commit()
    return {"message": f"Soft gate rule '{dimension_name}' deleted"}


# --- User List Endpoint (for dropdowns) ---
@router.get("/users")
def admin_get_users(db: Session = Depends(get_db)):
    """Get all users for dropdown selection."""
    users = db.query(User).all()
    return [{"id": u.id, "email": u.email, "name": u.name if hasattr(u, 'name') else None, "instrument": u.instrument} for u in users]


# --- User Soft Gate State Endpoints ---
@router.get("/user-soft-gate-state")
def admin_get_user_soft_gate_state(user_id: int = Query(...), db: Session = Depends(get_db)):
    """Get soft gate state for a user."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    states = db.query(UserSoftGateState).filter_by(user_id=user_id).all()
    return [{
        "id": s.id, "user_id": s.user_id, "dimension_name": s.dimension_name, "comfortable_value": s.comfortable_value,
        "max_demonstrated_value": s.max_demonstrated_value, "frontier_success_ema": s.frontier_success_ema,
        "frontier_attempt_count_since_last_promo": s.frontier_attempt_count_since_last_promo,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    } for s in states]


@router.put("/user-soft-gate-state/{state_id}")
def admin_update_user_soft_gate_state(state_id: int, data: UserSoftGateStateUpdate, db: Session = Depends(get_db)):
    """Update a user's soft gate state for a dimension."""
    state = db.query(UserSoftGateState).filter_by(id=state_id).first()
    if not state:
        raise HTTPException(status_code=404, detail="Soft gate state not found")
    
    if data.comfortable_value is not None:
        state.comfortable_value = data.comfortable_value
    if data.max_demonstrated_value is not None:
        state.max_demonstrated_value = data.max_demonstrated_value
    if data.frontier_success_ema is not None:
        state.frontier_success_ema = data.frontier_success_ema
    if data.frontier_attempt_count_since_last_promo is not None:
        state.frontier_attempt_count_since_last_promo = data.frontier_attempt_count_since_last_promo
    
    state.updated_at = datetime.datetime.utcnow()
    db.commit()
    
    return {
        "id": state.id, "user_id": state.user_id, "dimension_name": state.dimension_name, "comfortable_value": state.comfortable_value,
        "max_demonstrated_value": state.max_demonstrated_value, "frontier_success_ema": state.frontier_success_ema,
        "frontier_attempt_count_since_last_promo": state.frontier_attempt_count_since_last_promo,
        "updated_at": state.updated_at.isoformat() if state.updated_at else None,
    }


@router.post("/user-soft-gate-state/reset")
def admin_reset_user_soft_gate_state(data: UserSoftGateStateReset, db: Session = Depends(get_db)):
    """Reset user's soft gate state to defaults."""
    user = db.query(User).filter_by(id=data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    json_path = Path(__file__).parent.parent.parent / "resources" / "soft_gate_rules.json"
    try:
        with json_path.open("r") as f:
            defaults_data = json.load(f)
        default_state = defaults_data.get("default_user_state", {})
    except Exception:
        default_state = {}
    
    if data.dimension_names:
        states = db.query(UserSoftGateState).filter(
            UserSoftGateState.user_id == data.user_id,
            UserSoftGateState.dimension_name.in_(data.dimension_names)
        ).all()
    else:
        states = db.query(UserSoftGateState).filter_by(user_id=data.user_id).all()
    
    reset_count = 0
    for state in states:
        dim_defaults = default_state.get(state.dimension_name, {})
        state.comfortable_value = dim_defaults.get("comfortable_value", 0.0)
        state.max_demonstrated_value = dim_defaults.get("max_demonstrated_value", 0.0)
        state.frontier_success_ema = dim_defaults.get("frontier_success_ema", 0.0)
        state.frontier_attempt_count_since_last_promo = dim_defaults.get("frontier_attempt_count_since_last_promo", 0)
        state.updated_at = datetime.datetime.utcnow()
        reset_count += 1
    
    db.commit()
    return {"message": f"Reset {reset_count} soft gate dimension(s) for user {data.user_id}"}
