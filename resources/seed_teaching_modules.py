"""Seed teaching modules into the database.

Run with: python -m resources.seed_teaching_modules
"""
import json
import sys
sys.path.insert(0, '.')

from app.db import SessionLocal
from app.models.teaching_module import TeachingModule, Lesson

# ============================================================
# TEACHING MODULE DEFINITIONS
# ============================================================

MODULES = [
    # Note: first_note is established during Day 0 onboarding, not as a separate module
    # These modules become available after Day 0 is complete
    {
        "id": "pitch_direction_module",
        "capability_name": "pitch_direction_awareness",
        "display_name": "Pitch Direction",
        "description": "Learn to hear when melody moves up, down, or stays the same",
        "icon": "arrow-up-down",
        "prerequisite_capability_names": [],  # Available after Day 0 (first_note learned)
        "estimated_duration_minutes": 15,
        "difficulty_tier": 1,
        "display_order": 10,
        "completion_type": "all_required",
    },
    {
        "id": "pulse_tracking_module",
        "capability_name": "pulse_tracking",
        "display_name": "Feel the Pulse",
        "description": "Develop an internal sense of steady beat",
        "icon": "metronome",
        "prerequisite_capability_names": [],  # Available after Day 0 (first_note learned)
        "estimated_duration_minutes": 12,
        "difficulty_tier": 1,
        "display_order": 11,
        "completion_type": "all_required",
    },
    {
        "id": "whole_note_module",
        "capability_name": "rhythm_whole_notes",
        "display_name": "The Whole Note",
        "description": "Learn to sustain a note for 4 beats, ending right on the next ONE",
        "icon": "music-note",
        "prerequisite_capability_names": ["pulse_tracking"],  # Must feel the pulse first
        "estimated_duration_minutes": 10,
        "difficulty_tier": 1,
        "display_order": 12,
        "completion_type": "all_required",
    },
    {
        "id": "time_signature_basics_module",
        "capability_name": "time_signature_basics",
        "display_name": "Time Signature Basics",
        "description": "Learn what time signatures mean: top number = beats per measure, bottom number = note type",
        "icon": "time-signature",
        "prerequisite_capability_names": ["staff_basics", "rhythm_whole_notes"],  # Must know the staff and whole notes
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 13,
        "completion_type": "all_required",
    },
    {
        "id": "range_expansion_module",
        "capability_name": None,  # No capability - just expands comfort range
        "display_name": "Expand Your Range",
        "description": "Gradually extend your comfortable playing range, one note at a time",
        "icon": "expand",
        "prerequisite_capability_names": ["first_note", "pitch_direction_awareness"],
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 15,
        "completion_type": "all_required",
    },
]

# ============================================================
# LESSON DEFINITIONS
# ============================================================

LESSONS = [
    # Note: No first_note lessons - Day 0 handles that

    # ========== Pitch Direction Module ==========
    {
        "id": "pitch_direction_L1_same_different",
        "module_id": "pitch_direction_module",
        "display_name": "Same or Different?",
        "description": "Hear if two notes are the same or different",
        "exercise_template_id": "aural_compare",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "bpm": 60,
            "comparison_type": "pitch",
            "allowed_answers": ["same", "different"],
            "interval_pool": ["P1", "P5", "P4", "M3"],
            "sequence_length": 2,
            "use_first_note": True,
        },
        "mastery": {
            "correct_streak": 8,
        },
        "feedback": {
            "correct": ["Yes!", "That's right!", "You got it!"],
            "incorrect": ["Not quite. Listen again.", "Try once more."],
        },
        "hints": [
            "Close your eyes and really listen",
            "Focus on whether the pitch changed at all",
        ],
    },
    {
        "id": "pitch_direction_L2_up_down_easy",
        "module_id": "pitch_direction_module",
        "display_name": "Up or Down? (Easy)",
        "description": "Hear if the pitch goes up or down - large intervals",
        "exercise_template_id": "pitch_direction",
        "sequence_order": 2,
        "is_required": True,
        "config": {
            "allowed_answers": ["up", "down"],
            "interval_pool": ["P5", "P4", "M3"],
            "sequence_length": 2,
            "use_first_note": True,
        },
        "mastery": {
            "correct_streak": 8,
        },
        "hints": [
            "Think about going up stairs vs down stairs",
            "Large jumps are easier to hear",
        ],
    },
    {
        "id": "pitch_direction_L3_up_down_medium",
        "module_id": "pitch_direction_module",
        "display_name": "Up or Down? (Medium)",
        "description": "Hear if the pitch goes up or down - smaller intervals",
        "exercise_template_id": "pitch_direction",
        "sequence_order": 3,
        "is_required": True,
        "config": {
            "allowed_answers": ["up", "down"],
            "interval_pool": ["M2", "m2", "m3"],
            "sequence_length": 2,
            "use_first_note": True,
        },
        "mastery": {
            "correct_streak": 8,
        },
        "hints": [
            "Small steps require more careful listening",
            "Feel whether the note is higher or lower",
        ],
    },
    {
        "id": "pitch_direction_L4_three_way",
        "module_id": "pitch_direction_module",
        "display_name": "Up, Down, or Same?",
        "description": "Choose from all three possibilities",
        "exercise_template_id": "pitch_direction",
        "sequence_order": 4,
        "is_required": True,
        "config": {
            "allowed_answers": ["up", "down", "same"],
            "interval_pool": ["P1", "M2", "m2", "M3", "m3"],
            "sequence_length": 2,
            "use_first_note": True,
        },
        "mastery": {
            "correct_streak": 10,
        },
    },
    {
        "id": "pitch_direction_L5_contour",
        "module_id": "pitch_direction_module",
        "display_name": "Follow the Contour",
        "description": "Track the shape of a 3-note melody",
        "exercise_template_id": "contour_copy",
        "sequence_order": 5,
        "is_required": True,
        "config": {
            "contour_types": ["up-down", "down-up", "up-up", "down-down"],
            "sequence_length": 3,
            "use_first_note": True,
            "mode": "identify_then_sing",
        },
        "mastery": {
            "correct_streak": 6,
        },
    },
    
    # ========== Pulse Tracking Module ==========
    {
        "id": "pulse_L1_tap_along",
        "module_id": "pulse_tracking_module",
        "display_name": "Tap Along",
        "description": "Tap along with a steady beat",
        "exercise_template_id": "tap_with_beat",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "bpm": 60,
            "beats_per_measure": 4,
            "exercise_measures": 4,
            "count_in_beats": 4,
            "timing_tolerance_ms": 200,
        },
        "mastery": {
            "correct_streak": 8,
        },
        "feedback": {
            "correct": ["Great timing!", "Right on the beat!", "Perfect!"],
            "incorrect": ["A bit off. Feel the pulse.", "Listen and try again."],
        },
        "hints": [
            "Let your body feel the pulse",
            "Don't think - just feel the beat",
            "Relax your shoulders",
        ],
    },
    {
        "id": "pulse_L2_find_beat_one",
        "module_id": "pulse_tracking_module",
        "display_name": "Feel Beat 1",
        "description": "Identify and feel the downbeat (beat 1)",
        "exercise_template_id": "enter_on_beat_one",
        "sequence_order": 2,
        "is_required": True,
        "config": {
            "bpm": 60,
            "beats_per_measure": 4,
            "exercise_measures": 2,
            "count_in_beats": 4,
            "target_beat": 1,
            "timing_tolerance_ms": 150,
            "accent_beat_one": True,
        },
        "mastery": {
            "correct_streak": 8,
        },
        "feedback": {
            "correct": ["Right on beat 1!", "You found it!", "Perfect entry!"],
            "incorrect": ["That wasn't beat 1. Listen for the accent.", "Try feeling where the pattern starts."],
        },
        "hints": [
            "Beat 1 usually feels stronger",
            "Feel where the pattern restarts",
            "Listen for the natural emphasis",
        ],
    },
    {
        "id": "pulse_L3_enter_on_one",
        "module_id": "pulse_tracking_module",
        "display_name": "Enter on One",
        "description": "Play your first note precisely on beat 1",
        "exercise_template_id": "start_on_cue",
        "sequence_order": 3,
        "is_required": True,
        "config": {
            "bpm": 60,
            "beats_per_measure": 4,
            "count_in_beats": 4,
            "target_beat": 1,
            "timing_tolerance_ms": 100,
            "use_first_note": True,
        },
        "mastery": {
            "correct_streak": 8,
        },
        "feedback": {
            "correct": ["Perfect entry!", "Right on time!", "Excellent timing!"],
            "incorrect": ["A bit early/late. Feel the pulse first.", "Wait for beat 1."],
        },
        "hints": [
            "Hear the note in your head before playing",
            "Let the pulse carry you in",
            "Don't rush - trust the timing",
        ],
    },
    {
        "id": "pulse_L4_internal_pulse",
        "module_id": "pulse_tracking_module",
        "display_name": "Internal Pulse",
        "description": "Continue the beat internally after clicks stop",
        "exercise_template_id": "internal_pulse",
        "sequence_order": 4,
        "is_required": True,
        "config": {
            "bpm": 60,
            "beats_per_measure": 4,
            "count_in_beats": 4,
            "silent_beats": 4,
            "reentry_beat": 1,
            "timing_tolerance_ms": 100,
        },
        "mastery": {
            "correct_streak": 6,
        },
        "feedback": {
            "correct": ["You kept the pulse!", "Perfect internal timing!", "Great internal clock!"],
            "incorrect": ["Lost the pulse. Try keeping it in your body.", "Feel it internally."],
        },
        "hints": [
            "Feel the pulse in your body, not just your ears",
            "Let your body be the metronome",
            "Keep breathing with the beat",
        ],
    },
    
    # ========== Whole Note Module ==========
    {
        "id": "whole_note_L1_lesson",
        "module_id": "whole_note_module",
        "display_name": "The Whole Note",
        "description": "Learn that a whole note lasts 4 beats and ends on the next ONE",
        "exercise_template_id": "whole_note_lesson",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "bpm": 60,
            "use_first_note": True,
        },
        "mastery": {
            "correct_streak": 3,
        },
        "feedback": {
            "correct": ["Perfect timing!", "You got it!", "That's a whole note!"],
            "incorrect": ["Try again - hold for 4 beats, release on ONE"],
        },
        "hints": [
            "A whole note = 4 beats",
            "The note ends right on the next ONE",
            "Count: 1 - 2 - 3 - 4 - (1)",
        ],
    },
    
    # ========== Time Signature Basics Module ==========
    {
        "id": "time_signature_basics_L1_lesson",
        "module_id": "time_signature_basics_module",
        "display_name": "Time Signature Basics",
        "description": "Learn what time signatures mean: top number = beats, bottom number = note type",
        "exercise_template_id": "time_signature_basics",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "use_notation": True,
        },
        "mastery": {
            "correct_streak": 4,  # Must get all 4 quiz questions right
        },
        "feedback": {
            "correct": ["Perfect!", "You got it!", "That's right!"],
            "incorrect": ["Try again - review the material"],
        },
        "hints": [
            "Top number = how many beats per measure",
            "Bottom number = what note gets one beat",
            "4 = quarter note, 8 = eighth note, 2 = half note",
        ],
    },
    
    # ========== Range Expansion Module ==========
    {
        "id": "range_expansion_L1_lesson",
        "module_id": "range_expansion_module",
        "display_name": "Expand Your Range",
        "description": "Add one new note to your comfortable range",
        "exercise_template_id": "range_expansion",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "bpm": 60,
            "use_drone": True,
            "expansion_direction": "auto",  # System picks up or down based on user's range
        },
        "mastery": {
            "correct_streak": 3,
        },
        "feedback": {
            "correct": ["Range expanded!", "New note added!", "You're growing!"],
            "incorrect": ["Try finding that note again", "Almost - listen carefully"],
        },
        "hints": [
            "Listen to the target pitch",
            "Adjust until you match",
            "Take your time to find it",
        ],
    },
]


def seed_modules(db):
    """Seed teaching modules into database."""
    print("Seeding teaching modules...")
    
    for module_data in MODULES:
        existing = db.query(TeachingModule).filter(
            TeachingModule.id == module_data["id"]
        ).first()
        
        if existing:
            # Update existing
            for key, value in module_data.items():
                if key == "prerequisite_capability_names":
                    value = json.dumps(value)
                setattr(existing, key, value)
            print(f"  Updated module: {module_data['id']}")
        else:
            # Create new
            module = TeachingModule(
                id=module_data["id"],
                capability_name=module_data["capability_name"],
                display_name=module_data["display_name"],
                description=module_data.get("description"),
                icon=module_data.get("icon"),
                prerequisite_capability_names=json.dumps(module_data.get("prerequisite_capability_names", [])),
                estimated_duration_minutes=module_data.get("estimated_duration_minutes"),
                difficulty_tier=module_data.get("difficulty_tier", 1),
                display_order=module_data.get("display_order", 0),
                completion_type=module_data.get("completion_type", "all_required"),
                completion_count=module_data.get("completion_count"),
                is_active=True,
            )
            db.add(module)
            print(f"  Created module: {module_data['id']}")
    
    db.commit()
    print(f"  Total: {len(MODULES)} modules")


def seed_lessons(db):
    """Seed lessons into database."""
    print("Seeding lessons...")
    
    for lesson_data in LESSONS:
        existing = db.query(Lesson).filter(
            Lesson.id == lesson_data["id"]
        ).first()
        
        config_json = json.dumps(lesson_data.get("config", {}))
        mastery_json = json.dumps(lesson_data.get("mastery", {}))
        feedback_json = json.dumps(lesson_data.get("feedback", {})) if lesson_data.get("feedback") else None
        hints_json = json.dumps(lesson_data.get("hints", [])) if lesson_data.get("hints") else None
        
        if existing:
            # Update existing
            existing.module_id = lesson_data["module_id"]
            existing.display_name = lesson_data["display_name"]
            existing.description = lesson_data.get("description")
            existing.exercise_template_id = lesson_data["exercise_template_id"]
            existing.config_json = config_json
            existing.mastery_json = mastery_json
            existing.feedback_json = feedback_json
            existing.hints_json = hints_json
            existing.sequence_order = lesson_data["sequence_order"]
            existing.is_required = lesson_data.get("is_required", True)
            existing.unlock_condition = lesson_data.get("unlock_condition", "previous")
            print(f"  Updated lesson: {lesson_data['id']}")
        else:
            # Create new
            lesson = Lesson(
                id=lesson_data["id"],
                module_id=lesson_data["module_id"],
                display_name=lesson_data["display_name"],
                description=lesson_data.get("description"),
                exercise_template_id=lesson_data["exercise_template_id"],
                config_json=config_json,
                mastery_json=mastery_json,
                feedback_json=feedback_json,
                hints_json=hints_json,
                sequence_order=lesson_data["sequence_order"],
                is_required=lesson_data.get("is_required", True),
                unlock_condition=lesson_data.get("unlock_condition", "previous"),
                is_active=True,
            )
            db.add(lesson)
            print(f"  Created lesson: {lesson_data['id']}")
    
    db.commit()
    print(f"  Total: {len(LESSONS)} lessons")


def main():
    """Main entry point."""
    db = SessionLocal()
    try:
        seed_modules(db)
        seed_lessons(db)
        print("\nDone! Teaching modules seeded successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
