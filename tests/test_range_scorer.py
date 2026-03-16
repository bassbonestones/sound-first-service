"""
Tests for Range Domain Scorer.

Tests range analysis - PROFILE-ONLY, no difficulty scoring.
Range difficulty is instrument-dependent.
"""

import pytest
from app.scoring.range_scorer import analyze_range_domain
from app.scoring.models import DomainResult


# =============================================================================
# TEST: BASIC FUNCTIONALITY
# =============================================================================

class TestRangeScorerBasics:
    """Test basic range scorer functionality."""
    
    def test_returns_domain_result(self):
        """Should return a DomainResult instance."""
        profile = {'span_semitones': 24, 'lowest_pitch': 'C4', 'highest_pitch': 'C6'}
        result = analyze_range_domain(profile)
        assert isinstance(result, DomainResult)
    
    def test_result_has_required_fields(self):
        """Result should have all required domain result fields."""
        profile = {'span_semitones': 12}
        result = analyze_range_domain(profile)
        
        assert hasattr(result, 'scores')
        assert hasattr(result, 'profile')
        assert hasattr(result, 'bands')
        assert hasattr(result, 'facet_scores')
        assert hasattr(result, 'flags')
    
    def test_handles_empty_profile(self):
        """Should handle empty profile."""
        result = analyze_range_domain({})
        assert isinstance(result, DomainResult)


# =============================================================================
# TEST: NO SCORING (INSTRUMENT-DEPENDENT)
# =============================================================================

class TestNoScoring:
    """Range scorer returns null scores - scoring requires instrument context."""
    
    def test_scores_are_null(self):
        """All scores should be null - requires instrument context."""
        profile = {'span_semitones': 24, 'tessitura_span': 18}
        result = analyze_range_domain(profile)
        
        assert result.scores['primary'] is None
        assert result.scores['hazard'] is None
        assert result.scores['overall'] is None
    
    def test_bands_are_null(self):
        """All bands should be null - requires instrument context."""
        profile = {'span_semitones': 24}
        result = analyze_range_domain(profile)
        
        for key, value in result.bands.items():
            assert value is None, f"Band {key} should be None"
    
    def test_zero_confidence(self):
        """Confidence should be zero - cannot score without instrument."""
        profile = {'span_semitones': 24}
        result = analyze_range_domain(profile)
        
        assert result.confidence == 0.0
    
    def test_flags_requires_instrument_context(self):
        """Should flag that instrument context is required."""
        profile = {'span_semitones': 12}
        result = analyze_range_domain(profile)
        
        assert 'requires_instrument_context' in result.flags


# =============================================================================
# TEST: FACET SCORES
# =============================================================================

class TestFacetScores:
    """Test facet score calculations."""
    
    def test_has_span_breadth_facet(self):
        """Result should have span_breadth facet."""
        profile = {'span_semitones': 24}
        result = analyze_range_domain(profile)
        
        assert 'span_breadth' in result.facet_scores
    
    def test_span_breadth_scales_with_span(self):
        """Span breadth should increase with span_semitones."""
        narrow = analyze_range_domain({'span_semitones': 7})
        wide = analyze_range_domain({'span_semitones': 36})
        
        assert wide.facet_scores['span_breadth'] > narrow.facet_scores['span_breadth']
    
    def test_span_breadth_in_range(self):
        """Span breadth should be in [0, 1] range."""
        profile = {'span_semitones': 24}
        result = analyze_range_domain(profile)
        
        span_breadth = result.facet_scores['span_breadth']
        assert 0 <= span_breadth <= 1
    
    def test_span_breadth_none_when_no_span(self):
        """Span breadth should be None when span_semitones not provided."""
        profile = {}
        result = analyze_range_domain(profile)
        
        assert result.facet_scores['span_breadth'] is None


# =============================================================================
# TEST: FLAGS
# =============================================================================

class TestFlags:
    """Test flag generation."""
    
    def test_wide_range_flag(self):
        """Should flag when range > 2 octaves."""
        profile = {'span_semitones': 25}  # > 24
        result = analyze_range_domain(profile)
        
        assert 'wide_range' in result.flags
    
    def test_very_wide_range_flag(self):
        """Should flag when range > 3 octaves."""
        profile = {'span_semitones': 37}  # > 36
        result = analyze_range_domain(profile)
        
        assert 'very_wide_range' in result.flags
    
    def test_narrow_range_no_flag(self):
        """Should not flag narrow ranges."""
        profile = {'span_semitones': 12}
        result = analyze_range_domain(profile)
        
        assert 'wide_range' not in result.flags
        assert 'very_wide_range' not in result.flags


# =============================================================================
# TEST: PROFILE PRESERVATION
# =============================================================================

class TestProfilePreservation:
    """Test that profile data is preserved for instrument comparison."""
    
    def test_preserves_lowest_pitch(self):
        """Should preserve lowest_pitch in result."""
        profile = {'lowest_pitch': 'C4', 'span_semitones': 24}
        result = analyze_range_domain(profile)
        
        assert result.profile.get('lowest_pitch') == 'C4'
    
    def test_preserves_highest_pitch(self):
        """Should preserve highest_pitch in result."""
        profile = {'highest_pitch': 'C6', 'span_semitones': 24}
        result = analyze_range_domain(profile)
        
        assert result.profile.get('highest_pitch') == 'C6'
    
    def test_preserves_tessitura_span(self):
        """Should preserve tessitura_span in result."""
        profile = {'tessitura_span': 18, 'span_semitones': 24}
        result = analyze_range_domain(profile)
        
        assert result.profile.get('tessitura_span') == 18


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_span(self):
        """Should handle zero span (single note)."""
        profile = {'span_semitones': 0}
        result = analyze_range_domain(profile)
        
        assert isinstance(result, DomainResult)
        assert result.facet_scores['span_breadth'] == 0 or result.facet_scores['span_breadth'] < 0.1
    
    def test_very_large_span(self):
        """Should handle very large spans."""
        profile = {'span_semitones': 72}  # 6 octaves
        result = analyze_range_domain(profile)
        
        assert isinstance(result, DomainResult)
        assert result.facet_scores['span_breadth'] <= 1.0
    
    def test_negative_span_handled(self):
        """Should handle negative span (shouldn't occur in practice)."""
        profile = {'span_semitones': -5}
        result = analyze_range_domain(profile)
        assert isinstance(result, DomainResult)
