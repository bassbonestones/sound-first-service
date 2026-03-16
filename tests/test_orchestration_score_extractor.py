"""
Tests for orchestration/score_extractor.py

Tests for extract_note_data function that extracts note data from music21 scores.
"""

import pytest

try:
    from music21 import stream, note, chord, key, meter
    from app.calculators.orchestration.score_extractor import (
        extract_note_data,
        MUSIC21_AVAILABLE,
    )
    MUSIC21_OK = MUSIC21_AVAILABLE
except ImportError:
    MUSIC21_OK = False


@pytest.fixture
def simple_score():
    """Create a simple music21 score with C-D-E-F."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    
    for pitch in ["C4", "D4", "E4", "F4"]:
        n = note.Note(pitch)
        n.duration.quarterLength = 1.0
        m.append(n)
    
    p.append(m)
    s.append(p)
    return s


@pytest.fixture
def score_with_accidentals():
    """Score with accidentals (C major key with F#)."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    
    # Add key signature
    ks = key.KeySignature(0)  # C major
    m.insert(0, ks)
    
    # C, D, F#, G - F# is accidental in C major
    for pitch in ["C4", "D4", "F#4", "G4"]:
        n = note.Note(pitch)
        n.duration.quarterLength = 1.0
        m.append(n)
    
    p.append(m)
    s.append(p)
    return s


@pytest.fixture
def score_with_chord():
    """Score with a chord."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    
    # Single note, then chord
    n = note.Note("C4")
    n.duration.quarterLength = 1.0
    m.append(n)
    
    c = chord.Chord(["E4", "G4", "C5"])
    c.duration.quarterLength = 1.0
    m.append(c)
    
    p.append(m)
    s.append(p)
    return s


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestExtractNoteDataReturns:
    """Tests for extract_note_data return structure."""

    def test_returns_dict(self, simple_score):
        """Should return a dictionary."""
        result = extract_note_data(simple_score)
        assert isinstance(result, dict)

    def test_contains_pitch_class_count(self, simple_score):
        """Should include pitch_class_count."""
        result = extract_note_data(simple_score)
        assert "pitch_class_count" in result
        assert isinstance(result["pitch_class_count"], int)

    def test_contains_note_steps(self, simple_score):
        """Should include note_steps list."""
        result = extract_note_data(simple_score)
        assert "note_steps" in result
        assert isinstance(result["note_steps"], list)

    def test_contains_accidental_count(self, simple_score):
        """Should include accidental_count."""
        result = extract_note_data(simple_score)
        assert "accidental_count" in result
        assert isinstance(result["accidental_count"], int)

    def test_contains_total_notes(self, simple_score):
        """Should include total_notes."""
        result = extract_note_data(simple_score)
        assert "total_notes" in result
        assert isinstance(result["total_notes"], int)

    def test_contains_interval_data(self, simple_score):
        """Should include interval data."""
        result = extract_note_data(simple_score)
        assert "interval_semitones" in result
        assert "interval_offsets" in result
        assert "interval_measure_numbers" in result
        assert isinstance(result["interval_semitones"], list)

    def test_contains_note_events(self, simple_score):
        """Should include note_events list."""
        result = extract_note_data(simple_score)
        assert "note_events" in result
        assert isinstance(result["note_events"], list)

    def test_contains_rhythm_data(self, simple_score):
        """Should include rhythm-related data."""
        result = extract_note_data(simple_score)
        assert "durations" in result
        assert "types" in result
        assert "has_dots" in result
        assert "has_tuplets" in result
        assert "has_ties" in result
        assert "offsets" in result


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestPitchExtraction:
    """Tests for pitch data extraction."""

    def test_pitch_class_count(self, simple_score):
        """Should count unique pitch classes."""
        result = extract_note_data(simple_score)
        # C, D, E, F = 4 unique pitch classes
        assert result["pitch_class_count"] == 4

    def test_note_steps(self, simple_score):
        """Should extract note step letters."""
        result = extract_note_data(simple_score)
        assert result["note_steps"] == ["C", "D", "E", "F"]

    def test_total_notes(self, simple_score):
        """Should count total notes."""
        result = extract_note_data(simple_score)
        assert result["total_notes"] == 4


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestAccidentalCounting:
    """Tests for accidental counting."""

    def test_no_accidentals_in_diatonic(self, simple_score):
        """C-D-E-F in C major should have no accidentals."""
        result = extract_note_data(simple_score)
        assert result["accidental_count"] == 0

    def test_counts_accidentals(self, score_with_accidentals):
        """F# in C major should be counted as accidental."""
        result = extract_note_data(score_with_accidentals)
        assert result["accidental_count"] == 1


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestIntervalExtraction:
    """Tests for interval data extraction."""

    def test_interval_count(self, simple_score):
        """Should have n-1 intervals for n notes."""
        result = extract_note_data(simple_score)
        # 4 notes = 3 intervals
        assert len(result["interval_semitones"]) == 3

    def test_interval_values(self, simple_score):
        """C-D-E-F should have all step intervals (2 semitones)."""
        result = extract_note_data(simple_score)
        # C to D = 2, D to E = 2, E to F = 1
        assert result["interval_semitones"] == [2, 2, 1]

    def test_pitch_changes(self, simple_score):
        """Should track signed pitch changes."""
        result = extract_note_data(simple_score)
        # All ascending
        assert all(pc > 0 for pc in result["pitch_changes"])


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestNoteEventCreation:
    """Tests for NoteEvent creation."""

    def test_note_events_created(self, simple_score):
        """Should create NoteEvent for each note."""
        result = extract_note_data(simple_score)
        assert len(result["note_events"]) == 4

    def test_note_event_has_pitch(self, simple_score):
        """NoteEvents should have pitch_midi."""
        result = extract_note_data(simple_score)
        # C4 = MIDI 60
        assert result["note_events"][0].pitch_midi == 60

    def test_note_event_has_duration(self, simple_score):
        """NoteEvents should have duration_ql."""
        result = extract_note_data(simple_score)
        assert result["note_events"][0].duration_ql == 1.0


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestChordHandling:
    """Tests for chord handling."""

    def test_chord_notes_counted(self, score_with_chord):
        """Should count all notes in chords."""
        result = extract_note_data(score_with_chord)
        # 1 single note + 3 chord notes = 4
        assert result["total_notes"] == 4

    def test_chord_pitch_classes(self, score_with_chord):
        """Should extract pitch classes from chord."""
        result = extract_note_data(score_with_chord)
        # C, E, G, C5 (same pitch class as C4)
        # So: C, E, G = 3 unique pitch classes
        assert result["pitch_class_count"] == 3

    def test_chord_uses_top_note_for_interval(self, score_with_chord):
        """Should use highest chord note for interval calculation."""
        result = extract_note_data(score_with_chord)
        # C4 to C5 (top of chord) = 12 semitones
        assert result["interval_semitones"][0] == 12

    def test_chord_note_steps(self, score_with_chord):
        """Should include all note steps from chord."""
        result = extract_note_data(score_with_chord)
        # C, then E, G, C from chord
        assert "C" in result["note_steps"]
        assert "E" in result["note_steps"]
        assert "G" in result["note_steps"]


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestRhythmDataExtraction:
    """Tests for rhythm data extraction."""

    def test_durations_extracted(self, simple_score):
        """Should extract note durations."""
        result = extract_note_data(simple_score)
        assert len(result["durations"]) == 4
        assert all(d == 1.0 for d in result["durations"])

    def test_types_extracted(self, simple_score):
        """Should extract note types."""
        result = extract_note_data(simple_score)
        assert len(result["types"]) == 4
        assert all(t == "quarter" for t in result["types"])

    def test_has_dots_flags(self, simple_score):
        """Should track dotted notes."""
        result = extract_note_data(simple_score)
        assert len(result["has_dots"]) == 4
        assert all(not d for d in result["has_dots"])

    def test_has_tuplets_flags(self, simple_score):
        """Should track tuplets."""
        result = extract_note_data(simple_score)
        assert len(result["has_tuplets"]) == 4
        assert all(not t for t in result["has_tuplets"])

    def test_offsets_extracted(self, simple_score):
        """Should extract note offsets."""
        result = extract_note_data(simple_score)
        assert len(result["offsets"]) == 4


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestMeasureNumberTracking:
    """Tests for measure number tracking."""

    def test_note_measure_numbers(self, simple_score):
        """Should track measure numbers for notes."""
        result = extract_note_data(simple_score)
        assert "note_measure_numbers" in result
        # All notes in measure 1
        assert all(m == 1 for m in result["note_measure_numbers"])

    def test_interval_measure_numbers(self, simple_score):
        """Should track measure numbers for intervals."""
        result = extract_note_data(simple_score)
        assert "interval_measure_numbers" in result


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestEmptyScore:
    """Tests for handling empty scores."""

    def test_empty_score_returns_zeros(self):
        """Empty score should return zero counts."""
        s = stream.Score()
        p = stream.Part()
        m = stream.Measure(number=1)
        p.append(m)
        s.append(p)
        
        result = extract_note_data(s)
        
        assert result["total_notes"] == 0
        assert result["pitch_class_count"] == 0
        assert result["accidental_count"] == 0
        assert len(result["interval_semitones"]) == 0
