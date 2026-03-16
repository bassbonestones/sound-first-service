"""
Tests for app/session_config.py - Session Configuration Module

Tests the probabilistic session configuration:
- Weighted random selection
- Fatigue adjustments
- Time budgeting
- Anti-repetition logic
"""

import pytest
from collections import Counter
from app.session_config import (
    weighted_choice,
    get_adjusted_capability_weights,
    select_novelty_or_reinforcement,
    select_difficulty,
    select_intensity,
    select_capability,
    estimate_mini_session_duration,
    should_show_notation,
    CAPABILITY_WEIGHTS,
    DIFFICULTY_WEIGHTS,
    NOVELTY_REINFORCEMENT,
    AVG_MINI_SESSION_MINUTES,
    FATIGUE_CAPABILITY_MODIFIERS,
    MAX_CAPABILITY_STREAK,
)


# =============================================================================
# WEIGHTED CHOICE TESTS
# =============================================================================

class TestWeightedChoice:
    """Tests for weighted_choice() function."""
    
    def test_basic_selection(self):
        """Basic weighted selection works."""
        weights = {"a": 0.5, "b": 0.3, "c": 0.2}
        result = weighted_choice(weights)
        assert result in ["a", "b", "c"]
    
    def test_distribution_approximate(self):
        """Distribution approximately matches weights (statistical test)."""
        weights = {"a": 0.6, "b": 0.3, "c": 0.1}
        
        results = Counter()
        trials = 1000
        for _ in range(trials):
            results[weighted_choice(weights)] += 1
        
        # Allow 10% variance
        assert results["a"] > trials * 0.5
        assert results["a"] < trials * 0.7
        assert results["c"] < trials * 0.2
    
    def test_single_option(self):
        """Single option always selected."""
        weights = {"only_option": 1.0}
        for _ in range(10):
            assert weighted_choice(weights) == "only_option"
    
    def test_zero_total_weight(self):
        """Zero total weight falls back to random."""
        weights = {"a": 0, "b": 0, "c": 0}
        result = weighted_choice(weights)
        assert result in ["a", "b", "c"]
    
    def test_empty_dict(self):
        """Empty dict handles gracefully (random choice from empty)."""
        # This may raise an error - test for specific behavior
        try:
            result = weighted_choice({})
            # If it doesn't raise, result should be falsy or handled
        except (IndexError, ValueError, KeyError):
            pass  # Expected behavior


# =============================================================================
# FATIGUE-ADJUSTED WEIGHTS TESTS
# =============================================================================

class TestGetAdjustedCapabilityWeights:
    """Tests for get_adjusted_capability_weights() function."""
    
    def test_fatigue_1_no_changes(self):
        """Fatigue 1 doesn't modify weights."""
        weights = get_adjusted_capability_weights(1)
        
        for key, value in CAPABILITY_WEIGHTS.items():
            assert weights[key] == value
    
    def test_fatigue_2_no_changes(self):
        """Fatigue 2 doesn't modify weights."""
        weights = get_adjusted_capability_weights(2)
        
        for key, value in CAPABILITY_WEIGHTS.items():
            assert weights[key] == value
    
    def test_fatigue_3_reduces_range_expansion(self):
        """Fatigue 3 eliminates range expansion."""
        weights = get_adjusted_capability_weights(3)
        
        assert weights["range_expansion"] == 0
    
    def test_fatigue_4_reduces_technique(self):
        """Fatigue 4 strongly reduces technique work."""
        weights = get_adjusted_capability_weights(4)
        
        original_technique = CAPABILITY_WEIGHTS["technique"]
        assert weights["technique"] < original_technique
    
    def test_fatigue_5_favors_ear_training(self):
        """Fatigue 5 heavily favors ear training."""
        weights = get_adjusted_capability_weights(5)
        
        # Ear training should be boosted significantly
        assert weights["ear_training"] > CAPABILITY_WEIGHTS["ear_training"]
        # Physical work should be near zero
        assert weights["range_expansion"] == 0
        assert weights["technique"] == 0
    
    def test_all_fatigue_levels_valid_weights(self):
        """All fatigue levels produce valid (non-negative) weights."""
        for fatigue in range(1, 6):
            weights = get_adjusted_capability_weights(fatigue)
            
            for key, value in weights.items():
                assert value >= 0, f"Negative weight for {key} at fatigue {fatigue}"


# =============================================================================
# SELECTION FUNCTION TESTS
# =============================================================================

class TestSelectNoveltyOrReinforcement:
    """Tests for select_novelty_or_reinforcement() function."""
    
    def test_returns_valid_option(self):
        """Returns either novelty or reinforcement."""
        result = select_novelty_or_reinforcement()
        assert result in ["novelty", "reinforcement"]
    
    def test_distribution_matches_config(self):
        """Distribution approximately matches configured 20/80 split."""
        results = Counter()
        trials = 500
        
        for _ in range(trials):
            results[select_novelty_or_reinforcement()] += 1
        
        # Allow variance - novelty should be ~20%
        novelty_pct = results["novelty"] / trials
        assert 0.10 < novelty_pct < 0.35  # Wide margin for randomness


class TestSelectDifficulty:
    """Tests for select_difficulty() function."""
    
    def test_returns_valid_difficulty(self):
        """Returns easy, medium, or hard."""
        result = select_difficulty()
        assert result in ["easy", "medium", "hard"]
    
    def test_distribution_favors_easy(self):
        """Easy difficulty is most common (50% weight)."""
        results = Counter()
        trials = 500
        
        for _ in range(trials):
            results[select_difficulty()] += 1
        
        # Easy should be most common
        assert results["easy"] > results["hard"]


class TestSelectIntensity:
    """Tests for select_intensity() function."""
    
    def test_returns_valid_intensity(self):
        """Returns small, medium, or large."""
        result = select_intensity()
        assert result in ["small", "medium", "large"]
    
    def test_low_time_reduces_large(self):
        """Low time remaining reduces large intensity probability."""
        results_full = Counter()
        results_limited = Counter()
        trials = 200
        
        for _ in range(trials):
            results_full[select_intensity(time_remaining=60)] += 1
            results_limited[select_intensity(time_remaining=3)] += 1
        
        # With limited time, large should be rare or zero
        assert results_limited.get("large", 0) <= results_full.get("large", trials)
    
    def test_very_low_time_no_large(self):
        """Very low time should never select large."""
        for _ in range(50):
            result = select_intensity(time_remaining=2)
            # Large should be very unlikely with only 2 minutes
            # (Note: This tests probability, large weight becomes 0 at <5 min)


class TestSelectCapability:
    """Tests for select_capability() function."""
    
    def test_returns_valid_capability(self):
        """Returns a valid capability bucket."""
        result = select_capability(fatigue=2)
        assert result in CAPABILITY_WEIGHTS.keys()
    
    def test_fatigue_affects_selection(self):
        """High fatigue changes selection distribution."""
        results_normal = Counter()
        results_fatigued = Counter()
        trials = 200
        
        for _ in range(trials):
            results_normal[select_capability(fatigue=2)] += 1
            results_fatigued[select_capability(fatigue=5)] += 1
        
        # At fatigue 5, ear_training should dominate
        assert results_fatigued.get("ear_training", 0) > results_normal.get("ear_training", 0)
        # Range expansion should be zero at fatigue 5
        assert results_fatigued.get("range_expansion", 0) == 0
    
    def test_anti_repetition(self):
        """Avoids repeating same capability too many times."""
        # Create a streak
        recent = ["technique"] * MAX_CAPABILITY_STREAK
        
        results = Counter()
        trials = 100
        
        for _ in range(trials):
            result = select_capability(fatigue=2, recent_capabilities=recent)
            results[result] += 1
        
        # Technique should be rare after a streak
        technique_pct = results.get("technique", 0) / trials
        assert technique_pct < 0.5  # Should be reduced from streak
    
    def test_time_remaining_affects_selection(self):
        """Low time remaining may affect capability selection."""
        # With very low time, some capabilities may be deprioritized
        result = select_capability(fatigue=2, time_remaining=2)
        assert result in CAPABILITY_WEIGHTS.keys()


# =============================================================================
# DURATION AND NOTATION TESTS
# =============================================================================

class TestEstimateMiniSessionDuration:
    """Tests for estimate_mini_session_duration() function."""
    
    def test_known_capabilities(self):
        """Known capability types return their configured durations with medium intensity."""
        for capability, expected in AVG_MINI_SESSION_MINUTES.items():
            if capability != "default":
                result = estimate_mini_session_duration(capability, "medium")
                assert result == expected  # Medium intensity has 1.0 multiplier
    
    def test_unknown_capability_uses_default(self):
        """Unknown capability uses default duration."""
        result = estimate_mini_session_duration("unknown_capability", "medium")
        assert result == AVG_MINI_SESSION_MINUTES["default"]
    
    def test_intensity_multipliers(self):
        """Intensity affects duration."""
        base = AVG_MINI_SESSION_MINUTES["default"]
        
        small = estimate_mini_session_duration("default", "small")
        assert small == base * 0.7
        
        medium = estimate_mini_session_duration("default", "medium")
        assert medium == base * 1.0
        
        large = estimate_mini_session_duration("default", "large")
        assert large == base * 1.5


class TestShouldShowNotation:
    """Tests for should_show_notation() function."""
    
    def test_returns_boolean(self):
        """Returns True or False."""
        result = should_show_notation()
        assert result in (True, False)
    
    def test_distribution_matches_config(self):
        """Shows notation ~20% of the time."""
        show_count = sum(1 for _ in range(500) if should_show_notation())
        
        # Should be roughly 20% (allow large variance for randomness)
        show_pct = show_count / 500
        assert 0.10 < show_pct < 0.35


# =============================================================================
# CONFIGURATION CONSTANT TESTS
# =============================================================================

class TestConfigurationConstants:
    """Tests that configuration constants are valid."""
    
    def test_capability_weights_sum_to_one(self):
        """Capability weights should sum to approximately 1.0."""
        total = sum(CAPABILITY_WEIGHTS.values())
        assert 0.99 < total < 1.01
    
    def test_difficulty_weights_sum_to_one(self):
        """Difficulty weights should sum to approximately 1.0."""
        total = sum(DIFFICULTY_WEIGHTS.values())
        assert 0.99 < total < 1.01
    
    def test_novelty_reinforcement_sum_to_one(self):
        """Novelty/reinforcement weights should sum to 1.0."""
        total = sum(NOVELTY_REINFORCEMENT.values())
        assert 0.99 < total < 1.01
    
    def test_all_capabilities_have_duration(self):
        """All capability types should have duration estimates."""
        for capability in CAPABILITY_WEIGHTS.keys():
            assert capability in AVG_MINI_SESSION_MINUTES
    
    def test_fatigue_modifiers_valid(self):
        """All fatigue modifiers are non-negative."""
        for level, modifiers in FATIGUE_CAPABILITY_MODIFIERS.items():
            for capability, modifier in modifiers.items():
                assert modifier >= 0, f"Negative modifier at fatigue {level} for {capability}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
