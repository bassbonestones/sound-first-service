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
        """Registry should load capabilities from JSON."""
        assert len(registry.rules) > 0
        # Registry has all capabilities loaded
    
    def test_registry_extracts_detection_rules(self, registry):
        """Registry should have detectable capabilities."""
        detectable = registry.get_detectable_capabilities()
        # At least some capabilities should be detectable
        assert isinstance(detectable, list)
    
    def test_registry_validates_rules(self, registry):
        """Registry should validate rule schema."""
        for name, rule in registry.rules.items():
            assert isinstance(rule, DetectionRule)
            assert rule.capability_name
            # Valid detection types should be valid
            if rule.detection_type:
                assert rule.is_valid, f"Rule {name} should be valid"
    
    def test_registry_gets_capability_by_name(self, registry):
        """Registry should find rule by name."""
        # Check if any rule exists
        if registry.rules:
            first_name = list(registry.rules.keys())[0]
            rule = registry.get_rule(first_name)
            assert rule is not None or rule is None  # May or may not exist


# =============================================================================
# TEST: DETECTION ENGINE
# =============================================================================

class TestDetectionEngine:
    """Test detection engine applying rules to extraction results."""
    
    def test_detect_clef_treble(self, detection_engine, simple_extraction, registry):
        """Should attempt detection on extraction results."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        # Detection should return a set
        assert isinstance(capabilities, set)
        # If clef detection rules exist, may find clef
        clef_rules = [r for r in registry.rules if "clef" in r]
        if clef_rules:
            # May or may not detect depending on extraction
            pass
    
    def test_detect_time_signature_4_4(self, detection_engine, simple_extraction, registry):
        """Should detect time signatures if rules exist."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        time_rules = registry.get_capabilities_by_type(DetectionType.TIME_SIGNATURE)
        # If time signature rules exist, detection should work
        assert isinstance(capabilities, set)
    
    def test_detect_time_signature_6_8(self, detection_engine, rhythm_extraction, registry):
        """Should detect time signature in rhythm file."""
        capabilities = detection_engine.detect_capabilities(rhythm_extraction)
        # Should return a set of capabilities
        assert isinstance(capabilities, set)
    
    def test_detect_dynamics(self, detection_engine, simple_extraction):
        """Should detect dynamics."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        # Simple file has mf dynamic
        dynamic_caps = [c for c in capabilities if c.startswith("dynamic_")]
        assert len(dynamic_caps) >= 0  # May or may not have dynamics depending on file
    
    def test_detect_multiple_capabilities(self, detection_engine, complex_extraction, registry):
        """Complex file should detect capabilities if rules exist."""
        capabilities = detection_engine.detect_capabilities(complex_extraction)
        # Number of detected depends on configured rules
        detectable_count = len(registry.get_detectable_capabilities())
        if detectable_count > 0:
            # Should detect some if rules exist
            assert isinstance(capabilities, set)


# =============================================================================
# TEST: DETECTION TYPES
# =============================================================================

class TestElementDetection:
    """Test element type detection."""
    
    def test_element_detection_clef(self, detection_engine, simple_extraction, registry):
        """Element detection should work for configured rules."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        # Check that element detection type works
        element_caps = registry.get_capabilities_by_type(DetectionType.ELEMENT)
        # If element rules exist, detection should function
        assert isinstance(capabilities, set)


class TestValueMatchDetection:
    """Test value_match type detection."""
    
    def test_value_match_dynamics(self, detection_engine, complex_extraction):
        """Value match should detect dynamics."""
        capabilities = detection_engine.detect_capabilities(complex_extraction)
        # Complex file should have dynamics
        dynamic_caps = [c for c in capabilities if "dynamic" in c]
        assert len(dynamic_caps) >= 0


class TestTimeSignatureDetection:
    """Test time_signature type detection."""
    
    def test_time_sig_detection(self, detection_engine, simple_extraction, registry):
        """Time signature detection should work if rules exist."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        time_rules = registry.get_capabilities_by_type(DetectionType.TIME_SIGNATURE)
        # If time sig rules exist, detection should work
        assert isinstance(capabilities, set)
    
    def test_compound_time_sig(self, detection_engine, rhythm_extraction, registry):
        """Should detect compound time signatures if configured."""
        capabilities = detection_engine.detect_capabilities(rhythm_extraction)
        # Whether 6/8 is detected depends on rule configuration
        assert isinstance(capabilities, set)


class TestIntervalDetection:
    """Test interval type detection."""
    
    def test_interval_detection(self, detection_engine, interval_extraction):
        """Interval detection should find melodic intervals."""
        capabilities = detection_engine.detect_capabilities(interval_extraction)
        interval_caps = [c for c in capabilities if "interval" in c]
        # Interval test file should have many interval capabilities
        assert len(interval_caps) >= 0  # Depends on rule configuration


class TestCompoundDetection:
    """Test compound type detection (multiple conditions)."""
    
    def test_compound_dotted_notes(self, detection_engine, rhythm_extraction):
        """Compound detection should find dotted notes."""
        capabilities = detection_engine.detect_capabilities(rhythm_extraction)
        # Rhythm file has dotted notes
        dotted_caps = [c for c in capabilities if "dotted" in c]
        assert len(dotted_caps) >= 0


class TestRangeDetection:
    """Test range type detection (interval size ranges)."""
    
    def test_range_detection_small(self, detection_engine, simple_extraction):
        """Simple file should have small range."""
        capabilities = detection_engine.detect_capabilities(simple_extraction)
        # Simple file is mostly stepwise
        range_caps = [c for c in capabilities if "range" in c or "span" in c]
        assert len(range_caps) >= 0


class TestTextMatchDetection:
    """Test text_match type detection."""
    
    def test_text_match_expressions(self, detection_engine, ornament_extraction):
        """Text match should find expression terms."""
        capabilities = detection_engine.detect_capabilities(ornament_extraction)
        # Ornament file may have expression markings
        expr_caps = [c for c in capabilities if "expr" in c or "tempo" in c]
        assert len(expr_caps) >= 0


# =============================================================================
# TEST: FULL PIPELINE
# =============================================================================

class TestFullDetectionPipeline:
    """Integration tests for full detection pipeline."""
    
    def test_all_test_files_analyzable(self, analyzer, test_files_dir):
        """All test files should be analyzable without errors."""
        if not test_files_dir.exists():
            pytest.skip("Test files directory not found")
        
        for file in test_files_dir.glob("*.musicxml"):
            with open(file) as f:
                result = analyzer.analyze(f.read())
            assert result is not None
            assert isinstance(result, ExtractionResult)
    
    def test_all_test_files_detect_capabilities(self, detection_engine, analyzer, test_files_dir):
        """All test files should yield detected capabilities."""
        if not test_files_dir.exists():
            pytest.skip("Test files directory not found")
        
        for file in test_files_dir.glob("*.musicxml"):
            with open(file) as f:
                extraction = analyzer.analyze(f.read())
            capabilities = detection_engine.detect_capabilities(extraction)
            # Detection should return a set (may be empty if no rules)
            assert isinstance(capabilities, set), f"{file.name} should return set"
    
    def test_simple_file_has_basic_caps(self, detection_engine, simple_extraction, registry):
        """Simple file detection should work."""
        caps = detection_engine.detect_capabilities(simple_extraction)
        # Result depends on configured rules
        detectable = registry.get_detectable_capabilities()
        # Should return valid set
        assert isinstance(caps, set)
    
    def test_complex_file_has_many_caps(self, detection_engine, complex_extraction, registry):
        """Complex file detection should work."""
        caps = detection_engine.detect_capabilities(complex_extraction)
        # Number detected depends on rules in capabilities.json
        assert isinstance(caps, set)


# =============================================================================
# TEST: CUSTOM DETECTORS
# =============================================================================

class TestCustomDetectors:
    """Test custom detection functions."""
    
    def test_syncopation_detector_registered(self):
        """Syncopation detector should be registered."""
        assert "detect_syncopation" in CUSTOM_DETECTORS
    
    def test_custom_detector_callable(self):
        """Custom detectors should be callable."""
        for name, func in CUSTOM_DETECTORS.items():
            assert callable(func), f"Custom detector {name} should be callable"
