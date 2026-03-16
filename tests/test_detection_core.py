"""
Tests for capabilities/detection/core.py

Tests for the DetectionEngine class.
"""

import pytest
from dataclasses import dataclass, field
from typing import Dict, Set, Any, Optional

from app.capabilities.types import DetectionRule, DetectionType
from app.capabilities.detection.core import DetectionEngine


@dataclass
class MockExtractionResult:
    """Mock extraction result for testing."""
    clefs: Set[str] = field(default_factory=set)
    time_signatures: Set[str] = field(default_factory=set)
    key_signatures: Set[str] = field(default_factory=set)
    note_values: Dict[str, int] = field(default_factory=dict)
    dotted_notes: Set[str] = field(default_factory=set)
    rest_values: Dict[str, int] = field(default_factory=dict)
    dynamics: Set[str] = field(default_factory=set)
    articulations: Set[str] = field(default_factory=set)
    ornaments: Set[str] = field(default_factory=set)
    tempo_markings: Set[str] = field(default_factory=set)
    expression_terms: Set[str] = field(default_factory=set)
    melodic_intervals: Dict[str, Any] = field(default_factory=dict)
    harmonic_intervals: Dict[str, Any] = field(default_factory=dict)
    fermatas: int = 0
    breath_marks: int = 0
    has_ties: bool = False
    max_voices: int = 1
    range_analysis: Optional[Any] = None


class MockRegistry:
    """Mock capability registry for testing."""
    
    def __init__(self, rules: Dict[str, DetectionRule] = None):
        self.rules = rules or {}


class TestDetectionEngineInit:
    """Tests for DetectionEngine initialization."""

    def test_can_instantiate(self):
        """Should create DetectionEngine with registry."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        assert engine is not None
        assert engine.registry == registry

    def test_stores_registry(self):
        """Should store the registry reference."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        assert engine.registry is registry


class TestDetectCapabilities:
    """Tests for detect_capabilities method."""

    def test_empty_registry_returns_empty(self):
        """Empty registry should return empty set."""
        registry = MockRegistry(rules={})
        engine = DetectionEngine(registry)
        result = MockExtractionResult()
        
        detected = engine.detect_capabilities(result)
        
        assert detected == set()

    def test_skips_invalid_rules(self):
        """Should skip invalid rules."""
        registry = MockRegistry(rules={
            "invalid_cap": DetectionRule(
                capability_name="invalid_cap",
                detection_type=DetectionType.ELEMENT,
                config={},
                is_valid=False,
            )
        })
        engine = DetectionEngine(registry)
        result = MockExtractionResult()
        
        detected = engine.detect_capabilities(result)
        
        assert "invalid_cap" not in detected

    def test_skips_none_detection_type(self):
        """Should skip rules with None detection_type."""
        registry = MockRegistry(rules={
            "none_type": DetectionRule(
                capability_name="none_type",
                detection_type=None,
                config={},
                is_valid=True,
            )
        })
        engine = DetectionEngine(registry)
        result = MockExtractionResult()
        
        detected = engine.detect_capabilities(result)
        
        assert "none_type" not in detected

    def test_element_detection(self):
        """Should detect ELEMENT type rules."""
        registry = MockRegistry(rules={
            "clef_treble": DetectionRule(
                capability_name="clef_treble",
                detection_type=DetectionType.ELEMENT,
                config={"class": "music21.clef.TrebleClef"},
                is_valid=True,
            )
        })
        engine = DetectionEngine(registry)
        result = MockExtractionResult()
        result.clefs = {"clef_treble"}
        
        detected = engine.detect_capabilities(result)
        
        assert "clef_treble" in detected

    def test_returns_set(self):
        """Should return a set of capability names."""
        registry = MockRegistry(rules={})
        engine = DetectionEngine(registry)
        result = MockExtractionResult()
        
        detected = engine.detect_capabilities(result)
        
        assert isinstance(detected, set)


class TestCheckRule:
    """Tests for _check_rule method."""

    def test_element_rule_type(self):
        """Should handle ELEMENT detection type."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        rule = DetectionRule(
            capability_name="test",
            detection_type=DetectionType.ELEMENT,
            config={"class": "music21.clef.BassClef"},
            is_valid=True,
        )
        
        result = MockExtractionResult()
        result.clefs = {"clef_bass"}
        
        assert engine._check_rule(rule, result, None) is True

    def test_value_match_rule_type(self):
        """Should handle VALUE_MATCH detection type."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        rule = DetectionRule(
            capability_name="test",
            detection_type=DetectionType.VALUE_MATCH,
            config={"source": "dynamics", "field": "value", "eq": "f"},
            is_valid=True,
        )
        
        result = MockExtractionResult()
        result.dynamics = {"dynamic_f"}
        
        assert engine._check_rule(rule, result, None) is True

    def test_unknown_detection_type_returns_false(self):
        """Unknown detection type should return False."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        # Create a rule with a detection type we don't handle
        rule = DetectionRule(
            capability_name="test",
            detection_type=DetectionType.CUSTOM,
            config={"detector": "nonexistent"},
            is_valid=True,
        )
        
        result = MockExtractionResult()
        
        # CUSTOM without valid detector should return False
        assert engine._check_rule(rule, result, None) is False


class TestValueMatch:
    """Tests for _check_value_match method."""

    def test_matches_dynamics(self):
        """Should match dynamics values."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        config = {"source": "dynamics", "field": "value", "eq": "ff"}
        result = MockExtractionResult()
        result.dynamics = {"dynamic_ff", "dynamic_p"}
        
        assert engine._check_value_match(config, result) is True

    def test_no_match_missing_value(self):
        """Should not match when value is missing."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        config = {"source": "dynamics", "field": "value", "eq": "fff"}
        result = MockExtractionResult()
        result.dynamics = {"dynamic_f", "dynamic_p"}
        
        assert engine._check_value_match(config, result) is False

    def test_empty_source_returns_false(self):
        """Empty source data should return False."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        config = {"source": "dynamics", "field": "value", "eq": "f"}
        result = MockExtractionResult()
        result.dynamics = set()
        
        assert engine._check_value_match(config, result) is False


class TestCompound:
    """Tests for _check_compound method."""

    def test_compound_all_conditions_match(self):
        """Should match when all conditions pass."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        # Config that checks for dotted notes
        config = {
            "source": "notes",
            "conditions": [
                {"field": "dots", "gte": 1}
            ]
        }
        
        result = MockExtractionResult()
        result.note_values = {}
        result.dotted_notes = {"dotted_half"}
        
        assert engine._check_compound(config, result) is True

    def test_compound_one_condition_fails(self):
        """Should not match if any condition fails."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        config = {
            "source": "notes",
            "conditions": [
                {"field": "type", "eq": "quarter"},
                {"field": "dots", "gte": 1}  # No dotted quarters
            ]
        }
        
        result = MockExtractionResult()
        result.note_values = {"note_quarter": 5}
        result.dotted_notes = set()
        
        assert engine._check_compound(config, result) is False


class TestInterval:
    """Tests for _check_interval method."""

    def test_matches_melodic_interval(self):
        """Should match melodic intervals."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        config = {"quality": "M3", "melodic": True}
        
        result = MockExtractionResult()
        
        # Need to create mock IntervalInfo
        @dataclass
        class MockIntervalInfo:
            name: str
            direction: str
        
        result.melodic_intervals = {
            "M3_asc": MockIntervalInfo(name="M3", direction="ascending")
        }
        
        assert engine._check_interval(config, result) is True

    def test_no_match_wrong_interval(self):
        """Should not match wrong interval quality."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        config = {"quality": "P5", "melodic": True}
        
        result = MockExtractionResult()
        
        @dataclass
        class MockIntervalInfo:
            name: str
            direction: str
        
        result.melodic_intervals = {
            "M3_asc": MockIntervalInfo(name="M3", direction="ascending")
        }
        
        assert engine._check_interval(config, result) is False


class TestTimeSignature:
    """Tests for _check_time_signature method."""

    def test_matches_time_signature(self):
        """Should match time signatures."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        config = {"numerator": 4, "denominator": 4}
        result = MockExtractionResult()
        result.time_signatures = {"time_sig_4_4", "time_sig_3_4"}
        
        assert engine._check_time_signature(config, result) is True

    def test_no_match_missing_time_sig(self):
        """Should not match missing time signature."""
        registry = MockRegistry()
        engine = DetectionEngine(registry)
        
        config = {"numerator": 6, "denominator": 8}
        result = MockExtractionResult()
        result.time_signatures = {"time_sig_4_4"}
        
        assert engine._check_time_signature(config, result) is False
