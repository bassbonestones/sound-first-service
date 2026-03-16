"""
Tests for analyzers/note_parser.py

Tests for note and rest extraction from MusicXML scores.
"""

import pytest

try:
    from music21 import stream, note, chord, duration
    from app.analyzers.note_parser import (
        extract_notes_and_rests,
        get_tuplet_name,
        _extract_voice_count,
    )
    from app.analyzers.extraction_models import ExtractionResult
    MUSIC21_OK = True
except ImportError:
    MUSIC21_OK = False


@pytest.fixture
def simple_score():
    """Create a simple score with quarter notes."""
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
def score_with_rests():
    """Score with notes and rests."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    
    # Quarter note, quarter rest, half note
    n1 = note.Note("C4")
    n1.duration.quarterLength = 1.0
    m.append(n1)
    
    r = note.Rest()
    r.duration.quarterLength = 1.0
    m.append(r)
    
    n2 = note.Note("E4")
    n2.duration.quarterLength = 2.0
    m.append(n2)
    
    p.append(m)
    s.append(p)
    return s


@pytest.fixture
def score_with_dotted():
    """Score with dotted notes."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    
    # Dotted quarter
    n = note.Note("C4")
    n.duration.quarterLength = 1.5
    n.duration.dots = 1
    m.append(n)
    
    p.append(m)
    s.append(p)
    return s


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestExtractNotesAndRests:
    """Tests for extract_notes_and_rests function."""

    def test_extracts_note_values(self, simple_score):
        """Should extract note value counts."""
        result = ExtractionResult()
        extract_notes_and_rests(simple_score, result)
        
        assert "note_quarter" in result.note_values
        assert result.note_values["note_quarter"] == 4

    def test_extracts_rest_values(self, score_with_rests):
        """Should extract rest value counts."""
        result = ExtractionResult()
        extract_notes_and_rests(score_with_rests, result)
        
        assert "rest_quarter" in result.rest_values
        assert result.rest_values["rest_quarter"] == 1

    def test_extracts_dotted_notes(self, score_with_dotted):
        """Should track dotted notes."""
        result = ExtractionResult()
        extract_notes_and_rests(score_with_dotted, result)
        
        assert len(result.dotted_notes) > 0

    def test_ties_detection(self):
        """Should detect tied notes."""
        from music21 import tie
        
        s = stream.Score()
        p = stream.Part()
        m = stream.Measure(number=1)
        
        n1 = note.Note("C4")
        n1.tie = tie.Tie("start")
        m.append(n1)
        
        n2 = note.Note("C4")
        n2.tie = tie.Tie("stop")
        m.append(n2)
        
        p.append(m)
        s.append(p)
        
        result = ExtractionResult()
        extract_notes_and_rests(s, result)
        
        assert result.has_ties is True

    def test_chord_notes_counted(self):
        """Should count notes in chords."""
        s = stream.Score()
        p = stream.Part()
        m = stream.Measure(number=1)
        
        c = chord.Chord(["C4", "E4", "G4"])
        c.duration.quarterLength = 1.0
        m.append(c)
        
        p.append(m)
        s.append(p)
        
        result = ExtractionResult()
        extract_notes_and_rests(s, result)
        
        assert "note_quarter" in result.note_values


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestGetTupletName:
    """Tests for get_tuplet_name function."""

    def test_triplet(self):
        """Should identify triplet."""
        from music21 import duration
        t = duration.Tuplet(3, 2)
        name = get_tuplet_name(t)
        assert name == "tuplet_triplet"

    def test_quintuplet(self):
        """Should identify quintuplet."""
        from music21 import duration
        t = duration.Tuplet(5, 4)
        name = get_tuplet_name(t)
        assert name == "tuplet_quintuplet"

    def test_sextuplet(self):
        """Should identify sextuplet."""
        from music21 import duration
        t = duration.Tuplet(6, 4)
        name = get_tuplet_name(t)
        assert name == "tuplet_sextuplet"

    def test_septuplet(self):
        """Should identify septuplet."""
        from music21 import duration
        t = duration.Tuplet(7, 4)
        name = get_tuplet_name(t)
        assert name == "tuplet_septuplet"

    def test_generic_tuplet(self):
        """Should handle non-standard tuplets."""
        from music21 import duration
        t = duration.Tuplet(9, 8)
        name = get_tuplet_name(t)
        assert name == "tuplet_9_8"


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestExtractVoiceCount:
    """Tests for _extract_voice_count function."""

    def test_single_voice(self, simple_score):
        """Single voice score should have max_voices = 1."""
        result = ExtractionResult()
        _extract_voice_count(simple_score, result)
        
        assert result.max_voices == 1

    def test_multi_voice(self):
        """Should detect multiple voices."""
        s = stream.Score()
        p = stream.Part()
        m = stream.Measure(number=1)
        
        # Create two voices
        v1 = stream.Voice()
        v1.append(note.Note("C4"))
        v2 = stream.Voice()
        v2.append(note.Note("E4"))
        
        m.insert(0, v1)
        m.insert(0, v2)
        
        p.append(m)
        s.append(p)
        
        result = ExtractionResult()
        _extract_voice_count(s, result)
        
        assert result.max_voices >= 2
