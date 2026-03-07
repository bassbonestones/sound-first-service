"""Admin focus cards endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
import json

from app.db import get_db
from app.models.core import FocusCard, MiniSession


router = APIRouter(tags=["admin-focus-cards"])


# --- Pydantic Models ---
class FocusCardCreate(BaseModel):
    name: str
    category: str = ""
    description: str = ""
    attention_cue: str = ""
    micro_cues: List[str] = []
    prompts: dict = {}


class FocusCardUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    attention_cue: Optional[str] = None
    micro_cues: Optional[List[str]] = None
    prompts: Optional[dict] = None


# --- Helper Functions ---
def parse_focus_card_json_field(value):
    """Parse a JSON string field, returning empty structure if invalid."""
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []


# --- Endpoints ---
@router.get("/focus-cards/categories")
def admin_get_focus_card_categories(db: Session = Depends(get_db)):
    """Get distinct focus card categories."""
    categories = db.query(FocusCard.category).distinct().all()
    return sorted([c[0] for c in categories if c[0]])


@router.post("/focus-cards")
def admin_create_focus_card(data: FocusCardCreate, db: Session = Depends(get_db)):
    """Create a new focus card."""
    existing = db.query(FocusCard).filter_by(name=data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Focus card with name '{data.name}' already exists")
    
    fc = FocusCard(
        name=data.name, category=data.category, description=data.description, attention_cue=data.attention_cue,
        micro_cues=json.dumps(data.micro_cues), prompts=json.dumps(data.prompts)
    )
    db.add(fc)
    db.commit()
    db.refresh(fc)
    
    return {"id": fc.id, "name": fc.name, "category": fc.category, "description": fc.description, "attention_cue": fc.attention_cue, "micro_cues": data.micro_cues, "prompts": data.prompts}


@router.put("/focus-cards/{focus_card_id}")
def admin_update_focus_card(focus_card_id: int, data: FocusCardUpdate, db: Session = Depends(get_db)):
    """Update a focus card."""
    fc = db.query(FocusCard).filter_by(id=focus_card_id).first()
    if not fc:
        raise HTTPException(status_code=404, detail="Focus card not found")
    
    if data.name is not None and data.name != fc.name:
        existing = db.query(FocusCard).filter_by(name=data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Focus card with name '{data.name}' already exists")
        fc.name = data.name
    
    if data.category is not None:
        fc.category = data.category
    if data.description is not None:
        fc.description = data.description
    if data.attention_cue is not None:
        fc.attention_cue = data.attention_cue
    if data.micro_cues is not None:
        fc.micro_cues = json.dumps(data.micro_cues)
    if data.prompts is not None:
        fc.prompts = json.dumps(data.prompts)
    
    db.commit()
    
    micro_cues = parse_focus_card_json_field(fc.micro_cues)
    prompts = parse_focus_card_json_field(fc.prompts)
    
    return {
        "id": fc.id, "name": fc.name, "category": fc.category, "description": fc.description, "attention_cue": fc.attention_cue,
        "micro_cues": micro_cues if isinstance(micro_cues, list) else [],
        "prompts": prompts if isinstance(prompts, dict) else {}
    }


@router.delete("/focus-cards/{focus_card_id}")
def admin_delete_focus_card(focus_card_id: int, db: Session = Depends(get_db)):
    """Delete a focus card."""
    fc = db.query(FocusCard).filter_by(id=focus_card_id).first()
    if not fc:
        raise HTTPException(status_code=404, detail="Focus card not found")
    
    referenced = db.query(MiniSession).filter_by(focus_card_id=focus_card_id).first()
    if referenced:
        raise HTTPException(status_code=400, detail="Cannot delete focus card that is referenced by practice sessions")
    
    db.delete(fc)
    db.commit()
    return {"message": f"Focus card '{fc.name}' deleted"}
