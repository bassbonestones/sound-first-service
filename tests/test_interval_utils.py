"""
Tests for interval_utils module.

Tests interval ordering, conversion, and comparison functions.
"""

import pytest
from app.interval_utils import (
    INTERVAL_ORDER,
    INTERVAL_SEMITONES,
    INTERVAL_INDEX,
    DEFAULT_MAX_INTERVAL,
    INTERVAL_MILESTONES,
    interval_to_semitones,
    semitones_to_interval,
    can_play_interval,
    get_next_interval,
    get_previous_interval,
    get_intervals_up_to,
)


# =============================================================================
# CONSTANT VALIDATION
# =============================================================================

class TestConstants:
    """Test interval constants are correctly defined."""
    
    def test_interval_order_has_12_intervals(self):
        """Should have exactly 12 intervals (chromatic scale)."""
        assert len(INTERVAL_ORDER) == 12
    
    def test_interval_order_starts_with_m2(self):
        """Should start with minor second."""
        assert INTERVAL_ORDER[0] == "m2"
    
    def test_interval_order_ends_with_P8(self):
        """Should end with octave."""
        assert INTERVAL_ORDER[-1] == "P8"
    
    def test_interval_semitones_values(self):
        """All intervals should map to correct semitone counts."""
        expected = {
            "m2": 1, "M2": 2, "m3": 3, "M3": 4, "P4": 5, "A4": 6,
            "P5": 7, "m6": 8, "M6": 9, "m7": 10, "M7": 11, "P8": 12,
        }
        assert INTERVAL_SEMITONES == expected
    
    def test_interval_index_matches_order(self):
        """Index should match position in order."""
        for i, interval in enumerate(INTERVAL_ORDER):
            assert INTERVAL_INDEX[interval] == i
    
    def test_default_max_interval_is_M2(self):
        """Default should be major 2nd (whole step)."""
        assert DEFAULT_MAX_INTERVAL == "M2"
    
    def test_interval_milestones(self):
        """Milestone intervals should be valid."""
        for level, interval in INTERVAL_MILESTONES.items():
            assert interval in INTERVAL_ORDER


# =============================================================================
# CONVERSION FUNCTIONS
# =============================================================================

class TestIntervalToSemitones:
    """Test interval_to_semitones function."""
    
    def test_minor_second(self):
        assert interval_to_semitones("m2") == 1
    
    def test_major_second(self):
        assert interval_to_semitones("M2") == 2
    
    def test_perfect_fifth(self):
        assert interval_to_semitones("P5") == 7
    
    def test_octave(self):
        assert interval_to_semitones("P8") == 12
    
    def test_tritone(self):
        assert interval_to_semitones("A4") == 6
    
    def test_invalid_interval_returns_zero(self):
        assert interval_to_semitones("invalid") == 0
    
    def test_empty_string_returns_zero(self):
        assert interval_to_semitones("") == 0


class TestSemitonesToInterval:
    """Test semitones_to_interval function."""
    
    def test_one_semitone(self):
        assert semitones_to_interval(1) == "m2"
    
    def test_five_semitones(self):
        assert semitones_to_interval(5) == "P4"
    
    def test_twelve_semitones(self):
        assert semitones_to_interval(12) == "P8"
    
    def test_invalid_semitones_returns_none(self):
        assert semitones_to_interval(0) is None
        assert semitones_to_interval(13) is None
        assert semitones_to_interval(-1) is None


# =============================================================================
# COMPARISON FUNCTIONS
# =============================================================================

class TestCanPlayInterval:
    """Test can_play_interval function."""
    
    def test_user_can_play_smaller_interval(self):
        """User with P5 should be able to play material with M3."""
        assert can_play_interval("P5", "M3") is True
    
    def test_user_can_play_same_interval(self):
        """User can play material with exactly their max interval."""
        assert can_play_interval("P5", "P5") is True
    
    def test_user_cannot_play_larger_interval(self):
        """User with M3 cannot play material with P5."""
        assert can_play_interval("M3", "P5") is False
    
    def test_user_with_octave_can_play_anything(self):
        """User with P8 can play any interval."""
        assert can_play_interval("P8", "P8") is True
        assert can_play_interval("P8", "m2") is True
    
    def test_none_user_max_allows_all(self):
        """If user max is None, allow all materials."""
        assert can_play_interval(None, "P5") is True
    
    def test_none_material_interval_allows_all(self):
        """If material interval is None, allow."""
        assert can_play_interval("P5", None) is True
    
    def test_both_none_allows(self):
        """If both are None, allow."""
        assert can_play_interval(None, None) is True
    
    def test_invalid_user_interval_allows(self):
        """Invalid user interval allows by default."""
        assert can_play_interval("invalid", "P5") is True
    
    def test_invalid_material_interval_allows(self):
        """Invalid material interval allows by default."""
        assert can_play_interval("P5", "invalid") is True


# =============================================================================
# NAVIGATION FUNCTIONS
# =============================================================================

class TestGetNextInterval:
    """Test get_next_interval function."""
    
    def test_m2_to_M2(self):
        assert get_next_interval("m2") == "M2"
    
    def test_M2_to_m3(self):
        assert get_next_interval("M2") == "m3"
    
    def test_P5_to_m6(self):
        assert get_next_interval("P5") == "m6"
    
    def test_M7_to_P8(self):
        assert get_next_interval("M7") == "P8"
    
    def test_P8_returns_none(self):
        """No next interval after octave."""
        assert get_next_interval("P8") is None
    
    def test_invalid_returns_none(self):
        assert get_next_interval("invalid") is None


class TestGetPreviousInterval:
    """Test get_previous_interval function."""
    
    def test_M2_to_m2(self):
        assert get_previous_interval("M2") == "m2"
    
    def test_P5_to_A4(self):
        assert get_previous_interval("P5") == "A4"
    
    def test_P8_to_M7(self):
        assert get_previous_interval("P8") == "M7"
    
    def test_m2_returns_none(self):
        """No previous interval before m2."""
        assert get_previous_interval("m2") is None
    
    def test_invalid_returns_none(self):
        assert get_previous_interval("invalid") is None


class TestGetIntervalsUpTo:
    """Test get_intervals_up_to function."""
    
    def test_up_to_m2(self):
        assert get_intervals_up_to("m2") == ["m2"]
    
    def test_up_to_M3(self):
        assert get_intervals_up_to("M3") == ["m2", "M2", "m3", "M3"]
    
    def test_up_to_P5(self):
        expected = ["m2", "M2", "m3", "M3", "P4", "A4", "P5"]
        assert get_intervals_up_to("P5") == expected
    
    def test_up_to_P8(self):
        assert get_intervals_up_to("P8") == INTERVAL_ORDER
    
    def test_invalid_returns_empty(self):
        assert get_intervals_up_to("invalid") == []


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntervalProgression:
    """Test interval progression scenarios."""
    
    def test_full_progression_from_m2_to_P8(self):
        """Walking through all intervals should hit each one."""
        intervals = []
        current = "m2"
        while current:
            intervals.append(current)
            current = get_next_interval(current)
        assert intervals == INTERVAL_ORDER
    
    def test_reverse_progression_from_P8_to_m2(self):
        """Walking backwards should hit each interval."""
        intervals = []
        current = "P8"
        while current:
            intervals.append(current)
            current = get_previous_interval(current)
        assert intervals == list(reversed(INTERVAL_ORDER))
    
    def test_milestone_intervals_are_valid(self):
        """All milestone intervals should be in the order."""
        for milestone_interval in INTERVAL_MILESTONES.values():
            assert milestone_interval in INTERVAL_ORDER
    
    def test_beginner_can_play_up_to_M3(self):
        """Beginner milestone user can play M3 and below."""
        user_max = INTERVAL_MILESTONES["beginner"]  # M3
        assert can_play_interval(user_max, "m2") is True
        assert can_play_interval(user_max, "M3") is True
        assert can_play_interval(user_max, "P4") is False
    
    def test_intervals_up_to_matches_can_play(self):
        """get_intervals_up_to should list all playable intervals."""
        user_max = "P5"
        playable = get_intervals_up_to(user_max)
        for interval in playable:
            assert can_play_interval(user_max, interval) is True
        # Next one should not be playable
        next_int = get_next_interval(user_max)
        if next_int:
            assert can_play_interval(user_max, next_int) is False
