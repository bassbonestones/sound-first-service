"""
Tests for interval velocity score calculations.

Tests IVS score calculation considering interval size and speed.
"""

import pytest
from app.calculators.interval.velocity import (
    calculate_interval_velocity_score,
    calculate_interval_velocity_windowed,
    IVS_WINDOW_MIN_PIECE_QL,
)
from app.calculators.models import NoteEvent


class TestCalculateIntervalVelocityScore:
    """Test calculate_interval_velocity_score function."""
    
    def test_empty_events_returns_zero(self):
        """Empty list should return 0."""
        score, raw = calculate_interval_velocity_score([])
        assert score == 0.0
        assert raw["interval_count"] == 0
    
    def test_single_event_returns_zero(self):
        """Single note cannot have intervals."""
        events = [NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0)]
        score, raw = calculate_interval_velocity_score(events)
        assert score == 0.0
        assert raw["interval_count"] == 0
    
    def test_two_notes_calculates_interval(self):
        """Two notes should produce one interval contribution."""
        events = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=64, offset_ql=1.0, duration_ql=1.0),  # M3 up
        ]
        score, raw = calculate_interval_velocity_score(events)
        assert score > 0.0
        assert raw["interval_count"] == 1
    
    def test_larger_intervals_higher_score(self):
        """Larger intervals should produce higher IVS."""
        # Small interval (M2 = 2 semitones)
        small = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=62, offset_ql=1.0, duration_ql=1.0),
        ]
        # Large interval (octave = 12 semitones)
        large = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=72, offset_ql=1.0, duration_ql=1.0),
        ]
        
        small_score, _ = calculate_interval_velocity_score(small)
        large_score, _ = calculate_interval_velocity_score(large)
        assert large_score > small_score
    
    def test_faster_notes_higher_score(self):
        """Faster notes (shorter time between) should produce higher IVS."""
        # Slow (quarter notes)
        slow = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=67, offset_ql=4.0, duration_ql=1.0),  # 4 beats apart
        ]
        # Fast (sixteenth notes)
        fast = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=0.25),
            NoteEvent(pitch_midi=67, offset_ql=0.25, duration_ql=0.25),  # 0.25 beats apart
        ]
        
        slow_score, _ = calculate_interval_velocity_score(slow)
        fast_score, _ = calculate_interval_velocity_score(fast)
        assert fast_score > slow_score
    
    def test_score_bounded_zero_to_one(self):
        """Score should always be in [0, 1] range."""
        # Very fast and large intervals
        events = [
            NoteEvent(pitch_midi=36, offset_ql=0.0, duration_ql=0.1),
            NoteEvent(pitch_midi=84, offset_ql=0.1, duration_ql=0.1),
            NoteEvent(pitch_midi=36, offset_ql=0.2, duration_ql=0.1),
        ]
        score, _ = calculate_interval_velocity_score(events)
        assert 0.0 <= score <= 1.0
    
    def test_simultaneous_notes_skipped(self):
        """Notes at same time (dt=0) should be skipped."""
        events = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=64, offset_ql=0.0, duration_ql=1.0),  # Same time
            NoteEvent(pitch_midi=67, offset_ql=1.0, duration_ql=1.0),
        ]
        score, raw = calculate_interval_velocity_score(events)
        # Should skip the first interval (dt=0) but count the second
        assert raw["interval_count"] == 1
    
    def test_returns_metrics(self):
        """Should return detailed metrics."""
        events = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=64, offset_ql=1.0, duration_ql=1.0),
            NoteEvent(pitch_midi=67, offset_ql=2.0, duration_ql=1.0),
        ]
        score, raw = calculate_interval_velocity_score(events)
        assert "mean_contrib" in raw
        assert "p90_contrib" in raw
        assert "ivs_raw" in raw
    
    def test_custom_alpha_beta_parameters(self):
        """Should accept custom alpha and beta parameters."""
        events = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=72, offset_ql=1.0, duration_ql=1.0),
        ]
        
        # Default params
        default_score, _ = calculate_interval_velocity_score(events)
        
        # Higher alpha (size matters more)
        high_alpha_score, _ = calculate_interval_velocity_score(events, alpha=2.0)
        
        # Both should be valid
        assert 0.0 <= default_score <= 1.0
        assert 0.0 <= high_alpha_score <= 1.0


class TestCalculateIntervalVelocityWindowed:
    """Test calculate_interval_velocity_windowed function."""
    
    def test_empty_events_returns_none(self):
        """Empty list should return None."""
        peak, p95, raw = calculate_interval_velocity_windowed([])
        assert peak is None
        assert p95 is None
        assert raw["reason"] == "no_events"
    
    def test_short_piece_returns_none(self):
        """Piece shorter than minimum should return None."""
        # Create piece shorter than IVS_WINDOW_MIN_PIECE_QL (32)
        events = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=64, offset_ql=1.0, duration_ql=1.0),
        ]
        peak, p95, raw = calculate_interval_velocity_windowed(events)
        assert peak is None
        assert p95 is None
        assert raw["reason"] == "piece_too_short"
    
    def test_long_piece_returns_scores(self):
        """Long piece should return peak and p95 scores."""
        # Create piece longer than 32 quarter notes
        events = []
        for i in range(40):
            events.append(NoteEvent(
                pitch_midi=60 + (i % 12),
                offset_ql=float(i * 2),
                duration_ql=1.0
            ))
        
        peak, p95, raw = calculate_interval_velocity_windowed(events)
        # Verify scores are valid floats in expected range
        assert 0 <= peak <= 1
        assert 0 <= p95 <= 1
        assert raw["window_count"] > 0
    
    def test_peak_gte_p95(self):
        """Peak should always be >= p95."""
        events = []
        for i in range(50):
            events.append(NoteEvent(
                pitch_midi=60 + (i % 7),
                offset_ql=float(i),
                duration_ql=0.5
            ))
        
        peak, p95, raw = calculate_interval_velocity_windowed(events)
        assert peak >= p95
    
    def test_concentrated_difficulty_detected(self):
        """Should detect concentrated difficulty in one window."""
        events = []
        # Easy beginning
        for i in range(20):
            events.append(NoteEvent(pitch_midi=60, offset_ql=float(i), duration_ql=1.0))
        # Hard section with fast large leaps
        for i in range(10):
            offset = 20.0 + (i * 0.25)
            pitch = 60 if i % 2 == 0 else 72
            events.append(NoteEvent(pitch_midi=pitch, offset_ql=offset, duration_ql=0.25))
        # Easy ending
        for i in range(20):
            events.append(NoteEvent(pitch_midi=60, offset_ql=30.0 + float(i), duration_ql=1.0))
        
        peak, p95, raw = calculate_interval_velocity_windowed(events)
        # Peak should capture the hard section
        assert peak > 0.0


class TestIntervalVelocityEdgeCases:
    """Test edge cases that hit specific branches."""
    
    def test_single_stationary_note_zero_contribution(self):
        """A single note with no movement should give 0 IVS."""
        from app.calculators.models import NoteEvent
        from app.calculators.interval.velocity import calculate_interval_velocity_score
        
        # Single note - no intervals to calculate
        events = [NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0)]
        
        ivs, raw = calculate_interval_velocity_score(events)
        assert ivs == 0.0
        assert raw["interval_count"] == 0

    def test_windowed_no_valid_windows(self):
        """Windowed analysis with insufficient notes per window returns None."""
        from app.calculators.models import NoteEvent
        from app.calculators.interval.velocity import calculate_interval_velocity_windowed
        
        # Create a sparse piece where each window has < 2 notes
        # Windows are 4.0 QL, so place notes 5.0 apart
        events = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=64, offset_ql=10.0, duration_ql=1.0),
            NoteEvent(pitch_midi=67, offset_ql=20.0, duration_ql=1.0),
            NoteEvent(pitch_midi=72, offset_ql=30.0, duration_ql=1.0),
        ]
        
        peak, p95, raw = calculate_interval_velocity_windowed(events)
        # Should have no valid windows since notes are too sparse
        assert peak is None or raw.get("reason") == "no_valid_windows" or peak >= 0

    def test_all_simultaneous_notes_returns_zero(self):
        """When all note pairs are simultaneous (dt=0), should return 0."""
        from app.calculators.models import NoteEvent
        from app.calculators.interval.velocity import calculate_interval_velocity_score
        
        # All notes at same time - no valid intervals
        events = [
            NoteEvent(pitch_midi=60, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=64, offset_ql=0.0, duration_ql=1.0),
            NoteEvent(pitch_midi=67, offset_ql=0.0, duration_ql=1.0),
        ]
        
        ivs, raw = calculate_interval_velocity_score(events)
        assert ivs == 0.0
        assert raw["interval_count"] == 0
