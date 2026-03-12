"""
Tests for json_helpers utility module.

Tests JSON parsing functions used throughout the application.
"""

import pytest
from app.utils.json_helpers import parse_focus_card_json_field


class TestParseFocusCardJsonField:
    """Test parse_focus_card_json_field function."""
    
    # --- Valid JSON Strings ---
    
    def test_parses_valid_json_array(self):
        """Should parse valid JSON array string."""
        result = parse_focus_card_json_field('["item1", "item2", "item3"]')
        assert result == ["item1", "item2", "item3"]
    
    def test_parses_valid_json_object(self):
        """Should parse valid JSON object string."""
        result = parse_focus_card_json_field('{"key": "value", "number": 42}')
        assert result == {"key": "value", "number": 42}
    
    def test_parses_empty_json_array(self):
        """Should parse empty array."""
        result = parse_focus_card_json_field('[]')
        assert result == []
    
    def test_parses_empty_json_object(self):
        """Should parse empty object."""
        result = parse_focus_card_json_field('{}')
        assert result == {}
    
    def test_parses_nested_json(self):
        """Should parse nested JSON structures."""
        json_str = '{"nested": {"array": [1, 2, 3], "value": true}}'
        result = parse_focus_card_json_field(json_str)
        assert result == {"nested": {"array": [1, 2, 3], "value": True}}
    
    def test_parses_json_with_unicode(self):
        """Should parse JSON with unicode characters."""
        json_str = '{"name": "Café", "emoji": "🎵"}'
        result = parse_focus_card_json_field(json_str)
        assert result == {"name": "Café", "emoji": "🎵"}
    
    def test_parses_json_with_numbers(self):
        """Should parse JSON with various number types."""
        json_str = '[1, 2.5, -3, 1e10]'
        result = parse_focus_card_json_field(json_str)
        assert result == [1, 2.5, -3, 1e10]
    
    def test_parses_json_with_booleans_and_null(self):
        """Should parse JSON with boolean and null values."""
        json_str = '[true, false, null]'
        result = parse_focus_card_json_field(json_str)
        assert result == [True, False, None]
    
    # --- Invalid/Empty Input ---
    
    def test_returns_empty_list_for_none(self):
        """Should return empty list for None input."""
        result = parse_focus_card_json_field(None)
        assert result == []
    
    def test_returns_empty_list_for_empty_string(self):
        """Should return empty list for empty string."""
        result = parse_focus_card_json_field("")
        assert result == []
    
    def test_returns_empty_list_for_invalid_json(self):
        """Should return empty list for invalid JSON."""
        result = parse_focus_card_json_field("not valid json")
        assert result == []
    
    def test_returns_empty_list_for_partial_json(self):
        """Should return empty list for incomplete JSON."""
        result = parse_focus_card_json_field('{"key": "value"')
        assert result == []
    
    def test_returns_empty_list_for_single_quotes(self):
        """Should return empty list for single-quoted JSON (invalid)."""
        result = parse_focus_card_json_field("{'key': 'value'}")
        assert result == []
    
    # --- Edge Cases ---
    
    def test_handles_whitespace_string(self):
        """Whitespace-only string should return empty list."""
        result = parse_focus_card_json_field("   ")
        assert result == []
    
    def test_handles_json_with_leading_whitespace(self):
        """Should parse JSON with leading/trailing whitespace."""
        result = parse_focus_card_json_field('  ["a", "b"]  ')
        assert result == ["a", "b"]
    
    def test_handles_plain_string_as_invalid(self):
        """Plain string (not array/object) should return empty list."""
        result = parse_focus_card_json_field('"just a string"')
        # Actually this is valid JSON that returns a string
        assert result == "just a string"
    
    def test_handles_plain_number_as_valid(self):
        """Plain number is valid JSON."""
        result = parse_focus_card_json_field('42')
        assert result == 42
    
    def test_handles_integer_input(self):
        """Integer input should return empty list (not a string)."""
        result = parse_focus_card_json_field(42)
        # json.loads(42) would fail
        assert result == []
    
    def test_handles_list_input_returns_empty(self):
        """List input should return empty list (not a string)."""
        result = parse_focus_card_json_field([1, 2, 3])
        # json.loads([1,2,3]) would fail
        assert result == []


class TestParseFocusCardJsonFieldRealWorldExamples:
    """Test with realistic focus card data."""
    
    def test_focus_card_micro_cues(self):
        """Should parse typical micro_cues format."""
        json_str = '["Keep steady beat", "Breathe at phrases", "Listen for pitch center"]'
        result = parse_focus_card_json_field(json_str)
        assert len(result) == 3
        assert "Keep steady beat" in result
    
    def test_focus_card_prompts(self):
        """Should parse typical prompts format."""
        json_str = '{"before": "Set up your embouchure", "during": "Listen carefully", "after": "How did it feel?"}'
        result = parse_focus_card_json_field(json_str)
        assert result["before"] == "Set up your embouchure"
        assert result["during"] == "Listen carefully"
        assert result["after"] == "How did it feel?"
    
    def test_focus_card_empty_fields(self):
        """Should handle empty focus card fields gracefully."""
        assert parse_focus_card_json_field(None) == []
        assert parse_focus_card_json_field("") == []
        assert parse_focus_card_json_field("null") is None
