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
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 13,
        "completion_type": "all_required",
    },
    {
        "id": "time_signature_4_4_module",
        "capability_name": "time_signature_4_4",
        "display_name": "4/4 Time",
        "description": "Learn 4/4 time: 4 beats per measure, quarter note gets the beat, and common time",
        "icon": "time-signature",
        "estimated_duration_minutes": 6,
        "difficulty_tier": 1,
        "display_order": 14,
        "completion_type": "all_required",
    },
    {
        "id": "whole_rest_module",
        "capability_name": "rest_whole",
        "display_name": "The Whole Rest",
        "description": "Learn the whole rest: 4 beats of silence that hangs below the line because it's heavy",
        "icon": "music-rest",
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 15,
        "completion_type": "all_required",
    },
    {
        "id": "half_note_module",
        "capability_name": "rhythm_half_notes",
        "display_name": "The Half Note",
        "description": "Learn the half note: 2 beats, has a stem, hollow head",
        "icon": "music-note",
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 16,
        "completion_type": "all_required",
    },
    {
        "id": "half_rest_module",
        "capability_name": "rest_half",
        "display_name": "The Half Rest",
        "description": "Learn the half rest: 2 beats of silence that sits ON TOP of the line (like a hat)",
        "icon": "music-rest",
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 17,
        "completion_type": "all_required",
    },
    {
        "id": "quarter_note_module",
        "capability_name": "rhythm_quarter_notes",
        "display_name": "The Quarter Note",
        "description": "Learn the quarter note: 1 beat, has a stem, filled/solid head",
        "icon": "music-note",
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 18,
        "completion_type": "all_required",
    },
    {
        "id": "quarter_rest_module",
        "capability_name": "rest_quarter",
        "display_name": "The Quarter Rest",
        "description": "Learn the quarter rest: 1 beat of silence with a squiggly 'lightning bolt' shape",
        "icon": "music-rest",
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 19,
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
        "display_order": 20,
        "completion_type": "all_required",
    },
    {
        "id": "diatonic_scale_fragment_2_module",
        "capability_name": "diatonic_scale_fragment_2",
        "display_name": "2-Note Scale Fragments",
        "description": "Play 2-note diatonic scale fragments with pitch and rhythm precision",
        "icon": "music-note-2",
        "estimated_duration_minutes": 15,
        "difficulty_tier": 2,
        "display_order": 25,
        "completion_type": "all_required",
    },
    {
        "id": "note_name_recognition_module",
        "capability_name": "note_name_recognition",
        "display_name": "Note Names: A to G",
        "description": "Learn the seven note names that repeat in a cycle: A B C D E F G",
        "icon": "abc",
        "estimated_duration_minutes": 10,
        "difficulty_tier": 1,
        "display_order": 21,
        "completion_type": "all_required",
    },
    {
        "id": "octave_equivalence_module",
        "capability_name": "octave_equivalence",
        "display_name": "The Octave",
        "description": "Learn that notes an octave apart share the same name - same note, higher or lower version",
        "icon": "layers",
        "estimated_duration_minutes": 12,
        "difficulty_tier": 1,
        "display_order": 22,
        "completion_type": "all_required",
    },
    {
        "id": "half_steps_theory_module",
        "capability_name": "half_steps_theory",
        "display_name": "Half Steps",
        "description": "Learn the half step (semitone) - the smallest interval in Western music",
        "icon": "piano",
        "estimated_duration_minutes": 10,
        "difficulty_tier": 1,
        "display_order": 23,
        "completion_type": "all_required",
    },
    {
        "id": "accidental_flat_module",
        "capability_name": "accidental_flat_symbol",
        "display_name": "The Flat Sign",
        "description": "Learn the flat (♭) - lowers a note by one half step",
        "icon": "flat",
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 24,
        "completion_type": "all_required",
    },
    {
        "id": "accidental_sharp_module",
        "capability_name": "accidental_sharp_symbol",
        "display_name": "The Sharp Sign",
        "description": "Learn the sharp (♯) - raises a note by one half step",
        "icon": "sharp",
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 25,
        "completion_type": "all_required",
    },
    {
        "id": "accidental_natural_module",
        "capability_name": "accidental_natural_symbol",
        "display_name": "The Natural Sign",
        "description": "Learn the natural (♮) - cancels a sharp or flat",
        "icon": "natural",
        "estimated_duration_minutes": 8,
        "difficulty_tier": 1,
        "display_order": 26,
        "completion_type": "all_required",
    },
    {
        "id": "whole_steps_theory_module",
        "capability_name": "whole_steps_theory",
        "display_name": "Whole Steps",
        "description": "Learn the whole step - two half steps combined, skip one key",
        "icon": "piano",
        "estimated_duration_minutes": 10,
        "difficulty_tier": 1,
        "display_order": 27,
        "completion_type": "all_required",
    },
    {
        "id": "diatonic_scale_pattern_module",
        "capability_name": "diatonic_scale_pattern",
        "display_name": "Major Scale Pattern",
        "description": "Learn the WWHWWWH pattern that creates the major scale",
        "icon": "scale",
        "estimated_duration_minutes": 12,
        "difficulty_tier": 2,
        "display_order": 28,
        "completion_type": "all_required",
    },
    {
        "id": "key_signature_basics_module",
        "capability_name": "key_signature_basics",
        "display_name": "Key Signatures",
        "description": "Learn what key signatures are and how they work",
        "icon": "key",
        "estimated_duration_minutes": 10,
        "difficulty_tier": 2,
        "display_order": 29,
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
    
    # ========== 4/4 Time Signature Module ==========
    {
        "id": "time_signature_4_4_L1_lesson",
        "module_id": "time_signature_4_4_module",
        "display_name": "4/4 Time",
        "description": "Learn 4/4 time: 4 beats per measure, quarter note gets the beat, and common time",
        "exercise_template_id": "time_signature_4_4",
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
            "4/4 = 4 beats per measure",
            "The bottom 4 means quarter note gets the beat",
            "C = Common Time = 4/4",
            "A whole note fills one 4/4 measure perfectly",
        ],
    },
    
    # ========== Whole Rest Module ==========
    {
        "id": "whole_rest_L1_lesson",
        "module_id": "whole_rest_module",
        "display_name": "The Whole Rest",
        "description": "Learn the whole rest: 4 beats of silence that hangs below the line",
        "exercise_template_id": "whole_rest_lesson",
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
            "correct": ["Perfect timing!", "You got the rest!", "Silence is golden!"],
            "incorrect": ["Try again - stay silent during the rest!"],
        },
        "hints": [
            "A whole rest = 4 beats of SILENCE",
            "It hangs BELOW the line (it's heavy!)",
            "Play: note (4 beats), REST (silent!), note (4 beats)",
        ],
    },
    
    # ========== Half Note Module ==========
    {
        "id": "half_note_L1_lesson",
        "module_id": "half_note_module",
        "display_name": "The Half Note",
        "description": "Learn the half note: 2 beats, has a stem, hollow head",
        "exercise_template_id": "half_note_lesson",
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
            "correct": ["Perfect timing!", "You got it!", "That's a half note!"],
            "incorrect": ["Try again - hold for 2 beats, release on 3"],
        },
        "hints": [
            "A half note = 2 beats",
            "It has a stem and a hollow (white) head",
            "Count: 1 - 2 - (3) stop!",
        ],
    },
    
    # ========== Half Rest Module ==========
    {
        "id": "half_rest_L1_lesson",
        "module_id": "half_rest_module",
        "display_name": "The Half Rest",
        "description": "Learn the half rest: 2 beats of silence that sits ON TOP of the line",
        "exercise_template_id": "half_rest_lesson",
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
            "correct": ["Perfect timing!", "You got the rest!", "Silence for 2!"],
            "incorrect": ["Try again - stay silent during the rest!"],
        },
        "hints": [
            "A half rest = 2 beats of SILENCE",
            "It sits ON TOP of the line (like a HAT!)",
            "Play: half note, REST (silent 2 beats!), half note",
        ],
    },
    
    # ========== Quarter Note Module ==========
    {
        "id": "quarter_note_L1_lesson",
        "module_id": "quarter_note_module",
        "display_name": "The Quarter Note",
        "description": "Learn the quarter note: 1 beat, has a stem, filled/solid head",
        "exercise_template_id": "quarter_note_lesson",
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
            "correct": ["Perfect timing!", "You got it!", "That's a quarter note!"],
            "incorrect": ["Try again - play for 1 beat"],
        },
        "hints": [
            "A quarter note = 1 beat",
            "It has a stem and a filled (black) head",
            "Count: 1 - (2) stop!",
        ],
    },
    
    # ========== Quarter Rest Module ==========
    {
        "id": "quarter_rest_L1_lesson",
        "module_id": "quarter_rest_module",
        "display_name": "The Quarter Rest",
        "description": "Learn the quarter rest: 1 beat of silence with squiggly shape",
        "exercise_template_id": "quarter_rest_lesson",
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
            "correct": ["Perfect timing!", "You got the rest!", "Note-rest-note-rest!"],
            "incorrect": ["Try again - be silent on the rests!"],
        },
        "hints": [
            "A quarter rest = 1 beat of SILENCE",
            "It looks like a squiggly lightning bolt",
            "Play: note-rest-note-rest (alternating pattern)",
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
    
    # ========== Diatonic Scale Fragment-2 Module ==========
    {
        "id": "fragment_2_L1_lesson",
        "module_id": "diatonic_scale_fragment_2_module",
        "display_name": "2-Note Fragments",
        "description": "Play 2-note diatonic scale patterns: linear up/down, arc up/down",
        "exercise_template_id": "fragment_2_lesson",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "bpm": 66,
            "tempo_range": [50, 80],
            "use_first_note": True,
            "use_focus_cards": True,
            "use_drone_phase": True,
            "show_notation": True,
        },
        "mastery": {
            "patterns_complete": ["linear_up", "linear_down", "arc_up", "arc_down"],
            "success_per_pattern": 1,
        },
        "feedback": {
            "correct": ["Great pitch!", "Solid rhythm!", "Now that's musical!"],
            "incorrect": ["Listen again", "Focus on pitch center", "Lock in the beat"],
        },
        "hints": [
            "1→2 (Linear Up): Scale degrees 1 to 2",
            "2→1 (Linear Down): Scale degrees 2 to 1",
            "1→2→1 (Arc Up): Start/end on 1",
            "2→1→2 (Arc Down): Start/end on 2",
        ],
    },
    
    # ========== Note Name Recognition Module ==========
    {
        "id": "note_name_L1_pattern",
        "module_id": "note_name_recognition_module",
        "display_name": "The Seven Letter Names",
        "description": "Learn that music uses seven letters that repeat: A B C D E F G A B C...",
        "exercise_template_id": "note_name_pattern",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "show_visual": True,
            "show_pattern": "A B C D E F G A B C",
            "key_concept": "The names repeat in a cycle of seven",
        },
        "mastery": {
            "correct_streak": 4,
        },
        "feedback": {
            "correct": ["That's right!", "You got it!", "Perfect!"],
            "incorrect": ["Remember: A B C D E F G, then it repeats"],
        },
        "hints": [
            "There are only 7 letter names in music",
            "After G comes A again",
            "The pattern repeats forever: ...E F G A B C D E F G A...",
        ],
    },
    {
        "id": "note_name_L2_after_g",
        "module_id": "note_name_recognition_module",
        "display_name": "What Comes After G?",
        "description": "Practice the wrap-around: G goes back to A",
        "exercise_template_id": "note_name_quiz",
        "sequence_order": 2,
        "is_required": True,
        "config": {
            "question_type": "next_note",
            "focus_on": ["G", "F", "E"],
        },
        "mastery": {
            "correct_streak": 6,
        },
        "feedback": {
            "correct": ["Yes!", "That's right!", "You've got the pattern!"],
            "incorrect": ["Remember: after G comes A again"],
        },
        "hints": [
            "The alphabet wraps around",
            "After G, start over at A",
        ],
    },
    {
        "id": "note_name_L3_before_a",
        "module_id": "note_name_recognition_module",
        "display_name": "What Comes Before A?",
        "description": "Practice going backwards: A is preceded by G",
        "exercise_template_id": "note_name_quiz",
        "sequence_order": 3,
        "is_required": True,
        "config": {
            "question_type": "previous_note",
            "focus_on": ["A", "B", "C"],
        },
        "mastery": {
            "correct_streak": 6,
        },
        "feedback": {
            "correct": ["Yes!", "That's right!", "You've got it!"],
            "incorrect": ["Remember: before A comes G"],
        },
        "hints": [
            "Going backwards: A is preceded by G",
            "The cycle works both directions",
        ],
    },
    
    # ========== Octave Equivalence Module ==========
    {
        "id": "octave_L1_same_name",
        "module_id": "octave_equivalence_module",
        "display_name": "Same Note, Different Height",
        "description": "Learn that an octave is the same note played higher or lower",
        "exercise_template_id": "octave_concept",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "show_visual": True,
            "key_concept": "An octave is the same note, just higher or lower",
            "example_notes": ["C3", "C4", "C5"],
        },
        "mastery": {
            "correct_streak": 3,
        },
        "feedback": {
            "correct": ["Yes! Same name, different octave!", "That's right!"],
            "incorrect": ["Listen for how similar they sound - same note, different height"],
        },
        "hints": [
            "An octave sounds like the same note",
            "C and a higher C are both 'C'",
            "Your ear can hear they're related",
        ],
    },
    {
        "id": "octave_L2_hear_sameness",
        "module_id": "octave_equivalence_module",
        "display_name": "Hear the Sameness",
        "description": "Match notes by ear across different octaves",
        "exercise_template_id": "octave_matching",
        "sequence_order": 2,
        "is_required": True,
        "config": {
            "play_pairs": True,
            "interval": "P8",
            "use_first_note": True,
        },
        "mastery": {
            "correct_streak": 6,
        },
        "feedback": {
            "correct": ["Yes! You heard the octave!", "They're the same note!"],
            "incorrect": ["Listen again - do they sound like the same note?"],
        },
        "hints": [
            "Octaves sound 'the same but different'",
            "One is just higher/lower than the other",
            "They blend together perfectly",
        ],
    },
    {
        "id": "octave_L3_low_high",
        "module_id": "octave_equivalence_module",
        "display_name": "Low C, High C",
        "description": "Play and hear octaves on your instrument",
        "exercise_template_id": "octave_play",
        "sequence_order": 3,
        "is_required": True,
        "config": {
            "use_first_note": True,
            "octave_direction": "both",
        },
        "mastery": {
            "correct_streak": 4,
        },
        "feedback": {
            "correct": ["Perfect octave!", "Same note, different register!"],
            "incorrect": ["Try to match the pitch exactly - same note, different octave"],
        },
        "hints": [
            "Your first note has an octave above and below",
            "Listen for how the notes blend",
            "They should sound like 'the same pitch' at different heights",
        ],
    },
    
    # ========== Half Steps Theory Module ==========
    {
        "id": "half_steps_L1_theory",
        "module_id": "half_steps_theory_module",
        "display_name": "The Half Step",
        "description": "Learn that a half step is the smallest interval - adjacent piano keys",
        "exercise_template_id": "half_steps_theory",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "show_visual": True,
            "show_keyboard": True,
            "key_concept": "A half step is the distance between any two adjacent keys on the piano",
            "natural_half_steps": ["E-F", "B-C"],
        },
        "mastery": {
            "correct_streak": 4,  # Must get all 4 quiz questions right
        },
        "feedback": {
            "correct": ["That's right!", "You understand half steps!", "Perfect!"],
            "incorrect": ["Remember: adjacent keys (including black keys) make a half step"],
        },
        "hints": [
            "A half step = smallest interval in Western music",
            "E-F and B-C are natural half steps (white to white)",
            "All other adjacent notes use a black key",
            "12 half steps make one octave",
        ],
    },
    
    # ========== Accidental: Flat Module ==========
    {
        "id": "accidental_flat_L1_theory",
        "module_id": "accidental_flat_module",
        "display_name": "The Flat Sign",
        "description": "Learn the flat (♭) lowers a note by one half step",
        "exercise_template_id": "accidental_flat",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "show_visual": True,
            "show_keyboard": True,
            "key_concept": "A flat (♭) lowers a note by one half step",
        },
        "mastery": {
            "correct_streak": 4,
        },
        "feedback": {
            "correct": ["That's right!", "You understand flats!", "Perfect!"],
            "incorrect": ["Remember: flat = lower by one half step"],
        },
        "hints": [
            "♭ = flat = lower by half step",
            "B♭ is one half step below B",
            "Most flats are black keys",
        ],
    },
    
    # ========== Accidental: Sharp Module ==========
    {
        "id": "accidental_sharp_L1_theory",
        "module_id": "accidental_sharp_module",
        "display_name": "The Sharp Sign",
        "description": "Learn the sharp (♯) raises a note by one half step",
        "exercise_template_id": "accidental_sharp",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "show_visual": True,
            "show_keyboard": True,
            "key_concept": "A sharp (♯) raises a note by one half step",
        },
        "mastery": {
            "correct_streak": 4,
        },
        "feedback": {
            "correct": ["That's right!", "You understand sharps!", "Perfect!"],
            "incorrect": ["Remember: sharp = raise by one half step"],
        },
        "hints": [
            "♯ = sharp = raise by half step",
            "F♯ is one half step above F",
            "Most sharps are black keys",
        ],
    },
    
    # ========== Accidental: Natural Module ==========
    {
        "id": "accidental_natural_L1_theory",
        "module_id": "accidental_natural_module",
        "display_name": "The Natural Sign",
        "description": "Learn the natural (♮) cancels sharps and flats",
        "exercise_template_id": "accidental_natural",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "show_visual": True,
            "key_concept": "A natural (♮) cancels a sharp or flat",
        },
        "mastery": {
            "correct_streak": 4,
        },
        "feedback": {
            "correct": ["That's right!", "You understand naturals!", "Perfect!"],
            "incorrect": ["Remember: natural = cancel sharp or flat"],
        },
        "hints": [
            "♮ = natural = cancel accidental",
            "Returns note to white key",
            "Like an 'undo' for sharps/flats",
        ],
    },
    
    # ========== Whole Steps Theory Module ==========
    {
        "id": "whole_steps_theory_L1_theory",
        "module_id": "whole_steps_theory_module",
        "display_name": "Understanding Whole Steps",
        "description": "Learn that a whole step = 2 half steps (skip one key)",
        "exercise_template_id": "whole_steps_theory",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "show_visual": True,
            "key_concept": "A whole step = 2 half steps = skip one key",
        },
        "mastery": {
            "correct_streak": 4,
        },
        "feedback": {
            "correct": ["Correct!", "You got it!", "Great work!"],
            "incorrect": ["Remember: whole step = skip one key"],
        },
        "hints": [
            "W = 2H = skip one key",
            "C to D is a whole step (skips C♯)",
            "Like taking two small steps at once",
        ],
    },
    
    # ========== Diatonic Scale Pattern Module ==========
    {
        "id": "diatonic_scale_pattern_L1_theory",
        "module_id": "diatonic_scale_pattern_module",
        "display_name": "The Major Scale Pattern",
        "description": "Learn the WWHWWWH pattern that creates major scales",
        "exercise_template_id": "diatonic_scale_pattern",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "show_visual": True,
            "key_concept": "Major scale = WWHWWWH",
        },
        "mastery": {
            "correct_streak": 4,
        },
        "feedback": {
            "correct": ["That's right!", "You understand the pattern!", "Perfect!"],
            "incorrect": ["Remember: WWHWWWH"],
        },
        "hints": [
            "WWHWWWH = the major scale formula",
            "W = whole step, H = half step",
            "The half steps occur between 3-4 and 7-8",
        ],
    },
    
    # ========== Key Signature Basics Module ==========
    {
        "id": "key_signature_basics_L1_theory",
        "module_id": "key_signature_basics_module",
        "display_name": "Understanding Key Signatures",
        "description": "Learn what key signatures are and how to read them",
        "exercise_template_id": "key_signature_basics",
        "sequence_order": 1,
        "is_required": True,
        "config": {
            "show_visual": True,
            "key_concept": "Key signature = sharps/flats that apply throughout",
        },
        "mastery": {
            "correct_streak": 4,
        },
        "feedback": {
            "correct": ["Correct!", "You understand key signatures!", "Great!"],
            "incorrect": ["Remember: key sig applies to ALL notes of that letter"],
        },
        "hints": [
            "Key signatures appear at the start of each staff line",
            "They tell you which notes are always sharp or flat",
            "No sharps/flats = C major or A minor",
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
