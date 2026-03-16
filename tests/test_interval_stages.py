"""
Tests for calculators/interval/stages.py

Tests for interval stage calculation functions.
"""

import pytest

from app.calculators.interval.stages import (
    calculate_interval_size_stage,
    calculate_interval_sustained_stage,
    calculate_interval_hazard_stage,
)
from app.calculators.models import IntervalProfile, IntervalLocalDifficulty


class TestCalculateIntervalSizeStage:
    """Tests for calculate_interval_size_stage function."""

    def test_empty_intervals_returns_stage_0(self):
        """Empty intervals should return stage 0."""
        stage, raw = calculate_interval_size_stage([])
        
        assert stage == 0
        assert raw["p90_interval"] == 0
        assert raw["interval_count"] == 0

    def test_unison_returns_stage_0(self):
        """Unisons (0 semitones) should return stage 0."""
        stage, raw = calculate_interval_size_stage([0, 0, 0, 0])
        
        assert stage == 0
        assert raw["p90_interval"] == 0

    def test_half_steps_return_stage_1(self):
        """Half steps (1 semitone) should return stage 1."""
        stage, raw = calculate_interval_size_stage([1, 1, 1, 1, 1])
        
        assert stage == 1
        assert raw["p90_interval"] == 1

    def test_whole_steps_return_stage_2(self):
        """Whole steps (2 semitones) should return stage 2."""
        stage, raw = calculate_interval_size_stage([2, 2, 2, 2, 2])
        
        assert stage == 2
        assert raw["p90_interval"] == 2

    def test_thirds_return_stage_3(self):
        """Thirds (3-4 semitones) should return stage 3."""
        stage, raw = calculate_interval_size_stage([3, 4, 3, 4, 3])
        
        assert stage == 3

    def test_fourths_fifths_return_stage_4(self):
        """Fourths/Fifths (5-7 semitones) should return stage 4."""
        stage, raw = calculate_interval_size_stage([5, 6, 7, 5, 6])
        
        assert stage == 4

    def test_sixths_return_stage_5(self):
        """Sixths (8-9 semitones) should return stage 5."""
        stage, raw = calculate_interval_size_stage([8, 9, 8, 9, 8])
        
        assert stage == 5

    def test_sevenths_octaves_return_stage_6(self):
        """Sevenths/Octaves+ (10+ semitones) should return stage 6."""
        stage, raw = calculate_interval_size_stage([10, 11, 12, 10, 11])
        
        assert stage == 6

    def test_returns_raw_metrics(self):
        """Should return raw metrics dictionary."""
        stage, raw = calculate_interval_size_stage([1, 2, 3, 4, 5])
        
        assert "p90_interval" in raw
        assert "max_interval" in raw
        assert "mean_interval" in raw
        assert "interval_count" in raw
        assert raw["max_interval"] == 5
        assert raw["interval_count"] == 5


class TestCalculateIntervalSustainedStage:
    """Tests for calculate_interval_sustained_stage function."""

    def test_stage_0_for_unisons(self):
        """Unison p75 should return stage 0."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=1.0, skip_ratio=0.0, leap_ratio=0.0,
            large_leap_ratio=0.0, extreme_leap_ratio=0.0,
            interval_p50=0, interval_p75=0, interval_p90=0, interval_max=0
        )
        
        stage = calculate_interval_sustained_stage(profile)
        assert stage == 0

    def test_stage_1_for_half_steps(self):
        """Half step p75 should return stage 1."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=1.0, skip_ratio=0.0, leap_ratio=0.0,
            large_leap_ratio=0.0, extreme_leap_ratio=0.0,
            interval_p50=1, interval_p75=1, interval_p90=1, interval_max=1
        )
        
        stage = calculate_interval_sustained_stage(profile)
        assert stage == 1

    def test_stage_2_for_whole_steps(self):
        """Whole step p75 should return stage 2."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=1.0, skip_ratio=0.0, leap_ratio=0.0,
            large_leap_ratio=0.0, extreme_leap_ratio=0.0,
            interval_p50=2, interval_p75=2, interval_p90=2, interval_max=2
        )
        
        stage = calculate_interval_sustained_stage(profile)
        assert stage == 2

    def test_stage_bumps_for_high_large_leap_ratio(self):
        """Should bump stage +1 when large_leap_ratio > 0.15."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.5, skip_ratio=0.3, leap_ratio=0.0,
            large_leap_ratio=0.2,  # > 0.15
            extreme_leap_ratio=0.0,
            interval_p50=2, interval_p75=2, interval_p90=5, interval_max=12
        )
        
        stage = calculate_interval_sustained_stage(profile)
        # Base stage 2 (whole steps) + 1 for large_leap_ratio = 3
        assert stage == 3

    def test_stage_capped_at_6(self):
        """Should not exceed stage 6 with bump."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.0, skip_ratio=0.0, leap_ratio=0.0,
            large_leap_ratio=0.5,  # > 0.15
            extreme_leap_ratio=0.5,
            interval_p50=10, interval_p75=12, interval_p90=15, interval_max=20
        )
        
        stage = calculate_interval_sustained_stage(profile)
        assert stage == 6  # Capped at 6

    def test_no_bump_for_low_large_leap_ratio(self):
        """Should not bump when large_leap_ratio <= 0.15."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.7, skip_ratio=0.2, leap_ratio=0.0,
            large_leap_ratio=0.10,  # <= 0.15
            extreme_leap_ratio=0.0,
            interval_p50=2, interval_p75=2, interval_p90=4, interval_max=5
        )
        
        stage = calculate_interval_sustained_stage(profile)
        assert stage == 2  # No bump


class TestCalculateIntervalHazardStage:
    """Tests for calculate_interval_hazard_stage function."""

    def test_stage_0_for_steps_only(self):
        """Max interval of steps should return stage 0."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=1.0, skip_ratio=0.0, leap_ratio=0.0,
            large_leap_ratio=0.0, extreme_leap_ratio=0.0,
            interval_p50=1, interval_p75=2, interval_p90=2, interval_max=2
        )
        
        stage = calculate_interval_hazard_stage(profile, None)
        assert stage == 0

    def test_stage_1_for_small_skip(self):
        """Max interval of 3-4 should return stage 1."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.8, skip_ratio=0.2, leap_ratio=0.0,
            large_leap_ratio=0.0, extreme_leap_ratio=0.0,
            interval_p50=1, interval_p75=2, interval_p90=3, interval_max=4
        )
        
        stage = calculate_interval_hazard_stage(profile, None)
        assert stage == 1

    def test_stage_2_for_fourth_fifth(self):
        """Max interval of 5-7 should return stage 2."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.6, skip_ratio=0.3, leap_ratio=0.1,
            large_leap_ratio=0.0, extreme_leap_ratio=0.0,
            interval_p50=2, interval_p75=4, interval_p90=6, interval_max=7
        )
        
        stage = calculate_interval_hazard_stage(profile, None)
        assert stage == 2

    def test_stage_3_for_major_seventh(self):
        """Max interval up to 11 should return stage 3."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.5, skip_ratio=0.3, leap_ratio=0.2,
            large_leap_ratio=0.0, extreme_leap_ratio=0.0,
            interval_p50=3, interval_p75=5, interval_p90=9, interval_max=11
        )
        
        stage = calculate_interval_hazard_stage(profile, None)
        assert stage == 3

    def test_stage_4_for_octave(self):
        """Max interval of 12-15 should return stage 4."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.5, skip_ratio=0.2, leap_ratio=0.2,
            large_leap_ratio=0.1, extreme_leap_ratio=0.0,
            interval_p50=3, interval_p75=5, interval_p90=10, interval_max=12
        )
        
        stage = calculate_interval_hazard_stage(profile, None)
        assert stage == 4

    def test_stage_5_for_tenth_to_thirteenth(self):
        """Max interval of 16-20 should return stage 5."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.4, skip_ratio=0.3, leap_ratio=0.2,
            large_leap_ratio=0.1, extreme_leap_ratio=0.0,
            interval_p50=4, interval_p75=7, interval_p90=12, interval_max=18
        )
        
        stage = calculate_interval_hazard_stage(profile, None)
        assert stage == 5

    def test_stage_6_for_extreme_intervals(self):
        """Max interval of 21+ should return stage 6."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.3, skip_ratio=0.3, leap_ratio=0.2,
            large_leap_ratio=0.1, extreme_leap_ratio=0.1,
            interval_p50=5, interval_p75=8, interval_p90=15, interval_max=24
        )
        
        stage = calculate_interval_hazard_stage(profile, None)
        assert stage == 6

    def test_bumps_for_clustered_extreme_leaps(self):
        """Should bump stage +1 when clustered extreme leaps >= 2."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.5, skip_ratio=0.3, leap_ratio=0.1,
            large_leap_ratio=0.1, extreme_leap_ratio=0.0,
            interval_p50=2, interval_p75=4, interval_p90=7, interval_max=7
        )
        
        local_diff = IntervalLocalDifficulty(
            max_large_leaps_in_window=1,
            max_extreme_leaps_in_window=2,  # >= 2 triggers bump
            hardest_measure_numbers=[5, 6],
            window_count=10
        )
        
        stage = calculate_interval_hazard_stage(profile, local_diff)
        # Base stage 2 (fourth/fifth) + 1 = 3
        assert stage == 3

    def test_no_bump_without_local_difficulty(self):
        """Should not bump when local_difficulty is None."""
        profile = IntervalProfile(
            total_intervals=10,
            step_ratio=0.5, skip_ratio=0.3, leap_ratio=0.2,
            large_leap_ratio=0.0, extreme_leap_ratio=0.0,
            interval_p50=2, interval_p75=4, interval_p90=7, interval_max=7
        )
        
        stage = calculate_interval_hazard_stage(profile, None)
        assert stage == 2  # No bump
