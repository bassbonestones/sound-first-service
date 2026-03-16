"""
Tests for interval local difficulty calculator.

Tests sliding window analysis for concentrated difficulty spikes.
"""

import pytest
from app.calculators.interval.local_difficulty import (
    calculate_interval_local_difficulty,
    INTERVAL_WINDOW_MIN_PIECE_QL,
    INTERVAL_WINDOW_DURATION_QL,
)
from app.calculators.models import INTERVAL_BUCKET_LARGE, INTERVAL_BUCKET_EXTREME


class TestCalculateIntervalLocalDifficulty:
    """Test calculate_interval_local_difficulty function."""
    
    def test_empty_inputs_returns_none(self):
        """Empty inputs should return None."""
        assert calculate_interval_local_difficulty([], [], []) is None
    
    def test_empty_intervals_returns_none(self):
        """Empty intervals list should return None."""
        assert calculate_interval_local_difficulty([], [1.0, 2.0], [1, 1]) is None
    
    def test_empty_offsets_returns_none(self):
        """Empty offsets list should return None."""
        assert calculate_interval_local_difficulty([2, 3], [], [1, 1]) is None
    
    def test_short_piece_returns_result(self):
        """Short piece should still return result with window_count=0."""
        # Create piece shorter than INTERVAL_WINDOW_MIN_PIECE_QL (32)
        intervals = [2, 3, 4]  # Small intervals
        offsets = [1.0, 2.0, 3.0]  # Very short
        measures = [1, 1, 1]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        # Verify short piece returns result with window_count=0
        assert result.window_count == 0  # Too short for windowing
    
    def test_short_piece_detects_large_leaps(self):
        """Short piece should detect large leaps by measure."""
        # Large leap: 12-17 semitones
        intervals = [2, 14, 3]  # One large leap
        offsets = [1.0, 2.0, 3.0]
        measures = [1, 1, 1]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        assert result.max_large_leaps_in_window == 1
        assert 1 in result.hardest_measure_numbers
    
    def test_short_piece_detects_extreme_leaps(self):
        """Short piece should detect extreme leaps."""
        # Extreme leap: >= 18 semitones
        intervals = [2, 20, 3]  # One extreme leap
        offsets = [1.0, 2.0, 3.0]
        measures = [1, 2, 2]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        assert result.max_extreme_leaps_in_window == 1
        assert 2 in result.hardest_measure_numbers
    
    def test_long_piece_calculates_windows(self):
        """Long piece should use windowing and return window_count > 0."""
        # Create piece longer than 32 quarter notes
        num_intervals = 50
        intervals = [2] * num_intervals  # All small intervals
        offsets = [float(i * 2) for i in range(num_intervals)]  # 0, 2, 4, ..., 98
        measures = [(i // 4) + 1 for i in range(num_intervals)]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        # Verify long piece uses windowing
        assert result.window_count > 0
    
    def test_long_piece_with_large_leaps_in_window(self):
        """Long piece should detect max large leaps in any window."""
        num_intervals = 50
        # Put 3 large leaps clustered together (in same window)
        intervals = [2] * num_intervals
        intervals[10] = 14  # Large leap (12-17 semitones)
        intervals[11] = 14  # Large leap
        intervals[12] = 14  # Large leap
        
        offsets = [float(i * 2) for i in range(num_intervals)]
        measures = [(i // 4) + 1 for i in range(num_intervals)]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        assert result.max_large_leaps_in_window >= 3
    
    def test_hardest_measures_limited_to_three(self):
        """Should return at most 3 hardest measures."""
        num_intervals = 50
        # Put extreme leaps in many different measures
        # Extreme = 18+ semitones
        intervals = [20, 20, 20, 20, 20, 20, 20] + [2] * 43
        offsets = [float(i * 10) for i in range(num_intervals)]  # Spread out
        measures = list(range(1, num_intervals + 1))  # Each in different measure
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        assert len(result.hardest_measure_numbers) <= 3
    
    def test_extreme_leaps_weighted_higher(self):
        """Extreme leaps should be weighted higher for hardest measures."""
        # Two large leaps in measure 1, one extreme leap in measure 2
        # Large = 12-17 semitones, extreme = 18+ semitones
        intervals = [14, 14, 20, 2, 2]  # 2 large + 1 extreme
        offsets = [1.0, 2.0, 5.0, 6.0, 7.0]
        measures = [1, 1, 2, 3, 3]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        # Measure 2 should be hardest (1 extreme = 2 points)
        # Measure 1 has 2 large = 2 points (tie)
        assert 2 in result.hardest_measure_numbers
    
    def test_no_leaps_returns_zeros(self):
        """Piece with no large/extreme leaps should return zeros."""
        num_intervals = 50
        intervals = [2, 3, 4, 5, 2, 3] * 8 + [2, 2]  # All small intervals
        offsets = [float(i * 2) for i in range(num_intervals)]
        measures = [(i // 4) + 1 for i in range(num_intervals)]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        assert result.max_large_leaps_in_window == 0
        assert result.max_extreme_leaps_in_window == 0
        assert result.hardest_measure_numbers == []


class TestBucketBoundaries:
    """Test interval bucket boundary handling."""
    
    def test_large_leap_lower_bound(self):
        """11 semitones should NOT be large (boundary is 12)."""
        intervals = [11, 11, 11]
        offsets = [1.0, 2.0, 3.0]
        measures = [1, 1, 1]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        assert result.max_large_leaps_in_window == 0
    
    def test_large_leap_at_12_semitones(self):
        """12 semitones should be counted as large."""
        intervals = [12, 2, 2]
        offsets = [1.0, 2.0, 3.0]
        measures = [1, 1, 1]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        assert result.max_large_leaps_in_window == 1
    
    def test_extreme_leap_at_18_semitones(self):
        """18 semitones should be extreme (not large)."""
        intervals = [18, 2, 2]
        offsets = [1.0, 2.0, 3.0]
        measures = [1, 1, 1]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        assert result.max_extreme_leaps_in_window == 1
        assert result.max_large_leaps_in_window == 0  # Not counted as large
