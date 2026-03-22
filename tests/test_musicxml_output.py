"""Tests for musicxml_output module.

Tests MusicXML generation from PitchEvent lists.
"""

import pytest
from typing import List
import xml.etree.ElementTree as ET

from app.schemas.generation_schemas import (
    ArticulationType,
    GenerationRequest,
    GenerationType,
    MusicalKey,
    PitchEvent,
)
from app.services.generation.musicxml_output import (
    events_to_musicxml,
    generate_musicxml_from_request,
    midi_pitches_to_musicxml,
    _midi_to_pitch,
    _beats_to_type,
    _key_to_fifths,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def c_major_scale_events() -> List[PitchEvent]:
    """C major scale with quarter notes."""
    pitches = [60, 62, 64, 65, 67, 69, 71, 72]
    names = ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]
    return [
        PitchEvent(
            midi_note=p, pitch_name=n, duration_beats=1.0, offset_beats=float(i)
        )
        for i, (p, n) in enumerate(zip(pitches, names))
    ]


@pytest.fixture
def simple_melody_events() -> List[PitchEvent]:
    """Simple 4-note melody."""
    return [
        PitchEvent(midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0),
        PitchEvent(midi_note=64, pitch_name="E4", duration_beats=1.0, offset_beats=1.0),
        PitchEvent(midi_note=67, pitch_name="G4", duration_beats=1.0, offset_beats=2.0),
        PitchEvent(midi_note=72, pitch_name="C5", duration_beats=1.0, offset_beats=3.0),
    ]


# =============================================================================
# Test Pitch Helpers
# =============================================================================


class TestMidiToPitch:
    """Tests for _midi_to_pitch helper."""

    def test_middle_c(self) -> None:
        step, octave, alter = _midi_to_pitch(60)
        assert step == "C"
        assert octave == 4
        assert alter == 0

    def test_c_sharp(self) -> None:
        step, octave, alter = _midi_to_pitch(61)
        assert step == "C"
        assert alter == 1

    def test_d_flat_with_flats(self) -> None:
        step, octave, alter = _midi_to_pitch(61, use_flats=True)
        assert step == "D"
        assert alter == -1

    def test_b_natural(self) -> None:
        step, octave, alter = _midi_to_pitch(71)
        assert step == "B"
        assert alter == 0

    def test_octave_calculation(self) -> None:
        # C3 = 48, C4 = 60, C5 = 72
        _, octave_c3, _ = _midi_to_pitch(48)
        _, octave_c4, _ = _midi_to_pitch(60)
        _, octave_c5, _ = _midi_to_pitch(72)
        assert octave_c3 == 3
        assert octave_c4 == 4
        assert octave_c5 == 5


class TestBeatsToType:
    """Tests for _beats_to_type helper."""

    def test_whole_note(self) -> None:
        type_name, is_dotted = _beats_to_type(4.0)
        assert type_name == "whole"
        assert not is_dotted

    def test_half_note(self) -> None:
        type_name, is_dotted = _beats_to_type(2.0)
        assert type_name == "half"
        assert not is_dotted

    def test_quarter_note(self) -> None:
        type_name, is_dotted = _beats_to_type(1.0)
        assert type_name == "quarter"
        assert not is_dotted

    def test_eighth_note(self) -> None:
        type_name, is_dotted = _beats_to_type(0.5)
        assert type_name == "eighth"
        assert not is_dotted

    def test_dotted_quarter(self) -> None:
        type_name, is_dotted = _beats_to_type(1.5)
        assert type_name == "quarter"
        assert is_dotted

    def test_dotted_half(self) -> None:
        type_name, is_dotted = _beats_to_type(3.0)
        assert type_name == "half"
        assert is_dotted


class TestKeyToFifths:
    """Tests for _key_to_fifths helper."""

    def test_c_major(self) -> None:
        assert _key_to_fifths(MusicalKey.C) == 0

    def test_g_major(self) -> None:
        assert _key_to_fifths(MusicalKey.G) == 1

    def test_d_major(self) -> None:
        assert _key_to_fifths(MusicalKey.D) == 2

    def test_f_major(self) -> None:
        assert _key_to_fifths(MusicalKey.F) == -1

    def test_b_flat_major(self) -> None:
        assert _key_to_fifths(MusicalKey.B_FLAT) == -2


# =============================================================================
# Test events_to_musicxml
# =============================================================================


class TestEventsToMusicxml:
    """Tests for events_to_musicxml function."""

    def test_basic_output_structure(self, simple_melody_events: List[PitchEvent]) -> None:
        xml_str = events_to_musicxml(simple_melody_events, title="Test")
        
        # Should start with XML declaration
        assert xml_str.startswith('<?xml version="1.0"')
        # Should include DOCTYPE
        assert "score-partwise" in xml_str
        # Should have title
        assert "Test" in xml_str

    def test_parses_as_valid_xml(self, simple_melody_events: List[PitchEvent]) -> None:
        xml_str = events_to_musicxml(simple_melody_events)
        # Strip the DOCTYPE as ElementTree doesn't handle it well
        content = xml_str.split("?>", 1)[1]
        content = content.split(">", 1)[1]  # Remove DOCTYPE line
        content = "<score-partwise" + content.split("<score-partwise", 1)[1]
        
        # Should parse without error
        root = ET.fromstring(content)
        assert root.tag == "score-partwise"

    def test_correct_number_of_notes(self, simple_melody_events: List[PitchEvent]) -> None:
        xml_str = events_to_musicxml(simple_melody_events)
        # Count note elements (excluding rests)
        note_count = xml_str.count("<note>")
        assert note_count == 4

    def test_correct_pitch_values(self) -> None:
        events = [
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0
            )
        ]
        xml_str = events_to_musicxml(events)
        
        assert "<step>C</step>" in xml_str
        assert "<octave>4</octave>" in xml_str

    def test_sharp_pitch(self) -> None:
        events = [
            PitchEvent(
                midi_note=61, pitch_name="C#4", duration_beats=1.0, offset_beats=0.0
            )
        ]
        xml_str = events_to_musicxml(events, key=MusicalKey.G)
        
        assert "<step>C</step>" in xml_str
        assert "<alter>1</alter>" in xml_str

    def test_flat_pitch_in_flat_key(self) -> None:
        events = [
            PitchEvent(
                midi_note=61, pitch_name="Db4", duration_beats=1.0, offset_beats=0.0
            )
        ]
        xml_str = events_to_musicxml(events, key=MusicalKey.F)
        
        assert "<step>D</step>" in xml_str
        assert "<alter>-1</alter>" in xml_str

    def test_key_signature(self) -> None:
        events = [
            PitchEvent(
                midi_note=62, pitch_name="D4", duration_beats=1.0, offset_beats=0.0
            )
        ]
        
        xml_g = events_to_musicxml(events, key=MusicalKey.G)
        xml_f = events_to_musicxml(events, key=MusicalKey.F)
        
        assert "<fifths>1</fifths>" in xml_g  # G major
        assert "<fifths>-1</fifths>" in xml_f  # F major

    def test_time_signature(self) -> None:
        events = [
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0
            )
        ]
        xml_str = events_to_musicxml(events, time_signature=(3, 4))
        
        assert "<beats>3</beats>" in xml_str
        assert "<beat-type>4</beat-type>" in xml_str

    def test_multiple_measures(self, c_major_scale_events: List[PitchEvent]) -> None:
        xml_str = events_to_musicxml(c_major_scale_events, time_signature=(4, 4))
        
        # 8 quarter notes in 4/4 = 2 measures
        assert 'number="1"' in xml_str
        assert 'number="2"' in xml_str

    def test_final_barline(self, simple_melody_events: List[PitchEvent]) -> None:
        xml_str = events_to_musicxml(simple_melody_events)
        
        assert "<bar-style>light-heavy</bar-style>" in xml_str

    def test_tempo_marking(self) -> None:
        events = [
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0
            )
        ]
        xml_str = events_to_musicxml(events, tempo_bpm=120)
        
        assert "<per-minute>120</per-minute>" in xml_str
        assert 'tempo="120"' in xml_str

    def test_articulation_staccato(self) -> None:
        events = [
            PitchEvent(
                midi_note=60,
                pitch_name="C4",
                duration_beats=1.0,
                offset_beats=0.0,
                articulation=ArticulationType.STACCATO,
            )
        ]
        xml_str = events_to_musicxml(events)
        
        assert "<staccato" in xml_str

    def test_articulation_accent(self) -> None:
        events = [
            PitchEvent(
                midi_note=60,
                pitch_name="C4",
                duration_beats=1.0,
                offset_beats=0.0,
                articulation=ArticulationType.ACCENT,
            )
        ]
        xml_str = events_to_musicxml(events)
        
        assert "<accent" in xml_str

    def test_empty_events(self) -> None:
        xml_str = events_to_musicxml([])
        
        # Should still produce valid XML with a rest
        assert "<rest" in xml_str

    def test_rest_note(self) -> None:
        events = [
            PitchEvent(
                midi_note=0, pitch_name="rest", duration_beats=1.0, offset_beats=0.0
            )
        ]
        xml_str = events_to_musicxml(events)
        
        assert "<rest" in xml_str

    def test_dotted_note(self) -> None:
        events = [
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=1.5, offset_beats=0.0
            )
        ]
        xml_str = events_to_musicxml(events)
        
        assert "<dot" in xml_str


# =============================================================================
# Test generate_musicxml_from_request
# =============================================================================


class TestGenerateMusicxmlFromRequest:
    """Tests for generate_musicxml_from_request function."""

    def test_basic_request(self) -> None:
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            key=MusicalKey.G,
        )
        events = [
            PitchEvent(
                midi_note=67, pitch_name="G4", duration_beats=1.0, offset_beats=0.0
            )
        ]
        
        xml_str = generate_musicxml_from_request(request, events)
        
        assert "Ionian scale" in xml_str
        assert "G" in xml_str
        assert "<fifths>1</fifths>" in xml_str

    def test_custom_title(self) -> None:
        request = GenerationRequest(
            content_type=GenerationType.ARPEGGIO,
            definition="major",
        )
        events = [
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0
            )
        ]
        
        xml_str = generate_musicxml_from_request(request, events, title="My Custom Title")
        
        assert "My Custom Title" in xml_str


# =============================================================================
# Test midi_pitches_to_musicxml
# =============================================================================


class TestMidiPitchesToMusicxml:
    """Tests for midi_pitches_to_musicxml function."""

    def test_basic_conversion(self) -> None:
        pitches = [60, 62, 64, 65, 67]
        xml_str = midi_pitches_to_musicxml(pitches)
        
        assert "<step>C</step>" in xml_str
        assert "<step>D</step>" in xml_str
        assert "<step>E</step>" in xml_str
        assert "<step>F</step>" in xml_str
        assert "<step>G</step>" in xml_str

    def test_custom_title(self) -> None:
        pitches = [60, 64, 67]
        xml_str = midi_pitches_to_musicxml(pitches, title="C Major Triad")
        
        assert "C Major Triad" in xml_str

    def test_key_affects_spelling(self) -> None:
        pitches = [66]  # F#/Gb
        
        xml_sharp = midi_pitches_to_musicxml(pitches, key=MusicalKey.D)
        xml_flat = midi_pitches_to_musicxml(pitches, key=MusicalKey.D_FLAT)
        
        # D major uses F#
        assert "<alter>1</alter>" in xml_sharp
        # Db major uses Gb
        assert "<alter>-1</alter>" in xml_flat

    def test_custom_duration(self) -> None:
        pitches = [60, 62]
        xml_str = midi_pitches_to_musicxml(pitches, duration_beats=2.0)
        
        # Should have half notes
        assert "<type>half</type>" in xml_str
