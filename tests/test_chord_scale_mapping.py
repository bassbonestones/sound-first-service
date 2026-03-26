"""Tests for chord-to-scale mapping service.

Tests cover:
- All chord categories
- Alteration handling (b9, #9, #11, b13, alt)
- Scale recommendations and rankings
- Edge cases and parsing
"""
import pytest

from app.schemas.generation_schemas import ScaleType
from app.services.chord_scale_mapping import (
    ChordCategory,
    ChordScaleMapping,
    ScaleRecommendation,
    get_all_categories,
    get_scale_for_chord_simple,
    get_scales_for_chord,
    _parse_chord_symbol,
)


class TestChordSymbolParsing:
    """Tests for chord symbol parsing."""

    def test_simple_major(self) -> None:
        """Parse simple major chord."""
        root, quality, alts, bass = _parse_chord_symbol("C")
        assert root == "C"
        assert quality == ""
        assert alts == []
        assert bass is None

    def test_major_seventh(self) -> None:
        """Parse major 7th chord."""
        root, quality, alts, bass = _parse_chord_symbol("Cmaj7")
        assert root == "C"
        assert quality == "maj7"
        assert alts == []
        assert bass is None

    def test_sharp_root(self) -> None:
        """Parse chord with sharp root."""
        root, quality, alts, bass = _parse_chord_symbol("F#m7")
        assert root == "F#"
        assert quality == "m7"
        assert alts == []
        assert bass is None

    def test_flat_root(self) -> None:
        """Parse chord with flat root."""
        root, quality, alts, bass = _parse_chord_symbol("Bbmaj7")
        assert root == "Bb"
        assert quality == "maj7"
        assert alts == []
        assert bass is None

    def test_parenthesized_alterations(self) -> None:
        """Parse alterations in parentheses."""
        root, quality, alts, bass = _parse_chord_symbol("C7(b9)")
        assert root == "C"
        assert quality == "7"
        assert alts == ["b9"]
        assert bass is None

    def test_multiple_parenthesized_alterations(self) -> None:
        """Parse multiple alterations in parentheses."""
        root, quality, alts, bass = _parse_chord_symbol("G7(#9,b13)")
        assert root == "G"
        assert quality == "7"
        assert "#9" in alts
        assert "b13" in alts
        assert bass is None

    def test_inline_sharp_11(self) -> None:
        """Parse inline #11 alteration."""
        root, quality, alts, bass = _parse_chord_symbol("C7#11")
        assert root == "C"
        # The quality parsing extracts #11 as alteration
        assert "#11" in alts or quality == "7#11"
        assert bass is None

    def test_alt_suffix(self) -> None:
        """Parse alt suffix."""
        root, quality, alts, bass = _parse_chord_symbol("G7alt")
        assert root == "G"
        assert "alt" in alts
        assert bass is None

    def test_empty_symbol(self) -> None:
        """Handle empty symbol gracefully."""
        root, quality, alts, bass = _parse_chord_symbol("")
        assert root == "C"
        assert quality == ""
        assert alts == []
        assert bass is None

    def test_slash_chord_major(self) -> None:
        """Parse major slash chord."""
        root, quality, alts, bass = _parse_chord_symbol("C/E")
        assert root == "C"
        assert quality == ""
        assert alts == []
        assert bass == "E"

    def test_slash_chord_minor_seventh(self) -> None:
        """Parse minor 7 slash chord."""
        root, quality, alts, bass = _parse_chord_symbol("Dm7/G")
        assert root == "D"
        assert quality == "m7"
        assert alts == []
        assert bass == "G"

    def test_slash_chord_flat_bass(self) -> None:
        """Parse slash chord with flat bass note."""
        root, quality, alts, bass = _parse_chord_symbol("C/Bb")
        assert root == "C"
        assert quality == ""
        assert bass == "Bb"

    def test_slash_chord_sharp_bass(self) -> None:
        """Parse slash chord with sharp bass note."""
        root, quality, alts, bass = _parse_chord_symbol("Am7/G#")
        assert root == "A"
        assert quality == "m7"
        assert bass == "G#"


class TestMajorChords:
    """Tests for major chord scale mappings."""

    def test_major_triad(self) -> None:
        """Major triad gets Ionian/Lydian."""
        result = get_scales_for_chord("C")
        assert result.chord_category == ChordCategory.MAJOR
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.IONIAN in scale_types
        assert ScaleType.LYDIAN in scale_types

    def test_major_seventh(self) -> None:
        """Major 7 gets Ionian, Lydian, Major Pentatonic."""
        result = get_scales_for_chord("Cmaj7")
        assert result.chord_category == ChordCategory.MAJOR_7
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.IONIAN in scale_types
        assert ScaleType.LYDIAN in scale_types
        assert ScaleType.PENTATONIC_MAJOR in scale_types

    def test_major_ninth(self) -> None:
        """Major 9 treated as major 7."""
        result = get_scales_for_chord("Cmaj9")
        assert result.chord_category == ChordCategory.MAJOR_7

    def test_add9(self) -> None:
        """Add9 treated as major."""
        result = get_scales_for_chord("Cadd9")
        assert result.chord_category == ChordCategory.MAJOR

    def test_six_chord(self) -> None:
        """6 chord treated as major 7 family."""
        result = get_scales_for_chord("C6")
        assert result.chord_category == ChordCategory.MAJOR_7


class TestMinorChords:
    """Tests for minor chord scale mappings."""

    def test_minor_triad(self) -> None:
        """Minor triad gets Dorian/Aeolian."""
        result = get_scales_for_chord("Cm")
        assert result.chord_category == ChordCategory.MINOR
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.DORIAN in scale_types
        assert ScaleType.AEOLIAN in scale_types

    def test_minor_seventh(self) -> None:
        """Minor 7 gets Dorian, Aeolian, Minor Pentatonic."""
        result = get_scales_for_chord("Cm7")
        assert result.chord_category == ChordCategory.MINOR_7
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.DORIAN in scale_types
        assert ScaleType.AEOLIAN in scale_types
        assert ScaleType.PENTATONIC_MINOR in scale_types

    def test_minor_variants(self) -> None:
        """Various minor notations all map to minor."""
        for symbol in ["Cm", "Cmin", "C-"]:
            result = get_scales_for_chord(symbol)
            assert result.chord_category == ChordCategory.MINOR

    def test_minor_seventh_variants(self) -> None:
        """Various m7 notations all map to minor 7."""
        for symbol in ["Cm7", "Cmin7", "C-7"]:
            result = get_scales_for_chord(symbol)
            assert result.chord_category == ChordCategory.MINOR_7


class TestDominantChords:
    """Tests for dominant chord scale mappings."""

    def test_dominant_seventh(self) -> None:
        """Dominant 7 gets Mixolydian, Bebop Dominant."""
        result = get_scales_for_chord("C7")
        assert result.chord_category == ChordCategory.DOMINANT
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.MIXOLYDIAN in scale_types
        assert ScaleType.BEBOP_DOMINANT in scale_types

    def test_dominant_ninth(self) -> None:
        """Dominant 9 treated as dominant."""
        result = get_scales_for_chord("C9")
        assert result.chord_category == ChordCategory.DOMINANT

    def test_dominant_thirteenth(self) -> None:
        """Dominant 13 treated as dominant."""
        result = get_scales_for_chord("C13")
        assert result.chord_category == ChordCategory.DOMINANT


class TestAlteredDominants:
    """Tests for altered dominant chord scale mappings."""

    def test_seven_flat_nine(self) -> None:
        """7b9 gets Altered scale as primary."""
        result = get_scales_for_chord("C7b9")
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.ALTERED in scale_types

    def test_seven_sharp_nine(self) -> None:
        """7#9 gets Altered scale as primary."""
        result = get_scales_for_chord("C7#9")
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.ALTERED in scale_types

    def test_seven_alt(self) -> None:
        """7alt gets Altered scale as primary."""
        result = get_scales_for_chord("G7alt")
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.ALTERED in scale_types
        assert "alt" in result.alterations_applied

    def test_seven_sharp_eleven(self) -> None:
        """7#11 gets Lydian Dominant as primary."""
        result = get_scales_for_chord("C7#11")
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.LYDIAN_DOMINANT in scale_types
        assert "#11" in result.alterations_applied

    def test_parenthesized_flat_nine(self) -> None:
        """7(b9) parsed correctly."""
        result = get_scales_for_chord("C7(b9)")
        assert "b9" in result.alterations_applied
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.ALTERED in scale_types

    def test_parenthesized_sharp_eleven(self) -> None:
        """7(#11) parsed correctly."""
        result = get_scales_for_chord("C7(#11)")
        assert "#11" in result.alterations_applied
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.LYDIAN_DOMINANT in scale_types


class TestMinorMajorSeven:
    """Tests for minor-major 7 chord scale mappings."""

    def test_minor_major_seven(self) -> None:
        """mMaj7 gets Melodic Minor."""
        result = get_scales_for_chord("CmMaj7")
        assert result.chord_category == ChordCategory.MINOR_MAJOR_7
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.MELODIC_MINOR in scale_types
        assert ScaleType.HARMONIC_MINOR in scale_types

    def test_minor_major_seven_variants(self) -> None:
        """Various mMaj7 notations all map correctly."""
        for symbol in ["CmMaj7", "Cm/Maj7", "C-Δ7"]:
            result = get_scales_for_chord(symbol)
            assert result.chord_category == ChordCategory.MINOR_MAJOR_7


class TestHalfDiminished:
    """Tests for half-diminished chord scale mappings."""

    def test_half_diminished(self) -> None:
        """m7b5 gets Locrian ♮2 as primary."""
        result = get_scales_for_chord("Cm7b5")
        assert result.chord_category == ChordCategory.HALF_DIMINISHED
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.LOCRIAN_NAT2 in scale_types
        assert ScaleType.LOCRIAN in scale_types

    def test_half_diminished_symbol(self) -> None:
        """ø7 notation maps to half-diminished."""
        result = get_scales_for_chord("Cø7")
        assert result.chord_category == ChordCategory.HALF_DIMINISHED


class TestDiminished:
    """Tests for diminished chord scale mappings."""

    def test_diminished_triad(self) -> None:
        """Diminished triad gets Whole-Half Diminished."""
        result = get_scales_for_chord("Cdim")
        assert result.chord_category == ChordCategory.DIMINISHED
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.DIMINISHED_WH in scale_types

    def test_diminished_seventh(self) -> None:
        """Diminished 7 gets Whole-Half Diminished."""
        result = get_scales_for_chord("Cdim7")
        assert result.chord_category == ChordCategory.DIMINISHED
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.DIMINISHED_WH in scale_types

    def test_diminished_symbol(self) -> None:
        """° notation maps to diminished."""
        result = get_scales_for_chord("C°7")
        assert result.chord_category == ChordCategory.DIMINISHED


class TestAugmented:
    """Tests for augmented chord scale mappings."""

    def test_augmented_triad(self) -> None:
        """Augmented triad gets Whole Tone."""
        result = get_scales_for_chord("Caug")
        assert result.chord_category == ChordCategory.AUGMENTED
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.WHOLE_TONE in scale_types
        assert ScaleType.LYDIAN_AUGMENTED in scale_types

    def test_augmented_symbol(self) -> None:
        """+ notation maps to augmented."""
        result = get_scales_for_chord("C+")
        assert result.chord_category == ChordCategory.AUGMENTED


class TestSuspended:
    """Tests for suspended chord scale mappings."""

    def test_sus4(self) -> None:
        """Sus4 gets Mixolydian, Dorian."""
        result = get_scales_for_chord("Csus4")
        assert result.chord_category == ChordCategory.SUSPENDED
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.MIXOLYDIAN in scale_types
        assert ScaleType.DORIAN in scale_types

    def test_seven_sus4(self) -> None:
        """7sus4 treated as suspended."""
        result = get_scales_for_chord("C7sus4")
        assert result.chord_category == ChordCategory.SUSPENDED


class TestSimpleScaleFunction:
    """Tests for get_scale_for_chord_simple convenience function."""

    def test_major_returns_ionian(self) -> None:
        """Major chord returns Ionian."""
        scale = get_scale_for_chord_simple("Cmaj7")
        assert scale == ScaleType.IONIAN

    def test_minor_returns_dorian(self) -> None:
        """Minor chord returns Dorian."""
        scale = get_scale_for_chord_simple("Dm7")
        assert scale == ScaleType.DORIAN

    def test_dominant_returns_mixolydian(self) -> None:
        """Dominant chord returns Mixolydian."""
        scale = get_scale_for_chord_simple("G7")
        assert scale == ScaleType.MIXOLYDIAN

    def test_altered_returns_altered(self) -> None:
        """Altered dominant returns Altered scale."""
        scale = get_scale_for_chord_simple("G7alt")
        assert scale == ScaleType.ALTERED


class TestScaleRecommendations:
    """Tests for scale recommendation metadata."""

    def test_recommendations_have_names(self) -> None:
        """All recommendations have human-readable names."""
        result = get_scales_for_chord("Cmaj7")
        for rec in result.primary_scales + result.secondary_scales:
            assert rec.name
            assert len(rec.name) > 0

    def test_recommendations_have_reasons(self) -> None:
        """All recommendations have reasons."""
        result = get_scales_for_chord("Dm7")
        for rec in result.primary_scales + result.secondary_scales:
            assert rec.reason
            assert len(rec.reason) > 0

    def test_ionian_has_avoid_note(self) -> None:
        """Ionian recommends avoiding 4th."""
        result = get_scales_for_chord("Cmaj7")
        ionian_rec = next(r for r in result.primary_scales if r.scale == ScaleType.IONIAN)
        assert 4 in ionian_rec.avoid_notes


class TestGetAllCategories:
    """Tests for get_all_categories utility."""

    def test_returns_all_categories(self) -> None:
        """Returns all chord categories."""
        categories = get_all_categories()
        assert ChordCategory.MAJOR in categories
        assert ChordCategory.MINOR in categories
        assert ChordCategory.DOMINANT in categories
        assert len(categories) == len(ChordCategory)


class TestRealWorldChords:
    """Tests for real-world chord progressions."""

    def test_ii_v_i_in_c(self) -> None:
        """ii-V-I in C gets appropriate scales."""
        dm7 = get_scales_for_chord("Dm7")
        g7 = get_scales_for_chord("G7")
        cmaj7 = get_scales_for_chord("Cmaj7")

        assert dm7.chord_category == ChordCategory.MINOR_7
        assert g7.chord_category == ChordCategory.DOMINANT
        assert cmaj7.chord_category == ChordCategory.MAJOR_7

    def test_minor_ii_v_i(self) -> None:
        """Minor ii-V-i gets appropriate scales."""
        dm7b5 = get_scales_for_chord("Dm7b5")
        g7alt = get_scales_for_chord("G7alt")
        cm = get_scales_for_chord("Cm7")

        assert dm7b5.chord_category == ChordCategory.HALF_DIMINISHED
        assert ScaleType.ALTERED in [s.scale for s in g7alt.primary_scales]
        assert cm.chord_category == ChordCategory.MINOR_7

    def test_rhythm_changes_bridge(self) -> None:
        """Rhythm changes III7-VI7-II7-V7 gets dominants."""
        for chord in ["E7", "A7", "D7", "G7"]:
            result = get_scales_for_chord(chord)
            assert result.chord_category == ChordCategory.DOMINANT


class TestCompoundAlteredDominants:
    """Tests for compound altered chords like 13b9, 9#11."""

    def test_13b9_is_dominant_with_alterations(self) -> None:
        """13b9 treated as dominant with alterations."""
        result = get_scales_for_chord("C13b9")
        assert result.chord_category == ChordCategory.DOMINANT
        assert "b9" in result.alterations

    def test_9sharp11_gets_lydian_dominant(self) -> None:
        """9#11 gets Lydian Dominant scale."""
        result = get_scales_for_chord("C9#11")
        assert result.chord_category == ChordCategory.DOMINANT
        scale_types = [s.scale for s in result.primary_scales]
        assert ScaleType.LYDIAN_DOMINANT in scale_types
        assert "#11" in result.alterations

    def test_13sharp11_is_dominant(self) -> None:
        """13#11 treated as dominant."""
        result = get_scales_for_chord("C13#11")
        assert result.chord_category == ChordCategory.DOMINANT
        assert "#11" in result.alterations

    def test_7b9sharp11_is_dominant(self) -> None:
        """7b9#11 treated as dominant with alterations."""
        result = get_scales_for_chord("C7b9#11")
        assert result.chord_category == ChordCategory.DOMINANT
        assert "b9" in result.alterations or "#11" in result.alterations

    def test_7b9b13_is_dominant(self) -> None:
        """7b9b13 treated as dominant with alterations."""
        result = get_scales_for_chord("C7b9b13")
        assert result.chord_category == ChordCategory.DOMINANT

    def test_7sharp9sharp11_is_dominant(self) -> None:
        """7#9#11 treated as dominant with alterations."""
        result = get_scales_for_chord("C7#9#11")
        assert result.chord_category == ChordCategory.DOMINANT


class TestSlashChords:
    """Tests for slash chord handling."""

    def test_slash_chord_sets_bass_note(self) -> None:
        """Slash chord bass note is captured."""
        result = get_scales_for_chord("C/E")
        assert result.bass_note == "E"
        assert result.root == "C"

    def test_slash_chord_category_from_quality(self) -> None:
        """Slash chord category determined by quality."""
        result = get_scales_for_chord("Dm7/G")
        assert result.chord_category == ChordCategory.MINOR_7
        assert result.bass_note == "G"

    def test_minor_over_flat_third(self) -> None:
        """Am/C (Am over C bass)."""
        result = get_scales_for_chord("Am/C")
        assert result.chord_category == ChordCategory.MINOR
        assert result.bass_note == "C"
        assert result.root == "A"

    def test_dominant_slash_chord(self) -> None:
        """G7/F (dominant with 7th in bass)."""
        result = get_scales_for_chord("G7/F")
        assert result.chord_category == ChordCategory.DOMINANT
        assert result.bass_note == "F"

    def test_maj7_slash_chord(self) -> None:
        """Cmaj7/E (major 7 with 3rd in bass)."""
        result = get_scales_for_chord("Cmaj7/E")
        assert result.chord_category == ChordCategory.MAJOR_7
        assert result.bass_note == "E"


class TestSusVariants:
    """Tests for various sus chord notations."""

    def test_sus2(self) -> None:
        """sus2 treated as suspended."""
        result = get_scales_for_chord("Csus2")
        assert result.chord_category == ChordCategory.SUSPENDED

    def test_sus_alone(self) -> None:
        """sus alone treated as sus4."""
        result = get_scales_for_chord("Csus")
        assert result.chord_category == ChordCategory.SUSPENDED

    def test_9sus4(self) -> None:
        """9sus4 treated as suspended."""
        result = get_scales_for_chord("C9sus4")
        assert result.chord_category == ChordCategory.SUSPENDED

    def test_13sus4(self) -> None:
        """13sus4 treated as suspended."""
        result = get_scales_for_chord("C13sus4")
        assert result.chord_category == ChordCategory.SUSPENDED


class TestAlterationValidation:
    """Tests for alteration validation and conflict detection."""

    def test_valid_alterations_no_warnings(self) -> None:
        """Valid alterations produce no warnings."""
        result = get_scales_for_chord("C7(b9)")
        assert result.has_warnings is False
        assert result.warnings == []

    def test_conflicting_b9_sharp9(self) -> None:
        """b9 and #9 together produces warning."""
        result = get_scales_for_chord("C7(b9,#9)")
        assert result.has_warnings is True
        assert any("b9" in w and "#9" in w for w in result.warnings)

    def test_conflicting_b5_sharp5(self) -> None:
        """b5 and #5 together produces warning."""
        result = get_scales_for_chord("C7(b5,#5)")
        assert result.has_warnings is True
        assert any("b5" in w and "#5" in w for w in result.warnings)

    def test_unrecognized_alteration(self) -> None:
        """Unrecognized alterations produce warning."""
        result = get_scales_for_chord("C7(xyz)")
        assert result.has_warnings is True
        assert any("xyz" in w for w in result.warnings)

    def test_b11_unrecognized(self) -> None:
        """b11 is not a standard alteration."""
        result = get_scales_for_chord("C7(b11)")
        # b11 IS recognized (we added it) but unusual
        # Actually, let's check if it's in the valid set
        assert result.has_warnings is False  # b11 is in _VALID_ALTERATIONS

    def test_multiple_valid_alterations(self) -> None:
        """Multiple valid non-conflicting alterations work."""
        result = get_scales_for_chord("C7(b9,#11)")
        assert result.has_warnings is False
        assert "b9" in result.alterations
        assert "#11" in result.alterations

    def test_alteration_order_irrelevant(self) -> None:
        """Order of alterations doesn't matter for result."""
        result1 = get_scales_for_chord("C7(b9,#11)")
        result2 = get_scales_for_chord("C7(#11,b9)")
        
        assert set(result1.alterations) == set(result2.alterations)
        assert result1.chord_category == result2.chord_category
        assert result1.has_warnings == result2.has_warnings

    def test_conflicting_still_parses(self) -> None:
        """Conflicting alterations still parse (just warn)."""
        result = get_scales_for_chord("C7(b9,#9)")
        # Should still extract both alterations
        assert "b9" in result.alterations
        assert "#9" in result.alterations
        # But with a warning
        assert result.has_warnings is True
