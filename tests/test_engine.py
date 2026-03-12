"""
Tests for engine module - EMA, mastery, and config.

Tests core engine calculations used in the practice engine.
"""

import pytest
from dataclasses import asdict

from app.engine.config import EngineConfig, DEFAULT_CONFIG
from app.engine.ema import compute_ema, check_material_mastery, check_capability_mastery


# =============================================================================
# ENGINE CONFIG
# =============================================================================

class TestEngineConfig:
    """Test EngineConfig dataclass."""
    
    def test_default_config_exists(self):
        """DEFAULT_CONFIG should be available."""
        assert DEFAULT_CONFIG is not None
        assert isinstance(DEFAULT_CONFIG, EngineConfig)
    
    def test_default_ema_alpha(self):
        """Default EMA alpha should be 0.3."""
        assert DEFAULT_CONFIG.ema_alpha == 0.3
    
    def test_default_mastery_threshold(self):
        """Default mastery threshold should be 4.0."""
        assert DEFAULT_CONFIG.mastery_threshold == 4.0
    
    def test_default_min_attempts_for_mastery(self):
        """Default min attempts should be 5."""
        assert DEFAULT_CONFIG.min_attempts_for_mastery == 5
    
    def test_config_is_dataclass(self):
        """Config should be convertible to dict."""
        config_dict = asdict(DEFAULT_CONFIG)
        assert isinstance(config_dict, dict)
        assert "ema_alpha" in config_dict
    
    def test_custom_config(self):
        """Should be able to create custom config."""
        config = EngineConfig(
            ema_alpha=0.5,
            mastery_threshold=3.5,
            min_attempts_for_mastery=3
        )
        assert config.ema_alpha == 0.5
        assert config.mastery_threshold == 3.5
        assert config.min_attempts_for_mastery == 3
    
    def test_bucket_weights_sum_to_reasonable_minimum(self):
        """Bucket minimum weights should sum to less than 1."""
        total = (
            DEFAULT_CONFIG.min_bucket_new +
            DEFAULT_CONFIG.min_bucket_in_progress +
            DEFAULT_CONFIG.min_bucket_maintenance
        )
        assert total < 1.0
    
    def test_maturity_weights_sum_to_one(self):
        """Maturity weights should sum to ~1.0."""
        total = DEFAULT_CONFIG.maturity_cap_weight + DEFAULT_CONFIG.maturity_mat_weight
        assert total == pytest.approx(1.0)


# =============================================================================
# COMPUTE EMA
# =============================================================================

class TestComputeEma:
    """Test compute_ema function."""
    
    def test_ema_with_zero_previous(self):
        """EMA from zero should be alpha * current."""
        result = compute_ema(4.0, 0.0, alpha=0.3)
        assert result == pytest.approx(1.2)  # 0.3 * 4.0 + 0.7 * 0.0
    
    def test_ema_same_value(self):
        """EMA with same current and previous should stay same."""
        result = compute_ema(3.0, 3.0, alpha=0.3)
        assert result == pytest.approx(3.0)
    
    def test_ema_increases_with_high_score(self):
        """EMA should increase when current > previous."""
        result = compute_ema(5.0, 3.0, alpha=0.3)
        assert result > 3.0
        assert result == pytest.approx(3.6)  # 0.3 * 5.0 + 0.7 * 3.0
    
    def test_ema_decreases_with_low_score(self):
        """EMA should decrease when current < previous."""
        result = compute_ema(1.0, 3.0, alpha=0.3)
        assert result < 3.0
        assert result == pytest.approx(2.4)  # 0.3 * 1.0 + 0.7 * 3.0
    
    def test_ema_with_alpha_one(self):
        """Alpha of 1.0 should give current value."""
        result = compute_ema(5.0, 2.0, alpha=1.0)
        assert result == 5.0
    
    def test_ema_with_alpha_zero(self):
        """Alpha of 0.0 should give previous value."""
        result = compute_ema(5.0, 2.0, alpha=0.0)
        assert result == 2.0
    
    def test_ema_uses_default_config(self):
        """Should use DEFAULT_CONFIG alpha when not specified."""
        result = compute_ema(4.0, 2.0)
        expected = 0.3 * 4.0 + 0.7 * 2.0  # Using default alpha 0.3
        assert result == pytest.approx(expected)
    
    def test_ema_with_custom_config(self):
        """Should use custom config's alpha."""
        config = EngineConfig(ema_alpha=0.5)
        result = compute_ema(4.0, 2.0, config=config)
        expected = 0.5 * 4.0 + 0.5 * 2.0
        assert result == pytest.approx(expected)
    
    def test_ema_bounds(self):
        """EMA should stay within reasonable bounds."""
        # Extreme high
        result = compute_ema(5.0, 5.0)
        assert result == 5.0
        
        # Extreme low
        result = compute_ema(0.0, 0.0)
        assert result == 0.0
    
    def test_ema_convergence(self):
        """Repeated EMA calculations should converge to current."""
        ema = 0.0
        for _ in range(50):
            ema = compute_ema(4.0, ema, alpha=0.3)
        assert ema == pytest.approx(4.0, rel=0.01)


# =============================================================================
# CHECK MATERIAL MASTERY
# =============================================================================

class TestCheckMaterialMastery:
    """Test check_material_mastery function."""
    
    def test_not_mastered_insufficient_attempts(self):
        """Not mastered if attempt count too low."""
        result = check_material_mastery(5.0, attempt_count=3)
        assert result is False  # Default min is 5 attempts
    
    def test_not_mastered_low_ema(self):
        """Not mastered if EMA below threshold."""
        result = check_material_mastery(3.0, attempt_count=10)
        assert result is False  # Default threshold is 4.0
    
    def test_mastered_when_both_met(self):
        """Mastered when both criteria met."""
        result = check_material_mastery(4.5, attempt_count=10)
        assert result is True
    
    def test_mastered_at_exact_threshold(self):
        """Mastered at exactly threshold values."""
        result = check_material_mastery(4.0, attempt_count=5)
        assert result is True
    
    def test_not_mastered_at_boundary(self):
        """Not mastered just below threshold."""
        result = check_material_mastery(3.99, attempt_count=5)
        assert result is False
    
    def test_uses_custom_config(self):
        """Should use custom config thresholds."""
        config = EngineConfig(
            mastery_threshold=3.0,
            min_attempts_for_mastery=2
        )
        result = check_material_mastery(3.5, attempt_count=2, config=config)
        assert result is True


# =============================================================================
# CHECK CAPABILITY MASTERY
# =============================================================================

class TestCheckCapabilityMastery:
    """Test check_capability_mastery function."""
    
    def test_simple_count_met(self):
        """Mastered when evidence count meets required."""
        result = check_capability_mastery(evidence_count=5, required_count=5)
        assert result is True
    
    def test_simple_count_exceeded(self):
        """Mastered when evidence exceeds required."""
        result = check_capability_mastery(evidence_count=10, required_count=5)
        assert result is True
    
    def test_simple_count_not_met(self):
        """Not mastered when evidence below required."""
        result = check_capability_mastery(evidence_count=3, required_count=5)
        assert result is False
    
    def test_distinct_materials_met(self):
        """Mastered when distinct materials requirement met."""
        result = check_capability_mastery(
            evidence_count=10,
            required_count=3,
            distinct_materials_required=True,
            distinct_material_count=3
        )
        assert result is True
    
    def test_distinct_materials_not_met(self):
        """Not mastered when distinct materials below required."""
        result = check_capability_mastery(
            evidence_count=10,
            required_count=5,
            distinct_materials_required=True,
            distinct_material_count=3
        )
        assert result is False
    
    def test_evidence_count_ignored_for_distinct_mode(self):
        """Evidence count should be ignored in distinct mode."""
        result = check_capability_mastery(
            evidence_count=100,  # High evidence
            required_count=5,
            distinct_materials_required=True,
            distinct_material_count=2  # But low distinct
        )
        assert result is False
    
    def test_zero_required_always_mastered(self):
        """Zero required should always be mastered."""
        result = check_capability_mastery(evidence_count=0, required_count=0)
        assert result is True


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestEmaAndMasteryIntegration:
    """Test EMA and mastery work together correctly."""
    
    def test_progression_to_mastery(self):
        """Simulate progression to mastery over attempts."""
        ema = 0.0
        attempts = 0
        scores = [4, 5, 4, 5, 5, 4, 5, 5]  # Good practice scores
        
        for score in scores:
            ema = compute_ema(float(score), ema, alpha=0.3)
            attempts += 1
            if check_material_mastery(ema, attempts):
                break
        
        # Should reach mastery with these scores
        assert check_material_mastery(ema, attempts) is True
        assert attempts <= len(scores)
    
    def test_struggling_student_no_mastery(self):
        """Struggling student shouldn't reach mastery quickly."""
        ema = 0.0
        attempts = 0
        scores = [2, 2, 3, 2, 3]  # Poor practice scores
        
        for score in scores:
            ema = compute_ema(float(score), ema, alpha=0.3)
            attempts += 1
        
        # Should not reach mastery
        assert check_material_mastery(ema, attempts) is False
    
    def test_config_consistency(self):
        """Same config should give same results."""
        config = EngineConfig(ema_alpha=0.4, mastery_threshold=3.5)
        
        ema1 = compute_ema(4.0, 2.0, config=config)
        ema2 = compute_ema(4.0, 2.0, config=config)
        
        assert ema1 == ema2
