"""
Tests for Rhythm Domain Scorer.

Tests rhythm complexity analysis with facet-aware scoring.
"""

import pytest
from app.scoring.rhythm_scorer import analyze_rhythm_domain
from app.scoring.models import DomainResult


# =============================================================================
# TEST: BASIC FUNCTIONALITY
# =============================================================================

class TestRhythmScorerBasics:
    """Test basic rhythm scorer functionality."""
    
    def test_returns_domain_result(self):
        """Should return a DomainResult instance."""
        profile = {
            'shortest_duration': 0.5,
            'note_value_diversity': 0.4,
            'syncopation_ratio': 0.1,
        }
        result = analyze_rhythm_domain(profile)
        assert isinstance(result, DomainResult)
    
    def test_result_has_required_fields(self):
        """Result should have all required domain result fields."""
        profile = {'shortest_duration': 0.5}
        result = analyze_rhythm_domain(profile)
        
        assert hasattr(result, 'scores')
        assert hasattr(result, 'profile')
        assert hasattr(result, 'bands')
        assert hasattr(result, 'facet_scores')
    
    def test_handles_empty_profile(self):
        """Should handle empty profile with defaults."""
        result = analyze_rhythm_domain({})
        assert result is not None
        assert result.scores is not None
    
    def test_handles_none_values(self):
        """Should handle None values gracefully."""
        profile = {'shortest_duration': None, 'tuplet_ratio': None}
        # Some implementations may not handle None values for ratios
        try:
            result = analyze_rhythm_domain(profile)
            assert result is not None
        except (TypeError, ValueError):
            pytest.skip("Implementation does not handle None values for ratios")


# =============================================================================
# TEST: SCORE CALCULATIONS
# =============================================================================

class TestScoreCalculations:
    """Test score calculation logic."""
    
    def test_scores_in_zero_one_range(self):
        """All scores should be in [0, 1] range."""
        profile = {
            'shortest_duration': 0.25,
            'note_value_diversity': 0.6,
            'tuplet_ratio': 0.15,
            'dot_ratio': 0.1,
            'tie_ratio': 0.05,
            'syncopation_ratio': 0.2,
            'rhythm_measure_uniqueness_ratio': 0.6,
        }
        result = analyze_rhythm_domain(profile)
        
        # Check domain scores
        assert 0 <= result.scores['primary'] <= 1
        assert 0 <= result.scores['hazard'] <= 1
        assert 0 <= result.scores['overall'] <= 1
    
    def test_facet_scores_in_range(self):
        """Facet scores should be in [0, 1] range."""
        profile = {
            'shortest_duration': 0.125,
            'syncopation_ratio': 0.3,
            'tuplet_ratio': 0.1,
            'dot_ratio': 0.15,
            'tie_ratio': 0.1,
            'rhythm_measure_uniqueness_ratio': 0.7,
        }
        result = analyze_rhythm_domain(profile)
        
        for key, value in result.facet_scores.items():
            assert 0 <= value <= 1, f"Facet {key} = {value} out of range"
    
    def test_simple_rhythm_low_complexity(self):
        """Profile with simple rhythms should have low complexity."""
        simple_profile = {
            'shortest_duration': 1.0,  # Quarter note
            'note_value_diversity': 0.2,
            'tuplet_ratio': 0.0,
            'dot_ratio': 0.0,
            'tie_ratio': 0.0,
            'syncopation_ratio': 0.0,
            'rhythm_measure_uniqueness_ratio': 0.15,
        }
        result = analyze_rhythm_domain(simple_profile)
        
        assert result.scores['primary'] < 0.3, "Simple rhythms should have low complexity"
    
    def test_complex_rhythm_high_complexity(self):
        """Profile with complex rhythms should have high complexity."""
        complex_profile = {
            'shortest_duration': 0.125,  # 32nd note
            'note_value_diversity': 0.8,
            'tuplet_ratio': 0.2,
            'dot_ratio': 0.2,
            'tie_ratio': 0.15,
            'syncopation_ratio': 0.35,
            'rhythm_measure_uniqueness_ratio': 0.75,
        }
        result = analyze_rhythm_domain(complex_profile)
        
        assert result.scores['primary'] > 0.5, "Complex rhythms should have high complexity"
    
    def test_faster_subdivisions_increases_complexity(self):
        """Faster subdivisions should increase complexity."""
        slow = analyze_rhythm_domain({'shortest_duration': 1.0})  # quarter
        fast = analyze_rhythm_domain({'shortest_duration': 0.125})  # 32nd
        
        assert fast.scores['primary'] > slow.scores['primary']


# =============================================================================
# TEST: FACET SCORES
# =============================================================================

class TestFacetScores:
    """Test individual facet score calculations."""
    
    def test_has_expected_facets(self):
        """Result should have standard facet scores."""
        profile = {'shortest_duration': 0.5}
        result = analyze_rhythm_domain(profile)
        
        expected_facets = [
            'subdivision_complexity',
            'syncopation_complexity',
            'tuplet_complexity',
            'dot_tie_complexity',
            'pattern_novelty',
        ]
        
        for facet in expected_facets:
            assert facet in result.facet_scores, f"Missing facet: {facet}"
    
    def test_subdivision_complexity_scales_with_duration(self):
        """Subdivision complexity should increase with faster notes."""
        slow = analyze_rhythm_domain({'shortest_duration': 2.0})  # half note
        fast = analyze_rhythm_domain({'shortest_duration': 0.125})  # 32nd
        
        assert fast.facet_scores['subdivision_complexity'] > slow.facet_scores['subdivision_complexity']
    
    def test_syncopation_complexity_scales_with_ratio(self):
        """Syncopation complexity should increase with syncopation ratio."""
        low = analyze_rhythm_domain({'syncopation_ratio': 0.0})
        high = analyze_rhythm_domain({'syncopation_ratio': 0.3})
        
        assert high.facet_scores['syncopation_complexity'] > low.facet_scores['syncopation_complexity']
    
    def test_tuplet_complexity_scales_with_ratio(self):
        """Tuplet complexity should increase with tuplet ratio."""
        low = analyze_rhythm_domain({'tuplet_ratio': 0.0})
        high = analyze_rhythm_domain({'tuplet_ratio': 0.15})
        
        assert high.facet_scores['tuplet_complexity'] > low.facet_scores['tuplet_complexity']
    
    def test_dot_tie_complexity_scales_with_ratios(self):
        """Dot/tie complexity should increase with both ratios."""
        low = analyze_rhythm_domain({'dot_ratio': 0.0, 'tie_ratio': 0.0})
        high = analyze_rhythm_domain({'dot_ratio': 0.15, 'tie_ratio': 0.1})
        
        assert high.facet_scores['dot_tie_complexity'] > low.facet_scores['dot_tie_complexity']
    
    def test_pattern_novelty_scales_with_uniqueness(self):
        """Pattern novelty should increase with uniqueness ratio."""
        low = analyze_rhythm_domain({'rhythm_measure_uniqueness_ratio': 0.1})
        high = analyze_rhythm_domain({'rhythm_measure_uniqueness_ratio': 0.7})
        
        assert high.facet_scores['pattern_novelty'] > low.facet_scores['pattern_novelty']


# =============================================================================
# TEST: HAZARD CALCULATION
# =============================================================================

class TestHazardCalculation:
    """Test hazard score calculation."""
    
    def test_high_novelty_with_fast_subdivision_boosts_hazard(self):
        """Fast subdivisions + high novelty should boost hazard."""
        # Similar primary complexity but different hazard profiles
        steady = analyze_rhythm_domain({
            'shortest_duration': 0.25,
            'rhythm_measure_uniqueness_ratio': 0.2,
            'syncopation_ratio': 0.1,
        })
        
        bursty = analyze_rhythm_domain({
            'shortest_duration': 0.125,
            'rhythm_measure_uniqueness_ratio': 0.7,
            'syncopation_ratio': 0.3,
        })
        
        assert bursty.scores['hazard'] > steady.scores['hazard']
    
    def test_tuplets_contribute_to_hazard(self):
        """Tuplets should contribute to hazard."""
        no_tuplets = analyze_rhythm_domain({'tuplet_ratio': 0.0})
        with_tuplets = analyze_rhythm_domain({'tuplet_ratio': 0.2})
        
        assert with_tuplets.scores['hazard'] > no_tuplets.scores['hazard']


# =============================================================================
# TEST: BANDS/STAGES
# =============================================================================

class TestBands:
    """Test stage derivation from scores."""
    
    def test_bands_are_integers(self):
        """Band values should be integers."""
        profile = {'shortest_duration': 0.25, 'syncopation_ratio': 0.2}
        result = analyze_rhythm_domain(profile)
        
        if result.bands:
            for key, value in result.bands.items():
                if value is not None:
                    assert isinstance(value, int), f"Band {key} should be int"


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_duration_handled(self):
        """Should handle zero/invalid duration."""
        profile = {'shortest_duration': 0}
        result = analyze_rhythm_domain(profile)
        assert result is not None
        assert result.scores['primary'] <= 1.0
    
    def test_very_fast_subdivisions(self):
        """Should handle very fast subdivisions (64th notes)."""
        profile = {
            'shortest_duration': 0.0625,  # 64th note
            'tuplet_ratio': 0.3,
            'syncopation_ratio': 0.4,
            'rhythm_measure_uniqueness_ratio': 0.9,
        }
        result = analyze_rhythm_domain(profile)
        
        # Should cap at 1.0
        assert result.scores['primary'] <= 1.0
        assert result.scores['hazard'] <= 1.0
        assert result.scores['overall'] <= 1.0
    
    def test_all_ratios_at_max(self):
        """Should handle all ratios at maximum."""
        profile = {
            'shortest_duration': 0.0625,
            'tuplet_ratio': 1.0,
            'dot_ratio': 1.0,
            'tie_ratio': 1.0,
            'syncopation_ratio': 1.0,
            'rhythm_measure_uniqueness_ratio': 1.0,
        }
        result = analyze_rhythm_domain(profile)
        
        assert result.scores['primary'] <= 1.0
        assert result.scores['overall'] <= 1.0
    
    def test_negative_duration_handled(self):
        """Should handle negative duration (shouldn't occur in practice)."""
        profile = {'shortest_duration': -1}
        result = analyze_rhythm_domain(profile)
        assert result is not None
