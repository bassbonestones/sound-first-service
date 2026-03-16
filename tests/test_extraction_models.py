"""
Tests for analyzers/extraction_models.py

Tests for dataclasses and helper functions used in MusicXML analysis.
"""

import pytest
from dataclasses import asdict

from app.analyzers.extraction_models import (
    format_pitch_name,
    IntervalInfo,
    RhythmPatternAnalysis,
    MelodicPatternAnalysis,
    RangeAnalysis,
    ExtractionResult,
)


class TestFormatPitchName:
    """Tests for format_pitch_name helper function."""

    def test_flat_conversion(self):
        """Should convert music21 flat notation to standard."""
        assert format_pitch_name("E-5") == "Eb5"
        assert format_pitch_name("B-4") == "Bb4"
        assert format_pitch_name("A-3") == "Ab3"

    def test_natural_unchanged(self):
        """Natural pitches should be unchanged."""
        assert format_pitch_name("C4") == "C4"
        assert format_pitch_name("G5") == "G5"
        assert format_pitch_name("A3") == "A3"

    def test_sharp_unchanged(self):
        """Sharp notation should be unchanged."""
        assert format_pitch_name("F#4") == "F#4"
        assert format_pitch_name("C#5") == "C#5"

    def test_double_flat(self):
        """Double flats should convert both dashes."""
        assert format_pitch_name("B--4") == "Bbb4"

    def test_empty_string(self):
        """Empty string should remain empty."""
        assert format_pitch_name("") == ""


class TestIntervalInfo:
    """Tests for IntervalInfo dataclass."""

    def test_create_basic(self):
        """Should create basic interval info."""
        info = IntervalInfo(
            name="M3",
            direction="ascending",
            quality="major",
            semitones=4,
            is_melodic=True,
        )
        assert info.name == "M3"
        assert info.direction == "ascending"
        assert info.quality == "major"
        assert info.semitones == 4
        assert info.is_melodic is True
        assert info.count == 1  # default

    def test_count_default(self):
        """Count should default to 1."""
        info = IntervalInfo(
            name="P5",
            direction="descending",
            quality="perfect",
            semitones=7,
            is_melodic=False,
        )
        assert info.count == 1

    def test_count_override(self):
        """Count can be overridden."""
        info = IntervalInfo(
            name="m2",
            direction="ascending",
            quality="minor",
            semitones=1,
            is_melodic=True,
            count=5,
        )
        assert info.count == 5


class TestRhythmPatternAnalysis:
    """Tests for RhythmPatternAnalysis dataclass."""

    def test_create_empty(self):
        """Should create empty analysis."""
        analysis = RhythmPatternAnalysis(
            total_measures=0,
            unique_rhythm_patterns=0,
            rhythm_measure_uniqueness_ratio=0.0,
            rhythm_measure_repetition_ratio=1.0,
        )
        assert analysis.total_measures == 0
        assert analysis.pattern_counts == {}

    def test_pattern_counts_default(self):
        """pattern_counts should default to empty dict."""
        analysis = RhythmPatternAnalysis(
            total_measures=10,
            unique_rhythm_patterns=5,
            rhythm_measure_uniqueness_ratio=0.5,
            rhythm_measure_repetition_ratio=0.5,
        )
        assert analysis.pattern_counts == {}
        assert analysis.most_common_pattern is None
        assert analysis.most_common_count == 0

    def test_with_patterns(self):
        """Should store pattern counts."""
        analysis = RhythmPatternAnalysis(
            total_measures=10,
            unique_rhythm_patterns=3,
            rhythm_measure_uniqueness_ratio=0.3,
            rhythm_measure_repetition_ratio=0.7,
            pattern_counts={"n1.0|n1.0": 5, "n0.5|n0.5|n1.0": 3, "n2.0": 2},
            most_common_pattern="n1.0|n1.0",
            most_common_count=5,
        )
        assert len(analysis.pattern_counts) == 3
        assert analysis.most_common_pattern == "n1.0|n1.0"


class TestMelodicPatternAnalysis:
    """Tests for MelodicPatternAnalysis dataclass."""

    def test_create_basic(self):
        """Should create basic analysis."""
        analysis = MelodicPatternAnalysis(
            total_motifs=100,
            unique_motifs=25,
            motif_uniqueness_ratio=0.25,
            motif_repetition_ratio=0.75,
        )
        assert analysis.total_motifs == 100
        assert analysis.unique_motifs == 25
        assert analysis.sequence_count == 0  # default

    def test_defaults(self):
        """Optional fields should have sensible defaults."""
        analysis = MelodicPatternAnalysis(
            total_motifs=50,
            unique_motifs=10,
            motif_uniqueness_ratio=0.2,
            motif_repetition_ratio=0.8,
        )
        assert analysis.sequence_count == 0
        assert analysis.sequence_total_notes == 0
        assert analysis.sequence_coverage_ratio == 0.0
        assert analysis.most_common_motif is None
        assert analysis.most_common_count == 0


class TestRangeAnalysis:
    """Tests for RangeAnalysis dataclass."""

    def test_create_basic(self):
        """Should create basic range analysis."""
        analysis = RangeAnalysis(
            lowest_pitch="C3",
            highest_pitch="C5",
            lowest_midi=48,
            highest_midi=72,
            range_semitones=24,
            density_low=30.0,
            density_mid=50.0,
            density_high=20.0,
        )
        assert analysis.lowest_pitch == "C3"
        assert analysis.highest_pitch == "C5"
        assert analysis.range_semitones == 24
        assert analysis.density_low + analysis.density_mid + analysis.density_high == 100.0

    def test_trill_defaults(self):
        """Trill pitches should default to None."""
        analysis = RangeAnalysis(
            lowest_pitch="C3",
            highest_pitch="C5",
            lowest_midi=48,
            highest_midi=72,
            range_semitones=24,
            density_low=33.3,
            density_mid=33.3,
            density_high=33.4,
        )
        assert analysis.trill_lowest is None
        assert analysis.trill_highest is None

    def test_with_trills(self):
        """Should store trill pitch information."""
        analysis = RangeAnalysis(
            lowest_pitch="C3",
            highest_pitch="C5",
            lowest_midi=48,
            highest_midi=72,
            range_semitones=24,
            density_low=30.0,
            density_mid=50.0,
            density_high=20.0,
            trill_lowest="E4",
            trill_highest="G4",
        )
        assert analysis.trill_lowest == "E4"
        assert analysis.trill_highest == "G4"


class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""

    def test_create_empty(self):
        """Should create with all defaults."""
        result = ExtractionResult()
        assert result.title is None
        assert result.composer is None
        assert result.clefs == set()
        assert result.time_signatures == set()
        assert result.note_values == {}
        assert result.has_ties is False
        assert result.max_voices == 1

    def test_set_fields(self):
        """Should allow setting fields."""
        result = ExtractionResult()
        result.title = "Test Piece"
        result.clefs.add("treble")
        result.time_signatures.add("4/4")
        result.note_values["quarter"] = 10
        
        assert result.title == "Test Piece"
        assert "treble" in result.clefs
        assert "4/4" in result.time_signatures
        assert result.note_values["quarter"] == 10

    def test_dynamics_and_articulations(self):
        """Should store dynamics and articulations."""
        result = ExtractionResult()
        result.dynamics.add("mf")
        result.dynamics.add("f")
        result.articulations.add("staccato")
        
        assert len(result.dynamics) == 2
        assert "staccato" in result.articulations

    def test_melodic_intervals(self):
        """Should store interval info dictionaries."""
        result = ExtractionResult()
        result.melodic_intervals["M3_ascending"] = IntervalInfo(
            name="M3",
            direction="ascending",
            quality="major",
            semitones=4,
            is_melodic=True,
            count=3,
        )
        
        assert "M3_ascending" in result.melodic_intervals
        assert result.melodic_intervals["M3_ascending"].count == 3

    def test_default_factory_isolation(self):
        """Each instance should have isolated mutable defaults."""
        result1 = ExtractionResult()
        result2 = ExtractionResult()
        
        result1.clefs.add("treble")
        result2.clefs.add("bass")
        
        assert "treble" in result1.clefs
        assert "bass" in result2.clefs
        assert "bass" not in result1.clefs  # Should be isolated
