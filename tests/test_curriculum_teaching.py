"""Tests for app/curriculum/teaching.py - Capability teaching functions."""

import pytest

from app.curriculum.teaching import (
    should_introduce_capability,
    get_next_capability_to_introduce,
    generate_capability_lesson_steps,
    get_capabilities_for_material,
    get_help_menu_capabilities,
)


# =============================================================================
# should_introduce_capability Tests
# =============================================================================


class TestShouldIntroduceCapability:
    """Tests for should_introduce_capability function."""

    def test_early_phase_introduce_often(self):
        """Under 10 known caps: introduce every 2 sessions."""
        # User knows 5 caps, it's been 2 sessions - should introduce
        assert should_introduce_capability(5, 2) is True
        # Only 1 session - too soon
        assert should_introduce_capability(5, 1) is False

    def test_building_phase_moderate_pace(self):
        """10-20 known caps: introduce every 4 sessions."""
        # User knows 15 caps, it's been 4 sessions - should introduce
        assert should_introduce_capability(15, 4) is True
        # Only 3 sessions - too soon
        assert should_introduce_capability(15, 3) is False

    def test_reinforcement_phase_slow_pace(self):
        """20+ known caps: introduce every 6 sessions."""
        # User knows 25 caps, it's been 6 sessions - should introduce
        assert should_introduce_capability(25, 6) is True
        # Only 5 sessions - too soon
        assert should_introduce_capability(25, 5) is False

    def test_struggling_user_slower_pace_early(self):
        """Low quiz pass rate slows down intros."""
        # Normal: 2 sessions needed at 5 known
        assert should_introduce_capability(5, 2, user_quiz_pass_rate=0.8) is True
        # Struggling: 2+2=4 sessions needed
        assert should_introduce_capability(5, 2, user_quiz_pass_rate=0.5) is False
        assert should_introduce_capability(5, 4, user_quiz_pass_rate=0.5) is True

    def test_struggling_user_slower_pace_mid(self):
        """Low quiz pass rate in building phase."""
        # Normal: 4 sessions, struggling: 6 sessions
        assert should_introduce_capability(15, 4, user_quiz_pass_rate=0.8) is True
        assert should_introduce_capability(15, 4, user_quiz_pass_rate=0.5) is False
        assert should_introduce_capability(15, 6, user_quiz_pass_rate=0.5) is True

    def test_edge_case_zero_known(self):
        """User knows nothing."""
        assert should_introduce_capability(0, 2) is True
        assert should_introduce_capability(0, 1) is False

    def test_edge_case_exactly_10_known(self):
        """Boundary at 10 known caps."""
        # At exactly 10, should be in building phase (4 sessions)
        assert should_introduce_capability(10, 4) is True
        assert should_introduce_capability(10, 3) is False

    def test_edge_case_exactly_20_known(self):
        """Boundary at 20 known caps."""
        # At exactly 20, should be in reinforcement phase (6 sessions)
        assert should_introduce_capability(20, 6) is True
        assert should_introduce_capability(20, 5) is False


# =============================================================================
# get_next_capability_to_introduce Tests
# =============================================================================


class TestGetNextCapabilityToIntroduce:
    """Tests for get_next_capability_to_introduce function."""

    def test_returns_first_unknown_with_explanation(self):
        """Returns first unknown capability that has teaching content."""
        all_caps = [
            {"name": "treble_clef", "sequence_order": 1, "explanation": "The treble clef..."},
            {"name": "bass_clef", "sequence_order": 2, "explanation": "The bass clef..."},
            {"name": "quarter_note", "sequence_order": 3, "explanation": "A quarter note..."},
        ]
        user_known = ["treble_clef"]
        
        result = get_next_capability_to_introduce(user_known, all_caps)
        
        assert result is not None
        assert result["name"] == "bass_clef"

    def test_skips_caps_without_explanation(self):
        """Skip capabilities that don't have teaching content."""
        all_caps = [
            {"name": "advanced_cap", "sequence_order": 1},  # No explanation
            {"name": "basic_cap", "sequence_order": 2, "explanation": "Explanation here"},
        ]
        user_known = []
        
        result = get_next_capability_to_introduce(user_known, all_caps)
        
        assert result is not None
        assert result["name"] == "basic_cap"

    def test_returns_none_when_all_known(self):
        """Returns None when user knows all capabilities."""
        all_caps = [
            {"name": "cap1", "sequence_order": 1, "explanation": "..."},
            {"name": "cap2", "sequence_order": 2, "explanation": "..."},
        ]
        user_known = ["cap1", "cap2"]
        
        result = get_next_capability_to_introduce(user_known, all_caps)
        
        assert result is None

    def test_returns_none_when_remaining_have_no_explanation(self):
        """Returns None when remaining caps lack teaching content."""
        all_caps = [
            {"name": "cap1", "sequence_order": 1, "explanation": "..."},
            {"name": "cap2", "sequence_order": 2},  # No explanation
        ]
        user_known = ["cap1"]
        
        result = get_next_capability_to_introduce(user_known, all_caps)
        
        assert result is None

    def test_respects_sequence_order(self):
        """Should return caps in sequence_order, not list order."""
        all_caps = [
            {"name": "later", "sequence_order": 10, "explanation": "..."},
            {"name": "first", "sequence_order": 1, "explanation": "..."},
            {"name": "middle", "sequence_order": 5, "explanation": "..."},
        ]
        user_known = []
        
        result = get_next_capability_to_introduce(user_known, all_caps)
        
        assert result["name"] == "first"

    def test_handles_missing_sequence_order(self):
        """Handles caps without sequence_order (defaults to 999)."""
        all_caps = [
            {"name": "ordered", "sequence_order": 1, "explanation": "..."},
            {"name": "unordered", "explanation": "..."},  # No sequence_order
        ]
        user_known = []
        
        result = get_next_capability_to_introduce(user_known, all_caps)
        
        assert result["name"] == "ordered"

    def test_empty_all_caps(self):
        """Returns None for empty capability list."""
        result = get_next_capability_to_introduce([], [])
        assert result is None


# =============================================================================
# generate_capability_lesson_steps Tests
# =============================================================================


class TestGenerateCapabilityLessonSteps:
    """Tests for generate_capability_lesson_steps function."""

    def test_minimal_lesson_explain_and_try(self):
        """Minimal lesson has EXPLAIN and TRY_IT steps."""
        capability = {
            "name": "quarter_note",
            "display_name": "Quarter Note",
            "explanation": "A quarter note is one beat.",
        }
        
        steps = generate_capability_lesson_steps(capability)
        
        assert len(steps) == 2
        assert steps[0]["step_type"] == "EXPLAIN"
        assert steps[1]["step_type"] == "TRY_IT"

    def test_full_lesson_all_steps(self):
        """Full lesson with audio, visual, and quiz."""
        capability = {
            "name": "fermata",
            "display_name": "Fermata",
            "explanation": "A fermata indicates a pause.",
            "audio_example_url": "/audio/fermata.mp3",
            "visual_example_url": "/images/fermata.png",
            "quiz_question": "Which symbol means to hold?",
            "quiz_type": "visual_mc",
            "quiz_options": ["A", "B", "C"],
            "quiz_answer": "B",
        }
        
        steps = generate_capability_lesson_steps(capability)
        
        assert len(steps) == 5
        types = [s["step_type"] for s in steps]
        assert types == ["LISTEN", "EXPLAIN", "VISUAL", "TRY_IT", "QUIZ"]

    def test_listen_step_has_audio_url(self):
        """LISTEN step includes audio_url."""
        capability = {
            "name": "staccato",
            "audio_example_url": "/audio/staccato.mp3",
        }
        
        steps = generate_capability_lesson_steps(capability)
        listen_step = next(s for s in steps if s["step_type"] == "LISTEN")
        
        assert listen_step["audio_url"] == "/audio/staccato.mp3"

    def test_visual_step_has_visual_url(self):
        """VISUAL step includes visual_url."""
        capability = {
            "name": "accent",
            "visual_example_url": "/images/accent.png",
        }
        
        steps = generate_capability_lesson_steps(capability)
        visual_step = next(s for s in steps if s["step_type"] == "VISUAL")
        
        assert visual_step["visual_url"] == "/images/accent.png"

    def test_quiz_step_has_quiz_data(self):
        """QUIZ step includes quiz fields."""
        capability = {
            "name": "rest",
            "quiz_question": "What is this symbol?",
            "quiz_type": "audio_mc",
            "quiz_options": ["Rest", "Note", "Clef"],
            "quiz_answer": "Rest",
        }
        
        steps = generate_capability_lesson_steps(capability)
        quiz_step = next(s for s in steps if s["step_type"] == "QUIZ")
        
        assert quiz_step["instruction"] == "What is this symbol?"
        assert quiz_step["quiz_type"] == "audio_mc"
        assert quiz_step["quiz_options"] == ["Rest", "Note", "Clef"]
        assert quiz_step["quiz_answer"] == "Rest"

    def test_step_indices_are_sequential(self):
        """Step indices are 0-indexed and sequential."""
        capability = {
            "name": "tie",
            "audio_example_url": "/audio/tie.mp3",
            "visual_example_url": "/images/tie.png",
            "quiz_question": "What does this mean?",
        }
        
        steps = generate_capability_lesson_steps(capability)
        indices = [s["step_index"] for s in steps]
        
        assert indices == list(range(len(steps)))

    def test_all_steps_start_not_completed(self):
        """All steps start with is_completed=False."""
        capability = {
            "name": "natural",
            "audio_example_url": "/audio/natural.mp3",
            "quiz_question": "Identify the natural.",
        }
        
        steps = generate_capability_lesson_steps(capability)
        
        for step in steps:
            assert step["is_completed"] is False

    def test_explain_uses_capability_explanation(self):
        """EXPLAIN step uses capability's explanation text."""
        capability = {
            "name": "sharp",
            "explanation": "A sharp raises the pitch by a half step.",
        }
        
        steps = generate_capability_lesson_steps(capability)
        explain_step = next(s for s in steps if s["step_type"] == "EXPLAIN")
        
        assert explain_step["prompt"] == "A sharp raises the pitch by a half step."

    def test_uses_name_if_no_display_name(self):
        """Falls back to name if display_name not provided."""
        capability = {
            "name": "flat_note",
        }
        
        steps = generate_capability_lesson_steps(capability)
        explain_step = next(s for s in steps if s["step_type"] == "EXPLAIN")
        
        assert "flat_note" in explain_step["instruction"]


# =============================================================================
# get_capabilities_for_material Tests
# =============================================================================


class TestGetCapabilitiesForMaterial:
    """Tests for get_capabilities_for_material function."""

    def test_returns_unknown_scaffolding_caps(self):
        """Returns scaffolding caps that user doesn't know."""
        scaffolding = "treble_clef,bass_clef,quarter_note"
        user_known = ["treble_clef"]
        
        result = get_capabilities_for_material(scaffolding, user_known)
        
        assert set(result) == {"bass_clef", "quarter_note"}

    def test_returns_empty_when_all_known(self):
        """Returns empty list when user knows all scaffolding caps."""
        scaffolding = "cap1,cap2"
        user_known = ["cap1", "cap2", "cap3"]
        
        result = get_capabilities_for_material(scaffolding, user_known)
        
        assert result == []

    def test_returns_empty_for_empty_scaffolding(self):
        """Returns empty list when no scaffolding caps."""
        result = get_capabilities_for_material("", ["cap1"])
        assert result == []

    def test_returns_empty_for_none_scaffolding(self):
        """Handles None scaffolding string."""
        result = get_capabilities_for_material(None, ["cap1"])
        assert result == []

    def test_handles_whitespace_in_caps_string(self):
        """Handles whitespace around capability names."""
        scaffolding = "cap1 , cap2,  cap3  "
        user_known = []
        
        result = get_capabilities_for_material(scaffolding, user_known)
        
        assert set(result) == {"cap1", "cap2", "cap3"}

    def test_handles_empty_entries(self):
        """Handles empty entries from trailing commas."""
        scaffolding = "cap1,,cap2,"
        user_known = []
        
        result = get_capabilities_for_material(scaffolding, user_known)
        
        assert set(result) == {"cap1", "cap2"}


# =============================================================================
# get_help_menu_capabilities Tests
# =============================================================================


class TestGetHelpMenuCapabilities:
    """Tests for get_help_menu_capabilities function."""

    def test_combines_required_and_scaffolding(self):
        """Returns all capabilities from both required and scaffolding."""
        required = "req1,req2"
        scaffolding = "scaff1,scaff2"
        
        result = get_help_menu_capabilities(required, scaffolding)
        
        assert set(result) == {"req1", "req2", "scaff1", "scaff2"}

    def test_deduplicates_caps(self):
        """Removes duplicates that appear in both lists."""
        required = "cap1,cap2"
        scaffolding = "cap2,cap3"
        
        result = get_help_menu_capabilities(required, scaffolding)
        
        assert len([c for c in result if c == "cap2"]) == 1
        assert set(result) == {"cap1", "cap2", "cap3"}

    def test_handles_empty_required(self):
        """Works when required is empty."""
        result = get_help_menu_capabilities("", "scaff1,scaff2")
        assert set(result) == {"scaff1", "scaff2"}

    def test_handles_empty_scaffolding(self):
        """Works when scaffolding is empty."""
        result = get_help_menu_capabilities("req1,req2", "")
        assert set(result) == {"req1", "req2"}

    def test_handles_both_empty(self):
        """Returns empty list when both are empty."""
        result = get_help_menu_capabilities("", "")
        assert result == []

    def test_handles_none_values(self):
        """Handles None for required or scaffolding."""
        result = get_help_menu_capabilities(None, "scaff1")
        assert result == ["scaff1"]
        
        result = get_help_menu_capabilities("req1", None)
        assert result == ["req1"]

    def test_handles_whitespace(self):
        """Handles whitespace in capability strings."""
        result = get_help_menu_capabilities("  req1 , req2  ", " scaff1 ")
        assert set(result) == {"req1", "req2", "scaff1"}
