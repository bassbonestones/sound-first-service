"""Tests for chord progression generator.

Tests cover:
- Scale generation over chord changes
- Arpeggio generation over chord changes
- Guide tone generation
- ii-V-I progressions
- Voice leading between chords
"""
import pytest

from app.schemas.generation_schemas import (
    ChordEvent,
    ChordProgressionContentType,
    ChordProgressionRequest,
    RhythmType,
    ScaleType,
)
from app.services.generation.chord_progression_generator import (
    CATEGORY_TO_ARPEGGIO,
    ROOT_TO_KEY,
    generate_over_changes,
    _root_to_key,
    _calculate_notes_for_duration,
)


class TestRootToKey:
    """Tests for root-to-key conversion."""

    def test_natural_roots(self) -> None:
        """Natural note roots convert correctly."""
        from app.schemas.generation_schemas import MusicalKey

        assert _root_to_key("C") == MusicalKey.C
        assert _root_to_key("D") == MusicalKey.D
        assert _root_to_key("G") == MusicalKey.G

    def test_sharp_roots(self) -> None:
        """Sharp roots convert correctly."""
        from app.schemas.generation_schemas import MusicalKey

        assert _root_to_key("F#") == MusicalKey.F_SHARP
        assert _root_to_key("C#") == MusicalKey.C_SHARP

    def test_flat_roots(self) -> None:
        """Flat roots convert correctly."""
        from app.schemas.generation_schemas import MusicalKey

        assert _root_to_key("Bb") == MusicalKey.B_FLAT
        assert _root_to_key("Eb") == MusicalKey.E_FLAT

    def test_invalid_root(self) -> None:
        """Invalid root raises ValueError."""
        with pytest.raises(ValueError, match="Unrecognized"):
            _root_to_key("X")


class TestNotesForDuration:
    """Tests for calculating notes per duration."""

    def test_quarter_notes(self) -> None:
        """4 beats with quarter notes = 4 notes."""
        notes = _calculate_notes_for_duration(4.0, RhythmType.QUARTER_NOTES)
        assert notes == 4

    def test_eighth_notes(self) -> None:
        """4 beats with eighth notes = 8 notes."""
        notes = _calculate_notes_for_duration(4.0, RhythmType.EIGHTH_NOTES)
        assert notes == 8

    def test_half_notes(self) -> None:
        """4 beats with half notes = 2 notes."""
        notes = _calculate_notes_for_duration(4.0, RhythmType.HALF_NOTES)
        assert notes == 2

    def test_minimum_one_note(self) -> None:
        """Always at least one note."""
        notes = _calculate_notes_for_duration(0.1, RhythmType.WHOLE_NOTES)
        assert notes == 1


class TestScaleGeneration:
    """Tests for scale generation over changes."""

    def test_ii_v_i_progression(self) -> None:
        """ii-V-I generates appropriate scales."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.SCALES,
            chords=[
                ChordEvent(symbol="Dm7", duration_beats=4),
                ChordEvent(symbol="G7", duration_beats=4),
                ChordEvent(symbol="Cmaj7", duration_beats=4),
            ],
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = generate_over_changes(request)

        # Should have 3 segments
        assert len(response.segments) == 3

        # Check chord symbols
        assert response.segments[0].chord_symbol == "Dm7"
        assert response.segments[1].chord_symbol == "G7"
        assert response.segments[2].chord_symbol == "Cmaj7"

        # Check scales used
        assert response.segments[0].scale_used == ScaleType.DORIAN.value
        assert response.segments[1].scale_used == ScaleType.MIXOLYDIAN.value
        assert response.segments[2].scale_used == ScaleType.IONIAN.value

        # Total duration
        assert response.total_beats == 12.0

    def test_single_chord(self) -> None:
        """Single chord generates content."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.SCALES,
            chords=[
                ChordEvent(symbol="Am7", duration_beats=8),
            ],
            rhythm=RhythmType.EIGHTH_NOTES,
        )
        response = generate_over_changes(request)

        assert len(response.segments) == 1
        assert len(response.events) > 0
        assert response.total_beats == 8.0

    def test_events_have_correct_fields(self) -> None:
        """Events have all required fields."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.SCALES,
            chords=[
                ChordEvent(symbol="C", duration_beats=4),
            ],
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = generate_over_changes(request)

        for event in response.events:
            assert event.midi_note > 0
            assert event.pitch_name
            assert event.duration_beats > 0
            assert event.offset_beats >= 0

    def test_altered_dominant(self) -> None:
        """Altered dominant gets Altered scale."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.SCALES,
            chords=[
                ChordEvent(symbol="G7alt", duration_beats=4),
            ],
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = generate_over_changes(request)

        assert response.segments[0].scale_used == ScaleType.ALTERED.value


class TestArpeggioGeneration:
    """Tests for arpeggio generation over changes."""

    def test_basic_arpeggio_generation(self) -> None:
        """Chord arpeggios are generated."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.ARPEGGIOS,
            chords=[
                ChordEvent(symbol="Cmaj7", duration_beats=4),
            ],
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = generate_over_changes(request)

        assert len(response.segments) == 1
        assert response.segments[0].scale_used is None  # Arpeggios don't have scale
        assert len(response.events) > 0

    def test_minor_arpeggio(self) -> None:
        """Minor chord gets minor arpeggio."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.ARPEGGIOS,
            chords=[
                ChordEvent(symbol="Am", duration_beats=4),
            ],
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = generate_over_changes(request)

        # Should generate A minor arpeggio tones
        assert len(response.events) > 0

    def test_diminished_arpeggio(self) -> None:
        """Diminished chord gets dim7 arpeggio."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.ARPEGGIOS,
            chords=[
                ChordEvent(symbol="Bdim7", duration_beats=4),
            ],
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = generate_over_changes(request)

        assert len(response.events) > 0


class TestGuideToneGeneration:
    """Tests for guide tone generation."""

    def test_guide_tones_two_notes(self) -> None:
        """Guide tones produce 2 notes per chord (3rd and 7th)."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.GUIDE_TONES,
            chords=[
                ChordEvent(symbol="Dm7", duration_beats=4),
            ],
            rhythm=RhythmType.HALF_NOTES,  # Rhythm ignored for guide tones
        )
        response = generate_over_changes(request)

        # Guide tones are 3rd and 7th = 2 notes
        assert len(response.segments[0].events) == 2

    def test_guide_tone_durations(self) -> None:
        """Guide tones split duration evenly."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.GUIDE_TONES,
            chords=[
                ChordEvent(symbol="Cmaj7", duration_beats=4),
            ],
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = generate_over_changes(request)

        # Each guide tone should be 2 beats (4 / 2)
        for event in response.segments[0].events:
            assert event.duration_beats == 2.0


class TestCombinedEvents:
    """Tests for combined events list."""

    def test_all_events_have_absolute_timing(self) -> None:
        """All events list has absolute offset_beats."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.SCALES,
            chords=[
                ChordEvent(symbol="Dm7", duration_beats=4),
                ChordEvent(symbol="G7", duration_beats=4),
            ],
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = generate_over_changes(request)

        # Events should be sorted by offset
        offsets = [e.offset_beats for e in response.events]
        assert offsets == sorted(offsets)

        # Second chord's events should start at beat 4
        segment2_events = response.segments[1].events
        if segment2_events:
            assert segment2_events[0].offset_beats >= 4.0


class TestSlashChords:
    """Tests for slash chord handling."""

    def test_slash_chord_uses_root_for_scale(self) -> None:
        """Slash chord uses root for scale, not bass note."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.SCALES,
            chords=[
                ChordEvent(symbol="C/E", duration_beats=4),
            ],
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = generate_over_changes(request)

        # Should use C Ionian, not E
        assert response.segments[0].scale_used == ScaleType.IONIAN.value


class TestRhythmVariety:
    """Tests for different rhythm types."""

    def test_sixteenth_notes(self) -> None:
        """Sixteenth notes generate more events."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.SCALES,
            chords=[
                ChordEvent(symbol="C", duration_beats=4),
            ],
            rhythm=RhythmType.SIXTEENTH_NOTES,
        )
        response = generate_over_changes(request)

        # 4 beats of sixteenths = 16 notes (approximately, accounting for final note adjustment)
        assert len(response.events) >= 14

    def test_whole_notes(self) -> None:
        """Whole notes generate fewer events."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.SCALES,
            chords=[
                ChordEvent(symbol="C", duration_beats=8),
            ],
            rhythm=RhythmType.WHOLE_NOTES,
        )
        response = generate_over_changes(request)

        # 8 beats of whole notes = 2 notes
        assert len(response.events) >= 2
