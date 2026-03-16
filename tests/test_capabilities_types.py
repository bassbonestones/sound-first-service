"""
Tests for capabilities/types.py

Tests for capability detection types and dataclasses.
"""

import pytest
from enum import Enum

from app.capabilities.types import (
    DetectionType,
    DetectionRule,
    VALID_SOURCES,
)


class TestDetectionType:
    """Tests for DetectionType enum."""

    def test_is_enum(self):
        """Should be an enum."""
        assert issubclass(DetectionType, Enum)

    def test_is_string_enum(self):
        """Should be a string enum."""
        assert issubclass(DetectionType, str)

    def test_element_type(self):
        """Should have ELEMENT type."""
        assert DetectionType.ELEMENT is not None
        assert DetectionType.ELEMENT.value == "element"

    def test_value_match_type(self):
        """Should have VALUE_MATCH type."""
        assert DetectionType.VALUE_MATCH is not None
        assert DetectionType.VALUE_MATCH.value == "value_match"

    def test_compound_type(self):
        """Should have COMPOUND type."""
        assert DetectionType.COMPOUND is not None
        assert DetectionType.COMPOUND.value == "compound"

    def test_interval_type(self):
        """Should have INTERVAL type."""
        assert DetectionType.INTERVAL is not None
        assert DetectionType.INTERVAL.value == "interval"

    def test_text_match_type(self):
        """Should have TEXT_MATCH type."""
        assert DetectionType.TEXT_MATCH is not None
        assert DetectionType.TEXT_MATCH.value == "text_match"

    def test_time_signature_type(self):
        """Should have TIME_SIGNATURE type."""
        assert DetectionType.TIME_SIGNATURE is not None
        assert DetectionType.TIME_SIGNATURE.value == "time_signature"

    def test_range_type(self):
        """Should have RANGE type."""
        assert DetectionType.RANGE is not None
        assert DetectionType.RANGE.value == "range"

    def test_custom_type(self):
        """Should have CUSTOM type."""
        assert DetectionType.CUSTOM is not None
        assert DetectionType.CUSTOM.value == "custom"

    def test_string_comparison(self):
        """Should compare equal to string value."""
        assert DetectionType.ELEMENT == "element"
        assert DetectionType.COMPOUND == "compound"

    def test_iteration(self):
        """Should be iterable."""
        types = list(DetectionType)
        assert len(types) >= 8


class TestDetectionRule:
    """Tests for DetectionRule dataclass."""

    def test_create_basic(self):
        """Should create basic rule."""
        rule = DetectionRule(
            capability_name="note_quarter",
            detection_type=DetectionType.ELEMENT,
            config={"element": "note", "duration": "quarter"},
        )
        
        assert rule.capability_name == "note_quarter"
        assert rule.detection_type == DetectionType.ELEMENT
        assert rule.config["element"] == "note"

    def test_defaults(self):
        """Should have sensible defaults."""
        rule = DetectionRule(
            capability_name="test_cap",
            detection_type=DetectionType.VALUE_MATCH,
            config={},
        )
        
        assert rule.is_valid is True
        assert rule.validation_errors == []

    def test_invalid_rule(self):
        """Should allow marking rule as invalid."""
        rule = DetectionRule(
            capability_name="bad_cap",
            detection_type=None,
            config={},
            is_valid=False,
            validation_errors=["Missing detection_type"],
        )
        
        assert rule.is_valid is False
        assert len(rule.validation_errors) == 1

    def test_validation_errors_list(self):
        """Should store multiple validation errors."""
        rule = DetectionRule(
            capability_name="bad_cap",
            detection_type=DetectionType.VALUE_MATCH,
            config={},
            is_valid=False,
            validation_errors=["Error 1", "Error 2", "Error 3"],
        )
        
        assert len(rule.validation_errors) == 3

    def test_none_detection_type(self):
        """Should allow None detection type."""
        rule = DetectionRule(
            capability_name="unknown",
            detection_type=None,
            config={"something": "custom"},
        )
        
        assert rule.detection_type is None

    def test_complex_config(self):
        """Should handle complex config dictionaries."""
        config = {
            "source": "notes",
            "match": {"type": "quarter", "dots": 1},
            "conditions": ["in_key", "not_rest"],
            "threshold": 0.5,
        }
        rule = DetectionRule(
            capability_name="dotted_quarter",
            detection_type=DetectionType.COMPOUND,
            config=config,
        )
        
        assert rule.config["match"]["type"] == "quarter"
        assert rule.config["threshold"] == 0.5


class TestValidSources:
    """Tests for VALID_SOURCES constant."""

    def test_is_set(self):
        """Should be a set."""
        assert isinstance(VALID_SOURCES, set)

    def test_contains_notes(self):
        """Should contain 'notes' source."""
        assert "notes" in VALID_SOURCES

    def test_contains_dynamics(self):
        """Should contain 'dynamics' source."""
        assert "dynamics" in VALID_SOURCES

    def test_contains_intervals(self):
        """Should contain 'intervals' source."""
        assert "intervals" in VALID_SOURCES

    def test_contains_time_signatures(self):
        """Should contain 'time_signatures' source."""
        assert "time_signatures" in VALID_SOURCES

    def test_contains_articulations(self):
        """Should contain 'articulations' source."""
        assert "articulations" in VALID_SOURCES

    def test_contains_clefs(self):
        """Should contain 'clefs' source."""
        assert "clefs" in VALID_SOURCES

    def test_contains_ornaments(self):
        """Should contain 'ornaments' source."""
        assert "ornaments" in VALID_SOURCES

    def test_contains_rests(self):
        """Should contain 'rests' source."""
        assert "rests" in VALID_SOURCES

    def test_all_strings(self):
        """All sources should be strings."""
        assert all(isinstance(s, str) for s in VALID_SOURCES)

    def test_all_lowercase(self):
        """All sources should be lowercase."""
        assert all(s == s.lower() for s in VALID_SOURCES)

    def test_reasonable_count(self):
        """Should have reasonable number of sources."""
        assert len(VALID_SOURCES) >= 8
        assert len(VALID_SOURCES) <= 50  # Not too many
