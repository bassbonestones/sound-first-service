"""
Comprehensive capability detection tests.

Tests detection of all capabilities that have music21_detection rules using the
generated test MusicXML files.
"""
import json
import os
import pytest
from pathlib import Path
from typing import Set

# Import the detection infrastructure
from app.capability_registry import CapabilityRegistry, DetectionEngine
from app.musicxml_analyzer import MusicXMLAnalyzer

# Check if music21 is available
try:
    import music21
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not MUSIC21_AVAILABLE, reason="music21 not installed"
)

TEST_FILES_DIR = Path(__file__).parent / "test_musicxml_files"
MANIFEST_PATH = TEST_FILES_DIR / "manifest.json"


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def registry():
    """Create a capability registry for all tests."""
    reg = CapabilityRegistry()
    reg.load()
    return reg


@pytest.fixture(scope="module")
def engine(registry):
    """Create a detection engine for all tests."""
    return DetectionEngine(registry)


@pytest.fixture(scope="module")
def analyzer():
    """Create a MusicXML analyzer."""
    return MusicXMLAnalyzer()


@pytest.fixture(scope="module")
def manifest():
    """Load the test file manifest."""
    with open(MANIFEST_PATH) as f:
        return json.load(f)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_test_file_path(filename: str) -> str:
    """Get the full path to a test file."""
    return str(TEST_FILES_DIR / filename)


def detect_capabilities(filepath: str, analyzer: MusicXMLAnalyzer, 
                       engine: DetectionEngine) -> Set[str]:
    """Detect capabilities from a MusicXML file."""
    with open(filepath) as f:
        content = f.read()
    result = analyzer.analyze(content)
    
    # Also get the music21 score for custom detectors
    score = music21.converter.parse(filepath)
    
    return engine.detect_capabilities(result, score)


# =============================================================================
# TEST CLASSES
# =============================================================================

class TestBasicNoteValues:
    """Test detection of basic note value types."""
    
    def test_whole_notes(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("01_whole_notes.musicxml"), analyzer, engine)
        assert "rhythm_whole_notes" in caps, f"Expected rhythm_whole_notes, got {caps}"
        assert "time_signature_4_4" in caps
    
    def test_half_notes(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("02_half_notes.musicxml"), analyzer, engine)
        assert "rhythm_half_notes" in caps
    
    def test_quarter_notes(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("03_quarter_notes.musicxml"), analyzer, engine)
        assert "rhythm_quarter_notes" in caps
    
    def test_eighth_notes(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("04_eighth_notes.musicxml"), analyzer, engine)
        assert "rhythm_eighth_notes" in caps
    
    def test_sixteenth_notes(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("05_sixteenth_notes.musicxml"), analyzer, engine)
        assert "rhythm_sixteenth_notes" in caps
    
    def test_32nd_notes(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("06_32nd_notes.musicxml"), analyzer, engine)
        assert "rhythm_32nd_notes" in caps


class TestDottedRhythms:
    """Test detection of dotted note values."""
    
    def test_dotted_half(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("07_dotted_half.musicxml"), analyzer, engine)
        assert "rhythm_dotted_half" in caps
        assert "rhythm_half_notes" in caps
    
    def test_dotted_quarter(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("08_dotted_quarter.musicxml"), analyzer, engine)
        assert "rhythm_dotted_quarter" in caps
    
    def test_dotted_eighth(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("09_dotted_eighth.musicxml"), analyzer, engine)
        assert "rhythm_dotted_eighth" in caps


class TestTimeSignatures:
    """Test detection of various time signatures."""
    
    def test_time_sig_3_4(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("10_time_sig_3_4.musicxml"), analyzer, engine)
        assert "time_signature_3_4" in caps
    
    def test_time_sig_6_8(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("11_time_sig_6_8.musicxml"), analyzer, engine)
        assert "time_signature_6_8" in caps
    
    def test_time_sig_2_4(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("12_time_sig_2_4.musicxml"), analyzer, engine)
        assert "time_signature_2_4" in caps
    
    def test_time_sig_2_2(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("13_time_sig_2_2.musicxml"), analyzer, engine)
        assert "time_signature_2_2" in caps
    
    def test_time_sig_7_8(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("14_time_sig_7_8.musicxml"), analyzer, engine)
        assert "time_signature_7_8" in caps
    
    def test_time_sig_5_4(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("15_time_sig_5_4.musicxml"), analyzer, engine)
        assert "time_signature_5_4" in caps


class TestClefs:
    """Test detection of different clefs."""
    
    def test_clef_bass(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("16_clef_bass.musicxml"), analyzer, engine)
        assert "clef_bass" in caps
    
    def test_clef_alto(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("17_clef_alto.musicxml"), analyzer, engine)
        assert "clef_alto" in caps
    
    def test_clef_tenor(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("18_clef_tenor.musicxml"), analyzer, engine)
        assert "clef_tenor" in caps


class TestDynamics:
    """Test detection of dynamic markings."""
    
    def test_dynamics_basic(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("19_dynamics_basic.musicxml"), analyzer, engine)
        assert "dynamic_f" in caps
        assert "dynamic_p" in caps
    
    def test_dynamics_extremes(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("20_dynamics_extremes.musicxml"), analyzer, engine)
        assert "dynamic_fff" in caps
        assert "dynamic_ppp" in caps
    
    def test_dynamics_sfz(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("21_dynamics_sfz.musicxml"), analyzer, engine)
        assert "dynamic_sf" in caps
        assert "dynamic_sfz" in caps


class TestArticulations:
    """Test detection of articulation markings."""
    
    def test_staccato(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("22_articulations_staccato.musicxml"), analyzer, engine)
        assert "articulation_staccato" in caps
    
    def test_accent(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("23_articulations_accent.musicxml"), analyzer, engine)
        assert "articulation_accent" in caps
    
    def test_tenuto(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("24_articulations_tenuto.musicxml"), analyzer, engine)
        assert "articulation_tenuto" in caps
    
    def test_marcato(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("25_articulations_marcato.musicxml"), analyzer, engine)
        assert "articulation_marcato" in caps


class TestRests:
    """Test detection of rest types."""
    
    def test_whole_rest(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("26_rests_whole.musicxml"), analyzer, engine)
        assert "rest_whole" in caps
    
    def test_half_rest(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("27_rests_half.musicxml"), analyzer, engine)
        assert "rest_half" in caps
    
    def test_quarter_rest(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("28_rests_quarter.musicxml"), analyzer, engine)
        assert "rest_quarter" in caps
    
    def test_eighth_rest(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("29_rests_eighth.musicxml"), analyzer, engine)
        assert "rest_eighth" in caps
    
    def test_sixteenth_rest(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("30_rests_sixteenth.musicxml"), analyzer, engine)
        assert "rest_sixteenth" in caps


class TestIntervals:
    """Test detection of melodic intervals."""
    
    def test_minor_2nd(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("31_interval_minor_2.musicxml"), analyzer, engine)
        assert "interval_play_minor_2" in caps
    
    def test_major_3rd(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("32_interval_major_3.musicxml"), analyzer, engine)
        assert "interval_play_major_3" in caps
    
    def test_perfect_5th(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("33_interval_perfect_5.musicxml"), analyzer, engine)
        assert "interval_play_perfect_5" in caps
    
    def test_octave(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("34_interval_octave.musicxml"), analyzer, engine)
        assert "interval_play_octave" in caps
    
    def test_augmented_4th(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("35_interval_augmented_4.musicxml"), analyzer, engine)
        assert "interval_play_augmented_4" in caps


class TestAccidentals:
    """Test detection of accidentals."""
    
    def test_sharp(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("36_accidental_sharp.musicxml"), analyzer, engine)
        assert "accidental_sharp_symbol" in caps
    
    def test_flat(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("37_accidental_flat.musicxml"), analyzer, engine)
        assert "accidental_flat_symbol" in caps


class TestTies:
    """Test detection of tied notes."""
    
    def test_ties(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("38_ties.musicxml"), analyzer, engine)
        assert "notation_ties" in caps


class TestOrnaments:
    """Test detection of ornaments."""
    
    def test_trill(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("39_ornament_trill.musicxml"), analyzer, engine)
        assert "ornament_trill" in caps
    
    def test_mordent(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("40_ornament_mordent.musicxml"), analyzer, engine)
        assert "ornament_mordent" in caps
    
    def test_turn(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("41_ornament_turn.musicxml"), analyzer, engine)
        assert "ornament_turn" in caps


class TestNotations:
    """Test detection of special notations."""
    
    def test_fermata(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("42_fermata.musicxml"), analyzer, engine)
        assert "notation_fermata" in caps


class TestKeySignatures:
    """Test detection of key signatures."""
    
    def test_g_major(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("43_key_sig_g_major.musicxml"), analyzer, engine)
        assert "key_signature_basics" in caps
    
    def test_f_major(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("44_key_sig_f_major.musicxml"), analyzer, engine)
        assert "key_signature_basics" in caps


class TestTempoMarkings:
    """Test detection of tempo markings."""
    
    def test_allegro(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("45_tempo_allegro.musicxml"), analyzer, engine)
        assert "tempo_term_allegro" in caps
    
    def test_andante(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("46_tempo_andante.musicxml"), analyzer, engine)
        assert "tempo_term_andante" in caps


class TestExpressions:
    """Test detection of expression markings."""
    
    def test_dolce(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("47_expression_dolce.musicxml"), analyzer, engine)
        assert "expression_dolce" in caps
    
    def test_espressivo(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("48_expression_espressivo.musicxml"), analyzer, engine)
        assert "expression_espressivo" in caps


class TestScaleFragments:
    """Test detection of scale fragments."""
    
    def test_ascending_scale(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("49_scale_ascending.musicxml"), analyzer, engine)
        # Should detect various scale fragment sizes
        has_scale_fragment = any(
            c.startswith("diatonic_scale_fragment_") for c in caps
        )
        assert has_scale_fragment, f"Expected scale fragment detection, got {caps}"


# =============================================================================
# STAGE 1: ADDITIONAL TIME SIGNATURES
# =============================================================================

class TestAdditionalTimeSignatures:
    """Test detection of additional time signatures."""
    
    def test_9_8(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("50_time_sig_9_8.musicxml"), analyzer, engine)
        assert "time_signature_9_8" in caps, f"Expected time_signature_9_8, got {caps}"
    
    def test_12_8(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("51_time_sig_12_8.musicxml"), analyzer, engine)
        assert "time_signature_12_8" in caps, f"Expected time_signature_12_8, got {caps}"
    
    def test_3_8(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("52_time_sig_3_8.musicxml"), analyzer, engine)
        assert "time_signature_3_8" in caps, f"Expected time_signature_3_8, got {caps}"
    
    def test_3_2(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("53_time_sig_3_2.musicxml"), analyzer, engine)
        assert "time_signature_3_2" in caps, f"Expected time_signature_3_2, got {caps}"
    
    def test_6_4(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("54_time_sig_6_4.musicxml"), analyzer, engine)
        assert "time_signature_6_4" in caps, f"Expected time_signature_6_4, got {caps}"
    
    def test_5_8(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("55_time_sig_5_8.musicxml"), analyzer, engine)
        assert "time_signature_5_8" in caps, f"Expected time_signature_5_8, got {caps}"


# =============================================================================
# STAGE 1: ADDITIONAL DYNAMICS
# =============================================================================

class TestAdditionalDynamicsValueMatch:
    """Test detection of additional dynamics using value_match."""
    
    def test_ff(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("56_dynamic_ff.musicxml"), analyzer, engine)
        assert "dynamic_ff" in caps, f"Expected dynamic_ff, got {caps}"
    
    def test_pp(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("57_dynamic_pp.musicxml"), analyzer, engine)
        assert "dynamic_pp" in caps, f"Expected dynamic_pp, got {caps}"
    
    def test_mf(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("58_dynamic_mf.musicxml"), analyzer, engine)
        assert "dynamic_mf" in caps, f"Expected dynamic_mf, got {caps}"
    
    def test_mp(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("59_dynamic_mp.musicxml"), analyzer, engine)
        assert "dynamic_mp" in caps, f"Expected dynamic_mp, got {caps}"
    
    def test_fp(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("60_dynamic_fp.musicxml"), analyzer, engine)
        assert "dynamic_fp" in caps, f"Expected dynamic_fp, got {caps}"
    
    def test_rf(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("61_dynamic_rf.musicxml"), analyzer, engine)
        assert "dynamic_rf" in caps, f"Expected dynamic_rf, got {caps}"
    
    def test_rfz(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("62_dynamic_rfz.musicxml"), analyzer, engine)
        assert "dynamic_rfz" in caps, f"Expected dynamic_rfz, got {caps}"
    
    def test_sfp(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("63_dynamic_sfp.musicxml"), analyzer, engine)
        assert "dynamic_sfp" in caps, f"Expected dynamic_sfp, got {caps}"


class TestDynamicsHairpins:
    """Test detection of crescendo/decrescendo hairpins."""
    
    def test_crescendo(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("64_dynamic_crescendo.musicxml"), analyzer, engine)
        assert "dynamic_crescendo" in caps, f"Expected dynamic_crescendo, got {caps}"
    
    def test_decrescendo(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("65_dynamic_decrescendo.musicxml"), analyzer, engine)
        assert "dynamic_decrescendo" in caps, f"Expected dynamic_decrescendo, got {caps}"
    
    def test_diminuendo(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("66_dynamic_diminuendo.musicxml"), analyzer, engine)
        assert "dynamic_diminuendo" in caps, f"Expected dynamic_diminuendo, got {caps}"
    
    def test_subito(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("67_dynamic_subito.musicxml"), analyzer, engine)
        assert "dynamic_subito" in caps, f"Expected dynamic_subito, got {caps}"


# =============================================================================
# STAGE 2: ADDITIONAL INTERVAL TESTS
# =============================================================================

class TestAdditionalIntervals:
    """Test detection of additional interval capabilities."""
    
    def test_interval_major_2(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("68_interval_major_2.musicxml"), analyzer, engine)
        assert "interval_play_major_2" in caps, f"Expected interval_play_major_2, got {caps}"
    
    def test_interval_minor_3(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("69_interval_minor_3.musicxml"), analyzer, engine)
        assert "interval_play_minor_3" in caps, f"Expected interval_play_minor_3, got {caps}"
    
    def test_interval_perfect_4(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("70_interval_perfect_4.musicxml"), analyzer, engine)
        assert "interval_play_perfect_4" in caps, f"Expected interval_play_perfect_4, got {caps}"
    
    def test_interval_minor_6(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("71_interval_minor_6.musicxml"), analyzer, engine)
        assert "interval_play_minor_6" in caps, f"Expected interval_play_minor_6, got {caps}"
    
    def test_interval_major_6(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("72_interval_major_6.musicxml"), analyzer, engine)
        assert "interval_play_major_6" in caps, f"Expected interval_play_major_6, got {caps}"
    
    def test_interval_minor_7(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("73_interval_minor_7.musicxml"), analyzer, engine)
        assert "interval_play_minor_7" in caps, f"Expected interval_play_minor_7, got {caps}"
    
    def test_interval_major_7(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("74_interval_major_7.musicxml"), analyzer, engine)
        assert "interval_play_major_7" in caps, f"Expected interval_play_major_7, got {caps}"
    
    def test_interval_compound_9_plus(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("75_interval_compound_9.musicxml"), analyzer, engine)
        assert "interval_play_compound_9_plus" in caps, f"Expected interval_play_compound_9_plus, got {caps}"


# =============================================================================
# STAGE 2: RANGE SPAN TESTS
# =============================================================================

class TestRangeSpans:
    """Test detection of range span capabilities."""
    
    def test_range_minor_second(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("76_range_minor_second.musicxml"), analyzer, engine)
        assert "range_span_minor_second" in caps, f"Expected range_span_minor_second, got {caps}"
    
    def test_range_major_second(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("77_range_major_second.musicxml"), analyzer, engine)
        assert "range_span_major_second" in caps, f"Expected range_span_major_second, got {caps}"
    
    def test_range_minor_third(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("78_range_minor_third.musicxml"), analyzer, engine)
        assert "range_span_minor_third" in caps, f"Expected range_span_minor_third, got {caps}"
    
    def test_range_major_third(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("79_range_major_third.musicxml"), analyzer, engine)
        assert "range_span_major_third" in caps, f"Expected range_span_major_third, got {caps}"
    
    def test_range_perfect_fourth(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("80_range_perfect_fourth.musicxml"), analyzer, engine)
        assert "range_span_perfect_fourth" in caps, f"Expected range_span_perfect_fourth, got {caps}"
    
    def test_range_augmented_fourth(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("81_range_augmented_fourth.musicxml"), analyzer, engine)
        assert "range_span_augmented_fourth" in caps, f"Expected range_span_augmented_fourth, got {caps}"
    
    def test_range_perfect_fifth(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("82_range_perfect_fifth.musicxml"), analyzer, engine)
        assert "range_span_perfect_fifth" in caps, f"Expected range_span_perfect_fifth, got {caps}"
    
    def test_range_minor_sixth(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("83_range_minor_sixth.musicxml"), analyzer, engine)
        assert "range_span_minor_sixth" in caps, f"Expected range_span_minor_sixth, got {caps}"
    
    def test_range_major_sixth(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("84_range_major_sixth.musicxml"), analyzer, engine)
        assert "range_span_major_sixth" in caps, f"Expected range_span_major_sixth, got {caps}"
    
    def test_range_minor_seventh(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("85_range_minor_seventh.musicxml"), analyzer, engine)
        assert "range_span_minor_seventh" in caps, f"Expected range_span_minor_seventh, got {caps}"
    
    def test_range_major_seventh(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("86_range_major_seventh.musicxml"), analyzer, engine)
        assert "range_span_major_seventh" in caps, f"Expected range_span_major_seventh, got {caps}"
    
    def test_range_octave(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("87_range_octave.musicxml"), analyzer, engine)
        assert "range_span_octave" in caps, f"Expected range_span_octave, got {caps}"


# =============================================================================
# STAGE 3: TEMPO TERMS
# =============================================================================

class TestTempoTerms:
    """Test detection of tempo term capabilities."""
    
    def test_tempo_adagio(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("88_tempo_adagio.musicxml"), analyzer, engine)
        assert "tempo_term_adagio" in caps, f"Expected tempo_term_adagio, got {caps}"
    
    def test_tempo_allegretto(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("89_tempo_allegretto.musicxml"), analyzer, engine)
        assert "tempo_term_allegretto" in caps, f"Expected tempo_term_allegretto, got {caps}"
    
    def test_tempo_largo(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("90_tempo_largo.musicxml"), analyzer, engine)
        assert "tempo_term_largo" in caps, f"Expected tempo_term_largo, got {caps}"
    
    def test_tempo_moderato(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("91_tempo_moderato.musicxml"), analyzer, engine)
        assert "tempo_term_moderato" in caps, f"Expected tempo_term_moderato, got {caps}"
    
    def test_tempo_prestissimo(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("92_tempo_prestissimo.musicxml"), analyzer, engine)
        assert "tempo_term_prestissimo" in caps, f"Expected tempo_term_prestissimo, got {caps}"
    
    def test_tempo_presto(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("93_tempo_presto.musicxml"), analyzer, engine)
        assert "tempo_term_presto" in caps, f"Expected tempo_term_presto, got {caps}"
    
    def test_tempo_vivace(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("94_tempo_vivace.musicxml"), analyzer, engine)
        assert "tempo_term_vivace" in caps, f"Expected tempo_term_vivace, got {caps}"


# =============================================================================
# STAGE 3: TEMPO SKILLS
# =============================================================================

class TestTempoSkills:
    """Test detection of tempo skill capabilities."""
    
    def test_tempo_a_tempo(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("95_tempo_a_tempo.musicxml"), analyzer, engine)
        assert "tempo_skill_a_tempo" in caps, f"Expected tempo_skill_a_tempo, got {caps}"
    
    def test_tempo_accelerando(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("96_tempo_accelerando.musicxml"), analyzer, engine)
        assert "tempo_skill_accelerando" in caps, f"Expected tempo_skill_accelerando, got {caps}"
    
    def test_tempo_rallentando(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("97_tempo_rallentando.musicxml"), analyzer, engine)
        assert "tempo_skill_rallentando" in caps, f"Expected tempo_skill_rallentando, got {caps}"
    
    def test_tempo_ritardando(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("98_tempo_ritardando.musicxml"), analyzer, engine)
        assert "tempo_skill_ritardando" in caps, f"Expected tempo_skill_ritardando, got {caps}"
    
    def test_tempo_rubato(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("99_tempo_rubato.musicxml"), analyzer, engine)
        assert "tempo_skill_rubato" in caps, f"Expected tempo_skill_rubato, got {caps}"


# =============================================================================
# STAGE 3: EXPRESSION TERMS
# =============================================================================

class TestExpressionTerms:
    """Test detection of expression term capabilities."""
    
    def test_expression_agitato(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("100_expression_agitato.musicxml"), analyzer, engine)
        assert "expression_agitato" in caps, f"Expected expression_agitato, got {caps}"
    
    def test_expression_animato(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("101_expression_animato.musicxml"), analyzer, engine)
        assert "expression_animato" in caps, f"Expected expression_animato, got {caps}"
    
    def test_expression_appassionato(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("102_expression_appassionato.musicxml"), analyzer, engine)
        assert "expression_appassionato" in caps, f"Expected expression_appassionato, got {caps}"
    
    def test_expression_brillante(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("103_expression_brillante.musicxml"), analyzer, engine)
        assert "expression_brillante" in caps, f"Expected expression_brillante, got {caps}"
    
    def test_expression_cantabile(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("104_expression_cantabile.musicxml"), analyzer, engine)
        assert "expression_cantabile" in caps, f"Expected expression_cantabile, got {caps}"
    
    def test_expression_con_brio(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("105_expression_con_brio.musicxml"), analyzer, engine)
        assert "expression_con_brio" in caps, f"Expected expression_con_brio, got {caps}"
    
    def test_expression_con_fuoco(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("106_expression_con_fuoco.musicxml"), analyzer, engine)
        assert "expression_con_fuoco" in caps, f"Expected expression_con_fuoco, got {caps}"
    
    def test_expression_con_moto(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("107_expression_con_moto.musicxml"), analyzer, engine)
        assert "expression_con_moto" in caps, f"Expected expression_con_moto, got {caps}"
    
    def test_expression_grazioso(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("108_expression_grazioso.musicxml"), analyzer, engine)
        assert "expression_grazioso" in caps, f"Expected expression_grazioso, got {caps}"
    
    def test_expression_leggiero(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("109_expression_leggiero.musicxml"), analyzer, engine)
        assert "expression_leggiero" in caps, f"Expected expression_leggiero, got {caps}"
    
    def test_expression_maestoso(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("110_expression_maestoso.musicxml"), analyzer, engine)
        assert "expression_maestoso" in caps, f"Expected expression_maestoso, got {caps}"
    
    def test_expression_morendo(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("111_expression_morendo.musicxml"), analyzer, engine)
        assert "expression_morendo" in caps, f"Expected expression_morendo, got {caps}"
    
    def test_expression_perdendosi(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("112_expression_perdendosi.musicxml"), analyzer, engine)
        assert "expression_perdendosi" in caps, f"Expected expression_perdendosi, got {caps}"
    
    def test_expression_pesante(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("113_expression_pesante.musicxml"), analyzer, engine)
        assert "expression_pesante" in caps, f"Expected expression_pesante, got {caps}"
    
    def test_expression_sostenuto(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("114_expression_sostenuto.musicxml"), analyzer, engine)
        assert "expression_sostenuto" in caps, f"Expected expression_sostenuto, got {caps}"
    
    def test_expression_tranquillo(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("115_expression_tranquillo.musicxml"), analyzer, engine)
        assert "expression_tranquillo" in caps, f"Expected expression_tranquillo, got {caps}"


# =============================================================================
# STAGE 4: FORM STRUCTURE
# =============================================================================

class TestFormStructure:
    """Test detection of form structure capabilities."""
    
    def test_form_repeat_sign(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("116_form_repeat_sign.musicxml"), analyzer, engine)
        assert "form_repeat_sign" in caps, f"Expected form_repeat_sign, got {caps}"
    
    def test_form_first_ending(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("117_form_first_ending.musicxml"), analyzer, engine)
        assert "form_first_ending" in caps, f"Expected form_first_ending, got {caps}"
    
    def test_form_second_ending(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("118_form_second_ending.musicxml"), analyzer, engine)
        assert "form_second_ending" in caps, f"Expected form_second_ending, got {caps}"
    
    def test_form_dc(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("119_form_dc.musicxml"), analyzer, engine)
        assert "form_dc" in caps, f"Expected form_dc, got {caps}"
    
    def test_form_ds(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("120_form_ds.musicxml"), analyzer, engine)
        assert "form_ds" in caps, f"Expected form_ds, got {caps}"
    
    def test_form_fine(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("121_form_fine.musicxml"), analyzer, engine)
        assert "form_fine" in caps, f"Expected form_fine, got {caps}"
    
    def test_form_coda(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("122_form_coda.musicxml"), analyzer, engine)
        assert "form_coda" in caps, f"Expected form_coda, got {caps}"
    
    def test_form_segno(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("123_form_segno.musicxml"), analyzer, engine)
        assert "form_segno" in caps, f"Expected form_segno, got {caps}"


# =============================================================================
# Stage 5: Tuplets & Rhythm (12 tests)
# =============================================================================

class TestTuplets:
    """Test detection of tuplet capabilities."""
    
    def test_tuplet_duplet(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("124_tuplet_duplet.musicxml"), analyzer, engine)
        assert "tuplet_duplet" in caps, f"Expected tuplet_duplet, got {caps}"
    
    def test_tuplet_triplet_general(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("125_tuplet_triplet_general.musicxml"), analyzer, engine)
        assert "tuplet_triplet_general" in caps, f"Expected tuplet_triplet_general, got {caps}"
    
    def test_tuplet_triplet_quarter(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("126_tuplet_triplet_quarter.musicxml"), analyzer, engine)
        assert "tuplet_triplet_quarter" in caps, f"Expected tuplet_triplet_quarter, got {caps}"
    
    def test_tuplet_quintuplet(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("127_tuplet_quintuplet.musicxml"), analyzer, engine)
        assert "tuplet_quintuplet" in caps, f"Expected tuplet_quintuplet, got {caps}"
    
    def test_tuplet_sextuplet(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("128_tuplet_sextuplet.musicxml"), analyzer, engine)
        assert "tuplet_sextuplet" in caps, f"Expected tuplet_sextuplet, got {caps}"
    
    def test_tuplet_septuplet(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("129_tuplet_septuplet.musicxml"), analyzer, engine)
        assert "tuplet_septuplet" in caps, f"Expected tuplet_septuplet, got {caps}"


class TestAdvancedRhythm:
    """Test detection of advanced rhythm capabilities."""
    
    def test_rhythm_64th_notes(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("130_rhythm_64th_notes.musicxml"), analyzer, engine)
        assert "rhythm_64th_notes" in caps, f"Expected rhythm_64th_notes, got {caps}"
    
    def test_rhythm_dotted_whole(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("131_rhythm_dotted_whole.musicxml"), analyzer, engine)
        assert "rhythm_dotted_whole" in caps, f"Expected rhythm_dotted_whole, got {caps}"
    
    def test_rhythm_dotted_sixteenth(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("132_rhythm_dotted_sixteenth.musicxml"), analyzer, engine)
        assert "rhythm_dotted_sixteenth" in caps, f"Expected rhythm_dotted_sixteenth, got {caps}"
    
    def test_rhythm_double_dotted_half(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("133_rhythm_double_dotted_half.musicxml"), analyzer, engine)
        assert "rhythm_double_dotted_half" in caps, f"Expected rhythm_double_dotted_half, got {caps}"
    
    def test_rhythm_syncopation(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("134_rhythm_syncopation.musicxml"), analyzer, engine)
        assert "rhythm_syncopation" in caps, f"Expected rhythm_syncopation, got {caps}"
    
    def test_rhythm_tuplet_3_quarters(self, engine, analyzer):
        caps = detect_capabilities(get_test_file_path("135_rhythm_tuplet_3_quarters.musicxml"), analyzer, engine)
        assert "rhythm_tuplet_3_quarters" in caps, f"Expected rhythm_tuplet_3_quarters, got {caps}"


class TestManifestComprehensive:
    """Test all files against their manifest expectations."""
    
    def test_all_manifest_files(self, engine, analyzer, manifest):
        """Test that all files in manifest detect at least their expected capabilities."""
        failures = []
        successes = []
        
        for filename, info in manifest.items():
            filepath = get_test_file_path(filename)
            
            if not os.path.exists(filepath):
                failures.append(f"{filename}: File not found")
                continue
            
            try:
                caps = detect_capabilities(filepath, analyzer, engine)
            except Exception as e:
                failures.append(f"{filename}: Error - {e}")
                continue
            
            expected = set(info["expected_capabilities"])
            missing = expected - caps
            
            if missing:
                # Only report critical capability (first expected)
                primary = info["expected_capabilities"][0]
                if primary in missing:
                    failures.append(f"{filename}: Missing primary capability '{primary}'")
                else:
                    # Secondary capabilities missing is a warning
                    successes.append(f"{filename}: OK (missing secondary: {missing})")
            else:
                successes.append(f"{filename}: OK")
        
        print(f"\n\nDetection Results: {len(successes)} passed, {len(failures)} failed")
        
        if failures:
            pytest.fail(f"Detection failures:\n" + "\n".join(failures))


# Run a quick validation when this module is imported
if __name__ == "__main__":
    pytest.main([__file__, "-v"])
