"""
Tests for Scoring Functions and Stage Derivation

Uses relative validation (ordering expectations) rather than brittle exact numeric targets.
These tests verify that:
1. Harder inputs score higher than easier inputs
2. Stage derivation respects threshold boundaries
3. Interaction bonuses trigger at expected thresholds
"""

import pytest
from typing import Dict, Any

from app.scoring_functions import (
    interval_profile_to_scores,
    rhythm_profile_to_scores,
    tonal_profile_to_scores,
    tempo_profile_to_scores,
    range_profile_to_scores,
    throughput_profile_to_scores,
    analyze_range_domain,
    DomainScores,
    clamp,
    normalize_linear,
)
from app.stage_derivation import (
    score_to_stage,
    derive_domain_stages,
    derive_all_stages,
    get_stage_label,
    stage_to_score_range,
    DEFAULT_STAGE_THRESHOLDS,
)
from app.difficulty_interactions import (
    calculate_interaction_bonus,
    calculate_composite_difficulty,
    has_interaction_hazard,
    analyze_hazards,
    INTERACTION_CONFIG,
)


# =============================================================================
# UTILITY TESTS
# =============================================================================

class TestUtilities:
    """Test normalization utilities."""
    
    def test_clamp_within_range(self):
        assert clamp(0.5) == 0.5
        
    def test_clamp_below_min(self):
        assert clamp(-0.1) == 0.0
        
    def test_clamp_above_max(self):
        assert clamp(1.5) == 1.0
    
    def test_normalize_linear_middle(self):
        result = normalize_linear(5, 0, 10)
        assert result == 0.5
    
    def test_normalize_linear_low(self):
        result = normalize_linear(0, 0, 10)
        assert result == 0.0
    
    def test_normalize_linear_high(self):
        result = normalize_linear(10, 0, 10)
        assert result == 1.0
    
    def test_normalize_linear_beyond_high(self):
        result = normalize_linear(15, 0, 10)
        assert result == 1.0


# =============================================================================
# INTERVAL SCORING TESTS
# =============================================================================

class TestIntervalScoring:
    """Test interval profile to scores conversion."""
    
    @pytest.fixture
    def easy_interval_profile(self) -> Dict[str, Any]:
        """Profile with small intervals."""
        return {
            'interval_p75': 2,   # Whole steps
            'interval_p90': 4,   # Minor thirds
            'interval_max': 7,   # Perfect fifth
            'large_leap_ratio': 0.0,
            'extreme_leap_ratio': 0.0,
            'max_large_leaps_in_window': 0,
        }
    
    @pytest.fixture
    def hard_interval_profile(self) -> Dict[str, Any]:
        """Profile with large intervals."""
        return {
            'interval_p75': 10,  # Large leaps
            'interval_p90': 15,  # Octave+
            'interval_max': 24,  # Two octaves
            'large_leap_ratio': 0.15,
            'extreme_leap_ratio': 0.05,
            'max_large_leaps_in_window': 4,
        }
    
    def test_easy_scores_lower_than_hard(self, easy_interval_profile, hard_interval_profile):
        """Easy profile should score lower than hard profile."""
        easy_scores = interval_profile_to_scores(easy_interval_profile)
        hard_scores = interval_profile_to_scores(hard_interval_profile)
        
        assert easy_scores['primary'] < hard_scores['primary']
        assert easy_scores['hazard'] < hard_scores['hazard']
        assert easy_scores['overall'] < hard_scores['overall']
    
    def test_scores_in_valid_range(self, easy_interval_profile):
        """All scores should be in [0, 1]."""
        scores = interval_profile_to_scores(easy_interval_profile)
        
        for key in ['primary', 'hazard', 'overall']:
            assert 0.0 <= scores[key] <= 1.0
    
    def test_empty_profile_returns_low_scores(self):
        """Empty/default profile should return low scores."""
        scores = interval_profile_to_scores({})
        
        assert scores['primary'] <= 0.2
        assert scores['hazard'] <= 0.2


# =============================================================================
# RHYTHM SCORING TESTS
# =============================================================================

class TestRhythmScoring:
    """Test rhythm profile to scores conversion."""
    
    @pytest.fixture
    def predictable_rhythm_profile(self) -> Dict[str, Any]:
        """Profile with repetitive rhythm patterns."""
        return {
            'rhythm_measure_uniqueness_ratio': 0.15,  # Very repetitive
            'rhythm_measure_repetition_ratio': 0.85,
            'tuplet_ratio': 0.0,
            'dot_ratio': 0.05,
            'tie_ratio': 0.02,
            'syncopation_ratio': 0.0,
            'shortest_duration_ql': 1.0,  # Quarter notes
        }
    
    @pytest.fixture
    def unpredictable_rhythm_profile(self) -> Dict[str, Any]:
        """Profile with irregular rhythm patterns."""
        return {
            'rhythm_measure_uniqueness_ratio': 0.75,  # Very irregular
            'rhythm_measure_repetition_ratio': 0.25,
            'tuplet_ratio': 0.15,
            'dot_ratio': 0.20,
            'tie_ratio': 0.10,
            'syncopation_ratio': 0.25,
            'shortest_duration_ql': 0.25,  # 16th notes
        }
    
    def test_predictable_scores_lower_than_unpredictable(
        self, predictable_rhythm_profile, unpredictable_rhythm_profile
    ):
        """Predictable rhythm should score lower than unpredictable."""
        easy_scores = rhythm_profile_to_scores(predictable_rhythm_profile)
        hard_scores = rhythm_profile_to_scores(unpredictable_rhythm_profile)
        
        assert easy_scores['primary'] < hard_scores['primary']
        assert easy_scores['overall'] < hard_scores['overall']
    
    def test_uniqueness_ratio_impacts_primary(self):
        """Higher uniqueness ratio should increase primary score."""
        low_unique = rhythm_profile_to_scores({'rhythm_measure_uniqueness_ratio': 0.2})
        high_unique = rhythm_profile_to_scores({'rhythm_measure_uniqueness_ratio': 0.8})
        
        assert low_unique['primary'] < high_unique['primary']


# =============================================================================
# TONAL SCORING TESTS
# =============================================================================

class TestTonalScoring:
    """Test tonal profile to scores conversion."""
    
    def test_diatonic_scores_lower_than_chromatic(self):
        """Diatonic piece should score lower than chromatic."""
        diatonic = tonal_profile_to_scores({
            'pitch_class_count': 5,
            'accidental_rate': 0.0,
            'chromatic_ratio': 0.0,
        })
        chromatic = tonal_profile_to_scores({
            'pitch_class_count': 12,
            'accidental_rate': 0.35,
            'chromatic_ratio': 0.40,
        })
        
        assert diatonic['primary'] < chromatic['primary']
        assert diatonic['hazard'] < chromatic['hazard']


# =============================================================================
# TEMPO SCORING TESTS
# =============================================================================

class TestTempoScoring:
    """Test tempo profile to scores conversion."""
    
    def test_slow_scores_lower_than_fast(self):
        """Slow tempo should score lower than fast."""
        slow = tempo_profile_to_scores({'effective_bpm': 72, 'tempo_is_explicit': True})
        fast = tempo_profile_to_scores({'effective_bpm': 160, 'tempo_is_explicit': True})
        
        assert slow['primary'] < fast['primary']
    
    def test_stable_tempo_lower_hazard_than_volatile(self):
        """Stable tempo should have lower hazard than volatile."""
        stable = tempo_profile_to_scores({
            'effective_bpm': 120,
            'tempo_volatility': 0.0,
            'tempo_change_count': 0,
            'tempo_is_explicit': True,
        })
        volatile = tempo_profile_to_scores({
            'effective_bpm': 120,
            'tempo_volatility': 0.4,
            'tempo_change_count': 6,
            'has_accelerando': True,
            'has_ritardando': True,
            'tempo_is_explicit': True,
        })
        
        assert stable['hazard'] < volatile['hazard']


# =============================================================================
# RANGE SCORING TESTS
# =============================================================================

class TestRangeScoring:
    """Test range profile to scores conversion."""
    
    def test_range_returns_none_scores(self):
        """Range scoring requires instrument context - should return None."""
        result = range_profile_to_scores({
            'tessitura_span': 8,
            'span_semitones': 10,
        })
        # Range scoring deliberately returns None - requires instrument context
        assert result['primary'] is None
        assert result['hazard'] is None
        assert result['overall'] is None
    
    def test_wider_range_has_higher_span_breadth_facet(self):
        """Wider range should have higher span_breadth facet."""
        narrow = analyze_range_domain({'span_semitones': 10})
        wide = analyze_range_domain({'span_semitones': 30})
        
        # span_breadth is the only facet for range (no difficulty scoring)
        assert narrow.facet_scores['span_breadth'] < wide.facet_scores['span_breadth']


# =============================================================================
# THROUGHPUT SCORING TESTS
# =============================================================================

class TestThroughputScoring:
    """Test throughput (density) profile to scores conversion."""
    
    def test_sparse_scores_lower_than_dense(self):
        """Sparse note density should score lower than dense."""
        sparse = throughput_profile_to_scores({
            'notes_per_second': 1.5,
            'peak_notes_per_second': 2.0,
        })
        dense = throughput_profile_to_scores({
            'notes_per_second': 6.0,
            'peak_notes_per_second': 10.0,
        })
        
        assert sparse['primary'] < dense['primary']


# =============================================================================
# STAGE DERIVATION TESTS
# =============================================================================

class TestStageDeriavtion:
    """Test score to stage conversion."""
    
    def test_stage_boundaries(self):
        """Test that stages align with threshold boundaries."""
        # Just below each threshold
        assert score_to_stage(0.14) == 0
        assert score_to_stage(0.29) == 1
        assert score_to_stage(0.44) == 2
        assert score_to_stage(0.59) == 3
        assert score_to_stage(0.74) == 4
        assert score_to_stage(0.89) == 5
        
        # At or above maximum
        assert score_to_stage(0.90) == 6
        assert score_to_stage(1.0) == 6
    
    def test_stage_0_for_trivial(self):
        """Very low scores should map to stage 0."""
        assert score_to_stage(0.0) == 0
        assert score_to_stage(0.10) == 0
    
    def test_stage_6_for_extreme(self):
        """Very high scores should map to stage 6."""
        assert score_to_stage(0.95) == 6
        assert score_to_stage(1.0) == 6
    
    def test_clamping(self):
        """Out-of-range scores should be clamped."""
        assert score_to_stage(-0.5) == 0
        assert score_to_stage(1.5) == 6
    
    def test_stage_to_score_range(self):
        """Stage to score range should return correct bounds."""
        low, high = stage_to_score_range(3)
        assert low == 0.45
        assert high == 0.60
    
    def test_get_stage_label(self):
        """Stage labels should be human readable."""
        assert get_stage_label(0) == "Trivial"
        assert get_stage_label(3) == "Intermediate"
        assert get_stage_label(6) == "Expert"
    
    def test_get_stage_label_short(self):
        """Short labels should be Roman numerals."""
        assert get_stage_label(0, short=True) == "I"
        assert get_stage_label(3, short=True) == "IV"


# =============================================================================
# INTERACTION TESTS
# =============================================================================

class TestDifficultyInteractions:
    """Test domain interaction calculations."""
    
    @pytest.fixture
    def no_interaction_scores(self) -> Dict[str, Dict[str, float]]:
        """Scores that should not trigger interactions."""
        return {
            'interval': {'primary': 0.30, 'hazard': 0.25, 'overall': 0.28},
            'rhythm': {'primary': 0.35, 'hazard': 0.30, 'overall': 0.33},
        }
    
    @pytest.fixture
    def high_interaction_scores(self) -> Dict[str, Dict[str, float]]:
        """Scores that should trigger interval+rhythm interaction."""
        return {
            'interval': {'primary': 0.70, 'hazard': 0.75, 'overall': 0.72},
            'rhythm': {'primary': 0.65, 'hazard': 0.60, 'overall': 0.63},
        }
    
    def test_no_bonus_below_threshold(self, no_interaction_scores):
        """Low scores should not trigger interaction bonus."""
        result = calculate_interaction_bonus(no_interaction_scores)
        assert result.bonus == 0.0
        assert len(result.flags) == 0
    
    def test_bonus_above_threshold(self, high_interaction_scores):
        """High scores should trigger interaction bonus."""
        result = calculate_interaction_bonus(high_interaction_scores)
        assert result.bonus > 0.0
        assert 'high_leap_rhythm_combo' in result.flags
    
    def test_bonus_capped(self):
        """Interaction bonus should be capped at maximum."""
        # All domains high to trigger multiple interactions
        all_high = {
            'interval': {'primary': 0.80, 'hazard': 0.85, 'overall': 0.82},
            'rhythm': {'primary': 0.80, 'hazard': 0.75, 'overall': 0.78},
            'tempo': {'primary': 0.80, 'hazard': 0.70, 'overall': 0.76},
            'throughput': {'primary': 0.80, 'hazard': 0.75, 'overall': 0.78},
        }
        result = calculate_interaction_bonus(all_high)
        assert result.bonus <= 0.15
    
    def test_has_interaction_hazard(self, no_interaction_scores, high_interaction_scores):
        """has_interaction_hazard should correctly identify hazards."""
        assert not has_interaction_hazard(no_interaction_scores)
        assert has_interaction_hazard(high_interaction_scores)


class TestCompositeScoring:
    """Test composite difficulty calculation."""
    
    def test_composite_includes_weighted_sum(self):
        """Composite should include weighted domain sum."""
        scores = {
            'rhythm': {'primary': 0.50, 'hazard': 0.40, 'overall': 0.46},
            'interval': {'primary': 0.40, 'hazard': 0.35, 'overall': 0.38},
        }
        result = calculate_composite_difficulty(scores)
        assert 'weighted_sum' in result
        assert 0.0 <= result['weighted_sum'] <= 1.0
    
    def test_composite_includes_interaction_bonus(self):
        """Composite should include interaction bonus when enabled."""
        # High scores to trigger interaction
        scores = {
            'interval': {'primary': 0.70, 'hazard': 0.75, 'overall': 0.72},
            'rhythm': {'primary': 0.65, 'hazard': 0.60, 'overall': 0.63},
        }
        with_interactions = calculate_composite_difficulty(scores, include_interactions=True)
        without_interactions = calculate_composite_difficulty(scores, include_interactions=False)
        
        assert with_interactions['interaction_bonus'] > 0
        assert without_interactions['interaction_bonus'] == 0
        assert with_interactions['overall'] > without_interactions['overall']
    
    def test_composite_overall_capped_at_one(self):
        """Composite overall should never exceed 1.0."""
        extreme_scores = {
            'interval': {'primary': 0.95, 'hazard': 0.98, 'overall': 0.96},
            'rhythm': {'primary': 0.95, 'hazard': 0.90, 'overall': 0.93},
            'tempo': {'primary': 0.95, 'hazard': 0.85, 'overall': 0.91},
        }
        result = calculate_composite_difficulty(extreme_scores)
        assert result['overall'] <= 1.0


# =============================================================================
# HAZARD ANALYSIS TESTS
# =============================================================================

class TestHazardAnalysis:
    """Test hazard identification."""
    
    def test_identifies_high_domain_hazards(self):
        """Should identify domains with high hazard scores."""
        scores = {
            'interval': {'primary': 0.50, 'hazard': 0.85, 'overall': 0.60},
            'rhythm': {'primary': 0.40, 'hazard': 0.30, 'overall': 0.36},
        }
        hazards = analyze_hazards(scores)
        
        assert len(hazards['domain_hazards']) == 1
        assert hazards['domain_hazards'][0]['domain'] == 'interval'
    
    def test_identifies_ability_gaps(self):
        """Should identify when piece exceeds student ability."""
        piece_scores = {
            'interval': {'primary': 0.50, 'hazard': 0.70, 'overall': 0.55},
            'rhythm': {'primary': 0.40, 'hazard': 0.35, 'overall': 0.38},
        }
        student_scores = {
            'interval': 0.45,  # Student below piece hazard
            'rhythm': 0.50,   # Student above piece hazard
        }
        hazards = analyze_hazards(piece_scores, student_scores)
        
        # Should flag interval as hazardous (0.70 > 0.45 + 0.15)
        assert len(hazards['ability_hazards']) == 1
        assert hazards['ability_hazards'][0]['domain'] == 'interval'


# =============================================================================
# FACET-AWARE DOMAIN RESULT TESTS
# =============================================================================

from app.scoring_functions import (
    analyze_interval_domain,
    analyze_rhythm_domain,
    analyze_tonal_domain,
    analyze_tempo_domain,
    analyze_range_domain,
    analyze_throughput_domain,
    analyze_all_domains,
    DomainResult,
)


class TestFacetAwareDomainResults:
    """Test the facet-aware DomainResult structure."""
    
    def test_interval_returns_complete_structure(self):
        """Interval analysis should return all required fields."""
        profile = {
            'interval_p50': 2,
            'interval_p75': 5,
            'interval_p90': 9,
            'interval_max': 15,
            'step_ratio': 0.65,
            'large_leap_ratio': 0.04,
            'max_large_leaps_in_window': 2,
        }
        result = analyze_interval_domain(profile)
        
        # Verify structure
        assert isinstance(result, DomainResult)
        assert 'profile' in result.to_dict()
        assert 'facet_scores' in result.to_dict()
        assert 'scores' in result.to_dict()
        assert 'bands' in result.to_dict()
        assert 'flags' in result.to_dict()
        assert 'confidence' in result.to_dict()
        
    def test_interval_facet_scores_present(self):
        """Interval should have all expected facet scores."""
        profile = {'interval_p75': 5, 'interval_p90': 9, 'interval_max': 15}
        result = analyze_interval_domain(profile)
        
        facets = result.facet_scores
        assert 'step_skip_complexity' in facets
        assert 'sustained_leap_complexity' in facets
        assert 'extreme_leap_hazard' in facets
        assert 'clustered_leap_hazard' in facets
    
    def test_rhythm_facet_scores_present(self):
        """Rhythm should have all expected facet scores."""
        profile = {
            'shortest_duration': 0.25,
            'rhythm_measure_uniqueness_ratio': 0.5,
            'syncopation_ratio': 0.1,
        }
        result = analyze_rhythm_domain(profile)
        
        facets = result.facet_scores
        assert 'subdivision_complexity' in facets
        assert 'syncopation_complexity' in facets
        assert 'tuplet_complexity' in facets
        assert 'dot_tie_complexity' in facets
        assert 'pattern_novelty' in facets
    
    def test_tonal_facet_scores_present(self):
        """Tonal should have all expected facet scores."""
        profile = {'pitch_class_count': 7, 'accidental_rate': 0.1}
        result = analyze_tonal_domain(profile)
        
        facets = result.facet_scores
        # Note: diatonic_complexity was removed - pitch_class_count is not meaningful
        assert 'chromatic_complexity' in facets
        assert 'accidental_load' in facets
        assert 'tonal_instability' in facets
    
    def test_tempo_facet_scores_present(self):
        """Tempo should have all expected facet scores."""
        profile = {'effective_bpm': 120, 'tempo_change_count': 2}
        result = analyze_tempo_domain(profile)
        
        facets = result.facet_scores
        assert 'speed_demand' in facets
        assert 'tempo_control_demand' in facets
        assert 'tempo_variability' in facets
    
    def test_range_facet_scores_present(self):
        """Range should have all expected facet scores."""
        profile = {'span_semitones': 20, 'tessitura_span': 15}
        result = analyze_range_domain(profile)
        
        facets = result.facet_scores
        # Range only produces span_breadth - other facets require instrument context
        assert 'span_breadth' in facets
    
    def test_throughput_facet_scores_present(self):
        """Throughput should have all expected facet scores."""
        profile = {'notes_per_second': 3.0, 'peak_notes_per_second': 6.0}
        result = analyze_throughput_domain(profile)
        
        facets = result.facet_scores
        assert 'sustained_density' in facets
        assert 'peak_density' in facets
        assert 'adaptation_pressure' in facets  # renamed from variability_pressure
    
    def test_bands_derived_from_scores(self):
        """Bands should be correctly derived from scores."""
        profile = {'interval_p75': 5, 'interval_p90': 9, 'interval_max': 20}
        result = analyze_interval_domain(profile)
        
        # Bands should match score-to-stage conversion
        bands = result.bands
        scores = result.scores
        assert bands['primary_stage'] == score_to_stage(scores['primary'])
        assert bands['hazard_stage'] == score_to_stage(scores['hazard'])
        assert bands['overall_stage'] == score_to_stage(scores['overall'])
    
    def test_facet_ordering_interval(self):
        """Harder intervals should produce higher facet scores."""
        easy = analyze_interval_domain({'interval_p75': 2, 'interval_p90': 4})
        hard = analyze_interval_domain({'interval_p75': 10, 'interval_p90': 15})
        
        assert easy.facet_scores['step_skip_complexity'] < hard.facet_scores['step_skip_complexity']
        assert easy.facet_scores['sustained_leap_complexity'] < hard.facet_scores['sustained_leap_complexity']
    
    def test_facet_ordering_rhythm(self):
        """More complex rhythms should produce higher facet scores."""
        simple = analyze_rhythm_domain({
            'shortest_duration': 0.5,  # Eighth notes
            'rhythm_measure_uniqueness_ratio': 0.2,
        })
        complex_ = analyze_rhythm_domain({
            'shortest_duration': 0.125,  # 32nd notes
            'rhythm_measure_uniqueness_ratio': 0.8,
        })
        
        assert simple.facet_scores['subdivision_complexity'] < complex_.facet_scores['subdivision_complexity']
        assert simple.facet_scores['pattern_novelty'] < complex_.facet_scores['pattern_novelty']
    
    def test_confidence_reflects_data_quality(self):
        """Confidence should be lower when data is missing."""
        # Tempo without explicit marking should have lower confidence
        no_bpm = analyze_tempo_domain({})
        with_bpm = analyze_tempo_domain({
            'base_bpm': 120, 
            'effective_bpm': 120,
            'tempo_is_explicit': True,
        })
        
        assert no_bpm.confidence < with_bpm.confidence
    
    def test_flags_generated_for_hazards(self):
        """Should generate flags for detected hazards."""
        # Profile with extreme intervals
        extreme = analyze_interval_domain({
            'interval_max': 30,
            'extreme_leap_ratio': 0.1,
        })
        
        assert 'extreme_intervals_present' in extreme.flags
    
    def test_analyze_all_domains_returns_all_results(self):
        """analyze_all_domains should populate all present domains."""
        profiles = {
            'interval': {'interval_p75': 5},
            'rhythm': {'shortest_duration': 0.25},
            'tonal': {'pitch_class_count': 7},
        }
        results = analyze_all_domains(profiles)
        
        assert results.interval is not None
        assert results.rhythm is not None
        assert results.tonal is not None
        assert results.tempo is None  # Not in profiles
        
    def test_to_dict_serialization(self):
        """DomainResult should serialize to dict correctly."""
        result = analyze_interval_domain({'interval_p75': 5})
        d = result.to_dict()
        
        assert isinstance(d, dict)
        assert isinstance(d['profile'], dict)
        assert isinstance(d['facet_scores'], dict)
        assert isinstance(d['scores'], dict)
        assert isinstance(d['bands'], dict)
        assert isinstance(d['flags'], list)
        assert isinstance(d['confidence'], float)

