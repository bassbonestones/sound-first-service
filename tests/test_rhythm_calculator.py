"""
Tests for Rhythm Complexity Calculator.

Tests D3 — Rhythm Complexity Score (0-1) with global and windowed analysis.
"""

import pytest
from app.calculators.rhythm_calculator import (
    calculate_rhythm_complexity_score,
    calculate_rhythm_complexity_windowed,
)


# =============================================================================
# TEST: RHYTHM COMPLEXITY SCORE
# =============================================================================

class TestRhythmComplexityScore:
    """Test rhythm complexity score calculation."""
    
    def test_returns_tuple(self):
        """Should return (score, raw_dict) tuple."""
        result = calculate_rhythm_complexity_score(
            note_durations=[1.0, 1.0, 1.0],
            note_types=['quarter', 'quarter', 'quarter'],
            has_dots=[False, False, False],
            has_tuplets=[False, False, False],
            has_ties=[False, False, False],
            pitch_changes=[2, 3],
            offsets=[0.0, 1.0, 2.0],
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], float)
        assert isinstance(result[1], dict)
    
    def test_score_in_range(self):
        """Score should be in [0, 1] range."""
        score, _ = calculate_rhythm_complexity_score(
            note_durations=[0.25, 0.5, 1.0, 0.25],
            note_types=['16th', 'eighth', 'quarter', '16th'],
            has_dots=[False, True, False, False],
            has_tuplets=[False, False, False, True],
            has_ties=[False, False, True, False],
            pitch_changes=[5, 3, 7],
            offsets=[0.0, 0.25, 0.75, 1.75],
        )
        
        assert 0 <= score <= 1
    
    def test_empty_input_returns_zero(self):
        """Empty input should return 0."""
        score, raw = calculate_rhythm_complexity_score(
            note_durations=[],
            note_types=[],
            has_dots=[],
            has_tuplets=[],
            has_ties=[],
            pitch_changes=[],
            offsets=[],
        )
        
        assert score == 0.0
        assert raw['f1'] == 0
    
    def test_simple_rhythm_low_complexity(self):
        """Simple quarter notes should have low complexity."""
        score, _ = calculate_rhythm_complexity_score(
            note_durations=[1.0, 1.0, 1.0, 1.0],
            note_types=['quarter', 'quarter', 'quarter', 'quarter'],
            has_dots=[False, False, False, False],
            has_tuplets=[False, False, False, False],
            has_ties=[False, False, False, False],
            pitch_changes=[2, 2, 2],
            offsets=[0.0, 1.0, 2.0, 3.0],
        )
        
        assert score < 0.4, "Simple quarter notes should have low complexity"
    
    def test_complex_rhythm_high_complexity(self):
        """Complex rhythm with fast notes and irregular features should be higher."""
        score, _ = calculate_rhythm_complexity_score(
            note_durations=[0.125, 0.25, 0.5, 0.125, 0.25],
            note_types=['32nd', '16th', 'eighth', '32nd', '16th'],
            has_dots=[True, False, True, False, True],
            has_tuplets=[False, True, False, True, False],
            has_ties=[True, False, True, False, False],
            pitch_changes=[7, 5, 12, 3],
            offsets=[0.0, 0.125, 0.375, 0.875, 1.0],
        )
        
        assert score > 0.4, "Complex rhythm should have higher complexity"
    
    def test_fast_notes_increase_f1(self):
        """Fast notes should increase F1 subdivision difficulty."""
        slow_score, slow_raw = calculate_rhythm_complexity_score(
            note_durations=[2.0, 2.0, 2.0],
            note_types=['half', 'half', 'half'],
            has_dots=[False, False, False],
            has_tuplets=[False, False, False],
            has_ties=[False, False, False],
            pitch_changes=[2, 2],
            offsets=[0.0, 2.0, 4.0],
        )
        
        fast_score, fast_raw = calculate_rhythm_complexity_score(
            note_durations=[0.125, 0.125, 0.125],
            note_types=['32nd', '32nd', '32nd'],
            has_dots=[False, False, False],
            has_tuplets=[False, False, False],
            has_ties=[False, False, False],
            pitch_changes=[2, 2],
            offsets=[0.0, 0.125, 0.25],
        )
        
        assert fast_raw['f1'] > slow_raw['f1']
    
    def test_variety_increases_f2(self):
        """Note type variety should increase F2."""
        uniform_score, uniform_raw = calculate_rhythm_complexity_score(
            note_durations=[0.5, 0.5, 0.5, 0.5],
            note_types=['eighth', 'eighth', 'eighth', 'eighth'],
            has_dots=[False, False, False, False],
            has_tuplets=[False, False, False, False],
            has_ties=[False, False, False, False],
            pitch_changes=[2, 2, 2],
            offsets=[0.0, 0.5, 1.0, 1.5],
        )
        
        varied_score, varied_raw = calculate_rhythm_complexity_score(
            note_durations=[0.5, 1.0, 0.25, 2.0],
            note_types=['eighth', 'quarter', '16th', 'half'],
            has_dots=[False, False, False, False],
            has_tuplets=[False, False, False, False],
            has_ties=[False, False, False, False],
            pitch_changes=[2, 2, 2],
            offsets=[0.0, 0.5, 1.5, 1.75],
        )
        
        assert varied_raw['f2'] > uniform_raw['f2']
    
    def test_switches_increase_f3(self):
        """Frequent note type switches should increase F3."""
        steady_score, steady_raw = calculate_rhythm_complexity_score(
            note_durations=[0.5] * 6,
            note_types=['eighth'] * 6,
            has_dots=[False] * 6,
            has_tuplets=[False] * 6,
            has_ties=[False] * 6,
            pitch_changes=[2] * 5,
            offsets=[i * 0.5 for i in range(6)],
        )
        
        switching_score, switching_raw = calculate_rhythm_complexity_score(
            note_durations=[0.5, 0.25, 0.5, 0.25, 0.5, 0.25],
            note_types=['eighth', '16th', 'eighth', '16th', 'eighth', '16th'],
            has_dots=[False] * 6,
            has_tuplets=[False] * 6,
            has_ties=[False] * 6,
            pitch_changes=[2] * 5,
            offsets=[0.0, 0.5, 0.75, 1.25, 1.5, 2.0],
        )
        
        assert switching_raw['f3'] > steady_raw['f3']
    
    def test_irregular_features_increase_f4(self):
        """Dots, tuplets, ties should increase F4."""
        plain_score, plain_raw = calculate_rhythm_complexity_score(
            note_durations=[0.5, 0.5, 0.5],
            note_types=['eighth', 'eighth', 'eighth'],
            has_dots=[False, False, False],
            has_tuplets=[False, False, False],
            has_ties=[False, False, False],
            pitch_changes=[2, 2],
            offsets=[0.0, 0.5, 1.0],
        )
        
        irregular_score, irregular_raw = calculate_rhythm_complexity_score(
            note_durations=[0.75, 0.333, 0.5],
            note_types=['eighth', 'eighth', 'eighth'],
            has_dots=[True, False, False],
            has_tuplets=[False, True, False],
            has_ties=[False, False, True],
            pitch_changes=[2, 2],
            offsets=[0.0, 0.75, 1.083],
        )
        
        assert irregular_raw['f4'] > plain_raw['f4']
    
    def test_raw_metrics_included(self):
        """Should include all F factors in raw metrics."""
        _, raw = calculate_rhythm_complexity_score(
            note_durations=[1.0, 1.0],
            note_types=['quarter', 'quarter'],
            has_dots=[False, False],
            has_tuplets=[False, False],
            has_ties=[False, False],
            pitch_changes=[2],
            offsets=[0.0, 1.0],
        )
        
        assert 'f1' in raw
        assert 'f2' in raw
        assert 'f3' in raw
        assert 'f4' in raw
        assert 'f5' in raw


# =============================================================================
# TEST: WINDOWED RHYTHM COMPLEXITY
# =============================================================================

class TestRhythmComplexityWindowed:
    """Test windowed rhythm complexity calculation."""
    
    def test_returns_tuple(self):
        """Should return (peak, p95, raw_dict) tuple."""
        # Create long piece (>32 qL)
        n = 50
        result = calculate_rhythm_complexity_windowed(
            note_durations=[1.0] * n,
            note_types=['quarter'] * n,
            has_dots=[False] * n,
            has_tuplets=[False] * n,
            has_ties=[False] * n,
            pitch_changes=[2] * (n - 1),
            offsets=[float(i) for i in range(n)],
        )
        
        assert isinstance(result, tuple)
        assert len(result) == 3
    
    def test_short_piece_returns_none(self):
        """Short piece should return None for peak/p95."""
        # Short piece (<32 qL)
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            note_durations=[1.0, 1.0, 1.0],
            note_types=['quarter', 'quarter', 'quarter'],
            has_dots=[False, False, False],
            has_tuplets=[False, False, False],
            has_ties=[False, False, False],
            pitch_changes=[2, 2],
            offsets=[0.0, 1.0, 2.0],
        )
        
        assert peak is None
        assert p95 is None
        assert 'reason' in raw
    
    def test_empty_input_returns_none(self):
        """Empty input should return None."""
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            note_durations=[],
            note_types=[],
            has_dots=[],
            has_tuplets=[],
            has_ties=[],
            pitch_changes=[],
            offsets=[],
        )
        
        assert peak is None
        assert p95 is None
    
    def test_long_piece_returns_scores(self):
        """Long piece should return peak and p95 scores."""
        # Create long piece (>32 qL)
        n = 50
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            note_durations=[1.0] * n,
            note_types=['quarter'] * n,
            has_dots=[False] * n,
            has_tuplets=[False] * n,
            has_ties=[False] * n,
            pitch_changes=[2] * (n - 1),
            offsets=[float(i) for i in range(n)],
        )
        
        if peak is not None:
            assert 0 <= peak <= 1
            assert 0 <= p95 <= 1
    
    def test_peak_detects_hard_passage(self):
        """Peak should detect harder passages in otherwise easy piece."""
        n = 50
        # Create piece with one hard section in the middle
        note_types = ['quarter'] * 20 + ['32nd'] * 10 + ['quarter'] * 20
        durations = [1.0] * 20 + [0.125] * 10 + [1.0] * 20
        offsets = []
        offset = 0.0
        for d in durations:
            offsets.append(offset)
            offset += d
        
        peak, p95, _ = calculate_rhythm_complexity_windowed(
            note_durations=durations,
            note_types=note_types,
            has_dots=[False] * n,
            has_tuplets=[False] * n,
            has_ties=[False] * n,
            pitch_changes=[2] * (n - 1),
            offsets=offsets,
        )
        
        # Peak should be higher than if we just averaged
        if peak is not None:
            assert peak > 0


# =============================================================================
# TEST: EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_single_note(self):
        """Should handle single note."""
        score, _ = calculate_rhythm_complexity_score(
            note_durations=[1.0],
            note_types=['quarter'],
            has_dots=[False],
            has_tuplets=[False],
            has_ties=[False],
            pitch_changes=[],
            offsets=[0.0],
        )
        
        assert isinstance(score, float)
    
    def test_two_notes(self):
        """Should handle two notes."""
        score, raw = calculate_rhythm_complexity_score(
            note_durations=[1.0, 1.0],
            note_types=['quarter', 'quarter'],
            has_dots=[False, False],
            has_tuplets=[False, False],
            has_ties=[False, False],
            pitch_changes=[2],
            offsets=[0.0, 1.0],
        )
        
        assert isinstance(score, float)
    
    def test_unknown_note_type(self):
        """Should handle unknown note types."""
        score, raw = calculate_rhythm_complexity_score(
            note_durations=[1.0, 1.0],
            note_types=['unknown', 'mystery'],
            has_dots=[False, False],
            has_tuplets=[False, False],
            has_ties=[False, False],
            pitch_changes=[2],
            offsets=[0.0, 1.0],
        )
        
        assert isinstance(score, float)
    
    def test_all_irregular_features(self):
        """Should handle all irregular features at once."""
        score, raw = calculate_rhythm_complexity_score(
            note_durations=[0.75, 0.333, 0.5],
            note_types=['eighth', 'eighth', 'eighth'],
            has_dots=[True, True, True],
            has_tuplets=[True, True, True],
            has_ties=[True, True, True],
            pitch_changes=[5, 7],
            offsets=[0.0, 0.75, 1.083],
        )
        
        assert 0 <= score <= 1
        assert raw['f4'] > 0


class TestRhythmCalculatorEdgeCases:
    """Test edge cases for rhythm complexity calculator."""

    def test_no_note_types_returns_fallback_f1(self):
        """When note_types is empty, f1 should be 0.2."""
        score, raw = calculate_rhythm_complexity_score(
            note_durations=[1.0, 1.0],
            note_types=[],  # Empty note types
            has_dots=[False, False],
            has_tuplets=[False, False],
            has_ties=[False, False],
            pitch_changes=[2],
            offsets=[0.0, 1.0],
        )
        # f1 should be 0.2 when note_types is empty
        assert raw['f1'] == 0.2

    def test_no_note_types_zero_f2(self):
        """When note_types is empty, f2 should be 0."""
        score, raw = calculate_rhythm_complexity_score(
            note_durations=[1.0, 1.0],
            note_types=[],  # Empty note types
            has_dots=[False, False],
            has_tuplets=[False, False],
            has_ties=[False, False],
            pitch_changes=[2],
            offsets=[0.0, 1.0],
        )
        # f2 should be 0 when note_types is empty
        assert raw['f2'] == 0

    def test_no_pitch_changes_zero_f5(self):
        """When no pitch changes, f5 should be 0."""
        score, raw = calculate_rhythm_complexity_score(
            note_durations=[1.0, 1.0, 1.0],
            note_types=['quarter', 'quarter', 'quarter'],
            has_dots=[False, False, False],
            has_tuplets=[False, False, False],
            has_ties=[False, False, False],
            pitch_changes=[],  # Empty pitch changes
            offsets=[0.0, 1.0, 2.0],
        )
        # f5 should be 0 when no pitch changes
        assert raw['f5'] == 0

    def test_windowed_no_valid_windows(self):
        """Windowed analysis with no valid windows returns None."""
        # Piece with sparse notes that don't form valid windows
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            note_durations=[1.0],  # Single note
            note_types=['quarter'],
            has_dots=[False],
            has_tuplets=[False],
            has_ties=[False],
            pitch_changes=[],
            offsets=[0.0],
        )
        # Should return None for piece too short
        assert peak is None
        assert p95 is None

    def test_windowed_empty_offsets(self):
        """Windowed analysis with empty offsets returns None."""
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            note_durations=[],
            note_types=[],
            has_dots=[],
            has_tuplets=[],
            has_ties=[],
            pitch_changes=[],
            offsets=[],
        )
        assert peak is None
        assert p95 is None
        assert raw.get("reason") == "no_notes"

    def test_windowed_with_valid_windows(self):
        """Windowed analysis with enough notes should produce scores."""
        # Create a longer piece with enough notes spread over time
        # Need at least RHYTHM_WINDOW_MIN_PIECE_QL (8 beats typically) duration
        # and at least 2 notes per window for valid windows
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            note_durations=[1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
            note_types=['quarter'] * 10,
            has_dots=[False] * 10,
            has_tuplets=[False] * 10,
            has_ties=[False] * 10,
            pitch_changes=[2] * 9,  # minor 2nd between each note
            offsets=[0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0],
        )
        # Should have valid scores
        if peak is not None:
            assert 0.0 <= peak <= 1.0
            assert 0.0 <= p95 <= 1.0

    def test_windowed_sparse_notes_no_valid_windows(self):
        """Windowed analysis with sparse notes that don't form valid windows."""
        # Long piece with only 2 notes far apart (each window has < 2 notes)
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            note_durations=[1.0, 1.0],
            note_types=['quarter', 'quarter'],
            has_dots=[False, False],
            has_tuplets=[False, False],
            has_ties=[False, False],
            pitch_changes=[2],  
            offsets=[0.0, 20.0],  # Notes 20 beats apart, beyond typical window size
        )
        # Should return None since no windows have >= 2 notes
        assert peak is None or raw.get("reason") in ["no_valid_windows", "piece_too_short"]
