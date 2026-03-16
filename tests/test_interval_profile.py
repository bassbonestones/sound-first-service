"""
Tests for calculators/interval/profile.py

Tests for interval profile calculation functions.
"""

import pytest

from app.calculators.interval.profile import calculate_interval_profile
from app.calculators.models import IntervalProfile


class TestCalculateIntervalProfile:
    """Tests for calculate_interval_profile function."""

    def test_empty_intervals_returns_default_profile(self):
        """Empty intervals should return default profile."""
        result = calculate_interval_profile([])
        
        assert isinstance(result, IntervalProfile)
        assert result.total_intervals == 0
        assert result.step_ratio == 1.0
        assert result.skip_ratio == 0.0
        assert result.leap_ratio == 0.0
        assert result.interval_max == 0

    def test_single_step_interval(self):
        """Single step interval should have step_ratio of 1.0."""
        result = calculate_interval_profile([2])
        
        assert result.total_intervals == 1
        assert result.step_ratio == 1.0
        assert result.skip_ratio == 0.0
        assert result.leap_ratio == 0.0
        assert result.interval_max == 2

    def test_all_steps(self):
        """All step intervals should have step_ratio of 1.0."""
        result = calculate_interval_profile([1, 2, 1, 2, 0, 1])
        
        assert result.total_intervals == 6
        assert result.step_ratio == 1.0
        assert result.skip_ratio == 0.0
        assert result.leap_ratio == 0.0

    def test_all_skips(self):
        """All skip intervals should have skip_ratio of 1.0."""
        result = calculate_interval_profile([3, 4, 5, 3, 4])
        
        assert result.total_intervals == 5
        assert result.step_ratio == 0.0
        assert result.skip_ratio == 1.0
        assert result.leap_ratio == 0.0

    def test_all_leaps(self):
        """All leap intervals should have leap_ratio of 1.0."""
        result = calculate_interval_profile([6, 7, 8, 9, 10, 11])
        
        assert result.total_intervals == 6
        assert result.step_ratio == 0.0
        assert result.skip_ratio == 0.0
        assert result.leap_ratio == 1.0
        assert result.large_leap_ratio == 0.0

    def test_all_large_leaps(self):
        """All large leap intervals should have large_leap_ratio of 1.0."""
        result = calculate_interval_profile([12, 13, 14, 15, 16, 17])
        
        assert result.total_intervals == 6
        assert result.step_ratio == 0.0
        assert result.skip_ratio == 0.0
        assert result.leap_ratio == 0.0
        assert result.large_leap_ratio == 1.0
        assert result.extreme_leap_ratio == 0.0

    def test_all_extreme_leaps(self):
        """All extreme leap intervals should have extreme_leap_ratio of 1.0."""
        result = calculate_interval_profile([18, 19, 20, 24])
        
        assert result.total_intervals == 4
        assert result.large_leap_ratio == 0.0
        assert result.extreme_leap_ratio == 1.0

    def test_mixed_intervals(self):
        """Mixed intervals should have correct ratios."""
        # 2 steps, 2 skips, 1 leap = 5 total
        result = calculate_interval_profile([1, 2, 3, 4, 7])
        
        assert result.total_intervals == 5
        assert result.step_ratio == 0.4  # 2/5
        assert result.skip_ratio == 0.4  # 2/5
        assert result.leap_ratio == 0.2  # 1/5

    def test_percentile_p50(self):
        """Should calculate p50 (median) correctly."""
        result = calculate_interval_profile([1, 2, 3, 4, 5, 6, 7, 8, 9])
        
        # Median of [1,2,3,4,5,6,7,8,9] is 5
        assert result.interval_p50 == 5

    def test_percentile_p75(self):
        """Should calculate p75 correctly."""
        result = calculate_interval_profile([1, 2, 3, 4, 5, 6, 7, 8])
        
        # 75th percentile of [1,2,3,4,5,6,7,8] is 7 (index 6)
        assert result.interval_p75 == 7

    def test_percentile_p90(self):
        """Should calculate p90 correctly."""
        result = calculate_interval_profile([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        
        # 90th percentile of 10 elements is index 9
        assert result.interval_p90 == 10

    def test_interval_max(self):
        """Should track maximum interval."""
        result = calculate_interval_profile([1, 5, 12, 3, 7])
        
        assert result.interval_max == 12

    def test_unsorted_input(self):
        """Should handle unsorted input correctly."""
        result = calculate_interval_profile([7, 1, 12, 3, 5])
        
        assert result.total_intervals == 5
        assert result.interval_max == 12
        # Sorted: [1, 3, 5, 7, 12]
        assert result.interval_p50 == 5

    def test_typical_melody_profile(self):
        """Test typical melody with mostly steps and some skips."""
        # Simulate a simple stepwise melody with occasional thirds
        intervals = [2, 2, 1, 2, 3, 2, 1, 2, 4, 2]  # Mostly steps, 2 skips
        result = calculate_interval_profile(intervals)
        
        assert result.total_intervals == 10
        assert result.step_ratio == 0.8  # 8/10
        assert result.skip_ratio == 0.2  # 2/10
        assert result.leap_ratio == 0.0
        assert result.interval_max == 4

    def test_large_interval_piece(self):
        """Test piece with large intervals like arpeggios."""
        # Simulate arpeggio-heavy piece
        intervals = [5, 7, 5, 7, 12, 5, 7, 5]  # Skips, leaps, and one large
        result = calculate_interval_profile(intervals)
        
        assert result.total_intervals == 8
        assert result.step_ratio == 0.0
        assert result.skip_ratio == 0.5  # 4/8 (the 5s)
        assert result.leap_ratio == 0.375  # 3/8 (the 7s)
        assert result.large_leap_ratio == 0.125  # 1/8 (the 12)
        assert result.interval_max == 12
