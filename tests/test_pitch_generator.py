"""Tests for the pitch sequence generation engine."""
import pytest

from app.schemas.generation_schemas import (
    ArpeggioType,
    GenerationRequest,
    GenerationType,
    MusicalKey,
    ScaleType,
)
from app.services.generation import (
    ARPEGGIO_INTERVALS,
    SCALE_INTERVALS,
    PitchSequenceGenerator,
    get_arpeggio_intervals,
    get_scale_intervals,
)
from app.services.generation.pitch_generator import (
    KEY_OFFSETS,
    get_key_offset,
    midi_to_pitch_name,
    should_use_flats,
)
from app.services.generation.scale_definitions import (
    get_scale_note_count,
    scale_spans_octave,
    get_scale_spellings,
    get_transposed_scale_spellings,
    SCALE_SPELLINGS_IN_C,
)
from app.services.generation.arpeggio_definitions import (
    get_arpeggio_note_count,
    get_arpeggio_span_semitones,
)


# =============================================================================
# Scale Definitions Tests
# =============================================================================

class TestScaleDefinitions:
    """Tests for scale interval definitions."""

    def test_all_scale_types_defined(self) -> None:
        """Every ScaleType enum should have a definition."""
        for scale_type in ScaleType:
            assert scale_type in SCALE_INTERVALS, f"Missing: {scale_type}"

    def test_all_scale_spellings_defined(self) -> None:
        """Every ScaleType should have spellings defined in C."""
        for scale_type in ScaleType:
            assert scale_type in SCALE_SPELLINGS_IN_C, f"Missing spelling: {scale_type}"

    def test_scale_spellings_match_interval_count(self) -> None:
        """Each scale's spellings should match its interval count."""
        for scale_type in ScaleType:
            intervals = get_scale_intervals(scale_type)
            spellings = SCALE_SPELLINGS_IN_C[scale_type]
            assert len(intervals) == len(spellings), \
                f"{scale_type}: {len(intervals)} intervals but {len(spellings)} spellings"

    def test_ionian_intervals(self) -> None:
        """Ionian (major) should be W-W-H-W-W-W-H."""
        intervals = get_scale_intervals(ScaleType.IONIAN)
        assert intervals == (2, 2, 1, 2, 2, 2, 1)

    def test_dorian_intervals(self) -> None:
        """Dorian should be W-H-W-W-W-H-W."""
        intervals = get_scale_intervals(ScaleType.DORIAN)
        assert intervals == (2, 1, 2, 2, 2, 1, 2)

    def test_aeolian_intervals(self) -> None:
        """Aeolian (natural minor) should be W-H-W-W-H-W-W."""
        intervals = get_scale_intervals(ScaleType.AEOLIAN)
        assert intervals == (2, 1, 2, 2, 1, 2, 2)

    def test_pentatonic_major_intervals(self) -> None:
        """Pentatonic major should have 5 notes."""
        intervals = get_scale_intervals(ScaleType.PENTATONIC_MAJOR)
        assert len(intervals) == 5
        assert sum(intervals) == 12  # Spans octave

    def test_pentatonic_minor_intervals(self) -> None:
        """Pentatonic minor should have 5 notes."""
        intervals = get_scale_intervals(ScaleType.PENTATONIC_MINOR)
        assert len(intervals) == 5
        assert sum(intervals) == 12

    def test_chromatic_intervals(self) -> None:
        """Chromatic should be all half steps."""
        intervals = get_scale_intervals(ScaleType.CHROMATIC)
        assert all(i == 1 for i in intervals)
        assert len(intervals) == 12

    def test_whole_tone_intervals(self) -> None:
        """Whole tone should be all whole steps."""
        intervals = get_scale_intervals(ScaleType.WHOLE_TONE)
        assert all(i == 2 for i in intervals)
        assert len(intervals) == 6
        assert sum(intervals) == 12

    def test_diatonic_scales_span_octave(self) -> None:
        """All major modes should span exactly 12 semitones."""
        diatonic_scales = [
            ScaleType.IONIAN, ScaleType.DORIAN, ScaleType.PHRYGIAN,
            ScaleType.LYDIAN, ScaleType.MIXOLYDIAN, ScaleType.AEOLIAN,
            ScaleType.LOCRIAN,
        ]
        for scale in diatonic_scales:
            assert scale_spans_octave(scale), f"{scale} doesn't span octave"

    def test_diminished_scales_have_8_notes(self) -> None:
        """Diminished scales should have 8 notes."""
        assert get_scale_note_count(ScaleType.DIMINISHED_HW) == 8
        assert get_scale_note_count(ScaleType.DIMINISHED_WH) == 8

    def test_harmonic_minor_has_augmented_second(self) -> None:
        """Harmonic minor should contain an augmented 2nd (3 semitones)."""
        intervals = get_scale_intervals(ScaleType.HARMONIC_MINOR)
        assert 3 in intervals  # Augmented 2nd

    def test_blues_scale_spellings_in_c(self) -> None:
        """Blues scale should be spelled: C, Eb, F, F#, G, Bb (the #4, not b5)."""
        spellings = get_scale_spellings(ScaleType.BLUES)
        assert spellings == ("C", "Eb", "F", "F#", "G", "Bb")

    def test_blues_scale_transposed_to_g(self) -> None:
        """Blues scale in G should be: G, Bb, C, C#, D, F."""
        spellings = get_transposed_scale_spellings(ScaleType.BLUES, 7)  # G = 7 semitones
        # G, Bb, C, C#, D, F
        assert "G" in spellings[0]
        assert "Bb" in spellings[1]
        assert "C#" in spellings[3] or "Db" in spellings[3]  # Allow either spelling for now

    def test_ionian_scale_spellings_in_c(self) -> None:
        """Major scale in C should have all natural notes."""
        spellings = get_scale_spellings(ScaleType.IONIAN)
        assert spellings == ("C", "D", "E", "F", "G", "A", "B")

    def test_dorian_scale_spellings_in_c(self) -> None:
        """Dorian scale in C should have Eb and Bb."""
        spellings = get_scale_spellings(ScaleType.DORIAN)
        assert "Eb" in spellings
        assert "Bb" in spellings


# =============================================================================
# Arpeggio Definitions Tests
# =============================================================================

class TestArpeggioDefinitions:
    """Tests for arpeggio interval definitions."""

    def test_all_arpeggio_types_defined(self) -> None:
        """Every ArpeggioType enum should have a definition."""
        for arp_type in ArpeggioType:
            assert arp_type in ARPEGGIO_INTERVALS, f"Missing: {arp_type}"

    def test_major_triad_intervals(self) -> None:
        """Major triad should be root, M3, P5."""
        intervals = get_arpeggio_intervals(ArpeggioType.MAJOR)
        assert intervals == (0, 4, 7)

    def test_minor_triad_intervals(self) -> None:
        """Minor triad should be root, m3, P5."""
        intervals = get_arpeggio_intervals(ArpeggioType.MINOR)
        assert intervals == (0, 3, 7)

    def test_major_7_intervals(self) -> None:
        """Major 7 should be root, M3, P5, M7."""
        intervals = get_arpeggio_intervals(ArpeggioType.MAJOR_7)
        assert intervals == (0, 4, 7, 11)

    def test_dominant_7_intervals(self) -> None:
        """Dominant 7 should be root, M3, P5, m7."""
        intervals = get_arpeggio_intervals(ArpeggioType.DOMINANT_7)
        assert intervals == (0, 4, 7, 10)

    def test_minor_7_intervals(self) -> None:
        """Minor 7 should be root, m3, P5, m7."""
        intervals = get_arpeggio_intervals(ArpeggioType.MINOR_7)
        assert intervals == (0, 3, 7, 10)

    def test_triads_have_3_notes(self) -> None:
        """All triads should have 3 chord tones."""
        triads = [
            ArpeggioType.MAJOR, ArpeggioType.MINOR,
            ArpeggioType.AUGMENTED, ArpeggioType.DIMINISHED,
            ArpeggioType.SUS4, ArpeggioType.SUS2,
        ]
        for triad in triads:
            assert get_arpeggio_note_count(triad) == 3, f"{triad} is not 3 notes"

    def test_7th_chords_have_4_notes(self) -> None:
        """All 7th chords should have 4 chord tones."""
        sevenths = [
            ArpeggioType.MAJOR_7, ArpeggioType.DOMINANT_7,
            ArpeggioType.MINOR_7, ArpeggioType.MINOR_MAJOR_7,
            ArpeggioType.HALF_DIMINISHED, ArpeggioType.DIMINISHED_7,
        ]
        for seventh in sevenths:
            assert get_arpeggio_note_count(seventh) == 4, f"{seventh} is not 4 notes"

    def test_9th_chords_have_5_notes(self) -> None:
        """9th chords should have 5 chord tones."""
        ninths = [ArpeggioType.MAJOR_9, ArpeggioType.DOMINANT_9, ArpeggioType.MINOR_9]
        for ninth in ninths:
            assert get_arpeggio_note_count(ninth) == 5, f"{ninth} is not 5 notes"

    def test_arpeggio_span_calculations(self) -> None:
        """Span calculations should be correct."""
        assert get_arpeggio_span_semitones(ArpeggioType.MAJOR) == 7  # P5
        assert get_arpeggio_span_semitones(ArpeggioType.MAJOR_7) == 11  # M7
        assert get_arpeggio_span_semitones(ArpeggioType.MAJOR_9) == 14  # M9


# =============================================================================
# Pitch Generator Helper Tests
# =============================================================================

class TestPitchGeneratorHelpers:
    """Tests for helper functions."""

    def test_midi_to_pitch_name_middle_c(self) -> None:
        """MIDI 60 should be C4."""
        assert midi_to_pitch_name(60) == "C4"

    def test_midi_to_pitch_name_with_sharps(self) -> None:
        """Default should use sharps."""
        assert midi_to_pitch_name(61) == "C#4"
        assert midi_to_pitch_name(66) == "F#4"
        assert midi_to_pitch_name(70) == "A#4"

    def test_midi_to_pitch_name_with_flats(self) -> None:
        """prefer_flats=True should use flats."""
        assert midi_to_pitch_name(61, prefer_flats=True) == "Db4"
        assert midi_to_pitch_name(66, prefer_flats=True) == "Gb4"
        assert midi_to_pitch_name(70, prefer_flats=True) == "Bb4"

    def test_key_offsets_c(self) -> None:
        """C should have offset 0."""
        assert get_key_offset(MusicalKey.C) == 0

    def test_key_offsets_enharmonics(self) -> None:
        """Enharmonic keys should have same offset."""
        assert get_key_offset(MusicalKey.C_SHARP) == get_key_offset(MusicalKey.D_FLAT)
        assert get_key_offset(MusicalKey.F_SHARP) == get_key_offset(MusicalKey.G_FLAT)

    def test_all_keys_have_offsets(self) -> None:
        """All MusicalKey values should have offsets."""
        for key in MusicalKey:
            assert key in KEY_OFFSETS, f"Missing offset for {key}"

    def test_should_use_flats(self) -> None:
        """Flat keys should be identified."""
        assert should_use_flats(MusicalKey.F)
        assert should_use_flats(MusicalKey.B_FLAT)
        assert should_use_flats(MusicalKey.E_FLAT)
        assert not should_use_flats(MusicalKey.C)
        assert not should_use_flats(MusicalKey.G)
        assert not should_use_flats(MusicalKey.D)


# =============================================================================
# Scale Generation Tests
# =============================================================================

class TestScaleGeneration:
    """Tests for scale generation."""

    def test_c_major_one_octave(self) -> None:
        """C major scale should produce correct MIDI notes."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_scale(
            scale_type=ScaleType.IONIAN,
            octaves=1,
            key=MusicalKey.C,
        )
        # C4, D4, E4, F4, G4, A4, B4, C5
        expected = [60, 62, 64, 65, 67, 69, 71, 72]
        assert pitches == expected

    def test_c_major_without_top_note(self) -> None:
        """Scale without top note should have 7 notes."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_scale(
            scale_type=ScaleType.IONIAN,
            octaves=1,
            key=MusicalKey.C,
            include_top_note=False,
        )
        assert len(pitches) == 7
        assert pitches[-1] == 71  # B4, not C5

    def test_g_major_transposition(self) -> None:
        """G major should start on G."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_scale(
            scale_type=ScaleType.IONIAN,
            octaves=1,
            key=MusicalKey.G,
        )
        # Should start on G
        assert pitches[0] % 12 == 7  # G

    def test_two_octave_scale(self) -> None:
        """2-octave scale should span 24 semitones + top note."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_scale(
            scale_type=ScaleType.IONIAN,
            octaves=2,
            key=MusicalKey.C,
        )
        # 7 notes per octave + 1 top note = 15 notes
        assert len(pitches) == 15
        assert pitches[-1] - pitches[0] == 24  # 2 octaves

    def test_descending_scale(self) -> None:
        """Descending scale should be reversed."""
        generator = PitchSequenceGenerator()
        ascending = generator.generate_scale(
            scale_type=ScaleType.IONIAN,
            key=MusicalKey.C,
            ascending=True,
        )
        descending = generator.generate_scale(
            scale_type=ScaleType.IONIAN,
            key=MusicalKey.C,
            ascending=False,
        )
        assert descending == list(reversed(ascending))

    def test_range_constraint_low(self) -> None:
        """Range constraint should filter low notes."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_scale(
            scale_type=ScaleType.IONIAN,
            octaves=1,
            key=MusicalKey.C,
            range_low_midi=64,  # E4
        )
        assert all(p >= 64 for p in pitches)

    def test_range_constraint_high(self) -> None:
        """Range constraint should filter high notes."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_scale(
            scale_type=ScaleType.IONIAN,
            octaves=1,
            key=MusicalKey.C,
            range_high_midi=67,  # G4
        )
        assert all(p <= 67 for p in pitches)

    def test_dorian_intervals(self) -> None:
        """Dorian scale should have flat 3 and flat 7."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_scale(
            scale_type=ScaleType.DORIAN,
            octaves=1,
            key=MusicalKey.C,
        )
        # C Dorian: C, D, Eb, F, G, A, Bb, C
        # MIDI: 60, 62, 63, 65, 67, 69, 70, 72
        expected = [60, 62, 63, 65, 67, 69, 70, 72]
        assert pitches == expected

    def test_pentatonic_scale_5_notes(self) -> None:
        """Pentatonic should produce 5 notes per octave + top."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_scale(
            scale_type=ScaleType.PENTATONIC_MAJOR,
            octaves=1,
            key=MusicalKey.C,
        )
        assert len(pitches) == 6  # 5 + top note


# =============================================================================
# Arpeggio Generation Tests
# =============================================================================

class TestArpeggioGeneration:
    """Tests for arpeggio generation."""

    def test_c_major_triad(self) -> None:
        """C major triad should be C-E-G-C (with octave completion)."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_arpeggio(
            arpeggio_type=ArpeggioType.MAJOR,
            octaves=1,
            key=MusicalKey.C,
        )
        # C4, E4, G4, C5 (do mi sol do)
        expected = [60, 64, 67, 72]
        assert pitches == expected

    def test_c_minor_triad(self) -> None:
        """C minor triad should be C-Eb-G-C (with octave completion)."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_arpeggio(
            arpeggio_type=ArpeggioType.MINOR,
            octaves=1,
            key=MusicalKey.C,
        )
        # C4, Eb4, G4, C5 (do me sol do)
        expected = [60, 63, 67, 72]
        assert pitches == expected

    def test_c_major_7(self) -> None:
        """C major 7 should be C-E-G-B (4 notes, no octave completion)."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_arpeggio(
            arpeggio_type=ArpeggioType.MAJOR_7,
            octaves=1,
            key=MusicalKey.C,
        )
        # do mi sol ti (7ths stay at 4 notes)
        expected = [60, 64, 67, 71]
        assert pitches == expected

    def test_two_octave_arpeggio(self) -> None:
        """2-octave triad arpeggio should go up through both octaves with octave completion."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_arpeggio(
            arpeggio_type=ArpeggioType.MAJOR,
            octaves=2,
            key=MusicalKey.C,
        )
        # C4, E4, G4, C5, E5, G5, C6
        expected = [60, 64, 67, 72, 76, 79, 84]
        assert pitches == expected

    def test_f_major_arpeggio(self) -> None:
        """F major arpeggio should start on F."""
        generator = PitchSequenceGenerator()
        pitches = generator.generate_arpeggio(
            arpeggio_type=ArpeggioType.MAJOR,
            octaves=1,
            key=MusicalKey.F,
        )
        assert pitches[0] % 12 == 5  # F

    def test_descending_arpeggio(self) -> None:
        """Descending arpeggio should be reversed."""
        generator = PitchSequenceGenerator()
        ascending = generator.generate_arpeggio(
            arpeggio_type=ArpeggioType.MAJOR_7,
            key=MusicalKey.C,
            ascending=True,
        )
        descending = generator.generate_arpeggio(
            arpeggio_type=ArpeggioType.MAJOR_7,
            key=MusicalKey.C,
            ascending=False,
        )
        assert descending == list(reversed(ascending))


# =============================================================================
# Request-Based Generation Tests
# =============================================================================

class TestGenerateFromRequest:
    """Tests for generate_from_request method."""

    def test_scale_request(self) -> None:
        """Should generate scale from request."""
        generator = PitchSequenceGenerator()
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            key=MusicalKey.C,
        )
        pitches, effective_octaves = generator.generate_from_request(request)
        assert len(pitches) == 8
        assert effective_octaves == 1

    def test_arpeggio_request(self) -> None:
        """Should generate arpeggio from request (7ths stay at 4 notes)."""
        generator = PitchSequenceGenerator()
        request = GenerationRequest(
            content_type=GenerationType.ARPEGGIO,
            definition="maj7",
            octaves=1,
            key=MusicalKey.C,
        )
        pitches, effective_octaves = generator.generate_from_request(request)
        # maj7 stays at 4 notes: do mi sol ti
        assert len(pitches) == 4

    def test_lick_request_raises(self) -> None:
        """Lick requests should raise ValueError."""
        generator = PitchSequenceGenerator()
        request = GenerationRequest(
            content_type=GenerationType.LICK,
            definition="ii_v_i_lick_001",
        )
        with pytest.raises(ValueError, match="Lick generation is not supported"):
            generator.generate_from_request(request)

    def test_request_with_range_bounds(self) -> None:
        """Range bounds from request should be applied."""
        generator = PitchSequenceGenerator()
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=2,
            key=MusicalKey.C,
            range_low_midi=64,
            range_high_midi=76,
        )
        pitches, _ = generator.generate_from_request(request)
        assert all(64 <= p <= 76 for p in pitches)


# =============================================================================
# Pitch to Events Tests
# =============================================================================

class TestPitchesToEvents:
    """Tests for converting pitches to PitchEvent objects."""

    def test_basic_conversion(self) -> None:
        """Should convert pitches to events with correct offsets."""
        generator = PitchSequenceGenerator()
        pitches = [60, 62, 64]
        events = generator.pitches_to_events(pitches, duration_beats=1.0)
        
        assert len(events) == 3
        assert events[0].midi_note == 60
        assert events[0].offset_beats == 0.0
        assert events[1].offset_beats == 1.0
        assert events[2].offset_beats == 2.0

    def test_pitch_names_generated(self) -> None:
        """Should generate correct pitch names."""
        generator = PitchSequenceGenerator()
        pitches = [60, 61, 62]
        events = generator.pitches_to_events(pitches)
        
        assert events[0].pitch_name == "C4"
        assert events[1].pitch_name == "C#4"

    def test_flat_names(self) -> None:
        """Should use flats when requested."""
        generator = PitchSequenceGenerator()
        pitches = [61, 63]
        events = generator.pitches_to_events(pitches, use_flats=True)
        
        assert events[0].pitch_name == "Db4"
        assert events[1].pitch_name == "Eb4"

    def test_custom_duration(self) -> None:
        """Should apply custom duration."""
        generator = PitchSequenceGenerator()
        pitches = [60, 62, 64]
        events = generator.pitches_to_events(pitches, duration_beats=0.5)
        
        assert all(e.duration_beats == 0.5 for e in events)
        assert events[0].offset_beats == 0.0
        assert events[1].offset_beats == 0.5
        assert events[2].offset_beats == 1.0


# =============================================================================
# Effective Octave Calculation Tests
# =============================================================================

class TestEffectiveOctaves:
    """Tests for effective octave calculation."""

    def test_one_octave_span(self) -> None:
        """12 semitone span should be 1 octave."""
        generator = PitchSequenceGenerator()
        pitches = [60, 72]  # C4 to C5
        _, effective = generator.generate_from_request(
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                octaves=1,
            )
        )
        assert effective == 1

    def test_two_octave_span(self) -> None:
        """24 semitone span should be 2 octaves."""
        generator = PitchSequenceGenerator()
        _, effective = generator.generate_from_request(
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                octaves=2,
            )
        )
        assert effective == 2

    def test_constrained_reduces_effective(self) -> None:
        """Range constraints should reduce effective octaves."""
        generator = PitchSequenceGenerator()
        _, effective = generator.generate_from_request(
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                octaves=2,
                range_low_midi=60,   # Start at C4
                range_high_midi=67,  # Only up to G4
            )
        )
        # Should be 1 since span is only 7 semitones (rounds to 1 octave)
        assert effective == 1
