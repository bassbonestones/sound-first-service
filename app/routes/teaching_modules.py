"""Teaching Module endpoints for Sound First API.

Provides endpoints for:
- Listing available teaching modules
- Getting module details with lessons
- Tracking user progress through modules/lessons
- Recording lesson attempts
- Generating exercises for lessons
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DbSession
from sqlalchemy import and_
from typing import List, Optional
from datetime import datetime
import json

from app.db import get_db
from app.models.core import User
from app.models.capability_schema import Capability, UserCapability
from app.models.teaching_module import (
    TeachingModule,
    Lesson,
    UserModuleProgress,
    UserLessonProgress,
    LessonAttempt,
)
from app.schemas.teaching_module_schemas import (
    ModuleStatus,
    LessonStatus,
    ModuleSummary,
    ModuleDetail,
    ModuleWithProgress,
    LessonDetail,
    LessonWithProgress,
    LessonConfig,
    LessonMastery,
    UserModuleProgressOut,
    UserLessonProgressOut,
    LessonAttemptCreate,
    LessonAttemptOut,
    LessonAttemptResult,
    GeneratedExercise,
    ExerciseResultSubmit,
)

router = APIRouter(prefix="/modules", tags=["teaching-modules"])


# ==================== Module Endpoints ====================

@router.get("/", response_model=List[ModuleSummary])
def list_modules(
    db: DbSession = Depends(get_db),
    active_only: bool = Query(True, description="Only return active modules"),
):
    """List all available teaching modules."""
    query = db.query(TeachingModule)
    if active_only:
        query = query.filter(TeachingModule.is_active == True)
    
    modules = query.order_by(TeachingModule.display_order).all()
    
    result = []
    for module in modules:
        prereqs = json.loads(module.prerequisite_capability_names) if module.prerequisite_capability_names else []
        lesson_count = db.query(Lesson).filter(
            Lesson.module_id == module.id,
            Lesson.is_active == True
        ).count()
        
        result.append(ModuleSummary(
            id=module.id,
            capability_name=module.capability_name,
            display_name=module.display_name,
            description=module.description,
            icon=module.icon,
            estimated_duration_minutes=module.estimated_duration_minutes,
            difficulty_tier=module.difficulty_tier,
            lesson_count=lesson_count,
            prerequisite_capability_names=prereqs,
        ))
    
    return result


@router.get("/{module_id}", response_model=ModuleDetail)
def get_module(module_id: str, db: DbSession = Depends(get_db)):
    """Get detailed information about a specific module."""
    module = db.query(TeachingModule).filter(TeachingModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    prereqs = json.loads(module.prerequisite_capability_names) if module.prerequisite_capability_names else []
    
    lessons = db.query(Lesson).filter(
        Lesson.module_id == module_id,
        Lesson.is_active == True
    ).order_by(Lesson.sequence_order).all()
    
    lesson_details = []
    for lesson in lessons:
        config = json.loads(lesson.config_json) if lesson.config_json else {}
        mastery = json.loads(lesson.mastery_json) if lesson.mastery_json else {}
        hints = json.loads(lesson.hints_json) if lesson.hints_json else None
        
        lesson_details.append(LessonDetail(
            id=lesson.id,
            display_name=lesson.display_name,
            description=lesson.description,
            exercise_template_id=lesson.exercise_template_id,
            sequence_order=lesson.sequence_order,
            is_required=lesson.is_required,
            config=LessonConfig(**config) if config else LessonConfig(),
            mastery=LessonMastery(**mastery) if mastery else LessonMastery(),
            hints=hints,
        ))
    
    return ModuleDetail(
        id=module.id,
        capability_name=module.capability_name,
        display_name=module.display_name,
        description=module.description,
        icon=module.icon,
        estimated_duration_minutes=module.estimated_duration_minutes,
        difficulty_tier=module.difficulty_tier,
        prerequisite_capability_names=prereqs,
        lessons=lesson_details,
        completion_type=module.completion_type,
        completion_count=module.completion_count,
    )


@router.get("/user/{user_id}/available", response_model=List[ModuleWithProgress])
def get_available_modules(user_id: int, db: DbSession = Depends(get_db)):
    """Get modules available to a user (prerequisites met)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get all active modules
    modules = db.query(TeachingModule).filter(
        TeachingModule.is_active == True
    ).order_by(TeachingModule.display_order).all()
    
    # Get user's completed modules
    completed_module_ids = set(
        p.module_id for p in db.query(UserModuleProgress).filter(
            UserModuleProgress.user_id == user_id,
            UserModuleProgress.status == "completed"
        ).all()
    )
    
    # Get user's mastered capabilities for prerequisite checking
    mastered_cap_names = set(
        cap.name for cap, uc in db.query(Capability, UserCapability).join(
            UserCapability, Capability.id == UserCapability.capability_id
        ).filter(
            UserCapability.user_id == user_id,
            UserCapability.is_active == True,
            UserCapability.mastered_at != None
        ).all()
    )
    
    result = []
    for module in modules:
        # Skip modules where the user already mastered the capability it teaches
        # (but allow modules with no capability_name - they're always eligible like range expansion)
        if module.capability_name and module.capability_name in mastered_cap_names:
            continue
        
        prereqs = json.loads(module.prerequisite_capability_names) if module.prerequisite_capability_names else []
        
        # Check if prerequisites are met (capabilities mastered)
        prereqs_met = all(cap_name in mastered_cap_names for cap_name in prereqs)
        
        if not prereqs_met:
            continue  # Skip modules where prereqs not met
        
        # Get user's progress for this module
        progress = db.query(UserModuleProgress).filter(
            UserModuleProgress.user_id == user_id,
            UserModuleProgress.module_id == module.id
        ).first()
        
        # Count lessons
        total_lessons = db.query(Lesson).filter(
            Lesson.module_id == module.id,
            Lesson.is_active == True,
            Lesson.is_required == True
        ).count()
        
        # Count completed lessons
        lessons_completed = 0
        if progress:
            lessons_completed = db.query(UserLessonProgress).join(Lesson).filter(
                UserLessonProgress.user_id == user_id,
                Lesson.module_id == module.id,
                UserLessonProgress.status == "mastered"
            ).count()
        
        status = ModuleStatus.NOT_STARTED
        if progress:
            status = ModuleStatus(progress.status)
        
        result.append(ModuleWithProgress(
            id=module.id,
            capability_name=module.capability_name,
            display_name=module.display_name,
            description=module.description,
            icon=module.icon,
            estimated_duration_minutes=module.estimated_duration_minutes,
            difficulty_tier=module.difficulty_tier,
            lesson_count=total_lessons,
            prerequisite_capability_names=prereqs,
            status=status,
            lessons_completed=lessons_completed,
            started_at=progress.started_at if progress else None,
            completed_at=progress.completed_at if progress else None,
        ))
    
    return result


# ==================== Progress Endpoints ====================

@router.post("/user/{user_id}/start/{module_id}", response_model=UserModuleProgressOut)
def start_module(user_id: int, module_id: str, db: DbSession = Depends(get_db)):
    """Start a module for a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    module = db.query(TeachingModule).filter(TeachingModule.id == module_id).first()
    if not module:
        raise HTTPException(status_code=404, detail="Module not found")
    
    # Check prerequisites - must have mastered the required capabilities
    prereqs = json.loads(module.prerequisite_capability_names) if module.prerequisite_capability_names else []
    
    # Get user's mastered capabilities
    mastered_cap_names = set(
        cap.name for cap, uc in db.query(Capability, UserCapability).join(
            UserCapability, Capability.id == UserCapability.capability_id
        ).filter(
            UserCapability.user_id == user_id,
            UserCapability.is_active == True,
            UserCapability.mastered_at != None
        ).all()
    )
    
    for prereq_cap in prereqs:
        if prereq_cap not in mastered_cap_names:
            raise HTTPException(
                status_code=400,
                detail=f"Prerequisite capability '{prereq_cap}' not mastered"
            )
    
    # Get or create progress
    progress = db.query(UserModuleProgress).filter(
        UserModuleProgress.user_id == user_id,
        UserModuleProgress.module_id == module_id
    ).first()
    
    if not progress:
        progress = UserModuleProgress(
            user_id=user_id,
            module_id=module_id,
            status="in_progress",
            started_at=datetime.utcnow(),
            last_activity_at=datetime.utcnow(),
        )
        db.add(progress)
    elif progress.status == "not_started":
        progress.status = "in_progress"
        progress.started_at = datetime.utcnow()
        progress.last_activity_at = datetime.utcnow()
    
    # Unlock first lesson
    first_lesson = db.query(Lesson).filter(
        Lesson.module_id == module_id,
        Lesson.is_active == True
    ).order_by(Lesson.sequence_order).first()
    
    if first_lesson:
        lesson_progress = db.query(UserLessonProgress).filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == first_lesson.id
        ).first()
        
        if not lesson_progress:
            lesson_progress = UserLessonProgress(
                user_id=user_id,
                lesson_id=first_lesson.id,
                status="available",
            )
            db.add(lesson_progress)
        elif lesson_progress.status == "locked":
            lesson_progress.status = "available"
    
    db.commit()
    
    total_lessons = db.query(Lesson).filter(
        Lesson.module_id == module_id,
        Lesson.is_active == True,
        Lesson.is_required == True
    ).count()
    
    return UserModuleProgressOut(
        module_id=module_id,
        status=ModuleStatus(progress.status),
        lessons_completed=0,
        total_lessons=total_lessons,
        started_at=progress.started_at,
        completed_at=progress.completed_at,
    )


@router.get("/user/{user_id}/progress/{module_id}", response_model=UserModuleProgressOut)
def get_module_progress(user_id: int, module_id: str, db: DbSession = Depends(get_db)):
    """Get user's progress through a specific module."""
    progress = db.query(UserModuleProgress).filter(
        UserModuleProgress.user_id == user_id,
        UserModuleProgress.module_id == module_id
    ).first()
    
    if not progress:
        # Return not_started progress
        total_lessons = db.query(Lesson).filter(
            Lesson.module_id == module_id,
            Lesson.is_active == True,
            Lesson.is_required == True
        ).count()
        
        return UserModuleProgressOut(
            module_id=module_id,
            status=ModuleStatus.NOT_STARTED,
            lessons_completed=0,
            total_lessons=total_lessons,
        )
    
    total_lessons = db.query(Lesson).filter(
        Lesson.module_id == module_id,
        Lesson.is_active == True,
        Lesson.is_required == True
    ).count()
    
    lessons_completed = db.query(UserLessonProgress).join(Lesson).filter(
        UserLessonProgress.user_id == user_id,
        Lesson.module_id == module_id,
        UserLessonProgress.status == "mastered"
    ).count()
    
    return UserModuleProgressOut(
        module_id=module_id,
        status=ModuleStatus(progress.status),
        lessons_completed=lessons_completed,
        total_lessons=total_lessons,
        started_at=progress.started_at,
        completed_at=progress.completed_at,
    )


@router.get("/user/{user_id}/lessons/{module_id}", response_model=List[LessonWithProgress])
def get_lessons_with_progress(user_id: int, module_id: str, db: DbSession = Depends(get_db)):
    """Get all lessons in a module with user's progress."""
    lessons = db.query(Lesson).filter(
        Lesson.module_id == module_id,
        Lesson.is_active == True
    ).order_by(Lesson.sequence_order).all()
    
    result = []
    for lesson in lessons:
        progress = db.query(UserLessonProgress).filter(
            UserLessonProgress.user_id == user_id,
            UserLessonProgress.lesson_id == lesson.id
        ).first()
        
        status = LessonStatus.LOCKED
        attempts = 0
        current_streak = 0
        best_streak = 0
        best_accuracy = None
        
        if progress:
            status = LessonStatus(progress.status)
            attempts = progress.attempts
            current_streak = progress.current_streak
            best_streak = progress.best_streak
            best_accuracy = progress.best_accuracy
        
        result.append(LessonWithProgress(
            id=lesson.id,
            display_name=lesson.display_name,
            description=lesson.description,
            exercise_template_id=lesson.exercise_template_id,
            sequence_order=lesson.sequence_order,
            is_required=lesson.is_required,
            status=status,
            attempts=attempts,
            current_streak=current_streak,
            best_streak=best_streak,
            best_accuracy=best_accuracy,
        ))
    
    return result


# ==================== Lesson Attempt Endpoints ====================

@router.post("/user/{user_id}/attempt", response_model=LessonAttemptResult)
def record_lesson_attempt(
    user_id: int,
    attempt_data: LessonAttemptCreate,
    db: DbSession = Depends(get_db)
):
    """Record a lesson attempt and update progress."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    lesson = db.query(Lesson).filter(Lesson.id == attempt_data.lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Create attempt record
    attempt = LessonAttempt(
        user_id=user_id,
        lesson_id=attempt_data.lesson_id,
        is_correct=attempt_data.is_correct,
        timing_error_ms=attempt_data.timing_error_ms,
        duration_error_ms=attempt_data.duration_error_ms,
        expected_answer=attempt_data.expected_answer,
        given_answer=attempt_data.given_answer,
        exercise_params_json=json.dumps(attempt_data.exercise_params) if attempt_data.exercise_params else None,
    )
    db.add(attempt)
    
    # Get or create lesson progress
    progress = db.query(UserLessonProgress).filter(
        UserLessonProgress.user_id == user_id,
        UserLessonProgress.lesson_id == attempt_data.lesson_id
    ).first()
    
    if not progress:
        progress = UserLessonProgress(
            user_id=user_id,
            lesson_id=attempt_data.lesson_id,
            status="in_progress",
            started_at=datetime.utcnow(),
        )
        db.add(progress)
    
    # Update progress
    progress.attempts += 1
    progress.last_attempt_at = datetime.utcnow()
    
    if attempt_data.is_correct:
        progress.correct_count += 1
        progress.current_streak += 1
        if progress.current_streak > progress.best_streak:
            progress.best_streak = progress.current_streak
    else:
        progress.current_streak = 0
    
    # Calculate accuracy
    if progress.attempts > 0:
        accuracy = progress.correct_count / progress.attempts
        if progress.best_accuracy is None or accuracy > progress.best_accuracy:
            progress.best_accuracy = accuracy
    
    # Check mastery
    mastery_config = json.loads(lesson.mastery_json) if lesson.mastery_json else {}
    required_streak = mastery_config.get("correct_streak", 8)
    min_accuracy = mastery_config.get("min_accuracy")
    
    lesson_mastered = False
    module_completed = False
    capability_unlocked = None
    
    if progress.current_streak >= required_streak:
        if min_accuracy is None or (progress.best_accuracy and progress.best_accuracy >= min_accuracy):
            progress.status = "mastered"
            progress.mastered_at = datetime.utcnow()
            lesson_mastered = True
            
            # Unlock next lesson
            next_lesson = db.query(Lesson).filter(
                Lesson.module_id == lesson.module_id,
                Lesson.sequence_order > lesson.sequence_order,
                Lesson.is_active == True
            ).order_by(Lesson.sequence_order).first()
            
            if next_lesson:
                next_progress = db.query(UserLessonProgress).filter(
                    UserLessonProgress.user_id == user_id,
                    UserLessonProgress.lesson_id == next_lesson.id
                ).first()
                
                if not next_progress:
                    next_progress = UserLessonProgress(
                        user_id=user_id,
                        lesson_id=next_lesson.id,
                        status="available",
                    )
                    db.add(next_progress)
                elif next_progress.status == "locked":
                    next_progress.status = "available"
            
            # Check if module is complete
            module = db.query(TeachingModule).filter(TeachingModule.id == lesson.module_id).first()
            required_lessons = db.query(Lesson).filter(
                Lesson.module_id == lesson.module_id,
                Lesson.is_active == True,
                Lesson.is_required == True
            ).all()
            
            all_mastered = True
            for req_lesson in required_lessons:
                req_progress = db.query(UserLessonProgress).filter(
                    UserLessonProgress.user_id == user_id,
                    UserLessonProgress.lesson_id == req_lesson.id,
                    UserLessonProgress.status == "mastered"
                ).first()
                if not req_progress:
                    all_mastered = False
                    break
            
            if all_mastered:
                module_progress = db.query(UserModuleProgress).filter(
                    UserModuleProgress.user_id == user_id,
                    UserModuleProgress.module_id == lesson.module_id
                ).first()
                
                if module_progress:
                    module_progress.status = "completed"
                    module_progress.completed_at = datetime.utcnow()
                    module_completed = True
                
                # Mark capability as mastered
                capability = db.query(Capability).filter(
                    Capability.name == module.capability_name
                ).first()
                
                if capability:
                    user_cap = db.query(UserCapability).filter(
                        UserCapability.user_id == user_id,
                        UserCapability.capability_id == capability.id
                    ).first()
                    
                    if not user_cap:
                        user_cap = UserCapability(
                            user_id=user_id,
                            capability_id=capability.id,
                            maturity=1.0,
                            is_mastered=True,
                            mastered_at=datetime.utcnow(),
                        )
                        db.add(user_cap)
                        capability_unlocked = capability.name
                    elif not user_cap.is_mastered:
                        user_cap.is_mastered = True
                        user_cap.maturity = 1.0
                        user_cap.mastered_at = datetime.utcnow()
                        capability_unlocked = capability.name
    elif progress.status == "available":
        progress.status = "in_progress"
    
    db.commit()
    db.refresh(attempt)
    
    return LessonAttemptResult(
        attempt=LessonAttemptOut(
            id=attempt.id,
            lesson_id=attempt.lesson_id,
            is_correct=attempt.is_correct,
            timing_error_ms=attempt.timing_error_ms,
            duration_error_ms=attempt.duration_error_ms,
            expected_answer=attempt.expected_answer,
            given_answer=attempt.given_answer,
            created_at=attempt.created_at,
        ),
        lesson_progress=UserLessonProgressOut(
            lesson_id=progress.lesson_id,
            status=LessonStatus(progress.status),
            attempts=progress.attempts,
            correct_count=progress.correct_count,
            current_streak=progress.current_streak,
            best_streak=progress.best_streak,
            best_accuracy=progress.best_accuracy,
            mastered_at=progress.mastered_at,
        ),
        lesson_mastered=lesson_mastered,
        module_completed=module_completed,
        capability_unlocked=capability_unlocked,
    )


@router.post("/user/{user_id}/lesson/{lesson_id}/complete")
def mark_lesson_complete(
    user_id: int,
    lesson_id: str,
    streak: int = Query(8, description="Final streak achieved"),
    total_attempts: int = Query(8, description="Total attempts made"),
    correct_count: int = Query(8, description="Number correct"),
    db: DbSession = Depends(get_db)
):
    """Mark a lesson as mastered (called when client-side mastery is achieved).
    
    This is a simpler endpoint than /attempt for when the client tracks
    mastery locally and just needs to report the final result.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    # Get or create lesson progress
    progress = db.query(UserLessonProgress).filter(
        UserLessonProgress.user_id == user_id,
        UserLessonProgress.lesson_id == lesson_id
    ).first()
    
    if not progress:
        progress = UserLessonProgress(
            user_id=user_id,
            lesson_id=lesson_id,
            started_at=datetime.utcnow(),
        )
        db.add(progress)
    
    # Update progress with final stats
    progress.status = "mastered"
    progress.mastered_at = datetime.utcnow()
    progress.attempts = total_attempts
    progress.correct_count = correct_count
    progress.current_streak = streak
    progress.best_streak = max(progress.best_streak or 0, streak)
    if total_attempts > 0:
        progress.best_accuracy = correct_count / total_attempts
    
    # Check if module is complete
    module = db.query(TeachingModule).filter(TeachingModule.id == lesson.module_id).first()
    module_completed = False
    capability_unlocked = None
    
    if module:
        # Get all required lessons for this module
        required_lessons = db.query(Lesson).filter(
            Lesson.module_id == module.id,
            Lesson.is_required == True,
            Lesson.is_active == True
        ).all()
        
        # Check if all required lessons are mastered
        all_mastered = True
        for req_lesson in required_lessons:
            req_progress = db.query(UserLessonProgress).filter(
                UserLessonProgress.user_id == user_id,
                UserLessonProgress.lesson_id == req_lesson.id,
                UserLessonProgress.status == "mastered"
            ).first()
            if not req_progress:
                all_mastered = False
                break
        
        if all_mastered:
            module_progress = db.query(UserModuleProgress).filter(
                UserModuleProgress.user_id == user_id,
                UserModuleProgress.module_id == module.id
            ).first()
            
            if module_progress:
                module_progress.status = "completed"
                module_progress.completed_at = datetime.utcnow()
                module_completed = True
            
            # Mark capability as mastered
            capability = db.query(Capability).filter(
                Capability.name == module.capability_name
            ).first()
            
            if capability:
                user_cap = db.query(UserCapability).filter(
                    UserCapability.user_id == user_id,
                    UserCapability.capability_id == capability.id
                ).first()
                
                if not user_cap:
                    user_cap = UserCapability(
                        user_id=user_id,
                        capability_id=capability.id,
                        maturity=1.0,
                        is_mastered=True,
                        mastered_at=datetime.utcnow(),
                    )
                    db.add(user_cap)
                    capability_unlocked = capability.name
                elif not user_cap.is_mastered:
                    user_cap.is_mastered = True
                    user_cap.maturity = 1.0
                    user_cap.mastered_at = datetime.utcnow()
                    capability_unlocked = capability.name
    
    db.commit()
    
    return {
        "status": "success",
        "lesson_id": lesson_id,
        "lesson_mastered": True,
        "module_completed": module_completed,
        "capability_unlocked": capability_unlocked,
    }


# ==================== Exercise Generation ====================

@router.get("/user/{user_id}/exercise/{lesson_id}", response_model=GeneratedExercise)
def generate_exercise(user_id: int, lesson_id: str, db: DbSession = Depends(get_db)):
    """Generate an exercise for a specific lesson.
    
    This endpoint generates the exercise parameters that the mobile app
    will use to run the exercise. The actual audio/visual presentation
    happens on the client side.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    lesson = db.query(Lesson).filter(Lesson.id == lesson_id).first()
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    config = json.loads(lesson.config_json) if lesson.config_json else {}
    feedback_config = json.loads(lesson.feedback_json) if lesson.feedback_json else {}
    
    # Get user's first note for pitch exercises
    first_note = user.resonant_note or "C4"
    
    # Build exercise based on template type
    template_id = lesson.exercise_template_id
    
    exercise = GeneratedExercise(
        exercise_template_id=template_id,
        lesson_id=lesson_id,
        bpm=config.get("bpm", 60),
        count_in_beats=config.get("count_in_beats", 4),
        instruction_text=_get_instruction_text(template_id, config),
        feedback_correct=feedback_config.get("correct", ["Correct!", "Nice!", "That's right!"]),
        feedback_incorrect=feedback_config.get("incorrect", ["Not quite.", "Try again.", "Listen carefully."]),
    )
    
    # Template-specific generation
    if template_id in ["tap_with_beat", "enter_on_beat_one", "internal_pulse"]:
        # Rhythm/pulse exercises
        exercise.model_rhythm = _generate_pulse_pattern(template_id, config)
        
    elif template_id in ["aural_compare", "pitch_direction"]:
        # Pitch discrimination exercises
        exercise.choices = config.get("allowed_answers", ["same", "different"])
        exercise.model_notes = _generate_pitch_sequence(template_id, config, first_note)
        # Randomly select correct answer
        import random
        exercise.correct_answer = random.choice(exercise.choices)
        exercise.model_notes = _adjust_for_answer(exercise.model_notes, exercise.correct_answer, config)
    
    elif template_id in ["call_response_pitch", "call_response_rhythm", "contour_copy"]:
        # Response exercises
        exercise.model_notes = _generate_pitch_sequence(template_id, config, first_note)
    
    return exercise


def _get_instruction_text(template_id: str, config: dict) -> str:
    """Get instruction text for a template."""
    instructions = {
        "tap_with_beat": "Tap along with the beat",
        "enter_on_beat_one": "Enter on beat 1",
        "internal_pulse": "Feel the beat, then continue after clicks stop",
        "aural_compare": "Same or different?",
        "pitch_direction": "Did the pitch go up, down, or stay the same?",
        "call_response_pitch": "Listen, then sing/play back",
        "call_response_rhythm": "Listen, then clap/play the rhythm",
        "contour_copy": "Follow the melody shape",
        "sustain_for_beats": f"Hold for {config.get('beats', 4)} beats",
        "start_on_cue": "Start exactly on the cue",
    }
    return instructions.get(template_id, "Complete the exercise")


def _generate_pulse_pattern(template_id: str, config: dict) -> List[dict]:
    """Generate a pulse/rhythm pattern."""
    beats_per_measure = config.get("beats_per_measure", 4)
    measures = config.get("exercise_measures", 2)
    
    pattern = []
    for i in range(beats_per_measure * measures):
        pattern.append({
            "type": "beat",
            "beat_number": (i % beats_per_measure) + 1,
            "is_downbeat": (i % beats_per_measure) == 0,
        })
    return pattern


def _generate_pitch_sequence(template_id: str, config: dict, first_note: str) -> List[dict]:
    """Generate a pitch sequence starting from user's first note."""
    sequence_length = config.get("sequence_length", 2)
    
    # Simple implementation - start with first_note
    sequence = [{"pitch": first_note, "duration_beats": 1}]
    
    for i in range(1, sequence_length):
        sequence.append({"pitch": first_note, "duration_beats": 1})
    
    return sequence


def _adjust_for_answer(notes: List[dict], answer: str, config: dict) -> List[dict]:
    """Adjust note sequence to produce the correct answer."""
    import random
    
    if len(notes) < 2:
        return notes
    
    # Get interval pool
    interval_pool = config.get("interval_pool", ["M2", "m2", "P4", "P5"])
    interval_semitones = {
        "P1": 0, "m2": 1, "M2": 2, "m3": 3, "M3": 4,
        "P4": 5, "A4": 6, "d5": 6, "P5": 7, "m6": 8,
        "M6": 9, "m7": 10, "M7": 11, "P8": 12,
    }
    
    if answer == "same":
        # Keep notes the same
        pass
    elif answer == "different":
        # Change second note
        interval = random.choice(interval_pool)
        semitones = interval_semitones.get(interval, 2)
        direction = random.choice([1, -1])
        notes[1]["transpose_semitones"] = semitones * direction
    elif answer == "up":
        interval = random.choice(interval_pool)
        semitones = interval_semitones.get(interval, 2)
        notes[1]["transpose_semitones"] = semitones
    elif answer == "down":
        interval = random.choice(interval_pool)
        semitones = interval_semitones.get(interval, 2)
        notes[1]["transpose_semitones"] = -semitones
    
    return notes
