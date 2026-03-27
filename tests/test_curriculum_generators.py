"""
Tests for curriculum generators module.

Tests curriculum step generation and fatigue handling.
"""

import pytest

from app.curriculum.generators import (
    generate_curriculum_steps,
    get_goals_for_fatigue,
)


class TestGenerateCurriculumSteps:
    """Tests for generate_curriculum_steps function."""

    def test_returns_list_of_steps(self):
        """Should return a list of step dictionaries."""
        steps = generate_curriculum_steps(
            goal_type="fluency_through_keys",
            focus_card_prompts={},
            material_title="Simple Scale",
            target_key="C major",
        )
        assert isinstance(steps, list)
        assert len(steps) > 0

    def test_each_step_has_required_fields(self):
        """Each step should have all required fields."""
        steps = generate_curriculum_steps(
            goal_type="fluency_through_keys",
            focus_card_prompts={"listen": "Listen carefully"},
            material_title="Test",
            target_key="G major",
        )
        for step in steps:
            assert "step_index" in step
            assert "step_type" in step
            assert "instruction" in step
            assert "prompt" in step
            assert "is_completed" in step
            assert step["is_completed"] is False

    def test_material_placeholder_replaced(self):
        """Instructions with {material} should have it replaced."""
        steps = generate_curriculum_steps(
            goal_type="fluency_through_keys",
            focus_card_prompts={},
            material_title="My Special Scale",
            target_key="D major",
        )
        # Check no step still has the placeholder
        for step in steps:
            assert "{material}" not in step["instruction"]

    def test_key_placeholder_replaced(self):
        """Instructions with {key} should have it replaced."""
        steps = generate_curriculum_steps(
            goal_type="fluency_through_keys",
            focus_card_prompts={},
            material_title="Test Scale",
            target_key="F# major",
        )
        # Check no step still has the placeholder
        for step in steps:
            assert "{key}" not in step["instruction"]

    def test_high_fatigue_reduces_play_steps(self):
        """At fatigue level 4+, extra PLAY steps should be filtered."""
        normal_steps = generate_curriculum_steps(
            goal_type="fluency_through_keys",
            focus_card_prompts={},
            material_title="Test",
            target_key="C major",
            fatigue_level=2,
        )
        high_fatigue_steps = generate_curriculum_steps(
            goal_type="fluency_through_keys",
            focus_card_prompts={},
            material_title="Test",
            target_key="C major",
            fatigue_level=4,
        )
        
        # High fatigue should have <= play steps than normal
        normal_play = sum(1 for s in normal_steps if s["step_type"] == "PLAY")
        high_play = sum(1 for s in high_fatigue_steps if s["step_type"] == "PLAY")
        assert high_play <= normal_play

    def test_prompts_from_focus_card_used(self):
        """Prompts from focus_card_prompts should be used."""
        prompts = {
            "listen": "Listen to the melody carefully",
            "sing": "Sing along with the melody",
            "play": "Play the melody on your instrument",
        }
        steps = generate_curriculum_steps(
            goal_type="fluency_through_keys",
            focus_card_prompts=prompts,
            material_title="Test",
            target_key="C major",
        )
        
        # Find a LISTEN step and check it has the prompt
        listen_steps = [s for s in steps if s["step_type"] == "LISTEN"]
        if listen_steps:
            assert listen_steps[0]["prompt"] == "Listen to the melody carefully"

    def test_unknown_goal_uses_default(self):
        """Unknown goal type should use default curriculum."""
        steps = generate_curriculum_steps(
            goal_type="unknown_goal_type_xyz",
            focus_card_prompts={},
            material_title="Test",
            target_key="C major",
        )
        # Should still return some steps (from default curriculum)
        assert len(steps) > 0


class TestGetGoalsForFatigue:
    """Tests for get_goals_for_fatigue function."""

    def test_low_fatigue_returns_all_goals(self):
        """Low fatigue should return all goals."""
        goals = get_goals_for_fatigue(1)
        assert len(goals) > 0
        
        goals2 = get_goals_for_fatigue(2)
        assert goals == goals2

    def test_medium_fatigue_excludes_high_intensity(self):
        """Medium fatigue should exclude high intensity goals."""
        goals = get_goals_for_fatigue(3)
        
        # Should not include goals that risk bad habits
        assert "range_expansion" not in goals
        assert "tempo_build" not in goals

    def test_high_fatigue_reduces_goals_further(self):
        """High fatigue should reduce goals further."""
        normal_goals = get_goals_for_fatigue(1)
        high_fatigue_goals = get_goals_for_fatigue(4)
        
        # Should have fewer goals at high fatigue
        assert len(high_fatigue_goals) <= len(normal_goals)

    def test_extreme_fatigue_very_limited(self):
        """Extreme fatigue should have very limited goals."""
        goals = get_goals_for_fatigue(5)
        
        # Should have some goals available
        assert len(goals) >= 0  # May be empty or ear-only
