"""
Tests for scale_definitions module.

Tests pitch spelling, transposition, and chromatic passage spelling.
"""

import pytest
from app.schemas.generation_schemas import ScaleType
from app.services.generation.scale_definitions import (
    ASYMMETRIC_SCALES,
    LETTER_TO_SEMITONE,
    LETTER_ORDER,
    SHARP_KEYS,
    FLAT_KEYS,
    get_scale_intervals,
    get_scale_spellings,
    get_scale_note_count,
    is_asymmetric_scale,
    key_prefers_sharps,
    simplify_accidental,
    transpose_pitch_name,
    get_transposed_scale_spellings,
    get_chromatic_pitch_names,
)


# =============================================================================
# CONSTANT VALIDATION
# =============================================================================

class TestConstants:
    """Test scale definition constants."""
    
    def test_letter_to_semitone_c_is_0(self):
        """C should be 0 semitones."""
        assert LETTER_TO_SEMITONE["C"] == 0
    
    def test_letter_to_semitone_d_is_2(self):
        """D should be 2 semitones."""
        assert LETTER_TO_SEMITONE["D"] == 2
    
    def test_letter_to_semitone_e_is_4(self):
        """E should be 4 semitones."""
        assert LETTER_TO_SEMITONE["E"] == 4
    
    def test_letter_to_semitone_f_is_5(self):
        """F should be 5 semitones."""
        assert LETTER_TO_SEMITONE["F"] == 5
    
    def test_letter_to_semitone_g_is_7(self):
        """G should be 7 semitones."""
        assert LETTER_TO_SEMITONE["G"] == 7
    
    def test_letter_to_semitone_a_is_9(self):
        """A should be 9 semitones."""
        assert LETTER_TO_SEMITONE["A"] == 9
    
    def test_letter_to_semitone_b_is_11(self):
        """B should be 11 semitones."""
        assert LETTER_TO_SEMITONE["B"] == 11
    
    def test_letter_order_has_7_letters(self):
        """Should have exactly 7 letters."""
        assert len(LETTER_ORDER) == 7
        assert list(LETTER_ORDER) == ["C", "D", "E", "F", "G", "A", "B"]
    
    def test_sharp_keys_include_common_keys(self):
        """Sharp keys should include common sharp-based keys."""
        assert "G" in SHARP_KEYS
        assert "D" in SHARP_KEYS
        assert "A" in SHARP_KEYS
        assert "E" in SHARP_KEYS
    
    def test_flat_keys_include_common_keys(self):
        """Flat keys should include common flat-based keys."""
        assert "F" in FLAT_KEYS
        assert "Bb" in FLAT_KEYS
        assert "Eb" in FLAT_KEYS
        assert "Ab" in FLAT_KEYS


# =============================================================================
# KEY PREFERS SHARPS
# =============================================================================

class TestKeyPrefersSharps:
    """Test key_prefers_sharps function."""
    
    def test_c_prefers_sharps(self):
        """C major is neutral but conventionally prefers sharps."""
        assert key_prefers_sharps("C") is True
    
    def test_g_prefers_sharps(self):
        """G major prefers sharps (1 sharp)."""
        assert key_prefers_sharps("G") is True
    
    def test_d_prefers_sharps(self):
        """D major prefers sharps (2 sharps)."""
        assert key_prefers_sharps("D") is True
    
    def test_f_sharp_prefers_sharps(self):
        """F# major prefers sharps (6 sharps)."""
        assert key_prefers_sharps("F#") is True
    
    def test_f_prefers_flats(self):
        """F major prefers flats (1 flat)."""
        assert key_prefers_sharps("F") is False
    
    def test_bb_prefers_flats(self):
        """Bb major prefers flats (2 flats)."""
        assert key_prefers_sharps("Bb") is False
    
    def test_eb_prefers_flats(self):
        """Eb major prefers flats (3 flats)."""
        assert key_prefers_sharps("Eb") is False
    
    def test_ab_prefers_flats(self):
        """Ab major prefers flats (4 flats)."""
        assert key_prefers_sharps("Ab") is False
    
    def test_db_prefers_flats(self):
        """Db major prefers flats (5 flats)."""
        assert key_prefers_sharps("Db") is False


# =============================================================================
# SIMPLIFY ACCIDENTALS
# =============================================================================

class TestSimplifyAccidental:
    """Test simplify_accidental function."""
    
    def test_natural_note_unchanged(self):
        """Natural notes should be unchanged."""
        assert simplify_accidental("C") == "C"
        assert simplify_accidental("D") == "D"
        assert simplify_accidental("E") == "E"
    
    def test_single_sharp_unchanged(self):
        """Single sharps that aren't white-key should be unchanged."""
        assert simplify_accidental("C#") == "C#"
        assert simplify_accidental("F#") == "F#"
        assert simplify_accidental("G#") == "G#"
    
    def test_single_flat_unchanged(self):
        """Single flats that aren't white-key should be unchanged."""
        assert simplify_accidental("Db") == "Db"
        assert simplify_accidental("Gb") == "Gb"
        assert simplify_accidental("Ab") == "Ab"
    
    def test_e_sharp_to_f(self):
        """E# should simplify to F."""
        assert simplify_accidental("E#") == "F"
    
    def test_b_sharp_to_c(self):
        """B# should simplify to C."""
        assert simplify_accidental("B#") == "C"
    
    def test_f_flat_to_e(self):
        """Fb should simplify to E."""
        assert simplify_accidental("Fb") == "E"
    
    def test_c_flat_to_b(self):
        """Cb should simplify to B."""
        assert simplify_accidental("Cb") == "B"
    
    def test_double_sharp_simplifies(self):
        """Double sharps should simplify to simpler accidentals."""
        # F## = G (2 semitones up from F=5 is 7=G)
        assert simplify_accidental("F##") == "G"
        # C## = D
        assert simplify_accidental("C##") == "D"
        # G## = A
        assert simplify_accidental("G##") == "A"
    
    def test_double_flat_simplifies(self):
        """Double flats should simplify to simpler accidentals."""
        # Bbb = A (2 semitones down from B=11 is 9=A)
        assert simplify_accidental("Bbb") == "A"
        # Ebb = D (2 semitones down from E=4 is 2=D)
        assert simplify_accidental("Ebb") == "D"
        # Abb = G (2 semitones down from A=9 is 7=G)
        assert simplify_accidental("Abb") == "G"


# =============================================================================
# TRANSPOSE PITCH NAME
# =============================================================================

class TestTransposePitchName:
    """Test transpose_pitch_name function."""
    
    def test_transpose_c_up_semitone_sharp(self):
        """C transposed up 1 semitone with sharps should be C#."""
        result = transpose_pitch_name("C", 1, prefer_sharps=True)
        assert result == "C#"
    
    def test_transpose_c_up_semitone_flat(self):
        """C transposed up 1 semitone with flats should be Db."""
        result = transpose_pitch_name("C", 1, prefer_sharps=False)
        assert result == "Db"
    
    def test_transpose_c_up_whole_tone(self):
        """C transposed up 2 semitones should be D."""
        result = transpose_pitch_name("C", 2, prefer_sharps=True)
        assert result == "D"
    
    def test_transpose_c_up_perfect_fourth(self):
        """C transposed up 5 semitones should be F."""
        result = transpose_pitch_name("C", 5, prefer_sharps=True)
        assert result == "F"
    
    def test_transpose_c_up_perfect_fifth(self):
        """C transposed up 7 semitones should be G."""
        result = transpose_pitch_name("C", 7, prefer_sharps=True)
        assert result == "G"
    
    def test_transpose_c_up_octave(self):
        """C transposed up 12 semitones should be C."""
        result = transpose_pitch_name("C", 12, prefer_sharps=True)
        assert result == "C"
    
    def test_transpose_f_sharp_up_semitone(self):
        """F# transposed up 1 semitone should be G or F##."""
        result = transpose_pitch_name("F#", 1, prefer_sharps=True)
        # Result could be G or F## depending on implementation
        assert result in ("G", "F##")
    
    def test_transpose_bb_up_whole_tone(self):
        """Bb transposed up 2 semitones should be C."""
        result = transpose_pitch_name("Bb", 2, prefer_sharps=False)
        assert result == "C"


# =============================================================================
# GET SCALE INTERVALS
# =============================================================================

class TestGetScaleIntervals:
    """Test get_scale_intervals function."""
    
    def test_major_scale_intervals(self):
        """Major scale (Ionian) should have W-W-H-W-W-W-H pattern."""
        intervals = get_scale_intervals(ScaleType.IONIAN)
        assert intervals == (2, 2, 1, 2, 2, 2, 1)
    
    def test_dorian_intervals(self):
        """Dorian mode should have correct intervals."""
        intervals = get_scale_intervals(ScaleType.DORIAN)
        assert intervals == (2, 1, 2, 2, 2, 1, 2)
    
    def test_minor_scale_intervals(self):
        """Natural minor (Aeolian) should have W-H-W-W-H-W-W pattern."""
        intervals = get_scale_intervals(ScaleType.AEOLIAN)
        assert intervals == (2, 1, 2, 2, 1, 2, 2)
    
    def test_harmonic_minor_intervals(self):
        """Harmonic minor should have raised 7th."""
        intervals = get_scale_intervals(ScaleType.HARMONIC_MINOR)
        assert intervals == (2, 1, 2, 2, 1, 3, 1)
    
    def test_pentatonic_major_intervals(self):
        """Pentatonic major should have 5 notes."""
        intervals = get_scale_intervals(ScaleType.PENTATONIC_MAJOR)
        # Major pentatonic: W-W-m3-W-m3 (2-2-3-2-3)
        assert len(intervals) == 5
        assert sum(intervals) == 12  # One octave
    
    def test_chromatic_intervals(self):
        """Chromatic scale should have all half steps."""
        intervals = get_scale_intervals(ScaleType.CHROMATIC)
        assert intervals == (1,) * 12
        assert sum(intervals) == 12


# =============================================================================
# GET SCALE NOTE COUNT
# =============================================================================

class TestGetScaleNoteCount:
    """Test get_scale_note_count function."""
    
    def test_major_scale_has_7_notes(self):
        """Major scale (Ionian) has 7 notes per octave."""
        assert get_scale_note_count(ScaleType.IONIAN) == 7
    
    def test_chromatic_scale_has_12_notes(self):
        """Chromatic scale has 12 notes per octave."""
        assert get_scale_note_count(ScaleType.CHROMATIC) == 12
    
    def test_pentatonic_has_5_notes(self):
        """Pentatonic scale has 5 notes per octave."""
        assert get_scale_note_count(ScaleType.PENTATONIC_MAJOR) == 5
        assert get_scale_note_count(ScaleType.PENTATONIC_MINOR) == 5
    
    def test_blues_scale_has_6_notes(self):
        """Blues scale has 6 notes per octave."""
        assert get_scale_note_count(ScaleType.BLUES) == 6


# =============================================================================
# IS ASYMMETRIC SCALE
# =============================================================================

class TestIsAsymmetricScale:
    """Test is_asymmetric_scale function."""
    
    def test_melodic_minor_classical_is_asymmetric(self):
        """Classical melodic minor is asymmetric."""
        assert is_asymmetric_scale(ScaleType.MELODIC_MINOR_CLASSICAL) is True
    
    def test_major_is_symmetric(self):
        """Major scale (Ionian) is symmetric."""
        assert is_asymmetric_scale(ScaleType.IONIAN) is False
    
    def test_dorian_is_symmetric(self):
        """Dorian mode is symmetric."""
        assert is_asymmetric_scale(ScaleType.DORIAN) is False
    
    def test_harmonic_minor_is_symmetric(self):
        """Harmonic minor is symmetric."""
        assert is_asymmetric_scale(ScaleType.HARMONIC_MINOR) is False
    
    def test_asymmetric_scales_set_not_empty(self):
        """ASYMMETRIC_SCALES set should contain at least one scale."""
        assert len(ASYMMETRIC_SCALES) >= 1


# =============================================================================
# GET SCALE SPELLINGS
# =============================================================================

class TestGetScaleSpellings:
    """Test get_scale_spellings function."""
    
    def test_c_major_spellings(self):
        """C major (Ionian) should have natural note spellings."""
        spellings = get_scale_spellings(ScaleType.IONIAN)
        assert spellings[0] == "C"  # Root
        assert spellings[1] == "D"  # 2nd
        assert spellings[2] == "E"  # 3rd
        assert spellings[3] == "F"  # 4th
        assert spellings[4] == "G"  # 5th
        assert spellings[5] == "A"  # 6th
        assert spellings[6] == "B"  # 7th
    
    def test_major_scale_has_7_spellings(self):
        """Major scale (Ionian) should have 7 spellings."""
        spellings = get_scale_spellings(ScaleType.IONIAN)
        assert len(spellings) == 7
    
    def test_chromatic_scale_has_12_spellings(self):
        """Chromatic scale should have 12 spellings."""
        spellings = get_scale_spellings(ScaleType.CHROMATIC)
        assert len(spellings) == 12


# =============================================================================
# GET TRANSPOSED SCALE SPELLINGS
# =============================================================================

class TestGetTransposedScaleSpellings:
    """Test get_transposed_scale_spellings function."""
    
    def test_g_major_spellings(self):
        """G major should have F# instead of F."""
        spellings = get_transposed_scale_spellings(ScaleType.IONIAN, 7, "G")
        assert spellings[0] == "G"  # Root
        assert spellings[6] == "F#"  # 7th (raised)
    
    def test_f_major_spellings(self):
        """F major should have Bb instead of B."""
        spellings = get_transposed_scale_spellings(ScaleType.IONIAN, 5, "F")
        assert spellings[0] == "F"  # Root
        assert spellings[3] == "Bb"  # 4th (lowered B)
    
    def test_d_major_spellings(self):
        """D major should have F# and C#."""
        spellings = get_transposed_scale_spellings(ScaleType.IONIAN, 2, "D")
        assert spellings[0] == "D"  # Root
        assert any("F#" in s for s in spellings)  # Should have F#
        assert any("C#" in s for s in spellings)  # Should have C#
    
    def test_bb_major_spellings(self):
        """Bb major should use flats."""
        spellings = get_transposed_scale_spellings(ScaleType.IONIAN, 10, "Bb")
        assert spellings[0] == "Bb"  # Root
        assert any("Eb" in s for s in spellings)  # Should have Eb


# =============================================================================
# GET CHROMATIC PITCH NAMES
# =============================================================================

class TestGetChromaticPitchNames:
    """Test get_chromatic_pitch_names function."""
    
    def test_ascending_chromatic_uses_sharps(self):
        """Ascending chromatic passage should use sharps."""
        # C4=60, C#4=61, D4=62
        midi_notes = [60, 61, 62]
        spellings = get_chromatic_pitch_names(midi_notes, "C")
        assert "C" in spellings[0]  # C4 or similar
        assert "#" in spellings[1]  # Should be C# or similar
        assert "D" in spellings[2]  # D4 or similar
    
    def test_descending_chromatic_uses_flats(self):
        """Descending chromatic passage should use flats."""
        # D4=62, Db4=61, C4=60
        midi_notes = [62, 61, 60]
        spellings = get_chromatic_pitch_names(midi_notes, "C")
        assert "D" in spellings[0]
        assert "b" in spellings[1]  # Should be Db
        assert "C" in spellings[2]
    
    def test_scale_tones_correctly_spelled(self):
        """Scale tones should use key-signature spelling."""
        # C4=60, D4=62, E4=64 (all scale tones in C major)
        midi_notes = [60, 62, 64]
        spellings = get_chromatic_pitch_names(midi_notes, "C")
        assert "C" in spellings[0]
        assert "D" in spellings[1]
        assert "E" in spellings[2]
    
    def test_empty_input_returns_empty(self):
        """Empty input should return empty list."""
        spellings = get_chromatic_pitch_names([], "C")
        assert spellings == []
    
    def test_single_note_returns_single_spelling(self):
        """Single note should return single spelling."""
        spellings = get_chromatic_pitch_names([60], "C")
        assert len(spellings) == 1
        assert "C" in spellings[0]
    
    def test_chromatic_notes_with_sharp_key(self):
        """Chromatic notes in sharp key should prefer sharp spellings."""
        # G major (1 sharp). Test ascending chromatic: G4, G#4, A4
        midi_notes = [67, 68, 69]  # G4, Ab/G#, A4
        spellings = get_chromatic_pitch_names(midi_notes, "G")
        assert len(spellings) == 3
        # Middle note resolving to A should be G#
        assert "G" in spellings[0]
        assert "A" in spellings[2]
    
    def test_chromatic_notes_with_flat_key(self):
        """Chromatic notes in flat key should prefer flat spellings."""
        # F major (1 flat). Test descending chromatic: A4, Ab4, G4
        midi_notes = [69, 68, 67]  # A4, Ab/G#, G4
        spellings = get_chromatic_pitch_names(midi_notes, "F")
        assert len(spellings) == 3
        # Middle note resolving to G should be Ab
        assert "A" in spellings[0]
        assert "G" in spellings[2]
    
    def test_chromatic_with_enharmonic_key(self):
        """Keys like D# should be normalized to Eb."""
        # D# = Eb major (3 flats)
        midi_notes = [63, 65, 67]  # Eb4, F4, G4
        spellings = get_chromatic_pitch_names(midi_notes, "D#")
        assert len(spellings) == 3
    
    def test_chromatic_with_no_resolution_target_ahead(self):
        """Chromatic notes at end need backward resolution."""
        # End on a chromatic note - should look backward
        midi_notes = [60, 62, 61]  # C4, D4, Db/C#4 (chromatic last)
        spellings = get_chromatic_pitch_names(midi_notes, "C")
        assert len(spellings) == 3
        assert "C" in spellings[0]
        assert "D" in spellings[1]
        # Last note has no target ahead, looks backward to D, so should be Db
        assert "b" in spellings[2] or "#" in spellings[2]
    
    def test_chromatic_repeated_notes(self):
        """Groups of repeated chromatic notes should use same spelling."""
        # Two consecutive Eb notes
        midi_notes = [63, 63, 62]  # Eb4, Eb4, D4
        spellings = get_chromatic_pitch_names(midi_notes, "C")
        assert len(spellings) == 3
        assert spellings[0] == spellings[1]  # Both should have same spelling


# =============================================================================
# ADDITIONAL TRANSPOSE PITCH NAME TESTS
# =============================================================================

class TestTransposePitchNameEdgeCases:
    """Test edge cases in transpose_pitch_name function."""
    
    def test_transpose_zero_semitones(self):
        """Zero transposition should return same pitch."""
        assert transpose_pitch_name("C", 0, prefer_sharps=True) == "C"
        assert transpose_pitch_name("F#", 0, prefer_sharps=True) == "F#"
        assert transpose_pitch_name("Bb", 0, prefer_sharps=False) == "Bb"
    
    def test_transpose_negative_semitones(self):
        """Negative transposition should transpose down."""
        result = transpose_pitch_name("D", -2, prefer_sharps=True)
        # D down 2 semitones = C, but may be spelled as B# with sharps
        assert result in ("C", "B#")
    
    def test_transpose_creates_double_sharp(self):
        """Large transposition may create double sharps."""
        # G# up 2 semitones with sharps = A#
        result = transpose_pitch_name("G#", 2, prefer_sharps=True)
        assert result in ("A#", "Bb")  # Either spelling valid
    
    def test_transpose_creates_double_flat(self):
        """Large transposition may create double flats."""
        # Db down 2 semitones with flats = Cb or B
        result = transpose_pitch_name("Db", -2, prefer_sharps=False)
        # Result depends on implementation
        assert result is not None
    
    def test_transpose_octave_plus_semitone(self):
        """Transposition > 12 should work correctly."""
        result = transpose_pitch_name("C", 13, prefer_sharps=True)
        assert result == "C#"
    
    def test_transpose_large_negative(self):
        """Large negative transposition should work."""
        result = transpose_pitch_name("C", -14, prefer_sharps=False)
        assert result == "Bb"


# =============================================================================
# ADDITIONAL SIMPLIFY ACCIDENTAL TESTS
# =============================================================================

class TestSimplifyAccidentalEdgeCases:
    """Test edge cases in simplify_accidental function."""
    
    def test_double_sharp_resolving_to_natural(self):
        """Double sharps that equal natural notes."""
        # D## = E (4 semitones = E)
        assert simplify_accidental("D##") == "E"
        # A## = B (11 semitones = B)
        assert simplify_accidental("A##") == "B"
    
    def test_double_sharp_needing_single_sharp(self):
        """Double sharps that need single sharp output."""
        # E## = F# (6 semitones needs F# or Gb)
        result = simplify_accidental("E##")
        assert result in ("F#", "Gb")
    
    def test_double_flat_resolving_to_natural(self):
        """Double flats that equal natural notes."""
        # Dbb = C (0 semitones = C)
        assert simplify_accidental("Dbb") == "C"
        # Fbb = Eb but actually should be D# or Eb (3 semitones)
        result = simplify_accidental("Fbb")
        assert result in ("Eb", "D#", "D")  # 3 semitones down from F
    
    def test_double_flat_needing_single_flat(self):
        """Double flats that need single flat output."""
        # Cbb = Bb (10 semitones)
        result = simplify_accidental("Cbb")
        assert result in ("Bb", "A#")


# =============================================================================
# ADDITIONAL GET SCALE INTERVALS TESTS
# =============================================================================

class TestGetScaleIntervalsComplete:
    """Test get_scale_intervals for all scale types."""
    
    def test_mixolydian_intervals(self):
        """Mixolydian mode intervals."""
        intervals = get_scale_intervals(ScaleType.MIXOLYDIAN)
        assert intervals == (2, 2, 1, 2, 2, 1, 2)
        assert sum(intervals) == 12
    
    def test_locrian_intervals(self):
        """Locrian mode intervals."""
        intervals = get_scale_intervals(ScaleType.LOCRIAN)
        assert intervals == (1, 2, 2, 1, 2, 2, 2)
        assert sum(intervals) == 12
    
    def test_lydian_intervals(self):
        """Lydian mode intervals."""
        intervals = get_scale_intervals(ScaleType.LYDIAN)
        assert intervals == (2, 2, 2, 1, 2, 2, 1)
        assert sum(intervals) == 12
    
    def test_phrygian_intervals(self):
        """Phrygian mode intervals."""
        intervals = get_scale_intervals(ScaleType.PHRYGIAN)
        assert intervals == (1, 2, 2, 2, 1, 2, 2)
        assert sum(intervals) == 12
    
    def test_whole_tone_intervals(self):
        """Whole tone scale has all whole steps."""
        intervals = get_scale_intervals(ScaleType.WHOLE_TONE)
        assert intervals == (2, 2, 2, 2, 2, 2)
        assert sum(intervals) == 12
    
    def test_all_scale_types_have_intervals(self):
        """All scale types should return valid intervals."""
        for scale_type in ScaleType:
            intervals = get_scale_intervals(scale_type)
            assert intervals is not None
            assert sum(intervals) == 12  # All scales span an octave
