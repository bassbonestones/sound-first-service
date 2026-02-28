
from fastapi import FastAPI, Depends, Body, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime
from app.db import get_db
from app.models.core import Material, FocusCard, PracticeSession, MiniSession, PracticeAttempt
from sqlalchemy.orm import Session

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Onboarding Fetch API Endpoint ---
@app.get("/onboarding/{user_id}")
def get_onboarding(user_id: int, db: Session = Depends(get_db)):
    from app.models.core import User
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.id,
        "instrument": user.instrument,
        "resonant_note": user.resonant_note,
        "comfortable_capabilities": user.comfortable_capabilities.split(",") if user.comfortable_capabilities else []
    }
# --- (moved below app = FastAPI()) ---
# --- Onboarding Input Model ---
class OnboardingIn(BaseModel):
    user_id: int = 1
    instrument: str
    resonant_note: str
    comfortable_capabilities: List[str]

# --- Onboarding API Endpoint ---
@app.post("/onboarding")
def save_onboarding(data: OnboardingIn = Body(...), db: Session = Depends(get_db)):
    user = db.query(app.models.core.User).filter_by(id=data.user_id).first()
    if not user:
        # Create user if not exists
        user = app.models.core.User(id=data.user_id)
        db.add(user)
    user.instrument = data.instrument
    user.resonant_note = data.resonant_note
    user.comfortable_capabilities = ",".join(data.comfortable_capabilities)
    db.commit()
    return {"status": "success", "user_id": user.id}

from fastapi import FastAPI, Depends, Query, Body, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime
from app.db import get_db
from app.models.core import Material, FocusCard, PracticeSession, MiniSession, PracticeAttempt
from sqlalchemy.orm import Session




app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Onboarding Fetch API Endpoint ---
@app.get("/onboarding/{user_id}")
def get_onboarding(user_id: int, db: Session = Depends(get_db)):
    from app.models.core import User
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.id,
        "instrument": user.instrument,
        "resonant_note": user.resonant_note,
        "comfortable_capabilities": user.comfortable_capabilities.split(",") if user.comfortable_capabilities else []
    }


# --- Response Models ---
class MiniSessionOut(BaseModel):
    material_id: int
    material_title: str
    focus_card_id: int
    focus_card_name: str
    focus_card_description: str = ""
    goal_type: str
    goal_label: str
    show_notation: bool
    target_key: str = None
    original_key_center: str = None
    resolved_musicxml: str = None
    starting_pitch: str = None

class PracticeSessionResponse(BaseModel):
    session_id: int
    user_id: int
    planned_duration_minutes: int
    generated_at: datetime.datetime
    mini_sessions: List[MiniSessionOut]


# --- Self-Directed Session Input Model ---
class SelfDirectedSessionIn(BaseModel):
    user_id: int = 1
    planned_duration_minutes: int = 30
    material_id: int
    focus_card_id: int
    goal_type: str

class PracticeAttemptIn(BaseModel):
    user_id: int
    material_id: int
    key: str
    focus_card_id: int
    rating: int
    fatigue: int
    timestamp: datetime.datetime


# --- Example Data with DB Lookups ---
@app.post("/generate-session", response_model=PracticeSessionResponse)
def generate_session(user_id: int = 1, planned_duration_minutes: int = 30, db: Session = Depends(get_db)):
    import random
    materials = db.query(Material).all()
    focus_cards = db.query(FocusCard).all()
    if not materials or not focus_cards:
        raise Exception("No materials or focus cards in DB")
    mini_sessions = []
    mini_session_objs = []
    # Helper for user-friendly goal labels
    goal_label_map = {
        "repertoire_fluency": "Repertoire Fluency",
        "range_expansion": "Range Expansion",
        "articulation_development": "Articulation Development",
        # Add more as needed
    }
    for i in range(3):
        material = random.choice(materials)
        focus_card = random.choice(focus_cards)
        # --- Pitch resolution logic ---
        import json
        show_notation = random.random() < 0.2
        target_key = material.original_key_center or "C major"
        original_key_center = material.original_key_center or "C major"
        resolved_musicxml = material.musicxml_canonical or "<musicxml/>"
        # Determine starting_pitch
        starting_pitch = None
        if material.pitch_reference_type == "TONAL":
            # Use tonic from pitch_ref_json if available, default to C4
            try:
                ref = json.loads(material.pitch_ref_json) if material.pitch_ref_json else {}
                tonic = ref.get("tonic", "C")
                # Use octave 4 for now; could be improved with user range
                starting_pitch = f"{tonic}4"
            except Exception:
                starting_pitch = "C4"
        elif material.pitch_reference_type == "ANCHOR_INTERVAL":
            # For anchor-based, use target_key tonic if available
            try:
                tonic = None
                if target_key:
                    tonic = target_key.split()[0]  # e.g., "C major" -> "C"
                starting_pitch = f"{tonic}4" if tonic else "C4"
            except Exception:
                starting_pitch = "C4"
        else:
            starting_pitch = "C4"
        goal_type = random.choice(list(goal_label_map.keys()))
        goal_label = goal_label_map.get(goal_type, goal_type.replace("_", " ").title())
        mini_sessions.append(MiniSessionOut(
            material_id=material.id,
            material_title=material.title,
            focus_card_id=focus_card.id,
            focus_card_name=focus_card.name,
            focus_card_description=getattr(focus_card, "description", ""),
            goal_type=goal_type,
            goal_label=goal_label,
            show_notation=show_notation,
            target_key=target_key,
            original_key_center=original_key_center,
            resolved_musicxml=resolved_musicxml,
            starting_pitch=starting_pitch
        ))
        mini_session_objs.append(MiniSession(
            material_id=material.id,
            key=target_key,
            focus_card_id=focus_card.id,
            goal_type=goal_type
        ))
    session_obj = PracticeSession(
        user_id=user_id,
        started_at=datetime.datetime.now(),
        ended_at=None
    )
    db.add(session_obj)
    db.flush()  # get session_obj.id
    for mini in mini_session_objs:
        mini.practice_session_id = session_obj.id
        db.add(mini)
    db.commit()
    return PracticeSessionResponse(
        session_id=session_obj.id,
        user_id=user_id,
        planned_duration_minutes=planned_duration_minutes,
        generated_at=session_obj.started_at,
        mini_sessions=mini_sessions
    )


# --- Self-Directed Session Endpoint ---
@app.post("/generate-self-directed-session", response_model=PracticeSessionResponse)
def generate_self_directed_session(
    data: SelfDirectedSessionIn = Body(...),
    db: Session = Depends(get_db)
):
    # Fetch material and focus card
    material = db.query(Material).filter(Material.id == data.material_id).first()
    focus_card = db.query(FocusCard).filter(FocusCard.id == data.focus_card_id).first()
    if not material or not focus_card:
        raise Exception("Invalid material or focus card")
    key = "Bb"  # Default or could randomize/choose from allowed_keys
    mini_sessions = [
        MiniSessionOut(
            material_id=material.id,
            material_title=material.title,
            key=key,
            focus_card_id=focus_card.id,
            focus_card_name=focus_card.name,
            goal_type=data.goal_type
        )
    ]
    mini_session_objs = [
        MiniSession(
            material_id=material.id,
            key=key,
            focus_card_id=focus_card.id,
            goal_type=data.goal_type
        )
    ]
    session_obj = PracticeSession(
        user_id=data.user_id,
        started_at=datetime.datetime.now(),
        ended_at=None
    )
    db.add(session_obj)
    db.flush()
    for mini in mini_session_objs:
        mini.practice_session_id = session_obj.id
        db.add(mini)
    db.commit()
    return PracticeSessionResponse(
        session_id=session_obj.id,
        user_id=data.user_id,
        planned_duration_minutes=data.planned_duration_minutes,
        generated_at=session_obj.started_at,
        mini_sessions=mini_sessions
    )


@app.post("/practice-attempt")
def record_practice_attempt(attempt: PracticeAttemptIn, db: Session = Depends(get_db)):
    attempt_obj = PracticeAttempt(
        user_id=attempt.user_id,
        material_id=attempt.material_id,
        key=attempt.key,
        focus_card_id=attempt.focus_card_id,
        rating=attempt.rating,
        fatigue=attempt.fatigue,
        timestamp=attempt.timestamp
    )
    db.add(attempt_obj)
    db.commit()
    return {"status": "success", "attempt_id": attempt_obj.id}


# Fetch all materials
@app.get("/materials")
def get_materials(db: Session = Depends(get_db)):
    return db.query(Material).all()

# Fetch all focus cards
@app.get("/focus-cards")
def get_focus_cards(db: Session = Depends(get_db)):
    return db.query(FocusCard).all()

# Fetch all practice attempts for a user
@app.get("/practice-attempts")
def get_practice_attempts(user_id: int = Query(...), db: Session = Depends(get_db)):
    return db.query(PracticeAttempt).filter(PracticeAttempt.user_id == user_id).all()

# Fetch all practice attempts for a user
@app.get("/practice-attempts")
def get_practice_attempts(user_id: int = Query(...), db: Session = Depends(get_db)):
    return db.query(PracticeAttempt).filter(PracticeAttempt.user_id == user_id).all()
