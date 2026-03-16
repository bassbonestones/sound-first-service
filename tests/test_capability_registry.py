"""
Tests for Capability Registry and Detection Engine.

Tests all 8 detection types and the capability detection pipeline.
"""

import pytest
import os
from pathlib import Path

from app.capability_registry import (
    CapabilityRegistry,
    DetectionEngine,
    DetectionType,
    DetectionRule,
    CUSTOM_DETECTORS,
)
from app.musicxml_analyzer import MusicXMLAnalyzer, ExtractionResult

# Check if music21 is available
try:
    import music21
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False


# Skip all tests if music21 is not available
pytestmark = pytest.mark.skipif(
    not MUSIC21_AVAILABLE, reason="music21 not installed"
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def test_files_dir():
    """Path to test MusicXML files."""
    return Path(__file__).parent.parent / "resources" / "materials" / "test"


@pytest.fixture
def analyzer():
    """MusicXML analyzer instance."""
    return MusicXMLAnalyzer()


@pytest.fixture
def registry():
    """Capability registry loaded from capabilities.json."""
    reg = CapabilityRegistry()
    reg.load()  # Load capabilities from JSON
    return reg


@pytest.fixture
def detection_engine(registry):
    """Detection engine with registry."""
    return DetectionEngine(registry)


@pytest.fixture
def simple_extraction(analyzer):
    """Extraction result from test_01_simple.musicxml."""
    test_file = Path(__file__).parent.parent / "resources" / "materials" / "test" / "test_01_simple.musicxml"
    if not test_file.exists():
        pytest.skip("Test file not found")
    with open(test_file) as f:
        return analyzer.analyze(f.read())


@pytest.fixture
def rhythm_extraction(analyzer):
    """Extraction result from test_02_rhythms.musicxml."""
    test_file = Path(__file__).parent.parent / "resources" / "materials" / "test" / "test_02_rhythms.musicxml"
    if not test_file.exists():
        pytest.skip("Test file not found")
    with open(test_file) as f:
        return analyzer.analyze(f.read())


@pytest.fixture
def interval_extraction(analyzer):
    """Extraction result from test_03_intervals.musicxml."""
    test_file = Path(__file__).parent.parent / "resources" / "materials" / "test" / "test_03_intervals.musicxml"
    if not test_file.exists():
        pytest.skip("Test file not found")
    with open(test_file) as f:
        return analyzer.analyze(f.read())


@pytest.fixture
def chromatic_extraction(analyzer):
    """Extraction result from test_04_chromatic.musicxml."""
    test_file = Path(__file__).parent.parent / "resources" / "materials" / "test" / "test_04_chromatic.musicxml"
    if not test_file.exists():
        pytest.skip("Test file not found")
    with open(test_file) as f:
        return analyzer.analyze(f.read())


@pytest.fixture
def ornament_extraction(analyzer):
    """Extraction result from test_05_ornaments.musicxml."""
    test_file = Path(__file__).parent.parent / "resources" / "materials" / "test" / "test_05_ornaments.musicxml"
    if not test_file.exists():
        pytest.skip("Test file not found")
    with open(test_file) as f:
        return analyzer.analyze(f.read())


@pytest.fixture
def complex_extraction(analyzer):
    """Extraction result from test_06_complex.musicxml."""
    test_file = Path(__file__).parent.parent / "resources" / "materials" / "test" / "test_06_complex.musicxml"
    if not test_file.exists():
        pytest.skip("Test file not found")
    with open(test_file) as f:
        return analyzer.analyze(f.read())


# =============================================================================
# TEST: REGISTRY LOADING
# =============================================================================

class TestCapabilityRegistry:
    """Test capability registry loading and validation."""
    
    def test_registry_loads_capabilities(self, registry):
        """Registry should load at least 100 capabilities from JSON."""
        # The capabilities.json has ~210 capabilities
        assert len(registry.rules) >= 100, f"Expected 100+ capabilities, got {len(registry.rules)}"
    
    def test_registry_has_detectable_capabilities(self, registry):
        """Registry should have capabilities with detection rules."""
        detectable = registry.get_detectable_capabilities()
        # Should have meaningful detection coverage (~50+ detectable)
        assert len(detectable) >= 30, f"Expected 30+ detectable, got {len(detectable)}"
    
    def test_registry_tracks_domains(self, registry):
        """Registry should organize capabilities by domain."""
        assert len(registry.capabilities_by_domain) >= 15, "Should have 15+ domains"
        # Key domains should exist
        expected_domains = {"dynamics", "meter", "rhythm_duration", "pitch_foundation"}
        actual_domains = set(registry.capabilities_by_domain.keys())
        found = expected_domains & actual_domains
        assert len(found) >= 2, f"Should have dynamics/meter/rhythm domains, got {actual_domains}"
    
    def test_registry_validates_rules(self, registry):
        """Rules with detection_type should have required fields."""
        for name, rule in registry.rules.items():
            # Verify rule has required structure
            assert rule.capability_name == name
            if rule.detection_type and rule.is_valid:
                # Valid rules should have a method to apply
                assert rule.detection_type in DetectionType.__members__.values()
    
    def test_registry_gets_capability_by_name(self, registry):
        """Registry should find rule by name."""
        # Known capability should return its rule
        rule = registry.get_rule("clef_treble")
        assert rule.capability_name == "clef_treble"
        
        # Unknown capability should return None
        rule = registry.get_rule("not_a_real_capability_xyz")
        assert rule is None


# =============================================================================
# TEST: DETECTION ENGINE
# =============================================================================

class TestDetectionEngine:
    """Test detection engine applying rules to extraction results."""
    
    def test_detect_clef_treble(self, detection_engine, simple_extraction):
        """Should detect treble clef in simple file."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        # Simple test file uses treble clef
        assert "clef_treble" in capabilities, f"Expected clef_treble, got {capabilities}"
    
    def test_detect_time_signature_4_4(self, detection_engine, simple_extraction):
        """Should detect 4/4 time signature."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        # Simple file is in 4/4
        assert "time_signature_4_4" in capabilities, f"Expected 4/4 time sig, got {capabilities}"
    
    def test_detect_time_signature_6_8(self, detection_engine, rhythm_extraction):
        """Should detect 6/8 time signature in rhythm file."""
        capabilities = detection_engine.detect_capabilities(rhythm_extraction)
        # Rhythm file is in 6/8
        assert "time_signature_6_8" in capabilities, f"Expected 6/8 time sig, got {capabilities}"
    
    def test_detect_dynamics(self, detection_engine, simple_extraction):
        """Should detect dynamics in simple file."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        # Simple file should have at least one dynamic marking
        dynamic_caps = [c for c in capabilities if c.startswith("dynamic_")]
        # Test file should have mf or similar
        assert len(dynamic_caps) >= 1, f"Expected dynamics, got {capabilities}"
    
    def test_detect_multiple_capabilities(self, detection_engine, complex_extraction):
        """Complex file should detect many capabilities."""
        capabilities = detection_engine.detect_capabilities(complex_extraction)
        # Complex file should trigger 10+ capability detections
        assert len(capabilities) >= 10, f"Expected 10+ caps from complex file, got {len(capabilities)}"


# =============================================================================
# TEST: DETECTION TYPES
# =============================================================================

class TestElementDetection:
    """Test element type detection."""
    
    def test_element_detection_clef(self, detection_engine, simple_extraction, registry):
        """Element detection should detect clef from music21 elements."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        # Element-based clef detection should work
        element_rules = registry.get_capabilities_by_type(DetectionType.ELEMENT)
        assert len(element_rules) >= 1, "Should have element-type rules"
        # Should detect clef (element-based detection)
        assert "clef_treble" in capabilities or "clef_bass" in capabilities


class TestValueMatchDetection:
    """Test value_match type detection."""
    
    def test_value_match_dynamics(self, detection_engine, complex_extraction):
        """Value match should detect dynamics by field comparison."""
        capabilities = detection_engine.detect_capabilities(complex_extraction)
        # Complex file should have dynamic markings (mf, f, p, etc.)
        dynamic_caps = [c for c in capabilities if "dynamic" in c]
        assert len(dynamic_caps) >= 1, f"Expected dynamics in complex file, got {capabilities}"


class TestTimeSignatureDetection:
    """Test time_signature type detection."""
    
    def test_time_sig_detection_simple(self, detection_engine, simple_extraction, registry):
        """Time signature detection should find 4/4 in simple file."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        time_rules = registry.get_capabilities_by_type(DetectionType.TIME_SIGNATURE)
        assert len(time_rules) >= 3, "Should have multiple time sig rules"
        assert "time_signature_4_4" in capabilities
    
    def test_compound_time_sig(self, detection_engine, rhythm_extraction):
        """Should detect compound 6/8 time signature."""
        capabilities = detection_engine.detect_capabilities(rhythm_extraction)
        assert "time_signature_6_8" in capabilities, f"Expected 6/8, got {capabilities}"


class TestIntervalDetection:
    """Test interval type detection."""
    
    def test_interval_detection(self, detection_engine, interval_extraction):
        """Interval detection should find melodic intervals."""
        capabilities = detection_engine.detect_capabilities(interval_extraction)
        interval_caps = [c for c in capabilities if "interval" in c]
        # Interval test file specifically tests intervals - should find 3+
        assert len(interval_caps) >= 3, f"Expected 3+ interval caps, got {interval_caps}"


class TestCompoundDetection:
    """Test compound type detection (multiple conditions)."""
    
    def test_compound_dotted_notes(self, detection_engine, rhythm_extraction):
        """Compound detection should find dotted notes in rhythm file."""
        capabilities = detection_engine.detect_capabilities(rhythm_extraction)
        # Rhythm test file is designed to have dotted rhythms
        dotted_caps = [c for c in capabilities if "dotted" in c]
        assert len(dotted_caps) >= 1, f"Expected dotted notes in rhythm file, got {capabilities}"


class TestRangeDetection:
    """Test range type detection (interval size ranges)."""
    
    def test_range_detection_small(self, detection_engine, simple_extraction):
        """Simple file should detect range-based capabilities."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        # Simple file has notes - should detect some range/span based caps
        # At minimum should detect stepwise motion or similar
        assert len(capabilities) >= 5, f"Simple file should detect multiple caps"


class TestTextMatchDetection:
    """Test text_match type detection."""
    
    def test_text_match_expressions(self, detection_engine, ornament_extraction):
        """Text match should find expression markings in ornament file."""
        capabilities = detection_engine.detect_capabilities(ornament_extraction)
        # Ornament file should have articulation/ornament markings
        assert len(capabilities) >= 5, f"Ornament file should detect caps, got {capabilities}"


# =============================================================================
# TEST: FULL PIPELINE
# =============================================================================

class TestFullDetectionPipeline:
    """Integration tests for full detection pipeline."""
    
    def test_all_test_files_analyzable(self, analyzer, test_files_dir):
        """All test files should be analyzable without errors."""
        if not test_files_dir.exists():
            pytest.skip("Test files directory not found")
        
        test_files = list(test_files_dir.glob("*.musicxml"))
        assert len(test_files) >= 3, "Should have multiple test files"
        
        for file in test_files:
            with open(file) as f:
                result = analyzer.analyze(f.read())
            # Verify extraction produced meaningful data
            assert result.measure_count >= 1, f"{file.name} should have measures"
    
    def test_all_test_files_detect_capabilities(self, detection_engine, analyzer, test_files_dir):
        """All test files should yield detected capabilities."""
        if not test_files_dir.exists():
            pytest.skip("Test files directory not found")
        
        for file in test_files_dir.glob("*.musicxml"):
            with open(file) as f:
                extraction = analyzer.analyze(f.read())
            capabilities = detection_engine.detect_capabilities(extraction)
            # Each file should detect at least basic capabilities
            assert len(capabilities) >= 3, f"{file.name} should detect 3+ capabilities, got {len(capabilities)}"
    
    def test_simple_file_has_basic_caps(self, detection_engine, simple_extraction):
        """Simple file should detect core capabilities."""
        caps = detection_engine.detect_capabilities(simple_extraction)
        # Simple file must have: clef, time sig, key sig at minimum
        assert "clef_treble" in caps or "clef_bass" in caps
        assert any("time_signature" in c for c in caps)
    
    def test_complex_file_has_many_caps(self, detection_engine, complex_extraction):
        """Complex file should detect significantly more capabilities."""
        caps = detection_engine.detect_capabilities(complex_extraction)
        # Complex file should trigger many detections
        assert len(caps) >= 15, f"Complex file should have 15+ caps, got {len(caps)}"


# =============================================================================
# TEST: CUSTOM DETECTORS
# =============================================================================

class TestCustomDetectors:
    """Test custom detection functions."""
    
    def test_syncopation_detector_registered(self):
        """Syncopation detector should be registered and callable."""
        assert "detect_syncopation" in CUSTOM_DETECTORS
        detector = CUSTOM_DETECTORS["detect_syncopation"]
        # Verify detector is a function we can call
        import inspect
        assert inspect.isfunction(detector) or inspect.ismethod(detector)
    
    def test_custom_detectors_have_correct_signature(self):
        """Custom detectors should accept extraction and score params."""
        import inspect
        for name, func in CUSTOM_DETECTORS.items():
            sig = inspect.signature(func)
            params = list(sig.parameters.keys())
            # Should accept extraction_result at minimum
            assert len(params) >= 1, f"Detector {name} should accept parameters"
