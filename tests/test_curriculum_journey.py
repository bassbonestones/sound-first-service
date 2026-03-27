"""
Tests for curriculum journey module.

Tests journey stage adaptive weights and progression.
"""

import pytest

from app.curriculum.journey import get_stage_adaptive_weights


class TestGetStageAdaptiveWeights:
    """Tests for get_stage_adaptive_weights function."""

    def test_stage_1_arrival(self):
        """Stage 1 (Arrival) should have heavy reinforcement bias."""
        weights = get_stage_adaptive_weights(1)
        assert weights["reinforcement_bias"] == 0.9
        assert weights["novelty_bias"] == 0.1
        assert weights["max_keys_per_session"] == 2
        assert "learn_by_ear" in weights["preferred_goals"]
        assert "range_expansion" in weights["avoid_goals"]

    def test_stage_2_orientation(self):
        """Stage 2 (Orientation) should balance reinforcement and novelty."""
        weights = get_stage_adaptive_weights(2)
        assert weights["reinforcement_bias"] == 0.75
        assert weights["novelty_bias"] == 0.25
        assert weights["max_keys_per_session"] == 3
        assert "musical_phrase_flow" in weights["preferred_goals"]

    def test_stage_3_guided_growth(self):
        """Stage 3 (Guided Growth) should allow more novelty."""
        weights = get_stage_adaptive_weights(3)
        assert weights["reinforcement_bias"] == 0.6
        assert weights["novelty_bias"] == 0.4
        assert weights["max_keys_per_session"] == 4
        assert weights["preferred_goals"] is None
        assert weights["avoid_goals"] == []

    def test_stage_4_expanding_identity(self):
        """Stage 4 (Expanding Musical Identity) should be balanced."""
        weights = get_stage_adaptive_weights(4)
        assert weights["reinforcement_bias"] == 0.5
        assert weights["novelty_bias"] == 0.5
        assert weights["max_keys_per_session"] == 5
        assert weights["avoid_goals"] == []

    def test_stage_5_independent_fluency(self):
        """Stage 5 (Independent Fluency) should favor novelty."""
        weights = get_stage_adaptive_weights(5)
        assert weights["reinforcement_bias"] == 0.4
        assert weights["novelty_bias"] == 0.6
        assert weights["max_keys_per_session"] == 6

    def test_stage_6_lifelong_companion(self):
        """Stage 6 (Lifelong Companion) should have high novelty."""
        weights = get_stage_adaptive_weights(6)
        assert weights["reinforcement_bias"] == 0.3
        assert weights["novelty_bias"] == 0.7
        assert weights["max_keys_per_session"] == 8

    def test_invalid_stage_defaults_to_stage_1(self):
        """Invalid stage should default to stage 1."""
        weights = get_stage_adaptive_weights(99)
        assert weights["reinforcement_bias"] == 0.9
        assert weights["max_keys_per_session"] == 2

    def test_zero_stage_defaults_to_stage_1(self):
        """Stage 0 should default to stage 1."""
        weights = get_stage_adaptive_weights(0)
        assert weights["reinforcement_bias"] == 0.9

    def test_negative_stage_defaults_to_stage_1(self):
        """Negative stage should default to stage 1."""
        weights = get_stage_adaptive_weights(-1)
        assert weights["reinforcement_bias"] == 0.9

    def test_all_stages_have_required_keys(self):
        """All stages should have the required keys."""
        required_keys = [
            "reinforcement_bias",
            "novelty_bias", 
            "max_keys_per_session",
            "preferred_goals",
            "avoid_goals",
        ]
        
        for stage in range(1, 7):
            weights = get_stage_adaptive_weights(stage)
            for key in required_keys:
                assert key in weights, f"Stage {stage} missing key {key}"
