"""
Tests for engine/ema.py

Tests for EMA and mastery calculation functions.
"""

import pytest

from app.engine.config import EngineConfig
from app.engine.ema import (
    compute_ema,
    check_material_mastery,
    check_capability_mastery,
)


class TestComputeEma:
    """Tests for compute_ema function."""

    def test_ema_with_default_alpha(self):
        """Should compute EMA with default alpha=0.3."""
        result = compute_ema(5.0, 3.0)  # Current=5, Previous=3
        # EMA = 0.3 * 5 + 0.7 * 3 = 1.5 + 2.1 = 3.6
        assert result == pytest.approx(3.6)

    def test_ema_with_custom_alpha(self):
        """Should compute EMA with custom alpha."""
        result = compute_ema(5.0, 3.0, alpha=0.5)
        # EMA = 0.5 * 5 + 0.5 * 3 = 2.5 + 1.5 = 4.0
        assert result == pytest.approx(4.0)

    def test_ema_with_config(self):
        """Should use alpha from config."""
        config = EngineConfig(ema_alpha=0.2)
        result = compute_ema(5.0, 3.0, config=config)
        # EMA = 0.2 * 5 + 0.8 * 3 = 1.0 + 2.4 = 3.4
        assert result == pytest.approx(3.4)

    def test_ema_explicit_alpha_overrides_config(self):
        """Explicit alpha should override config alpha."""
        config = EngineConfig(ema_alpha=0.2)
        result = compute_ema(5.0, 3.0, alpha=0.5, config=config)
        # Explicit alpha=0.5 used, not config's 0.2
        assert result == pytest.approx(4.0)

    def test_ema_zero_previous(self):
        """Should handle zero previous EMA."""
        result = compute_ema(4.0, 0.0)
        # EMA = 0.3 * 4 + 0.7 * 0 = 1.2
        assert result == pytest.approx(1.2)

    def test_ema_high_alpha_responds_fast(self):
        """Higher alpha should weight current score more."""
        ema_low = compute_ema(5.0, 1.0, alpha=0.1)  # Slow response
        ema_high = compute_ema(5.0, 1.0, alpha=0.9)  # Fast response
        
        assert ema_low < 2.0  # Still closer to previous
        assert ema_high > 4.0  # Near current


class TestCheckMaterialMastery:
    """Tests for check_material_mastery function."""

    def test_mastered_when_above_threshold_and_attempts(self):
        """Should return True when EMA >= 4.0 and attempts >= 5."""
        assert check_material_mastery(4.5, 6) is True

    def test_not_mastered_low_ema(self):
        """Should return False when EMA below threshold."""
        assert check_material_mastery(3.5, 10) is False

    def test_not_mastered_few_attempts(self):
        """Should return False when attempts below minimum."""
        assert check_material_mastery(5.0, 3) is False

    def test_boundary_exactly_at_threshold(self):
        """Should return True at exactly threshold values."""
        assert check_material_mastery(4.0, 5) is True

    def test_custom_config_thresholds(self):
        """Should respect custom config thresholds."""
        config = EngineConfig(mastery_threshold=3.0, min_attempts_for_mastery=3)
        assert check_material_mastery(3.0, 3, config=config) is True
        assert check_material_mastery(2.9, 3, config=config) is False


class TestCheckCapabilityMastery:
    """Tests for check_capability_mastery function."""

    def test_mastered_simple_count(self):
        """Should return True when evidence >= required."""
        assert check_capability_mastery(5, 3) is True

    def test_not_mastered_simple_count(self):
        """Should return False when evidence < required."""
        assert check_capability_mastery(2, 3) is False

    def test_exactly_at_required(self):
        """Should return True when evidence equals required."""
        assert check_capability_mastery(3, 3) is True

    def test_distinct_materials_required_met(self):
        """Should check distinct materials when required."""
        assert check_capability_mastery(
            evidence_count=10,
            required_count=3,
            distinct_materials_required=True,
            distinct_material_count=5
        ) is True

    def test_distinct_materials_required_not_met(self):
        """Should fail if distinct materials below required."""
        assert check_capability_mastery(
            evidence_count=10,
            required_count=3,
            distinct_materials_required=True,
            distinct_material_count=2
        ) is False
