"""Tests for enharmonic_spelling module.

Tests the KEY_ALTERATION_MAP and related functions for 
correct enharmonic pitch spelling in all keys.
"""

import pytest

from app.services.generation.enharmonic_spelling import (
    Accidental,
    SpellingEntry,
    KEY_ALTERATION_MAP,
    key_to_fifths,
    key_to_semitone,
    get_scale_degree_pitches,
    get_scale_degree_and_alteration,
    get_spelling_from_map,
    midi_to_pitch_name_in_key,
    spelling_to_pitch_name,
)


class TestKeyToFifths:
    """Test key_to_fifths conversion."""
    
    def test_c_major_is_zero(self):
        """C major has 0 sharps/flats."""
        assert key_to_fifths("C") == 0
    
    def test_sharp_keys(self):
        """Sharp keys have positive fifths."""
        assert key_to_fifths("G") == 1
        assert key_to_fifths("D") == 2
        assert key_to_fifths("A") == 3
        assert key_to_fifths("E") == 4
        assert key_to_fifths("B") == 5
        assert key_to_fifths("F#") == 6
        assert key_to_fifths("C#") == 7
    
    def test_flat_keys(self):
        """Flat keys have negative fifths."""
        assert key_to_fifths("F") == -1
        assert key_to_fifths("Bb") == -2
        assert key_to_fifths("Eb") == -3
        assert key_to_fifths("Ab") == -4
        assert key_to_fifths("Db") == -5
        assert key_to_fifths("Gb") == -6
    
    def test_invalid_key_raises(self):
        """Unknown key should raise ValueError."""
        with pytest.raises(ValueError, match="Unknown key"):
            key_to_fifths("X")


class TestKeyToSemitone:
    """Test key_to_semitone conversion."""
    
    def test_c_major_root(self):
        """C major root is pitch class 0."""
        assert key_to_semitone(0) == 0
    
    def test_g_major_root(self):
        """G major root is pitch class 7."""
        assert key_to_semitone(1) == 7
    
    def test_f_major_root(self):
        """F major root is pitch class 5."""
        assert key_to_semitone(-1) == 5
    
    def test_bb_major_root(self):
        """Bb major root is pitch class 10."""
        assert key_to_semitone(-2) == 10


class TestGetScaleDegreePitches:
    """Test get_scale_degree_pitches."""
    
    def test_c_major_scale(self):
        """C major scale pitches are C D E F G A B."""
        pitches = get_scale_degree_pitches(0)
        assert pitches == (0, 2, 4, 5, 7, 9, 11)
    
    def test_g_major_scale(self):
        """G major scale starts on G (pitch class 7)."""
        pitches = get_scale_degree_pitches(1)
        assert pitches[0] == 7  # G
        assert pitches[6] == 6  # F#
    
    def test_f_major_scale(self):
        """F major scale starts on F (pitch class 5)."""
        pitches = get_scale_degree_pitches(-1)
        assert pitches[0] == 5  # F
        assert pitches[3] == 10  # Bb


class TestGetScaleDegreeAndAlteration:
    """Test get_scale_degree_and_alteration."""
    
    def test_c_in_c_major(self):
        """C4 (MIDI 60) is diatonic degree 0 in C major."""
        degree, alteration = get_scale_degree_and_alteration(60, 0)
        assert degree == 0
        assert alteration == 0
    
    def test_fsharp_in_g_major(self):
        """F#4 (MIDI 66) is diatonic degree 6 in G major."""
        degree, alteration = get_scale_degree_and_alteration(66, 1)
        assert degree == 6
        assert alteration == 0
    
    def test_f_natural_in_g_major(self):
        """F4 (MIDI 65) is lowered degree 6 in G major."""
        degree, alteration = get_scale_degree_and_alteration(65, 1)
        assert degree == 6
        assert alteration == -1
    
    def test_bb_in_bb_major(self):
        """Bb3 (MIDI 58) is diatonic degree 0 in Bb major."""
        degree, alteration = get_scale_degree_and_alteration(58, -2)
        assert degree == 0
        assert alteration == 0
    
    def test_b_natural_in_bb_major(self):
        """B3 (MIDI 59) is raised degree 0 in Bb major."""
        degree, alteration = get_scale_degree_and_alteration(59, -2)
        assert degree == 0
        assert alteration == 1
    
    def test_dsharp_in_c_major(self):
        """D#4 (MIDI 63) is raised degree 1 in C major per the map."""
        degree, alteration = get_scale_degree_and_alteration(63, 0)
        assert degree == 1
        assert alteration == 1


class TestGetSpellingFromMap:
    """Test get_spelling_from_map lookup."""
    
    def test_c_diatonic_in_c_major(self):
        """Diatonic tonic in C major is C natural."""
        spelling = get_spelling_from_map(0, 0, 0)
        assert spelling.letter == "C"
        assert spelling.accidental is None
    
    def test_fsharp_diatonic_in_g_major(self):
        """Diatonic 7th in G major is F#."""
        spelling = get_spelling_from_map(1, 6, 0)
        assert spelling.letter == "F"
        assert spelling.accidental == Accidental.SHARP
    
    def test_f_natural_in_g_major(self):
        """Lowered 7th in G major is F natural."""
        spelling = get_spelling_from_map(1, 6, -1)
        assert spelling.letter == "F"
        assert spelling.accidental == Accidental.NATURAL
    
    def test_bb_diatonic_in_bb_major(self):
        """Diatonic tonic in Bb major is Bb."""
        spelling = get_spelling_from_map(-2, 0, 0)
        assert spelling.letter == "B"
        assert spelling.accidental == Accidental.FLAT
    
    def test_b_natural_in_bb_major(self):
        """Raised tonic in Bb major is B natural."""
        spelling = get_spelling_from_map(-2, 0, 1)
        assert spelling.letter == "B"
        assert spelling.accidental == Accidental.NATURAL
    
    def test_csharp_double_raised_in_c_major(self):
        """Double-raised tonic in C major is C##."""
        spelling = get_spelling_from_map(0, 0, 2)
        assert spelling.letter == "C"
        assert spelling.accidental == Accidental.DOUBLE_SHARP
    
    def test_invalid_key_raises(self):
        """Invalid key should raise KeyError."""
        with pytest.raises(KeyError):
            get_spelling_from_map(100, 0, 0)
    
    def test_invalid_degree_raises(self):
        """Invalid degree should raise KeyError."""
        with pytest.raises(KeyError):
            get_spelling_from_map(0, 10, 0)


class TestMidiToPitchNameInKey:
    """Test midi_to_pitch_name_in_key (main function)."""
    
    # C Major tests
    def test_c4_in_c_major(self):
        """C4 (MIDI 60) in C major."""
        assert midi_to_pitch_name_in_key(60, "C") == "C4"
    
    def test_d4_in_c_major(self):
        """D4 (MIDI 62) in C major."""
        assert midi_to_pitch_name_in_key(62, "C") == "D4"
    
    def test_csharp4_in_c_major(self):
        """C#4 (MIDI 61) in C major."""
        assert midi_to_pitch_name_in_key(61, "C") == "C#4"
    
    def test_dsharp4_in_c_major(self):
        """D#4 (MIDI 63) in C major is spelled D# per the map."""
        assert midi_to_pitch_name_in_key(63, "C") == "D#4"
    
    # G Major tests (1 sharp)
    def test_fsharp4_in_g_major(self):
        """F#4 (MIDI 66) is diatonic in G major."""
        assert midi_to_pitch_name_in_key(66, "G") == "F#4"
    
    def test_f_natural_in_g_major(self):
        """F4 (MIDI 65) in G major is F natural."""
        assert midi_to_pitch_name_in_key(65, "G") == "F4"
    
    def test_g4_in_g_major(self):
        """G4 (MIDI 67) in G major."""
        assert midi_to_pitch_name_in_key(67, "G") == "G4"
    
    # Bb Major tests (2 flats)
    def test_bb3_in_bb_major(self):
        """Bb3 (MIDI 58) in Bb major."""
        assert midi_to_pitch_name_in_key(58, "Bb") == "Bb3"
    
    def test_b_natural_in_bb_major(self):
        """B3 (MIDI 59) in Bb major is B natural."""
        assert midi_to_pitch_name_in_key(59, "Bb") == "B3"
    
    def test_eb4_in_bb_major(self):
        """Eb4 (MIDI 63) in Bb major."""
        assert midi_to_pitch_name_in_key(63, "Bb") == "Eb4"
    
    def test_e_natural_in_bb_major(self):
        """E4 (MIDI 64) in Bb major is E natural."""
        assert midi_to_pitch_name_in_key(64, "Bb") == "E4"
    
    # D Major tests (2 sharps)
    def test_fsharp4_in_d_major(self):
        """F#4 (MIDI 66) is diatonic in D major."""
        assert midi_to_pitch_name_in_key(66, "D") == "F#4"
    
    def test_csharp4_in_d_major(self):
        """C#4 (MIDI 61) is diatonic in D major."""
        assert midi_to_pitch_name_in_key(61, "D") == "C#4"
    
    def test_c_natural_in_d_major(self):
        """C4 (MIDI 60) in D major is C natural."""
        assert midi_to_pitch_name_in_key(60, "D") == "C4"
    
    # F Major tests (1 flat)
    def test_bb3_in_f_major(self):
        """Bb3 (MIDI 58) is diatonic in F major."""
        assert midi_to_pitch_name_in_key(58, "F") == "Bb3"
    
    def test_b_natural_in_f_major(self):
        """B3 (MIDI 59) in F major is B natural."""
        assert midi_to_pitch_name_in_key(59, "F") == "B3"
    
    # Ab Major tests (4 flats)
    def test_ab3_in_ab_major(self):
        """Ab3 (MIDI 56) in Ab major."""
        assert midi_to_pitch_name_in_key(56, "Ab") == "Ab3"
    
    def test_db4_in_ab_major(self):
        """Db4 (MIDI 61) is diatonic in Ab major."""
        assert midi_to_pitch_name_in_key(61, "Ab") == "Db4"
    
    # E Major tests (4 sharps)
    def test_gsharp4_in_e_major(self):
        """G#4 (MIDI 68) is diatonic in E major."""
        assert midi_to_pitch_name_in_key(68, "E") == "G#4"
    
    def test_dsharp4_in_e_major(self):
        """D#4 (MIDI 63) is diatonic in E major."""
        assert midi_to_pitch_name_in_key(63, "E") == "D#4"


class TestEnharmonicEdgeCases:
    """Test edge cases for enharmonic spelling."""
    
    def test_chromatic_passage_in_g_major(self):
        """Chromatic notes should be spelled correctly in context."""
        # In G major: G G# A A# B C C# D D# E F F# G
        assert midi_to_pitch_name_in_key(67, "G") == "G4"   # diatonic
        assert midi_to_pitch_name_in_key(68, "G") == "G#4"  # raised 0
        assert midi_to_pitch_name_in_key(69, "G") == "A4"   # diatonic
    
    def test_chromatic_notes_in_c_major(self):
        """Chromatic notes spelled according to the map."""
        # Map prefers raised interpretations in C major (sharp key)
        assert midi_to_pitch_name_in_key(63, "C") == "D#4"  # raised 1
        assert midi_to_pitch_name_in_key(68, "C") == "G#4"  # raised 4
        assert midi_to_pitch_name_in_key(70, "C") == "A#4"  # raised 5
    
    def test_raised_scale_degrees(self):
        """Raised scale degrees should use correct spelling."""
        # In C major, raised notes:
        assert midi_to_pitch_name_in_key(61, "C") == "C#4"  # raised 0
        assert midi_to_pitch_name_in_key(66, "C") == "F#4"  # raised 3
    
    def test_octave_boundary(self):
        """Notes near octave boundaries should have correct octave."""
        # B4 should be B4
        assert midi_to_pitch_name_in_key(71, "C") == "B4"
        # C5 should be C5
        assert midi_to_pitch_name_in_key(72, "C") == "C5"
    
    def test_multiple_octaves(self):
        """Same pitch class in different octaves."""
        assert midi_to_pitch_name_in_key(48, "C") == "C3"
        assert midi_to_pitch_name_in_key(60, "C") == "C4"
        assert midi_to_pitch_name_in_key(72, "C") == "C5"
        assert midi_to_pitch_name_in_key(84, "C") == "C6"


class TestKeyAlterationMapCompleteness:
    """Verify KEY_ALTERATION_MAP is complete."""
    
    def test_all_keys_present(self):
        """All 15 key signatures should be in the map."""
        for fifths in range(-7, 8):
            assert fifths in KEY_ALTERATION_MAP
    
    def test_all_degrees_present(self):
        """Each key should have 7 scale degrees."""
        for fifths in range(-7, 8):
            assert len(KEY_ALTERATION_MAP[fifths]) == 7
    
    def test_all_alterations_present(self):
        """Each degree should have 5 alterations (-2 to +2)."""
        for fifths in range(-7, 8):
            for degree in range(7):
                degree_map = KEY_ALTERATION_MAP[fifths][degree]
                for alt in (-2, -1, 0, 1, 2):
                    assert alt in degree_map, (
                        f"Missing alteration {alt} for degree {degree} in key {fifths}"
                    )


class TestSpellingToPitchName:
    """Test spelling_to_pitch_name formatting."""
    
    def test_natural_note(self):
        """Natural note without accidental."""
        spelling = SpellingEntry("C", None)
        assert spelling_to_pitch_name(spelling, 4) == "C4"
    
    def test_sharp_note(self):
        """Sharp note."""
        spelling = SpellingEntry("F", Accidental.SHARP)
        assert spelling_to_pitch_name(spelling, 4) == "F#4"
    
    def test_flat_note(self):
        """Flat note."""
        spelling = SpellingEntry("B", Accidental.FLAT)
        assert spelling_to_pitch_name(spelling, 3) == "Bb3"
    
    def test_double_sharp(self):
        """Double sharp note."""
        spelling = SpellingEntry("C", Accidental.DOUBLE_SHARP)
        assert spelling_to_pitch_name(spelling, 4) == "C##4"
    
    def test_double_flat(self):
        """Double flat note."""
        spelling = SpellingEntry("B", Accidental.DOUBLE_FLAT)
        assert spelling_to_pitch_name(spelling, 4) == "Bbb4"
    
    def test_natural_accidental(self):
        """Explicit natural accidental is omitted in simple naming."""
        spelling = SpellingEntry("F", Accidental.NATURAL)
        assert spelling_to_pitch_name(spelling, 4) == "F4"
