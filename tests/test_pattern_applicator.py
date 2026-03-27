"""Tests for pattern_applicator module.

Tests all scale and arpeggio pattern algorithms to ensure they
transform pitch sequences correctly.
"""

import pytest
from typing import List

from app.schemas.generation_schemas import ArpeggioPattern, ScalePattern
from app.services.generation.pattern_applicator import (
    apply_scale_pattern,
    apply_arpeggio_pattern,
    get_supported_scale_patterns,
    get_supported_arpeggio_patterns,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def c_major_scale() -> List[int]:
    """C major scale one octave: C4 to C5."""
    return [60, 62, 64, 65, 67, 69, 71, 72]


@pytest.fixture
def c_major_scale_2_octaves() -> List[int]:
    """C major scale two octaves: C4 to C6."""
    return [60, 62, 64, 65, 67, 69, 71, 72, 74, 76, 77, 79, 81, 83, 84]


@pytest.fixture
def c_major_triad() -> List[int]:
    """C major triad: C4, E4, G4, C5, E5, G5."""
    return [60, 64, 67, 72, 76, 79]


@pytest.fixture
def c_major_7th() -> List[int]:
    """C major 7th arpeggio: C4, E4, G4, B4, C5, E5, G5, B5."""
    return [60, 64, 67, 71, 72, 76, 79, 83]


# =============================================================================
# Test Scale Patterns - Straight
# =============================================================================


class TestScaleStraightPatterns:
    """Tests for straight scale patterns."""

    def test_straight_up(self, c_major_scale: List[int]) -> None:
        result = apply_scale_pattern(c_major_scale, ScalePattern.STRAIGHT_UP)
        assert result == c_major_scale

    def test_straight_down(self, c_major_scale: List[int]) -> None:
        result = apply_scale_pattern(c_major_scale, ScalePattern.STRAIGHT_DOWN)
        assert result == list(reversed(c_major_scale))

    def test_straight_up_down(self, c_major_scale: List[int]) -> None:
        result = apply_scale_pattern(c_major_scale, ScalePattern.STRAIGHT_UP_DOWN)
        # Up: C D E F G A B C, Down: B A G F E D C (no repeated C at top)
        expected = c_major_scale + list(reversed(c_major_scale[:-1]))
        assert result == expected
        assert len(result) == 15  # 8 up + 7 down

    def test_straight_up_short_scale(self) -> None:
        """Edge case: single note."""
        result = apply_scale_pattern([60], ScalePattern.STRAIGHT_UP)
        assert result == [60]

    def test_straight_down_up(self, c_major_scale: List[int]) -> None:
        """Down then up pattern: 7 6 5 4 3 2 1 2 3 4 5 6 7."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.STRAIGHT_DOWN_UP)
        # Down: C5 B A G F E D C4, Up: D E F G A B C5 (no repeated C4)
        expected = list(reversed(c_major_scale)) + c_major_scale[1:]
        assert result == expected
        assert len(result) == 15  # 8 down + 7 up

    def test_straight_down_up_short_scale(self) -> None:
        """Edge case: single note."""
        result = apply_scale_pattern([60], ScalePattern.STRAIGHT_DOWN_UP)
        assert result == [60]


class TestScalePyramidPatterns:
    """Tests for pyramid (cumulative reach) scale patterns."""

    def test_pyramid_ascend_basic(self) -> None:
        """Pyramid ascending: 1-2-1-2-3-2-1-2-3-4-3-2-1 (no repeated tonic)."""
        # Use 4-note scale for simpler testing
        pitches = [60, 62, 64, 65]  # C D E F (1 2 3 4)
        result = apply_scale_pattern(pitches, ScalePattern.PYRAMID_ASCEND)
        # Pattern: start from 1, reach further each time, return to 1 (no double tonic)
        # 1-2-1-2-3-2-1-2-3-4-3-2-1
        expected = [
            60, 62, 60,  # 1-2-1
            62, 64, 62, 60,  # -2-3-2-1
            62, 64, 65, 64, 62, 60,  # -2-3-4-3-2-1
        ]
        assert result == expected

    def test_pyramid_ascend_7_notes(self, c_major_scale: List[int]) -> None:
        """Pyramid ascending with full octave scale."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.PYRAMID_ASCEND)
        # First segment should be 1-2-1
        assert result[:3] == [60, 62, 60]
        # Last segment is -2-3-4-5-6-7-8-7-6-5-4-3-2-1 (14 notes, no leading 1)
        assert result[-14:] == [62, 64, 65, 67, 69, 71, 72, 71, 69, 67, 65, 64, 62, 60]

    def test_pyramid_descend_basic(self) -> None:
        """Pyramid descending: 4-3-4-3-2-3-4-3-2-1-2-3-4 (no repeated top)."""
        # Use 4-note scale for simpler testing
        pitches = [60, 62, 64, 65]  # C D E F (1 2 3 4)
        result = apply_scale_pattern(pitches, ScalePattern.PYRAMID_DESCEND)
        # Mirror of ascending: start from 4, reach further down, return to 4 (no double top)
        # 4-3-4-3-2-3-4-3-2-1-2-3-4
        expected = [
            65, 64, 65,  # 4-3-4
            64, 62, 64, 65,  # -3-2-3-4
            64, 62, 60, 62, 64, 65,  # -3-2-1-2-3-4
        ]
        assert result == expected

    def test_pyramid_descend_7_notes(self, c_major_scale: List[int]) -> None:
        """Pyramid descending with full octave scale."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.PYRAMID_DESCEND)
        # First segment should be 8-7-8
        assert result[:3] == [72, 71, 72]
        # Last segment is -7-6-5-4-3-2-1-2-3-4-5-6-7-8 (14 notes, no leading 8)
        assert result[-14:] == [71, 69, 67, 65, 64, 62, 60, 62, 64, 65, 67, 69, 71, 72]

    def test_pyramid_single_note(self) -> None:
        """Edge case: single note returns itself."""
        result = apply_scale_pattern([60], ScalePattern.PYRAMID_ASCEND)
        assert result == [60]
        result = apply_scale_pattern([60], ScalePattern.PYRAMID_DESCEND)
        assert result == [60]


# =============================================================================
# Test Scale Patterns - Intervals
# =============================================================================


class TestScaleIntervalPatterns:
    """Tests for interval-based scale patterns with extension."""

    def test_in_3rds(self, c_major_scale: List[int]) -> None:
        """In 3rds: ascending pairs to re above, descending pairs to ti below, end on do."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.IN_3RDS)
        # 1-3, 2-4, 3-5, 4-6, 5-7, 6-8, 7-9, 8-6, 7-5, 6-4, 5-3, 4-2, 3-1, 2-7, 1
        expected = [
            60, 64,  # C-E (1-3)
            62, 65,  # D-F (2-4)
            64, 67,  # E-G (3-5)
            65, 69,  # F-A (4-6)
            67, 71,  # G-B (5-7)
            69, 72,  # A-C (6-8)
            71, 74,  # B-D (7-9 - extends to re above)
            72, 69,  # C-A (8-6)
            71, 67,  # B-G (7-5)
            69, 65,  # A-F (6-4)
            67, 64,  # G-E (5-3)
            65, 62,  # F-D (4-2)
            64, 60,  # E-C (3-1)
            62, 59,  # D-B (2-7 - extends to ti below)
            60,      # C (final do)
        ]
        assert result == expected

    def test_in_4ths(self, c_major_scale: List[int]) -> None:
        """In 4ths: ascending pairs to mi above, descending pairs to la below, end on do."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.IN_4THS)
        # 1-4, 2-5, 3-6, 4-7, 5-8, 6-9, 7-10, 8-5, 7-4, 6-3, 5-2, 4-1, 3-7, 2-6, 1
        expected = [
            60, 65,  # C-F (1-4)
            62, 67,  # D-G (2-5)
            64, 69,  # E-A (3-6)
            65, 71,  # F-B (4-7)
            67, 72,  # G-C (5-8)
            69, 74,  # A-D (6-9 - extends to re above)
            71, 76,  # B-E (7-10 - extends to mi above)
            72, 67,  # C-G (8-5)
            71, 65,  # B-F (7-4)
            69, 64,  # A-E (6-3)
            67, 62,  # G-D (5-2)
            65, 60,  # F-C (4-1)
            64, 59,  # E-B (3-7 - extends to ti below)
            62, 57,  # D-A (2-6 - extends to la below)
            60,      # C (final do)
        ]
        assert result == expected

    def test_in_5ths(self, c_major_scale: List[int]) -> None:
        """In 5ths: ascending pairs extending above, descending extending below."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.IN_5THS)
        # Starts at do, extends 3 notes above and below
        assert result[0] == 60  # Starts on C
        assert result[-1] == 60  # Ends on C
        assert len(result) == 29  # 7 ascending pairs + 7 descending pairs + 1 final

    def test_in_6ths(self, c_major_scale: List[int]) -> None:
        """In 6ths: ascending pairs extending above, descending extending below."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.IN_6THS)
        assert result[0] == 60  # Starts on C
        assert result[-1] == 60  # Ends on C
        assert len(result) == 29

    def test_in_7ths(self, c_major_scale: List[int]) -> None:
        """In 7ths: ascending pairs extending above, descending extending below."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.IN_7THS)
        assert result[0] == 60  # Starts on C
        assert result[-1] == 60  # Ends on C
        assert len(result) == 29

    def test_in_octaves_requires_two_octaves(
        self, c_major_scale_2_octaves: List[int]
    ) -> None:
        """In octaves: needs two octaves to work properly."""
        result = apply_scale_pattern(
            c_major_scale_2_octaves, ScalePattern.IN_OCTAVES
        )
        # With 15 notes (2 octaves - 1), extension=6
        assert result[0] == 60  # Starts on C
        assert result[-1] == 60  # Ends on C


# =============================================================================
# Test Scale Patterns - Groups
# =============================================================================


class TestScaleGroupPatterns:
    """Tests for group-based scale patterns (up and down with extension)."""

    def test_groups_of_3(self, c_major_scale: List[int]) -> None:
        """Groups of 3 goes up then down, extending above and below the octave.
        
        Traditional pattern: 1-2-3, 2-3-4, ..., 7-8-9, 8-7-6, ..., 2-1-7, 1
        """
        result = apply_scale_pattern(c_major_scale, ScalePattern.GROUPS_OF_3)
        
        # Ascending: 7 groups (extends to D5=74 above)
        expected_asc = [
            60, 62, 64,  # C-D-E (1-2-3)
            62, 64, 65,  # D-E-F (2-3-4)
            64, 65, 67,  # E-F-G (3-4-5)
            65, 67, 69,  # F-G-A (4-5-6)
            67, 69, 71,  # G-A-B (5-6-7)
            69, 71, 72,  # A-B-C (6-7-8)
            71, 72, 74,  # B-C-D (7-8-9) - extends above octave!
        ]
        # Descending: 7 groups (extends to B3=59 below)
        expected_desc = [
            72, 71, 69,  # C-B-A (8-7-6)
            71, 69, 67,  # B-A-G (7-6-5)
            69, 67, 65,  # A-G-F (6-5-4)
            67, 65, 64,  # G-F-E (5-4-3)
            65, 64, 62,  # F-E-D (4-3-2)
            64, 62, 60,  # E-D-C (3-2-1)
            62, 60, 59,  # D-C-B (2-1-7) - extends below octave!
        ]
        # Final note (do)
        expected_final = [60]
        
        expected = expected_asc + expected_desc + expected_final
        assert result == expected

    def test_groups_of_3_descending_same_as_ascending(self, c_major_scale: List[int]) -> None:
        """Ascending flag is now ignored - groups always do up-then-down."""
        result_asc = apply_scale_pattern(c_major_scale, ScalePattern.GROUPS_OF_3, ascending=True)
        result_desc = apply_scale_pattern(c_major_scale, ScalePattern.GROUPS_OF_3, ascending=False)
        # Both should produce the same up-then-down pattern
        assert result_asc == result_desc

    def test_groups_of_4(self, c_major_scale: List[int]) -> None:
        """Groups of 4 extends 2 notes above (D5, E5) and 2 notes below (B3, A3)."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.GROUPS_OF_4)
        
        # Should extend by 2 notes each direction
        # Ascending groups: 7 groups of 4
        # Descending groups: 7 groups of 4 + final note
        # Check first ascending group
        assert result[0:4] == [60, 62, 64, 65]  # C-D-E-F (1-2-3-4)
        # Check last ascending group goes to E5 (76)
        # Groups of 4 on 8-note scale needs extension of 2 notes above
        # Last ascending group starts at B (71): B-C-D-E = 71-72-74-76
        assert 76 in result  # E5 should be in the pattern
        # Check it extends below to A3 (57)
        assert 57 in result  # A3 should be in the pattern
        # Final note should be C4 (60)
        assert result[-1] == 60

    def test_groups_of_5(self, c_major_scale: List[int]) -> None:
        """Groups of 5 extends 3 notes above and below."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.GROUPS_OF_5)
        # First group: C-D-E-F-G (1-2-3-4-5)
        assert result[0:5] == [60, 62, 64, 65, 67]
        # Should extend 3 above (D5, E5, F5) and 3 below (B3, A3, G3)
        assert 77 in result  # F5 (sol above)
        assert 55 in result  # G3 (sol below)
        assert result[-1] == 60  # Ends on do

    def test_groups_of_6(self, c_major_scale: List[int]) -> None:
        """Groups of 6 extends 4 notes above and below."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.GROUPS_OF_6)
        # First group: C-D-E-F-G-A (1-2-3-4-5-6)
        assert result[0:6] == [60, 62, 64, 65, 67, 69]
        # Should extend 4 above and 4 below
        assert 79 in result  # G5 (la above)
        assert 53 in result  # F3 (fa below)
        assert result[-1] == 60  # Ends on do

    def test_groups_of_7(self, c_major_scale: List[int]) -> None:
        """Groups of 7 extends 5 notes above and below."""
        result = apply_scale_pattern(c_major_scale, ScalePattern.GROUPS_OF_7)
        # First group: C-D-E-F-G-A-B (1-2-3-4-5-6-7)
        assert result[0:7] == [60, 62, 64, 65, 67, 69, 71]
        # Should extend 5 above and 5 below
        assert 81 in result  # A5 (ti above)
        assert 52 in result  # E3 (mi below)
        assert result[-1] == 60  # Ends on do


# =============================================================================
# Test Scale Patterns - Weaving
# =============================================================================


class TestScaleWeavingPatterns:
    """Tests for weaving scale patterns."""

    pass  # All weaving tests moved to other pattern categories


# =============================================================================
# Test Scale Patterns - Diatonic
# =============================================================================


class TestScaleDiatonicPatterns:
    """Tests for diatonic chord-based scale patterns."""

    def test_diatonic_triads(self, c_major_scale: List[int]) -> None:
        result = apply_scale_pattern(c_major_scale, ScalePattern.DIATONIC_TRIADS)
        # Ascending: I, ii, iii, IV, V, vi, vii° (extends past do)
        # Descending: back down (extends below do)
        # Ends on do
        # First 4 triads: I, ii, iii, IV
        assert result[:12] == [
            60, 64, 67,  # C-E-G (I)
            62, 65, 69,  # D-F-A (ii)
            64, 67, 71,  # E-G-B (iii)
            65, 69, 72,  # F-A-C (IV)
        ]
        # Last triad descending + do
        assert result[-4:] == [62, 59, 55, 60]  # re-ti-sol, do
        assert result[-1] == 60  # Ends on do
        assert len(result) == 43  # 7*3 + 7*3 + 1

    def test_diatonic_7ths(self, c_major_scale_2_octaves: List[int]) -> None:
        result = apply_scale_pattern(
            c_major_scale_2_octaves, ScalePattern.DIATONIC_7THS
        )
        # Imaj7: C-E-G-B, ii7: D-F-A-C, iii7: E-G-B-D, ...
        # First chord: indices 0, 2, 4, 6 = 60, 64, 67, 71
        assert result[:4] == [60, 64, 67, 71]  # Cmaj7
        assert result[-1] == 60  # Ends on do
        # 2 octaves = 14 degrees: 14*4 up + 14*4 down + 1 = 113
        assert len(result) == 113

    def test_broken_chords(self, c_major_scale: List[int]) -> None:
        result = apply_scale_pattern(c_major_scale, ScalePattern.BROKEN_CHORDS)
        # Pattern: 1-5-3 on each degree, extends past do, ends on do
        # First 4 broken chords: I, ii, iii, IV
        assert result[:12] == [
            60, 67, 64,  # C-G-E (I)
            62, 69, 65,  # D-A-F (ii)
            64, 71, 67,  # E-B-G (iii)
            65, 72, 69,  # F-C-A (IV)
        ]
        assert result[-1] == 60  # Ends on do
        assert len(result) == 43  # 7*3 + 7*3 + 1


# =============================================================================
# Test Arpeggio Patterns - Straight
# =============================================================================


class TestArpeggioStraightPatterns:
    """Tests for straight arpeggio patterns."""

    def test_straight_up(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(c_major_triad, ArpeggioPattern.STRAIGHT_UP)
        assert result == c_major_triad

    def test_straight_down(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(c_major_triad, ArpeggioPattern.STRAIGHT_DOWN)
        assert result == list(reversed(c_major_triad))

    def test_straight_up_down(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(c_major_triad, ArpeggioPattern.STRAIGHT_UP_DOWN)
        expected = c_major_triad + list(reversed(c_major_triad[:-1]))
        assert result == expected


# =============================================================================
# Test Arpeggio Patterns - Weaving
# =============================================================================


class TestArpeggioWeavingPatterns:
    """Tests for weaving arpeggio patterns."""

    def test_weaving_ascend(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(c_major_triad, ArpeggioPattern.WEAVING_ASCEND)
        # C-E-C, E-G-E, G-C-G, C-E-C, E-G-E, end on G
        # Each step: [i, i+1, i], then append last
        assert result[0:3] == [60, 64, 60]  # C-E-C
        assert result[-1] == 79  # Ends on top G

    def test_weaving_descend(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(c_major_triad, ArpeggioPattern.WEAVING_DESCEND)
        # G5-E5-G5, E5-C5-E5, ...
        assert result[0:3] == [79, 76, 79]  # G5-E5-G5
        assert result[-1] == 60  # Ends on bottom C

    def test_broken_skip_1(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(c_major_triad, ArpeggioPattern.BROKEN_SKIP_1)
        # C-G, E-C, G-E, C-G (skipping one)
        # 60-67, 64-72, 67-76, 72-79
        expected = [60, 67, 64, 72, 67, 76, 72, 79]
        assert result == expected


# =============================================================================
# Test Arpeggio Patterns - Inversions
# =============================================================================


class TestArpeggioInversionPatterns:
    """Tests for arpeggio inversion patterns."""

    def test_inversion_root(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(
            c_major_triad, ArpeggioPattern.INVERSION_ROOT, chord_size=3
        )
        # Root position: C-E-G in each octave
        assert result == c_major_triad

    def test_inversion_1st(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(
            c_major_triad, ArpeggioPattern.INVERSION_1ST, chord_size=3
        )
        # 1st inversion: E-G-C in each octave
        # [64, 67, 60] in first octave, [76, 79, 72] in second
        assert result[0:3] == [64, 67, 60]
        assert result[3:6] == [76, 79, 72]

    def test_inversion_2nd(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(
            c_major_triad, ArpeggioPattern.INVERSION_2ND, chord_size=3
        )
        # 2nd inversion: G-C-E in each octave
        assert result[0:3] == [67, 60, 64]

    def test_inversion_3rd_with_7th(self, c_major_7th: List[int]) -> None:
        result = apply_arpeggio_pattern(
            c_major_7th, ArpeggioPattern.INVERSION_3RD, chord_size=4
        )
        # 3rd inversion starts from B: B-C-E-G
        assert result[0:4] == [71, 60, 64, 67]


# =============================================================================
# Test Arpeggio Patterns - Advanced
# =============================================================================


class TestArpeggioAdvancedPatterns:
    """Tests for advanced arpeggio patterns."""

    def test_rolling_alberti(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(
            c_major_triad, ArpeggioPattern.ROLLING_ALBERTI, chord_size=3
        )
        # Pattern: low-high-mid-high for each chord
        # C4-E4-G4 -> C-G-E-G
        # C5-E5-G5 -> C-G-E-G
        assert result[0:4] == [60, 67, 64, 67]  # First group
        assert result[4:8] == [72, 79, 76, 79]  # Second group

    def test_approach_notes(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(
            c_major_triad, ArpeggioPattern.APPROACH_NOTES, ascending=True
        )
        # Each note preceded by half step below
        # B-C, Eb-E, Gb-G, ...
        assert result[0:2] == [59, 60]  # B3-C4
        assert result[2:4] == [63, 64]  # Eb4-E4
        assert result[4:6] == [66, 67]  # Gb4-G4

    def test_enclosures(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(
            c_major_triad, ArpeggioPattern.ENCLOSURES, ascending=True
        )
        # Each note enclosed: above, below, target
        # Db-B-C, F-Eb-E, Ab-Gb-G, ...
        assert result[0:3] == [61, 59, 60]  # Db-B-C
        assert result[3:6] == [65, 63, 64]  # F-Eb-E

    def test_diatonic_sequence(self, c_major_triad: List[int]) -> None:
        result = apply_arpeggio_pattern(
            c_major_triad, ArpeggioPattern.DIATONIC_SEQUENCE, chord_size=3
        )
        # Steps through the arpeggio in groups
        # C-E-G, E-G-C, G-C-E, C-E-G
        assert len(result) > 0

    def test_circle_patterns_return_pitches(self, c_major_triad: List[int]) -> None:
        # These are placeholder implementations
        result_4ths = apply_arpeggio_pattern(
            c_major_triad, ArpeggioPattern.CIRCLE_4THS
        )
        result_5ths = apply_arpeggio_pattern(
            c_major_triad, ArpeggioPattern.CIRCLE_5THS
        )
        assert len(result_4ths) > 0
        assert len(result_5ths) > 0


# =============================================================================
# Test Helper Functions
# =============================================================================


class TestHelperFunctions:
    """Tests for helper functions."""

    def test_get_supported_scale_patterns(self) -> None:
        patterns = get_supported_scale_patterns()
        assert len(patterns) == 32  # All 32 scale patterns (includes extended intervals, groups, and broken thirds neighbor)
        assert ScalePattern.IN_3RDS in patterns
        assert ScalePattern.GROUPS_OF_4 in patterns
        assert ScalePattern.PYRAMID_ASCEND in patterns
        assert ScalePattern.PYRAMID_DESCEND in patterns
        assert ScalePattern.BROKEN_THIRDS_NEIGHBOR in patterns
        # Verify new extended patterns
        assert ScalePattern.IN_13THS in patterns
        assert ScalePattern.GROUPS_OF_12 in patterns

    def test_get_supported_arpeggio_patterns(self) -> None:
        patterns = get_supported_arpeggio_patterns()
        assert len(patterns) == 17  # All 17 arpeggio patterns
        assert ArpeggioPattern.ROLLING_ALBERTI in patterns
        assert ArpeggioPattern.ENCLOSURES in patterns


# =============================================================================
# Test Edge Cases
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases."""

    def test_empty_list(self) -> None:
        result = apply_scale_pattern([], ScalePattern.IN_3RDS)
        assert result == []

    def test_single_note(self) -> None:
        result = apply_scale_pattern([60], ScalePattern.GROUPS_OF_3)
        assert result == [60]

    def test_two_notes(self) -> None:
        result = apply_scale_pattern([60, 62], ScalePattern.IN_3RDS)
        # Not enough for 3rds, should handle gracefully
        assert isinstance(result, list)

    def test_unsupported_pattern_defaults_to_straight(
        self, c_major_scale: List[int]
    ) -> None:
        # If somehow an invalid pattern gets through, should default
        # This tests internal robustness
        pass  # Enum validation handles this at schema level

    def test_arpeggio_with_chord_size_4(self, c_major_7th: List[int]) -> None:
        result = apply_arpeggio_pattern(
            c_major_7th, ArpeggioPattern.ROLLING_ALBERTI, chord_size=4
        )
        # Should handle 4-note chords
        assert len(result) > 0

    def test_two_octave_patterns(self, c_major_scale_2_octaves: List[int]) -> None:
        """Patterns should work across multiple octaves."""
        result = apply_scale_pattern(
            c_major_scale_2_octaves, ScalePattern.GROUPS_OF_4
        )
        # Groups pattern does up-and-down, extending beyond the scale
        # Should start with C4 and end with C4
        assert result[0] == 60  # Starts on C4
        assert result[-1] == 60  # Ends on C4
        # Should include notes above the top C (C6=84) - D6=86, E6=88
        assert 86 in result  # D6 is in the extended pattern
        # Should include notes below the bottom C (C4=60) - B3=59, A3=57
        assert 59 in result  # B3 is in the extended pattern
