"""
Tests for Tempo Domain Scorer.

Tests tempo complexity analysis with facet-aware scoring.
"""

import pytest
from app.scoring.tempo_scorer import analyze_tempo_domain
from app.scoring.models import DomainResult


# =============================================================================
# TEST: BASIC FUNCTIONALITY
# =============================================================================

class TestTempoScorerBasics:
    """Test basic tempo scorer functionality."""
    
    def test_returns_domain_result(self):
        """Should return a DomainResult instance."""
        profile = {
            'tempo_is_explicit': True,
            'base_bpm': 120,
        }
        result = analyze_tempo_domain(profile)
        assert isinstance(result, DomainResult)
    
    def test_result_has_required_fields(self):
        """Result should have all required domain result fields."""
        profile = {'tempo_is_explicit': True, 'base_bpm': 100}
        result = analyze_tempo_domain(profile)
        
        assert hasattr(result, 'scores')
        assert hasattr(result, 'profile')
        assert hasattr(result, 'bands')
        assert hasattr(result, 'facet_scores')
    
    def test_handles_empty_profile(self):
        """Should handle empty profile (no explicit tempo)."""
        result = analyze_tempo_domain({})
        assert isinstance(result, DomainResult)
        # Empty profile means no explicit tempo
        assert 'no_tempo_marking' in result.flags


# =============================================================================
# TEST: NO EXPLICIT TEMPO
# =============================================================================

class TestNoExplicitTempo:
    """Test behavior when tempo is not explicitly marked."""
    
    def test_returns_null_scores_when_no_explicit_tempo(self):
        """Should return null scores when tempo not explicit."""
        profile = {'tempo_is_explicit': False, 'base_bpm': 120}
        result = analyze_tempo_domain(profile)
        
        assert result.scores['primary'] is None
        assert result.scores['hazard'] is None
        assert result.scores['overall'] is None
    
    def test_returns_null_facets_when_no_explicit_tempo(self):
        """Should return null facet scores when tempo not explicit."""
        profile = {'tempo_is_explicit': False}
        result = analyze_tempo_domain(profile)
        
        assert result.facet_scores['speed_demand'] is None
        assert result.facet_scores['tempo_control_demand'] is None
        assert result.facet_scores['tempo_variability'] is None
    
    def test_flags_no_tempo_marking(self):
        """Should flag when no tempo marking."""
        profile = {'tempo_is_explicit': False}
        result = analyze_tempo_domain(profile)
        
        assert 'no_tempo_marking' in result.flags
    
    def test_low_confidence_when_no_explicit_tempo(self):
        """Should have low confidence when no explicit tempo."""
        profile = {'tempo_is_explicit': False}
        result = analyze_tempo_domain(profile)
        
        assert result.confidence == 0.0


# =============================================================================
# TEST: SCORE CALCULATIONS
# =============================================================================

class TestScoreCalculations:
    """Test score calculation logic."""
    
    def test_scores_in_zero_one_range(self):
        """All scores should be in [0, 1] range."""
        profile = {
            'tempo_is_explicit': True,
            'base_bpm': 140,
            'effective_bpm': 140,
            'tempo_change_count': 3,
            'tempo_volatility': 0.2,
        }
        result = analyze_tempo_domain(profile)
        
        # Check domain scores
        assert 0 <= result.scores['primary'] <= 1
        assert 0 <= result.scores['hazard'] <= 1
        assert 0 <= result.scores['overall'] <= 1
    
    def test_facet_scores_in_range(self):
        """Facet scores should be in [0, 1] range."""
        profile = {
            'tempo_is_explicit': True,
            'base_bpm': 150,
            'tempo_change_count': 4,
            'tempo_volatility': 0.3,
        }
        result = analyze_tempo_domain(profile)
        
        for key, value in result.facet_scores.items():
            if value is not None:
                assert 0 <= value <= 1, f"Facet {key} = {value} out of range"
    
    def test_slow_tempo_low_speed_demand(self):
        """Slow tempo should have low speed demand."""
        profile = {
            'tempo_is_explicit': True,
            'base_bpm': 60,
            'effective_bpm': 60,
        }
        result = analyze_tempo_domain(profile)
        
        assert result.facet_scores['speed_demand'] < 0.2, "Slow tempo should have low speed demand"
    
    def test_fast_tempo_high_speed_demand(self):
        """Fast tempo should have high speed demand."""
        profile = {
            'tempo_is_explicit': True,
            'base_bpm': 180,
            'effective_bpm': 180,
        }
        result = analyze_tempo_domain(profile)
        
        assert result.facet_scores['speed_demand'] > 0.8, "Fast tempo should have high speed demand"
    
    def test_higher_bpm_increases_primary_score(self):
        """Higher BPM should increase primary score."""
        slow = analyze_tempo_domain({
            'tempo_is_explicit': True,
            'base_bpm': 60,
            'effective_bpm': 60,
        })
        fast = analyze_tempo_domain({
            'tempo_is_explicit': True,
            'base_bpm': 180,
            'effective_bpm': 180,
        })
        
        assert fast.scores['primary'] > slow.scores['primary']


# =============================================================================
# TEST: FACET SCORES
# =============================================================================

class TestFacetScores:
    """Test individual facet score calculations."""
    
    def test_has_expected_facets(self):
        """Result should have standard facet scores."""
        profile = {'tempo_is_explicit': True, 'base_bpm': 120}
        result = analyze_tempo_domain(profile)
        
        expected_facets = [
            'speed_demand',
            'tempo_control_demand',
            'tempo_variability',
        ]
        
        for facet in expected_facets:
            assert facet in result.facet_scores, f"Missing facet: {facet}"
    
    def test_tempo_control_scales_with_changes(self):
        """Tempo control demand should increase with tempo changes."""
        few_changes = analyze_tempo_domain({
            'tempo_is_explicit': True,
            'base_bpm': 120,
            'tempo_change_count': 0,
        })
        many_changes = analyze_tempo_domain({
            'tempo_is_explicit': True,
            'base_bpm': 120,
            'tempo_change_count': 6,
        })
        
        assert many_changes.facet_scores['tempo_control_demand'] > few_changes.facet_scores['tempo_control_demand']
    
    def test_tempo_variability_scales_with_volatility(self):
        """Tempo variability should increase with volatility."""
        low_volatility = analyze_tempo_domain({
            'tempo_is_explicit': True,
            'base_bpm': 120,
            'tempo_volatility': 0.0,
        })
        high_volatility = analyze_tempo_domain({
            'tempo_is_explicit': True,
            'base_bpm': 120,
            'tempo_volatility': 0.4,
        })
        
        assert high_volatility.facet_scores['tempo_variability'] > low_volatility.facet_scores['tempo_variability']


# =============================================================================
# TEST: HAZARD CALCULATION
# =============================================================================

class TestHazardCalculation:
    """Test hazard score calculation."""
    
    def test_sudden_changes_increase_hazard(self):
        """Sudden tempo changes should increase hazard."""
        gradual = analyze_tempo_domain({
            'tempo_is_explicit': True,
            'base_bpm': 120,
            'has_sudden_change': False,
            'tempo_change_count': 2,
        })
        sudden = analyze_tempo_domain({
            'tempo_is_explicit': True,
            'base_bpm': 120,
            'has_sudden_change': True,
            'tempo_change_count': 2,
        })
        
        assert sudden.scores['hazard'] >= gradual.scores['hazard']
    
    def test_accel_ritard_contribute_to_control(self):
        """Accelerando/ritardando should contribute to complexity."""
        no_changes = analyze_tempo_domain({
            'tempo_is_explicit': True,
            'base_bpm': 120,
            'has_accelerando': False,
            'has_ritardando': False,
        })
        with_changes = analyze_tempo_domain({
            'tempo_is_explicit': True,
            'base_bpm': 120,
            'has_accelerando': True,
            'has_ritardando': True,
        })
        
        assert with_changes.scores['overall'] >= no_changes.scores['overall']


# =============================================================================
# TEST: BANDS/STAGES
# =============================================================================

class TestBands:
    """Test stage derivation from scores."""
    
    def test_bands_are_integers_when_explicit_tempo(self):
        """Band values should be integers when tempo is explicit."""
        profile = {'tempo_is_explicit': True, 'base_bpm': 120}
        result = analyze_tempo_domain(profile)
        
        if result.bands:
            for key, value in result.bands.items():
                if value is not None:
                    assert isinstance(value, int), f"Band {key} should be int"
    
    def test_bands_are_null_when_no_explicit_tempo(self):
        """Band values should be null when tempo not explicit."""
        profile = {'tempo_is_explicit': False}
        result = analyze_tempo_domain(profile)
        
        for key, value in result.bands.items():
            assert value is None


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_minimum_bpm(self):
        """Should handle very slow tempo."""
        profile = {
            'tempo_is_explicit': True,
            'base_bpm': 40,
            'effective_bpm': 40,
        }
        result = analyze_tempo_domain(profile)
        
        assert isinstance(result, DomainResult)
        assert result.scores['primary'] != None
    
    def test_maximum_bpm(self):
        """Should handle very fast tempo."""
        profile = {
            'tempo_is_explicit': True,
            'base_bpm': 240,
            'effective_bpm': 240,
            'tempo_change_count': 10,
            'tempo_volatility': 0.9,
        }
        result = analyze_tempo_domain(profile)
        
        # Should cap at 1.0
        assert result.scores['primary'] <= 1.0
        assert result.scores['hazard'] <= 1.0
        assert result.scores['overall'] <= 1.0
    
    def test_zero_bpm_handled(self):
        """Should handle zero BPM (edge case)."""
        profile = {
            'tempo_is_explicit': True,
            'base_bpm': 0,
        }
        # Should not crash
        result = analyze_tempo_domain(profile)
        assert isinstance(result, DomainResult)
    
    def test_rubato_flag(self):
        """Should handle rubato indication."""
        profile = {
            'tempo_is_explicit': True,
            'base_bpm': 80,
            'has_rubato': True,
        }
        result = analyze_tempo_domain(profile)
        assert isinstance(result, DomainResult)
