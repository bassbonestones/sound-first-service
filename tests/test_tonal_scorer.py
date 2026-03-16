"""
Tests for Tonal Domain Scorer.

Tests tonal complexity analysis with facet-aware scoring.
"""

import pytest
from app.scoring.tonal_scorer import analyze_tonal_domain
from app.scoring.models import DomainResult


# =============================================================================
# TEST: BASIC FUNCTIONALITY
# =============================================================================

class TestTonalScorerBasics:
    """Test basic tonal scorer functionality."""
    
    def test_returns_domain_result(self):
        """Should return a DomainResult instance."""
        profile = {
            'accidental_rate': 0.1,
            'chromatic_ratio': 0.05,
        }
        result = analyze_tonal_domain(profile)
        assert isinstance(result, DomainResult)
    
    def test_result_has_required_fields(self):
        """Result should have all required domain result fields."""
        profile = {'accidental_rate': 0.1}
        result = analyze_tonal_domain(profile)
        
        assert hasattr(result, 'scores')
        assert hasattr(result, 'profile')
        assert hasattr(result, 'bands')
        assert hasattr(result, 'facet_scores')
    
    def test_handles_empty_profile(self):
        """Should handle empty profile with defaults."""
        result = analyze_tonal_domain({})
        assert result is not None
        assert result.scores is not None


# =============================================================================
# TEST: SCORE CALCULATIONS
# =============================================================================

class TestScoreCalculations:
    """Test score calculation logic."""
    
    def test_scores_in_zero_one_range(self):
        """All scores should be in [0, 1] range."""
        profile = {
            'accidental_rate': 0.2,
            'chromatic_ratio': 0.15,
            'diatonic_predictability_proxy': 0.7,
            'modulation_count': 2,
        }
        result = analyze_tonal_domain(profile)
        
        # Check domain scores
        assert 0 <= result.scores['primary'] <= 1
        assert 0 <= result.scores['hazard'] <= 1
        assert 0 <= result.scores['overall'] <= 1
    
    def test_facet_scores_in_range(self):
        """Facet scores should be in [0, 1] range."""
        profile = {
            'accidental_rate': 0.3,
            'chromatic_ratio': 0.2,
            'modulation_count': 3,
        }
        result = analyze_tonal_domain(profile)
        
        for key, value in result.facet_scores.items():
            assert 0 <= value <= 1, f"Facet {key} = {value} out of range"
    
    def test_diatonic_music_low_complexity(self):
        """Purely diatonic music should have low complexity."""
        profile = {
            'accidental_rate': 0.0,
            'chromatic_ratio': 0.0,
            'diatonic_predictability_proxy': 1.0,
            'modulation_count': 0,
        }
        result = analyze_tonal_domain(profile)
        
        assert result.scores['primary'] < 0.2, "Diatonic should have low complexity"
        assert result.scores['hazard'] < 0.2, "Diatonic should have low hazard"
    
    def test_chromatic_music_high_complexity(self):
        """Highly chromatic music should have high complexity."""
        profile = {
            'accidental_rate': 0.4,
            'chromatic_ratio': 0.3,
            'diatonic_predictability_proxy': 0.3,
            'modulation_count': 4,
        }
        result = analyze_tonal_domain(profile)
        
        assert result.scores['primary'] > 0.5, "Chromatic should have high complexity"
    
    def test_higher_accidentals_increases_score(self):
        """Higher accidental rate should increase primary score."""
        low = analyze_tonal_domain({'accidental_rate': 0.05})
        high = analyze_tonal_domain({'accidental_rate': 0.35})
        
        assert high.scores['primary'] > low.scores['primary']


# =============================================================================
# TEST: FACET SCORES
# =============================================================================

class TestFacetScores:
    """Test individual facet score calculations."""
    
    def test_has_expected_facets(self):
        """Result should have standard facet scores."""
        profile = {'accidental_rate': 0.1}
        result = analyze_tonal_domain(profile)
        
        expected_facets = [
            'chromatic_complexity',
            'accidental_load',
            'tonal_instability',
        ]
        
        for facet in expected_facets:
            assert facet in result.facet_scores, f"Missing facet: {facet}"
    
    def test_chromatic_complexity_scales_with_ratio(self):
        """Chromatic complexity should increase with chromatic_ratio."""
        low = analyze_tonal_domain({'chromatic_ratio': 0.0})
        high = analyze_tonal_domain({'chromatic_ratio': 0.25})
        
        assert high.facet_scores['chromatic_complexity'] > low.facet_scores['chromatic_complexity']
    
    def test_accidental_load_scales_with_rate(self):
        """Accidental load should increase with accidental_rate."""
        low = analyze_tonal_domain({'accidental_rate': 0.0})
        high = analyze_tonal_domain({'accidental_rate': 0.3})
        
        assert high.facet_scores['accidental_load'] > low.facet_scores['accidental_load']
    
    def test_tonal_instability_scales_with_predictability(self):
        """Tonal instability should increase when predictability decreases."""
        stable = analyze_tonal_domain({'diatonic_predictability_proxy': 1.0})
        unstable = analyze_tonal_domain({'diatonic_predictability_proxy': 0.3})
        
        assert unstable.facet_scores['tonal_instability'] > stable.facet_scores['tonal_instability']
    
    def test_modulations_increase_instability(self):
        """Modulations should increase tonal instability."""
        no_mods = analyze_tonal_domain({'modulation_count': 0})
        many_mods = analyze_tonal_domain({'modulation_count': 4})
        
        assert many_mods.facet_scores['tonal_instability'] > no_mods.facet_scores['tonal_instability']


# =============================================================================
# TEST: HAZARD CALCULATION
# =============================================================================

class TestHazardCalculation:
    """Test hazard score calculation."""
    
    def test_chromatic_spikes_increase_hazard(self):
        """Chromatic sections should increase hazard."""
        diatonic = analyze_tonal_domain({
            'chromatic_ratio': 0.0,
            'diatonic_predictability_proxy': 1.0,
        })
        chromatic = analyze_tonal_domain({
            'chromatic_ratio': 0.3,
            'diatonic_predictability_proxy': 0.5,
        })
        
        assert chromatic.scores['hazard'] > diatonic.scores['hazard']
    
    def test_instability_contributes_to_hazard(self):
        """Tonal instability should contribute to hazard."""
        stable = analyze_tonal_domain({
            'diatonic_predictability_proxy': 1.0,
            'modulation_count': 0,
        })
        unstable = analyze_tonal_domain({
            'diatonic_predictability_proxy': 0.4,
            'modulation_count': 3,
        })
        
        assert unstable.scores['hazard'] > stable.scores['hazard']


# =============================================================================
# TEST: FLAGS
# =============================================================================

class TestFlags:
    """Test flag generation."""
    
    def test_highly_chromatic_flag(self):
        """Should flag highly chromatic music."""
        profile = {'chromatic_ratio': 0.25}  # Results in complexity > 0.5
        result = analyze_tonal_domain(profile)
        
        # Note: Flag triggers at facet > 0.5, so need high enough ratio
        if result.facet_scores['chromatic_complexity'] > 0.5:
            assert 'highly_chromatic' in result.flags
    
    def test_heavy_accidentals_flag(self):
        """Should flag heavy accidental load."""
        profile = {'accidental_rate': 0.35}  # Results in load > 0.6
        result = analyze_tonal_domain(profile)
        
        if result.facet_scores['accidental_load'] > 0.6:
            assert 'heavy_accidentals' in result.flags
    
    def test_modulations_detected_flag(self):
        """Should flag when modulations detected."""
        profile = {'modulation_count': 3}
        result = analyze_tonal_domain(profile)
        
        assert any('modulations_detected' in flag for flag in result.flags)


# =============================================================================
# TEST: BANDS/STAGES
# =============================================================================

class TestBands:
    """Test stage derivation from scores."""
    
    def test_bands_are_integers(self):
        """Band values should be integers."""
        profile = {'accidental_rate': 0.2, 'chromatic_ratio': 0.1}
        result = analyze_tonal_domain(profile)
        
        if result.bands:
            for key, value in result.bands.items():
                if value is not None:
                    assert isinstance(value, int), f"Band {key} should be int"


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_all_zeros(self):
        """Should handle all-zero profile."""
        profile = {
            'accidental_rate': 0.0,
            'chromatic_ratio': 0.0,
            'modulation_count': 0,
        }
        result = analyze_tonal_domain(profile)
        
        assert result is not None
        assert result.scores['primary'] < 0.2
    
    def test_all_maxed_out(self):
        """Should handle maximum values."""
        profile = {
            'accidental_rate': 1.0,
            'chromatic_ratio': 1.0,
            'diatonic_predictability_proxy': 0.0,
            'modulation_count': 10,
            'key_center_ambiguity': 1.0,
        }
        result = analyze_tonal_domain(profile)
        
        # Should cap at 1.0
        assert result.scores['primary'] <= 1.0
        assert result.scores['hazard'] <= 1.0
        assert result.scores['overall'] <= 1.0
    
    def test_none_values_handled(self):
        """Should handle None values by using defaults."""
        profile = {
            'accidental_rate': None,
            'chromatic_ratio': None,
        }
        result = analyze_tonal_domain(profile)
        assert result is not None
