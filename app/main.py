from fastapi import FastAPI, Depends, Body, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import datetime
import random
import json
from app.db import get_db
from app.models.core import User, Material, FocusCard, PracticeSession, MiniSession, PracticeAttempt, CurriculumStep
from app.models.capability_schema import Capability, UserCapability
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
    range_low: Optional[str] = None  # e.g., "E3" - comfortable low note
    range_high: Optional[str] = None  # e.g., "C6" - comfortable high note
    comfortable_capabilities: List[str] = []

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
        "range_low": user.range_low,
        "range_high": user.range_high,
        "comfortable_capabilities": user.comfortable_capabilities.split(",") if user.comfortable_capabilities else [],
        "day0_completed": user.day0_completed if hasattr(user, 'day0_completed') else False,
        "day0_stage": user.day0_stage if hasattr(user, 'day0_stage') else 0,
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
    user.range_low = data.range_low
    user.range_high = data.range_high
    user.comfortable_capabilities = ",".join(data.comfortable_capabilities) if data.comfortable_capabilities else ""
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
    from app.curriculum import JourneyMetrics, estimate_journey_stage
    
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
    
    # Build SR items and mastery counts
    sr_items = []
    mastered_count = 0
    familiar_count = 0
    stabilizing_count = 0
    learning_count = 0
    
    for m in materials:
        mat_attempts = attempt_history.get(m.id, [])
        sr_item = build_sr_item_from_db(m.id, mat_attempts)
        sr_items.append(sr_item)
        
        if mat_attempts:
            mastery = estimate_mastery_level(sr_item)
            if mastery == "mastered":
                mastered_count += 1
            elif mastery == "familiar":
                familiar_count += 1
            elif mastery == "stabilizing":
                stabilizing_count += 1
            elif mastery in ("learning", "new"):
                learning_count += 1
    
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
    
    # Calculate days since first session
    days_since_first = 0
    if sessions:
        first_session = min(s.started_at for s in sessions if s.started_at)
        if first_session:
            days_since_first = (datetime.datetime.now() - first_session).days
    
    # Total practice time (estimate based on sessions)
    total_sessions = len(sessions)
    total_attempts = len(attempts)
    
    # Average rating
    ratings = [a.rating for a in attempts if a.rating is not None]
    avg_rating = sum(ratings) / len(ratings) if ratings else 0
    
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
    
    # Build journey metrics
    metrics = JourneyMetrics(
        total_sessions=total_sessions,
        total_attempts=total_attempts,
        days_since_first_session=days_since_first,
        average_rating=avg_rating,
        mastered_count=mastered_count,
        familiar_count=familiar_count,
        stabilizing_count=stabilizing_count,
        learning_count=learning_count,
        unique_keys_practiced=len(unique_keys),
        capabilities_introduced=cap_progress,
        self_directed_sessions=self_directed_count,
        current_streak_days=current_streak,
    )
    
    # Estimate journey stage
    stage_num, stage_name, factors = estimate_journey_stage(metrics)
    
    return {
        "total_sessions": total_sessions,
        "total_attempts": total_attempts,
        "current_streak_days": current_streak,
        "average_rating": round(avg_rating, 2),
        "spaced_repetition": stats,
        "journey_stage": {
            "stage": stage_num,
            "stage_name": stage_name,
        },
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


@app.get("/history/analytics")
def get_session_analytics(user_id: int = Query(...), db: Session = Depends(get_db)):
    """
    Comprehensive session history analytics with capability progress and time spent.
    
    Returns aggregate stats on:
    - Practice time (total minutes, average session duration)
    - Capability progress (introduced, quiz pass rate, by domain)
    - Quality metrics (rating trends, fatigue trends, strain occurrences)
    - Completion stats (mini-session completion rate)
    """
    from sqlalchemy import func
    
    # --- Time Stats ---
    sessions = db.query(PracticeSession).filter_by(user_id=user_id).all()
    
    total_minutes = 0
    session_durations = []
    for s in sessions:
        if s.started_at and s.ended_at:
            duration = (s.ended_at - s.started_at).total_seconds() / 60
            if 0 < duration < 180:  # Cap at 3 hours to filter outliers
                total_minutes += duration
                session_durations.append(duration)
    
    avg_session_minutes = sum(session_durations) / len(session_durations) if session_durations else 0
    
    # --- Capability Progress (V2) ---
    cap_progress = db.query(UserCapability).filter_by(user_id=user_id).all()
    capabilities = db.query(Capability).all()
    cap_map = {c.id: c for c in capabilities}
    
    capabilities_introduced = len([cp for cp in cap_progress if cp.introduced_at])
    capabilities_mastered = len([cp for cp in cap_progress if cp.mastered_at])
    mastery_rate = (capabilities_mastered / capabilities_introduced * 100) if capabilities_introduced else 0
    
    # Group by domain
    domain_stats = {}
    for cp in cap_progress:
        cap = cap_map.get(cp.capability_id)
        if cap:
            domain = cap.domain or "other"
            if domain not in domain_stats:
                domain_stats[domain] = {"introduced": 0, "mastered": 0, "refreshed": 0}
            domain_stats[domain]["introduced"] += 1
            if cp.mastered_at:
                domain_stats[domain]["mastered"] += 1
            domain_stats[domain]["refreshed"] += cp.times_refreshed or 0
    
    # --- Quality Metrics ---
    attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).order_by(
        PracticeAttempt.timestamp
    ).all()
    
    ratings = [a.rating for a in attempts if a.rating is not None]
    fatigues = [a.fatigue for a in attempts if a.fatigue is not None]
    
    # Recent vs overall rating trend
    overall_avg_rating = sum(ratings) / len(ratings) if ratings else 0
    recent_ratings = ratings[-10:] if len(ratings) >= 10 else ratings
    recent_avg_rating = sum(recent_ratings) / len(recent_ratings) if recent_ratings else 0
    
    # Fatigue trend
    overall_avg_fatigue = sum(fatigues) / len(fatigues) if fatigues else 0
    recent_fatigues = fatigues[-10:] if len(fatigues) >= 10 else fatigues
    recent_avg_fatigue = sum(recent_fatigues) / len(recent_fatigues) if recent_fatigues else 0
    
    # Strain occurrences
    mini_sessions = db.query(MiniSession).join(PracticeSession).filter(
        PracticeSession.user_id == user_id
    ).all()
    total_mini_sessions = len(mini_sessions)
    strain_count = sum(1 for ms in mini_sessions if ms.strain_detected)
    strain_rate = (strain_count / total_mini_sessions * 100) if total_mini_sessions else 0
    
    # --- Completion Stats ---
    completed_mini_sessions = sum(1 for ms in mini_sessions if ms.is_completed)
    completion_rate = (completed_mini_sessions / total_mini_sessions * 100) if total_mini_sessions else 0
    
    # --- Practice by Day of Week ---
    day_of_week_stats = {i: {"count": 0, "minutes": 0} for i in range(7)}  # 0=Mon, 6=Sun
    for s in sessions:
        if s.started_at:
            dow = s.started_at.weekday()
            day_of_week_stats[dow]["count"] += 1
            if s.ended_at:
                duration = (s.ended_at - s.started_at).total_seconds() / 60
                if 0 < duration < 180:
                    day_of_week_stats[dow]["minutes"] += duration
    
    day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    practice_by_day = [
        {"day": day_names[i], "sessions": day_of_week_stats[i]["count"], 
         "minutes": round(day_of_week_stats[i]["minutes"], 1)}
        for i in range(7)
    ]
    
    # --- Rating Distribution ---
    rating_distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in ratings:
        if r in rating_distribution:
            rating_distribution[r] += 1
    
    return {
        "time_stats": {
            "total_minutes": round(total_minutes, 1),
            "total_sessions": len(sessions),
            "avg_session_minutes": round(avg_session_minutes, 1),
            "total_mini_sessions": total_mini_sessions,
        },
        "capability_progress": {
            "total_introduced": capabilities_introduced,
            "total_available": len(capabilities),
            "quizzes_passed": quizzes_passed,
            "quiz_pass_rate": round(quiz_pass_rate, 1),
            "by_domain": domain_stats,
        },
        "quality_metrics": {
            "overall_avg_rating": round(overall_avg_rating, 2),
            "recent_avg_rating": round(recent_avg_rating, 2),
            "rating_trend": "improving" if recent_avg_rating > overall_avg_rating + 0.1 else (
                "declining" if recent_avg_rating < overall_avg_rating - 0.1 else "stable"
            ),
            "overall_avg_fatigue": round(overall_avg_fatigue, 2),
            "recent_avg_fatigue": round(recent_avg_fatigue, 2),
            "fatigue_trend": "increasing" if recent_avg_fatigue > overall_avg_fatigue + 0.2 else (
                "decreasing" if recent_avg_fatigue < overall_avg_fatigue - 0.2 else "stable"
            ),
            "strain_count": strain_count,
            "strain_rate": round(strain_rate, 1),
            "rating_distribution": rating_distribution,
        },
        "completion_stats": {
            "completed_mini_sessions": completed_mini_sessions,
            "total_mini_sessions": total_mini_sessions,
            "completion_rate": round(completion_rate, 1),
        },
        "practice_by_day": practice_by_day,
    }


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


# --- Audio Generation ---
@app.get("/audio/material/{material_id}")
def get_material_audio(
    material_id: int,
    key: str = Query(..., description="Target key for transposition (e.g., 'Bb major')"),
    instrument: str = Query(default="piano", description="Instrument for soundfont"),
    db: Session = Depends(get_db)
):
    """
    Generate audio for a material transposed to the specified key.
    
    Uses music21 to transpose MusicXML and FluidSynth to render audio.
    Returns WAV audio if soundfont available, otherwise MIDI.
    
    Error responses include structured error info with codes:
    - music21_not_installed: Audio library missing
    - soundfont_not_found: No .sf2 file available (returns MIDI)
    - invalid_musicxml: Bad notation content
    - midi_conversion_failed: MusicXML parsing failed
    - audio_render_failed: FluidSynth error (returns MIDI)
    """
    from fastapi.responses import Response, JSONResponse
    from app.audio import (
        generate_audio_with_result, 
        MUSIC21_AVAILABLE, 
        FLUIDSYNTH_AVAILABLE,
        AudioErrorCode
    )
    
    # Get material
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        return JSONResponse(
            status_code=404,
            content={
                "error": True,
                "code": "material_not_found",
                "message": f"Material {material_id} not found",
                "detail": None
            }
        )
    
    # Check for MusicXML content
    if not material.musicxml_canonical:
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "code": "no_musicxml",
                "message": "Material has no notation content",
                "detail": f"Material '{material.title}' does not have MusicXML data"
            }
        )
    
    # Generate audio
    result = generate_audio_with_result(
        musicxml_content=material.musicxml_canonical,
        original_key=material.original_key_center or "C major",
        target_key=key,
        instrument=instrument,
        material_id=material_id,
    )
    
    # Handle complete failure
    if not result.success and result.data is None:
        error = result.error
        # Map error codes to HTTP status codes
        status_map = {
            AudioErrorCode.MUSIC21_NOT_INSTALLED: 503,
            AudioErrorCode.INVALID_MUSICXML: 400,
            AudioErrorCode.MIDI_CONVERSION_FAILED: 422,
        }
        status_code = status_map.get(error.code, 500) if error else 500
        
        return JSONResponse(
            status_code=status_code,
            content=error.to_dict() if error else {"error": True, "message": "Unknown error"}
        )
    
    # Determine filename
    safe_title = material.title.replace(" ", "_").replace("/", "-")[:30]
    safe_key = key.replace(" ", "_")
    
    if result.content_type == "audio/wav":
        filename = f"{safe_title}_{safe_key}.wav"
    else:
        filename = f"{safe_title}_{safe_key}.mid"
    
    # Add warning header if returning fallback MIDI
    headers = {
        "Content-Disposition": f'inline; filename="{filename}"',
        "Cache-Control": "no-cache",
    }
    if result.is_fallback and result.error:
        headers["X-Audio-Warning"] = result.error.message
        headers["X-Audio-Fallback"] = "true"
    
    return Response(
        content=result.data,
        media_type=result.content_type,
        headers=headers
    )


@app.get("/audio/note/{note}")
def get_single_note_audio(
    note: str,
    instrument: str = Query(default="piano", description="Instrument for soundfont"),
    duration: int = Query(default=3, description="Duration in beats (3 = 3 seconds at 60 BPM)"),
    octave: Optional[int] = Query(default=None, description="Override octave (1-8)")
):
    """
    Generate audio for a single sustained note.
    
    Used for Day 0 first-note experience - plays a whole note for the user's
    resonant pitch so they can listen, sing, and match it.
    
    Examples:
    - /audio/note/Bb4?instrument=trombone
    - /audio/note/F%233?instrument=trumpet (F#3 URL-encoded)
    - /audio/note/Eb?octave=3&instrument=tuba
    
    Returns WAV audio if soundfont available, otherwise MIDI fallback.
    """
    from fastapi.responses import Response, JSONResponse
    from app.audio import generate_single_note_audio, AudioErrorCode
    
    # Validate octave if provided
    if octave is not None and (octave < 1 or octave > 8):
        return JSONResponse(
            status_code=400,
            content={
                "error": True,
                "code": "invalid_octave",
                "message": "Octave must be between 1 and 8",
                "detail": f"Got octave={octave}"
            }
        )
    
    # Generate audio
    result = generate_single_note_audio(
        note_name=note,
        instrument=instrument,
        duration_beats=duration,
        octave=octave
    )
    
    # Handle complete failure
    if not result.success and result.data is None:
        error = result.error
        status_map = {
            AudioErrorCode.MUSIC21_NOT_INSTALLED: 503,
            AudioErrorCode.MIDI_CONVERSION_FAILED: 400,
        }
        status_code = status_map.get(error.code, 500) if error else 500
        
        return JSONResponse(
            status_code=status_code,
            content=error.to_dict() if error else {"error": True, "message": "Unknown error"}
        )
    
    # Determine filename
    safe_note = note.replace("#", "sharp").replace("b", "flat")[:10]
    
    if result.content_type == "audio/wav":
        filename = f"note_{safe_note}.wav"
    else:
        filename = f"note_{safe_note}.mid"
    
    # Add headers
    headers = {
        "Content-Disposition": f'inline; filename="{filename}"',
        "Cache-Control": "public, max-age=3600",  # Cache single notes longer
    }
    if result.is_fallback and result.error:
        headers["X-Audio-Warning"] = result.error.message
        headers["X-Audio-Fallback"] = "true"
    
    return Response(
        content=result.data,
        media_type=result.content_type,
        headers=headers
    )


@app.get("/audio/status")
def get_audio_status():
    """Check audio generation capability."""
    from app.audio import (
        MUSIC21_AVAILABLE, 
        FLUIDSYNTH_AVAILABLE, 
        get_soundfont_path,
        get_cache_stats
    )
    from app.config import USE_DIRECT_FLUIDSYNTH
    
    soundfont = get_soundfont_path()
    
    return {
        "music21_available": MUSIC21_AVAILABLE,
        "fluidsynth_available": FLUIDSYNTH_AVAILABLE,
        "use_direct_fluidsynth": USE_DIRECT_FLUIDSYNTH,
        "soundfont_found": soundfont is not None,
        "soundfont_path": str(soundfont) if soundfont else None,
        "can_render_audio": MUSIC21_AVAILABLE and FLUIDSYNTH_AVAILABLE and soundfont is not None,
        "can_render_midi": MUSIC21_AVAILABLE,
        "cache": get_cache_stats(),
    }


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
    return [{"id": c.id, "name": c.name, "domain": c.domain} for c in capabilities]


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


@app.get("/users/{user_id}/journey-stage")
def get_user_journey_stage(user_id: int, db: Session = Depends(get_db)):
    """
    Estimate user's journey stage based on practice history.
    
    INTERNAL USE: Per spec, users are never told their stage.
    This is for adaptive system behavior only.
    
    Returns stage 1-6 with name and contributing factors.
    """
    from app.curriculum import JourneyMetrics, estimate_journey_stage
    
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


@app.post("/users/{user_id}/reset")
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


# --- User Update ---
class UserUpdateIn(BaseModel):
    day0_completed: Optional[bool] = None
    day0_stage: Optional[int] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None

# Day 0 capabilities that all users learn
DAY0_BASE_CAPABILITIES = [
    "staff_basics",       # Stage 3: The Musical Staff
    "ledger_lines",       # Stage 3: The Musical Staff (ledger lines)
    "note_basics",        # Stage 4: What is a Note?
    "first_note",         # Stage 1: Play Your Note
    "accidental_flat_symbol",    # Stage 6: Sharps & Flats
    "accidental_natural_symbol", # Stage 6: Sharps & Flats
    "accidental_sharp_symbol",   # Stage 6: Sharps & Flats
]

# Instruments that use bass clef (all others use treble)
BASS_CLEF_INSTRUMENTS = {
    "Tenor Trombone", "Bass Trombone", "Euphonium", "Tuba",
    "Bassoon", "Cello", "Double Bass", "Bass Voice",
    "trombone", "bass_trombone", "euphonium", "tuba",
    "bassoon", "cello", "double_bass", "bass_voice",
}

def grant_day0_capabilities(user, db: Session):
    """
    Grant all Day 0 capabilities to a user when they complete the first-note flow.
    
    This marks the user as having mastered:
    - staff_basics, ledger_lines, note_basics, first_note
    - accidental symbols (flat, natural, sharp)
    - their instrument's clef (treble or bass)
    """
    from app.models.capability_schema import Capability, UserCapability
    from datetime import datetime
    
    # Determine which clef to grant based on instrument
    user_instrument = user.instrument or ""
    clef_capability = "clef_bass" if user_instrument in BASS_CLEF_INSTRUMENTS else "clef_treble"
    
    # Full list of capabilities to grant
    capabilities_to_grant = DAY0_BASE_CAPABILITIES + [clef_capability]
    
    # Look up capability IDs
    caps = db.query(Capability).filter(Capability.name.in_(capabilities_to_grant)).all()
    cap_map = {c.name: c for c in caps}
    
    now = datetime.utcnow()
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

@app.patch("/users/{user_id}")
def update_user(user_id: int, data: UserUpdateIn = Body(...), db: Session = Depends(get_db)):
    """Update user fields (day0 progress, range, etc.)."""
    from app.models.capability_schema import UserCapability
    
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


# --- Client Logging ---
class ClientLogIn(BaseModel):
    event: str
    data: dict
    timestamp: Optional[str] = None

@app.post("/log/client")
def log_client_event(log: ClientLogIn = Body(...)):
    """
    Receive log events from client apps (web/mobile) for server-side logging.
    Useful for tracking startup timing, errors, and performance metrics.
    """
    import logging
    logger = logging.getLogger("client")
    
    ts = log.timestamp or datetime.datetime.now().isoformat()
    logger.info(f"[CLIENT] {log.event} | {ts} | {json.dumps(log.data)}")
    
    # Also print to stdout for uvicorn visibility
    print(f"[CLIENT LOG] {log.event} | {ts} | {json.dumps(log.data)}")
    
    return {"status": "logged"}


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
# MICRO-TEACHING BLOCKS (DEPRECATED - V1 quiz system, V2 uses evidence-based mastery)
# =============================================================================

@app.get("/capabilities/{capability_id}/lesson", deprecated=True)
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


@app.post("/capabilities/{capability_id}/quiz-result", deprecated=True)
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


@app.get("/users/{user_id}/capability-progress")
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


@app.get("/users/{user_id}/next-capability")
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


# =============================================================================
# MATERIAL UPLOAD & ANALYSIS ENDPOINTS
# =============================================================================

class MaterialUpload(BaseModel):
    """Input model for material upload."""
    title: str
    musicxml_content: str
    original_key_center: Optional[str] = None
    allowed_keys: Optional[List[str]] = None  # If not provided, will default to common keys

class MaterialAnalysisResponse(BaseModel):
    """Response model for material analysis."""
    material_id: int
    title: str
    extracted_capabilities: List[str]
    range_analysis: Optional[dict]
    chromatic_complexity: float
    measure_count: int
    warnings: List[str] = []


@app.post("/materials/upload", response_model=MaterialAnalysisResponse)
def upload_material(
    data: MaterialUpload = Body(...),
    db: Session = Depends(get_db)
):
    """
    Upload a new material from MusicXML content.
    
    This endpoint:
    1. Parses the MusicXML using music21
    2. Extracts all musical capabilities (clefs, rhythms, intervals, etc.)
    3. Creates MaterialCapability records
    4. Creates MaterialAnalysis with range/density info
    5. Computes and stores bitmask for fast eligibility checking
    """
    from app.musicxml_analyzer import MusicXMLAnalyzer, analyze_musicxml, compute_capability_bitmask
    from app.models.capability_schema import Capability, MaterialCapability, MaterialAnalysis
    
    warnings = []
    
    # Analyze the MusicXML
    try:
        analyzer = MusicXMLAnalyzer()
        extraction_result = analyzer.analyze(data.musicxml_content)
        capability_names = analyzer.get_capability_names(extraction_result)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to analyze MusicXML: {str(e)}")
    
    # Determine allowed keys
    allowed_keys = data.allowed_keys
    if not allowed_keys:
        # Default to common keys based on original key
        allowed_keys = ["C", "G", "F", "D", "Bb", "A", "Eb"]
    
    # Create the Material record
    material = Material(
        title=data.title or extraction_result.title or "Untitled",
        musicxml_canonical=data.musicxml_content,
        original_key_center=data.original_key_center,
        allowed_keys=",".join(allowed_keys),
        pitch_reference_type="TONAL",
        spelling_policy="from_key",
    )
    db.add(material)
    db.flush()  # Get the ID
    
    # Look up or create capabilities, then link to material
    capability_ids_for_bitmask = []
    
    for cap_name in capability_names:
        # Try to find existing capability
        cap = db.query(Capability).filter_by(name=cap_name).first()
        
        if not cap:
            # Capability doesn't exist - create a placeholder
            # (In production, you'd want to seed all known capabilities first)
            domain = cap_name.split("_")[0] if "_" in cap_name else "other"
            
            # Find next available bit_index
            max_bit = db.query(db.func.max(Capability.bit_index)).scalar() or -1
            new_bit_index = max_bit + 1
            
            if new_bit_index >= 512:
                warnings.append(f"Capability '{cap_name}' exceeds bitmask capacity, created without bit_index")
                new_bit_index = None
            
            cap = Capability(
                name=cap_name,
                display_name=cap_name.replace("_", " ").title(),
                domain=domain,
                bit_index=new_bit_index,
            )
            db.add(cap)
            db.flush()
        
        # Create MaterialCapability link
        mat_cap = MaterialCapability(
            material_id=material.id,
            capability_id=cap.id,
            is_required=True,  # Default to required
        )
        db.add(mat_cap)
        
        if cap.bit_index is not None:
            capability_ids_for_bitmask.append(cap.bit_index)
    
    # Compute and store bitmasks on the material
    masks = compute_capability_bitmask(capability_ids_for_bitmask)
    material.req_cap_mask_0 = masks[0]
    material.req_cap_mask_1 = masks[1]
    material.req_cap_mask_2 = masks[2]
    material.req_cap_mask_3 = masks[3]
    material.req_cap_mask_4 = masks[4]
    material.req_cap_mask_5 = masks[5]
    material.req_cap_mask_6 = masks[6]
    material.req_cap_mask_7 = masks[7]
    
    # Create MaterialAnalysis record
    range_data = extraction_result.range_analysis
    analysis = MaterialAnalysis(
        material_id=material.id,
        lowest_pitch=range_data.lowest_pitch if range_data else None,
        highest_pitch=range_data.highest_pitch if range_data else None,
        range_semitones=range_data.range_semitones if range_data else None,
        pitch_density_low=range_data.density_low if range_data else None,
        pitch_density_mid=range_data.density_mid if range_data else None,
        pitch_density_high=range_data.density_high if range_data else None,
        trill_lowest=range_data.trill_lowest if range_data else None,
        trill_highest=range_data.trill_highest if range_data else None,
        chromatic_complexity=extraction_result.chromatic_complexity_score,
        tempo_marking=list(extraction_result.tempo_markings)[0] if extraction_result.tempo_markings else None,
        tempo_bpm=extraction_result.tempo_bpm,
        measure_count=extraction_result.measure_count,
        raw_extraction_json=json.dumps(extraction_result.to_dict()),
    )
    db.add(analysis)
    
    db.commit()
    
    return MaterialAnalysisResponse(
        material_id=material.id,
        title=material.title,
        extracted_capabilities=capability_names,
        range_analysis=range_data.__dict__ if range_data else None,
        chromatic_complexity=extraction_result.chromatic_complexity_score,
        measure_count=extraction_result.measure_count,
        warnings=warnings,
    )


@app.get("/materials/{material_id}/analysis")
def get_material_analysis(material_id: int, db: Session = Depends(get_db)):
    """Get the analysis data for a material."""
    from app.models.capability_schema import MaterialAnalysis, MaterialCapability, Capability
    
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    analysis = db.query(MaterialAnalysis).filter_by(material_id=material_id).first()
    
    # Get linked capabilities
    mat_caps = db.query(MaterialCapability).filter_by(material_id=material_id).all()
    cap_ids = [mc.capability_id for mc in mat_caps]
    caps = db.query(Capability).filter(Capability.id.in_(cap_ids)).all() if cap_ids else []
    
    return {
        "material_id": material_id,
        "title": material.title,
        "capabilities": [
            {
                "id": c.id,
                "name": c.name,
                "display_name": c.display_name,
                "domain": c.domain,
            }
            for c in caps
        ],
        "analysis": {
            "lowest_pitch": analysis.lowest_pitch if analysis else None,
            "highest_pitch": analysis.highest_pitch if analysis else None,
            "range_semitones": analysis.range_semitones if analysis else None,
            "pitch_density": {
                "low": analysis.pitch_density_low,
                "mid": analysis.pitch_density_mid,
                "high": analysis.pitch_density_high,
            } if analysis else None,
            "chromatic_complexity": analysis.chromatic_complexity if analysis else None,
            "tempo_marking": analysis.tempo_marking if analysis else None,
            "tempo_bpm": analysis.tempo_bpm if analysis else None,
            "measure_count": analysis.measure_count if analysis else None,
        } if analysis else None,
    }


@app.post("/materials/analyze")
def analyze_material_preview(data: MaterialUpload = Body(...)):
    """
    Preview material analysis without saving to database.
    
    Useful for testing MusicXML before committing.
    """
    from app.musicxml_analyzer import MusicXMLAnalyzer
    
    try:
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(data.musicxml_content)
        capabilities = analyzer.get_capability_names(result)
        
        return {
            "title": result.title,
            "capabilities": capabilities,
            "capability_count": len(capabilities),
            "range_analysis": result.range_analysis.__dict__ if result.range_analysis else None,
            "chromatic_complexity": result.chromatic_complexity_score,
            "measure_count": result.measure_count,
            "detailed_extraction": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Analysis failed: {str(e)}")


@app.get("/capabilities/v2")
def list_capabilities(
    domain: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """List all capabilities in the v2 system, optionally filtered by domain."""
    from app.models.capability_schema import Capability
    
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


@app.get("/capabilities/v2/domains")
def list_capability_domains(db: Session = Depends(get_db)):
    """List all capability domains with counts."""
    from app.models.capability_schema import Capability
    from sqlalchemy import func
    
    result = db.query(
        Capability.domain,
        func.count(Capability.id).label('count')
    ).group_by(Capability.domain).all()
    
    return [{"domain": r[0], "count": r[1]} for r in result]


@app.get("/users/{user_id}/eligible-materials")
def get_eligible_materials(user_id: int, db: Session = Depends(get_db)):
    """
    Get materials the user is eligible for based on their capabilities.
    
    Uses bitmask for fast O(1) per-material eligibility check.
    """
    from app.models.capability_schema import MaterialAnalysis
    
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


@app.post("/users/{user_id}/capabilities/grant")
def grant_capability(
    user_id: int,
    capability_id: int = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Grant a capability to a user (mark as mastered).
    
    Updates both the normalized table and the user's bitmask.
    """
    from app.models.capability_schema import Capability, UserCapability
    
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


@app.post("/users/{user_id}/capabilities/revoke")
def revoke_capability(
    user_id: int,
    capability_id: int = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    Revoke a capability from a user (mark as no longer able).
    
    Updates both the normalized table and the user's bitmask.
    """
    from app.models.capability_schema import Capability, UserCapability
    
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


# =============================================================================
# ADMIN API ENDPOINTS
# =============================================================================

@app.get("/admin/capabilities")
def admin_get_capabilities(
    domain: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all capabilities with extended admin info.
    """
    from app.models.capability_schema import Capability, MaterialCapability, MaterialTeachesCapability
    
    query = db.query(Capability)
    if domain:
        query = query.filter(Capability.domain == domain)
    
    capabilities = query.order_by(Capability.domain, Capability.bit_index, Capability.name).all()
    
    result = []
    for cap in capabilities:
        # Count materials that require this capability
        requires_count = db.query(MaterialCapability).filter_by(capability_id=cap.id).count()
        
        # Count materials that teach this capability
        teaches_count = db.query(MaterialTeachesCapability).filter_by(capability_id=cap.id).count()
        
        # Parse prerequisites
        prereq_names = []
        prereq_ids_list = []
        if cap.prerequisite_ids:
            try:
                prereq_ids_list = json.loads(cap.prerequisite_ids) if isinstance(cap.prerequisite_ids, str) else cap.prerequisite_ids
                if prereq_ids_list:
                    prereqs = db.query(Capability).filter(Capability.id.in_(prereq_ids_list)).all()
                    prereq_names = [p.name for p in prereqs]
            except:
                prereq_ids_list = []
        
        # Parse soft_gate_requirements
        soft_gate_reqs = None
        if cap.soft_gate_requirements:
            try:
                soft_gate_reqs = json.loads(cap.soft_gate_requirements) if isinstance(cap.soft_gate_requirements, str) else cap.soft_gate_requirements
            except:
                pass
        
        result.append({
            "id": cap.id,
            "name": cap.name,
            "display_name": cap.display_name,
            "domain": cap.domain,
            "subdomain": cap.subdomain,
            "bit_index": cap.bit_index,
            "requirement_type": cap.requirement_type,
            "difficulty_tier": cap.difficulty_tier,
            "difficulty_weight": cap.difficulty_weight,
            "mastery_type": cap.mastery_type,
            "mastery_count": cap.mastery_count,
            "evidence_required_count": cap.evidence_required_count,
            "evidence_distinct_materials": cap.evidence_distinct_materials,
            "evidence_acceptance_threshold": cap.evidence_acceptance_threshold,
            "soft_gate_requirements": soft_gate_reqs,
            "is_active": cap.is_active if cap.is_active is not None else True,
            "prerequisite_ids": prereq_ids_list,
            "prerequisite_names": prereq_names,
            "materials_requiring": requires_count,
            "materials_teaching": teaches_count,
        })
    
    return {"capabilities": result, "count": len(result)}


@app.get("/admin/capabilities/{capability_id}/graph")
def admin_get_capability_graph(
    capability_id: int,
    db: Session = Depends(get_db)
):
    """
    Get dependency graph for a capability (what it depends on, what depends on it).
    """
    from app.models.capability_schema import Capability
    
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    # Get capabilities this one depends on
    depends_on = []
    if cap.prerequisite_ids:
        try:
            prereq_ids = json.loads(cap.prerequisite_ids) if isinstance(cap.prerequisite_ids, str) else cap.prerequisite_ids
            if prereq_ids:
                prereqs = db.query(Capability).filter(Capability.id.in_(prereq_ids)).all()
                depends_on = [p.name for p in prereqs]
        except:
            pass
    
    # Get capabilities that depend on this one
    all_caps = db.query(Capability).all()
    required_by = []
    for other_cap in all_caps:
        if other_cap.prerequisite_ids:
            try:
                prereq_ids = json.loads(other_cap.prerequisite_ids) if isinstance(other_cap.prerequisite_ids, str) else other_cap.prerequisite_ids
                if prereq_ids and capability_id in prereq_ids:
                    required_by.append(other_cap.name)
            except:
                pass
    
    return {
        "capability": cap.name,
        "depends_on": depends_on,
        "required_by": required_by,
    }


@app.post("/admin/capabilities/export")
def admin_export_capabilities(
    db: Session = Depends(get_db)
):
    """
    Export all capabilities to capabilities.json in the resources folder.
    Archives the existing capabilities.json to resources/capability_history/ first.
    """
    from app.models.capability_schema import Capability
    from datetime import datetime
    import os
    import shutil
    
    capabilities = db.query(Capability).order_by(Capability.domain, Capability.bit_index, Capability.name).all()
    
    # Build capability ID to name mapping for prerequisites
    cap_id_to_name = {cap.id: cap.name for cap in capabilities}
    
    # Format capabilities in the same structure as capabilities.json
    exported = []
    for cap in capabilities:
        # Parse prerequisite IDs and convert to names
        prereq_names = []
        if cap.prerequisite_ids:
            try:
                prereq_ids = json.loads(cap.prerequisite_ids) if isinstance(cap.prerequisite_ids, str) else cap.prerequisite_ids
                if prereq_ids:
                    prereq_names = [cap_id_to_name[pid] for pid in prereq_ids if pid in cap_id_to_name]
            except:
                pass
        
        # Parse evidence_qualifier_json
        evidence_qualifier = {}
        if cap.evidence_qualifier_json:
            try:
                evidence_qualifier = json.loads(cap.evidence_qualifier_json) if isinstance(cap.evidence_qualifier_json, str) else cap.evidence_qualifier_json
            except:
                pass
        
        # Parse soft_gate_requirements
        soft_gate_reqs = None
        if cap.soft_gate_requirements:
            try:
                soft_gate_reqs = json.loads(cap.soft_gate_requirements) if isinstance(cap.soft_gate_requirements, str) else cap.soft_gate_requirements
            except:
                pass
        
        exported.append({
            "name": cap.name,
            "display_name": cap.display_name,
            "domain": cap.domain,
            "subdomain": cap.subdomain,
            "requirement_type": cap.requirement_type or "required",
            "prerequisite_names": prereq_names,
            "difficulty_tier": cap.difficulty_tier or 1,
            "mastery_type": cap.mastery_type or "single",
            "mastery_count": cap.mastery_count or 1,
            "evidence_required_count": cap.evidence_required_count or 1,
            "evidence_distinct_materials": cap.evidence_distinct_materials or False,
            "evidence_acceptance_threshold": cap.evidence_acceptance_threshold or 4,
            "evidence_qualifier_json": evidence_qualifier,
            "difficulty_weight": cap.difficulty_weight or 1.0,
            "soft_gate_requirements": soft_gate_reqs,
            "bit_index": cap.bit_index
        })
    
    # Create output structure
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output = {
        "version": f"capabilities_{timestamp}",
        "count": len(exported),
        "capabilities": exported
    }
    
    # Paths
    resources_dir = os.path.join(os.path.dirname(__file__), "..", "resources")
    history_dir = os.path.join(resources_dir, "capability_history")
    current_file = os.path.join(resources_dir, "capabilities.json")
    
    try:
        # Create history directory if it doesn't exist
        os.makedirs(history_dir, exist_ok=True)
        
        # Archive existing capabilities.json if it exists
        archived_file = None
        if os.path.exists(current_file):
            archive_filename = f"capabilities_{timestamp}.json"
            archive_path = os.path.join(history_dir, archive_filename)
            shutil.copy2(current_file, archive_path)
            archived_file = archive_filename
        
        # Write new capabilities.json
        with open(current_file, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=1, ensure_ascii=False)
        
        message = f"Exported {len(exported)} capabilities"
        if archived_file:
            message += f" (archived previous to capability_history/{archived_file})"
        
        return {
            "success": True,
            "message": message,
            "filename": "capabilities.json",
            "archived": archived_file
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to export capabilities",
                "error": str(e)
            }
        )


@app.post("/admin/capabilities/{capability_id}/archive")
def admin_archive_capability(
    capability_id: int,
    db: Session = Depends(get_db)
):
    """
    Archive a capability by setting is_active=False.
    Archived capabilities won't appear in normal capability lists.
    """
    from app.models.capability_schema import Capability
    
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if not cap.is_active:
        return {
            "success": True,
            "message": f"Capability '{cap.name}' is already archived",
            "capability_id": capability_id,
            "is_active": False
        }
    
    cap.is_active = False
    db.commit()
    
    return {
        "success": True,
        "message": f"Archived capability '{cap.name}'",
        "capability_id": capability_id,
        "is_active": False
    }


@app.post("/admin/capabilities/{capability_id}/restore")
def admin_restore_capability(
    capability_id: int,
    db: Session = Depends(get_db)
):
    """
    Restore an archived capability by setting is_active=True.
    """
    from app.models.capability_schema import Capability
    
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    if cap.is_active:
        return {
            "success": True,
            "message": f"Capability '{cap.name}' is already active",
            "capability_id": capability_id,
            "is_active": True
        }
    
    cap.is_active = True
    db.commit()
    
    return {
        "success": True,
        "message": f"Restored capability '{cap.name}'",
        "capability_id": capability_id,
        "is_active": True
    }


@app.delete("/admin/capabilities/{capability_id}")
def admin_delete_capability(
    capability_id: int,
    db: Session = Depends(get_db)
):
    """
    Permanently delete a capability. Shifts bit_indexes of capabilities after it down by 1.
    If the domain becomes empty, it effectively gets removed (no capabilities reference it).
    Also removes this capability from any other capability's prerequisite_ids list.
    """
    from app.models.capability_schema import Capability
    
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    cap_name = cap.name
    cap_domain = cap.domain
    deleted_bit_index = cap.bit_index
    
    # Remove this capability from all prerequisite lists
    all_caps = db.query(Capability).all()
    prereqs_cleaned = 0
    for c in all_caps:
        if c.prerequisite_ids:
            try:
                prereq_list = json.loads(c.prerequisite_ids) if isinstance(c.prerequisite_ids, str) else c.prerequisite_ids
                if capability_id in prereq_list:
                    prereq_list = [pid for pid in prereq_list if pid != capability_id]
                    c.prerequisite_ids = json.dumps(prereq_list) if prereq_list else None
                    prereqs_cleaned += 1
            except:
                pass
    
    # Get all capabilities that come after this one (higher bit_index)
    caps_after = [c for c in all_caps if c.bit_index is not None and c.bit_index > deleted_bit_index]
    
    # Delete the capability
    db.delete(cap)
    
    # Shift all capabilities after it down by 1
    # Two-pass to avoid UNIQUE constraint violations
    if caps_after:
        # First pass: set to negative temporary values
        for c in caps_after:
            c.bit_index = -(c.bit_index)
        db.flush()
        # Second pass: set to final values (original - 1)
        for c in caps_after:
            c.bit_index = -(c.bit_index) - 1
    
    db.commit()
    
    # Check if domain is now empty
    remaining_in_domain = db.query(Capability).filter_by(domain=cap_domain).count()
    domain_removed = remaining_in_domain == 0
    
    return {
        "success": True,
        "message": f"Deleted capability '{cap_name}'",
        "capability_id": capability_id,
        "shifted_count": len(caps_after),
        "prereqs_cleaned": prereqs_cleaned,
        "domain_removed": domain_removed,
        "domain": cap_domain
    }


# Pydantic model for creating a new capability
class CapabilityCreateRequest(BaseModel):
    """Request model for creating a new capability."""
    name: str
    display_name: Optional[str] = None
    domain: str
    subdomain: Optional[str] = None
    requirement_type: str = "required"
    difficulty_tier: int = 1
    mastery_type: str = "single"
    mastery_count: int = 1
    evidence_required_count: int = 1
    evidence_distinct_materials: bool = False
    evidence_acceptance_threshold: int = 4
    difficulty_weight: float = 1.0
    prerequisite_ids: Optional[List[int]] = None
    soft_gate_requirements: Optional[Dict[str, float]] = None  # e.g., {"interval_velocity_score": 0.5}


@app.post("/admin/capabilities")
def admin_create_capability(
    create_data: CapabilityCreateRequest,
    db: Session = Depends(get_db)
):
    """
    Create a new capability. Inserts at the correct position based on alphabetical domain order.
    Capabilities in alphabetically-later domains get their bit_indexes shifted up.
    """
    from app.models.capability_schema import Capability
    from sqlalchemy import func
    
    # Check name uniqueness
    existing = db.query(Capability).filter_by(name=create_data.name).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Capability with name '{create_data.name}' already exists")
    
    # Get all capabilities ordered by bit_index
    all_caps = db.query(Capability).order_by(Capability.bit_index).all()
    
    # Get domains sorted alphabetically
    existing_domains = sorted(set(c.domain for c in all_caps))
    target_domain = create_data.domain
    
    # Find where target domain fits alphabetically and determine insert position
    if target_domain in existing_domains:
        # Existing domain - insert at end of that domain's capabilities
        domain_caps = [c for c in all_caps if c.domain == target_domain]
        if domain_caps:
            # Insert after the last capability in this domain
            max_bit_in_domain = max(c.bit_index for c in domain_caps)
            insert_bit_index = max_bit_in_domain + 1
        else:
            insert_bit_index = 0
    else:
        # New domain - find alphabetical position and insert at that point
        # Find the first domain that comes after this one alphabetically
        insert_bit_index = None
        for existing_domain in existing_domains:
            if existing_domain > target_domain:
                # Insert before this domain
                domain_caps = [c for c in all_caps if c.domain == existing_domain]
                if domain_caps:
                    insert_bit_index = min(c.bit_index for c in domain_caps)
                break
        
        # If no domain comes after, insert at the end
        if insert_bit_index is None:
            max_bit = db.query(func.max(Capability.bit_index)).scalar() or -1
            insert_bit_index = max_bit + 1
    
    # Shift all capabilities at or after insert_bit_index up by 1
    # Use two-pass to avoid UNIQUE constraint violations
    caps_to_shift = [c for c in all_caps if c.bit_index >= insert_bit_index]
    # Store original indexes
    original_indexes = {c.id: c.bit_index for c in caps_to_shift}
    # First pass: set to negative temporary values
    for cap in caps_to_shift:
        cap.bit_index = -(cap.bit_index + 1)
    db.flush()
    # Second pass: set to final positive values (original + 1)
    for cap in caps_to_shift:
        cap.bit_index = original_indexes[cap.id] + 1
    
    # Create the capability with the correct bit_index
    cap = Capability(
        name=create_data.name,
        display_name=create_data.display_name,
        domain=create_data.domain,
        subdomain=create_data.subdomain,
        requirement_type=create_data.requirement_type,
        bit_index=insert_bit_index,
        difficulty_tier=create_data.difficulty_tier,
        mastery_type=create_data.mastery_type,
        mastery_count=create_data.mastery_count,
        evidence_required_count=create_data.evidence_required_count,
        evidence_distinct_materials=create_data.evidence_distinct_materials,
        evidence_acceptance_threshold=create_data.evidence_acceptance_threshold,
        difficulty_weight=create_data.difficulty_weight,
        prerequisite_ids=json.dumps(create_data.prerequisite_ids) if create_data.prerequisite_ids else None,
        soft_gate_requirements=json.dumps(create_data.soft_gate_requirements) if create_data.soft_gate_requirements else None,
        is_active=True
    )
    
    db.add(cap)
    db.commit()
    db.refresh(cap)
    
    return {
        "success": True,
        "message": f"Created capability '{cap.name}' at bit_index {cap.bit_index}",
        "capability": {
            "id": cap.id,
            "name": cap.name,
            "display_name": cap.display_name,
            "domain": cap.domain,
            "bit_index": cap.bit_index
        },
        "shifted_count": len(caps_to_shift)
    }


class ReorderCapabilitiesRequest(BaseModel):
    """Request model for reordering capabilities within a domain."""
    domain: str
    capability_ids: List[int]  # Ordered list of capability IDs


@app.post("/admin/capabilities/reorder")
def admin_reorder_capabilities(
    reorder_data: ReorderCapabilitiesRequest,
    db: Session = Depends(get_db)
):
    """
    Reorder capabilities within a domain by reassigning bit_indexes.
    The capability_ids list should contain all capabilities in the domain in the desired order.
    """
    from app.models.capability_schema import Capability
    
    domain = reorder_data.domain
    capability_ids = reorder_data.capability_ids
    
    # Get all capabilities in this domain
    domain_caps = db.query(Capability).filter_by(domain=domain).all()
    domain_cap_ids = {c.id for c in domain_caps}
    
    # Validate all IDs belong to this domain
    provided_ids = set(capability_ids)
    if provided_ids != domain_cap_ids:
        missing = domain_cap_ids - provided_ids
        extra = provided_ids - domain_cap_ids
        errors = []
        if missing:
            errors.append(f"Missing capability IDs from domain: {list(missing)}")
        if extra:
            errors.append(f"Capability IDs not in domain '{domain}': {list(extra)}")
        raise HTTPException(status_code=400, detail="; ".join(errors))
    
    # Get the min bit_index in this domain to use as base
    min_bit = min(c.bit_index for c in domain_caps if c.bit_index is not None)
    
    # Two-pass to avoid UNIQUE constraint violations
    cap_by_id = {c.id: c for c in domain_caps}
    # First pass: set to negative temporary values
    for i, cap_id in enumerate(capability_ids):
        cap = cap_by_id[cap_id]
        cap.bit_index = -(i + 1)
    db.flush()
    # Second pass: set to final positive values
    for i, cap_id in enumerate(capability_ids):
        cap = cap_by_id[cap_id]
        cap.bit_index = min_bit + i
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Reordered {len(capability_ids)} capabilities in domain '{domain}'",
        "domain": domain,
        "new_order": [
            {"id": cap_id, "bit_index": min_bit + i}
            for i, cap_id in enumerate(capability_ids)
        ]
    }


class RenameDomainRequest(BaseModel):
    """Request model for renaming a domain."""
    old_name: str
    new_name: str


@app.post("/admin/domains/rename")
def admin_rename_domain(
    rename_data: RenameDomainRequest,
    db: Session = Depends(get_db)
):
    """
    Rename a domain. Updates all capabilities in that domain.
    After renaming, re-sorts all capabilities by alphabetical domain order.
    """
    from app.models.capability_schema import Capability
    
    old_name = rename_data.old_name.strip()
    new_name = rename_data.new_name.strip()
    
    if not new_name:
        raise HTTPException(status_code=400, detail="New domain name cannot be empty")
    
    # Check if old domain exists
    caps_in_domain = db.query(Capability).filter_by(domain=old_name).all()
    if not caps_in_domain:
        raise HTTPException(status_code=404, detail=f"Domain '{old_name}' not found")
    
    # Check if new name already exists (unless same name with different case)
    if old_name.lower() != new_name.lower():
        existing = db.query(Capability).filter_by(domain=new_name).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Domain '{new_name}' already exists")
    
    # Update all capabilities in this domain
    for cap in caps_in_domain:
        cap.domain = new_name
    
    # Re-sort all capabilities by alphabetical domain order
    all_caps = db.query(Capability).all()
    
    # Group by domain, sorted alphabetically
    caps_by_domain = {}
    for cap in all_caps:
        if cap.domain not in caps_by_domain:
            caps_by_domain[cap.domain] = []
        caps_by_domain[cap.domain].append(cap)
    
    # Sort capabilities within each domain by their current bit_index
    for domain in caps_by_domain:
        caps_by_domain[domain].sort(key=lambda c: c.bit_index)
    
    # Build the new order list
    new_order = []
    for domain in sorted(caps_by_domain.keys()):
        new_order.extend(caps_by_domain[domain])
    
    # Two-pass approach to avoid UNIQUE constraint violations:
    # First, set all bit_indexes to negative temporary values
    for i, cap in enumerate(new_order):
        cap.bit_index = -(i + 1)
    db.flush()
    
    # Then set them to final positive values
    for i, cap in enumerate(new_order):
        cap.bit_index = i
    
    db.commit()
    
    return {
        "success": True,
        "message": f"Renamed domain '{old_name}' to '{new_name}' ({len(caps_in_domain)} capabilities updated)",
        "old_name": old_name,
        "new_name": new_name,
        "capabilities_updated": len(caps_in_domain)
    }


# Pydantic model for capability update request
class CapabilityUpdateRequest(BaseModel):
    """
    Request model for updating a capability.
    
    Note: id and bit_index are NOT editable via this endpoint.
    - id: Primary key, never changes
    - bit_index: Used for bitmask operations, changing could corrupt user progress
    """
    name: str
    display_name: Optional[str] = None
    domain: str
    subdomain: Optional[str] = None
    requirement_type: str = "required"
    difficulty_tier: int = 1
    mastery_type: str = "single"
    mastery_count: int = 1
    evidence_required_count: int = 1
    evidence_distinct_materials: bool = False
    evidence_acceptance_threshold: int = 4
    difficulty_weight: float = 1.0
    prerequisite_ids: Optional[List[int]] = None  # List of capability IDs, or None to skip update
    soft_gate_requirements: Optional[Dict[str, float]] = None  # e.g., {"interval_velocity_score": 0.5}


# Validation constants for capabilities
VALID_REQUIREMENT_TYPES = ["required", "learnable_in_context"]
VALID_MASTERY_TYPES = ["single", "any_of_pool", "multiple"]
MIN_RATING = 1
MAX_RATING = 5
MIN_DIFFICULTY_WEIGHT = 0.1
MAX_DIFFICULTY_WEIGHT = 10.0


def check_circular_dependency(capability_id: int, new_prereq_ids: List[int], db) -> Optional[List[str]]:
    """
    Check if setting new_prereq_ids on capability_id would create a circular dependency.
    
    Returns None if no cycle, or a list of capability names forming the cycle path.
    
    A cycle exists if any of the new prerequisites (or their transitive prerequisites)
    eventually include capability_id itself.
    """
    from app.models.capability_schema import Capability
    import json
    
    if not new_prereq_ids:
        return None
    
    # Build a map of capability_id -> prerequisite_ids for traversal
    all_caps = db.query(Capability).all()
    cap_map = {c.id: c for c in all_caps}
    prereq_map = {}
    for c in all_caps:
        try:
            prereq_map[c.id] = json.loads(c.prerequisite_ids) if c.prerequisite_ids else []
        except:
            prereq_map[c.id] = []
    
    # Replace the prereqs for the capability being edited (simulate the change)
    prereq_map[capability_id] = new_prereq_ids
    
    # BFS/DFS from capability_id to see if we can reach capability_id again
    visited = set()
    path = []
    
    def dfs(current_id, path_so_far):
        """Returns cycle path if found, None otherwise."""
        if current_id in visited:
            return None
        
        if current_id == capability_id and len(path_so_far) > 0:
            # Found a cycle back to the original
            return path_so_far + [cap_map[current_id].name if current_id in cap_map else f"id:{current_id}"]
        
        visited.add(current_id)
        path_so_far = path_so_far + [cap_map[current_id].name if current_id in cap_map else f"id:{current_id}"]
        
        for prereq_id in prereq_map.get(current_id, []):
            if prereq_id == capability_id:
                # Direct cycle found
                prereq_name = cap_map[prereq_id].name if prereq_id in cap_map else f"id:{prereq_id}"
                return path_so_far + [prereq_name]
            result = dfs(prereq_id, path_so_far)
            if result:
                return result
        
        return None
    
    # Start from each new prerequisite and see if we eventually reach capability_id
    for prereq_id in new_prereq_ids:
        if prereq_id == capability_id:
            return [cap_map[capability_id].name, cap_map[capability_id].name]  # Self-reference
        
        visited.clear()
        prereq_name = cap_map[prereq_id].name if prereq_id in cap_map else f"id:{prereq_id}"
        result = dfs(prereq_id, [cap_map[capability_id].name])
        if result:
            return result
    
    return None


@app.put("/admin/capabilities/{capability_id}")
def admin_update_capability(
    capability_id: int,
    update_data: CapabilityUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Update an existing capability with validated data.
    
    Only updates allowed editable fields. Does NOT modify:
    - id (primary key)
    - bit_index (used for bitmask eligibility checks)
    
    Prerequisite editing includes circular dependency validation to prevent
    cycles like A→B→C→A.
    
    Authorization:
    - This endpoint is intended for internal admin use only.
    - In production, add authentication middleware to restrict access.
    - Currently no auth check (development mode).
    
    Returns structured success/error response.
    """
    from app.models.capability_schema import Capability
    import json
    
    # Find the capability
    cap = db.query(Capability).filter_by(id=capability_id).first()
    if not cap:
        raise HTTPException(status_code=404, detail="Capability not found")
    
    # Server-side validation
    errors = []
    
    # Validate name
    name = update_data.name.strip() if update_data.name else ""
    if not name:
        errors.append("name: Name is required")
    elif not all(c.islower() or c.isdigit() or c == '_' for c in name):
        errors.append("name: Must be lowercase alphanumeric with underscores only")
    else:
        # Check for duplicate name (excluding current capability)
        existing = db.query(Capability).filter(
            Capability.name == name,
            Capability.id != capability_id
        ).first()
        if existing:
            errors.append(f"name: A capability with name '{name}' already exists (id={existing.id})")
    
    # Validate domain
    domain = update_data.domain.strip() if update_data.domain else ""
    if not domain:
        errors.append("domain: Domain is required")
    
    # Validate requirement_type
    if update_data.requirement_type not in VALID_REQUIREMENT_TYPES:
        errors.append(f"requirement_type: Must be one of {VALID_REQUIREMENT_TYPES}")
    
    # Validate mastery_type
    if update_data.mastery_type not in VALID_MASTERY_TYPES:
        errors.append(f"mastery_type: Must be one of {VALID_MASTERY_TYPES}")
    
    # Validate numeric fields
    if update_data.difficulty_tier < 1 or update_data.difficulty_tier > 5:
        errors.append("difficulty_tier: Must be between 1 and 5")
    
    if update_data.difficulty_weight < MIN_DIFFICULTY_WEIGHT or update_data.difficulty_weight > MAX_DIFFICULTY_WEIGHT:
        errors.append(f"difficulty_weight: Must be between {MIN_DIFFICULTY_WEIGHT} and {MAX_DIFFICULTY_WEIGHT}")
    
    if update_data.mastery_count < 1:
        errors.append("mastery_count: Must be at least 1")
    
    if update_data.evidence_required_count < 1:
        errors.append("evidence_required_count: Must be at least 1")
    
    if update_data.evidence_acceptance_threshold < MIN_RATING or update_data.evidence_acceptance_threshold > MAX_RATING:
        errors.append(f"evidence_acceptance_threshold: Must be between {MIN_RATING} and {MAX_RATING}")
    
    # Validate prerequisite_ids if provided
    if update_data.prerequisite_ids is not None:
        prereq_ids = update_data.prerequisite_ids
        
        # Check for self-reference
        if capability_id in prereq_ids:
            errors.append("prerequisite_ids: Cannot set self as a prerequisite")
        
        # Validate all IDs exist
        if prereq_ids:
            existing_ids = [c.id for c in db.query(Capability.id).filter(Capability.id.in_(prereq_ids)).all()]
            missing_ids = set(prereq_ids) - set(existing_ids)
            if missing_ids:
                errors.append(f"prerequisite_ids: The following capability IDs do not exist: {list(missing_ids)}")
        
        # Check for circular dependencies
        if not errors:  # Only check if no other prereq errors
            cycle_path = check_circular_dependency(capability_id, prereq_ids, db)
            if cycle_path:
                cycle_str = " → ".join(cycle_path)
                errors.append(f"prerequisite_ids: Would create circular dependency: {cycle_str}")
    
    # If there are validation errors, return them all
    if errors:
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Validation failed",
                "errors": errors
            }
        )
    
    # Apply updates (only to allowed editable fields)
    try:
        cap.name = name
        cap.display_name = update_data.display_name.strip() if update_data.display_name else None
        cap.domain = domain
        cap.subdomain = update_data.subdomain.strip() if update_data.subdomain else None
        cap.requirement_type = update_data.requirement_type
        cap.difficulty_tier = update_data.difficulty_tier
        cap.mastery_type = update_data.mastery_type
        cap.mastery_count = update_data.mastery_count
        cap.evidence_required_count = update_data.evidence_required_count
        cap.evidence_distinct_materials = update_data.evidence_distinct_materials
        cap.evidence_acceptance_threshold = update_data.evidence_acceptance_threshold
        cap.difficulty_weight = update_data.difficulty_weight
        
        # Update prerequisites if provided (already validated above)
        if update_data.prerequisite_ids is not None:
            cap.prerequisite_ids = json.dumps(update_data.prerequisite_ids) if update_data.prerequisite_ids else None
        
        # Update soft_gate_requirements if provided
        if update_data.soft_gate_requirements is not None:
            cap.soft_gate_requirements = json.dumps(update_data.soft_gate_requirements) if update_data.soft_gate_requirements else None
        
        db.commit()
        db.refresh(cap)
        
        # Get prerequisite names for response
        prereq_ids_list = json.loads(cap.prerequisite_ids) if cap.prerequisite_ids else []
        prereq_names = []
        if prereq_ids_list:
            prereqs = db.query(Capability).filter(Capability.id.in_(prereq_ids_list)).all()
            prereq_map = {p.id: p for p in prereqs}
            prereq_names = [
                {"id": pid, "name": prereq_map[pid].name, "domain": prereq_map[pid].domain}
                for pid in prereq_ids_list if pid in prereq_map
            ]
        
        # Parse soft_gate_requirements for response
        soft_gate_reqs = None
        if cap.soft_gate_requirements:
            try:
                soft_gate_reqs = json.loads(cap.soft_gate_requirements) if isinstance(cap.soft_gate_requirements, str) else cap.soft_gate_requirements
            except:
                pass
        
        return {
            "success": True,
            "message": "Capability updated successfully",
            "capability": {
                "id": cap.id,
                "name": cap.name,
                "display_name": cap.display_name,
                "domain": cap.domain,
                "subdomain": cap.subdomain,
                "bit_index": cap.bit_index,  # Read-only, returned for reference
                "requirement_type": cap.requirement_type,
                "difficulty_tier": cap.difficulty_tier,
                "difficulty_weight": cap.difficulty_weight,
                "mastery_type": cap.mastery_type,
                "mastery_count": cap.mastery_count,
                "evidence_required_count": cap.evidence_required_count,
                "evidence_distinct_materials": cap.evidence_distinct_materials,
                "evidence_acceptance_threshold": cap.evidence_acceptance_threshold,
                "soft_gate_requirements": soft_gate_reqs,
                "prerequisite_names": prereq_names,
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail={
                "message": "Failed to save capability",
                "error": str(e)
            }
        )


@app.get("/admin/materials")
def admin_get_materials(
    db: Session = Depends(get_db)
):
    """
    Get all materials with analysis data.
    """
    from app.models.capability_schema import MaterialAnalysis, MaterialCapability, MaterialTeachesCapability, Capability
    
    materials = db.query(Material).all()
    
    result = []
    for mat in materials:
        # Get analysis data if available
        analysis = db.query(MaterialAnalysis).filter_by(material_id=mat.id).first()
        
        # Get required capabilities
        req_caps = db.query(MaterialCapability, Capability).join(
            Capability, MaterialCapability.capability_id == Capability.id
        ).filter(MaterialCapability.material_id == mat.id).all()
        required_capabilities = [c.name for _, c in req_caps]
        
        # Get taught capabilities
        teach_caps = db.query(MaterialTeachesCapability, Capability).join(
            Capability, MaterialTeachesCapability.capability_id == Capability.id
        ).filter(MaterialTeachesCapability.material_id == mat.id).all()
        teaches_capabilities = [c.name for _, c in teach_caps]
        
        mat_data = {
            "id": mat.id,
            "title": mat.title,
            "original_key_center": mat.original_key_center,
            "allowed_keys": mat.allowed_keys,
            "required_capabilities": required_capabilities,
            "teaches_capabilities": teaches_capabilities,
        }
        
        if analysis:
            mat_data.update({
                "lowest_pitch": analysis.lowest_pitch,
                "highest_pitch": analysis.highest_pitch,
                "range_semitones": analysis.range_semitones,
                "chromatic_complexity": analysis.chromatic_complexity,
                "rhythmic_complexity": analysis.rhythmic_complexity,
                "reading_complexity": analysis.reading_complexity,
                "measure_count": analysis.measure_count,
                "estimated_duration_seconds": analysis.estimated_duration_seconds,
                "tonal_complexity_stage": analysis.tonal_complexity_stage,
                "interval_size_stage": analysis.interval_size_stage,
                "rhythm_complexity_stage": analysis.rhythm_complexity_stage,
                "range_usage_stage": analysis.range_usage_stage,
                "difficulty_index": analysis.difficulty_index,
            })
        
        result.append(mat_data)
    
    return {"materials": result, "count": len(result)}


@app.get("/admin/materials/{material_id}/gate-check")
def admin_check_material_gates(
    material_id: int,
    user_id: int = Query(...),
    db: Session = Depends(get_db)
):
    """
    Check if a material passes hard gates and soft envelope for a user.
    """
    from app.models.capability_schema import (
        MaterialCapability, MaterialAnalysis, Capability,
        UserCapability, UserSoftGateState, SoftGateRule
    )
    
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check hard gates (capability requirements)
    hard_gate_failures = []
    
    # Get required capabilities for this material
    req_caps = db.query(MaterialCapability, Capability).join(
        Capability, MaterialCapability.capability_id == Capability.id
    ).filter(
        MaterialCapability.material_id == material_id,
        MaterialCapability.is_required == True
    ).all()
    
    for mat_cap, cap in req_caps:
        # Check if user has this capability
        user_cap = db.query(UserCapability).filter_by(
            user_id=user_id, capability_id=cap.id, is_active=True
        ).first()
        
        if not user_cap or not user_cap.mastered_at:
            hard_gate_failures.append(cap.name)
    
    # Also check via bitmask for speed (if bit_index available)
    # This is a secondary check that validates our logic
    
    passes_hard_gates = len(hard_gate_failures) == 0
    
    # Check soft envelope
    soft_envelope_failures = []
    analysis = db.query(MaterialAnalysis).filter_by(material_id=material_id).first()
    
    if analysis:
        # Get all soft gate rules and user states
        soft_rules = db.query(SoftGateRule).all()
        
        dimension_mapping = {
            "tonal_complexity_stage": analysis.tonal_complexity_stage,
            "interval_size_stage": analysis.interval_size_stage,
            "rhythm_complexity_stage": analysis.rhythm_complexity_stage,
            "range_usage_stage": analysis.range_usage_stage,
        }
        
        for rule in soft_rules:
            material_value = dimension_mapping.get(rule.dimension_name)
            if material_value is None:
                continue
            
            user_state = db.query(UserSoftGateState).filter_by(
                user_id=user_id, dimension_name=rule.dimension_name
            ).first()
            
            comfort = user_state.comfortable_value if user_state else 0
            max_allowed = comfort + rule.frontier_buffer
            
            if material_value > max_allowed:
                soft_envelope_failures.append(
                    f"{rule.dimension_name}: material={material_value}, max_allowed={max_allowed}"
                )
    
    passes_soft_envelope = len(soft_envelope_failures) == 0
    
    return {
        "material_id": material_id,
        "material_title": material.title,
        "user_id": user_id,
        "passes_hard_gates": passes_hard_gates,
        "hard_gate_failures": hard_gate_failures,
        "passes_soft_envelope": passes_soft_envelope,
        "soft_envelope_failures": soft_envelope_failures,
        "overall_eligible": passes_hard_gates and passes_soft_envelope,
    }


@app.post("/admin/materials/{material_id}/analyze")
def admin_trigger_analysis(
    material_id: int,
    db: Session = Depends(get_db)
):
    """
    Trigger re-analysis of a material's MusicXML.
    """
    from app.musicxml_analyzer import analyze_musicxml
    from app.models.capability_schema import MaterialAnalysis
    
    material = db.query(Material).filter_by(id=material_id).first()
    if not material:
        raise HTTPException(status_code=404, detail="Material not found")
    
    if not material.musicxml_canonical:
        raise HTTPException(status_code=400, detail="Material has no MusicXML content")
    
    # Run analysis
    try:
        analysis_result = analyze_musicxml(material.musicxml_canonical)
        
        # Update or create analysis record
        existing = db.query(MaterialAnalysis).filter_by(material_id=material_id).first()
        if existing:
            for key, value in analysis_result.items():
                if hasattr(existing, key):
                    setattr(existing, key, value)
        else:
            analysis = MaterialAnalysis(material_id=material_id, **analysis_result)
            db.add(analysis)
        
        db.commit()
        return {"message": "Analysis completed", "analysis": analysis_result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@app.get("/admin/users/{user_id}/progression")
def admin_get_user_progression(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get comprehensive user progression data for admin inspection.
    """
    from app.models.capability_schema import (
        Capability, UserCapability, UserSoftGateState,
        UserCapabilityEvidenceEvent, UserMaterialState
    )
    
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get user's capabilities
    user_caps = db.query(UserCapability, Capability).join(
        Capability, UserCapability.capability_id == Capability.id
    ).filter(UserCapability.user_id == user_id, UserCapability.is_active == True).all()
    
    mastered = []
    introduced = []
    for user_cap, cap in user_caps:
        cap_data = {
            "id": cap.id,
            "name": cap.name,
            "display_name": cap.display_name,
            "domain": cap.domain,
            "introduced_at": user_cap.introduced_at.isoformat() if user_cap.introduced_at else None,
            "mastered_at": user_cap.mastered_at.isoformat() if user_cap.mastered_at else None,
            "evidence_count": user_cap.evidence_count,
        }
        if user_cap.mastered_at:
            mastered.append(cap_data)
        else:
            introduced.append(cap_data)
    
    # Get recent promotions (capabilities mastered in last 7 days)
    from datetime import timedelta
    recent_date = datetime.datetime.now() - timedelta(days=7)
    recent_promotions = [
        {"capability_name": c["name"], "promoted_at": c["mastered_at"]}
        for c in mastered
        if c["mastered_at"] and c["mastered_at"] > recent_date.isoformat()
    ]
    
    # Get soft gate states
    soft_gates = db.query(UserSoftGateState).filter_by(user_id=user_id).all()
    soft_gate_data = [
        {
            "dimension_name": sg.dimension_name,
            "comfortable_value": sg.comfortable_value,
            "max_demonstrated_value": sg.max_demonstrated_value,
            "frontier_success_ema": sg.frontier_success_ema,
            "frontier_attempt_count_since_last_promo": sg.frontier_attempt_count_since_last_promo,
        }
        for sg in soft_gates
    ]
    
    # Get journey stats
    materials_completed = db.query(UserMaterialState).filter_by(
        user_id=user_id, status="MASTERED"
    ).count()
    
    return {
        "user": {
            "id": user.id,
            "email": user.email,
            "instrument": user.instrument,
            "resonant_note": user.resonant_note,
            "range_low": user.range_low,
            "range_high": user.range_high,
            "day0_completed": getattr(user, "day0_completed", False),
            "day0_stage": getattr(user, "day0_stage", 0),
        },
        "capabilities": {
            "mastered": mastered,
            "introduced": introduced,
            "recent_promotions": recent_promotions,
        },
        "soft_gates": soft_gate_data,
        "journey": {
            "stage": "learning",  # Could compute actual stage
            "capabilities_mastered": len(mastered),
            "materials_completed": materials_completed,
        },
    }


@app.get("/admin/users/{user_id}/session-candidates")
def admin_get_session_candidates(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get the candidate pool of materials for the next session generation.
    """
    from app.models.capability_schema import (
        MaterialAnalysis, MaterialCapability, Capability,
        UserCapability, UserSoftGateState, SoftGateRule
    )
    
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all materials
    materials = db.query(Material).all()
    
    # Get user's mastered capability IDs for quick lookup
    mastered_caps = db.query(UserCapability).filter_by(
        user_id=user_id, is_active=True
    ).filter(UserCapability.mastered_at != None).all()
    mastered_cap_ids = {uc.capability_id for uc in mastered_caps}
    
    # Get soft gate states
    soft_rules = {r.dimension_name: r for r in db.query(SoftGateRule).all()}
    soft_states = {
        s.dimension_name: s
        for s in db.query(UserSoftGateState).filter_by(user_id=user_id).all()
    }
    
    eligible_materials = []
    ineligible_sample = []
    
    for mat in materials:
        # Check hard gates
        req_caps = db.query(MaterialCapability).filter_by(
            material_id=mat.id, is_required=True
        ).all()
        missing_caps = [rc.capability_id for rc in req_caps if rc.capability_id not in mastered_cap_ids]
        
        if missing_caps:
            # Get names of missing capabilities
            missing_names = db.query(Capability.name).filter(
                Capability.id.in_(missing_caps)
            ).all()
            missing_names = [n[0] for n in missing_names]
            
            if len(ineligible_sample) < 20:
                ineligible_sample.append({
                    "id": mat.id,
                    "title": mat.title,
                    "ineligibility_reason": f"Missing capabilities: {', '.join(missing_names[:3])}"
                })
            continue
        
        # Check soft gates
        analysis = db.query(MaterialAnalysis).filter_by(material_id=mat.id).first()
        soft_failure = None
        
        if analysis:
            dimension_mapping = {
                "tonal_complexity_stage": analysis.tonal_complexity_stage,
                "interval_size_stage": analysis.interval_size_stage,
                "rhythm_complexity_stage": analysis.rhythm_complexity_stage,
                "range_usage_stage": analysis.range_usage_stage,
            }
            
            for dim_name, mat_value in dimension_mapping.items():
                if mat_value is None:
                    continue
                    
                rule = soft_rules.get(dim_name)
                state = soft_states.get(dim_name)
                
                if rule:
                    comfort = state.comfortable_value if state else 0
                    max_allowed = comfort + rule.frontier_buffer
                    
                    if mat_value > max_allowed:
                        soft_failure = f"{dim_name} too high ({mat_value} > {max_allowed})"
                        break
        
        if soft_failure:
            if len(ineligible_sample) < 20:
                ineligible_sample.append({
                    "id": mat.id,
                    "title": mat.title,
                    "ineligibility_reason": soft_failure
                })
            continue
        
        eligible_materials.append({
            "id": mat.id,
            "title": mat.title,
            "eligibility_reason": "Passes all gates",
        })
    
    return {
        "user_id": user_id,
        "eligible_materials": eligible_materials,
        "eligible_count": len(eligible_materials),
        "ineligible_sample": ineligible_sample,
        "total_materials": len(materials),
    }


@app.post("/admin/users/{user_id}/generate-diagnostic-session")
def admin_generate_diagnostic_session(
    user_id: int,
    duration_minutes: int = 30,
    db: Session = Depends(get_db)
):
    """
    Generate a practice session with detailed diagnostics for debugging.
    """
    from app.models.capability_schema import (
        MaterialAnalysis, UserCapability, UserSoftGateState, SoftGateRule, Capability
    )
    
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Collect diagnostics as we go
    diagnostics = {
        "target_capabilities": [],
        "hard_gates": [],
        "soft_envelope_filters": [],
        "candidates_considered": 0,
        "candidate_ranking": [],
        "selection_reasons": [],
    }
    
    # Get user's soft gate states for diagnostics
    soft_states = db.query(UserSoftGateState).filter_by(user_id=user_id).all()
    soft_rules = db.query(SoftGateRule).all()
    
    for rule in soft_rules:
        state = next((s for s in soft_states if s.dimension_name == rule.dimension_name), None)
        comfort = state.comfortable_value if state else 0
        max_allowed = comfort + rule.frontier_buffer
        
        diagnostics["soft_envelope_filters"].append({
            "dimension": rule.dimension_name,
            "comfort": comfort,
            "max_allowed": max_allowed,
            "frontier_buffer": rule.frontier_buffer,
        })
    
    # Get target capabilities (based on weightings)
    all_caps = db.query(Capability).order_by(Capability.bit_index).limit(10).all()
    diagnostics["target_capabilities"] = [
        {"name": c.name, "weight": c.difficulty_weight or 1.0}
        for c in all_caps
    ]
    
    # Hard gates description
    diagnostics["hard_gates"] = [
        "User must have mastered all required capabilities",
        "Material must be within user's pitch range",
        "Capability prerequisites must be met",
    ]
    
    # Try to generate a session using existing logic
    try:
        # Use the existing session generation endpoint logic
        from app.session_config import (
            select_capability, select_difficulty, select_intensity,
            select_novelty_or_reinforcement, estimate_mini_session_duration
        )
        
        # Get eligible materials
        eligible = filter_materials_by_capabilities(db.query(Material).all(), db, user_id)
        eligible = filter_materials_by_range(eligible, user.range_low, user.range_high)
        
        diagnostics["candidates_considered"] = len(eligible)
        
        # Sample candidate rankings
        for i, mat in enumerate(eligible[:10]):
            diagnostics["candidate_ranking"].append({
                "title": mat.title,
                "score": 1.0 - (i * 0.1),  # Decreasing score
                "reason": "Selected by standard algorithm"
            })
        
        # Generate actual session
        practice_session = PracticeSession(
            user_id=user_id,
            started_at=datetime.datetime.now(),
            practice_mode="guided"
        )
        db.add(practice_session)
        db.flush()
        
        mini_sessions_out = []
        focus_cards = db.query(FocusCard).all()
        
        for i, material in enumerate(eligible[:3]):
            focus_card = random.choice(focus_cards) if focus_cards else None
            
            target_key = select_key_for_mini_session(material, user, db)
            
            mini_session = MiniSession(
                practice_session_id=practice_session.id,
                material_id=material.id,
                key=target_key,
                focus_card_id=focus_card.id if focus_card else None,
                goal_type="Accuracy"
            )
            db.add(mini_session)
            db.flush()
            
            mini_sessions_out.append({
                "material_id": material.id,
                "material_title": material.title,
                "focus_card_id": focus_card.id if focus_card else None,
                "focus_card_name": focus_card.name if focus_card else "None",
                "goal_type": "Accuracy",
                "target_key": target_key,
            })
            
            diagnostics["selection_reasons"].append({
                "material": material.title,
                "reason": f"Ranked #{i+1} in candidate pool"
            })
        
        db.commit()
        
        return {
            "session": {
                "session_id": practice_session.id,
                "user_id": user_id,
                "planned_duration_minutes": duration_minutes,
                "mini_sessions": mini_sessions_out,
            },
            "diagnostics": diagnostics,
        }
    except Exception as e:
        db.rollback()
        return {
            "session": None,
            "diagnostics": diagnostics,
            "error": str(e),
        }


@app.get("/admin/users/{user_id}/last-session-diagnostics")
def admin_get_last_session_diagnostics(
    user_id: int,
    db: Session = Depends(get_db)
):
    """
    Get diagnostics for the user's last practice session.
    """
    user = db.query(User).filter_by(id=user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get the last session
    last_session = db.query(PracticeSession).filter_by(
        user_id=user_id
    ).order_by(PracticeSession.started_at.desc()).first()
    
    if not last_session:
        return {"session": None, "diagnostics": {"message": "No sessions found"}}
    
    # Get mini-sessions
    mini_sessions = db.query(MiniSession).filter_by(
        practice_session_id=last_session.id
    ).all()
    
    mini_session_data = []
    for mini in mini_sessions:
        mat = db.query(Material).filter_by(id=mini.material_id).first()
        focus = db.query(FocusCard).filter_by(id=mini.focus_card_id).first() if mini.focus_card_id else None
        
        mini_session_data.append({
            "material_id": mini.material_id,
            "material_title": mat.title if mat else "Unknown",
            "target_key": mini.key,
            "focus_card_id": mini.focus_card_id,
            "focus_card_name": focus.name if focus else "None",
            "goal_type": mini.goal_type,
            "is_completed": mini.is_completed,
        })
    
    return {
        "session": {
            "session_id": last_session.id,
            "user_id": user_id,
            "started_at": last_session.started_at.isoformat() if last_session.started_at else None,
            "ended_at": last_session.ended_at.isoformat() if last_session.ended_at else None,
            "practice_mode": last_session.practice_mode,
            "mini_sessions": mini_session_data,
        },
        "diagnostics": {
            "message": "Retrieved from database (live diagnostics not available for past sessions)",
            "mini_session_count": len(mini_session_data),
        },
    }
