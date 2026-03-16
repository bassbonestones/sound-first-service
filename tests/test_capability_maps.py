"""
Tests for analyzers/capability_maps.py

Tests for capability name mappings used in MusicXML analysis.
"""

import pytest

from app.analyzers.capability_maps import (
    CLEF_CAPABILITY_MAP,
    NOTE_VALUE_CAPABILITY_MAP,
    REST_CAPABILITY_MAP,
    DYNAMIC_CAPABILITY_MAP,
    ARTICULATION_CAPABILITY_MAP,
    ORNAMENT_CAPABILITY_MAP,
    TEMPO_TERMS,
    EXPRESSION_TERMS,
)


class TestClefCapabilityMap:
    """Tests for CLEF_CAPABILITY_MAP."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(CLEF_CAPABILITY_MAP, dict)

    def test_contains_common_clefs(self):
        """Should contain common clef types."""
        assert "TrebleClef" in CLEF_CAPABILITY_MAP
        assert "BassClef" in CLEF_CAPABILITY_MAP
        assert "AltoClef" in CLEF_CAPABILITY_MAP
        assert "TenorClef" in CLEF_CAPABILITY_MAP

    def test_values_have_clef_prefix(self):
        """All values should have clef_ prefix."""
        for value in CLEF_CAPABILITY_MAP.values():
            assert value.startswith("clef_"), f"{value} should start with clef_"

    def test_no_empty_values(self):
        """No values should be empty."""
        for key, value in CLEF_CAPABILITY_MAP.items():
            assert value, f"Value for {key} should not be empty"


class TestNoteValueCapabilityMap:
    """Tests for NOTE_VALUE_CAPABILITY_MAP."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(NOTE_VALUE_CAPABILITY_MAP, dict)

    def test_contains_standard_values(self):
        """Should contain standard note values."""
        assert "whole" in NOTE_VALUE_CAPABILITY_MAP
        assert "half" in NOTE_VALUE_CAPABILITY_MAP
        assert "quarter" in NOTE_VALUE_CAPABILITY_MAP
        assert "eighth" in NOTE_VALUE_CAPABILITY_MAP
        assert "16th" in NOTE_VALUE_CAPABILITY_MAP

    def test_values_have_note_prefix(self):
        """All values should have note_ prefix."""
        for value in NOTE_VALUE_CAPABILITY_MAP.values():
            assert value.startswith("note_"), f"{value} should start with note_"

    def test_sixteenth_mapping(self):
        """16th should map to note_sixteenth."""
        assert NOTE_VALUE_CAPABILITY_MAP["16th"] == "note_sixteenth"

    def test_thirty_second_mapping(self):
        """32nd should map to note_thirty_second."""
        assert NOTE_VALUE_CAPABILITY_MAP["32nd"] == "note_thirty_second"


class TestRestCapabilityMap:
    """Tests for REST_CAPABILITY_MAP."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(REST_CAPABILITY_MAP, dict)

    def test_contains_standard_values(self):
        """Should contain standard rest values."""
        assert "whole" in REST_CAPABILITY_MAP
        assert "half" in REST_CAPABILITY_MAP
        assert "quarter" in REST_CAPABILITY_MAP
        assert "eighth" in REST_CAPABILITY_MAP

    def test_values_have_rest_prefix(self):
        """All values should have rest_ prefix."""
        for value in REST_CAPABILITY_MAP.values():
            assert value.startswith("rest_"), f"{value} should start with rest_"

    def test_parallel_to_note_values(self):
        """Rest map should have same keys as note map."""
        assert set(REST_CAPABILITY_MAP.keys()) == set(NOTE_VALUE_CAPABILITY_MAP.keys())


class TestDynamicCapabilityMap:
    """Tests for DYNAMIC_CAPABILITY_MAP."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(DYNAMIC_CAPABILITY_MAP, dict)

    def test_contains_common_dynamics(self):
        """Should contain common dynamic markings."""
        common = ["pp", "p", "mp", "mf", "f", "ff"]
        for d in common:
            assert d in DYNAMIC_CAPABILITY_MAP, f"Missing dynamic: {d}"

    def test_values_have_dynamic_prefix(self):
        """All values should have dynamic_ prefix."""
        for value in DYNAMIC_CAPABILITY_MAP.values():
            assert value.startswith("dynamic_"), f"{value} should start with dynamic_"

    def test_contains_accent_dynamics(self):
        """Should contain accent/sforzando dynamics."""
        assert "sf" in DYNAMIC_CAPABILITY_MAP
        assert "sfz" in DYNAMIC_CAPABILITY_MAP
        assert "fp" in DYNAMIC_CAPABILITY_MAP


class TestArticulationCapabilityMap:
    """Tests for ARTICULATION_CAPABILITY_MAP."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(ARTICULATION_CAPABILITY_MAP, dict)

    def test_contains_common_articulations(self):
        """Should contain common articulations."""
        assert "Staccato" in ARTICULATION_CAPABILITY_MAP
        assert "Accent" in ARTICULATION_CAPABILITY_MAP
        assert "Tenuto" in ARTICULATION_CAPABILITY_MAP

    def test_values_have_appropriate_prefix(self):
        """Values should have articulation_ or notation_ prefix."""
        for key, value in ARTICULATION_CAPABILITY_MAP.items():
            assert value.startswith("articulation_") or value.startswith("notation_"), \
                f"{value} should start with articulation_ or notation_"

    def test_staccato_mapping(self):
        """Staccato should map correctly."""
        assert ARTICULATION_CAPABILITY_MAP["Staccato"] == "articulation_staccato"


class TestOrnamentCapabilityMap:
    """Tests for ORNAMENT_CAPABILITY_MAP."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(ORNAMENT_CAPABILITY_MAP, dict)

    def test_contains_common_ornaments(self):
        """Should contain common ornaments."""
        assert "Trill" in ORNAMENT_CAPABILITY_MAP
        assert "Mordent" in ORNAMENT_CAPABILITY_MAP
        assert "Turn" in ORNAMENT_CAPABILITY_MAP

    def test_values_have_ornament_prefix(self):
        """All values should have ornament_ prefix."""
        for value in ORNAMENT_CAPABILITY_MAP.values():
            assert value.startswith("ornament_"), f"{value} should start with ornament_"

    def test_inverted_variants(self):
        """Should include inverted variants."""
        assert "InvertedMordent" in ORNAMENT_CAPABILITY_MAP
        assert "InvertedTurn" in ORNAMENT_CAPABILITY_MAP


class TestTempoTerms:
    """Tests for TEMPO_TERMS set."""

    def test_is_set(self):
        """Should be a set."""
        assert isinstance(TEMPO_TERMS, set)

    def test_contains_common_tempos(self):
        """Should contain common tempo terms."""
        common = ["allegro", "andante", "adagio", "presto", "moderato"]
        for term in common:
            assert term in TEMPO_TERMS, f"Missing tempo: {term}"

    def test_all_lowercase(self):
        """All terms should be lowercase."""
        for term in TEMPO_TERMS:
            assert term == term.lower(), f"{term} should be lowercase"

    def test_contains_tempo_changes(self):
        """Should contain tempo change terms."""
        assert "accelerando" in TEMPO_TERMS
        assert "ritardando" in TEMPO_TERMS
        assert "a tempo" in TEMPO_TERMS


class TestExpressionTerms:
    """Tests for EXPRESSION_TERMS set."""

    def test_is_set(self):
        """Should be a set."""
        assert isinstance(EXPRESSION_TERMS, set)

    def test_contains_common_expressions(self):
        """Should contain common expression terms."""
        common = ["dolce", "cantabile", "espressivo", "legato"]
        for term in common:
            assert term in EXPRESSION_TERMS, f"Missing expression: {term}"

    def test_all_lowercase(self):
        """All terms should be lowercase."""
        for term in EXPRESSION_TERMS:
            assert term == term.lower(), f"{term} should be lowercase"

    def test_contains_modifier_terms(self):
        """Should contain modifier terms."""
        assert "molto" in EXPRESSION_TERMS
        assert "poco" in EXPRESSION_TERMS
        assert "sempre" in EXPRESSION_TERMS

    def test_no_overlap_with_tempo_terms(self):
        """Expression terms should not duplicate tempo terms."""
        overlap = EXPRESSION_TERMS.intersection(TEMPO_TERMS)
        # Some overlap is expected (e.g., 'legato' might be both)
        # but core tempo terms should not be in expressions
        core_tempo = {"allegro", "andante", "adagio", "presto"}
        assert not overlap.intersection(core_tempo), \
            f"Expression should not contain core tempo terms: {overlap}"
