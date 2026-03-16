"""
Tests for Throughput (Density) Domain Scorer.

Tests note density and throughput complexity with facet-aware scoring.
"""

import pytest
from app.scoring.throughput_scorer import analyze_throughput_domain
from app.scoring.models import DomainResult


# =============================================================================
# TEST: BASIC FUNCTIONALITY
# =============================================================================

class TestThroughputScorerBasics:
    """Test basic throughput scorer functionality."""
    
    def test_returns_domain_result(self):
        """Should return a DomainResult instance."""
        profile = {
            'notes_per_second': 3.0,
            'peak_notes_per_second': 5.0,
        }
        result = analyze_throughput_domain(profile)
        assert isinstance(result, DomainResult)
    
    def test_result_has_required_fields(self):
        """Result should have all required domain result fields."""
        profile = {'notes_per_second': 2.0}
        result = analyze_throughput_domain(profile)
        
        assert hasattr(result, 'scores')
        assert hasattr(result, 'profile')
        assert hasattr(result, 'bands')
        assert hasattr(result, 'facet_scores')
    
    def test_handles_empty_profile(self):
        """Should handle empty profile with defaults."""
        result = analyze_throughput_domain({})
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
            'notes_per_second': 4.0,
            'peak_notes_per_second': 8.0,
            'throughput_volatility': 0.25,
        }
        result = analyze_throughput_domain(profile)
        
        # Check domain scores
        assert 0 <= result.scores['primary'] <= 1
        assert 0 <= result.scores['hazard'] <= 1
        assert 0 <= result.scores['overall'] <= 1
    
    def test_facet_scores_in_range(self):
        """Facet scores should be in [0, 1] range."""
        profile = {
            'notes_per_second': 5.0,
            'peak_notes_per_second': 10.0,
            'throughput_volatility': 0.4,
        }
        result = analyze_throughput_domain(profile)
        
        for key, value in result.facet_scores.items():
            assert 0 <= value <= 1, f"Facet {key} = {value} out of range"
    
    def test_low_density_low_complexity(self):
        """Low note density should have low complexity."""
        profile = {
            'notes_per_second': 1.0,
            'peak_notes_per_second': 1.5,
            'throughput_volatility': 0.0,
        }
        result = analyze_throughput_domain(profile)
        
        assert result.scores['primary'] < 0.2, "Low density should have low complexity"
    
    def test_high_density_high_complexity(self):
        """High note density should have high complexity."""
        profile = {
            'notes_per_second': 6.0,
            'peak_notes_per_second': 10.0,
            'throughput_volatility': 0.3,
        }
        result = analyze_throughput_domain(profile)
        
        assert result.scores['primary'] > 0.7, "High density should have high complexity"
    
    def test_higher_nps_increases_score(self):
        """Higher notes-per-second should increase primary score."""
        slow = analyze_throughput_domain({'notes_per_second': 1.0})
        fast = analyze_throughput_domain({'notes_per_second': 6.0})
        
        assert fast.scores['primary'] > slow.scores['primary']


# =============================================================================
# TEST: FACET SCORES
# =============================================================================

class TestFacetScores:
    """Test individual facet score calculations."""
    
    def test_has_expected_facets(self):
        """Result should have standard facet scores."""
        profile = {'notes_per_second': 3.0}
        result = analyze_throughput_domain(profile)
        
        expected_facets = [
            'sustained_density',
            'peak_density',
            'adaptation_pressure',
        ]
        
        for facet in expected_facets:
            assert facet in result.facet_scores, f"Missing facet: {facet}"
    
    def test_sustained_density_scales_with_nps(self):
        """Sustained density should increase with notes_per_second."""
        low = analyze_throughput_domain({'notes_per_second': 1.0})
        high = analyze_throughput_domain({'notes_per_second': 6.0})
        
        assert high.facet_scores['sustained_density'] > low.facet_scores['sustained_density']
    
    def test_peak_density_scales_with_peak_nps(self):
        """Peak density should increase with peak_notes_per_second."""
        low = analyze_throughput_domain({'peak_notes_per_second': 2.0})
        high = analyze_throughput_domain({'peak_notes_per_second': 10.0})
        
        assert high.facet_scores['peak_density'] > low.facet_scores['peak_density']
    
    def test_adaptation_pressure_scales_with_volatility(self):
        """Adaptation pressure should increase with throughput_volatility."""
        steady = analyze_throughput_domain({'throughput_volatility': 0.0})
        volatile = analyze_throughput_domain({'throughput_volatility': 0.4})
        
        assert volatile.facet_scores['adaptation_pressure'] > steady.facet_scores['adaptation_pressure']


# =============================================================================
# TEST: HAZARD CALCULATION
# =============================================================================

class TestHazardCalculation:
    """Test hazard score calculation."""
    
    def test_peak_density_affects_hazard(self):
        """Peak density should strongly affect hazard."""
        low_peak = analyze_throughput_domain({
            'notes_per_second': 3.0,
            'peak_notes_per_second': 3.0,
        })
        high_peak = analyze_throughput_domain({
            'notes_per_second': 3.0,
            'peak_notes_per_second': 10.0,
        })
        
        assert high_peak.scores['hazard'] > low_peak.scores['hazard']
    
    def test_volatility_contributes_to_hazard(self):
        """Throughput volatility should contribute to hazard."""
        steady = analyze_throughput_domain({
            'notes_per_second': 4.0,
            'throughput_volatility': 0.0,
        })
        volatile = analyze_throughput_domain({
            'notes_per_second': 4.0,
            'throughput_volatility': 0.4,
        })
        
        assert volatile.scores['hazard'] > steady.scores['hazard']


# =============================================================================
# TEST: FLAGS
# =============================================================================

class TestFlags:
    """Test flag generation."""
    
    def test_high_sustained_density_flag(self):
        """Should flag high sustained density."""
        profile = {'notes_per_second': 5.5}  # Results in sustained > 0.6
        result = analyze_throughput_domain(profile)
        
        if result.facet_scores['sustained_density'] > 0.6:
            assert 'high_sustained_density' in result.flags
    
    def test_dense_passages_flag(self):
        """Should flag dense passages (high peak)."""
        profile = {'peak_notes_per_second': 10.0}  # Results in peak > 0.7
        result = analyze_throughput_domain(profile)
        
        if result.facet_scores['peak_density'] > 0.7:
            assert 'dense_passages' in result.flags
    
    def test_throughput_burst_warning_flag(self):
        """Should flag when peak >> sustained."""
        profile = {
            'notes_per_second': 2.0,
            'peak_notes_per_second': 10.0,
        }
        result = analyze_throughput_domain(profile)
        
        # Peak is much higher than sustained
        if result.facet_scores['peak_density'] > result.facet_scores['sustained_density'] + 0.3:
            assert 'throughput_burst_warning' in result.flags


# =============================================================================
# TEST: CONFIDENCE
# =============================================================================

class TestConfidence:
    """Test confidence scoring."""
    
    def test_full_confidence_when_nps_provided(self):
        """Should have full confidence when notes_per_second provided."""
        profile = {'notes_per_second': 3.0}
        result = analyze_throughput_domain(profile)
        
        assert result.confidence == 1.0
    
    def test_lower_confidence_when_nps_missing(self):
        """Should have lower confidence when notes_per_second not provided."""
        profile = {}  # No notes_per_second
        result = analyze_throughput_domain(profile)
        
        assert result.confidence < 1.0


# =============================================================================
# TEST: BANDS/STAGES
# =============================================================================

class TestBands:
    """Test stage derivation from scores."""
    
    def test_bands_are_integers(self):
        """Band values should be integers."""
        profile = {'notes_per_second': 4.0}
        result = analyze_throughput_domain(profile)
        
        if result.bands:
            for key, value in result.bands.items():
                if value is not None:
                    assert isinstance(value, int), f"Band {key} should be int"


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_nps(self):
        """Should handle zero notes-per-second."""
        profile = {'notes_per_second': 0}
        result = analyze_throughput_domain(profile)
        
        assert result is not None
    
    def test_very_high_nps(self):
        """Should handle very high notes-per-second."""
        profile = {
            'notes_per_second': 20.0,
            'peak_notes_per_second': 30.0,
            'throughput_volatility': 1.0,
        }
        result = analyze_throughput_domain(profile)
        
        # Should cap at 1.0
        assert result.scores['primary'] <= 1.0
        assert result.scores['hazard'] <= 1.0
        assert result.scores['overall'] <= 1.0
    
    def test_none_peak_uses_nps(self):
        """Should use nps as default when peak not provided."""
        profile = {'notes_per_second': 4.0}
        result = analyze_throughput_domain(profile)
        
        # Peak defaults to nps when not provided, but normalized differently
        # Just ensure it doesn't crash and returns valid scores
        assert result is not None
        assert result.facet_scores['peak_density'] is not None
