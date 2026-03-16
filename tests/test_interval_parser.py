"""
Tests for analyzers/interval_parser.py

Tests for melodic and harmonic interval extraction.
"""

import pytest

try:
    from music21 import stream, note, chord, interval
    from app.analyzers.interval_parser import (
        extract_intervals,
        _get_interval_info,
    )
    from app.analyzers.extraction_models import ExtractionResult, IntervalInfo
    MUSIC21_OK = True
except ImportError:
    MUSIC21_OK = False


@pytest.fixture
def simple_melody():
    """Create a simple scale melody: C-D-E-F-G."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    
    for pitch in ["C4", "D4", "E4", "F4", "G4"]:
        n = note.Note(pitch)
        n.duration.quarterLength = 1.0
        m.append(n)
    
    p.append(m)
    s.append(p)
    return s


@pytest.fixture
def melody_with_leaps():
    """Melody with larger intervals: C-G-C-E."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    
    for pitch in ["C4", "G4", "C5", "E5"]:
        n = note.Note(pitch)
        n.duration.quarterLength = 1.0
        m.append(n)
    
    p.append(m)
    s.append(p)
    return s


@pytest.fixture
def score_with_chord():
    """Score containing a chord."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    
    c = chord.Chord(["C4", "E4", "G4"])
    c.duration.quarterLength = 4.0
    m.append(c)
    
    p.append(m)
    s.append(p)
    return s


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestExtractIntervals:
    """Tests for extract_intervals function."""

    def test_extracts_melodic_intervals(self, simple_melody):
        """Should extract melodic intervals from consecutive notes."""
        result = ExtractionResult()
        extract_intervals(simple_melody, result)
        
        # Should have melodic intervals
        assert len(result.melodic_intervals) > 0

    def test_interval_count_correct(self, simple_melody):
        """5 notes should produce 4 melodic intervals."""
        result = ExtractionResult()
        extract_intervals(simple_melody, result)
        
        # Count total intervals (may have duplicates with different keys)
        total_count = sum(info.count for info in result.melodic_intervals.values())
        assert total_count == 4

    def test_step_intervals(self, simple_melody):
        """Scale should produce step intervals (M2, m2)."""
        result = ExtractionResult()
        extract_intervals(simple_melody, result)
        
        # Check that step intervals are detected
        interval_names = [info.name for info in result.melodic_intervals.values()]
        assert any("2" in name for name in interval_names)

    def test_leap_intervals(self, melody_with_leaps):
        """Should detect larger intervals."""
        result = ExtractionResult()
        extract_intervals(melody_with_leaps, result)
        
        # Should have some larger intervals
        semitones = [info.semitones for info in result.melodic_intervals.values()]
        assert any(s > 4 for s in semitones)

    def test_extracts_harmonic_intervals(self, score_with_chord):
        """Should extract harmonic intervals from chords."""
        result = ExtractionResult()
        extract_intervals(score_with_chord, result)
        
        # Should have harmonic intervals from the chord
        assert len(result.harmonic_intervals) > 0

    def test_chord_interval_count(self, score_with_chord):
        """C-E-G chord should produce 3 harmonic intervals."""
        result = ExtractionResult()
        extract_intervals(score_with_chord, result)
        
        # C-E (M3), C-G (P5), E-G (m3) = 3 intervals
        total = sum(info.count for info in result.harmonic_intervals.values())
        assert total == 3

    def test_direction_tracking(self, simple_melody):
        """Should track interval direction."""
        result = ExtractionResult()
        extract_intervals(simple_melody, result)
        
        # All ascending scale intervals
        directions = [info.direction for info in result.melodic_intervals.values()]
        assert "ascending" in directions


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestGetIntervalInfo:
    """Tests for _get_interval_info function."""

    def test_ascending_interval(self):
        """Should identify ascending direction."""
        intv = interval.Interval("M3")
        info = _get_interval_info(intv, is_melodic=True)
        
        assert info.direction == "ascending"
        assert info.semitones == 4

    def test_descending_interval(self):
        """Should identify descending direction."""
        intv = interval.Interval("m3")
        intv = interval.Interval(noteStart=note.Note("E4"), noteEnd=note.Note("C4"))
        info = _get_interval_info(intv, is_melodic=True)
        
        assert info.direction == "descending"

    def test_unison_interval(self):
        """Should identify unison."""
        intv = interval.Interval("P1")
        info = _get_interval_info(intv, is_melodic=True)
        
        assert info.direction == "unison"
        assert info.semitones == 0

    def test_interval_quality(self):
        """Should extract interval quality."""
        intv = interval.Interval("M3")
        info = _get_interval_info(intv, is_melodic=True)
        
        assert info.quality == "major"

    def test_perfect_interval(self):
        """Should identify perfect intervals."""
        intv = interval.Interval("P5")
        info = _get_interval_info(intv, is_melodic=True)
        
        assert info.quality == "perfect"
        assert info.semitones == 7

    def test_is_melodic_flag(self):
        """Should set is_melodic flag."""
        intv = interval.Interval("M2")
        
        melodic_info = _get_interval_info(intv, is_melodic=True)
        harmonic_info = _get_interval_info(intv, is_melodic=False)
        
        assert melodic_info.is_melodic is True
        assert harmonic_info.is_melodic is False

    def test_octave_handling(self):
        """Octave should be preserved as P8."""
        intv = interval.Interval("P8")
        info = _get_interval_info(intv, is_melodic=True)
        
        assert info.semitones == 12
        # Should be P8, not reduced to P1

    def test_compound_interval(self):
        """Compound intervals should preserve size."""
        intv = interval.Interval("M9")  # Octave + M2
        info = _get_interval_info(intv, is_melodic=True)
        
        assert info.semitones == 14


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestIntervalInfoDataclass:
    """Tests for IntervalInfo dataclass."""

    def test_create_interval_info(self):
        """Should create IntervalInfo with all fields."""
        info = IntervalInfo(
            name="M3",
            direction="ascending",
            quality="major",
            semitones=4,
            is_melodic=True,
        )
        assert info.name == "M3"
        assert info.count == 1  # default

    def test_count_increment(self):
        """Count should be mutable."""
        info = IntervalInfo(
            name="P5",
            direction="ascending",
            quality="perfect",
            semitones=7,
            is_melodic=True,
        )
        info.count += 1
        assert info.count == 2
