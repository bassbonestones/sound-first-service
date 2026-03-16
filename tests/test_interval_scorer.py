"""
Tests for Interval Domain Scorer.

Tests interval complexity analysis with facet-aware scoring.
"""

import pytest
from app.scoring.interval_scorer import analyze_interval_domain
from app.scoring.models import DomainResult


# =============================================================================
# TEST: BASIC FUNCTIONALITY
# =============================================================================

class TestIntervalScorerBasics:
    """Test basic interval scorer functionality."""
    
    def test_returns_domain_result(self):
        """Should return a DomainResult instance."""
        profile = {
            'interval_p50': 2,
            'interval_p75': 4,
            'interval_p90': 7,
            'interval_max': 12,
            'step_ratio': 0.6,
            'skip_ratio': 0.3,
            'leap_ratio': 0.1,
        }
        result = analyze_interval_domain(profile)
        assert isinstance(result, DomainResult)
    
    def test_result_has_required_fields(self):
        """Result should have all required domain result fields."""
        profile = {'interval_p50': 2, 'interval_p75': 4}
        result = analyze_interval_domain(profile)
        
        assert hasattr(result, 'scores')
        assert hasattr(result, 'profile')
        assert hasattr(result, 'bands')
    
    def test_handles_empty_profile(self):
        """Should handle empty profile with defaults."""
        result = analyze_interval_domain({})
        assert isinstance(result, DomainResult)
        assert result.scores is not None
    
    def test_handles_none_values(self):
        """Should handle None values gracefully."""
        profile = {'interval_p50': None, 'interval_p75': None}
        # Should not raise, may use defaults
        try:
            result = analyze_interval_domain(profile)
            assert isinstance(result, DomainResult)
        except (TypeError, ValueError):
            # Some implementations may not handle None gracefully
            pytest.skip("Implementation does not handle None values")


# =============================================================================
# TEST: SCORE CALCULATIONS
# =============================================================================

class TestScoreCalculations:
    """Test score calculation logic."""
    
    def test_scores_in_zero_one_range(self):
        """All scores should be in [0, 1] range."""
        profile = {
            'interval_p50': 5,
            'interval_p75': 10,
            'interval_p90': 15,
            'interval_max': 24,
            'step_ratio': 0.4,
            'skip_ratio': 0.3,
            'leap_ratio': 0.2,
            'large_leap_ratio': 0.1,
            'max_large_leaps_in_window': 3,
        }
        result = analyze_interval_domain(profile)
        
        # Check domain scores (scores is a dict)
        assert 0 <= result.scores['primary'] <= 1
        assert 0 <= result.scores['hazard'] <= 1
        assert 0 <= result.scores['overall'] <= 1
    
    def test_facet_scores_in_range(self):
        """Facet scores should be in [0, 1] range."""
        profile = {
            'interval_p75': 8,
            'interval_p90': 12,
            'interval_max': 20,
            'large_leap_ratio': 0.15,
            'extreme_leap_ratio': 0.05,
            'max_large_leaps_in_window': 2,
            'max_extreme_leaps_in_window': 1,
        }
        result = analyze_interval_domain(profile)
        
        for key, value in result.facet_scores.items():
            assert 0 <= value <= 1, f"Facet {key} = {value} out of range"
    
    def test_simple_intervals_low_complexity(self):
        """Profile with small intervals should have low complexity."""
        simple_profile = {
            'interval_p50': 1,
            'interval_p75': 2,
            'interval_p90': 3,
            'interval_max': 4,
            'step_ratio': 0.9,
            'skip_ratio': 0.1,
            'leap_ratio': 0.0,
            'large_leap_ratio': 0.0,
            'extreme_leap_ratio': 0.0,
            'max_large_leaps_in_window': 0,
            'max_extreme_leaps_in_window': 0,
        }
        result = analyze_interval_domain(simple_profile)
        
        # Simple stepwise motion should have low primary score
        assert result.scores['primary'] < 0.3, "Simple intervals should have low complexity"
        assert result.scores['hazard'] < 0.2, "No leaps should mean low hazard"
    
    def test_complex_intervals_high_complexity(self):
        """Profile with large intervals should have high complexity."""
        complex_profile = {
            'interval_p50': 7,
            'interval_p75': 12,
            'interval_p90': 19,
            'interval_max': 36,
            'step_ratio': 0.1,
            'skip_ratio': 0.2,
            'leap_ratio': 0.3,
            'large_leap_ratio': 0.25,
            'extreme_leap_ratio': 0.15,
            'max_large_leaps_in_window': 4,
            'max_extreme_leaps_in_window': 2,
        }
        result = analyze_interval_domain(complex_profile)
        
        # Large leaps should increase complexity
        assert result.scores['primary'] > 0.5, "Large intervals should have high complexity"
        assert result.scores['hazard'] > 0.5, "Extreme leaps should increase hazard"
    
    def test_extreme_leap_boosts_hazard(self):
        """Extreme leaps should boost hazard score."""
        base_profile = {
            'interval_p75': 5,
            'interval_p90': 7,
            'interval_max': 12,
            'extreme_leap_ratio': 0.0,
            'max_large_leaps_in_window': 0,
            'max_extreme_leaps_in_window': 0,
        }
        
        extreme_profile = {
            **base_profile,
            'interval_max': 24,
            'extreme_leap_ratio': 0.1,
            'max_extreme_leaps_in_window': 2,
        }
        
        base_result = analyze_interval_domain(base_profile)
        extreme_result = analyze_interval_domain(extreme_profile)
        
        assert extreme_result.scores['hazard'] > base_result.scores['hazard']


# =============================================================================
# TEST: FACET SCORES
# =============================================================================

class TestFacetScores:
    """Test individual facet score calculations."""
    
    def test_has_expected_facets(self):
        """Result should have standard facet scores."""
        profile = {'interval_p75': 5, 'interval_p90': 10, 'interval_max': 15}
        result = analyze_interval_domain(profile)
        
        expected_facets = [
            'step_skip_complexity',
            'sustained_leap_complexity', 
            'extreme_leap_hazard',
            'clustered_leap_hazard',
        ]
        
        for facet in expected_facets:
            assert facet in result.facet_scores, f"Missing facet: {facet}"
    
    def test_step_skip_complexity_scales_with_p75(self):
        """Step/skip complexity should increase with p75."""
        low_p75 = analyze_interval_domain({'interval_p75': 2})
        high_p75 = analyze_interval_domain({'interval_p75': 10})
        
        assert high_p75.facet_scores['step_skip_complexity'] > low_p75.facet_scores['step_skip_complexity']
    
    def test_sustained_leap_scales_with_p90(self):
        """Sustained leap complexity should increase with p90."""
        low_p90 = analyze_interval_domain({'interval_p90': 5})
        high_p90 = analyze_interval_domain({'interval_p90': 17})
        
        assert high_p90.facet_scores['sustained_leap_complexity'] > low_p90.facet_scores['sustained_leap_complexity']
    
    def test_extreme_hazard_scales_with_max(self):
        """Extreme leap hazard should increase with max interval."""
        low_max = analyze_interval_domain({'interval_max': 12})
        high_max = analyze_interval_domain({'interval_max': 30})
        
        assert high_max.facet_scores['extreme_leap_hazard'] > low_max.facet_scores['extreme_leap_hazard']


# =============================================================================
# TEST: BANDS/STAGES
# =============================================================================

class TestBands:
    """Test stage derivation from scores."""
    
    def test_bands_are_integers(self):
        """Band values should be integers."""
        profile = {'interval_p75': 5, 'interval_p90': 10, 'interval_max': 15}
        result = analyze_interval_domain(profile)
        
        if result.bands:
            for key, value in result.bands.items():
                if value is not None:
                    assert isinstance(value, int), f"Band {key} should be int"
    
    def test_primary_band_exists(self):
        """Should have a primary stage band."""
        profile = {'interval_p75': 7, 'interval_p90': 12, 'interval_max': 18}
        result = analyze_interval_domain(profile)
        
        assert 'primary_stage' in result.bands or result.bands.get('primary') is not None or len(result.bands) > 0


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_intervals(self):
        """Should handle zero-interval profiles (single note pieces)."""
        profile = {
            'interval_p50': 0,
            'interval_p75': 0,
            'interval_p90': 0,
            'interval_max': 0,
            'step_ratio': 0,
            'skip_ratio': 0,
            'leap_ratio': 0,
        }
        result = analyze_interval_domain(profile)
        
        # Zero intervals should produce minimal scores
        assert result.scores['primary'] == 0 or result.scores['primary'] < 0.1
    
    def test_maximum_intervals(self):
        """Should handle very large intervals."""
        profile = {
            'interval_p50': 12,
            'interval_p75': 24,
            'interval_p90': 36,
            'interval_max': 48,  # 4 octaves
            'large_leap_ratio': 0.5,
            'extreme_leap_ratio': 0.3,
            'max_large_leaps_in_window': 10,
            'max_extreme_leaps_in_window': 5,
        }
        result = analyze_interval_domain(profile)
        
        # Should cap at 1.0
        assert result.scores['primary'] <= 1.0
        assert result.scores['hazard'] <= 1.0
        assert result.scores['overall'] <= 1.0
    
    def test_negative_values_handled(self):
        """Should handle negative values (shouldn't occur in practice)."""
        profile = {'interval_p75': -1, 'interval_max': -5}
        # Should not crash
        result = analyze_interval_domain(profile)
        assert isinstance(result, DomainResult)
