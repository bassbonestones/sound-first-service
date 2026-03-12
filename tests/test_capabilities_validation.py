"""
Tests for capability detection rule validation.

Tests validation of detection rules from capabilities.json.
"""

import pytest
from app.capabilities.validation import validate_detection_rule
from app.capabilities.types import DetectionType


class TestValidateDetectionRule:
    """Test validate_detection_rule function."""
    
    def test_none_rule_is_valid(self):
        """None rule config should be valid (not auto-detectable)."""
        result = validate_detection_rule("test_cap", None)
        assert result.is_valid is True
        assert result.detection_type is None
    
    def test_missing_type_is_invalid(self):
        """Missing type field should be invalid."""
        result = validate_detection_rule("test_cap", {"source": "analysis"})
        assert result.is_valid is False
        assert "Missing 'type' field" in result.validation_errors
    
    def test_unknown_type_is_invalid(self):
        """Unknown type should be invalid."""
        result = validate_detection_rule("test_cap", {"type": "unknown_type"})
        assert result.is_valid is False
        assert any("Unknown detection type" in e for e in result.validation_errors)


class TestElementRuleValidation:
    """Test element type validation."""
    
    def test_valid_element_rule(self):
        """Valid element rule with class field."""
        result = validate_detection_rule("test_cap", {
            "type": "element",
            "class": "Articulation"
        })
        assert result.is_valid is True
        assert result.detection_type == DetectionType.ELEMENT
    
    def test_element_missing_class(self):
        """Element rule missing class should be invalid."""
        result = validate_detection_rule("test_cap", {"type": "element"})
        assert result.is_valid is False
        assert any("'class' field" in e for e in result.validation_errors)


class TestValueMatchRuleValidation:
    """Test value_match type validation."""
    
    def test_valid_value_match_rule(self):
        """Valid value_match rule."""
        result = validate_detection_rule("test_cap", {
            "type": "value_match",
            "source": "intervals",
            "field": "interval_size_stage",
            "gte": 3
        })
        assert result.is_valid is True
        assert result.detection_type == DetectionType.VALUE_MATCH
    
    def test_value_match_missing_source(self):
        """Value match missing source should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "value_match",
            "field": "some_field",
            "eq": 1
        })
        assert result.is_valid is False
        assert any("'source' field" in e for e in result.validation_errors)
    
    def test_value_match_missing_field(self):
        """Value match missing field should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "value_match",
            "source": "intervals",
            "eq": 1
        })
        assert result.is_valid is False
        assert any("'field' field" in e for e in result.validation_errors)
    
    def test_value_match_missing_comparator(self):
        """Value match missing comparator should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "value_match",
            "source": "intervals",
            "field": "some_field"
        })
        assert result.is_valid is False
        assert any("eq, contains, gte, lte" in e for e in result.validation_errors)
    
    def test_value_match_with_different_comparators(self):
        """Value match should accept different comparators."""
        for comparator in ["eq", "contains", "gte", "lte"]:
            result = validate_detection_rule("test_cap", {
                "type": "value_match",
                "source": "intervals",
                "field": "test_field",
                comparator: 1
            })
            assert result.is_valid is True, f"Failed for {comparator}"
    
    def test_value_match_invalid_source(self):
        """Value match with invalid source should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "value_match",
            "source": "invalid_source",
            "field": "test",
            "eq": 1
        })
        assert result.is_valid is False
        assert any("Invalid source" in e for e in result.validation_errors)


class TestCompoundRuleValidation:
    """Test compound type validation."""
    
    def test_valid_compound_rule(self):
        """Valid compound rule."""
        result = validate_detection_rule("test_cap", {
            "type": "compound",
            "source": "notes",
            "conditions": [{"field": "x", "gte": 1}]
        })
        assert result.is_valid is True
        assert result.detection_type == DetectionType.COMPOUND
    
    def test_compound_missing_source(self):
        """Compound missing source should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "compound",
            "conditions": []
        })
        assert result.is_valid is False
        assert any("'source' field" in e for e in result.validation_errors)
    
    def test_compound_missing_conditions(self):
        """Compound missing conditions should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "compound",
            "source": "notes"
        })
        assert result.is_valid is False
        assert any("'conditions' array" in e for e in result.validation_errors)
    
    def test_compound_invalid_source(self):
        """Compound with invalid source should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "compound",
            "source": "invalid_source",
            "conditions": []
        })
        assert result.is_valid is False
        assert any("Invalid source" in e for e in result.validation_errors)


class TestIntervalRuleValidation:
    """Test interval type validation."""
    
    def test_valid_interval_rule(self):
        """Valid interval rule with quality."""
        result = validate_detection_rule("test_cap", {
            "type": "interval",
            "quality": "M3"
        })
        assert result.is_valid is True
        assert result.detection_type == DetectionType.INTERVAL
    
    def test_interval_missing_quality(self):
        """Interval missing quality should be invalid."""
        result = validate_detection_rule("test_cap", {"type": "interval"})
        assert result.is_valid is False
        assert any("'quality' field" in e for e in result.validation_errors)


class TestTextMatchRuleValidation:
    """Test text_match type validation."""
    
    def test_valid_text_match_with_contains(self):
        """Valid text_match with contains."""
        result = validate_detection_rule("test_cap", {
            "type": "text_match",
            "source": "title",
            "contains": "jazz"
        })
        assert result.is_valid is True
        assert result.detection_type == DetectionType.TEXT_MATCH
    
    def test_valid_text_match_with_equals(self):
        """Valid text_match with equals."""
        result = validate_detection_rule("test_cap", {
            "type": "text_match",
            "source": "title",
            "equals": "test"
        })
        assert result.is_valid is True
    
    def test_text_match_missing_source(self):
        """Text match missing source should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "text_match",
            "contains": "test"
        })
        assert result.is_valid is False
        assert any("'source' field" in e for e in result.validation_errors)
    
    def test_text_match_missing_matcher(self):
        """Text match missing contains/equals should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "text_match",
            "source": "title"
        })
        assert result.is_valid is False
        assert any("'contains' or 'equals'" in e for e in result.validation_errors)


class TestTimeSignatureRuleValidation:
    """Test time_signature type validation."""
    
    def test_valid_time_signature_rule(self):
        """Valid time_signature rule."""
        result = validate_detection_rule("test_cap", {
            "type": "time_signature",
            "numerator": 3,
            "denominator": 4
        })
        assert result.is_valid is True
        assert result.detection_type == DetectionType.TIME_SIGNATURE
    
    def test_time_signature_missing_numerator(self):
        """Time signature missing numerator should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "time_signature",
            "denominator": 4
        })
        assert result.is_valid is False
        assert any("'numerator' field" in e for e in result.validation_errors)
    
    def test_time_signature_missing_denominator(self):
        """Time signature missing denominator should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "time_signature",
            "numerator": 3
        })
        assert result.is_valid is False
        assert any("'denominator' field" in e for e in result.validation_errors)


class TestRangeRuleValidation:
    """Test range type validation."""
    
    def test_valid_range_with_min(self):
        """Valid range rule with min_semitones."""
        result = validate_detection_rule("test_cap", {
            "type": "range",
            "min_semitones": 12
        })
        assert result.is_valid is True
        assert result.detection_type == DetectionType.RANGE
    
    def test_valid_range_with_max(self):
        """Valid range rule with max_semitones."""
        result = validate_detection_rule("test_cap", {
            "type": "range",
            "max_semitones": 24
        })
        assert result.is_valid is True
    
    def test_valid_range_with_both(self):
        """Valid range with both min and max."""
        result = validate_detection_rule("test_cap", {
            "type": "range",
            "min_semitones": 12,
            "max_semitones": 24
        })
        assert result.is_valid is True
    
    def test_range_missing_both(self):
        """Range missing both min and max should be invalid."""
        result = validate_detection_rule("test_cap", {"type": "range"})
        assert result.is_valid is False
        assert any("min_semitones, max_semitones" in e for e in result.validation_errors)


class TestCustomRuleValidation:
    """Test custom type validation."""
    
    def test_custom_missing_function(self):
        """Custom missing function should be invalid."""
        result = validate_detection_rule("test_cap", {"type": "custom"})
        assert result.is_valid is False
        assert any("'function' field" in e for e in result.validation_errors)
    
    def test_custom_unknown_function(self):
        """Custom with unknown function should be invalid."""
        result = validate_detection_rule("test_cap", {
            "type": "custom",
            "function": "nonexistent_function"
        })
        assert result.is_valid is False
        assert any("Unknown custom function" in e for e in result.validation_errors)
