"""Capabilities and Focus Cards endpoints."""
from fastapi import APIRouter, Depends, Body, HTTPException, Query
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
import json

from app.db import get_db
from app.models.core import Material, FocusCard
from app.models.capability_schema import Capability
from app.curriculum import get_help_menu_capabilities
from app.schemas import FocusCardOut

router = APIRouter(tags=["capabilities"])


def parse_focus_card_json_field(value):
    """Parse a JSON string field, returning empty structure if invalid."""
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []


@router.get("/focus-cards", response_model=List[FocusCardOut])
def get_focus_cards(db: Session = Depends(get_db)):
    """Get all focus cards with their prompts and cues."""
    focus_cards = db.query(FocusCard).all()
    result = []
    for fc in focus_cards:
        prompts_data = parse_focus_card_json_field(fc.prompts)
        result.append(FocusCardOut(
            id=fc.id,
            name=fc.name,
            description=fc.description or "",
            category=fc.category or "",
            attention_cue=fc.attention_cue or "",
            micro_cues=parse_focus_card_json_field(fc.micro_cues),
            prompts=prompts_data if isinstance(prompts_data, dict) else {}
        ))
    return result


@router.get("/capabilities")
def get_capabilities(db: Session = Depends(get_db)):
    """List all capabilities (legacy endpoint)."""
    capabilities = db.query(Capability).all()
    return [{"id": c.id, "name": c.name, "domain": c.domain} for c in capabilities]


@router.get("/capabilities/{capability_id}/lesson", deprecated=True)
def get_capability_lesson(capability_id: int, db: Session = Depends(get_db)):
    """
    [DEPRECATED] Get a mini-lesson for a specific capability.
    
    This endpoint used the V1 quiz-based system. V2 uses evidence-based mastery.
    Returns 410 Gone status.
    """
    raise HTTPException(
        status_code=410, 
        detail="This endpoint is deprecated. V2 uses evidence-based mastery instead of quizzes."
    )


class QuizResultIn(BaseModel):
    user_id: int
    passed: bool
    answer_given: Optional[str] = None


@router.post("/capabilities/{capability_id}/quiz-result", deprecated=True)
def record_quiz_result(
    capability_id: int, 
    data: QuizResultIn = Body(...), 
    db: Session = Depends(get_db)
):
    """
    [DEPRECATED] Record the result of a capability quiz.
    
    This endpoint used the V1 quiz-based system. V2 uses evidence-based mastery.
    Returns 410 Gone status.
    """
    raise HTTPException(
        status_code=410, 
        detail="This endpoint is deprecated. V2 uses evidence-based mastery instead of quizzes."
    )


@router.get("/materials/{material_id}/help-capabilities")
def get_material_help_capabilities(material_id: int, db: Session = Depends(get_db)):
    """
    Get all capabilities referenced in a material for the help menu.
    
    Allows users to review any capability they encounter during practice.
    """
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    # Get all referenced capabilities
    cap_names = get_help_menu_capabilities(
        material.required_capability_ids,
        material.scaffolding_capability_ids
    )
    
    # Fetch full capability info from V2
    capabilities = []
    for cap_name in cap_names:
        cap = db.query(Capability).filter_by(name=cap_name).first()
        if cap:
            capabilities.append({
                "id": cap.id,
                "name": cap.name,
                "display_name": cap.display_name or cap.name,
                "domain": cap.domain,
                "has_lesson": bool(cap.display_name)  # V2 doesn't have explanation field
            })
    
    return {
        "material_id": material_id,
        "material_title": material.title,
        "capabilities": capabilities
    }


@router.get("/capabilities/v2")
def list_capabilities_v2(
    domain: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all capabilities in the v2 system, optionally filtered by domain."""
    query = db.query(Capability)
    if domain:
        query = query.filter_by(domain=domain)
    
    caps = query.order_by(Capability.domain, Capability.bit_index, Capability.name).all()
    
    return [
        {
            "id": c.id,
            "name": c.name,
            "display_name": c.display_name,
            "domain": c.domain,
            "subdomain": c.subdomain,
            "requirement_type": c.requirement_type,
            "bit_index": c.bit_index,
            "difficulty_tier": c.difficulty_tier,
        }
        for c in caps
    ]


@router.get("/capabilities/v2/domains")
def list_capability_domains(db: Session = Depends(get_db)):
    """List all capability domains with counts."""
    from sqlalchemy import func
    
    result = db.query(
        Capability.domain,
        func.count(Capability.id).label('count')
    ).group_by(Capability.domain).all()
    
    return [{"domain": r[0], "count": r[1]} for r in result]
