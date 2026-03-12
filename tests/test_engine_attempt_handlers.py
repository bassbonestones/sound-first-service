"""
Tests for engine attempt handler utilities.

Tests pure functions used in attempt processing.
"""

import pytest
from app.services.engine.attempt_handlers import pitch_name_to_midi


class TestPitchNameToMidi:
    """Test pitch_name_to_midi conversion function."""
    
    def test_middle_c(self):
        """C4 should be MIDI 60."""
        assert pitch_name_to_midi("C4") == 60
    
    def test_a440(self):
        """A4 should be MIDI 69 (A440 reference)."""
        assert pitch_name_to_midi("A4") == 69
    
    def test_c3(self):
        """C3 should be MIDI 48."""
        assert pitch_name_to_midi("C3") == 48
    
    def test_c5(self):
        """C5 should be MIDI 72."""
        assert pitch_name_to_midi("C5") == 72
    
    def test_sharp_note(self):
        """C#4 should be MIDI 61."""
        assert pitch_name_to_midi("C#4") == 61
    
    def test_flat_note(self):
        """Bb4 should be MIDI 70."""
        assert pitch_name_to_midi("Bb4") == 70
    
    def test_double_sharp(self):
        """C##4 should be MIDI 62."""
        assert pitch_name_to_midi("C##4") == 62
    
    def test_double_flat(self):
        """Dbb4 should be MIDI 60 (enharmonic to C4)."""
        assert pitch_name_to_midi("Dbb4") == 60
    
    def test_lowercase_input(self):
        """Should handle lowercase input."""
        assert pitch_name_to_midi("c4") == 60
    
    def test_mixed_case(self):
        """Should handle mixed case."""
        assert pitch_name_to_midi("c#4") == 61
    
    def test_empty_string_default(self):
        """Empty string should default to 60."""
        assert pitch_name_to_midi("") == 60
    
    def test_none_default(self):
        """None should default to 60."""
        assert pitch_name_to_midi(None) == 60
    
    def test_whitespace_stripped(self):
        """Should strip whitespace."""
        assert pitch_name_to_midi(" C4 ") == 60
    
    def test_missing_octave_defaults_to_4(self):
        """Missing octave should default to 4."""
        assert pitch_name_to_midi("C") == 60
    
    def test_all_natural_notes_octave_4(self):
        """All natural notes in octave 4."""
        expected = {
            "C4": 60, "D4": 62, "E4": 64, "F4": 65,
            "G4": 67, "A4": 69, "B4": 71
        }
        for note, midi in expected.items():
            assert pitch_name_to_midi(note) == midi
    
    def test_very_low_octave(self):
        """Should handle very low octave."""
        assert pitch_name_to_midi("C0") == 12
    
    def test_very_high_octave(self):
        """Should handle very high octave."""
        assert pitch_name_to_midi("C8") == 108
    
    def test_uppercase_flat(self):
        """Should handle uppercase B as flat."""
        # 'B' as a note vs 'b' as flat - both handled
        assert pitch_name_to_midi("Bb4") == 70
        assert pitch_name_to_midi("BB4") == 70
