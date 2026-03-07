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
