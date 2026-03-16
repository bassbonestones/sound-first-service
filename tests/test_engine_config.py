"""
Tests for engine/config.py

Tests for EngineConfig dataclass and defaults.
"""

import pytest

from app.engine.config import EngineConfig, DEFAULT_CONFIG


class TestEngineConfig:
    """Tests for EngineConfig dataclass."""

    def test_default_ema_alpha(self):
        """Default EMA alpha should be 0.3."""
        config = EngineConfig()
        assert config.ema_alpha == 0.3

    def test_default_mastery_threshold(self):
        """Default mastery threshold should be 4.0."""
        config = EngineConfig()
        assert config.mastery_threshold == 4.0

    def test_default_min_attempts_for_mastery(self):
        """Default min attempts for mastery should be 5."""
        config = EngineConfig()
        assert config.min_attempts_for_mastery == 5

    def test_custom_config_values(self):
        """Should create config with custom values."""
        config = EngineConfig(
            ema_alpha=0.5,
            mastery_threshold=3.5,
            min_attempts_for_mastery=3
        )
        assert config.ema_alpha == 0.5
        assert config.mastery_threshold == 3.5
        assert config.min_attempts_for_mastery == 3

    def test_bucket_minimum_weights(self):
        """Should have minimum weights for all buckets."""
        config = EngineConfig()
        assert config.min_bucket_new == 0.10
        assert config.min_bucket_in_progress == 0.20
        assert config.min_bucket_maintenance == 0.05

    def test_maturity_weights(self):
        """Maturity weights should sum to 1.0."""
        config = EngineConfig()
        total = config.maturity_cap_weight + config.maturity_mat_weight
        assert total == pytest.approx(1.0)

    def test_unified_scoring_defaults(self):
        """Should have unified scoring parameters."""
        config = EngineConfig()
        assert config.use_unified_score_eligibility is True
        assert config.max_primary_score_delta == 0.3
        assert config.max_hazard_score == 0.7

    def test_focus_targeting_defaults(self):
        """Should have focus targeting parameters."""
        config = EngineConfig()
        assert config.focus_targets_per_material == 3
        assert config.avoid_extremes_factor == 0.5


class TestDefaultConfig:
    """Tests for DEFAULT_CONFIG singleton."""

    def test_default_config_exists(self):
        """DEFAULT_CONFIG should be an EngineConfig instance."""
        assert isinstance(DEFAULT_CONFIG, EngineConfig)

    def test_default_config_has_expected_values(self):
        """DEFAULT_CONFIG should have expected default values."""
        assert DEFAULT_CONFIG.ema_alpha == 0.3
        assert DEFAULT_CONFIG.mastery_threshold == 4.0

    def test_default_config_not_modified(self):
        """Creating new config should not affect DEFAULT_CONFIG."""
        original_alpha = DEFAULT_CONFIG.ema_alpha
        _ = EngineConfig(ema_alpha=0.9)
        assert DEFAULT_CONFIG.ema_alpha == original_alpha
