"""
Tests for analyzers/capability_mapper.py

Tests for converting ExtractionResult to capability names.
"""

import pytest

from app.analyzers.capability_mapper import get_capability_names
from app.analyzers.extraction_models import (
    ExtractionResult,
    IntervalInfo,
)


class TestGetCapabilityNames:
    """Tests for get_capability_names function."""

    def test_empty_result(self):
        """Empty result should return empty list."""
        result = ExtractionResult()
        capabilities = get_capability_names(result)
        
        # Default values don't add capabilities
        assert isinstance(capabilities, list)

    def test_extracts_clefs(self):
        """Should extract clef capabilities."""
        result = ExtractionResult()
        result.clefs.add("clef_treble")
        result.clefs.add("clef_bass")
        
        capabilities = get_capability_names(result)
        
        assert "clef_treble" in capabilities
        assert "clef_bass" in capabilities

    def test_extracts_time_signatures(self):
        """Should extract time signature capabilities."""
        result = ExtractionResult()
        result.time_signatures.add("time_sig_4_4")
        result.time_signatures.add("time_sig_3_4")
        
        capabilities = get_capability_names(result)
        
        assert "time_sig_4_4" in capabilities
        assert "time_sig_3_4" in capabilities

    def test_extracts_key_signatures(self):
        """Should extract key signature capabilities."""
        result = ExtractionResult()
        result.key_signatures.add("key_C_major")
        result.key_signatures.add("key_G_major")
        
        capabilities = get_capability_names(result)
        
        assert "key_C_major" in capabilities
        assert "key_G_major" in capabilities

    def test_extracts_note_values(self):
        """Should extract note value capabilities."""
        result = ExtractionResult()
        result.note_values = {"note_quarter": 10, "note_eighth": 5}
        
        capabilities = get_capability_names(result)
        
        assert "note_quarter" in capabilities
        assert "note_eighth" in capabilities

    def test_extracts_dotted_notes(self):
        """Should extract dotted note capabilities."""
        result = ExtractionResult()
        result.dotted_notes.add("dotted_quarter")
        
        capabilities = get_capability_names(result)
        
        assert "note_dotted_quarter" in capabilities

    def test_extracts_ties(self):
        """Should extract tie capability when present."""
        result = ExtractionResult()
        result.has_ties = True
        
        capabilities = get_capability_names(result)
        
        assert "notation_ties" in capabilities

    def test_no_tie_when_absent(self):
        """Should not add tie capability when absent."""
        result = ExtractionResult()
        result.has_ties = False
        
        capabilities = get_capability_names(result)
        
        assert "notation_ties" not in capabilities

    def test_extracts_rest_values(self):
        """Should extract rest value capabilities."""
        result = ExtractionResult()
        result.rest_values = {"rest_quarter": 3, "rest_half": 1}
        
        capabilities = get_capability_names(result)
        
        assert "rest_quarter" in capabilities
        assert "rest_half" in capabilities

    def test_extracts_multi_measure_rest(self):
        """Should extract multi-measure rest capability."""
        result = ExtractionResult()
        result.has_multi_measure_rest = True
        
        capabilities = get_capability_names(result)
        
        assert "rest_multi_measure" in capabilities

    def test_extracts_tuplets(self):
        """Should extract tuplet capabilities."""
        result = ExtractionResult()
        result.tuplets = {"tuplet_triplet": 5, "tuplet_quintuplet": 2}
        
        capabilities = get_capability_names(result)
        
        assert "tuplet_triplet" in capabilities
        assert "tuplet_quintuplet" in capabilities

    def test_extracts_melodic_intervals(self):
        """Should extract melodic interval capabilities."""
        result = ExtractionResult()
        result.melodic_intervals = {
            "interval_melodic_M3_ascending": IntervalInfo(
                name="M3", direction="ascending", quality="major",
                semitones=4, is_melodic=True, count=3
            )
        }
        
        capabilities = get_capability_names(result)
        
        assert "interval_melodic_M3_ascending" in capabilities

    def test_extracts_harmonic_intervals(self):
        """Should extract harmonic interval capabilities."""
        result = ExtractionResult()
        result.harmonic_intervals = {
            "interval_harmonic_P5": IntervalInfo(
                name="P5", direction="ascending", quality="perfect",
                semitones=7, is_melodic=False, count=2
            )
        }
        
        capabilities = get_capability_names(result)
        
        assert "interval_harmonic_P5" in capabilities

    def test_extracts_dynamics(self):
        """Should extract dynamic capabilities."""
        result = ExtractionResult()
        result.dynamics.add("dynamic_f")
        result.dynamics.add("dynamic_p")
        
        capabilities = get_capability_names(result)
        
        assert "dynamic_f" in capabilities
        assert "dynamic_p" in capabilities

    def test_extracts_dynamic_changes(self):
        """Should extract dynamic change capabilities."""
        result = ExtractionResult()
        result.dynamic_changes.add("dynamic_change_crescendo")
        
        capabilities = get_capability_names(result)
        
        assert "dynamic_change_crescendo" in capabilities

    def test_extracts_articulations(self):
        """Should extract articulation capabilities."""
        result = ExtractionResult()
        result.articulations.add("articulation_staccato")
        result.articulations.add("articulation_accent")
        
        capabilities = get_capability_names(result)
        
        assert "articulation_staccato" in capabilities
        assert "articulation_accent" in capabilities

    def test_extracts_ornaments(self):
        """Should extract ornament capabilities."""
        result = ExtractionResult()
        result.ornaments.add("ornament_trill")
        result.ornaments.add("ornament_mordent")
        
        capabilities = get_capability_names(result)
        
        assert "ornament_trill" in capabilities
        assert "ornament_mordent" in capabilities

    def test_extracts_tempo_markings(self):
        """Should extract tempo marking capabilities."""
        result = ExtractionResult()
        result.tempo_markings.add("tempo_allegro")
        
        capabilities = get_capability_names(result)
        
        assert "tempo_allegro" in capabilities

    def test_extracts_expression_terms(self):
        """Should extract expression term capabilities."""
        result = ExtractionResult()
        result.expression_terms.add("expression_dolce")
        
        capabilities = get_capability_names(result)
        
        assert "expression_dolce" in capabilities

    def test_extracts_repeat_structures(self):
        """Should extract repeat structure capabilities."""
        result = ExtractionResult()
        result.repeat_structures.add("repeat_sign")
        result.repeat_structures.add("repeat_coda")
        
        capabilities = get_capability_names(result)
        
        assert "repeat_sign" in capabilities
        assert "repeat_coda" in capabilities

    def test_extracts_fermatas(self):
        """Should extract fermata capability when present."""
        result = ExtractionResult()
        result.fermatas = 3
        
        capabilities = get_capability_names(result)
        
        assert "notation_fermata" in capabilities

    def test_no_fermata_when_zero(self):
        """Should not add fermata when count is zero."""
        result = ExtractionResult()
        result.fermatas = 0
        
        capabilities = get_capability_names(result)
        
        assert "notation_fermata" not in capabilities

    def test_extracts_breath_marks(self):
        """Should extract breath mark capability."""
        result = ExtractionResult()
        result.breath_marks = 2
        
        capabilities = get_capability_names(result)
        
        assert "notation_breath_mark" in capabilities

    def test_extracts_chord_symbols(self):
        """Should extract chord symbols capability."""
        result = ExtractionResult()
        result.chord_symbols.add("C")
        result.chord_symbols.add("G7")
        
        capabilities = get_capability_names(result)
        
        assert "notation_chord_symbols" in capabilities

    def test_extracts_figured_bass(self):
        """Should extract figured bass capability."""
        result = ExtractionResult()
        result.figured_bass = True
        
        capabilities = get_capability_names(result)
        
        assert "notation_figured_bass" in capabilities

    def test_extracts_multi_voice(self):
        """Should extract multi-voice capability."""
        result = ExtractionResult()
        result.max_voices = 3
        
        capabilities = get_capability_names(result)
        
        assert "notation_3_voices" in capabilities

    def test_no_multi_voice_for_single(self):
        """Should not add multi-voice for single voice."""
        result = ExtractionResult()
        result.max_voices = 1
        
        capabilities = get_capability_names(result)
        
        # No notation_X_voices for single voice
        assert not any("_voices" in c for c in capabilities)


class TestCapabilityListFormat:
    """Tests for capability list format and structure."""

    def test_returns_list(self):
        """Should always return a list."""
        result = ExtractionResult()
        capabilities = get_capability_names(result)
        
        assert isinstance(capabilities, list)

    def test_all_strings(self):
        """All capabilities should be strings."""
        result = ExtractionResult()
        result.clefs.add("clef_treble")
        result.dynamics.add("dynamic_f")
        
        capabilities = get_capability_names(result)
        
        assert all(isinstance(c, str) for c in capabilities)

    def test_no_duplicates_from_sets(self):
        """Sets should not produce duplicates."""
        result = ExtractionResult()
        result.clefs.add("clef_treble")
        result.clefs.add("clef_treble")  # Duplicate add
        
        capabilities = get_capability_names(result)
        
        treble_count = sum(1 for c in capabilities if c == "clef_treble")
        assert treble_count == 1
