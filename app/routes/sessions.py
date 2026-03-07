"""Session generation and management endpoints."""
from fastapi import APIRouter, Depends, Body, HTTPException, Query
from sqlalchemy.orm import Session
import datetime
import random
import json

from app.db import get_db
from app.models.core import User, Material, FocusCard, PracticeSession, MiniSession, PracticeAttempt, CurriculumStep
from app.schemas import (
    SelfDirectedSessionIn,
    PracticeAttemptIn,
    MiniSessionOut,
    PracticeSessionResponse,
    CurriculumStepOut,
    MiniSessionWithStepsOut,
    StepCompleteIn,
)
from app.curriculum import (
    generate_curriculum_steps,
    filter_materials_by_range,
    filter_keys_by_range,
    select_key_for_mini_session,
    get_goals_for_fatigue,
    insert_recovery_steps,
)
from app.session_config import (
    select_capability,
    select_difficulty,
    select_intensity,
    select_novelty_or_reinforcement,
    estimate_mini_session_duration,
    should_show_notation,
)
from app.spaced_repetition import (
    build_sr_item_from_db,
    get_capability_weight_adjustment,
)

router = APIRouter(tags=["sessions"])


# --- Constants ---
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


# --- Helper Functions ---
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


# --- Session Generation Endpoints ---
@router.post("/generate-session", response_model=PracticeSessionResponse)
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
    if not materials and not focus_cards:
        raise HTTPException(
            status_code=422,
            detail="No practice content available. Please add materials and focus cards to the database."
        )
    if not materials:
        raise HTTPException(
            status_code=422,
            detail="No materials available. Please add materials to the database."
        )
    if not focus_cards:
        raise HTTPException(
            status_code=422,
            detail="No focus cards available. Please add focus cards to the database."
        )

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


@router.post("/generate-self-directed-session", response_model=PracticeSessionResponse)
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
@router.post("/practice-attempt")
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


@router.get("/practice-attempts")
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


# --- Session Completion ---
@router.post("/sessions/{session_id}/complete")
def complete_session(session_id: int, db: Session = Depends(get_db)):
    session = db.query(PracticeSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.ended_at = datetime.datetime.now()
    db.commit()
    return {"status": "success", "session_id": session_id}


# --- Mini-Session Curriculum ---
@router.get("/mini-sessions/{mini_session_id}/curriculum")
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


@router.post("/mini-sessions/{mini_session_id}/steps/{step_index}/complete")
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


@router.get("/sessions/{session_id}/next-mini-session")
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
