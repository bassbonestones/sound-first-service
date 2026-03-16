"""
Tests for Pattern / Predictability Domain Scorer.

Tests melodic and rhythmic pattern predictability with facet-aware scoring.
NOTE: This domain is INVERTED - high predictability = easier.
"""

import pytest
from app.scoring.pattern_scorer import analyze_pattern_domain
from app.scoring.models import DomainResult


# =============================================================================
# TEST: BASIC FUNCTIONALITY
# =============================================================================

class TestPatternScorerBasics:
    """Test basic pattern scorer functionality."""
    
    def test_returns_domain_result(self):
        """Should return a DomainResult instance."""
        profile = {
            'melodic_motif_uniqueness_ratio': 0.3,
            'rhythm_uniqueness_ratio': 0.4,
        }
        result = analyze_pattern_domain(profile)
        assert isinstance(result, DomainResult)
    
    def test_result_has_required_fields(self):
        """Result should have all required domain result fields."""
        profile = {'melodic_motif_repetition_ratio': 0.7}
        result = analyze_pattern_domain(profile)
        
        assert hasattr(result, 'scores')
        assert hasattr(result, 'profile')
        assert hasattr(result, 'bands')
        assert hasattr(result, 'facet_scores')
    
    def test_handles_empty_profile(self):
        """Should handle empty profile with defaults."""
        result = analyze_pattern_domain({})
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
            'melodic_motif_uniqueness_ratio': 0.4,
            'melodic_motif_repetition_ratio': 0.6,
            'rhythm_uniqueness_ratio': 0.3,
            'rhythm_repetition_ratio': 0.7,
            'sequence_coverage_ratio': 0.3,
        }
        result = analyze_pattern_domain(profile)
        
        # Check domain scores
        assert 0 <= result.scores['primary'] <= 1
        assert 0 <= result.scores['hazard'] <= 1
        assert 0 <= result.scores['overall'] <= 1
    
    def test_facet_scores_in_range(self):
        """Facet scores should be in [0, 1] range."""
        profile = {
            'melodic_motif_repetition_ratio': 0.5,
            'rhythm_repetition_ratio': 0.5,
            'sequence_coverage_ratio': 0.3,
        }
        result = analyze_pattern_domain(profile)
        
        for key, value in result.facet_scores.items():
            assert 0 <= value <= 1, f"Facet {key} = {value} out of range"
    
    def test_high_repetition_low_difficulty(self):
        """High repetition should result in LOW difficulty (inverted domain)."""
        profile = {
            'melodic_motif_repetition_ratio': 0.9,  # Very repetitive
            'rhythm_repetition_ratio': 0.85,
            'sequence_coverage_ratio': 0.45,  # Lots of sequences
        }
        result = analyze_pattern_domain(profile)
        
        assert result.scores['primary'] < 0.3, "High repetition should = low difficulty"
    
    def test_high_uniqueness_high_difficulty(self):
        """High uniqueness should result in HIGH difficulty (inverted domain)."""
        profile = {
            'melodic_motif_uniqueness_ratio': 0.9,  # Very unique
            'melodic_motif_repetition_ratio': 0.1,
            'rhythm_uniqueness_ratio': 0.85,
            'rhythm_repetition_ratio': 0.15,
            'sequence_coverage_ratio': 0.0,  # No predictable sequences
        }
        result = analyze_pattern_domain(profile)
        
        assert result.scores['primary'] > 0.6, "High uniqueness should = high difficulty"
    
    def test_more_repetition_decreases_score(self):
        """More repetition should decrease difficulty score."""
        unique = analyze_pattern_domain({
            'melodic_motif_repetition_ratio': 0.2,
            'rhythm_repetition_ratio': 0.2,
        })
        repetitive = analyze_pattern_domain({
            'melodic_motif_repetition_ratio': 0.8,
            'rhythm_repetition_ratio': 0.8,
        })
        
        assert repetitive.scores['primary'] < unique.scores['primary']


# =============================================================================
# TEST: FACET SCORES
# =============================================================================

class TestFacetScores:
    """Test individual facet score calculations."""
    
    def test_has_expected_facets(self):
        """Result should have standard facet scores."""
        profile = {'melodic_motif_repetition_ratio': 0.5}
        result = analyze_pattern_domain(profile)
        
        expected_facets = [
            'melodic_predictability',
            'rhythmic_predictability',
            'structural_regularity',
        ]
        
        for facet in expected_facets:
            assert facet in result.facet_scores, f"Missing facet: {facet}"
    
    def test_melodic_predictability_from_repetition(self):
        """Melodic predictability should come from repetition ratio."""
        profile = {'melodic_motif_repetition_ratio': 0.7}
        result = analyze_pattern_domain(profile)
        
        # Predictability facet should be high when repetition is high
        assert result.facet_scores['melodic_predictability'] >= 0.6
    
    def test_rhythmic_predictability_from_repetition(self):
        """Rhythmic predictability should come from rhythm repetition ratio."""
        profile = {'rhythm_repetition_ratio': 0.8}
        result = analyze_pattern_domain(profile)
        
        assert result.facet_scores['rhythmic_predictability'] >= 0.7
    
    def test_structural_regularity_from_sequences(self):
        """Structural regularity should increase with sequence coverage."""
        low = analyze_pattern_domain({'sequence_coverage_ratio': 0.0})
        high = analyze_pattern_domain({'sequence_coverage_ratio': 0.5})
        
        assert high.facet_scores['structural_regularity'] > low.facet_scores['structural_regularity']


# =============================================================================
# TEST: INVERTED DOMAIN BEHAVIOR
# =============================================================================

class TestInvertedDomain:
    """Test that domain is correctly inverted (predictability = easier)."""
    
    def test_predictability_is_ease_not_difficulty(self):
        """Facet scores should represent PREDICTABILITY (ease), not difficulty."""
        repetitive = analyze_pattern_domain({
            'melodic_motif_repetition_ratio': 0.9,
        })
        unique = analyze_pattern_domain({
            'melodic_motif_repetition_ratio': 0.1,
        })
        
        # Repetitive music should have HIGH predictability facet
        assert repetitive.facet_scores['melodic_predictability'] > unique.facet_scores['melodic_predictability']
        
        # But LOW difficulty score
        assert repetitive.scores['primary'] < unique.scores['primary']
    
    def test_domain_scores_are_difficulty(self):
        """Domain scores should represent DIFFICULTY, not ease."""
        # High predictability = low difficulty
        easy_profile = {
            'melodic_motif_repetition_ratio': 0.9,
            'rhythm_repetition_ratio': 0.9,
            'sequence_coverage_ratio': 0.5,
        }
        # Low predictability = high difficulty
        hard_profile = {
            'melodic_motif_repetition_ratio': 0.1,
            'rhythm_repetition_ratio': 0.1,
            'sequence_coverage_ratio': 0.0,
        }
        
        easy = analyze_pattern_domain(easy_profile)
        hard = analyze_pattern_domain(hard_profile)
        
        assert hard.scores['primary'] > easy.scores['primary']
        assert hard.scores['overall'] > easy.scores['overall']


# =============================================================================
# TEST: HAZARD CALCULATION
# =============================================================================

class TestHazardCalculation:
    """Test hazard score calculation."""
    
    def test_high_uniqueness_increases_hazard(self):
        """High uniqueness in any facet should increase hazard."""
        predictable = analyze_pattern_domain({
            'melodic_motif_repetition_ratio': 0.85,
            'rhythm_repetition_ratio': 0.85,
        })
        unpredictable = analyze_pattern_domain({
            'melodic_motif_repetition_ratio': 0.1,
            'rhythm_repetition_ratio': 0.1,
        })
        
        assert unpredictable.scores['hazard'] > predictable.scores['hazard']
    
    def test_max_facet_difficulty_affects_hazard(self):
        """Hazard should consider max difficulty across facets."""
        # One very unpredictable facet should increase hazard
        mixed = analyze_pattern_domain({
            'melodic_motif_repetition_ratio': 0.9,  # Easy melodic
            'rhythm_repetition_ratio': 0.1,         # Hard rhythmic
        })
        
        # Hazard should be elevated due to rhythmic difficulty
        assert mixed.scores['hazard'] > 0.3


# =============================================================================
# TEST: BANDS/STAGES
# =============================================================================

class TestBands:
    """Test stage derivation from scores."""
    
    def test_bands_are_integers(self):
        """Band values should be integers."""
        profile = {'melodic_motif_repetition_ratio': 0.5}
        result = analyze_pattern_domain(profile)
        
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
            'melodic_motif_repetition_ratio': 0.0,
            'rhythm_repetition_ratio': 0.0,
            'sequence_coverage_ratio': 0.0,
        }
        result = analyze_pattern_domain(profile)
        
        assert result is not None
        # All zeros = no repetition = high difficulty
        assert result.scores['primary'] >= 0.5
    
    def test_all_ones(self):
        """Should handle all-one profile (maximum repetition)."""
        profile = {
            'melodic_motif_repetition_ratio': 1.0,
            'rhythm_repetition_ratio': 1.0,
            'sequence_coverage_ratio': 0.5,  # Max normalized value
        }
        result = analyze_pattern_domain(profile)
        
        # Should cap at 1.0
        assert result.scores['primary'] <= 1.0
        assert result.scores['primary'] < 0.3  # Very predictable = low difficulty
    
    def test_none_values_handled(self):
        """Should handle None values by using defaults."""
        profile = {
            'melodic_motif_repetition_ratio': None,
            'rhythm_repetition_ratio': None,
        }
        result = analyze_pattern_domain(profile)
        
        assert result is not None
        assert result.scores['primary'] is not None
