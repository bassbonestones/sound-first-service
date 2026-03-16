"""
Tests for Throughput Calculator.

Tests D5 — Density metrics (notes per second, per measure, peak, volatility)
and tempo difficulty score calculation.
"""

import pytest
from app.calculators.throughput_calculator import (
    calculate_density_metrics,
    calculate_tempo_difficulty_score,
)


# =============================================================================
# TEST: DENSITY METRICS
# =============================================================================

class TestDensityMetrics:
    """Test density metrics calculation."""
    
    def test_returns_tuple(self):
        """Should return 5-tuple."""
        result = calculate_density_metrics(
            total_notes=100,
            duration_seconds=30.0,
            measure_count=10,
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 5
    
    def test_notes_per_second_calculation(self):
        """Should correctly calculate notes per second."""
        nps, npm, peak, vol, raw = calculate_density_metrics(
            total_notes=120,
            duration_seconds=60.0,
            measure_count=20,
        )
        
        assert nps == 2.0  # 120 notes / 60 seconds
    
    def test_notes_per_measure_calculation(self):
        """Should correctly calculate notes per measure."""
        nps, npm, peak, vol, raw = calculate_density_metrics(
            total_notes=100,
            duration_seconds=30.0,
            measure_count=25,
        )
        
        assert npm == 4.0  # 100 notes / 25 measures
    
    def test_handles_zero_duration(self):
        """Should handle zero duration."""
        nps, npm, peak, vol, raw = calculate_density_metrics(
            total_notes=100,
            duration_seconds=0.0,
            measure_count=10,
        )
        
        assert nps == 0
    
    def test_handles_zero_measure_count(self):
        """Should handle zero measure count."""
        nps, npm, peak, vol, raw = calculate_density_metrics(
            total_notes=100,
            duration_seconds=30.0,
            measure_count=0,
        )
        
        assert npm == 0
    
    def test_peak_nps_with_measure_list(self):
        """Should calculate peak NPS from per-measure data."""
        nps, npm, peak, vol, raw = calculate_density_metrics(
            total_notes=40,
            duration_seconds=20.0,
            measure_count=10,
            notes_per_measure_list=[2, 4, 6, 8, 10, 4, 2, 2, 1, 1],  # Peak at measure 5 with 10 notes
            tempo_bpm=120,
            beats_per_measure=4.0,
        )
        
        # Peak should be higher than average
        assert peak >= nps
    
    def test_volatility_calculation(self):
        """Should calculate volatility (coefficient of variation)."""
        # High variance case
        nps1, npm1, peak1, vol1, raw1 = calculate_density_metrics(
            total_notes=40,
            duration_seconds=20.0,
            measure_count=10,
            notes_per_measure_list=[1, 10, 1, 10, 1, 10, 1, 10, 1, 10],  # Alternating
            tempo_bpm=120,
            beats_per_measure=4.0,
        )
        
        # Low variance case
        nps2, npm2, peak2, vol2, raw2 = calculate_density_metrics(
            total_notes=40,
            duration_seconds=20.0,
            measure_count=10,
            notes_per_measure_list=[4, 4, 4, 4, 4, 4, 4, 4, 4, 4],  # Uniform
            tempo_bpm=120,
            beats_per_measure=4.0,
        )
        
        # High variance should have higher volatility
        assert vol1 > vol2
    
    def test_no_measure_list_uses_average(self):
        """Without measure list, peak should equal average."""
        nps, npm, peak, vol, raw = calculate_density_metrics(
            total_notes=100,
            duration_seconds=50.0,
            measure_count=10,
        )
        
        assert peak == pytest.approx(nps, rel=0.01)
        assert vol == 0.0
    
    def test_raw_metrics_included(self):
        """Should include raw metrics in result."""
        nps, npm, peak, vol, raw = calculate_density_metrics(
            total_notes=100,
            duration_seconds=30.0,
            measure_count=10,
        )
        
        assert 'total_notes' in raw
        assert 'duration_seconds' in raw
        assert 'measure_count' in raw
        assert 'peak_nps' in raw
        assert 'volatility' in raw


# =============================================================================
# TEST: TEMPO DIFFICULTY SCORE
# =============================================================================

class TestTempoDifficultyScore:
    """Test tempo difficulty score calculation."""
    
    def test_returns_tuple(self):
        """Should return (score, raw_dict) tuple."""
        result = calculate_tempo_difficulty_score(
            bpm=120,
            rhythm_complexity=0.5,
            interval_velocity=0.5,
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 2
    
    def test_score_in_range(self):
        """Score should be in [0, 1] range."""
        score, _ = calculate_tempo_difficulty_score(
            bpm=140,
            rhythm_complexity=0.6,
            interval_velocity=0.7,
        )
        
        assert 0 <= score <= 1
    
    def test_none_bpm_returns_none(self):
        """None BPM should return None score."""
        score, raw = calculate_tempo_difficulty_score(
            bpm=None,
            rhythm_complexity=0.5,
            interval_velocity=0.5,
        )
        
        assert score is None
        assert 'reason' in raw
    
    def test_higher_bpm_increases_score(self):
        """Higher BPM should increase score."""
        slow_score, _ = calculate_tempo_difficulty_score(
            bpm=60,
            rhythm_complexity=0.5,
            interval_velocity=0.5,
        )
        fast_score, _ = calculate_tempo_difficulty_score(
            bpm=180,
            rhythm_complexity=0.5,
            interval_velocity=0.5,
        )
        
        assert fast_score > slow_score
    
    def test_higher_rhythm_complexity_increases_score(self):
        """Higher rhythm complexity should increase score."""
        simple_score, _ = calculate_tempo_difficulty_score(
            bpm=120,
            rhythm_complexity=0.2,
            interval_velocity=0.5,
        )
        complex_score, _ = calculate_tempo_difficulty_score(
            bpm=120,
            rhythm_complexity=0.8,
            interval_velocity=0.5,
        )
        
        assert complex_score > simple_score
    
    def test_higher_interval_velocity_increases_score(self):
        """Higher interval velocity should increase score."""
        slow_score, _ = calculate_tempo_difficulty_score(
            bpm=120,
            rhythm_complexity=0.5,
            interval_velocity=0.2,
        )
        fast_score, _ = calculate_tempo_difficulty_score(
            bpm=120,
            rhythm_complexity=0.5,
            interval_velocity=0.8,
        )
        
        assert fast_score > slow_score
    
    def test_zero_complexity_gives_zero(self):
        """Zero rhythm complexity should give zero score."""
        score, _ = calculate_tempo_difficulty_score(
            bpm=180,
            rhythm_complexity=0.0,
            interval_velocity=0.5,
        )
        
        assert score == 0.0
    
    def test_zero_velocity_gives_zero(self):
        """Zero interval velocity should give zero score."""
        score, _ = calculate_tempo_difficulty_score(
            bpm=180,
            rhythm_complexity=0.5,
            interval_velocity=0.0,
        )
        
        assert score == 0.0
    
    def test_raw_metrics_included(self):
        """Should include raw metrics in result."""
        _, raw = calculate_tempo_difficulty_score(
            bpm=120,
            rhythm_complexity=0.5,
            interval_velocity=0.5,
        )
        
        assert 'bpm' in raw
        assert 'rhythm_complexity' in raw
        assert 'interval_velocity' in raw
        assert 'raw_score' in raw


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_density_with_empty_measure_list(self):
        """Should handle empty measure list."""
        nps, npm, peak, vol, raw = calculate_density_metrics(
            total_notes=100,
            duration_seconds=30.0,
            measure_count=10,
            notes_per_measure_list=[],
        )
        
        assert isinstance(nps, float)
        assert isinstance(npm, float)
    
    def test_density_with_all_zero_measures(self):
        """Should handle all-zero measure list."""
        nps, npm, peak, vol, raw = calculate_density_metrics(
            total_notes=0,
            duration_seconds=30.0,
            measure_count=10,
            notes_per_measure_list=[0, 0, 0, 0, 0],
        )
        
        assert nps == 0
    
    def test_very_high_bpm(self):
        """Should handle very high BPM."""
        score, _ = calculate_tempo_difficulty_score(
            bpm=300,
            rhythm_complexity=1.0,
            interval_velocity=1.0,
        )
        
        # Should cap at 1.0
        assert score <= 1.0
    
    def test_very_low_bpm(self):
        """Should handle very low BPM."""
        score, _ = calculate_tempo_difficulty_score(
            bpm=30,
            rhythm_complexity=0.3,
            interval_velocity=0.3,
        )
        
        assert score >= 0.0
