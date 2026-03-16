"""
Tests for Unified Domain Score Calculator.

Tests the bridge from SoftGateMetrics to facet-aware scoring schema.
"""

import pytest
from app.calculators.unified_calculator import calculate_unified_domain_scores
from app.calculators.models import (
    SoftGateMetrics,
    IntervalProfile,
    IntervalLocalDifficulty,
)
from app.scoring.models import DomainResult


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def basic_metrics():
    """Create basic SoftGateMetrics for testing."""
    return SoftGateMetrics(
        tonal_complexity_stage=2,
        interval_size_stage=3,
        rhythm_complexity_score=0.4,
        range_usage_stage=2,
        interval_sustained_stage=3,
        interval_hazard_stage=3,
        legacy_interval_size_stage=3,
        interval_profile=IntervalProfile(
            total_intervals=100,
            step_ratio=0.6,
            skip_ratio=0.25,
            leap_ratio=0.10,
            large_leap_ratio=0.04,
            extreme_leap_ratio=0.01,
            interval_p50=2,
            interval_p75=4,
            interval_p90=7,
            interval_max=12,
        ),
        interval_local_difficulty=IntervalLocalDifficulty(
            max_large_leaps_in_window=2,
            max_extreme_leaps_in_window=1,
            hardest_measure_numbers=[4, 8, 12],
            window_count=10,
        ),
        density_notes_per_second=3.0,
        note_density_per_measure=12.0,
        peak_notes_per_second=5.0,
        throughput_volatility=0.2,
    )


@pytest.fixture
def metrics_with_raw():
    """Create SoftGateMetrics with raw_metrics dict."""
    metrics = SoftGateMetrics(
        tonal_complexity_stage=2,
        interval_size_stage=3,
        rhythm_complexity_score=0.4,
        range_usage_stage=2,
        density_notes_per_second=3.0,
        note_density_per_measure=12.0,
        peak_notes_per_second=5.0,
        throughput_volatility=0.2,
    )
    metrics.raw_metrics = {
        'd1': {
            'pitch_class_count': 7,
            'accidental_rate': 0.1,
        },
        'd3': {
            'f2': 0.3,  # rhythm uniqueness
            'f4': 0.2,  # irregular features
        },
    }
    metrics.unique_pitch_count = 7
    return metrics


# =============================================================================
# TEST: BASIC FUNCTIONALITY
# =============================================================================

class TestUnifiedCalculatorBasics:
    """Test basic unified calculator functionality."""
    
    def test_returns_dict_of_domain_results(self, basic_metrics):
        """Should return dict mapping domain names to DomainResults."""
        results = calculate_unified_domain_scores(basic_metrics)
        
        assert isinstance(results, dict)
        assert len(results) > 0
    
    def test_includes_all_expected_domains(self, basic_metrics):
        """Should include all expected domain results."""
        results = calculate_unified_domain_scores(basic_metrics)
        
        expected_domains = ['interval', 'rhythm', 'tonal', 'tempo', 'range', 'throughput', 'pattern']
        for domain in expected_domains:
            assert domain in results, f"Missing domain: {domain}"
    
    def test_each_result_is_domain_result(self, basic_metrics):
        """Each result should be a DomainResult instance."""
        results = calculate_unified_domain_scores(basic_metrics)
        
        for domain, result in results.items():
            assert isinstance(result, DomainResult), f"{domain} is not DomainResult"


# =============================================================================
# TEST: INTERVAL DOMAIN
# =============================================================================

class TestIntervalDomain:
    """Test interval domain calculation."""
    
    def test_interval_uses_profile_data(self, basic_metrics):
        """Interval result should be based on interval profile."""
        results = calculate_unified_domain_scores(basic_metrics)
        
        interval = results['interval']
        assert interval.scores['primary'] is not None
        # High step ratio should result in lower complexity
        assert interval.scores['primary'] < 0.5
    
    def test_interval_handles_missing_profile(self):
        """Should handle missing interval profile gracefully."""
        metrics = SoftGateMetrics(
            tonal_complexity_stage=2,
            interval_size_stage=0,
            rhythm_complexity_score=0.3,
            range_usage_stage=1,
            interval_profile=None,
            interval_local_difficulty=None,
            density_notes_per_second=2.0,
            note_density_per_measure=8.0,
            peak_notes_per_second=3.0,
            throughput_volatility=0.1,
        )
        results = calculate_unified_domain_scores(metrics)
        
        assert 'interval' in results
        assert results['interval'] is not None


# =============================================================================
# TEST: RHYTHM DOMAIN
# =============================================================================

class TestRhythmDomain:
    """Test rhythm domain calculation."""
    
    def test_rhythm_uses_complexity_score(self, basic_metrics):
        """Rhythm result should incorporate rhythm_complexity_score."""
        results = calculate_unified_domain_scores(basic_metrics)
        
        rhythm = results['rhythm']
        assert rhythm.scores['primary'] is not None
    
    def test_rhythm_with_extraction_data(self, basic_metrics):
        """Should use extraction data when available."""
        extraction = {
            'note_values': {'quarter': 50, 'eighth': 30, 'sixteenth': 20},
            'tuplets': {'triplet': 5},
            'dotted_notes': ['note1', 'note2', 'note3'],
            'has_ties': True,
            'rhythm_measure_uniqueness_ratio': 0.4,
        }
        results = calculate_unified_domain_scores(basic_metrics, extraction=extraction)
        
        rhythm = results['rhythm']
        assert rhythm is not None
        # With sixteenth notes, complexity should be moderate
        assert rhythm.facet_scores['subdivision_complexity'] > 0
    
    def test_rhythm_falls_back_to_raw_metrics(self, metrics_with_raw):
        """Should fall back to raw_metrics if extraction not available."""
        results = calculate_unified_domain_scores(metrics_with_raw)
        
        rhythm = results['rhythm']
        assert rhythm is not None


# =============================================================================
# TEST: TONAL DOMAIN
# =============================================================================

class TestTonalDomain:
    """Test tonal domain calculation."""
    
    def test_tonal_uses_raw_metrics(self, metrics_with_raw):
        """Tonal result should use raw_metrics d1 data."""
        results = calculate_unified_domain_scores(metrics_with_raw)
        
        tonal = results['tonal']
        assert tonal.scores['primary'] is not None
        # Accidental rate of 0.1 should give some complexity
        assert tonal.facet_scores['accidental_load'] > 0
    
    def test_tonal_handles_no_raw_metrics(self, basic_metrics):
        """Should handle missing raw_metrics."""
        results = calculate_unified_domain_scores(basic_metrics)
        
        assert 'tonal' in results
        assert results['tonal'] is not None


# =============================================================================
# TEST: TEMPO DOMAIN
# =============================================================================

class TestTempoDomain:
    """Test tempo domain calculation."""
    
    def test_tempo_with_explicit_marking(self, basic_metrics):
        """Should use tempo profile when provided."""
        tempo_profile = {
            'base_bpm': 120,
            'effective_bpm': 120,
            'primary_source_type': 'metronome_marking',
        }
        results = calculate_unified_domain_scores(basic_metrics, tempo_profile=tempo_profile)
        
        tempo = results['tempo']
        assert tempo.scores['primary'] is not None
        # 120 BPM is moderate
        assert 0.3 < tempo.facet_scores['speed_demand'] < 0.7
    
    def test_tempo_with_default_source(self, basic_metrics):
        """Tempo with default source should flag no explicit marking."""
        tempo_profile = {
            'base_bpm': 120,
            'effective_bpm': 120,
            'primary_source_type': 'default',
        }
        results = calculate_unified_domain_scores(basic_metrics, tempo_profile=tempo_profile)
        
        tempo = results['tempo']
        assert 'no_tempo_marking' in tempo.flags
    
    def test_tempo_without_profile(self, basic_metrics):
        """Should handle missing tempo profile."""
        results = calculate_unified_domain_scores(basic_metrics, tempo_profile=None)
        
        assert 'tempo' in results
        # No explicit tempo
        assert results['tempo'].scores['primary'] is None


# =============================================================================
# TEST: RANGE DOMAIN
# =============================================================================

class TestRangeDomain:
    """Test range domain calculation."""
    
    def test_range_with_analysis(self, basic_metrics):
        """Should use range analysis when provided."""
        range_analysis = {
            'range_semitones': 24,  # 2 octaves
            'lowest_pitch': 'C4',
            'highest_pitch': 'C6',
        }
        results = calculate_unified_domain_scores(basic_metrics, range_analysis=range_analysis)
        
        range_result = results['range']
        assert range_result.facet_scores['span_breadth'] is not None
        # 24 semitones is between narrow and wide
        assert 0.3 < range_result.facet_scores['span_breadth'] < 0.8
    
    def test_range_requires_instrument_context(self, basic_metrics):
        """Range should flag that instrument context is required."""
        results = calculate_unified_domain_scores(basic_metrics)
        
        range_result = results['range']
        assert 'requires_instrument_context' in range_result.flags


# =============================================================================
# TEST: THROUGHPUT DOMAIN
# =============================================================================

class TestThroughputDomain:
    """Test throughput domain calculation."""
    
    def test_throughput_uses_metrics(self, basic_metrics):
        """Should use density metrics from SoftGateMetrics."""
        results = calculate_unified_domain_scores(basic_metrics)
        
        throughput = results['throughput']
        assert throughput.scores['primary'] is not None
        # 3.0 NPS is moderate
        assert throughput.facet_scores['sustained_density'] > 0
    
    def test_throughput_captures_peak(self, basic_metrics):
        """Should capture peak NPS for hazard."""
        results = calculate_unified_domain_scores(basic_metrics)
        
        throughput = results['throughput']
        # Peak and sustained are normalized on different scales
        # Just ensure both are captured
        assert throughput.facet_scores['peak_density'] is not None
        assert throughput.facet_scores['sustained_density'] is not None


# =============================================================================
# TEST: PATTERN DOMAIN
# =============================================================================

class TestPatternDomain:
    """Test pattern domain calculation."""
    
    def test_pattern_with_extraction(self, basic_metrics):
        """Should use melodic pattern analysis from extraction."""
        extraction = {
            'melodic_pattern_analysis': {
                'total_motifs': 20,
                'unique_motifs': 8,
                'motif_uniqueness_ratio': 0.4,
                'motif_repetition_ratio': 0.6,
                'sequence_count': 3,
                'sequence_coverage_ratio': 0.25,
            },
            'rhythm_measure_uniqueness_ratio': 0.3,
        }
        results = calculate_unified_domain_scores(basic_metrics, extraction=extraction)
        
        pattern = results['pattern']
        assert pattern.scores['primary'] is not None
        # With 60% repetition, predictability should be moderate-high
        assert pattern.facet_scores['melodic_predictability'] >= 0.5
    
    def test_pattern_without_extraction(self, basic_metrics):
        """Should handle missing extraction data."""
        results = calculate_unified_domain_scores(basic_metrics, extraction=None)
        
        assert 'pattern' in results
        assert results['pattern'] is not None


# =============================================================================
# TEST: INTEGRATION
# =============================================================================

class TestIntegration:
    """Test integration scenarios."""
    
    def test_all_domains_have_valid_scores(self, basic_metrics):
        """All domains should produce valid (or intentionally null) scores."""
        results = calculate_unified_domain_scores(basic_metrics)
        
        for domain, result in results.items():
            # Scores should be dict
            assert isinstance(result.scores, dict)
            # If primary is not None, it should be in [0, 1]
            if result.scores['primary'] is not None:
                assert 0 <= result.scores['primary'] <= 1
    
    def test_with_all_optional_data(self, basic_metrics):
        """Should handle all optional parameters together."""
        tempo_profile = {'base_bpm': 140, 'effective_bpm': 140, 'primary_source_type': 'metronome_marking'}
        range_analysis = {'range_semitones': 30, 'lowest_pitch': 'G3', 'highest_pitch': 'C6'}
        extraction = {
            'note_values': {'quarter': 40, 'eighth': 40, '16th': 20},
            'melodic_pattern_analysis': {'motif_repetition_ratio': 0.7},
        }
        
        results = calculate_unified_domain_scores(
            basic_metrics,
            tempo_profile=tempo_profile,
            range_analysis=range_analysis,
            extraction=extraction,
        )
        
        assert len(results) == 7
        for domain, result in results.items():
            assert result is not None


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_minimal_metrics(self):
        """Should handle minimal SoftGateMetrics."""
        metrics = SoftGateMetrics(
            tonal_complexity_stage=0,
            interval_size_stage=0,
            rhythm_complexity_score=0.0,
            range_usage_stage=0,
            density_notes_per_second=0.0,
            note_density_per_measure=0.0,
            peak_notes_per_second=0.0,
            throughput_volatility=0.0,
        )
        results = calculate_unified_domain_scores(metrics)
        
        assert isinstance(results, dict)
        assert len(results) == 7
    
    def test_empty_extraction(self, basic_metrics):
        """Should handle empty extraction dict."""
        results = calculate_unified_domain_scores(basic_metrics, extraction={})
        
        assert isinstance(results, dict)
        assert len(results) == 7
