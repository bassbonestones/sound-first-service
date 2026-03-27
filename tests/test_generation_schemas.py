"""Tests for generation engine Pydantic schemas."""
import pytest
from pydantic import ValidationError

from app.schemas.generation_schemas import (
    ArticulationType,
    ArpeggioPattern,
    ArpeggioType,
    CANONICAL_KEYS,
    ChordEvent,
    ChordProgressionContentType,
    ChordProgressionRequest,
    DynamicType,
    GenerationPreview,
    GenerationRequest,
    GenerationResponse,
    GenerationType,
    MusicalKey,
    PitchEvent,
    RangeSpec,
    RhythmType,
    ScalePattern,
    ScaleType,
)


class TestGenerationTypeEnum:
    """Test GenerationType enum values."""

    def test_all_types_exist(self) -> None:
        """Verify all generation types are defined."""
        assert GenerationType.SCALE.value == "scale"
        assert GenerationType.ARPEGGIO.value == "arpeggio"
        assert GenerationType.LICK.value == "lick"

    def test_type_count(self) -> None:
        """Verify expected number of generation types."""
        assert len(GenerationType) == 3


class TestScaleTypeEnum:
    """Test ScaleType enum values."""

    def test_major_modes_exist(self) -> None:
        """Verify all 7 major modes are defined."""
        major_modes = [
            ScaleType.IONIAN,
            ScaleType.DORIAN,
            ScaleType.PHRYGIAN,
            ScaleType.LYDIAN,
            ScaleType.MIXOLYDIAN,
            ScaleType.AEOLIAN,
            ScaleType.LOCRIAN,
        ]
        assert len(major_modes) == 7
        for mode in major_modes:
            assert isinstance(mode, ScaleType)

    def test_harmonic_minor_modes_exist(self) -> None:
        """Verify all 7 harmonic minor modes are defined."""
        harmonic_modes = [
            ScaleType.HARMONIC_MINOR,
            ScaleType.LOCRIAN_NAT6,
            ScaleType.IONIAN_AUG,
            ScaleType.DORIAN_SHARP4,
            ScaleType.PHRYGIAN_DOMINANT,
            ScaleType.LYDIAN_SHARP2,
            ScaleType.SUPER_LOCRIAN_BB7,
        ]
        assert len(harmonic_modes) == 7

    def test_melodic_minor_modes_exist(self) -> None:
        """Verify all 7 melodic minor modes are defined."""
        melodic_modes = [
            ScaleType.MELODIC_MINOR,
            ScaleType.DORIAN_FLAT2,
            ScaleType.LYDIAN_AUGMENTED,
            ScaleType.LYDIAN_DOMINANT,
            ScaleType.MIXOLYDIAN_FLAT6,
            ScaleType.LOCRIAN_NAT2,
            ScaleType.ALTERED,
        ]
        assert len(melodic_modes) == 7

    def test_pentatonic_and_blues_exist(self) -> None:
        """Verify pentatonic and blues scales exist."""
        assert ScaleType.PENTATONIC_MAJOR.value == "pentatonic_major"
        assert ScaleType.PENTATONIC_MINOR.value == "pentatonic_minor"
        assert ScaleType.BLUES.value == "blues"
        assert ScaleType.BLUES_MAJOR.value == "blues_major"

    def test_symmetric_scales_exist(self) -> None:
        """Verify symmetric scales exist."""
        assert ScaleType.WHOLE_TONE.value == "whole_tone"
        assert ScaleType.DIMINISHED_HW.value == "diminished_hw"
        assert ScaleType.DIMINISHED_WH.value == "diminished_wh"
        assert ScaleType.CHROMATIC.value == "chromatic"

    def test_total_scale_count(self) -> None:
        """Verify total number of scale types matches spec (~30)."""
        # 7 major + 7 harmonic + 7 melodic + 4 pentatonic/blues + 4 symmetric + 3 bebop
        assert len(ScaleType) >= 30


class TestArpeggioTypeEnum:
    """Test ArpeggioType enum values."""

    def test_triads_exist(self) -> None:
        """Verify all triad types are defined."""
        triads = [
            ArpeggioType.MAJOR,
            ArpeggioType.MINOR,
            ArpeggioType.AUGMENTED,
            ArpeggioType.DIMINISHED,
            ArpeggioType.SUS4,
            ArpeggioType.SUS2,
        ]
        assert len(triads) == 6

    def test_seventh_chords_exist(self) -> None:
        """Verify all 7th chord types are defined."""
        sevenths = [
            ArpeggioType.MAJOR_7,
            ArpeggioType.DOMINANT_7,
            ArpeggioType.MINOR_7,
            ArpeggioType.MINOR_MAJOR_7,
            ArpeggioType.HALF_DIMINISHED,
            ArpeggioType.DIMINISHED_7,
        ]
        assert len(sevenths) >= 6

    def test_extended_chords_exist(self) -> None:
        """Verify extended chord types are defined."""
        extended = [
            ArpeggioType.MAJOR_9,
            ArpeggioType.DOMINANT_9,
            ArpeggioType.MINOR_9,
        ]
        for arp in extended:
            assert isinstance(arp, ArpeggioType)

    def test_total_arpeggio_count(self) -> None:
        """Verify total number of arpeggio types matches spec (~25)."""
        assert len(ArpeggioType) >= 25


class TestMusicalKeyEnum:
    """Test MusicalKey enum values."""

    def test_all_12_chromatic_pitches(self) -> None:
        """Verify all 12 chromatic pitches are represented."""
        # Count unique pitch classes
        keys_values = [k.value for k in MusicalKey]
        # Should have at least 12 keys
        assert len(keys_values) >= 12

    def test_canonical_keys_list(self) -> None:
        """Verify canonical keys list has 12 unique entries."""
        assert len(CANONICAL_KEYS) == 12
        # All should be MusicalKey instances
        for key in CANONICAL_KEYS:
            assert isinstance(key, MusicalKey)

    def test_c_major_default(self) -> None:
        """C should be available as reference key."""
        assert MusicalKey.C.value == "C"


class TestGenerationRequest:
    """Test GenerationRequest validation."""

    def test_minimal_valid_scale_request(self) -> None:
        """Minimal valid scale request should pass."""
        req = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
        )
        assert req.content_type == GenerationType.SCALE
        assert req.definition == "ionian"
        assert req.key == MusicalKey.C  # Default
        assert req.octaves == 1  # Default

    def test_minimal_valid_arpeggio_request(self) -> None:
        """Minimal valid arpeggio request should pass."""
        req = GenerationRequest(
            content_type=GenerationType.ARPEGGIO,
            definition="maj7",
        )
        assert req.content_type == GenerationType.ARPEGGIO
        assert req.definition == "maj7"

    def test_full_scale_request(self) -> None:
        """Full scale request with all options should pass."""
        req = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="dorian",
            octaves=2,
            pattern="in_3rds",
            rhythm=RhythmType.EIGHTH_NOTES,
            key=MusicalKey.F,
            dynamics=DynamicType.CRESCENDO,
            articulation=ArticulationType.STACCATO,
            tempo_min_bpm=60,
            tempo_max_bpm=120,
        )
        assert req.octaves == 2
        assert req.pattern == "in_3rds"
        assert req.rhythm == RhythmType.EIGHTH_NOTES
        assert req.key == MusicalKey.F
        assert req.dynamics == DynamicType.CRESCENDO
        assert req.articulation == ArticulationType.STACCATO
        assert req.tempo_min_bpm == 60
        assert req.tempo_max_bpm == 120

    def test_invalid_scale_type_rejected(self) -> None:
        """Invalid scale type should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="not_a_real_scale",
            )
        assert "Invalid scale type" in str(exc_info.value)

    def test_invalid_arpeggio_type_rejected(self) -> None:
        """Invalid arpeggio type should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(
                content_type=GenerationType.ARPEGGIO,
                definition="not_a_real_arpeggio",
            )
        assert "Invalid arpeggio type" in str(exc_info.value)

    def test_lick_accepts_arbitrary_id(self) -> None:
        """Lick type should accept arbitrary definition IDs."""
        req = GenerationRequest(
            content_type=GenerationType.LICK,
            definition="ii_v_i_lick_001",
        )
        assert req.definition == "ii_v_i_lick_001"

    def test_invalid_octaves_rejected(self) -> None:
        """Octaves outside 1-3 should fail."""
        with pytest.raises(ValidationError):
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                octaves=4,  # type: ignore[arg-type]
            )

    def test_invalid_scale_pattern_rejected(self) -> None:
        """Invalid scale pattern should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                pattern="not_a_real_pattern",
            )
        assert "Invalid scale pattern" in str(exc_info.value)

    def test_invalid_arpeggio_pattern_rejected(self) -> None:
        """Invalid arpeggio pattern should fail validation."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(
                content_type=GenerationType.ARPEGGIO,
                definition="maj7",
                pattern="not_a_real_pattern",
            )
        assert "Invalid arpeggio pattern" in str(exc_info.value)

    def test_valid_scale_patterns_accepted(self) -> None:
        """All scale patterns should be accepted for scale type."""
        for pattern in ScalePattern:
            req = GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                pattern=pattern.value,
            )
            assert req.pattern == pattern.value

    def test_valid_arpeggio_patterns_accepted(self) -> None:
        """All arpeggio patterns should be accepted for arpeggio type."""
        for pattern in ArpeggioPattern:
            req = GenerationRequest(
                content_type=GenerationType.ARPEGGIO,
                definition="maj7",
                pattern=pattern.value,
            )
            assert req.pattern == pattern.value

    def test_tempo_range_valid(self) -> None:
        """Valid tempo range should pass."""
        req = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            tempo_min_bpm=40,
            tempo_max_bpm=200,
        )
        assert req.tempo_min_bpm == 40
        assert req.tempo_max_bpm == 200

    def test_tempo_range_inverted_rejected(self) -> None:
        """tempo_min > tempo_max should fail."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                tempo_min_bpm=200,
                tempo_max_bpm=60,
            )
        assert "tempo_min_bpm cannot exceed tempo_max_bpm" in str(exc_info.value)

    def test_tempo_below_minimum_rejected(self) -> None:
        """Tempo below 20 BPM should fail."""
        with pytest.raises(ValidationError):
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                tempo_min_bpm=10,
            )

    def test_tempo_above_maximum_rejected(self) -> None:
        """Tempo above 400 BPM should fail."""
        with pytest.raises(ValidationError):
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                tempo_max_bpm=500,
            )

    def test_definition_must_be_snake_case(self) -> None:
        """Definition must be lowercase snake_case."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(
                content_type=GenerationType.LICK,
                definition="InvalidCase",
            )
        assert "lowercase" in str(exc_info.value)

    def test_definition_cannot_start_with_number(self) -> None:
        """Definition cannot start with a number."""
        with pytest.raises(ValidationError):
            GenerationRequest(
                content_type=GenerationType.LICK,
                definition="123_invalid",
            )

    def test_range_bounds_valid(self) -> None:
        """Valid range bounds should pass."""
        req = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            range_low_midi=36,  # C2
            range_high_midi=70,  # Bb4
        )
        assert req.range_low_midi == 36
        assert req.range_high_midi == 70

    def test_range_bounds_inverted_rejected(self) -> None:
        """range_low_midi > range_high_midi should fail."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                range_low_midi=70,
                range_high_midi=36,
            )
        assert "range_low_midi cannot exceed range_high_midi" in str(exc_info.value)

    def test_range_bounds_midi_limits(self) -> None:
        """MIDI bounds must be 0-127."""
        # Valid edge cases
        GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            range_low_midi=0,
            range_high_midi=127,
        )
        # Invalid
        with pytest.raises(ValidationError):
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                range_low_midi=-1,
            )
        with pytest.raises(ValidationError):
            GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                range_high_midi=128,
            )

    def test_range_bounds_optional(self) -> None:
        """Range bounds are optional."""
        req = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
        )
        assert req.range_low_midi is None
        assert req.range_high_midi is None

    def test_range_bounds_can_be_equal(self) -> None:
        """Range low and high can be equal (single note)."""
        req = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            range_low_midi=60,
            range_high_midi=60,
        )
        assert req.range_low_midi == 60
        assert req.range_high_midi == 60


class TestRangeSpec:
    """Test RangeSpec model for resolving user pitch ranges."""

    def test_valid_range_spec(self) -> None:
        """Valid range spec should pass."""
        spec = RangeSpec(low_pitch="C2", high_pitch="Bb4")
        assert spec.low_pitch == "C2"
        assert spec.high_pitch == "Bb4"

    def test_midi_conversion_natural_notes(self) -> None:
        """Natural notes should convert to correct MIDI values."""
        spec = RangeSpec(low_pitch="C4", high_pitch="C5")
        assert spec.low_midi == 60  # Middle C
        assert spec.high_midi == 72  # C5

    def test_midi_conversion_sharps(self) -> None:
        """Sharp notes should convert correctly."""
        spec = RangeSpec(low_pitch="F#3", high_pitch="G#5")
        assert spec.low_midi == 54  # F#3
        assert spec.high_midi == 80  # G#5

    def test_midi_conversion_flats(self) -> None:
        """Flat notes should convert correctly."""
        spec = RangeSpec(low_pitch="Bb2", high_pitch="Eb5")
        assert spec.low_midi == 46  # Bb2
        assert spec.high_midi == 75  # Eb5

    def test_span_calculations(self) -> None:
        """Span should calculate correctly."""
        spec = RangeSpec(low_pitch="C4", high_pitch="C6")
        assert spec.span_semitones == 24
        assert spec.span_octaves == 2.0

    def test_span_fractional_octaves(self) -> None:
        """Fractional octave spans should work."""
        spec = RangeSpec(low_pitch="C4", high_pitch="G4")  # P5 = 7 semitones
        assert spec.span_semitones == 7
        assert spec.span_octaves == pytest.approx(7 / 12)

    def test_inverted_range_rejected(self) -> None:
        """low_pitch above high_pitch should fail."""
        with pytest.raises(ValidationError) as exc_info:
            RangeSpec(low_pitch="C5", high_pitch="C4")
        assert "must be below" in str(exc_info.value)

    def test_invalid_pitch_format_rejected(self) -> None:
        """Invalid pitch format should fail."""
        with pytest.raises(ValueError):
            RangeSpec(low_pitch="X4", high_pitch="C5")

    def test_low_register_pitches(self) -> None:
        """Low register pitches should work."""
        spec = RangeSpec(low_pitch="E1", high_pitch="C3")
        assert spec.low_midi == 28  # E1
        assert spec.high_midi == 48  # C3

    def test_negative_octave_pitches(self) -> None:
        """Negative octave pitches (below C0) should work."""
        spec = RangeSpec(low_pitch="C-1", high_pitch="C0")
        assert spec.low_midi == 0  # C-1 (lowest MIDI)
        assert spec.high_midi == 12  # C0

    def test_typical_brass_range(self) -> None:
        """Typical trumpet range should work."""
        spec = RangeSpec(low_pitch="E3", high_pitch="C6")
        assert spec.span_semitones == 32
        assert spec.span_octaves == pytest.approx(32 / 12)

    def test_typical_voice_range(self) -> None:
        """Typical vocal range should work."""
        spec = RangeSpec(low_pitch="C3", high_pitch="G5")
        assert spec.low_midi == 48
        assert spec.high_midi == 79


class TestPitchEvent:
    """Test PitchEvent model."""

    def test_valid_pitch_event(self) -> None:
        """Valid pitch event should pass."""
        event = PitchEvent(
            midi_note=60,
            pitch_name="C4",
            duration_beats=1.0,
            offset_beats=0.0,
        )
        assert event.midi_note == 60
        assert event.pitch_name == "C4"
        assert event.duration_beats == 1.0
        assert event.velocity == 80  # Default

    def test_pitch_event_with_all_fields(self) -> None:
        """Pitch event with all fields should pass."""
        event = PitchEvent(
            midi_note=72,
            pitch_name="C5",
            duration_beats=0.5,
            offset_beats=4.0,
            velocity=100,
            articulation=ArticulationType.STACCATO,
        )
        assert event.velocity == 100
        assert event.articulation == ArticulationType.STACCATO

    def test_midi_note_bounds(self) -> None:
        """MIDI note must be 0-127."""
        # Valid edge cases
        PitchEvent(midi_note=0, pitch_name="C-1", duration_beats=1.0, offset_beats=0.0)
        PitchEvent(
            midi_note=127, pitch_name="G9", duration_beats=1.0, offset_beats=0.0
        )

        # Invalid
        with pytest.raises(ValidationError):
            PitchEvent(
                midi_note=128, pitch_name="G#9", duration_beats=1.0, offset_beats=0.0
            )
        with pytest.raises(ValidationError):
            PitchEvent(
                midi_note=-1, pitch_name="B-2", duration_beats=1.0, offset_beats=0.0
            )

    def test_duration_must_be_positive(self) -> None:
        """Duration must be greater than 0."""
        with pytest.raises(ValidationError):
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=0.0, offset_beats=0.0
            )
        with pytest.raises(ValidationError):
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=-1.0, offset_beats=0.0
            )

    def test_offset_must_be_non_negative(self) -> None:
        """Offset must be >= 0."""
        # Valid at 0
        PitchEvent(midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0)
        # Invalid negative
        with pytest.raises(ValidationError):
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=-1.0
            )

    def test_velocity_bounds(self) -> None:
        """Velocity must be 1-127."""
        PitchEvent(
            midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0, velocity=1
        )
        PitchEvent(
            midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0, velocity=127
        )
        with pytest.raises(ValidationError):
            PitchEvent(
                midi_note=60,
                pitch_name="C4",
                duration_beats=1.0,
                offset_beats=0.0,
                velocity=0,
            )
        with pytest.raises(ValidationError):
            PitchEvent(
                midi_note=60,
                pitch_name="C4",
                duration_beats=1.0,
                offset_beats=0.0,
                velocity=128,
            )


class TestGenerationResponse:
    """Test GenerationResponse model."""

    def test_valid_response(self) -> None:
        """Valid generation response should pass."""
        events = [
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0
            ),
            PitchEvent(
                midi_note=62, pitch_name="D4", duration_beats=1.0, offset_beats=1.0
            ),
        ]
        response = GenerationResponse(
            content_type=GenerationType.SCALE,
            definition="ionian",
            key=MusicalKey.C,
            octaves=1,
            effective_octaves=1,
            pattern="straight_up",
            rhythm=RhythmType.QUARTER_NOTES,
            dynamics=DynamicType.NONE,
            articulation=ArticulationType.LEGATO,
            events=events,
            total_beats=2.0,
        )
        assert len(response.events) == 2
        assert response.total_beats == 2.0
        assert response.effective_octaves == 1

    def test_effective_octaves_less_than_requested(self) -> None:
        """effective_octaves can be less than octaves (range constrained)."""
        events = [
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0
            ),
        ]
        response = GenerationResponse(
            content_type=GenerationType.SCALE,
            definition="ionian",
            key=MusicalKey.C,
            octaves=2,  # Requested 2
            effective_octaves=1,  # Only got 1 due to range
            pattern=None,
            rhythm=RhythmType.QUARTER_NOTES,
            dynamics=DynamicType.NONE,
            articulation=ArticulationType.LEGATO,
            events=events,
            total_beats=1.0,
            range_used_low_midi=60,
            range_used_high_midi=72,
        )
        assert response.octaves == 2
        assert response.effective_octaves == 1

    def test_range_used_fields(self) -> None:
        """Response includes actual range used."""
        events = [
            PitchEvent(
                midi_note=48, pitch_name="C3", duration_beats=1.0, offset_beats=0.0
            ),
            PitchEvent(
                midi_note=72, pitch_name="C5", duration_beats=1.0, offset_beats=1.0
            ),
        ]
        response = GenerationResponse(
            content_type=GenerationType.SCALE,
            definition="ionian",
            key=MusicalKey.C,
            octaves=2,
            effective_octaves=2,
            pattern=None,
            rhythm=RhythmType.QUARTER_NOTES,
            dynamics=DynamicType.NONE,
            articulation=ArticulationType.LEGATO,
            events=events,
            total_beats=2.0,
            range_used_low_midi=48,
            range_used_high_midi=72,
        )
        assert response.range_used_low_midi == 48
        assert response.range_used_high_midi == 72

    def test_events_cannot_be_empty(self) -> None:
        """Events list cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            GenerationResponse(
                content_type=GenerationType.SCALE,
                definition="ionian",
                key=MusicalKey.C,
                octaves=1,
                effective_octaves=1,
                pattern=None,
                rhythm=RhythmType.QUARTER_NOTES,
                dynamics=DynamicType.NONE,
                articulation=ArticulationType.LEGATO,
                events=[],
                total_beats=0.0,
            )
        assert "events cannot be empty" in str(exc_info.value)

    def test_response_with_capabilities(self) -> None:
        """Response can include required capabilities."""
        events = [
            PitchEvent(
                midi_note=60, pitch_name="C4", duration_beats=1.0, offset_beats=0.0
            ),
        ]
        response = GenerationResponse(
            content_type=GenerationType.SCALE,
            definition="ionian",
            key=MusicalKey.C,
            octaves=1,
            effective_octaves=1,
            pattern=None,
            rhythm=RhythmType.QUARTER_NOTES,
            dynamics=DynamicType.NONE,
            articulation=ArticulationType.LEGATO,
            events=events,
            total_beats=1.0,
            capabilities_required=["scale_major_1_octave", "rhythm_quarter_notes"],
        )
        assert len(response.capabilities_required) == 2


class TestGenerationPreview:
    """Test GenerationPreview model."""

    def test_valid_preview(self) -> None:
        """Valid preview should pass."""
        preview = GenerationPreview(
            content_type=GenerationType.SCALE,
            definition="dorian",
            key=MusicalKey.F,
            display_name="F Dorian Scale, 2 octaves",
            estimated_notes=15,
            estimated_beats=15.0,
            difficulty_tier=2,
        )
        assert preview.display_name == "F Dorian Scale, 2 octaves"
        assert preview.estimated_notes == 15

    def test_estimated_notes_must_be_positive(self) -> None:
        """estimated_notes must be >= 1."""
        with pytest.raises(ValidationError):
            GenerationPreview(
                content_type=GenerationType.SCALE,
                definition="ionian",
                key=MusicalKey.C,
                display_name="C Major Scale",
                estimated_notes=0,
                estimated_beats=1.0,
            )

    def test_estimated_beats_must_be_positive(self) -> None:
        """estimated_beats must be > 0."""
        with pytest.raises(ValidationError):
            GenerationPreview(
                content_type=GenerationType.SCALE,
                definition="ionian",
                key=MusicalKey.C,
                display_name="C Major Scale",
                estimated_notes=8,
                estimated_beats=0.0,
            )

    def test_difficulty_tier_bounds(self) -> None:
        """difficulty_tier must be 1-5."""
        # Valid
        GenerationPreview(
            content_type=GenerationType.SCALE,
            definition="ionian",
            key=MusicalKey.C,
            display_name="Test",
            estimated_notes=1,
            estimated_beats=1.0,
            difficulty_tier=1,
        )
        GenerationPreview(
            content_type=GenerationType.SCALE,
            definition="ionian",
            key=MusicalKey.C,
            display_name="Test",
            estimated_notes=1,
            estimated_beats=1.0,
            difficulty_tier=5,
        )
        # Invalid
        with pytest.raises(ValidationError):
            GenerationPreview(
                content_type=GenerationType.SCALE,
                definition="ionian",
                key=MusicalKey.C,
                display_name="Test",
                estimated_notes=1,
                estimated_beats=1.0,
                difficulty_tier=0,
            )
        with pytest.raises(ValidationError):
            GenerationPreview(
                content_type=GenerationType.SCALE,
                definition="ionian",
                key=MusicalKey.C,
                display_name="Test",
                estimated_notes=1,
                estimated_beats=1.0,
                difficulty_tier=6,
            )


class TestRhythmTypeEnum:
    """Test RhythmType enum completeness."""

    def test_sustained_rhythms_exist(self) -> None:
        """Sustained rhythm types should exist."""
        assert RhythmType.WHOLE_NOTES.value == "whole_notes"
        assert RhythmType.HALF_NOTES.value == "half_notes"

    def test_subdivision_rhythms_exist(self) -> None:
        """Subdivision rhythm types should exist."""
        assert RhythmType.QUARTER_NOTES.value == "quarter_notes"
        assert RhythmType.EIGHTH_NOTES.value == "eighth_notes"
        assert RhythmType.SIXTEENTH_NOTES.value == "sixteenth_notes"

    def test_triplet_rhythms_exist(self) -> None:
        """Triplet rhythm types should exist."""
        assert RhythmType.EIGHTH_TRIPLETS.value == "eighth_triplets"

    def test_swing_rhythms_exist(self) -> None:
        """Swing rhythm types should exist."""
        assert RhythmType.SWING_EIGHTHS.value == "swing_eighths"
        assert RhythmType.SCOTCH_SNAP.value == "scotch_snap"


class TestDynamicTypeEnum:
    """Test DynamicType enum completeness."""

    def test_all_dynamic_types_exist(self) -> None:
        """All specified dynamic types should exist."""
        expected = ["none", "crescendo", "decrescendo", "terraced", "accented", "hairpin"]
        for value in expected:
            assert any(d.value == value for d in DynamicType), f"Missing: {value}"


class TestArticulationTypeEnum:
    """Test ArticulationType enum completeness."""

    def test_all_articulation_types_exist(self) -> None:
        """All specified articulation types should exist."""
        expected = ["legato", "staccato", "tenuto", "accent", "marcato", "mixed"]
        for value in expected:
            assert any(a.value == value for a in ArticulationType), f"Missing: {value}"


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestPitchToMidi:
    """Test _pitch_to_midi helper function."""

    def test_middle_c(self) -> None:
        """C4 should be MIDI 60."""
        from app.schemas.generation_schemas import _pitch_to_midi
        assert _pitch_to_midi("C4") == 60

    def test_a440(self) -> None:
        """A4 should be MIDI 69."""
        from app.schemas.generation_schemas import _pitch_to_midi
        assert _pitch_to_midi("A4") == 69

    def test_with_sharp(self) -> None:
        """C#4 should be MIDI 61."""
        from app.schemas.generation_schemas import _pitch_to_midi
        assert _pitch_to_midi("C#4") == 61

    def test_with_flat(self) -> None:
        """Bb4 should be MIDI 70."""
        from app.schemas.generation_schemas import _pitch_to_midi
        assert _pitch_to_midi("Bb4") == 70

    def test_empty_string_returns_default(self) -> None:
        """Empty string returns middle C (60)."""
        from app.schemas.generation_schemas import _pitch_to_midi
        assert _pitch_to_midi("") == 60

    def test_invalid_format_raises(self) -> None:
        """Invalid pitch format raises ValueError."""
        from app.schemas.generation_schemas import _pitch_to_midi
        with pytest.raises(ValueError, match="Invalid pitch format"):
            _pitch_to_midi("invalid")

    def test_negative_octave(self) -> None:
        """C-1 should be MIDI 0."""
        from app.schemas.generation_schemas import _pitch_to_midi
        assert _pitch_to_midi("C-1") == 0


class TestMidiToPitch:
    """Test _midi_to_pitch helper function."""

    def test_middle_c(self) -> None:
        """MIDI 60 should be C4."""
        from app.schemas.generation_schemas import _midi_to_pitch
        assert _midi_to_pitch(60) == "C4"

    def test_a440(self) -> None:
        """MIDI 69 should be A4."""
        from app.schemas.generation_schemas import _midi_to_pitch
        assert _midi_to_pitch(69) == "A4"

    def test_sharp_note(self) -> None:
        """MIDI 61 should be C#4."""
        from app.schemas.generation_schemas import _midi_to_pitch
        assert _midi_to_pitch(61) == "C#4"

    def test_low_note(self) -> None:
        """MIDI 0 should be C-1."""
        from app.schemas.generation_schemas import _midi_to_pitch
        assert _midi_to_pitch(0) == "C-1"

    def test_high_note(self) -> None:
        """MIDI 127 should be G9."""
        from app.schemas.generation_schemas import _midi_to_pitch
        assert _midi_to_pitch(127) == "G9"


class TestChordProgressionRequest:
    """Test ChordProgressionRequest validation."""

    def test_valid_request(self) -> None:
        """Valid request with proper range."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.SCALES,
            chords=[ChordEvent(symbol="Cmaj7", duration_beats=4)],
            range_low_midi=48,
            range_high_midi=72,
        )
        assert request.range_low_midi == 48
        assert request.range_high_midi == 72

    def test_invalid_range_raises(self) -> None:
        """Range low > high should raise ValidationError."""
        with pytest.raises(ValidationError, match="range_low_midi cannot exceed"):
            ChordProgressionRequest(
                content_type=ChordProgressionContentType.SCALES,
                chords=[ChordEvent(symbol="Cmaj7", duration_beats=4)],
                range_low_midi=80,
                range_high_midi=60,
            )

    def test_equal_range_allowed(self) -> None:
        """Equal range values should be allowed."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.ARPEGGIOS,
            chords=[ChordEvent(symbol="Am7", duration_beats=4)],
            range_low_midi=60,
            range_high_midi=60,
        )
        assert request.range_low_midi == 60

    def test_none_values_allowed(self) -> None:
        """Both None values should be allowed (use defaults)."""
        request = ChordProgressionRequest(
            content_type=ChordProgressionContentType.GUIDE_TONES,
            chords=[ChordEvent(symbol="G7", duration_beats=2)],
        )
        assert request.range_low_midi is None
        assert request.range_high_midi is None
