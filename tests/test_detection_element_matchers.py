"""
Tests for capabilities/detection/element_matchers.py

Tests for element mapping and matching functions.
"""

import pytest
from dataclasses import dataclass, field
from typing import Set

from app.capabilities.detection.element_matchers import (
    check_element,
    CLEF_MAP,
    ARTICULATION_MAP,
    ORNAMENT_MAP,
)


@dataclass
class MockExtractionResult:
    """Mock extraction result for testing."""
    clefs: Set[str] = field(default_factory=set)
    articulations: Set[str] = field(default_factory=set)
    ornaments: Set[str] = field(default_factory=set)
    fermatas: int = 0
    breath_marks: int = 0


class TestClefMap:
    """Tests for CLEF_MAP constant."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(CLEF_MAP, dict)

    def test_contains_treble_clef(self):
        """Should map treble clef."""
        assert "music21.clef.TrebleClef" in CLEF_MAP
        assert CLEF_MAP["music21.clef.TrebleClef"] == "clef_treble"

    def test_contains_bass_clef(self):
        """Should map bass clef."""
        assert "music21.clef.BassClef" in CLEF_MAP
        assert CLEF_MAP["music21.clef.BassClef"] == "clef_bass"

    def test_contains_alto_clef(self):
        """Should map alto clef."""
        assert "music21.clef.AltoClef" in CLEF_MAP
        assert CLEF_MAP["music21.clef.AltoClef"] == "clef_alto"

    def test_contains_tenor_clef(self):
        """Should map tenor clef."""
        assert "music21.clef.TenorClef" in CLEF_MAP
        assert CLEF_MAP["music21.clef.TenorClef"] == "clef_tenor"


class TestArticulationMap:
    """Tests for ARTICULATION_MAP constant."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(ARTICULATION_MAP, dict)

    def test_contains_staccato(self):
        """Should map staccato."""
        assert "music21.articulations.Staccato" in ARTICULATION_MAP
        assert ARTICULATION_MAP["music21.articulations.Staccato"] == "articulation_staccato"

    def test_contains_accent(self):
        """Should map accent."""
        assert "music21.articulations.Accent" in ARTICULATION_MAP
        assert ARTICULATION_MAP["music21.articulations.Accent"] == "articulation_accent"

    def test_contains_tenuto(self):
        """Should map tenuto."""
        assert "music21.articulations.Tenuto" in ARTICULATION_MAP
        assert ARTICULATION_MAP["music21.articulations.Tenuto"] == "articulation_tenuto"

    def test_maps_strong_accent_to_marcato(self):
        """StrongAccent should map to marcato."""
        assert "music21.articulations.StrongAccent" in ARTICULATION_MAP
        assert ARTICULATION_MAP["music21.articulations.StrongAccent"] == "articulation_marcato"


class TestOrnamentMap:
    """Tests for ORNAMENT_MAP constant."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(ORNAMENT_MAP, dict)

    def test_contains_trill(self):
        """Should map trill."""
        assert "music21.expressions.Trill" in ORNAMENT_MAP
        assert ORNAMENT_MAP["music21.expressions.Trill"] == "ornament_trill"

    def test_contains_mordent(self):
        """Should map mordent."""
        assert "music21.expressions.Mordent" in ORNAMENT_MAP
        assert ORNAMENT_MAP["music21.expressions.Mordent"] == "ornament_mordent"

    def test_contains_turn(self):
        """Should map turn."""
        assert "music21.expressions.Turn" in ORNAMENT_MAP
        assert ORNAMENT_MAP["music21.expressions.Turn"] == "ornament_turn"

    def test_contains_tremolo(self):
        """Should map tremolo."""
        assert "music21.expressions.Tremolo" in ORNAMENT_MAP
        assert ORNAMENT_MAP["music21.expressions.Tremolo"] == "ornament_tremolo"


class TestCheckElement:
    """Tests for check_element function."""

    def test_matches_treble_clef(self):
        """Should detect treble clef."""
        result = MockExtractionResult()
        result.clefs = {"clef_treble", "clef_bass"}
        
        config = {"class": "music21.clef.TrebleClef"}
        
        assert check_element(config, result) is True

    def test_no_match_missing_clef(self):
        """Should not match missing clef."""
        result = MockExtractionResult()
        result.clefs = {"clef_bass"}
        
        config = {"class": "music21.clef.TrebleClef"}
        
        assert check_element(config, result) is False

    def test_matches_articulation(self):
        """Should detect articulation."""
        result = MockExtractionResult()
        result.articulations = {"articulation_staccato"}
        
        config = {"class": "music21.articulations.Staccato"}
        
        assert check_element(config, result) is True

    def test_no_match_missing_articulation(self):
        """Should not match missing articulation."""
        result = MockExtractionResult()
        result.articulations = {"articulation_accent"}
        
        config = {"class": "music21.articulations.Staccato"}
        
        assert check_element(config, result) is False

    def test_matches_ornament(self):
        """Should detect ornament."""
        result = MockExtractionResult()
        result.ornaments = {"ornament_trill"}
        
        config = {"class": "music21.expressions.Trill"}
        
        assert check_element(config, result) is True

    def test_matches_fermata(self):
        """Should detect fermata by count."""
        result = MockExtractionResult()
        result.fermatas = 3
        
        config = {"class": "music21.expressions.Fermata"}
        
        assert check_element(config, result) is True

    def test_no_match_zero_fermata(self):
        """Should not match when no fermatas."""
        result = MockExtractionResult()
        result.fermatas = 0
        
        config = {"class": "music21.expressions.Fermata"}
        
        assert check_element(config, result) is False

    def test_breath_mark_detection(self):
        """Should detect breath marks."""
        result = MockExtractionResult()
        result.breath_marks = 2
        
        config = {"class": "music21.articulations.BreathMark"}
        
        assert check_element(config, result) is True

    def test_unknown_class_returns_false(self):
        """Unknown class should return False."""
        result = MockExtractionResult()
        
        config = {"class": "some.unknown.Class"}
        
        assert check_element(config, result) is False

    def test_empty_config_returns_false(self):
        """Empty config should return False."""
        result = MockExtractionResult()
        
        config = {}
        
        # Should handle missing "class" key
        assert check_element(config, result) is False
