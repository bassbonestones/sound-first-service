"""Tests for tempo_definitions module."""

import pytest

from app.schemas.generation_schemas import RhythmType
from app.services.generation.tempo_definitions import (
    TempoBounds,
    TEMPO_BOUNDS,
    get_tempo_bounds,
    get_default_tempo,
    validate_tempo_for_rhythm,
    get_supported_rhythms_with_bounds,
    get_max_notes_for_rhythm,
    validate_note_count_for_rhythm,
    get_compatible_rhythms_for_note_count,
)


class TestTempoBounds:
    """Tests for TempoBounds dataclass."""

    def test_create_valid_bounds(self) -> None:
        """Can create bounds with valid min/max."""
        bounds = TempoBounds(min_bpm=60, max_bpm=120)
        assert bounds.min_bpm == 60
        assert bounds.max_bpm == 120

    def test_min_bpm_too_low_raises(self) -> None:
        """Creating bounds with min < 20 raises ValueError."""
        with pytest.raises(ValueError, match="min_bpm must be >= 20"):
            TempoBounds(min_bpm=15, max_bpm=100)

    def test_max_bpm_too_high_raises(self) -> None:
        """Creating bounds with max > 400 raises ValueError."""
        with pytest.raises(ValueError, match="max_bpm must be <= 400"):
            TempoBounds(min_bpm=40, max_bpm=450)

    def test_min_exceeds_max_raises(self) -> None:
        """Creating bounds where min > max raises ValueError."""
        with pytest.raises(ValueError, match="min_bpm.*cannot exceed max_bpm"):
            TempoBounds(min_bpm=120, max_bpm=60)

    def test_equal_min_max_valid(self) -> None:
        """Bounds with min == max are valid (fixed tempo)."""
        bounds = TempoBounds(min_bpm=100, max_bpm=100)
        assert bounds.min_bpm == bounds.max_bpm == 100

    def test_contains_within_range(self) -> None:
        """contains() returns True for BPM within range."""
        bounds = TempoBounds(min_bpm=60, max_bpm=120)
        assert bounds.contains(60) is True
        assert bounds.contains(90) is True
        assert bounds.contains(120) is True

    def test_contains_outside_range(self) -> None:
        """contains() returns False for BPM outside range."""
        bounds = TempoBounds(min_bpm=60, max_bpm=120)
        assert bounds.contains(59) is False
        assert bounds.contains(121) is False

    def test_clamp_below_min(self) -> None:
        """clamp() brings up values below min."""
        bounds = TempoBounds(min_bpm=60, max_bpm=120)
        assert bounds.clamp(40) == 60

    def test_clamp_above_max(self) -> None:
        """clamp() brings down values above max."""
        bounds = TempoBounds(min_bpm=60, max_bpm=120)
        assert bounds.clamp(150) == 120

    def test_clamp_within_range(self) -> None:
        """clamp() returns value unchanged when in range."""
        bounds = TempoBounds(min_bpm=60, max_bpm=120)
        assert bounds.clamp(90) == 90

    def test_as_tuple(self) -> None:
        """as_tuple() returns (min, max) tuple."""
        bounds = TempoBounds(min_bpm=60, max_bpm=120)
        assert bounds.as_tuple() == (60, 120)

    def test_frozen(self) -> None:
        """TempoBounds is immutable (frozen)."""
        bounds = TempoBounds(min_bpm=60, max_bpm=120)
        with pytest.raises(Exception):  # FrozenInstanceError
            bounds.min_bpm = 80  # type: ignore[misc]


class TestTempoBoundsMapping:
    """Tests for TEMPO_BOUNDS mapping completeness."""

    def test_all_rhythm_types_have_bounds(self) -> None:
        """Every RhythmType has tempo bounds defined."""
        for rhythm_type in RhythmType:
            assert rhythm_type in TEMPO_BOUNDS, f"Missing bounds for {rhythm_type}"

    def test_all_bounds_are_valid(self) -> None:
        """All defined bounds are valid TempoBounds."""
        for rhythm_type, bounds in TEMPO_BOUNDS.items():
            assert isinstance(bounds, TempoBounds), f"Invalid bounds for {rhythm_type}"
            assert bounds.min_bpm >= 20
            assert bounds.max_bpm <= 400
            assert bounds.min_bpm <= bounds.max_bpm

    def test_sustained_rhythms_have_low_max(self) -> None:
        """Sustained rhythms (whole, half) have lower max tempo."""
        assert TEMPO_BOUNDS[RhythmType.WHOLE_NOTES].max_bpm <= 100
        assert TEMPO_BOUNDS[RhythmType.HALF_NOTES].max_bpm <= 100

    def test_sixteenths_have_lower_max_than_eighths(self) -> None:
        """Sixteenths should have lower max BPM than eighths."""
        eighths_max = TEMPO_BOUNDS[RhythmType.EIGHTH_NOTES].max_bpm
        sixteenths_max = TEMPO_BOUNDS[RhythmType.SIXTEENTH_NOTES].max_bpm
        assert sixteenths_max <= eighths_max

    def test_all_rhythms_start_at_40(self) -> None:
        """All rhythms should allow slow practice starting at 40 BPM."""
        for rhythm_type, bounds in TEMPO_BOUNDS.items():
            assert bounds.min_bpm == 40, f"{rhythm_type} min_bpm should be 40"


class TestGetTempoBounds:
    """Tests for get_tempo_bounds function."""

    def test_returns_bounds_for_valid_rhythm(self) -> None:
        """get_tempo_bounds returns TempoBounds for valid rhythm."""
        bounds = get_tempo_bounds(RhythmType.QUARTER_NOTES)
        assert isinstance(bounds, TempoBounds)
        assert bounds.min_bpm > 0
        assert bounds.max_bpm > bounds.min_bpm

    def test_quarter_notes_bounds(self) -> None:
        """Quarter notes have expected wide range."""
        bounds = get_tempo_bounds(RhythmType.QUARTER_NOTES)
        assert bounds.min_bpm == 40
        assert bounds.max_bpm == 200

    def test_sixteenth_notes_bounds(self) -> None:
        """Sixteenth notes have expected range."""
        bounds = get_tempo_bounds(RhythmType.SIXTEENTH_NOTES)
        assert bounds.min_bpm == 40
        assert bounds.max_bpm == 120


class TestGetDefaultTempo:
    """Tests for get_default_tempo function."""

    def test_returns_int(self) -> None:
        """Default tempo is an integer."""
        tempo = get_default_tempo(RhythmType.QUARTER_NOTES)
        assert isinstance(tempo, int)

    def test_within_bounds(self) -> None:
        """Default tempo is within the rhythm's bounds."""
        for rhythm_type in RhythmType:
            tempo = get_default_tempo(rhythm_type)
            bounds = get_tempo_bounds(rhythm_type)
            assert bounds.contains(tempo), f"Default {tempo} outside bounds for {rhythm_type}"

    def test_not_at_extremes(self) -> None:
        """Default tempo is not at min or max (has headroom)."""
        for rhythm_type in RhythmType:
            tempo = get_default_tempo(rhythm_type)
            bounds = get_tempo_bounds(rhythm_type)
            # Only check if there's range to work with
            if bounds.max_bpm > bounds.min_bpm + 20:
                assert tempo > bounds.min_bpm, f"Default too low for {rhythm_type}"
                assert tempo < bounds.max_bpm, f"Default too high for {rhythm_type}"


class TestValidateTempoForRhythm:
    """Tests for validate_tempo_for_rhythm function."""

    def test_valid_tempo_passes(self) -> None:
        """Valid tempo is returned unchanged."""
        result = validate_tempo_for_rhythm(RhythmType.QUARTER_NOTES, 120)
        assert result == 120

    def test_tempo_too_low_raises(self) -> None:
        """Tempo below min raises ValueError."""
        with pytest.raises(ValueError, match="outside valid range"):
            validate_tempo_for_rhythm(RhythmType.QUARTER_NOTES, 30)

    def test_tempo_too_high_raises(self) -> None:
        """Tempo above max raises ValueError."""
        with pytest.raises(ValueError, match="outside valid range"):
            validate_tempo_for_rhythm(RhythmType.SIXTEENTH_NOTES, 200)

    def test_clamp_mode_low(self) -> None:
        """Clamp mode brings up values below min."""
        result = validate_tempo_for_rhythm(RhythmType.QUARTER_NOTES, 30, clamp=True)
        assert result == 40  # min for quarter notes

    def test_clamp_mode_high(self) -> None:
        """Clamp mode brings down values above max."""
        result = validate_tempo_for_rhythm(RhythmType.SIXTEENTH_NOTES, 200, clamp=True)
        assert result == 120  # max for sixteenths

    def test_clamp_mode_valid(self) -> None:
        """Clamp mode returns valid values unchanged."""
        result = validate_tempo_for_rhythm(RhythmType.QUARTER_NOTES, 100, clamp=True)
        assert result == 100


class TestGetSupportedRhythmsWithBounds:
    """Tests for get_supported_rhythms_with_bounds function."""

    def test_returns_dict(self) -> None:
        """Returns a dictionary."""
        result = get_supported_rhythms_with_bounds()
        assert isinstance(result, dict)

    def test_all_rhythms_included(self) -> None:
        """All rhythm types are in result."""
        result = get_supported_rhythms_with_bounds()
        assert len(result) == len(RhythmType)

    def test_uses_string_keys(self) -> None:
        """Keys are rhythm type string values."""
        result = get_supported_rhythms_with_bounds()
        assert "quarter_notes" in result
        assert "sixteenth_notes" in result

    def test_bounds_structure(self) -> None:
        """Each entry has min_bpm and max_bpm."""
        result = get_supported_rhythms_with_bounds()
        for rhythm_name, bounds in result.items():
            assert "min_bpm" in bounds, f"Missing min_bpm for {rhythm_name}"
            assert "max_bpm" in bounds, f"Missing max_bpm for {rhythm_name}"
            assert isinstance(bounds["min_bpm"], int)
            assert isinstance(bounds["max_bpm"], int)

    def test_values_match_constants(self) -> None:
        """Returned values match TEMPO_BOUNDS constants."""
        result = get_supported_rhythms_with_bounds()
        for rhythm_type in RhythmType:
            rhythm_name = rhythm_type.value
            expected_bounds = TEMPO_BOUNDS[rhythm_type]
            assert result[rhythm_name]["min_bpm"] == expected_bounds.min_bpm
            assert result[rhythm_name]["max_bpm"] == expected_bounds.max_bpm


# =============================================================================
# NOTE COUNT VALIDATION TESTS
# =============================================================================

class TestGetMaxNotesForRhythm:
    """Tests for get_max_notes_for_rhythm function."""

    def test_whole_notes_has_limit(self) -> None:
        """Whole notes should have a note count limit."""
        result = get_max_notes_for_rhythm(RhythmType.WHOLE_NOTES)
        assert result is not None
        assert result == 16

    def test_half_notes_has_limit(self) -> None:
        """Half notes should have a note count limit."""
        result = get_max_notes_for_rhythm(RhythmType.HALF_NOTES)
        assert result is not None
        assert result == 32

    def test_quarter_notes_no_limit(self) -> None:
        """Quarter notes should have no limit."""
        result = get_max_notes_for_rhythm(RhythmType.QUARTER_NOTES)
        assert result is None

    def test_eighth_notes_no_limit(self) -> None:
        """Eighth notes should have no limit."""
        result = get_max_notes_for_rhythm(RhythmType.EIGHTH_NOTES)
        assert result is None

    def test_sixteenth_notes_no_limit(self) -> None:
        """Sixteenth notes should have no limit."""
        result = get_max_notes_for_rhythm(RhythmType.SIXTEENTH_NOTES)
        assert result is None


class TestValidateNoteCountForRhythm:
    """Tests for validate_note_count_for_rhythm function."""

    def test_whole_notes_under_limit_passes(self) -> None:
        """Whole notes under limit should pass validation."""
        # Should not raise
        validate_note_count_for_rhythm(RhythmType.WHOLE_NOTES, 8)

    def test_whole_notes_at_limit_passes(self) -> None:
        """Whole notes at limit should pass validation."""
        validate_note_count_for_rhythm(RhythmType.WHOLE_NOTES, 16)

    def test_whole_notes_over_limit_raises(self) -> None:
        """Whole notes over limit should raise ValueError."""
        with pytest.raises(ValueError, match="whole_notes rhythm is limited to 16 notes"):
            validate_note_count_for_rhythm(RhythmType.WHOLE_NOTES, 50)

    def test_half_notes_over_limit_raises(self) -> None:
        """Half notes over limit should raise ValueError."""
        with pytest.raises(ValueError, match="half_notes rhythm is limited to 32 notes"):
            validate_note_count_for_rhythm(RhythmType.HALF_NOTES, 100)

    def test_quarter_notes_high_count_passes(self) -> None:
        """Quarter notes should allow high note counts."""
        # Should not raise
        validate_note_count_for_rhythm(RhythmType.QUARTER_NOTES, 500)

    def test_eighth_notes_high_count_passes(self) -> None:
        """Eighth notes should allow high note counts."""
        validate_note_count_for_rhythm(RhythmType.EIGHTH_NOTES, 1000)

    def test_error_message_suggests_faster_rhythm(self) -> None:
        """Error message should suggest using faster rhythm."""
        with pytest.raises(ValueError, match="Use a faster rhythm"):
            validate_note_count_for_rhythm(RhythmType.WHOLE_NOTES, 50)


class TestGetCompatibleRhythmsForNoteCount:
    """Tests for get_compatible_rhythms_for_note_count function."""

    def test_low_count_all_rhythms_compatible(self) -> None:
        """Low note count should be compatible with all rhythms."""
        result = get_compatible_rhythms_for_note_count(8)
        assert len(result) == len(RhythmType)

    def test_medium_count_excludes_whole_notes(self) -> None:
        """Medium note count should exclude whole notes."""
        result = get_compatible_rhythms_for_note_count(20)
        assert RhythmType.WHOLE_NOTES not in result
        assert RhythmType.HALF_NOTES in result
        assert RhythmType.QUARTER_NOTES in result

    def test_high_count_excludes_sustained_rhythms(self) -> None:
        """High note count should exclude both sustained rhythms."""
        result = get_compatible_rhythms_for_note_count(50)
        assert RhythmType.WHOLE_NOTES not in result
        assert RhythmType.HALF_NOTES not in result
        assert RhythmType.QUARTER_NOTES in result
        assert RhythmType.EIGHTH_NOTES in result

    def test_returns_rhythm_types(self) -> None:
        """Result should contain RhythmType enum values."""
        result = get_compatible_rhythms_for_note_count(8)
        for item in result:
            assert isinstance(item, RhythmType)
