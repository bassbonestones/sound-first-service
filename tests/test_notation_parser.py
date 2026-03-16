"""
Tests for analyzers/notation_parser.py

Tests for notation element extraction functions.
Uses music21 mocking at the source level since imports are deferred.
"""

import pytest
from unittest.mock import MagicMock, patch
import sys

from app.analyzers.extraction_models import ExtractionResult
from app.analyzers.notation_parser import (
    extract_metadata,
    extract_clefs,
    extract_time_signatures,
    extract_key_signatures,
    extract_dynamics,
    extract_articulations,
    extract_ornaments,
    extract_tempo_expression,
    extract_repeats,
    extract_other_notation,
)


@pytest.fixture
def extraction_result():
    """Create a fresh ExtractionResult for testing."""
    return ExtractionResult()


class TestExtractMetadata:
    """Tests for extract_metadata function."""

    def test_extracts_title_and_composer(self, extraction_result):
        """Should extract title and composer from metadata."""
        mock_score = MagicMock()
        mock_score.metadata.title = "Test Piece"
        mock_score.metadata.composer = "Test Composer"
        
        extract_metadata(mock_score, extraction_result)
        
        assert extraction_result.title == "Test Piece"
        assert extraction_result.composer == "Test Composer"

    def test_handles_no_metadata(self, extraction_result):
        """Should handle score with no metadata."""
        mock_score = MagicMock()
        mock_score.metadata = None
        
        extract_metadata(mock_score, extraction_result)
        
        assert extraction_result.title is None

    def test_handles_partial_metadata(self, extraction_result):
        """Should handle metadata with only title."""
        mock_score = MagicMock()
        mock_score.metadata.title = "Only Title"
        mock_score.metadata.composer = None
        
        extract_metadata(mock_score, extraction_result)
        
        assert extraction_result.title == "Only Title"
        assert extraction_result.composer is None


class TestExtractClefs:
    """Tests for extract_clefs function."""

    def test_extracts_known_clef(self, extraction_result):
        """Should extract known clef types from CLEF_CAPABILITY_MAP."""
        with patch.dict(sys.modules, {'music21.clef': MagicMock()}):
            # Create a mock clef
            mock_clef_obj = MagicMock()
            type(mock_clef_obj).__name__ = "TrebleClef"
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.return_value = [mock_clef_obj]
            
            extract_clefs(mock_score, extraction_result)
            
            # TrebleClef is in CLEF_CAPABILITY_MAP
            assert "clef_treble" in extraction_result.clefs

    def test_handles_unknown_clef_with_sign(self, extraction_result):
        """Should handle unknown clef types using sign attribute."""
        with patch.dict(sys.modules, {'music21.clef': MagicMock()}):
            mock_clef_obj = MagicMock()
            type(mock_clef_obj).__name__ = "UnknownClef"
            mock_clef_obj.sign = "C"
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.return_value = [mock_clef_obj]
            
            extract_clefs(mock_score, extraction_result)
            
            assert "clef_c" in extraction_result.clefs


class TestExtractTimeSignatures:
    """Tests for extract_time_signatures function."""

    def test_extracts_common_time(self, extraction_result):
        """Should extract 4/4 time signature."""
        with patch.dict(sys.modules, {'music21.meter': MagicMock()}):
            mock_ts = MagicMock()
            mock_ts.numerator = 4
            mock_ts.denominator = 4
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.return_value = [mock_ts]
            
            extract_time_signatures(mock_score, extraction_result)
            
            assert "time_sig_4_4" in extraction_result.time_signatures

    def test_extracts_complex_time(self, extraction_result):
        """Should extract complex time signatures."""
        with patch.dict(sys.modules, {'music21.meter': MagicMock()}):
            mock_ts = MagicMock()
            mock_ts.numerator = 7
            mock_ts.denominator = 8
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.return_value = [mock_ts]
            
            extract_time_signatures(mock_score, extraction_result)
            
            assert "time_sig_7_8" in extraction_result.time_signatures

    def test_extracts_multiple_time_signatures(self, extraction_result):
        """Should extract multiple different time signatures."""
        with patch.dict(sys.modules, {'music21.meter': MagicMock()}):
            mock_ts1 = MagicMock()
            mock_ts1.numerator = 4
            mock_ts1.denominator = 4
            
            mock_ts2 = MagicMock()
            mock_ts2.numerator = 3
            mock_ts2.denominator = 4
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.return_value = [mock_ts1, mock_ts2]
            
            extract_time_signatures(mock_score, extraction_result)
            
            assert "time_sig_4_4" in extraction_result.time_signatures
            assert "time_sig_3_4" in extraction_result.time_signatures


class TestExtractKeySignatures:
    """Tests for extract_key_signatures function."""

    def test_extracts_major_key(self, extraction_result):
        """Should extract major key signature."""
        with patch.dict(sys.modules, {'music21.key': MagicMock()}):
            mock_ks = MagicMock()
            mock_k = MagicMock()
            mock_k.mode = 'major'
            mock_k.tonic.name = 'C'
            mock_ks.asKey.return_value = mock_k
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.return_value = [mock_ks]
            
            extract_key_signatures(mock_score, extraction_result)
            
            assert "key_C_major" in extraction_result.key_signatures

    def test_extracts_minor_key(self, extraction_result):
        """Should extract minor key signature."""
        with patch.dict(sys.modules, {'music21.key': MagicMock()}):
            mock_ks = MagicMock()
            mock_k = MagicMock()
            mock_k.mode = 'minor'
            mock_k.tonic.name = 'A'
            mock_ks.asKey.return_value = mock_k
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.return_value = [mock_ks]
            
            extract_key_signatures(mock_score, extraction_result)
            
            assert "key_A_minor" in extraction_result.key_signatures

    def test_handles_sharps_key_without_asKey(self, extraction_result):
        """Should handle key signature without asKey using sharps count."""
        with patch.dict(sys.modules, {'music21.key': MagicMock()}):
            # Create an object without asKey attribute
            mock_ks = MagicMock(spec=['sharps'])
            mock_ks.sharps = 2
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.return_value = [mock_ks]
            
            extract_key_signatures(mock_score, extraction_result)
            
            assert "key_sig_2_sharps" in extraction_result.key_signatures

    def test_handles_flats_key(self, extraction_result):
        """Should handle key signature with flats (negative sharps)."""
        with patch.dict(sys.modules, {'music21.key': MagicMock()}):
            mock_ks = MagicMock(spec=['sharps'])
            mock_ks.sharps = -3
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.return_value = [mock_ks]
            
            extract_key_signatures(mock_score, extraction_result)
            
            assert "key_sig_3_flats" in extraction_result.key_signatures


class TestExtractDynamics:
    """Tests for extract_dynamics function."""

    def test_extracts_known_dynamic(self, extraction_result):
        """Should extract known dynamic value."""
        with patch.dict(sys.modules, {
            'music21.dynamics': MagicMock(),
            'music21.expressions': MagicMock()
        }):
            mock_d = MagicMock()
            mock_d.value = 'f'  # forte
            
            mock_score = MagicMock()
            # Return dynamics, then empty for wedges, then empty for text
            mock_score.recurse.return_value.getElementsByClass.side_effect = [
                [mock_d],
                [],
                [],
            ]
            
            extract_dynamics(mock_score, extraction_result)
            
            # 'f' maps to dynamic_f (not dynamic_forte)
            assert "dynamic_f" in extraction_result.dynamics

    def test_extracts_unknown_dynamic(self, extraction_result):
        """Should handle unknown dynamic values."""
        with patch.dict(sys.modules, {
            'music21.dynamics': MagicMock(),
            'music21.expressions': MagicMock()
        }):
            mock_d = MagicMock()
            mock_d.value = 'sfz'  # Not in map
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.side_effect = [
                [mock_d], [], []
            ]
            
            extract_dynamics(mock_score, extraction_result)
            
            assert "dynamic_sfz" in extraction_result.dynamics


class TestExtractArticulations:
    """Tests for extract_articulations function."""

    def test_extracts_known_articulation(self, extraction_result):
        """Should extract known articulation type."""
        mock_art = MagicMock()
        type(mock_art).__name__ = "Staccato"
        
        mock_note = MagicMock()
        mock_note.articulations = [mock_art]
        
        mock_score = MagicMock()
        mock_score.recurse.return_value.notes = [mock_note]
        
        extract_articulations(mock_score, extraction_result)
        
        # Staccato is in ARTICULATION_CAPABILITY_MAP
        assert "articulation_staccato" in extraction_result.articulations

    def test_extracts_unknown_articulation(self, extraction_result):
        """Should handle unknown articulation types."""
        mock_art = MagicMock()
        type(mock_art).__name__ = "CustomArticulation"
        
        mock_note = MagicMock()
        mock_note.articulations = [mock_art]
        
        mock_score = MagicMock()
        mock_score.recurse.return_value.notes = [mock_note]
        
        extract_articulations(mock_score, extraction_result)
        
        assert "articulation_customarticulation" in extraction_result.articulations

    def test_handles_notes_without_articulations(self, extraction_result):
        """Should handle notes with no articulations."""
        mock_note = MagicMock()
        mock_note.articulations = []
        
        mock_score = MagicMock()
        mock_score.recurse.return_value.notes = [mock_note]
        
        extract_articulations(mock_score, extraction_result)
        
        assert len(extraction_result.articulations) == 0


class TestExtractOrnaments:
    """Tests for extract_ornaments function."""

    def test_extracts_known_ornament(self, extraction_result):
        """Should extract known ornament type."""
        with patch.dict(sys.modules, {'music21.expressions': MagicMock()}):
            mock_orn = MagicMock()
            type(mock_orn).__name__ = "Trill"
            
            mock_note = MagicMock()
            mock_note.expressions = [mock_orn]
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.notes = [mock_note]
            
            extract_ornaments(mock_score, extraction_result)
            
            # Trill is in ORNAMENT_CAPABILITY_MAP
            assert "ornament_trill" in extraction_result.ornaments

    def test_extracts_grace_note(self, extraction_result):
        """Should extract grace notes."""
        with patch.dict(sys.modules, {'music21.expressions': MagicMock()}):
            mock_grace = MagicMock()
            type(mock_grace).__name__ = "GraceNote"
            
            mock_note = MagicMock()
            mock_note.expressions = [mock_grace]
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.notes = [mock_note]
            
            extract_ornaments(mock_score, extraction_result)
            
            assert "ornament_grace_note" in extraction_result.ornaments

    def test_extracts_appoggiatura(self, extraction_result):
        """Should extract appoggiatura."""
        with patch.dict(sys.modules, {'music21.expressions': MagicMock()}):
            mock_app = MagicMock()
            type(mock_app).__name__ = "Appoggiatura"
            
            mock_note = MagicMock()
            mock_note.expressions = [mock_app]
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.notes = [mock_note]
            
            extract_ornaments(mock_score, extraction_result)
            
            assert "ornament_appoggiatura" in extraction_result.ornaments


class TestExtractTempoExpression:
    """Tests for extract_tempo_expression function."""

    def test_builds_tempo_profile(self, extraction_result):
        """Should build tempo profile using tempo analyzer."""
        with patch.dict(sys.modules, {
            'music21.tempo': MagicMock(),
            'music21.expressions': MagicMock()
        }):
            with patch('app.analyzers.notation_parser.build_tempo_profile') as mock_build:
                with patch('app.analyzers.notation_parser.get_legacy_tempo_bpm') as mock_legacy:
                    mock_profile = MagicMock()
                    mock_build.return_value = mock_profile
                    mock_legacy.return_value = 120
                    
                    mock_score = MagicMock()
                    mock_score.recurse.return_value.getElementsByClass.return_value = []
                    
                    extract_tempo_expression(mock_score, extraction_result)
                    
                    mock_build.assert_called_once_with(mock_score)
                    assert extraction_result.tempo_profile == mock_profile
                    assert extraction_result.tempo_bpm == 120

    def test_extracts_tempo_term(self, extraction_result):
        """Should extract tempo terms from metronome marks."""
        with patch.dict(sys.modules, {
            'music21.tempo': MagicMock(),
            'music21.expressions': MagicMock()
        }):
            with patch('app.analyzers.notation_parser.build_tempo_profile'):
                with patch('app.analyzers.notation_parser.get_legacy_tempo_bpm'):
                    mock_mm = MagicMock()
                    mock_mm.text = "Allegro"
                    
                    mock_score = MagicMock()
                    mock_score.recurse.return_value.getElementsByClass.side_effect = [
                        [mock_mm],  # MetronomeMark
                        [],  # TempoText
                        [],  # TextExpression
                    ]
                    
                    extract_tempo_expression(mock_score, extraction_result)
                    
                    assert "tempo_allegro" in extraction_result.tempo_markings

    def test_extracts_expression_terms(self, extraction_result):
        """Should extract expression terms from text expressions."""
        with patch.dict(sys.modules, {
            'music21.tempo': MagicMock(),
            'music21.expressions': MagicMock()
        }):
            with patch('app.analyzers.notation_parser.build_tempo_profile'):
                with patch('app.analyzers.notation_parser.get_legacy_tempo_bpm'):
                    mock_te = MagicMock()
                    mock_te.content = "dolce"
                    
                    mock_score = MagicMock()
                    mock_score.recurse.return_value.getElementsByClass.side_effect = [
                        [],  # MetronomeMark
                        [],  # TempoText
                        [mock_te],  # TextExpression
                    ]
                    
                    extract_tempo_expression(mock_score, extraction_result)
                    
                    assert "expression_dolce" in extraction_result.expression_terms


class TestExtractRepeats:
    """Tests for extract_repeats function."""

    def test_extracts_repeat_mark(self, extraction_result):
        """Should extract repeat marks."""
        with patch.dict(sys.modules, {
            'music21.repeat': MagicMock(),
            'music21.expressions': MagicMock(),
            'music21.spanner': MagicMock()
        }):
            mock_rm = MagicMock()
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.side_effect = [
                [mock_rm],  # RepeatMark
                [],  # Barline
                [],  # TextExpression
                [],  # RepeatBracket
            ]
            
            extract_repeats(mock_score, extraction_result)
            
            assert "repeat_sign" in extraction_result.repeat_structures

    def test_extracts_da_capo(self, extraction_result):
        """Should extract Da Capo from text."""
        with patch.dict(sys.modules, {
            'music21.repeat': MagicMock(),
            'music21.expressions': MagicMock(),
            'music21.spanner': MagicMock()
        }):
            mock_te = MagicMock()
            mock_te.content = "D.C. al Fine"
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.side_effect = [
                [],  # RepeatMark
                [],  # Barline
                [mock_te],  # TextExpression
                [],  # RepeatBracket
            ]
            
            extract_repeats(mock_score, extraction_result)
            
            assert "repeat_dc" in extraction_result.repeat_structures

    def test_extracts_dal_segno(self, extraction_result):
        """Should extract Dal Segno from text."""
        with patch.dict(sys.modules, {
            'music21.repeat': MagicMock(),
            'music21.expressions': MagicMock(),
            'music21.spanner': MagicMock()
        }):
            mock_te = MagicMock()
            mock_te.content = "D.S. al Coda"
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.side_effect = [
                [],  # RepeatMark
                [],  # Barline
                [mock_te],  # TextExpression  
                [],  # RepeatBracket
            ]
            
            extract_repeats(mock_score, extraction_result)
            
            assert "repeat_ds" in extraction_result.repeat_structures
            assert "repeat_coda" in extraction_result.repeat_structures

    def test_extracts_repeat_brackets(self, extraction_result):
        """Should extract first/second endings."""
        with patch.dict(sys.modules, {
            'music21.repeat': MagicMock(),
            'music21.expressions': MagicMock(),
            'music21.spanner': MagicMock()
        }):
            mock_bracket = MagicMock()
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.side_effect = [
                [],  # RepeatMark
                [],  # Barline
                [],  # TextExpression
                [mock_bracket],  # RepeatBracket
            ]
            
            extract_repeats(mock_score, extraction_result)
            
            assert "repeat_first_ending" in extraction_result.repeat_structures
            assert "repeat_second_ending" in extraction_result.repeat_structures


class TestExtractOtherNotation:
    """Tests for extract_other_notation function."""

    def test_extracts_breath_marks_from_text(self, extraction_result):
        """Should extract breath marks from text expressions."""
        with patch.dict(sys.modules, {'music21.expressions': MagicMock()}):
            mock_te = MagicMock()
            mock_te.content = "breath"
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.side_effect = [
                [mock_te],  # TextExpression
                [],  # ChordSymbol
                [],  # FiguredBass
            ]
            mock_score.recurse.return_value.notes = []
            
            extract_other_notation(mock_score, extraction_result)
            
            assert extraction_result.breath_marks >= 1

    def test_extracts_chord_symbols(self, extraction_result):
        """Should extract chord symbols."""
        with patch.dict(sys.modules, {'music21.expressions': MagicMock()}):
            mock_cs = MagicMock()
            mock_cs.figure = "Cmaj7"
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.side_effect = [
                [],  # TextExpression
                [mock_cs],  # ChordSymbol
                [],  # FiguredBass
            ]
            mock_score.recurse.return_value.notes = []
            
            extract_other_notation(mock_score, extraction_result)
            
            assert "Cmaj7" in extraction_result.chord_symbols

    def test_extracts_figured_bass(self, extraction_result):
        """Should detect figured bass presence."""
        with patch.dict(sys.modules, {'music21.expressions': MagicMock()}):
            mock_fb = MagicMock()
            
            mock_score = MagicMock()
            mock_score.recurse.return_value.getElementsByClass.side_effect = [
                [],  # TextExpression
                [],  # ChordSymbol
                [mock_fb],  # FiguredBass
            ]
            mock_score.recurse.return_value.notes = []
            
            extract_other_notation(mock_score, extraction_result)
            
            assert extraction_result.figured_bass is True
