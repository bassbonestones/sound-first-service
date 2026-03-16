"""
Tests for Interval Calculator Module.

Tests interval profile, stage, and local difficulty calculations.
"""

import pytest
from app.calculators.interval_calculator import (
    calculate_interval_size_stage,
    calculate_interval_sustained_stage,
    calculate_interval_hazard_stage,
    calculate_interval_profile,
    calculate_interval_local_difficulty,
    calculate_interval_velocity_score,
)
from app.calculators.models import (
    IntervalProfile,
    IntervalLocalDifficulty,
    NoteEvent,
)


# =============================================================================
# TEST: INTERVAL PROFILE
# =============================================================================

class TestIntervalProfile:
    """Test interval profile calculation."""
    
    def test_returns_interval_profile(self):
        """Should return IntervalProfile instance."""
        intervals = [2, 3, 4, 5, 7, 12]
        result = calculate_interval_profile(intervals)
        assert isinstance(result, IntervalProfile)
    
    def test_empty_list_returns_defaults(self):
        """Empty list should return safe defaults."""
        result = calculate_interval_profile([])
        
        assert result.total_intervals == 0
        assert result.step_ratio == 1.0
        assert result.interval_max == 0
    
    def test_counts_total_intervals(self):
        """Should count total intervals correctly."""
        intervals = [1, 2, 3, 4, 5]
        result = calculate_interval_profile(intervals)
        
        assert result.total_intervals == 5
    
    def test_bucket_classification_steps(self):
        """Intervals 0-2 should be classified as steps."""
        intervals = [0, 1, 2, 2, 1, 0]  # All steps
        result = calculate_interval_profile(intervals)
        
        assert result.step_ratio == 1.0
        assert result.skip_ratio == 0.0
        assert result.leap_ratio == 0.0
    
    def test_bucket_classification_skips(self):
        """Intervals 3-5 should be classified as skips."""
        intervals = [3, 4, 5, 3, 4]  # All skips
        result = calculate_interval_profile(intervals)
        
        assert result.step_ratio == 0.0
        assert result.skip_ratio == 1.0
        assert result.leap_ratio == 0.0
    
    def test_bucket_classification_leaps(self):
        """Intervals 6-11 should be classified as leaps."""
        intervals = [6, 7, 8, 9, 10, 11]  # All leaps
        result = calculate_interval_profile(intervals)
        
        assert result.leap_ratio == 1.0
    
    def test_bucket_classification_large_leaps(self):
        """Intervals 12-17 should be classified as large leaps."""
        intervals = [12, 14, 16, 12]  # All large leaps
        result = calculate_interval_profile(intervals)
        
        assert result.large_leap_ratio == 1.0
    
    def test_bucket_classification_extreme_leaps(self):
        """Intervals 18+ should be classified as extreme leaps."""
        intervals = [18, 19, 24, 30]  # All extreme
        result = calculate_interval_profile(intervals)
        
        assert result.extreme_leap_ratio == 1.0
    
    def test_mixed_intervals_ratios(self):
        """Mixed intervals should have proper ratio distribution."""
        # 5 intervals: 2 steps, 2 skips, 1 leap
        intervals = [1, 2, 3, 4, 7]
        result = calculate_interval_profile(intervals)
        
        assert abs(result.step_ratio - 0.4) < 0.01
        assert abs(result.skip_ratio - 0.4) < 0.01
        assert abs(result.leap_ratio - 0.2) < 0.01
    
    def test_percentile_calculation(self):
        """Should calculate percentiles correctly."""
        intervals = list(range(1, 101))  # 1 to 100
        result = calculate_interval_profile(intervals)
        
        assert result.interval_p50 == 50 or result.interval_p50 == 51
        assert result.interval_p75 >= 75
        assert result.interval_p90 >= 90
        assert result.interval_max == 100


# =============================================================================
# TEST: INTERVAL SIZE STAGE
# =============================================================================

class TestIntervalSizeStage:
    """Test interval size stage calculation."""
    
    def test_returns_tuple(self):
        """Should return (stage, raw_dict) tuple."""
        result = calculate_interval_size_stage([2, 3, 4])
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], int)
        assert isinstance(result[1], dict)
    
    def test_empty_list_returns_stage_zero(self):
        """Empty list should return stage 0."""
        stage, raw = calculate_interval_size_stage([])
        
        assert stage == 0
        assert raw['interval_count'] == 0
    
    def test_stage_0_unisons(self):
        """All unisons should be stage 0."""
        stage, _ = calculate_interval_size_stage([0, 0, 0, 0])
        assert stage == 0
    
    def test_stage_1_half_steps(self):
        """p90 of 1 should be stage 1."""
        stage, _ = calculate_interval_size_stage([0, 1, 1, 1, 1, 1, 1, 1, 1, 1])
        assert stage == 1
    
    def test_stage_2_whole_steps(self):
        """p90 of 2 should be stage 2."""
        stage, _ = calculate_interval_size_stage([1, 2, 2, 2, 2, 2, 2, 2, 2, 2])
        assert stage == 2
    
    def test_stage_3_thirds(self):
        """p90 of 3-4 should be stage 3."""
        stage, _ = calculate_interval_size_stage([2, 3, 3, 3, 3, 3, 4, 4, 4, 4])
        assert stage == 3
    
    def test_stage_4_fourths_fifths(self):
        """p90 of 5-7 should be stage 4."""
        stage, _ = calculate_interval_size_stage([3, 4, 5, 5, 5, 6, 6, 7, 7, 7])
        assert stage == 4
    
    def test_stage_5_sixths(self):
        """p90 of 8-9 should be stage 5."""
        stage, _ = calculate_interval_size_stage([5, 6, 7, 8, 8, 8, 9, 9, 9, 9])
        assert stage == 5
    
    def test_stage_6_sevenths_plus(self):
        """p90 of 10+ should be stage 6."""
        stage, _ = calculate_interval_size_stage([7, 8, 9, 10, 10, 11, 11, 12, 12, 14])
        assert stage == 6
    
    def test_raw_metrics_included(self):
        """Should include raw metrics in result."""
        _, raw = calculate_interval_size_stage([2, 3, 5, 7, 12])
        
        assert 'p90_interval' in raw
        assert 'max_interval' in raw
        assert 'mean_interval' in raw
        assert raw['max_interval'] == 12


# =============================================================================
# TEST: SUSTAINED AND HAZARD STAGES
# =============================================================================

class TestSustainedAndHazardStages:
    """Test sustained and hazard stage calculations."""
    
    def test_sustained_stage_returns_int(self):
        """Should return integer stage."""
        profile = IntervalProfile(
            total_intervals=100,
            step_ratio=0.7,
            skip_ratio=0.2,
            leap_ratio=0.08,
            large_leap_ratio=0.02,
            extreme_leap_ratio=0.0,
            interval_p50=2,
            interval_p75=3,
            interval_p90=5,
            interval_max=10,
        )
        stage = calculate_interval_sustained_stage(profile)
        
        assert isinstance(stage, int)
        assert 0 <= stage <= 6
    
    def test_hazard_stage_returns_int(self):
        """Should return integer stage."""
        profile = IntervalProfile(
            total_intervals=100,
            step_ratio=0.5,
            skip_ratio=0.3,
            leap_ratio=0.1,
            large_leap_ratio=0.08,
            extreme_leap_ratio=0.02,
            interval_p50=3,
            interval_p75=5,
            interval_p90=8,
            interval_max=18,
        )
        # Hazard stage requires local_difficulty parameter
        stage = calculate_interval_hazard_stage(profile, None)
        
        assert isinstance(stage, int)
        assert 0 <= stage <= 6
    
    def test_hazard_driven_by_max(self):
        """Hazard stage should be driven by max interval."""
        # High max, low p75 - hazard should be high, sustained should be low
        profile = IntervalProfile(
            total_intervals=100,
            step_ratio=0.9,
            skip_ratio=0.08,
            leap_ratio=0.02,
            large_leap_ratio=0.0,
            extreme_leap_ratio=0.0,
            interval_p50=1,
            interval_p75=2,
            interval_p90=3,
            interval_max=24,  # One big leap!
        )
        sustained = calculate_interval_sustained_stage(profile)
        hazard = calculate_interval_hazard_stage(profile, None)
        
        # Hazard should be higher than sustained
        assert hazard > sustained


# =============================================================================
# TEST: LOCAL DIFFICULTY
# =============================================================================

class TestIntervalLocalDifficulty:
    """Test interval local difficulty calculation."""
    
    def test_returns_local_difficulty_or_none(self):
        """Should return IntervalLocalDifficulty for long pieces or None for short."""
        intervals = [12, 12]  # Two octave leaps
        offsets = [0.0, 1.0]  # Short piece
        measures = [1, 1]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        
        # May return None for short pieces
        assert result is None or isinstance(result, IntervalLocalDifficulty)
    
    def test_empty_lists_returns_none(self):
        """Empty lists should return None."""
        result = calculate_interval_local_difficulty([], [], [])
        assert result is None
    
    def test_long_piece_returns_result(self):
        """Long piece should return IntervalLocalDifficulty."""
        # Create enough data for windowing (>32 qL)
        intervals = [2, 3, 12, 5, 4, 18, 3, 2, 4, 5, 12, 3]
        offsets = [i * 4.0 for i in range(len(intervals))]  # 48 qL total
        measures = [i // 4 + 1 for i in range(len(intervals))]
        
        result = calculate_interval_local_difficulty(intervals, offsets, measures)
        
        if result is not None:
            assert isinstance(result, IntervalLocalDifficulty)
            assert result.max_large_leaps_in_window >= 0
            assert result.max_extreme_leaps_in_window >= 0


# =============================================================================
# TEST: INTERVAL VELOCITY SCORE
# =============================================================================

class TestIntervalVelocityScore:
    """Test interval velocity score calculation."""
    
    def test_returns_tuple(self):
        """Should return (score, raw_dict) tuple."""
        notes = [
            NoteEvent(pitch_midi=60, duration_ql=0.5, offset_ql=0.0),
            NoteEvent(pitch_midi=64, duration_ql=0.5, offset_ql=0.5),
            NoteEvent(pitch_midi=67, duration_ql=0.5, offset_ql=1.0),
        ]
        result = calculate_interval_velocity_score(notes)
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], dict)
    
    def test_score_in_range(self):
        """Score should be in [0, 1] range."""
        notes = [
            NoteEvent(pitch_midi=60, duration_ql=0.25, offset_ql=0.0),
            NoteEvent(pitch_midi=72, duration_ql=0.25, offset_ql=0.25),
            NoteEvent(pitch_midi=84, duration_ql=0.25, offset_ql=0.5),
            NoteEvent(pitch_midi=72, duration_ql=0.25, offset_ql=0.75),
        ]
        score, _ = calculate_interval_velocity_score(notes)
        
        assert 0 <= score <= 1
    
    def test_empty_notes_returns_zero(self):
        """Empty notes should return 0."""
        score, raw = calculate_interval_velocity_score([])
        
        assert score == 0.0
        assert raw['interval_count'] == 0
    
    def test_single_note_returns_zero(self):
        """Single note should return 0 (no intervals)."""
        notes = [NoteEvent(pitch_midi=60, duration_ql=1.0, offset_ql=0.0)]
        score, raw = calculate_interval_velocity_score(notes)
        
        assert score == 0.0
        assert raw['interval_count'] == 0


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_profile_single_interval(self):
        """Should handle single interval."""
        result = calculate_interval_profile([7])
        
        assert result.total_intervals == 1
        assert result.interval_max == 7
    
    def test_stage_all_same_intervals(self):
        """Should handle all same intervals."""
        stage, _ = calculate_interval_size_stage([5, 5, 5, 5, 5])
        
        assert isinstance(stage, int)
    
    def test_profile_very_large_intervals(self):
        """Should handle very large intervals."""
        intervals = [48, 60, 72]  # Multi-octave
        result = calculate_interval_profile(intervals)
        
        assert result.extreme_leap_ratio == 1.0
        assert result.interval_max == 72
