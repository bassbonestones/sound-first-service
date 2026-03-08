"""Session generation and management endpoints."""
from fastapi import APIRouter, Depends, Body, HTTPException, Query
from sqlalchemy.orm import Session as DbSession
import datetime

from app.db import get_db
from app.models.core import (
    User, Material, FocusCard, PracticeSession, 
    MiniSession, PracticeAttempt, CurriculumStep
)
from app.schemas import (
    SelfDirectedSessionIn,
    PracticeAttemptIn,
    MiniSessionOut,
    PracticeSessionResponse,
    CurriculumStepOut,
    MiniSessionWithStepsOut,
    StepCompleteIn,
)
from app.services import (
    SessionService, 
    SessionState, 
    MiniSessionData,
    GOAL_LABEL_MAP,
)
from app.curriculum import generate_curriculum_steps, insert_recovery_steps

router = APIRouter(tags=["sessions"])


def _mini_session_data_to_out(data: MiniSessionData) -> MiniSessionOut:
    """Convert service dataclass to API schema."""
    return MiniSessionOut(
        material_id=data.material_id,
        material_title=data.material_title,
        focus_card_id=data.focus_card_id,
        focus_card_name=data.focus_card_name,
        focus_card_description=data.focus_card_description,
        focus_card_category=data.focus_card_category,
        focus_card_attention_cue=data.focus_card_attention_cue,
        focus_card_micro_cues=data.focus_card_micro_cues,
        focus_card_prompts=data.focus_card_prompts,
        goal_type=data.goal_type,
        goal_label=data.goal_label,
        show_notation=data.show_notation,
        target_key=data.target_key,
        original_key_center=data.original_key_center,
        resolved_musicxml=data.resolved_musicxml,
        starting_pitch=data.starting_pitch
    )


# --- Session Generation Endpoints ---
@router.post("/generate-session", response_model=PracticeSessionResponse)
def generate_session(
    user_id: int = 1,
    planned_duration_minutes: int = 30,
    fatigue: int = 2,
    cooldown_mode: bool = False,
    ear_only_mode: bool = False,
    db: DbSession = Depends(get_db)
):
    """Generate a practice session using probabilistic selection with time budgeting."""
    # Load data from DB
    materials = db.query(Material).all()
    focus_cards = db.query(FocusCard).all()
    
    # Validate content exists
    if not materials and not focus_cards:
        raise HTTPException(status_code=422, detail="No practice content available.")
    if not materials:
        raise HTTPException(status_code=422, detail="No materials available.")
    if not focus_cards:
        raise HTTPException(status_code=422, detail="No focus cards available.")

    # Adjust fatigue for special modes
    if ear_only_mode:
        fatigue = 5
    elif cooldown_mode:
        fatigue = max(fatigue, 4)

    # Get user and history
    user = db.query(User).filter_by(id=user_id).first()
    all_attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
    attempt_history = SessionService.build_attempt_history(all_attempts)

    # Generate mini-sessions using service
    state = SessionState(time_remaining=float(planned_duration_minutes))
    
    while state.time_remaining > 0 and len(state.mini_sessions) < SessionService.MAX_MINI_SESSIONS:
        SessionService.generate_mini_session(
            materials=materials,
            focus_cards=focus_cards,
            state=state,
            attempt_history=attempt_history,
            user=user,
            fatigue=fatigue
        )

    # Persist session to DB
    session_obj = PracticeSession(
        user_id=user_id,
        started_at=datetime.datetime.now(),
        ended_at=None
    )
    db.add(session_obj)
    db.flush()

    for mini_record in state.mini_session_records:
        mini_record.practice_session_id = session_obj.id
        db.add(mini_record)
    db.commit()

    return PracticeSessionResponse(
        session_id=session_obj.id,
        user_id=user_id,
        planned_duration_minutes=planned_duration_minutes,
        generated_at=session_obj.started_at,
        mini_sessions=[_mini_session_data_to_out(ms) for ms in state.mini_sessions]
    )


@router.post("/generate-self-directed-session", response_model=PracticeSessionResponse)
def generate_self_directed_session(data: SelfDirectedSessionIn = Body(...), db: DbSession = Depends(get_db)):
    """Generate a session with user-selected material and focus card."""
    material = db.query(Material).filter(Material.id == data.material_id).first()
    focus_card = db.query(FocusCard).filter(FocusCard.id == data.focus_card_id).first()
    if not material or not focus_card:
        raise HTTPException(status_code=400, detail="Invalid material or focus card")

    mini_data = SessionService.build_mini_session_data(material, focus_card, data.goal_type)
    
    # Persist to DB
    session_obj = PracticeSession(
        user_id=data.user_id,
        started_at=datetime.datetime.now(),
        ended_at=None
    )
    db.add(session_obj)
    db.flush()
    
    mini_record = MiniSession(
        practice_session_id=session_obj.id,
        material_id=material.id,
        key=mini_data.target_key,
        focus_card_id=focus_card.id,
        goal_type=data.goal_type
    )
    db.add(mini_record)
    db.commit()

    return PracticeSessionResponse(
        session_id=session_obj.id,
        user_id=data.user_id,
        planned_duration_minutes=data.planned_duration_minutes,
        generated_at=session_obj.started_at,
        mini_sessions=[_mini_session_data_to_out(mini_data)]
    )


# --- Practice Attempts ---
@router.post("/practice-attempt")
def record_practice_attempt(attempt: PracticeAttemptIn, db: DbSession = Depends(get_db)):
    """Record a practice attempt."""
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
def get_practice_attempts(user_id: int = Query(...), db: DbSession = Depends(get_db)):
    """Get all practice attempts for a user."""
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
def complete_session(session_id: int, db: DbSession = Depends(get_db)):
    """Mark a session as complete."""
    session = db.query(PracticeSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    session.ended_at = datetime.datetime.now()
    db.commit()
    return {"status": "success", "session_id": session_id}


# --- Mini-Session Curriculum ---
@router.get("/mini-sessions/{mini_session_id}/curriculum")
def get_mini_session_curriculum(mini_session_id: int, db: DbSession = Depends(get_db)):
    """Get the full curriculum for a mini-session with all steps."""
    mini = db.query(MiniSession).filter_by(id=mini_session_id).first()
    if not mini:
        raise HTTPException(status_code=404, detail="Mini-session not found")

    material = db.query(Material).filter_by(id=mini.material_id).first()
    focus_card = db.query(FocusCard).filter_by(id=mini.focus_card_id).first()

    # Get or generate curriculum steps
    steps = db.query(CurriculumStep).filter_by(mini_session_id=mini_session_id).order_by(CurriculumStep.step_index).all()

    if not steps:
        prompts = SessionService.parse_focus_card_json_field(focus_card.prompts) if focus_card else {}
        step_data = generate_curriculum_steps(
            goal_type=mini.goal_type or "repertoire_fluency",
            focus_card_prompts=prompts if isinstance(prompts, dict) else {},
            material_title=material.title if material else "Unknown",
            target_key=mini.key or "C major",
            fatigue_level=2
        )

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
def complete_step(
    mini_session_id: int, 
    step_index: int, 
    data: StepCompleteIn = Body(...), 
    db: DbSession = Depends(get_db)
):
    """Mark a curriculum step as complete and advance to next step."""
    mini = db.query(MiniSession).filter_by(id=mini_session_id).first()
    if not mini:
        raise HTTPException(status_code=404, detail="Mini-session not found")

    step = db.query(CurriculumStep).filter_by(mini_session_id=mini_session_id, step_index=step_index).first()
    if not step:
        raise HTTPException(status_code=404, detail="Step not found")

    step.is_completed = True
    step.rating = data.rating
    step.notes = data.notes

    # Handle strain detection for range work
    if data.strain_detected and mini.goal_type == "range_expansion":
        mini.strain_detected = True
        mini.is_completed = True
        db.commit()
        return {
            "status": "strain_detected",
            "message": "Session terminated for safety. Take a break.",
            "attempt_count": mini.attempt_count or 0
        }

    # Track failed attempts for range expansion (max 3)
    if step.step_type == "PLAY" and mini.goal_type == "range_expansion":
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

    # Check for next step
    next_step = db.query(CurriculumStep).filter_by(
        mini_session_id=mini_session_id, 
        step_index=step_index + 1
    ).first()

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
def get_next_mini_session(session_id: int, db: DbSession = Depends(get_db)):
    """Get the next incomplete mini-session in a practice session."""
    session = db.query(PracticeSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    mini = db.query(MiniSession).filter_by(
        practice_session_id=session_id,
        is_completed=False
    ).order_by(MiniSession.id).first()

    if not mini:
        return {"status": "session_complete", "message": "All mini-sessions complete!"}

    return get_mini_session_curriculum(mini.id, db)
