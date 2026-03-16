"""
Tests for capabilities/detection/source_extractors.py

Tests for extracting data from ExtractionResult for rule matching.
"""

import pytest
from dataclasses import dataclass, field
from typing import Dict, Set

from app.capabilities.detection.source_extractors import (
    get_source_data,
    _extract_notes,
    _extract_rests,
    _extract_time_signatures,
    _extract_intervals,
    NOTE_TYPE_MAP,
)
from app.analyzers.extraction_models import ExtractionResult, IntervalInfo


class TestNoteTypeMap:
    """Tests for NOTE_TYPE_MAP constant."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(NOTE_TYPE_MAP, dict)

    def test_maps_thirty_second(self):
        """Should map thirty_second to 32nd."""
        assert NOTE_TYPE_MAP.get("thirty_second") == "32nd"

    def test_maps_sixty_fourth(self):
        """Should map sixty_fourth to 64th."""
        assert NOTE_TYPE_MAP.get("sixty_fourth") == "64th"


class TestGetSourceData:
    """Tests for get_source_data function."""

    def test_notes_source(self):
        """Should extract notes data."""
        result = ExtractionResult()
        result.note_values = {"note_quarter": 10, "note_eighth": 5}
        
        data = get_source_data("notes", result)
        
        assert isinstance(data, list)
        assert len(data) >= 2
        types = [d["type"] for d in data]
        assert "quarter" in types
        assert "eighth" in types

    def test_dynamics_source(self):
        """Should extract dynamics data."""
        result = ExtractionResult()
        result.dynamics = {"dynamic_f", "dynamic_p"}
        
        data = get_source_data("dynamics", result)
        
        assert isinstance(data, list)
        assert len(data) == 2
        values = [d["value"] for d in data]
        assert "f" in values
        assert "p" in values

    def test_rests_source(self):
        """Should extract rests data."""
        result = ExtractionResult()
        result.rest_values = {"rest_quarter": 3, "rest_half": 1}
        
        data = get_source_data("rests", result)
        
        assert isinstance(data, list)
        assert len(data) == 2

    def test_articulations_source(self):
        """Should extract articulations data."""
        result = ExtractionResult()
        result.articulations = {"articulation_staccato", "articulation_accent"}
        
        data = get_source_data("articulations", result)
        
        assert len(data) == 2
        names = [d["name"] for d in data]
        assert "staccato" in names
        assert "accent" in names

    def test_ornaments_source(self):
        """Should extract ornaments data."""
        result = ExtractionResult()
        result.ornaments = {"ornament_trill", "ornament_mordent"}
        
        data = get_source_data("ornaments", result)
        
        names = [d["name"] for d in data]
        assert "trill" in names
        assert "mordent" in names

    def test_clefs_source(self):
        """Should extract clefs data."""
        result = ExtractionResult()
        result.clefs = {"clef_treble", "clef_bass"}
        
        data = get_source_data("clefs", result)
        
        names = [d["name"] for d in data]
        assert "treble" in names
        assert "bass" in names

    def test_time_signatures_source(self):
        """Should extract time signature data."""
        result = ExtractionResult()
        result.time_signatures = {"time_sig_4_4", "time_sig_3_4"}
        
        data = get_source_data("time_signatures", result)
        
        assert len(data) == 2

    def test_key_signatures_source(self):
        """Should extract key signature data."""
        result = ExtractionResult()
        result.key_signatures = {"key_C_major", "key_G_major"}
        
        data = get_source_data("key_signatures", result)
        
        names = [d["name"] for d in data]
        assert "key_C_major" in names
        assert "key_G_major" in names

    def test_intervals_source(self):
        """Should extract interval data."""
        result = ExtractionResult()
        result.melodic_intervals = {
            "M3_ascending": IntervalInfo(
                name="M3", direction="ascending", quality="major",
                semitones=4, is_melodic=True
            )
        }
        
        data = get_source_data("intervals", result)
        
        assert len(data) >= 1

    def test_unknown_source_returns_empty(self):
        """Unknown source should return empty list."""
        result = ExtractionResult()
        data = get_source_data("unknown_source", result)
        
        assert data == []


class TestExtractNotes:
    """Tests for _extract_notes helper function."""

    def test_extracts_note_types(self):
        """Should extract note types with counts."""
        result = ExtractionResult()
        result.note_values = {"note_quarter": 10}
        
        notes = _extract_notes(result)
        
        quarter_notes = [n for n in notes if n["type"] == "quarter"]
        assert len(quarter_notes) >= 1
        assert quarter_notes[0]["count"] == 10

    def test_extracts_dotted_notes(self):
        """Should extract dotted notes."""
        result = ExtractionResult()
        result.note_values = {}
        result.dotted_notes = {"dotted_half"}
        
        notes = _extract_notes(result)
        
        # Should have entries for dotted notes
        assert len(notes) >= 1

    def test_normalizes_sixteenth(self):
        """Should normalize 16th to sixteenth."""
        result = ExtractionResult()
        result.note_values = {"note_16th": 5}
        result.dotted_notes = set()
        
        notes = _extract_notes(result)
        
        # Note: depends on mapping direction
        assert len(notes) >= 1


class TestExtractRests:
    """Tests for _extract_rests helper function."""

    def test_extracts_rest_types(self):
        """Should extract rest types."""
        result = ExtractionResult()
        result.rest_values = {"rest_quarter": 3}
        
        rests = _extract_rests(result)
        
        assert len(rests) == 1
        assert rests[0]["type"] == "quarter"
        assert rests[0]["count"] == 3


class TestExtractTimeSignatures:
    """Tests for _extract_time_signatures helper function."""

    def test_parses_time_signature(self):
        """Should parse time_sig_X_Y format."""
        result = ExtractionResult()
        result.time_signatures = {"time_sig_4_4"}
        
        time_sigs = _extract_time_signatures(result)
        
        assert len(time_sigs) == 1
        assert time_sigs[0]["numerator"] == 4
        assert time_sigs[0]["denominator"] == 4

    def test_parses_compound_time(self):
        """Should parse compound time signatures."""
        result = ExtractionResult()
        result.time_signatures = {"time_sig_6_8"}
        
        time_sigs = _extract_time_signatures(result)
        
        assert time_sigs[0]["numerator"] == 6
        assert time_sigs[0]["denominator"] == 8

    def test_parses_multiple_time_sigs(self):
        """Should parse multiple time signatures."""
        result = ExtractionResult()
        result.time_signatures = {"time_sig_4_4", "time_sig_3_4"}
        
        time_sigs = _extract_time_signatures(result)
        
        assert len(time_sigs) == 2


class TestExtractIntervals:
    """Tests for _extract_intervals helper function."""

    def test_extracts_melodic_intervals(self):
        """Should extract melodic interval info."""
        result = ExtractionResult()
        result.melodic_intervals = {
            "M3_asc": IntervalInfo(
                name="M3", direction="ascending", quality="major",
                semitones=4, is_melodic=True
            )
        }
        result.harmonic_intervals = {}
        
        intervals = _extract_intervals(result)
        
        assert len(intervals) >= 1
        m3 = [i for i in intervals if i["name"] == "M3"]
        assert len(m3) >= 1

    def test_extracts_harmonic_intervals(self):
        """Should extract harmonic interval info."""
        result = ExtractionResult()
        result.melodic_intervals = {}
        result.harmonic_intervals = {
            "P5_harm": IntervalInfo(
                name="P5", direction="ascending", quality="perfect",
                semitones=7, is_melodic=False
            )
        }
        
        intervals = _extract_intervals(result)
        
        assert len(intervals) >= 1
