"""
Tests for calculators/models.py

Tests for calculator data models and constants.
"""

import pytest

from app.calculators.models import (
    INTERVAL_BUCKET_STEP,
    INTERVAL_BUCKET_SKIP,
    INTERVAL_BUCKET_LEAP,
    INTERVAL_BUCKET_LARGE,
    INTERVAL_BUCKET_EXTREME,
    NoteEvent,
    IntervalProfile,
    IntervalLocalDifficulty,
    SoftGateMetrics,
)


class TestIntervalBucketConstants:
    """Tests for interval bucket constants."""

    def test_step_bucket_range(self):
        """Step bucket should be 0-2 semitones."""
        assert INTERVAL_BUCKET_STEP == (0, 2)

    def test_skip_bucket_range(self):
        """Skip bucket should be 3-5 semitones."""
        assert INTERVAL_BUCKET_SKIP == (3, 5)

    def test_leap_bucket_range(self):
        """Leap bucket should be 6-11 semitones."""
        assert INTERVAL_BUCKET_LEAP == (6, 11)

    def test_large_bucket_range(self):
        """Large bucket should be 12-17 semitones."""
        assert INTERVAL_BUCKET_LARGE == (12, 17)

    def test_extreme_bucket_range(self):
        """Extreme bucket should start at 18 semitones."""
        assert INTERVAL_BUCKET_EXTREME[0] == 18

    def test_buckets_are_contiguous(self):
        """Bucket boundaries should be contiguous."""
        # Step ends at 2, skip starts at 3
        assert INTERVAL_BUCKET_STEP[1] + 1 == INTERVAL_BUCKET_SKIP[0]
        # Skip ends at 5, leap starts at 6
        assert INTERVAL_BUCKET_SKIP[1] + 1 == INTERVAL_BUCKET_LEAP[0]
        # Leap ends at 11, large starts at 12
        assert INTERVAL_BUCKET_LEAP[1] + 1 == INTERVAL_BUCKET_LARGE[0]
        # Large ends at 17, extreme starts at 18
        assert INTERVAL_BUCKET_LARGE[1] + 1 == INTERVAL_BUCKET_EXTREME[0]


class TestNoteEvent:
    """Tests for NoteEvent dataclass."""

    def test_create_note_event(self):
        """Should create NoteEvent with required fields."""
        event = NoteEvent(pitch_midi=60, duration_ql=1.0, offset_ql=0.0)
        
        assert event.pitch_midi == 60
        assert event.duration_ql == 1.0
        assert event.offset_ql == 0.0

    def test_note_event_with_float_duration(self):
        """Should handle float duration correctly."""
        event = NoteEvent(pitch_midi=60, duration_ql=0.5, offset_ql=4.5)
        
        assert event.duration_ql == 0.5
        assert event.offset_ql == 4.5


class TestIntervalProfile:
    """Tests for IntervalProfile dataclass."""

    def test_create_interval_profile(self):
        """Should create IntervalProfile with all fields."""
        profile = IntervalProfile(
            total_intervals=100,
            step_ratio=0.5,
            skip_ratio=0.3,
            leap_ratio=0.15,
            large_leap_ratio=0.04,
            extreme_leap_ratio=0.01,
            interval_p50=2,
            interval_p75=4,
            interval_p90=7,
            interval_max=12
        )
        
        assert profile.total_intervals == 100
        assert profile.step_ratio == 0.5
        assert profile.skip_ratio == 0.3
        assert profile.leap_ratio == 0.15
        assert profile.large_leap_ratio == 0.04
        assert profile.extreme_leap_ratio == 0.01
        assert profile.interval_p50 == 2
        assert profile.interval_p75 == 4
        assert profile.interval_p90 == 7
        assert profile.interval_max == 12

    def test_ratios_can_sum_to_one(self):
        """Texture ratios should be able to sum to 1.0."""
        profile = IntervalProfile(
            total_intervals=100,
            step_ratio=0.6,
            skip_ratio=0.25,
            leap_ratio=0.1,
            large_leap_ratio=0.04,
            extreme_leap_ratio=0.01,
            interval_p50=2,
            interval_p75=4,
            interval_p90=7,
            interval_max=12
        )
        
        total = (profile.step_ratio + profile.skip_ratio + profile.leap_ratio + 
                 profile.large_leap_ratio + profile.extreme_leap_ratio)
        assert abs(total - 1.0) < 0.001


class TestIntervalLocalDifficulty:
    """Tests for IntervalLocalDifficulty dataclass."""

    def test_create_local_difficulty(self):
        """Should create IntervalLocalDifficulty with all fields."""
        local_diff = IntervalLocalDifficulty(
            max_large_leaps_in_window=3,
            max_extreme_leaps_in_window=1,
            hardest_measure_numbers=[5, 10, 15],
            window_count=20
        )
        
        assert local_diff.max_large_leaps_in_window == 3
        assert local_diff.max_extreme_leaps_in_window == 1
        assert local_diff.hardest_measure_numbers == [5, 10, 15]
        assert local_diff.window_count == 20

    def test_hardest_measures_can_be_empty(self):
        """Should handle empty hardest_measure_numbers."""
        local_diff = IntervalLocalDifficulty(
            max_large_leaps_in_window=0,
            max_extreme_leaps_in_window=0,
            hardest_measure_numbers=[],
            window_count=10
        )
        
        assert local_diff.hardest_measure_numbers == []


class TestSoftGateMetrics:
    """Tests for SoftGateMetrics dataclass."""

    def test_create_basic_metrics(self):
        """Should create SoftGateMetrics with required fields."""
        metrics = SoftGateMetrics(
            tonal_complexity_stage=2,
            interval_size_stage=3,
            rhythm_complexity_score=0.45,
            range_usage_stage=4
        )
        
        assert metrics.tonal_complexity_stage == 2
        assert metrics.interval_size_stage == 3
        assert metrics.rhythm_complexity_score == 0.45
        assert metrics.range_usage_stage == 4

    def test_default_values(self):
        """Should have correct default values."""
        metrics = SoftGateMetrics(
            tonal_complexity_stage=0,
            interval_size_stage=0,
            rhythm_complexity_score=0.0,
            range_usage_stage=0
        )
        
        assert metrics.interval_sustained_stage == 0
        assert metrics.interval_hazard_stage == 0
        assert metrics.legacy_interval_size_stage == 0
        assert metrics.interval_profile is None
        assert metrics.interval_local_difficulty is None
        assert metrics.rhythm_complexity_peak is None
        assert metrics.density_notes_per_second == 0.0
        assert metrics.unique_pitch_count == 0
        assert metrics.raw_metrics is None

    def test_full_metrics_with_all_fields(self):
        """Should create metrics with all optional fields."""
        profile = IntervalProfile(
            total_intervals=50,
            step_ratio=0.6, skip_ratio=0.3, leap_ratio=0.1,
            large_leap_ratio=0.0, extreme_leap_ratio=0.0,
            interval_p50=2, interval_p75=3, interval_p90=5, interval_max=7
        )
        
        metrics = SoftGateMetrics(
            tonal_complexity_stage=2,
            interval_size_stage=3,
            rhythm_complexity_score=0.45,
            range_usage_stage=4,
            interval_sustained_stage=2,
            interval_hazard_stage=3,
            legacy_interval_size_stage=3,
            interval_profile=profile,
            rhythm_complexity_peak=0.6,
            rhythm_complexity_p95=0.55,
            density_notes_per_second=2.5,
            note_density_per_measure=8.0,
            peak_notes_per_second=4.0,
            throughput_volatility=0.3,
            tempo_difficulty_score=0.5,
            interval_velocity_score=0.4,
            interval_velocity_peak=0.6,
            interval_velocity_p95=0.5,
            unique_pitch_count=8,
            largest_interval_semitones=7,
            tessitura_span_semitones=12,
            raw_metrics={"test": "value"}
        )
        
        assert metrics.interval_sustained_stage == 2
        assert metrics.interval_hazard_stage == 3
        assert metrics.interval_profile.total_intervals == 50
        assert metrics.rhythm_complexity_peak == 0.6
        assert metrics.density_notes_per_second == 2.5
        assert metrics.tempo_difficulty_score == 0.5
        assert metrics.raw_metrics == {"test": "value"}
