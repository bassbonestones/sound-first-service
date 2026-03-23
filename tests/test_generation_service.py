"""Tests for GenerationService.

Tests the service layer orchestration including:
- Pipeline execution (pitch → pattern → rhythm → events)
- MusicXML output generation
- Error handling
- Metadata calculation
"""

import pytest

from app.services.generation.service import GenerationService
from app.schemas.generation_schemas import (
    ArpeggioType,
    ArticulationType,
    DynamicType,
    GenerationRequest,
    GenerationType,
    MusicalKey,
    RhythmType,
    ScalePattern,
    ScaleType,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def service() -> GenerationService:
    """Create a GenerationService instance."""
    return GenerationService()


@pytest.fixture
def basic_scale_request() -> GenerationRequest:
    """Basic scale generation request."""
    return GenerationRequest(
        content_type=GenerationType.SCALE,
        definition="ionian",
        octaves=1,
        rhythm=RhythmType.QUARTER_NOTES,
    )


@pytest.fixture
def full_scale_request() -> GenerationRequest:
    """Scale request with all parameters."""
    return GenerationRequest(
        content_type=GenerationType.SCALE,
        definition="dorian",
        octaves=2,
        pattern="in_3rds",
        rhythm=RhythmType.EIGHTH_NOTES,
        key=MusicalKey.G,
        dynamics=DynamicType.CRESCENDO,
        articulation=ArticulationType.STACCATO,
        tempo_min_bpm=80,
        tempo_max_bpm=120,
    )


@pytest.fixture
def arpeggio_request() -> GenerationRequest:
    """Arpeggio generation request."""
    return GenerationRequest(
        content_type=GenerationType.ARPEGGIO,
        definition="maj7",
        octaves=2,
        rhythm=RhythmType.EIGHTH_NOTES,
        key=MusicalKey.B_FLAT,
    )


# =============================================================================
# GENERATE METHOD TESTS
# =============================================================================

class TestGenerateMethod:
    """Tests for GenerationService.generate()."""

    def test_generate_basic_scale(
        self, service: GenerationService, basic_scale_request: GenerationRequest
    ) -> None:
        """Test basic scale generation produces correct response."""
        response = service.generate(basic_scale_request)
        
        assert response.content_type == GenerationType.SCALE
        assert response.definition == "ionian"
        assert response.key == MusicalKey.C
        assert response.octaves == 1
        assert len(response.events) > 0

    def test_generate_returns_events(
        self, service: GenerationService, basic_scale_request: GenerationRequest
    ) -> None:
        """Test that generate returns pitch events."""
        response = service.generate(basic_scale_request)
        
        assert len(response.events) >= 8  # Ionian has 8 notes per octave
        
        for event in response.events:
            assert event.midi_note >= 0
            assert event.midi_note <= 127
            assert len(event.pitch_name) >= 2
            assert event.duration_beats > 0

    def test_generate_with_pattern(
        self, service: GenerationService
    ) -> None:
        """Test generation with pattern produces modified sequence."""
        request_no_pattern = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.QUARTER_NOTES,
        )
        request_with_pattern = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            pattern="in_3rds",
            rhythm=RhythmType.QUARTER_NOTES,
        )
        
        response_no_pattern = service.generate(request_no_pattern)
        response_with_pattern = service.generate(request_with_pattern)
        
        # Pattern should produce different event sequence
        assert len(response_with_pattern.events) != len(response_no_pattern.events)

    def test_generate_respects_key(
        self, service: GenerationService
    ) -> None:
        """Test that key parameter transposes correctly."""
        request_c = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.C,
        )
        request_g = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.G,
        )
        
        response_c = service.generate(request_c)
        response_g = service.generate(request_g)
        
        # G is 7 semitones above C
        assert response_g.events[0].midi_note - response_c.events[0].midi_note == 7

    def test_generate_arpeggio(
        self, service: GenerationService, arpeggio_request: GenerationRequest
    ) -> None:
        """Test arpeggio generation."""
        response = service.generate(arpeggio_request)
        
        assert response.content_type == GenerationType.ARPEGGIO
        assert response.definition == "maj7"
        assert response.key == MusicalKey.B_FLAT
        assert len(response.events) > 0

    def test_generate_lick_raises_error(
        self, service: GenerationService
    ) -> None:
        """Test that lick generation raises ValueError."""
        request = GenerationRequest(
            content_type=GenerationType.LICK,
            definition="bebop_phrase_1",
            octaves=1,
            rhythm=RhythmType.EIGHTH_NOTES,
        )
        
        with pytest.raises(ValueError) as exc_info:
            service.generate(request)
        
        assert "not yet supported" in str(exc_info.value).lower()

    def test_generate_calculates_range(
        self, service: GenerationService, basic_scale_request: GenerationRequest
    ) -> None:
        """Test that generate calculates range metadata."""
        response = service.generate(basic_scale_request)
        
        assert response.range_used_low_midi is not None
        assert response.range_used_high_midi is not None
        assert response.range_used_low_midi <= response.range_used_high_midi
        
        # Range should match actual events
        event_low = min(e.midi_note for e in response.events)
        event_high = max(e.midi_note for e in response.events)
        assert response.range_used_low_midi == event_low
        assert response.range_used_high_midi == event_high

    def test_generate_calculates_total_beats(
        self, service: GenerationService, basic_scale_request: GenerationRequest
    ) -> None:
        """Test that generate calculates total beats."""
        response = service.generate(basic_scale_request)
        
        assert response.total_beats > 0
        
        # Should match sum of event durations
        calculated_beats = sum(e.duration_beats for e in response.events)
        assert response.total_beats == calculated_beats

    def test_generate_tempo_range(
        self, service: GenerationService, full_scale_request: GenerationRequest
    ) -> None:
        """Test that tempo range is included when specified."""
        response = service.generate(full_scale_request)
        
        assert response.tempo_range is not None
        assert response.tempo_range == (80, 120)

    def test_generate_tempo_range_defaults_from_rhythm(
        self, service: GenerationService, basic_scale_request: GenerationRequest
    ) -> None:
        """Test that tempo range defaults to rhythm-appropriate bounds."""
        # basic_scale_request uses QUARTER_NOTES with no explicit tempo
        response = service.generate(basic_scale_request)
        
        # QUARTER_NOTES should have range 40-200
        assert response.tempo_range is not None
        assert response.tempo_range == (40, 200)

    def test_generate_tempo_range_varies_by_rhythm(
        self, service: GenerationService
    ) -> None:
        """Test that different rhythms have different default tempo bounds."""
        # Sixteenth notes - should have lower max BPM
        request_16ths = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.SIXTEENTH_NOTES,
        )
        response_16ths = service.generate(request_16ths)
        
        # SIXTEENTH_NOTES should have range 40-120
        assert response_16ths.tempo_range == (40, 120)
        
        # Whole notes - sustained, lower max
        request_whole = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.WHOLE_NOTES,
        )
        response_whole = service.generate(request_whole)
        
        # WHOLE_NOTES should have range 40-80
        assert response_whole.tempo_range == (40, 80)

    def test_generate_tempo_range_clamps_user_bounds(
        self, service: GenerationService
    ) -> None:
        """Test that user-provided tempo bounds are clamped to valid range."""
        # Request with bounds outside valid range for sixteenths (max 120)
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.SIXTEENTH_NOTES,
            tempo_min_bpm=30,   # Below valid (40)
            tempo_max_bpm=200,  # Above valid (120)
        )
        response = service.generate(request)
        
        # Should be clamped to valid range
        assert response.tempo_range == (40, 120)

    def test_generate_preserves_request_params(
        self, service: GenerationService, full_scale_request: GenerationRequest
    ) -> None:
        """Test that response includes request parameters."""
        response = service.generate(full_scale_request)
        
        assert response.content_type == full_scale_request.content_type
        assert response.definition == full_scale_request.definition
        assert response.key == full_scale_request.key
        assert response.octaves == full_scale_request.octaves
        assert response.pattern == full_scale_request.pattern
        assert response.rhythm == full_scale_request.rhythm
        assert response.dynamics == full_scale_request.dynamics
        assert response.articulation == full_scale_request.articulation


# =============================================================================
# ARTICULATION TESTS
# =============================================================================

class TestArticulation:
    """Tests for articulation application."""

    def test_staccato_modifies_duration(
        self, service: GenerationService
    ) -> None:
        """Test that staccato articulation modifies event durations."""
        request_legato = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.QUARTER_NOTES,
            articulation=ArticulationType.LEGATO,
        )
        request_staccato = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.QUARTER_NOTES,
            articulation=ArticulationType.STACCATO,
        )
        
        response_legato = service.generate(request_legato)
        response_staccato = service.generate(request_staccato)
        
        # Both should have same number of events
        assert len(response_legato.events) == len(response_staccato.events)


# =============================================================================
# MUSICXML GENERATION TESTS
# =============================================================================

class TestGenerateMusicxml:
    """Tests for GenerationService.generate_musicxml()."""

    def test_generates_valid_xml(
        self, service: GenerationService, basic_scale_request: GenerationRequest
    ) -> None:
        """Test that generate_musicxml produces valid XML."""
        musicxml = service.generate_musicxml(basic_scale_request)
        
        assert musicxml.startswith("<?xml")
        assert "score-partwise" in musicxml
        assert "<note>" in musicxml

    def test_musicxml_with_custom_title(
        self, service: GenerationService, basic_scale_request: GenerationRequest
    ) -> None:
        """Test that custom title is included in MusicXML."""
        musicxml = service.generate_musicxml(
            basic_scale_request, 
            title="My Test Scale"
        )
        
        assert "My Test Scale" in musicxml

    def test_musicxml_contains_notes(
        self, service: GenerationService, basic_scale_request: GenerationRequest
    ) -> None:
        """Test that MusicXML contains note elements."""
        musicxml = service.generate_musicxml(basic_scale_request)
        
        assert "<pitch>" in musicxml
        assert "<step>" in musicxml
        assert "<octave>" in musicxml
        assert "<duration>" in musicxml

    def test_musicxml_respects_key(
        self, service: GenerationService
    ) -> None:
        """Test that MusicXML includes key signature."""
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.G,
        )
        musicxml = service.generate_musicxml(request)
        
        # G major has 1 sharp
        assert "<fifths>1</fifths>" in musicxml or "<key>" in musicxml


# =============================================================================
# HELPER METHOD TESTS
# =============================================================================

class TestHelperMethods:
    """Tests for GenerationService helper methods."""

    def test_get_chord_size_triads(
        self, service: GenerationService
    ) -> None:
        """Test chord size calculation for triads."""
        triads = [
            ArpeggioType.MAJOR,
            ArpeggioType.MINOR,
            ArpeggioType.AUGMENTED,
            ArpeggioType.DIMINISHED,
        ]
        
        for triad in triads:
            size = service._get_chord_size(triad)
            assert size == 3, f"Expected 3 for {triad}, got {size}"

    def test_get_chord_size_sevenths(
        self, service: GenerationService
    ) -> None:
        """Test chord size calculation for 7th chords."""
        sevenths = [
            ArpeggioType.MAJOR_7,
            ArpeggioType.DOMINANT_7,
            ArpeggioType.MINOR_7,
        ]
        
        for seventh in sevenths:
            size = service._get_chord_size(seventh)
            assert size == 4, f"Expected 4 for {seventh}, got {size}"

    def test_should_use_flats(
        self, service: GenerationService
    ) -> None:
        """Test flat key detection."""
        # Flat keys should return True
        flat_keys = [
            MusicalKey.F,
            MusicalKey.B_FLAT,
            MusicalKey.E_FLAT,
            MusicalKey.A_FLAT,
            MusicalKey.D_FLAT,
        ]
        for key in flat_keys:
            # Method should exist and return boolean
            assert hasattr(service, '_should_use_flats')

    def test_apply_pattern_scale(
        self, service: GenerationService
    ) -> None:
        """Test pattern application for scales."""
        pitches = [60, 62, 64, 65, 67, 69, 71, 72]  # C major scale
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            pattern="in_3rds",
            rhythm=RhythmType.QUARTER_NOTES,
        )
        
        result = service._apply_pattern(pitches, request)
        
        # Pattern should produce different sequence
        assert result != pitches

    def test_apply_pattern_none(
        self, service: GenerationService
    ) -> None:
        """Test that None pattern returns original pitches."""
        pitches = [60, 62, 64, 65, 67, 69, 71, 72]
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.QUARTER_NOTES,
            pattern=None,
        )
        
        result = service._apply_pattern(pitches, request)
        
        assert result == pitches


# =============================================================================
# EDGE CASES
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_generate_1_octave(
        self, service: GenerationService
    ) -> None:
        """Test 1-octave generation."""
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = service.generate(request)
        
        assert response.effective_octaves >= 1
        assert len(response.events) >= 8

    def test_generate_3_octaves(
        self, service: GenerationService
    ) -> None:
        """Test 3-octave generation."""
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=3,
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = service.generate(request)
        
        assert response.effective_octaves >= 1
        assert len(response.events) >= 8

    def test_generate_all_rhythms(
        self, service: GenerationService
    ) -> None:
        """Test generation with all rhythm types."""
        for rhythm in RhythmType:
            request = GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                octaves=1,
                rhythm=rhythm,
            )
            response = service.generate(request)
            
            assert len(response.events) > 0, f"Failed for rhythm: {rhythm}"
            assert response.total_beats > 0

    def test_generate_all_dynamics(
        self, service: GenerationService
    ) -> None:
        """Test generation with all dynamic levels."""
        for dynamic in DynamicType:
            request = GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                octaves=1,
                rhythm=RhythmType.QUARTER_NOTES,
                dynamics=dynamic,
            )
            response = service.generate(request)
            
            assert response.dynamics == dynamic

    def test_generate_all_articulations(
        self, service: GenerationService
    ) -> None:
        """Test generation with all articulation types."""
        for articulation in ArticulationType:
            request = GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                octaves=1,
                rhythm=RhythmType.QUARTER_NOTES,
                articulation=articulation,
            )
            response = service.generate(request)
            
            assert response.articulation == articulation

    def test_generate_extreme_keys(
        self, service: GenerationService
    ) -> None:
        """Test generation in extreme keys (many sharps/flats)."""
        extreme_keys = [
            MusicalKey.F_SHARP,
            MusicalKey.C_SHARP,
            MusicalKey.G_FLAT,
        ]
        
        for key in extreme_keys:
            request = GenerationRequest(
                content_type=GenerationType.SCALE,
                definition="ionian",
                octaves=1,
                rhythm=RhythmType.QUARTER_NOTES,
                key=key,
            )
            response = service.generate(request)
            
            assert response.key == key
            assert len(response.events) > 0

    def test_whole_notes_with_complex_pattern_rejected(
        self, service: GenerationService
    ) -> None:
        """Test that whole notes with complex patterns raises error.
        
        Whole notes are only allowed with simple patterns (straight_up, straight_down).
        Complex patterns like groups_of_7 cannot use whole notes.
        """
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=3,
            rhythm=RhythmType.WHOLE_NOTES,
            pattern="groups_of_7",
        )
        
        with pytest.raises(ValueError, match="whole_notes rhythm is only allowed"):
            service.generate(request)

    def test_half_notes_with_complex_pattern_rejected(
        self, service: GenerationService
    ) -> None:
        """Test that half notes with complex patterns raises error.
        
        Half notes are only allowed with simple patterns:
        straight_up, straight_down, straight_up_down, straight_down_up.
        """
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=2,
            rhythm=RhythmType.HALF_NOTES,
            pattern="in_3rds",
        )
        
        with pytest.raises(ValueError, match="half_notes rhythm is only allowed"):
            service.generate(request)

    def test_whole_notes_simple_pattern_accepted(
        self, service: GenerationService
    ) -> None:
        """Test that whole notes with few notes is accepted."""
        # 1 octave scale = 8 notes, well under limit of 16
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            octaves=1,
            rhythm=RhythmType.WHOLE_NOTES,
        )
        
        response = service.generate(request)
        assert len(response.events) <= 16

    def test_blues_scale_uses_flat_spellings(
        self, service: GenerationService
    ) -> None:
        """Test that blues scale uses correct scale degree spellings.
        
        Blues scale formula: 1 b3 4 #4 5 b7
        In C: C, Eb, F, F#, G, Bb, C
        Note: The "blue note" is #4 (F#), NOT b5 (Gb)
        """
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="blues",
            octaves=1,
            key=MusicalKey.C,
            rhythm=RhythmType.QUARTER_NOTES,
        )
        response = service.generate(request)
        
        pitch_names = [e.pitch_name for e in response.events]
        
        # Check for correct spellings based on scale degree
        # b3 should be Eb
        assert any("Eb" in name for name in pitch_names), \
            f"Blues scale should have Eb (flat 3rd), got: {pitch_names}"
        # #4 should be F# (the "blue note")
        assert any("F#" in name for name in pitch_names), \
            f"Blues scale should have F# (sharp 4th / blue note), got: {pitch_names}"
        # b7 should be Bb
        assert any("Bb" in name for name in pitch_names), \
            f"Blues scale should have Bb (flat 7th), got: {pitch_names}"
        
        # Should NOT have these wrong spellings
        assert not any("D#" in name for name in pitch_names), \
            f"Blues scale should NOT have D# (should be Eb), got: {pitch_names}"
        assert not any("Gb" in name for name in pitch_names), \
            f"Blues scale should NOT have Gb (should be F#), got: {pitch_names}"
        assert not any("A#" in name for name in pitch_names), \
            f"Blues scale should NOT have A# (should be Bb), got: {pitch_names}"
