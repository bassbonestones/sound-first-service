"""Tests for rhythm_applicator module.

Tests all rhythm application functions to ensure correct
timing and duration calculations.
"""

import pytest
from typing import List

from app.schemas.generation_schemas import PitchEvent, RhythmType
from app.services.generation.rhythm_applicator import (
    apply_rhythm,
    apply_rhythm_with_repeats,
    get_duration,
    get_cell_info,
    calculate_total_duration,
    calculate_measures,
    get_supported_rhythms,
    beats_to_seconds,
    seconds_to_beats,
    quantize_to_grid,
    create_rest_event,
    insert_rests_between_groups,
    RHYTHM_CELLS,
    QUARTER_NOTE,
    HALF_NOTE,
    WHOLE_NOTE,
    EIGHTH_NOTE,
    SIXTEENTH_NOTE,
    DOTTED_QUARTER,
    SWING_LONG,
    SWING_SHORT,
)


# =============================================================================
# Helper Functions
# =============================================================================


def notes_only(events: List[PitchEvent]) -> List[PitchEvent]:
    """Filter out rest events (midi_note=0) to get only note events."""
    return [e for e in events if e.midi_note != 0]


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def c_major_pitches() -> List[int]:
    """C major scale: C4 to C5."""
    return [60, 62, 64, 65, 67, 69, 71, 72]


@pytest.fixture
def triad_pitches() -> List[int]:
    """C major triad."""
    return [60, 64, 67]


# =============================================================================
# Test Duration Constants
# =============================================================================


class TestDurationConstants:
    """Verify duration constant values."""

    def test_whole_note(self) -> None:
        assert WHOLE_NOTE == 4.0

    def test_half_note(self) -> None:
        assert HALF_NOTE == 2.0

    def test_quarter_note(self) -> None:
        assert QUARTER_NOTE == 1.0

    def test_eighth_note(self) -> None:
        assert EIGHTH_NOTE == 0.5

    def test_sixteenth_note(self) -> None:
        assert SIXTEENTH_NOTE == 0.25

    def test_dotted_quarter(self) -> None:
        assert DOTTED_QUARTER == 1.5

    def test_swing_ratio(self) -> None:
        # Swing pair should equal 1 beat total
        assert SWING_LONG + SWING_SHORT == pytest.approx(1.0)
        # Standard swing is 2:1 ratio
        assert SWING_LONG / SWING_SHORT == pytest.approx(2.0)


# =============================================================================
# Test Rhythm Cells
# =============================================================================


class TestRhythmCells:
    """Test rhythm cell definitions."""

    def test_all_rhythm_types_defined(self) -> None:
        """All RhythmType values should have a cell definition."""
        for rhythm in RhythmType:
            assert rhythm in RHYTHM_CELLS

    def test_quarter_note_cell(self) -> None:
        cell = RHYTHM_CELLS[RhythmType.QUARTER_NOTES]
        assert cell.durations == (QUARTER_NOTE,)
        assert cell.cell_length == 1.0
        assert cell.notes_per_cell == 1

    def test_swing_eighths_cell(self) -> None:
        cell = RHYTHM_CELLS[RhythmType.SWING_EIGHTHS]
        assert len(cell.durations) == 2
        assert cell.cell_length == pytest.approx(1.0)

    def test_syncopated_cell(self) -> None:
        cell = RHYTHM_CELLS[RhythmType.SYNCOPATED]
        # Syncopated: 8th-quarter-quarter-quarter-8th = 5 notes
        assert len(cell.durations) == 5
        # 0.5 + 1.0 + 1.0 + 1.0 + 0.5 = 4.0
        assert cell.cell_length == pytest.approx(4.0)


# =============================================================================
# Test apply_rhythm
# =============================================================================


class TestApplyRhythm:
    """Tests for the apply_rhythm function."""

    def test_quarter_notes_timing(self, c_major_pitches: List[int]) -> None:
        events = apply_rhythm(c_major_pitches, RhythmType.QUARTER_NOTES)
        
        assert len(events) == 8
        # Check all durations are quarter notes
        for event in events:
            assert event.duration_beats == 1.0
        
        # Check sequential offsets
        for i, event in enumerate(events):
            assert event.offset_beats == float(i)

    def test_eighth_notes_timing(self, c_major_pitches: List[int]) -> None:
        events = apply_rhythm(c_major_pitches, RhythmType.EIGHTH_NOTES)
        note_events = notes_only(events)
        
        # 8 original scale notes + 1 final "do" = 9 notes
        # C5 at offset 3.5 STARTS off-beat, so:
        # - Keep its 0.5 duration (fills to beat 4)
        # - Add quarter "do" (C5) on beat 4
        assert len(note_events) == 9
        # All notes are 8ths except final note at 3.5 and added do
        for event in note_events[:-2]:
            assert event.duration_beats == 0.5
        # C5 at offset 3.5 keeps 0.5 duration
        assert note_events[-2].duration_beats == 0.5
        assert note_events[-2].offset_beats == 3.5
        # Final do (C5) at beat 4.0 with quarter duration
        assert note_events[-1].duration_beats == 1.0
        assert note_events[-1].offset_beats == 4.0
        assert note_events[-1].midi_note == note_events[-2].midi_note  # Same pitch

    def test_whole_notes_timing(self, triad_pitches: List[int]) -> None:
        events = apply_rhythm(triad_pitches, RhythmType.WHOLE_NOTES)
        
        assert len(events) == 3
        for event in events:
            assert event.duration_beats == 4.0
        
        # Check offsets: 0.0, 4.0, 8.0
        assert events[0].offset_beats == 0.0
        assert events[1].offset_beats == 4.0
        assert events[2].offset_beats == 8.0

    def test_swing_eighths_timing(self) -> None:
        pitches = [60, 62, 64, 65]  # 4 notes
        events = apply_rhythm(pitches, RhythmType.SWING_EIGHTHS)
        note_events = notes_only(events)
        
        # 4 original + 1 final "do" = 5 notes
        # F4 at offset 1.667 STARTS off-beat, so:
        # - Keep its 0.333 duration (fills to beat 2)
        # - Add quarter "do" (F4) on beat 2
        assert len(note_events) == 5
        assert note_events[0].duration_beats == pytest.approx(SWING_LONG)
        assert note_events[1].duration_beats == pytest.approx(SWING_SHORT)
        assert note_events[2].duration_beats == pytest.approx(SWING_LONG)
        # F4 at offset 1.667 keeps its swing short duration
        assert note_events[3].duration_beats == pytest.approx(SWING_SHORT)
        # Final do (F4) at beat 2.0 with quarter duration
        assert note_events[4].duration_beats == pytest.approx(QUARTER_NOTE)
        assert note_events[4].offset_beats == pytest.approx(2.0)

    def test_dotted_pattern(self) -> None:
        pitches = [60, 62, 64, 65]
        events = apply_rhythm(pitches, RhythmType.DOTTED_QUARTER_EIGHTH)
        note_events = notes_only(events)
        
        # Pattern: dotted quarter (1.5), eighth (0.5), ...
        # 4 notes: C4 at 0 (1.5), D4 at 1.5 (0.5), E4 at 2.0 (1.5), F4 at 3.5 (0.5)
        # F4 at offset 3.5 STARTS off-beat, so:
        # - Keep its 0.5 duration (fills to beat 4)
        # - Add quarter "do" (F4) on beat 4
        assert len(note_events) == 5
        assert note_events[0].duration_beats == pytest.approx(DOTTED_QUARTER)
        assert note_events[1].duration_beats == pytest.approx(EIGHTH_NOTE)
        assert note_events[2].duration_beats == pytest.approx(DOTTED_QUARTER)
        # F4 at offset 3.5 keeps its 0.5 duration
        assert note_events[3].duration_beats == pytest.approx(EIGHTH_NOTE)
        # Final do (F4) at beat 4.0 with quarter duration
        assert note_events[4].duration_beats == pytest.approx(QUARTER_NOTE)
        assert note_events[4].offset_beats == pytest.approx(4.0)

    def test_syncopated_pattern(self) -> None:
        pitches = [60, 62, 64]  # 3 notes for partial syncopated cell
        events = apply_rhythm(pitches, RhythmType.SYNCOPATED)
        note_events = notes_only(events)
        
        # Syncopated cell is 8th-Q-Q-Q-8th (5 notes per 4 beats)
        # With 3 notes: uses first 3 durations (8th, Q, Q)
        # C4 at 0.0 (0.5), D4 at 0.5 (1.0), E4 at 1.5 (1.0)
        # E4 at offset 1.5 STARTS off-beat (0.5 into beat 2), so:
        # - SHORTEN to 0.5 to end exactly on beat 2
        # - Add quarter "do" on beat 2.0
        assert len(note_events) == 4  # 3 original + 1 final do
        assert note_events[0].duration_beats == EIGHTH_NOTE  # C4
        assert note_events[1].duration_beats == QUARTER_NOTE  # D4
        assert note_events[2].duration_beats == pytest.approx(0.5)  # E4 shortened to end on beat 2
        assert note_events[3].duration_beats == QUARTER_NOTE  # Final do (E4) on beat 2
        assert note_events[3].offset_beats == pytest.approx(2.0)

    def test_preserves_pitch_values(self, c_major_pitches: List[int]) -> None:
        events = apply_rhythm(c_major_pitches, RhythmType.QUARTER_NOTES)
        
        pitches_out = [e.midi_note for e in events]
        assert pitches_out == c_major_pitches

    def test_empty_list(self) -> None:
        events = apply_rhythm([], RhythmType.QUARTER_NOTES)
        assert events == []

    def test_single_note(self) -> None:
        events = apply_rhythm([60], RhythmType.QUARTER_NOTES)
        note_events = notes_only(events)
        assert len(note_events) == 1
        assert note_events[0].midi_note == 60
        assert note_events[0].offset_beats == 0.0

    def test_with_pitch_names(self) -> None:
        pitches = [60, 62, 64]
        names = ["C4", "D4", "E4"]
        events = apply_rhythm(pitches, RhythmType.QUARTER_NOTES, pitch_names=names)
        
        assert events[0].pitch_name == "C4"
        assert events[1].pitch_name == "D4"
        assert events[2].pitch_name == "E4"

    def test_min_final_duration_extends_short_notes(self) -> None:
        """Final note should be extended to min_final_duration."""
        pitches = [60, 62, 64, 65]
        events = apply_rhythm(pitches, RhythmType.SIXTEENTH_NOTES)
        note_events = notes_only(events)
        
        # All sixteenths except last which is extended to quarter
        for event in note_events[:-1]:
            assert event.duration_beats == SIXTEENTH_NOTE
        assert note_events[-1].duration_beats == QUARTER_NOTE  # Extended

    def test_min_final_duration_respects_longer_notes(self) -> None:
        """Final note already >= min_final_duration should not change."""
        pitches = [60, 62, 64]
        events = apply_rhythm(pitches, RhythmType.HALF_NOTES)
        
        # Half notes are longer than quarter, should stay as half
        for event in events:
            assert event.duration_beats == HALF_NOTE

    def test_min_final_duration_disabled(self) -> None:
        """Can disable min_final_duration by setting to 0."""
        pitches = [60, 62, 64, 65]
        events = apply_rhythm(
            pitches, RhythmType.SIXTEENTH_NOTES, min_final_duration=0.0
        )
        note_events = notes_only(events)
        
        # All sixteenths when min_final_duration is 0
        for event in note_events:
            assert event.duration_beats == SIXTEENTH_NOTE


# =============================================================================
# Test apply_rhythm_with_repeats
# =============================================================================


class TestApplyRhythmWithRepeats:
    """Tests for the apply_rhythm_with_repeats function."""

    def test_repeat_count_1(self, triad_pitches: List[int]) -> None:
        events = apply_rhythm_with_repeats(
            triad_pitches, RhythmType.QUARTER_NOTES, repeat_count=1
        )
        note_events = notes_only(events)
        assert len(note_events) == 3

    def test_repeat_count_2(self, triad_pitches: List[int]) -> None:
        events = apply_rhythm_with_repeats(
            triad_pitches, RhythmType.QUARTER_NOTES, repeat_count=2
        )
        note_events = notes_only(events)
        assert len(note_events) == 6
        
        # First pass
        assert note_events[0].offset_beats == 0.0
        assert note_events[1].offset_beats == 1.0
        assert note_events[2].offset_beats == 2.0
        
        # Second pass starts after first (3 beats total)
        assert note_events[3].offset_beats == 3.0
        assert note_events[4].offset_beats == 4.0
        assert note_events[5].offset_beats == 5.0

    def test_repeat_count_3(self, triad_pitches: List[int]) -> None:
        events = apply_rhythm_with_repeats(
            triad_pitches, RhythmType.QUARTER_NOTES, repeat_count=3
        )
        note_events = notes_only(events)
        assert len(note_events) == 9
        
        # Third pass should start at beat 6
        assert note_events[6].offset_beats == 6.0

    def test_repeat_preserves_pitches(self, triad_pitches: List[int]) -> None:
        events = apply_rhythm_with_repeats(
            triad_pitches, RhythmType.QUARTER_NOTES, repeat_count=2
        )
        note_events = notes_only(events)
        
        pitches_out = [e.midi_note for e in note_events]
        assert pitches_out == triad_pitches * 2

    def test_repeat_zero_defaults_to_1(self, triad_pitches: List[int]) -> None:
        events = apply_rhythm_with_repeats(
            triad_pitches, RhythmType.QUARTER_NOTES, repeat_count=0
        )
        note_events = notes_only(events)
        assert len(note_events) == 3


# =============================================================================
# Test Helper Functions
# =============================================================================


class TestGetDuration:
    """Tests for get_duration function."""

    def test_quarter_note_duration(self) -> None:
        assert get_duration(RhythmType.QUARTER_NOTES) == 1.0

    def test_eighth_note_duration(self) -> None:
        assert get_duration(RhythmType.EIGHTH_NOTES) == 0.5

    def test_whole_note_duration(self) -> None:
        assert get_duration(RhythmType.WHOLE_NOTES) == 4.0


class TestGetCellInfo:
    """Tests for get_cell_info function."""

    def test_quarter_notes_cell(self) -> None:
        length, notes = get_cell_info(RhythmType.QUARTER_NOTES)
        assert length == 1.0
        assert notes == 1

    def test_swing_eighths_cell(self) -> None:
        length, notes = get_cell_info(RhythmType.SWING_EIGHTHS)
        assert length == pytest.approx(1.0)
        assert notes == 2

    def test_syncopated_cell(self) -> None:
        length, notes = get_cell_info(RhythmType.SYNCOPATED)
        # Syncopated: 8th-quarter-quarter-quarter-8th = 5 notes, 4 beats
        assert length == pytest.approx(4.0)
        assert notes == 5


class TestCalculateTotalDuration:
    """Tests for calculate_total_duration function."""

    def test_quarter_notes(self) -> None:
        duration = calculate_total_duration(8, RhythmType.QUARTER_NOTES)
        assert duration == 8.0

    def test_eighth_notes(self) -> None:
        duration = calculate_total_duration(8, RhythmType.EIGHTH_NOTES)
        assert duration == 4.0

    def test_zero_pitches(self) -> None:
        duration = calculate_total_duration(0, RhythmType.QUARTER_NOTES)
        assert duration == 0.0

    def test_swing_eighths(self) -> None:
        # 4 swing notes = 2 pairs = 2 beats
        duration = calculate_total_duration(4, RhythmType.SWING_EIGHTHS)
        assert duration == pytest.approx(2.0)


class TestCalculateMeasures:
    """Tests for calculate_measures function."""

    def test_8_quarter_notes_in_4_4(self) -> None:
        measures = calculate_measures(8, RhythmType.QUARTER_NOTES, 4)
        assert measures == 2.0

    def test_16_eighth_notes_in_4_4(self) -> None:
        measures = calculate_measures(16, RhythmType.EIGHTH_NOTES, 4)
        assert measures == 2.0

    def test_12_eighth_notes_in_3_4(self) -> None:
        # 12 eighths = 6 beats / 3 beats per measure = 2 measures
        measures = calculate_measures(12, RhythmType.EIGHTH_NOTES, 3)
        assert measures == 2.0


class TestTempoConversions:
    """Tests for tempo conversion functions."""

    def test_beats_to_seconds_120bpm(self) -> None:
        # At 120 BPM, 1 beat = 0.5 seconds
        seconds = beats_to_seconds(1.0, 120.0)
        assert seconds == 0.5

    def test_beats_to_seconds_60bpm(self) -> None:
        # At 60 BPM, 1 beat = 1.0 second
        seconds = beats_to_seconds(1.0, 60.0)
        assert seconds == 1.0

    def test_seconds_to_beats_120bpm(self) -> None:
        beats = seconds_to_beats(0.5, 120.0)
        assert beats == 1.0

    def test_seconds_to_beats_roundtrip(self) -> None:
        original_beats = 3.5
        tempo = 100.0
        seconds = beats_to_seconds(original_beats, tempo)
        back_to_beats = seconds_to_beats(seconds, tempo)
        assert back_to_beats == pytest.approx(original_beats)

    def test_invalid_tempo_raises(self) -> None:
        with pytest.raises(ValueError):
            beats_to_seconds(1.0, 0.0)
        with pytest.raises(ValueError):
            beats_to_seconds(1.0, -60.0)
        with pytest.raises(ValueError):
            seconds_to_beats(1.0, 0.0)


class TestQuantize:
    """Tests for quantize_to_grid function."""

    def test_quantize_to_sixteenth(self) -> None:
        # 0.12 should round to 0.0 (closer than 0.25)
        assert quantize_to_grid(0.12) == 0.0
        # 0.13 should round to 0.25
        assert quantize_to_grid(0.13) == 0.25
        # 0.6 should round to 0.5
        assert quantize_to_grid(0.6) == 0.5

    def test_quantize_to_eighth(self) -> None:
        assert quantize_to_grid(0.4, 0.5) == 0.5
        assert quantize_to_grid(0.2, 0.5) == 0.0

    def test_exact_values_unchanged(self) -> None:
        assert quantize_to_grid(0.25) == 0.25
        assert quantize_to_grid(0.5) == 0.5
        assert quantize_to_grid(1.0) == 1.0


class TestRestFunctions:
    """Tests for rest-related functions."""

    def test_create_rest_event(self) -> None:
        rest = create_rest_event(1.0, 4.0)
        assert rest.midi_note == 0
        assert rest.pitch_name == "rest"
        assert rest.duration_beats == 1.0
        assert rest.offset_beats == 4.0

    def test_insert_rests_between_groups(self) -> None:
        events = [
            PitchEvent(midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0),
            PitchEvent(midi_note=62, pitch_name="D4", duration_beats=1.0, offset_beats=1.0),
            PitchEvent(midi_note=64, pitch_name="E4", duration_beats=1.0, offset_beats=2.0),
            PitchEvent(midi_note=65, pitch_name="F4", duration_beats=1.0, offset_beats=3.0),
        ]
        
        result = insert_rests_between_groups(events, group_size=2, rest_duration=0.5)
        
        # Should have: note, note, rest, note, note
        assert len(result) == 5
        # First two events unchanged
        assert result[0].midi_note == 60
        assert result[1].midi_note == 62
        # Rest inserted
        assert result[2].midi_note == 0
        assert result[2].duration_beats == 0.5
        # Next two events offset by rest duration
        assert result[3].midi_note == 64
        assert result[3].offset_beats == 2.0 + 0.5
        assert result[4].midi_note == 65

    def test_insert_rests_empty_list(self) -> None:
        result = insert_rests_between_groups([], group_size=2, rest_duration=0.5)
        assert result == []


class TestGetSupportedRhythms:
    """Tests for get_supported_rhythms function."""

    def test_returns_all_rhythms(self) -> None:
        rhythms = get_supported_rhythms()
        assert len(rhythms) == len(RHYTHM_CELLS)
        assert RhythmType.QUARTER_NOTES in rhythms
        assert RhythmType.SWING_EIGHTHS in rhythms
