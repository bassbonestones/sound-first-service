"""
Tests for capabilities/detection/value_matchers.py

Tests for value matching utilities used in detection rules.
"""

import pytest

from app.capabilities.detection.value_matchers import (
    check_value_condition,
    get_nested_value,
)


class TestGetNestedValue:
    """Tests for get_nested_value function."""

    def test_empty_path_returns_item(self):
        """Empty path should return the item itself."""
        item = {"type": "quarter", "dots": 1}
        result = get_nested_value(item, "")
        assert result == item

    def test_simple_dict_access(self):
        """Should access dict by key."""
        item = {"type": "quarter", "dots": 1}
        assert get_nested_value(item, "type") == "quarter"
        assert get_nested_value(item, "dots") == 1

    def test_nested_dict_access(self):
        """Should access nested dicts with dot notation."""
        item = {"note": {"type": "quarter", "duration": {"beats": 1}}}
        assert get_nested_value(item, "note.type") == "quarter"
        assert get_nested_value(item, "note.duration.beats") == 1

    def test_missing_key_returns_none(self):
        """Missing key should return None."""
        item = {"type": "quarter"}
        result = get_nested_value(item, "dots")
        assert result is None

    def test_missing_nested_key_returns_none(self):
        """Missing nested key should return None."""
        item = {"note": {"type": "quarter"}}
        result = get_nested_value(item, "note.duration.beats")
        assert result is None

    def test_object_attribute_access(self):
        """Should access object attributes."""
        class Note:
            def __init__(self):
                self.type = "quarter"
                self.dots = 0
        
        note = Note()
        assert get_nested_value(note, "type") == "quarter"
        assert get_nested_value(note, "dots") == 0

    def test_mixed_dict_and_object(self):
        """Should handle mixed dict and object traversal."""
        class Duration:
            beats = 2
        
        item = {"note": Duration()}
        result = get_nested_value(item, "note.beats")
        assert result == 2

    def test_none_item_returns_none(self):
        """None item should return None for any path."""
        result = get_nested_value(None, "type")
        assert result is None


class TestCheckValueCondition:
    """Tests for check_value_condition function."""

    def test_eq_match(self):
        """Should match equal values."""
        item = {"type": "quarter"}
        config = {"eq": "quarter"}
        
        assert check_value_condition(item, "type", config) is True

    def test_eq_no_match(self):
        """Should not match unequal values."""
        item = {"type": "quarter"}
        config = {"eq": "half"}
        
        assert check_value_condition(item, "type", config) is False

    def test_contains_match(self):
        """Should match containing substring."""
        item = {"name": "articulation_staccato"}
        config = {"contains": "staccato"}
        
        assert check_value_condition(item, "name", config) is True

    def test_contains_case_insensitive(self):
        """Contains should be case-insensitive."""
        item = {"name": "STACCATO"}
        config = {"contains": "staccato"}
        
        assert check_value_condition(item, "name", config) is True

    def test_contains_no_match(self):
        """Should not match non-containing string."""
        item = {"name": "articulation_accent"}
        config = {"contains": "staccato"}
        
        assert check_value_condition(item, "name", config) is False

    def test_gte_match(self):
        """Should match greater-than-or-equal."""
        item = {"dots": 2}
        config = {"gte": 1}
        
        assert check_value_condition(item, "dots", config) is True

    def test_gte_exact_match(self):
        """Should match exactly equal for gte."""
        item = {"dots": 1}
        config = {"gte": 1}
        
        assert check_value_condition(item, "dots", config) is True

    def test_gte_no_match(self):
        """Should not match less-than for gte."""
        item = {"dots": 0}
        config = {"gte": 1}
        
        assert check_value_condition(item, "dots", config) is False

    def test_lte_match(self):
        """Should match less-than-or-equal."""
        item = {"dots": 0}
        config = {"lte": 1}
        
        assert check_value_condition(item, "dots", config) is True

    def test_lte_exact_match(self):
        """Should match exactly equal for lte."""
        item = {"dots": 1}
        config = {"lte": 1}
        
        assert check_value_condition(item, "dots", config) is True

    def test_lte_no_match(self):
        """Should not match greater-than for lte."""
        item = {"dots": 2}
        config = {"lte": 1}
        
        assert check_value_condition(item, "dots", config) is False

    def test_missing_field_returns_false(self):
        """Missing field should return False."""
        item = {"type": "quarter"}
        config = {"eq": 1}
        
        assert check_value_condition(item, "dots", config) is False

    def test_no_condition_returns_false(self):
        """Empty config should return False."""
        item = {"type": "quarter"}
        config = {}
        
        assert check_value_condition(item, "type", config) is False

    def test_numeric_eq(self):
        """Should handle numeric equality."""
        item = {"count": 5}
        config = {"eq": 5}
        
        assert check_value_condition(item, "count", config) is True

    def test_nested_field_condition(self):
        """Should handle nested field paths."""
        item = {"note": {"duration": {"beats": 2}}}
        config = {"gte": 2}
        
        assert check_value_condition(item, "note.duration.beats", config) is True
