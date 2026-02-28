from fastapi import FastAPI, Depends, Body, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import datetime
import random
import json
from app.db import get_db
from app.models.core import User, Material, FocusCard, PracticeSession, MiniSession, PracticeAttempt, Capability, CurriculumStep, UserCapabilityProgress
from app.curriculum import (
    generate_curriculum_steps, 
    filter_materials_by_capabilities, 
    filter_materials_by_range,
    filter_keys_by_range,
    select_key_for_mini_session,
    get_goals_for_fatigue,
    insert_recovery_steps,
    CURRICULUM_TEMPLATES,
    should_introduce_capability,
    get_next_capability_to_introduce,
    generate_capability_lesson_steps,
    get_capabilities_for_material,
    get_help_menu_capabilities,
)
from app.session_config import (
    select_capability,
    select_difficulty,
    select_intensity,
    select_novelty_or_reinforcement,
    estimate_mini_session_duration,
    should_show_notation,
    get_adjusted_capability_weights,
    CAPABILITY_WEIGHTS,
    DIFFICULTY_WEIGHTS,
    NOVELTY_REINFORCEMENT,
    AVG_MINI_SESSION_MINUTES,
    WRAP_UP_THRESHOLD_MINUTES,
    KEYS_PER_INTENSITY,
    MAX_MATERIAL_REPEATS_PER_SESSION,
)
from app.spaced_repetition import (
    SpacedRepetitionItem,
    build_sr_item_from_db,
    select_materials_with_sr,
    get_review_stats,
    estimate_mastery_level,
    prioritize_materials,
    get_capability_weight_adjustment,
)
from sqlalchemy.orm import Session

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development, allow all. Restrict in production.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Models ---
class OnboardingIn(BaseModel):
    user_id: int = 1
    instrument: str
    resonant_note: str
    comfortable_capabilities: List[str]

class SelfDirectedSessionIn(BaseModel):
    user_id: int = 1
    planned_duration_minutes: int = 30
    material_id: int
    focus_card_id: int
    goal_type: str

class PracticeAttemptIn(BaseModel):
    user_id: int
    material_id: int
    key: Optional[str] = None
    focus_card_id: Optional[int] = None
    rating: int
    fatigue: int
    timestamp: datetime.datetime

class MiniSessionOut(BaseModel):
    material_id: int
    material_title: str
    focus_card_id: int
    focus_card_name: str
    focus_card_description: str = ""
    focus_card_category: str = ""
    focus_card_attention_cue: str = ""
    focus_card_micro_cues: List[str] = []
    focus_card_prompts: dict = {}
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

class FocusCardOut(BaseModel):
    id: int
    name: str
    description: str = ""
    category: str = ""
    attention_cue: str = ""
    micro_cues: List[str] = []
    prompts: dict = {}

    class Config:
        from_attributes = True


# --- Onboarding Endpoints ---
@app.get("/onboarding/{user_id}")
def get_onboarding(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return {
        "user_id": user.id,
        "instrument": user.instrument,
        "resonant_note": user.resonant_note,
        "comfortable_capabilities": user.comfortable_capabilities.split(",") if user.comfortable_capabilities else []
    }

@app.post("/onboarding")
def save_onboarding(data: OnboardingIn = Body(...), db: Session = Depends(get_db)):
    user = db.query(User).filter_by(id=data.user_id).first()
    if not user:
        # Create user if not exists
        user = User(id=data.user_id, email=f"user{data.user_id}@example.com")
        db.add(user)
    user.instrument = data.instrument
    user.resonant_note = data.resonant_note
    user.comfortable_capabilities = ",".join(data.comfortable_capabilities)
    db.commit()
    return {"status": "success", "user_id": user.id}


# --- Session Generation ---
GOAL_LABEL_MAP = {
    "repertoire_fluency": "Repertoire Fluency",
    "fluency_through_keys": "Fluency Through Keys",
    "range_expansion": "Range Expansion",
    "articulation_development": "Articulation Development",
    "tempo_build": "Tempo Building",
    "dynamic_control": "Dynamic Control",
    "learn_by_ear": "Learn By Ear",
    "musical_phrase_flow": "Musical Phrase Flow",
}

def get_starting_pitch(material, target_key):
    """Determine starting pitch based on material's pitch reference type."""
    if material.pitch_reference_type == "TONAL":
        try:
            ref = json.loads(material.pitch_ref_json) if material.pitch_ref_json else {}
            tonic = ref.get("tonic", "C")
            return f"{tonic}4"
        except Exception:
            return "C4"
    elif material.pitch_reference_type == "ANCHOR_INTERVAL":
        try:
            if target_key:
                tonic = target_key.split()[0]
                return f"{tonic}4" if tonic else "C4"
        except Exception:
            pass
        return "C4"
    return "C4"

def parse_focus_card_json_field(value):
    """Parse a JSON string field, returning empty structure if invalid."""
    if not value:
        return []
    try:
        return json.loads(value)
    except Exception:
        return []

def build_mini_session_out(material, focus_card, goal_type, target_key: str = None):
    """Build a MiniSessionOut from material and focus card."""
    if not target_key:
        target_key = material.original_key_center or "C major"
    prompts_data = parse_focus_card_json_field(focus_card.prompts)
    return MiniSessionOut(
        material_id=material.id,
        material_title=material.title,
        focus_card_id=focus_card.id,
        focus_card_name=focus_card.name,
        focus_card_description=focus_card.description or "",
        focus_card_category=focus_card.category or "",
        focus_card_attention_cue=focus_card.attention_cue or "",
        focus_card_micro_cues=parse_focus_card_json_field(focus_card.micro_cues),
        focus_card_prompts=prompts_data if isinstance(prompts_data, dict) else {},
        goal_type=goal_type,
        goal_label=GOAL_LABEL_MAP.get(goal_type, goal_type.replace("_", " ").title()),
        show_notation=random.random() < 0.2,
        target_key=target_key,
        original_key_center=material.original_key_center or "C major",
        resolved_musicxml=material.musicxml_canonical or "<musicxml/>",
        starting_pitch=get_starting_pitch(material, target_key)
    )


@app.post("/generate-session", response_model=PracticeSessionResponse)
def generate_session(
    user_id: int = 1, 
    planned_duration_minutes: int = 30, 
    fatigue: int = 2,
    cooldown_mode: bool = False,
    ear_only_mode: bool = False,
    db: Session = Depends(get_db)
):
    """
    Generate a practice session using probabilistic selection with time budgeting.
    Implements: Novelty/Reinforcement, Capability weights, Difficulty, Time budgeting.
    
    Modes:
    - cooldown_mode: Very light playing, breathing exercises (fatigue 5 option)
    - ear_only_mode: Listen and sing only, no instrument (fatigue 5 option)
    """
    materials = db.query(Material).all()
    focus_cards = db.query(FocusCard).all()
    if not materials or not focus_cards:
        raise HTTPException(status_code=500, detail="No materials or focus cards in DB")
    
    # Force certain settings for special modes
    if ear_only_mode:
        fatigue = 5  # Force fatigue 5 behavior
    elif cooldown_mode:
        fatigue = max(fatigue, 4)  # At least fatigue 4 behavior
    
    # Get user's practice history for novelty/reinforcement decisions
    user = db.query(User).filter_by(id=user_id).first()
    recent_attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).order_by(
        PracticeAttempt.timestamp.desc()
    ).limit(50).all()
    recently_practiced_material_ids = {a.material_id for a in recent_attempts}
    
    # Build attempt history for spaced repetition
    all_attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    attempt_history = {}
    for a in all_attempts:
        if a.material_id not in attempt_history:
            attempt_history[a.material_id] = []
        attempt_history[a.material_id].append({
            "rating": a.rating,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        })
    
    mini_sessions = []
    mini_session_objs = []
    
    # Time budgeting state
    time_remaining = float(planned_duration_minutes)
    
    # Session state for anti-repetition
    used_materials = set()
    used_focus_cards = set()
    recent_capabilities = []
    recent_keys = set()
    
    # Generate mini-sessions until time budget exhausted
    while time_remaining > 0:
        # Step 1: Decide novelty vs reinforcement
        selection_mode = select_novelty_or_reinforcement()
        
        # Step 2: Choose capability bucket (considering fatigue and anti-repetition)
        capability = select_capability(
            fatigue=fatigue,
            recent_capabilities=recent_capabilities,
            time_remaining=time_remaining
        )
        recent_capabilities.append(capability)
        
        # Step 3: Choose difficulty
        difficulty = select_difficulty()
        
        # Step 4: Select intensity (constrained by time remaining)
        intensity = select_intensity(time_remaining)
        
        # Step 5: Select material using spaced repetition
        # Build SR items for unused materials
        available = [m for m in materials if m.id not in used_materials]
        if not available:
            available = materials  # Fallback
        
        # Filter by user's range if available
        if user and user.range_low and user.range_high:
            range_filtered = filter_materials_by_range(available, user.range_low, user.range_high)
            if range_filtered:
                available = range_filtered
        
        # Use spaced repetition for smart selection
        sr_items = {}
        for m in available:
            mat_attempts = attempt_history.get(m.id, [])
            sr_item = build_sr_item_from_db(m.id, mat_attempts)
            sr_items[m.id] = sr_item
        
        if selection_mode == "novelty":
            # Prefer materials never reviewed (new)
            new_materials = [m for m in available if sr_items[m.id].repetitions == 0]
            if new_materials:
                material = random.choice(new_materials)
            else:
                material = random.choice(available)
        else:
            # Reinforcement: use SR weighting (due items get higher weight)
            weights = [get_capability_weight_adjustment(sr_items[m.id]) for m in available]
            total_weight = sum(weights)
            if total_weight > 0:
                probs = [w / total_weight for w in weights]
                material = random.choices(available, weights=probs, k=1)[0]
            else:
                material = random.choice(available)
        
        used_materials.add(material.id)
        
        # Step 6: Choose goal based on capability and fatigue
        available_goals = get_goals_for_fatigue(fatigue)
        # Map capability to preferred goals
        capability_goal_map = {
            "repertoire_fluency": ["repertoire_fluency", "fluency_through_keys", "musical_phrase_flow"],
            "technique": ["articulation_development", "tempo_build"],
            "range_expansion": ["range_expansion"],
            "rhythm": ["tempo_build", "repertoire_fluency"],
            "ear_training": ["learn_by_ear", "musical_phrase_flow"],
            "articulation": ["articulation_development", "dynamic_control"],
        }
        preferred_goals = capability_goal_map.get(capability, list(GOAL_LABEL_MAP.keys()))
        # Intersect with fatigue-appropriate goals
        valid_goals = [g for g in preferred_goals if g in available_goals]
        if not valid_goals:
            valid_goals = available_goals
        goal_type = random.choice(valid_goals)
        
        # Step 7: Choose focus card (prefer matching category if available)
        category_for_capability = {
            "repertoire_fluency": "MUSICIANSHIP",
            "technique": "PHYSICAL",
            "range_expansion": "PHYSICAL",
            "rhythm": "TIME",
            "ear_training": "LISTENING",
            "articulation": "PHYSICAL",
        }
        preferred_category = category_for_capability.get(capability)
        
        available_fc = [fc for fc in focus_cards if fc.id not in used_focus_cards]
        if not available_fc:
            available_fc = focus_cards
        
        # Prefer focus cards matching category
        category_matched = [fc for fc in available_fc if fc.category == preferred_category]
        if category_matched:
            focus_card = random.choice(category_matched)
        else:
            focus_card = random.choice(available_fc)
        used_focus_cards.add(focus_card.id)
        
        # Step 8: Select key filtered by user's range
        user_range_low = user.range_low if user else None
        user_range_high = user.range_high if user else None
        
        selected_key = select_key_for_mini_session(
            material=material,
            user_range_low=user_range_low,
            user_range_high=user_range_high,
            used_keys=recent_keys,
            prefer_original=(selection_mode == "reinforcement")  # Prefer familiar keys for reinforcement
        )
        recent_keys.add(selected_key.split()[0])  # Track just the tonic
        
        # Check if key is playable - if not, mark for listen/sing mode
        playable_keys = filter_keys_by_range(
            [k.strip() for k in (material.allowed_keys or "C").split(",")],
            material,
            user_range_low,
            user_range_high
        )
        mode_listen_only = len(playable_keys) == 0
        
        # Build mini-session output with notation decision
        mini_session = build_mini_session_out(material, focus_card, goal_type, target_key=selected_key)
        mini_session.show_notation = should_show_notation()
        
        # If no playable keys, this is listen/sing mode (ear-first only, no PLAY steps)
        if mode_listen_only:
            mini_session.show_notation = False  # Ear-first: no notation for out-of-range material
        
        mini_sessions.append(mini_session)
        
        # Track the mini-session object for DB
        mini_session_objs.append(MiniSession(
            material_id=material.id,
            key=mini_session.target_key,
            focus_card_id=focus_card.id,
            goal_type=goal_type
        ))
        
        # Step 8: Update time remaining
        estimated_duration = estimate_mini_session_duration(capability, intensity)
        time_remaining -= estimated_duration
        
        # Safety: ensure we don't create infinite sessions
        if len(mini_sessions) >= 10:
            break
    
    # Create session record
    session_obj = PracticeSession(
        user_id=user_id,
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
        user_id=user_id,
        planned_duration_minutes=planned_duration_minutes,
        generated_at=session_obj.started_at,
        mini_sessions=mini_sessions
    )


@app.post("/generate-self-directed-session", response_model=PracticeSessionResponse)
def generate_self_directed_session(data: SelfDirectedSessionIn = Body(...), db: Session = Depends(get_db)):
    material = db.query(Material).filter(Material.id == data.material_id).first()
    focus_card = db.query(FocusCard).filter(FocusCard.id == data.focus_card_id).first()
    if not material or not focus_card:
        raise HTTPException(status_code=400, detail="Invalid material or focus card")
    
    mini_session = build_mini_session_out(material, focus_card, data.goal_type)
    mini_sessions = [mini_session]
    
    mini_session_obj = MiniSession(
        material_id=material.id,
        key=mini_session.target_key,
        focus_card_id=focus_card.id,
        goal_type=data.goal_type
    )
    
    session_obj = PracticeSession(
        user_id=data.user_id,
        started_at=datetime.datetime.now(),
        ended_at=None
    )
    db.add(session_obj)
    db.flush()
    mini_session_obj.practice_session_id = session_obj.id
    db.add(mini_session_obj)
    db.commit()
    
    return PracticeSessionResponse(
        session_id=session_obj.id,
        user_id=data.user_id,
        planned_duration_minutes=data.planned_duration_minutes,
        generated_at=session_obj.started_at,
        mini_sessions=mini_sessions
    )


# --- Practice Attempts ---
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

@app.get("/practice-attempts")
def get_practice_attempts(user_id: int = Query(...), db: Session = Depends(get_db)):
    attempts = db.query(PracticeAttempt).filter(PracticeAttempt.user_id == user_id).all()
    return [
        {
            "id": a.id,
            "material_id": a.material_id,
            "key": a.key,
            "focus_card_id": a.focus_card_id,
            "rating": a.rating,
            "fatigue": a.fatigue,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None
        }
        for a in attempts
    ]


# --- History & Analytics Endpoints ---
@app.get("/history/summary")
def get_history_summary(user_id: int = Query(...), db: Session = Depends(get_db)):
    """Get practice history summary with spaced repetition stats."""
    # Get all attempts
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    materials = db.query(Material).all()
    
    # Build attempt history by material
    attempt_history = {}
    for a in attempts:
        if a.material_id not in attempt_history:
            attempt_history[a.material_id] = []
        attempt_history[a.material_id].append({
            "rating": a.rating,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            "fatigue": a.fatigue,
        })
    
    # Build SR items
    sr_items = []
    for m in materials:
        mat_attempts = attempt_history.get(m.id, [])
        sr_item = build_sr_item_from_db(m.id, mat_attempts)
        sr_items.append(sr_item)
    
    # Get review stats
    stats = get_review_stats(sr_items)
    
    # Calculate streaks
    sessions = db.query(PracticeSession).filter_by(user_id=user_id).order_by(PracticeSession.started_at.desc()).all()
    
    # Calculate current streak (consecutive days with practice)
    current_streak = 0
    if sessions:
        today = datetime.datetime.now().date()
        check_date = today
        session_dates = set(s.started_at.date() for s in sessions if s.started_at)
        
        while check_date in session_dates:
            current_streak += 1
            check_date -= datetime.timedelta(days=1)
    
    # Total practice time (estimate based on sessions)
    total_sessions = len(sessions)
    total_attempts = len(attempts)
    
    # Average rating
    avg_rating = sum(a.rating for a in attempts) / len(attempts) if attempts else 0
    
    return {
        "total_sessions": total_sessions,
        "total_attempts": total_attempts,
        "current_streak_days": current_streak,
        "average_rating": round(avg_rating, 2),
        "spaced_repetition": stats,
    }


@app.get("/history/materials")
def get_material_history(user_id: int = Query(...), db: Session = Depends(get_db)):
    """Get practice history for each material with mastery level."""
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    materials = db.query(Material).all()
    
    # Build attempt history by material
    attempt_history = {}
    for a in attempts:
        if a.material_id not in attempt_history:
            attempt_history[a.material_id] = []
        attempt_history[a.material_id].append({
            "id": a.id,
            "rating": a.rating,
            "timestamp": a.timestamp,
            "fatigue": a.fatigue,
            "key": a.key,
        })
    
    result = []
    for m in materials:
        mat_attempts = attempt_history.get(m.id, [])
        sr_item = build_sr_item_from_db(m.id, [
            {"rating": a["rating"], "timestamp": a["timestamp"]} for a in mat_attempts
        ])
        
        # Calculate stats for this material
        ratings = [a["rating"] for a in mat_attempts]
        avg_rating = sum(ratings) / len(ratings) if ratings else None
        last_practiced = max((a["timestamp"] for a in mat_attempts if a["timestamp"]), default=None)
        
        result.append({
            "material_id": m.id,
            "material_title": m.title,
            "attempt_count": len(mat_attempts),
            "average_rating": round(avg_rating, 2) if avg_rating else None,
            "last_practiced": last_practiced.isoformat() if last_practiced else None,
            "mastery_level": estimate_mastery_level(sr_item),
            "ease_factor": round(sr_item.ease_factor, 2),
            "interval_days": sr_item.interval,
            "next_review": sr_item.next_review.isoformat() if sr_item.next_review else None,
            "is_due": sr_item.is_due(),
        })
    
    # Sort by due status, then by overdue-ness
    result.sort(key=lambda x: (not x["is_due"], x.get("next_review") or "9999"))
    
    return result


@app.get("/history/timeline")
def get_practice_timeline(
    user_id: int = Query(...),
    days: int = Query(default=30),
    db: Session = Depends(get_db)
):
    """Get practice activity over time for visualization."""
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days)
    
    attempts = db.query(PracticeAttempt).filter(
        PracticeAttempt.user_id == user_id,
        PracticeAttempt.timestamp >= cutoff
    ).order_by(PracticeAttempt.timestamp).all()
    
    # Group by date
    daily_stats = {}
    for a in attempts:
        if not a.timestamp:
            continue
        date_str = a.timestamp.date().isoformat()
        if date_str not in daily_stats:
            daily_stats[date_str] = {"date": date_str, "attempts": 0, "total_rating": 0, "avg_fatigue": 0, "fatigue_sum": 0}
        daily_stats[date_str]["attempts"] += 1
        daily_stats[date_str]["total_rating"] += a.rating
        daily_stats[date_str]["fatigue_sum"] += a.fatigue
    
    # Calculate averages
    result = []
    for date_str, stats in sorted(daily_stats.items()):
        count = stats["attempts"]
        result.append({
            "date": date_str,
            "attempts": count,
            "avg_rating": round(stats["total_rating"] / count, 2) if count else 0,
            "avg_fatigue": round(stats["fatigue_sum"] / count, 2) if count else 0,
        })
    
    return result


@app.get("/history/focus-cards")
def get_focus_card_history(user_id: int = Query(...), db: Session = Depends(get_db)):
    """Get practice history grouped by focus card."""
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    focus_cards = db.query(FocusCard).all()
    fc_map = {fc.id: fc for fc in focus_cards}
    
    # Group by focus card
    fc_stats = {}
    for a in attempts:
        fc_id = a.focus_card_id
        if fc_id not in fc_stats:
            fc = fc_map.get(fc_id)
            fc_stats[fc_id] = {
                "focus_card_id": fc_id,
                "focus_card_name": fc.name if fc else "Unknown",
                "category": fc.category if fc else "",
                "attempts": 0,
                "ratings": [],
            }
        fc_stats[fc_id]["attempts"] += 1
        fc_stats[fc_id]["ratings"].append(a.rating)
    
    result = []
    for fc_id, stats in fc_stats.items():
        ratings = stats["ratings"]
        result.append({
            "focus_card_id": fc_id,
            "focus_card_name": stats["focus_card_name"],
            "category": stats["category"],
            "attempt_count": stats["attempts"],
            "average_rating": round(sum(ratings) / len(ratings), 2) if ratings else None,
            "best_rating": max(ratings) if ratings else None,
            "recent_trend": "improving" if len(ratings) >= 3 and ratings[-1] > ratings[-3] else (
                "declining" if len(ratings) >= 3 and ratings[-1] < ratings[-3] else "stable"
            ),
        })
    
    result.sort(key=lambda x: x["attempt_count"], reverse=True)
    return result


@app.get("/history/due-items")
def get_due_items(user_id: int = Query(...), limit: int = Query(default=10), db: Session = Depends(get_db)):
    """Get materials due for review based on spaced repetition."""
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    materials = db.query(Material).all()
    
    # Build attempt history
    attempt_history = {}
    for a in attempts:
        if a.material_id not in attempt_history:
            attempt_history[a.material_id] = []
        attempt_history[a.material_id].append({
            "rating": a.rating,
            "timestamp": a.timestamp.isoformat() if a.timestamp else None,
        })
    
    # Build SR items
    sr_items = []
    mat_map = {m.id: m for m in materials}
    for m in materials:
        mat_attempts = attempt_history.get(m.id, [])
        sr_item = build_sr_item_from_db(m.id, mat_attempts)
        sr_items.append(sr_item)
    
    # Prioritize by due status
    prioritized = prioritize_materials(sr_items, limit=limit)
    
    result = []
    for sr_item in prioritized:
        mat = mat_map.get(sr_item.material_id)
        if not mat:
            continue
        result.append({
            "material_id": sr_item.material_id,
            "material_title": mat.title,
            "mastery_level": estimate_mastery_level(sr_item),
            "days_overdue": round(sr_item.days_overdue(), 1),
            "is_due": sr_item.is_due(),
            "interval_days": sr_item.interval,
            "ease_factor": round(sr_item.ease_factor, 2),
        })
    
    return result


# --- Materials ---
@app.get("/materials")
def get_materials(db: Session = Depends(get_db)):
    materials = db.query(Material).all()
    return [
        {
            "id": m.id,
            "title": m.title,
            "allowed_keys": m.allowed_keys.split(",") if m.allowed_keys else [],
            "original_key_center": m.original_key_center,
            "pitch_reference_type": m.pitch_reference_type
        }
        for m in materials
    ]


# --- Focus Cards ---
@app.get("/focus-cards", response_model=List[FocusCardOut])
def get_focus_cards(db: Session = Depends(get_db)):
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


# --- Capabilities ---
@app.get("/capabilities")
def get_capabilities(db: Session = Depends(get_db)):
    capabilities = db.query(Capability).all()
    return [{"id": c.id, "name": c.name} for c in capabilities]


# --- User Endpoints ---
@app.get("/users/{user_id}")
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


# --- Session Completion ---
@app.post("/sessions/{session_id}/complete")
def complete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(PracticeSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.ended_at = datetime.datetime.now()
    db.commit()
    return {"status": "success", "session_id": session_id}


# --- Curriculum Step Endpoints ---
class CurriculumStepOut(BaseModel):
    id: int
    step_index: int
    step_type: str
    instruction: str
    prompt: str = ""
    is_completed: bool = False
    rating: Optional[int] = None

class MiniSessionWithStepsOut(BaseModel):
    mini_session_id: int
    material_title: str
    focus_card_name: str
    focus_card_attention_cue: str
    goal_type: str
    goal_label: str
    target_key: str
    current_step_index: int
    is_completed: bool
    steps: List[CurriculumStepOut]

@app.get("/mini-sessions/{mini_session_id}/curriculum")
def get_mini_session_curriculum(mini_session_id: int, db: Session = Depends(get_db)):
    """Get the full curriculum for a mini-session with all steps."""
    mini = db.query(MiniSession).filter_by(id=mini_session_id).first()
    if not mini:
        raise HTTPException(status_code=404, detail="Mini-session not found")
    
    material = db.query(Material).filter_by(id=mini.material_id).first()
    focus_card = db.query(FocusCard).filter_by(id=mini.focus_card_id).first()
    
    # Get or generate curriculum steps
    steps = db.query(CurriculumStep).filter_by(mini_session_id=mini_session_id).order_by(CurriculumStep.step_index).all()
    
    if not steps:
        # Generate steps on first access
        prompts = parse_focus_card_json_field(focus_card.prompts) if focus_card else {}
        step_data = generate_curriculum_steps(
            goal_type=mini.goal_type or "repertoire_fluency",
            focus_card_prompts=prompts if isinstance(prompts, dict) else {},
            material_title=material.title if material else "Unknown",
            target_key=mini.key or "C major",
            fatigue_level=2
        )
        
        # Insert recovery steps for range work
        if mini.goal_type == "range_expansion":
            step_data = insert_recovery_steps(step_data, after_play_count=1)
        
        for sd in step_data:
            step = CurriculumStep(
                mini_session_id=mini_session_id,
                step_index=sd["step_index"],
                step_type=sd["step_type"],
                instruction=sd["instruction"],
                prompt=sd["prompt"],
                is_completed=False
            )
            db.add(step)
        db.commit()
        steps = db.query(CurriculumStep).filter_by(mini_session_id=mini_session_id).order_by(CurriculumStep.step_index).all()
    
    return MiniSessionWithStepsOut(
        mini_session_id=mini.id,
        material_title=material.title if material else "Unknown",
        focus_card_name=focus_card.name if focus_card else "Unknown",
        focus_card_attention_cue=focus_card.attention_cue if focus_card else "",
        goal_type=mini.goal_type or "",
        goal_label=GOAL_LABEL_MAP.get(mini.goal_type, "Practice"),
        target_key=mini.key or "C major",
        current_step_index=mini.current_step_index or 0,
        is_completed=mini.is_completed or False,
        steps=[CurriculumStepOut(
            id=s.id,
            step_index=s.step_index,
            step_type=s.step_type,
            instruction=s.instruction,
            prompt=s.prompt or "",
            is_completed=s.is_completed or False,
            rating=s.rating
        ) for s in steps]
    )


class StepCompleteIn(BaseModel):
    rating: Optional[int] = None
    notes: Optional[str] = None
    strain_detected: bool = False

@app.post("/mini-sessions/{mini_session_id}/steps/{step_index}/complete")
def complete_step(mini_session_id: int, step_index: int, data: StepCompleteIn = Body(...), db: Session = Depends(get_db)):
    """Mark a curriculum step as complete and advance to next step."""
    mini = db.query(MiniSession).filter_by(id=mini_session_id).first()
    if not mini:
        raise HTTPException(status_code=404, detail="Mini-session not found")
    
    step = db.query(CurriculumStep).filter_by(mini_session_id=mini_session_id, step_index=step_index).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")
    
    # Mark step complete
    step.is_completed = True
    step.rating = data.rating
    step.notes = data.notes
    
    # Handle strain detection for range work
    if data.strain_detected and mini.goal_type == "range_expansion":
        mini.strain_detected = True
        mini.is_completed = True  # Terminate immediately on strain
        db.commit()
        return {
            "status": "strain_detected", 
            "message": "Session terminated for safety. Take a break.",
            "attempt_count": mini.attempt_count or 0
        }
    
    # Track attempts for range expansion (max 3 failed attempts)
    if step.step_type == "PLAY" and mini.goal_type == "range_expansion":
        # Count as failed attempt if rating is low (< 3) or no rating given
        is_failed_attempt = (data.rating is None) or (data.rating < 3)
        if is_failed_attempt:
            mini.attempt_count = (mini.attempt_count or 0) + 1
        
        if mini.attempt_count >= 3:
            mini.is_completed = True
            db.commit()
            return {
                "status": "max_attempts", 
                "message": "Maximum range attempts reached. Take a recovery break.",
                "attempt_count": mini.attempt_count
            }
    
    # Check if there are more steps
    next_step = db.query(CurriculumStep).filter_by(mini_session_id=mini_session_id, step_index=step_index + 1).first()
    
    if next_step:
        mini.current_step_index = step_index + 1
        db.commit()
        return {
            "status": "next_step",
            "next_step_index": step_index + 1,
            "next_step_type": next_step.step_type,
            "next_instruction": next_step.instruction,
            "attempt_count": mini.attempt_count or 0,
            "is_range_work": mini.goal_type == "range_expansion"
        }
    else:
        mini.is_completed = True
        mini.current_step_index = step_index
        db.commit()
        return {"status": "completed", "message": "Mini-session complete!"}


@app.get("/sessions/{session_id}/next-mini-session")
def get_next_mini_session(session_id: int, db: Session = Depends(get_db)):
    """Get the next incomplete mini-session in a practice session."""
    session = db.query(PracticeSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Find first incomplete mini-session
    mini = db.query(MiniSession).filter_by(
        practice_session_id=session_id,
        is_completed=False
    ).order_by(MiniSession.id).first()
    
    if not mini:
        return {"status": "session_complete", "message": "All mini-sessions complete!"}
    
    # Return the mini-session with its curriculum
    return get_mini_session_curriculum(mini.id, db)


# --- User Range Management ---
class UserRangeIn(BaseModel):
    range_low: str  # e.g., "E3"
    range_high: str  # e.g., "C6"

@app.patch("/users/{user_id}/range")
def update_user_range(user_id: int, data: UserRangeIn = Body(...), db: Session = Depends(get_db)):
    """Update user's comfortable playing range."""
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.range_low = data.range_low
    user.range_high = data.range_high
    db.commit()
    return {"status": "success", "range_low": user.range_low, "range_high": user.range_high}


# --- Health Check ---
@app.get("/health")
def health_check():
    return {"status": "healthy"}


# --- Session Config Endpoints ---
@app.get("/config")
def get_session_config():
    """Get current session generation configuration."""
    return {
        "capability_weights": CAPABILITY_WEIGHTS,
        "difficulty_weights": DIFFICULTY_WEIGHTS,
        "novelty_reinforcement": NOVELTY_REINFORCEMENT,
        "avg_mini_session_minutes": AVG_MINI_SESSION_MINUTES,
        "wrap_up_threshold_minutes": WRAP_UP_THRESHOLD_MINUTES,
        "keys_per_intensity": KEYS_PER_INTENSITY,
    }


class ConfigUpdateIn(BaseModel):
    capability_weights: Optional[dict] = None
    difficulty_weights: Optional[dict] = None
    novelty_reinforcement: Optional[dict] = None

@app.patch("/config")
def update_session_config(data: ConfigUpdateIn = Body(...)):
    """
    Update session generation configuration at runtime.
    Changes are applied immediately but not persisted across restarts.
    """
    import app.session_config as config
    
    updated = []
    
    if data.capability_weights:
        config.CAPABILITY_WEIGHTS.update(data.capability_weights)
        updated.append("capability_weights")
    
    if data.difficulty_weights:
        config.DIFFICULTY_WEIGHTS.update(data.difficulty_weights)
        updated.append("difficulty_weights")
    
    if data.novelty_reinforcement:
        config.NOVELTY_REINFORCEMENT.update(data.novelty_reinforcement)
        updated.append("novelty_reinforcement")
    
    return {"status": "success", "updated": updated}


# =============================================================================
# MICRO-TEACHING BLOCKS
# =============================================================================

@app.get("/capabilities/{capability_id}/lesson")
def get_capability_lesson(capability_id: int, db: Session = Depends(get_db)):
    """
    Get a mini-lesson for a specific capability.
    
    Returns curriculum steps following: LISTEN → EXPLAIN → VISUAL → TRY_IT → QUIZ
    """
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if not cap.explanation:
        raise HTTPException(status_code=400, detail="Capability has no teaching content")
    
    # Build capability dict from model
    cap_dict = {
        "name": cap.name,
        "display_name": cap.display_name or cap.name,
        "explanation": cap.explanation,
        "visual_example_url": cap.visual_example_url,
        "audio_example_url": cap.audio_example_url,
        "quiz_type": cap.quiz_type,
        "quiz_question": cap.quiz_question,
        "quiz_options": cap.quiz_options,
        "quiz_answer": cap.quiz_answer,
    }
    
    steps = generate_capability_lesson_steps(cap_dict)
    
    return {
        "capability_id": cap.id,
        "capability_name": cap.display_name or cap.name,
        "domain": cap.domain,
        "steps": steps
    }


class QuizResultIn(BaseModel):
    user_id: int
    passed: bool
    answer_given: Optional[str] = None


@app.post("/capabilities/{capability_id}/quiz-result")
def record_quiz_result(
    capability_id: int, 
    data: QuizResultIn = Body(...), 
    db: Session = Depends(get_db)
):
    """
    Record the result of a capability quiz.
    
    Updates or creates UserCapabilityProgress record.
    """
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    user = db.query(User).filter_by(id=data.user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Find or create progress record
    progress = db.query(UserCapabilityProgress).filter_by(
        user_id=data.user_id,
        capability_id=capability_id
    ).first()
    
    if not progress:
        progress = UserCapabilityProgress(
            user_id=data.user_id,
            capability_id=capability_id,
            introduced_at=datetime.datetime.utcnow(),
            quiz_passed=data.passed,
            times_refreshed=0
        )
        db.add(progress)
    else:
        progress.quiz_passed = data.passed
        progress.times_refreshed += 1
    
    db.commit()
    
    return {
        "status": "success",
        "capability_id": capability_id,
        "passed": data.passed,
        "times_refreshed": progress.times_refreshed
    }


@app.get("/materials/{material_id}/help-capabilities")
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
    
    # Fetch full capability info
    capabilities = []
    for cap_name in cap_names:
        cap = db.query(Capability).filter_by(name=cap_name).first()
        if cap:
            capabilities.append({
                "id": cap.id,
                "name": cap.name,
                "display_name": cap.display_name or cap.name,
                "domain": cap.domain,
                "has_lesson": bool(cap.explanation)
            })
    
    return {
        "material_id": material_id,
        "material_title": material.title,
        "capabilities": capabilities
    }


@app.get("/users/{user_id}/capability-progress")
def get_user_capability_progress(user_id: int, db: Session = Depends(get_db)):
    """
    Get user's progress on capability learning.
    
    Returns stats on known vs unknown capabilities and recent introductions.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all progress records
    progress_records = db.query(UserCapabilityProgress).filter_by(user_id=user_id).all()
    
    # Get all capabilities
    all_caps = db.query(Capability).filter(Capability.explanation != None).all()
    total_teachable = len(all_caps)
    
    known_caps = [p for p in progress_records if p.quiz_passed]
    introduced_but_not_passed = [p for p in progress_records if not p.quiz_passed]
    
    # Calculate sessions since last intro (approximation)
    last_intro = None
    if progress_records:
        intros = [p.introduced_at for p in progress_records if p.introduced_at]
        if intros:
            last_intro = max(intros)
    
    return {
        "user_id": user_id,
        "total_teachable_capabilities": total_teachable,
        "capabilities_known": len(known_caps),
        "capabilities_in_progress": len(introduced_but_not_passed),
        "last_introduction": last_intro.isoformat() if last_intro else None,
        "known_capability_names": [p.capability_id for p in known_caps]
    }


@app.get("/users/{user_id}/next-capability")
def get_next_capability_for_user(user_id: int, db: Session = Depends(get_db)):
    """
    Get the next capability that should be introduced to the user.
    
    Based on sequence order and user's current knowledge.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's known capabilities
    progress = db.query(UserCapabilityProgress).filter_by(
        user_id=user_id,
        quiz_passed=True
    ).all()
    known_cap_ids = [p.capability_id for p in progress]
    
    # Get names of known caps
    known_cap_names = []
    for cap_id in known_cap_ids:
        cap = db.query(Capability).filter_by(id=cap_id).first()
        if cap:
            known_cap_names.append(cap.name)
    
    # Get all capabilities ordered by sequence
    all_caps = db.query(Capability).filter(
        Capability.explanation != None,
        Capability.sequence_order != None
    ).order_by(Capability.sequence_order).all()
    
    # Build list for the logic function
    caps_list = []
    for cap in all_caps:
        caps_list.append({
            "id": cap.id,
            "name": cap.name,
            "display_name": cap.display_name,
            "sequence_order": cap.sequence_order,
            "explanation": cap.explanation,
            "domain": cap.domain
        })
    
    next_cap = get_next_capability_to_introduce(known_cap_names, caps_list)
    
    if not next_cap:
        return {"message": "All capabilities learned!", "next_capability": None}
    
    return {
        "next_capability": {
            "id": next_cap.get("id"),
            "name": next_cap.get("name"),
            "display_name": next_cap.get("display_name"),
            "domain": next_cap.get("domain"),
            "sequence_order": next_cap.get("sequence_order")
        },
        "user_known_count": len(known_cap_names)
    }

