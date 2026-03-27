"""
Tests for Difficulty Interactions.

Tests interaction bonuses when multiple domains are simultaneously difficult.
"""

import pytest
from app.scoring.interactions import (
    calculate_interaction_bonus,
    get_interaction_flags,
    has_interaction_hazard,
    InteractionResult,
    INTERACTION_CONFIG,
    MAX_INTERACTION_BONUS,
)


# =============================================================================
# TEST: BASIC FUNCTIONALITY
# =============================================================================

class TestInteractionBasics:
    """Test basic interaction calculation functionality."""
    
    def test_returns_interaction_result(self):
        """Should return an InteractionResult instance."""
        domain_scores = {
            'interval': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
            'rhythm': {'primary': 0.6, 'hazard': 0.4, 'overall': 0.5},
        }
        result = calculate_interaction_bonus(domain_scores)
        assert isinstance(result, InteractionResult)
    
    def test_result_has_required_fields(self):
        """Result should have all required fields."""
        domain_scores = {'interval': {'primary': 0.5}}
        result = calculate_interaction_bonus(domain_scores)
        
        assert hasattr(result, 'bonus')
        assert hasattr(result, 'flags')
        assert hasattr(result, 'warnings')
        assert hasattr(result, 'triggered_interactions')
    
    def test_handles_empty_domain_scores(self):
        """Should handle empty domain scores."""
        result = calculate_interaction_bonus({})
        assert result.bonus == 0.0
        assert result.flags == []
        assert result.triggered_interactions == []
    
    def test_handles_missing_domains(self):
        """Should handle when expected domains are missing."""
        domain_scores = {'interval': {'primary': 0.7}}  # Only interval, no rhythm
        result = calculate_interaction_bonus(domain_scores)
        assert result is not None


# =============================================================================
# TEST: INTERACTION TRIGGERING
# =============================================================================

class TestInteractionTriggering:
    """Test when interactions are triggered."""
    
    def test_interval_rhythm_interaction_triggers(self):
        """Interval-rhythm interaction should trigger when both above threshold."""
        domain_scores = {
            'interval': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
            'rhythm': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert 'interval_rhythm' in result.triggered_interactions
        assert 'high_leap_rhythm_combo' in result.flags
    
    def test_tempo_rhythm_interaction_triggers(self):
        """Tempo-rhythm interaction should trigger when both above threshold."""
        domain_scores = {
            'tempo': {'primary': 0.65, 'hazard': 0.5, 'overall': 0.55},
            'rhythm': {'primary': 0.65, 'hazard': 0.5, 'overall': 0.55},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert 'tempo_rhythm' in result.triggered_interactions
        assert 'fast_complex_rhythm' in result.flags
    
    def test_interval_tempo_interaction_triggers(self):
        """Interval-tempo interaction should trigger when both above threshold."""
        domain_scores = {
            'interval': {'primary': 0.65, 'hazard': 0.5, 'overall': 0.55},
            'tempo': {'primary': 0.65, 'hazard': 0.5, 'overall': 0.55},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert 'interval_tempo' in result.triggered_interactions
        assert 'leaps_at_speed' in result.flags
    
    def test_throughput_rhythm_interaction_triggers(self):
        """Throughput-rhythm interaction should trigger when both above threshold."""
        domain_scores = {
            'throughput': {'primary': 0.7, 'hazard': 0.5, 'overall': 0.55},
            'rhythm': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert 'throughput_rhythm' in result.triggered_interactions
        assert 'dense_complex_rhythm' in result.flags
    
    def test_no_interaction_when_below_thresholds(self):
        """Should not trigger when scores below thresholds."""
        domain_scores = {
            'interval': {'primary': 0.3, 'hazard': 0.2, 'overall': 0.25},
            'rhythm': {'primary': 0.3, 'hazard': 0.2, 'overall': 0.25},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert 'interval_rhythm' not in result.triggered_interactions
        assert result.bonus == 0.0
    
    def test_no_interaction_when_one_below_threshold(self):
        """Should not trigger when only one score above threshold."""
        domain_scores = {
            'interval': {'primary': 0.7, 'hazard': 0.6, 'overall': 0.65},  # Above
            'rhythm': {'primary': 0.3, 'hazard': 0.2, 'overall': 0.25},    # Below
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert 'interval_rhythm' not in result.triggered_interactions


# =============================================================================
# TEST: BONUS CALCULATION
# =============================================================================

class TestBonusCalculation:
    """Test bonus value calculations."""
    
    def test_single_interaction_bonus_value(self):
        """Single interaction should add its bonus."""
        domain_scores = {
            'interval': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
            'rhythm': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        # interval_rhythm has bonus of 0.08
        assert result.bonus == 0.08
    
    def test_multiple_interactions_sum_bonuses(self):
        """Multiple interactions should sum their bonuses."""
        domain_scores = {
            'interval': {'primary': 0.7, 'hazard': 0.6, 'overall': 0.65},
            'rhythm': {'primary': 0.7, 'hazard': 0.6, 'overall': 0.65},
            'tempo': {'primary': 0.7, 'hazard': 0.6, 'overall': 0.65},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        # Should trigger multiple interactions
        assert len(result.triggered_interactions) >= 2
        assert result.bonus > 0.08
    
    def test_bonus_capped_at_max(self):
        """Total bonus should be capped at MAX_INTERACTION_BONUS."""
        # Create domain scores that would trigger all interactions
        domain_scores = {
            'interval': {'primary': 0.8, 'hazard': 0.7, 'overall': 0.75},
            'rhythm': {'primary': 0.8, 'hazard': 0.7, 'overall': 0.75},
            'tempo': {'primary': 0.8, 'hazard': 0.7, 'overall': 0.75},
            'throughput': {'primary': 0.8, 'hazard': 0.7, 'overall': 0.75},
            'range': {'primary': 0.8, 'hazard': 0.7, 'overall': 0.75},
            'tonal': {'primary': 0.8, 'hazard': 0.7, 'overall': 0.75},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert result.bonus <= MAX_INTERACTION_BONUS
    
    def test_custom_max_bonus(self):
        """Should respect custom max_bonus parameter."""
        domain_scores = {
            'interval': {'primary': 0.8, 'hazard': 0.7, 'overall': 0.75},
            'rhythm': {'primary': 0.8, 'hazard': 0.7, 'overall': 0.75},
            'tempo': {'primary': 0.8, 'hazard': 0.7, 'overall': 0.75},
        }
        result = calculate_interaction_bonus(domain_scores, max_bonus=0.05)
        
        assert result.bonus <= 0.05


# =============================================================================
# TEST: NONE / NULL HANDLING
# =============================================================================

class TestNoneHandling:
    """Test handling of None scores."""
    
    def test_skips_interaction_when_score_is_none(self):
        """Should skip interaction when either score is None."""
        domain_scores = {
            'interval': {'primary': 0.7, 'hazard': 0.6, 'overall': 0.65},
            'rhythm': {'primary': None, 'hazard': None, 'overall': None},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert 'interval_rhythm' not in result.triggered_interactions
    
    def test_handles_missing_primary_key(self):
        """Should handle when 'primary' key is missing."""
        domain_scores = {
            'interval': {'hazard': 0.6, 'overall': 0.55},  # No 'primary'
            'rhythm': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert 'interval_rhythm' not in result.triggered_interactions


# =============================================================================
# TEST: FLAGS AND WARNINGS
# =============================================================================

class TestFlagsAndWarnings:
    """Test flag and warning generation."""
    
    def test_generates_flags_for_triggered_interactions(self):
        """Should generate flags for each triggered interaction."""
        domain_scores = {
            'interval': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
            'rhythm': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert len(result.flags) > 0
    
    def test_generates_warnings_for_triggered_interactions(self):
        """Should generate warnings for each triggered interaction."""
        domain_scores = {
            'interval': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
            'rhythm': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert len(result.warnings) > 0
        assert any('leap' in w.lower() or 'rhythm' in w.lower() for w in result.warnings)
    
    def test_no_flags_when_no_interactions(self):
        """Should have no flags when no interactions triggered."""
        domain_scores = {
            'interval': {'primary': 0.3},
            'rhythm': {'primary': 0.3},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert result.flags == []


# =============================================================================
# TEST: CONVENIENCE FUNCTIONS
# =============================================================================

class TestConvenienceFunctions:
    """Test convenience functions."""
    
    def test_get_interaction_flags(self):
        """get_interaction_flags should return just flags."""
        domain_scores = {
            'interval': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
            'rhythm': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
        }
        flags = get_interaction_flags(domain_scores)
        
        assert isinstance(flags, list)
        assert 'high_leap_rhythm_combo' in flags
    
    def test_get_interaction_flags_empty_when_none(self):
        """get_interaction_flags should return empty when no interactions."""
        domain_scores = {
            'interval': {'primary': 0.3},
            'rhythm': {'primary': 0.3},
        }
        flags = get_interaction_flags(domain_scores)
        
        assert flags == []
    
    def test_has_interaction_hazard_true(self):
        """has_interaction_hazard should return True when bonus > threshold."""
        domain_scores = {
            'interval': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
            'rhythm': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
        }
        # Default threshold is 0.05, interval_rhythm bonus is 0.08
        assert has_interaction_hazard(domain_scores) is True
    
    def test_has_interaction_hazard_false(self):
        """has_interaction_hazard should return False when bonus < threshold."""
        domain_scores = {
            'interval': {'primary': 0.3},
            'rhythm': {'primary': 0.3},
        }
        assert has_interaction_hazard(domain_scores) is False
    
    def test_has_interaction_hazard_custom_threshold(self):
        """has_interaction_hazard should respect custom threshold."""
        domain_scores = {
            'interval': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
            'rhythm': {'primary': 0.6, 'hazard': 0.5, 'overall': 0.55},
        }
        # Bonus is 0.08, set threshold higher
        assert has_interaction_hazard(domain_scores, threshold=0.1) is False


# =============================================================================
# TEST: CUSTOM CONFIG
# =============================================================================

class TestCustomConfig:
    """Test custom configuration support."""
    
    def test_custom_config_overrides_defaults(self):
        """Should use custom config when provided."""
        custom_config = {
            'interval_rhythm': {
                'interval_threshold': 0.3,  # Lower threshold
                'rhythm_threshold': 0.3,
                'bonus': 0.1,
                'flag': 'custom_flag',
                'warning': 'Custom warning',
            },
        }
        domain_scores = {
            'interval': {'primary': 0.4},
            'rhythm': {'primary': 0.4},
        }
        result = calculate_interaction_bonus(domain_scores, config=custom_config)
        
        assert 'interval_rhythm' in result.triggered_interactions
        assert 'custom_flag' in result.flags
        assert result.bonus == 0.1


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_exactly_at_threshold(self):
        """Should not trigger when exactly at threshold (> not >=)."""
        domain_scores = {
            'interval': {'primary': 0.55},  # Exactly at threshold
            'rhythm': {'primary': 0.55},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        # Threshold is 0.55, score must be > 0.55
        assert 'interval_rhythm' not in result.triggered_interactions
    
    def test_just_above_threshold(self):
        """Should trigger when just above threshold."""
        domain_scores = {
            'interval': {'primary': 0.56},  # Just above threshold
            'rhythm': {'primary': 0.56},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        assert 'interval_rhythm' in result.triggered_interactions
    
    def test_bonus_is_rounded(self):
        """Bonus should be rounded to 4 decimal places."""
        domain_scores = {
            'interval': {'primary': 0.6},
            'rhythm': {'primary': 0.6},
        }
        result = calculate_interaction_bonus(domain_scores)
        
        # Check bonus has at most 4 decimal places
        bonus_str = str(result.bonus)
        if '.' in bonus_str:
            decimals = len(bonus_str.split('.')[1])
            assert decimals <= 4


class TestGetInteractionHazards:
    """Tests for analyze_hazards function."""

    def test_returns_hazard_dict(self):
        """Should return dict with hazard categories."""
        from app.scoring.interactions import analyze_hazards
        
        domain_scores = {
            'interval': {'primary': 0.5, 'hazard': 0.3},
            'rhythm': {'primary': 0.4, 'hazard': 0.2},
        }
        result = analyze_hazards(domain_scores)
        
        assert isinstance(result, dict)
        assert 'domain_hazards' in result
        assert 'ability_hazards' in result
        assert 'interaction_hazards' in result

    def test_domain_hazards_flagged_at_high_threshold(self):
        """High hazard scores should be flagged."""
        from app.scoring.interactions import analyze_hazards
        
        domain_scores = {
            'interval': {'primary': 0.6, 'hazard': 0.85},  # High hazard
            'rhythm': {'primary': 0.4, 'hazard': 0.3},
        }
        result = analyze_hazards(domain_scores)
        
        assert len(result['domain_hazards']) == 1
        assert result['domain_hazards'][0]['domain'] == 'interval'
        assert result['domain_hazards'][0]['level'] == 'high'

    def test_ability_hazards_with_student_scores(self):
        """Should flag when piece exceeds student ability."""
        from app.scoring.interactions import analyze_hazards
        
        domain_scores = {
            'interval': {'primary': 0.6, 'hazard': 0.7},
            'rhythm': {'primary': 0.4, 'hazard': 0.3},
        }
        student_scores = {
            'interval': 0.4,  # Student ability lower than piece hazard
            'rhythm': 0.5,
        }
        result = analyze_hazards(domain_scores, student_scores, tolerance=0.1)
        
        # interval: 0.7 > 0.4 + 0.1 = 0.5, so should flag
        assert len(result['ability_hazards']) == 1
        assert result['ability_hazards'][0]['domain'] == 'interval'

    def test_interaction_hazards_when_triggered(self):
        """Interaction hazards should be included when interactions trigger."""
        from app.scoring.interactions import analyze_hazards
        
        # Scores high enough to trigger interval_rhythm interaction
        domain_scores = {
            'interval': {'primary': 0.7, 'hazard': 0.3},
            'rhythm': {'primary': 0.7, 'hazard': 0.3},
        }
        result = analyze_hazards(domain_scores)
        
        # Should have interaction hazards populated with warnings
        assert len(result['interaction_hazards']) > 0

    def test_no_interaction_hazards_when_none_triggered(self):
        """Should have empty interaction hazards when no interactions trigger."""
        from app.scoring.interactions import analyze_hazards
        
        # Low scores - no interactions should trigger
        domain_scores = {
            'interval': {'primary': 0.2, 'hazard': 0.1},
            'rhythm': {'primary': 0.2, 'hazard': 0.1},
        }
        result = analyze_hazards(domain_scores)
        
        assert result['interaction_hazards'] == []
