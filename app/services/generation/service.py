"""Generation service for orchestrating content generation.

Provides a high-level service that coordinates pitch generation,
pattern application, rhythm application, and output formatting.
"""

from typing import List, Optional, Set, Tuple

from app.schemas.generation_schemas import (
    ArpeggioPattern,
    ArticulationType,
    DynamicType,
    GenerationRequest,
    GenerationResponse,
    GenerationType,
    MusicalKey,
    PitchEvent,
    PredictedSoftGates,
    RhythmType,
    ScalePattern,
    ScaleType,
    ArpeggioType,
    SCALE_PATTERN_CONSTRAINTS,
    WHOLE_NOTE_PATTERNS,
    HALF_NOTE_PATTERNS,
)
from app.capabilities import sort_capabilities_by_bit_index
from .pitch_generator import PitchSequenceGenerator, midi_to_pitch_name, get_key_offset
from .pattern_applicator import apply_scale_pattern, apply_arpeggio_pattern
from .rhythm_applicator import apply_rhythm
from .musicxml_output import events_to_musicxml
from .enharmonic_spelling import midi_to_pitch_name_in_key
from .scale_definitions import (
    get_transposed_scale_spellings,
    is_asymmetric_scale,
    get_scale_intervals_descending,
    DIRECTION_AWARE_SPELLING_SCALES,
    get_chromatic_pitch_names,
    get_scale_note_count,
)
from .tempo_definitions import (
    get_tempo_bounds,
    validate_tempo_for_rhythm,
)
from .valid_pool_calculator import get_valid_pool_calculator
from .soft_gate_predictor import predict_soft_gates


class GenerationService:
    """Orchestrates the content generation pipeline.
    
    The pipeline:
    1. Generate raw pitches (PitchSequenceGenerator)
    2. Apply pattern algorithm (pattern_applicator)
    3. Apply rhythm template (rhythm_applicator)
    4. Build response with metadata
    
    Example:
        service = GenerationService()
        response = service.generate(GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="dorian",
            octaves=2,
            pattern="in_3rds",
            rhythm=RhythmType.EIGHTH_NOTES,
            key=MusicalKey.F,
        ))
    """
    
    def __init__(self) -> None:
        """Initialize the service with a pitch generator."""
        self._pitch_generator = PitchSequenceGenerator()
    
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate musical content from a request.
        
        Args:
            request: The generation parameters.
            
        Returns:
            GenerationResponse with pitch events and metadata.
            
        Raises:
            ValueError: If content_type is LICK (not yet supported).
        """
        if request.content_type == GenerationType.LICK:
            raise ValueError(
                "Lick generation is not yet supported. "
                "Use SCALE or ARPEGGIO content types."
            )
        
        # Step 1: Validate rhythm/pattern compatibility for scales
        # Whole notes and half notes are only allowed with simple patterns
        pattern = request.pattern
        if pattern is not None and request.content_type == GenerationType.SCALE:
            if request.rhythm == RhythmType.WHOLE_NOTES and pattern not in WHOLE_NOTE_PATTERNS:
                raise ValueError(
                    f"whole_notes rhythm is only allowed with patterns: "
                    f"straight_up, straight_down"
                )
            if request.rhythm == RhythmType.HALF_NOTES and pattern not in HALF_NOTE_PATTERNS:
                raise ValueError(
                    f"half_notes rhythm is only allowed with patterns: "
                    f"straight_up, straight_down, straight_up_down, straight_down_up"
                )
        
        # Step 2: Generate raw pitches
        pitches, effective_octaves = self._generate_pitches(request)
        
        # Step 3: Apply pattern if specified
        pitches = self._apply_pattern(pitches, request)
        
        # Step 4: Generate pitch names with proper scale-degree-aware spelling
        # Each scale type defines canonical spellings in C which are transposed
        pitch_names = self._generate_pitch_names(pitches, request)
        
        # Step 5: Apply rhythm to get PitchEvents
        # Global rule: if final note ends off-beat, extend and add quarter "do"
        events = apply_rhythm(
            pitches=pitches,
            rhythm=request.rhythm,
            pitch_names=pitch_names,
        )
        
        # Step 6: Apply articulation to events if not legato
        if request.articulation != ArticulationType.LEGATO:
            events = self._apply_articulation(events, request.articulation)
        
        # Step 7: Calculate metadata
        total_beats = sum(e.duration_beats for e in events)
        range_low = min(e.midi_note for e in events) if events else None
        range_high = max(e.midi_note for e in events) if events else None
        
        # Build tempo range from rhythm-appropriate bounds
        # Always include tempo bounds; user overrides are clamped to valid range
        rhythm_bounds = get_tempo_bounds(request.rhythm)
        if request.tempo_min_bpm is not None or request.tempo_max_bpm is not None:
            # User provided explicit bounds - clamp to valid range for this rhythm
            min_bpm = validate_tempo_for_rhythm(
                request.rhythm,
                request.tempo_min_bpm or rhythm_bounds.min_bpm,
                clamp=True,
            )
            max_bpm = validate_tempo_for_rhythm(
                request.rhythm,
                request.tempo_max_bpm or rhythm_bounds.max_bpm,
                clamp=True,
            )
            tempo_range: Tuple[int, int] = (min_bpm, max_bpm)
        else:
            # Use rhythm-appropriate defaults
            tempo_range = rhythm_bounds.as_tuple()
        
        # Compute required capabilities for this generation
        required_caps = self._compute_required_capabilities(request)
        
        # Compute predicted soft gates for difficulty estimation
        soft_gates_result = predict_soft_gates(request)
        predicted_gates = PredictedSoftGates(
            interval_sustained_stage=soft_gates_result.interval_sustained_stage,
            interval_hazard_stage=soft_gates_result.interval_hazard_stage,
            rhythm_complexity_score=soft_gates_result.rhythm_complexity_score,
            tonal_complexity_stage=soft_gates_result.tonal_complexity_stage,
            accidental_count=soft_gates_result.accidental_count,
            max_interval_semitones=soft_gates_result.max_interval_semitones,
            interval_p75_semitones=soft_gates_result.interval_p75_semitones,
        )
        
        return GenerationResponse(
            content_type=request.content_type,
            definition=request.definition,
            key=request.key,
            octaves=request.octaves,
            pattern=request.pattern,
            rhythm=request.rhythm,
            dynamics=request.dynamics,
            articulation=request.articulation,
            effective_octaves=effective_octaves,
            range_used_low_midi=range_low,
            range_used_high_midi=range_high,
            events=events,
            total_beats=total_beats,
            tempo_range=tempo_range,
            capabilities_required=sort_capabilities_by_bit_index(list(required_caps)),
            predicted_soft_gates=predicted_gates,
        )
    
    def generate_musicxml(
        self,
        request: GenerationRequest,
        title: Optional[str] = None,
    ) -> str:
        """Generate content and return as MusicXML string.
        
        Args:
            request: The generation parameters.
            title: Optional title for the MusicXML document.
            
        Returns:
            MusicXML string representation of the generated content.
        """
        response = self.generate(request)
        
        if title is None:
            title = self._generate_title(request)
        
        return events_to_musicxml(
            events=response.events,
            title=title,
            key=request.key,
            rhythm=request.rhythm,
        )
    
    def _generate_pitches(
        self,
        request: GenerationRequest,
    ) -> Tuple[List[int], int]:
        """Generate raw pitches from the request."""
        return self._pitch_generator.generate_from_request(
            request=request,
            ascending=True,
        )
    
    def _generate_pitch_names(
        self,
        pitches: List[int],
        request: GenerationRequest,
    ) -> List[str]:
        """Generate pitch names using scale-degree-aware spelling.
        
        For scales, uses the canonical spellings defined in C, transposed
        to the target key. For arpeggios and other content, falls back
        to key-signature-aware spelling.
        
        For direction-aware scales (like chromatic), uses sharps when
        ascending and flats when descending.
        """
        if request.content_type == GenerationType.SCALE:
            try:
                scale_type = ScaleType(request.definition)
                key_semitones = get_key_offset(request.key)
                key_name = request.key.value
                
                # Special handling for chromatic scale: use leading tone rule
                # (sharps lead up, flats lead down based on next note)
                if scale_type == ScaleType.CHROMATIC:
                    return get_chromatic_pitch_names(pitches, key_name)
                
                # Get transposed scale spellings
                scale_spellings = get_transposed_scale_spellings(scale_type, key_semitones, key_name)
                
                # Build a mapping from pitch class to name (ascending)
                root_midi = key_semitones + 60  # C4 transposed to key
                pitch_class_to_name_asc: dict[int, str] = {}
                
                cumulative = 0
                for i, name in enumerate(scale_spellings):
                    pitch_class = (root_midi + cumulative) % 12
                    pitch_class_to_name_asc[pitch_class] = name
                    if i < len(scale_spellings) - 1:
                        from .scale_definitions import get_scale_intervals
                        intervals = get_scale_intervals(scale_type)
                        cumulative += intervals[i]
                
                # For direction-aware scales (like chromatic), build descending map
                pitch_class_to_name_desc: dict[int, str] = {}
                if scale_type in DIRECTION_AWARE_SPELLING_SCALES:
                    from .scale_definitions import get_transposed_scale_spellings_descending
                    desc_spellings = get_transposed_scale_spellings_descending(
                        scale_type, key_semitones, key_name
                    )
                    cumulative = 0
                    for i, name in enumerate(desc_spellings):
                        pitch_class = (root_midi + cumulative) % 12
                        pitch_class_to_name_desc[pitch_class] = name
                        if i < len(desc_spellings) - 1:
                            from .scale_definitions import get_scale_intervals
                            intervals = get_scale_intervals(scale_type)
                            cumulative += intervals[i]
                
                # For asymmetric scales, also add descending pitch spellings
                # (they may have different pitch classes, e.g., A vs Ab)
                if is_asymmetric_scale(scale_type):
                    from .scale_definitions import get_transposed_scale_spellings_descending
                    desc_spellings = get_transposed_scale_spellings_descending(
                        scale_type, key_semitones, key_name
                    )
                    desc_intervals = get_scale_intervals_descending(scale_type)
                    
                    cumulative = 0
                    for i, name in enumerate(desc_spellings):
                        pitch_class = (root_midi + cumulative) % 12
                        # Only add if not already present (ascending takes precedence)
                        if pitch_class not in pitch_class_to_name_asc:
                            pitch_class_to_name_asc[pitch_class] = name
                        if i < len(desc_spellings) - 1:
                            cumulative += desc_intervals[i]
                
                # Map each MIDI pitch to its name with octave
                result = []
                for i, midi in enumerate(pitches):
                    pitch_class = midi % 12
                    octave = (midi // 12) - 1
                    
                    # For direction-aware scales, choose spelling based on direction
                    pitch_name: Optional[str] = None
                    if scale_type in DIRECTION_AWARE_SPELLING_SCALES and pitch_class_to_name_desc:
                        # Look at next note to determine direction
                        # If no next note or same pitch, use ascending by default
                        if i < len(pitches) - 1 and pitches[i + 1] < midi:
                            # Descending - use flats
                            pitch_name = pitch_class_to_name_desc.get(pitch_class)
                        else:
                            # Ascending or stationary - use sharps
                            pitch_name = pitch_class_to_name_asc.get(pitch_class)
                    else:
                        pitch_name = pitch_class_to_name_asc.get(pitch_class)
                    
                    if pitch_name:
                        # Adjust octave for enharmonic spellings that cross the C boundary:
                        # - Cb is enharmonically B, but Cb belongs to the next octave
                        #   (Cb5 = B4 = MIDI 71, not Cb4 which would be MIDI 59)
                        # - B# is enharmonically C, but B# belongs to the previous octave
                        #   (B#3 = C4 = MIDI 60, not B#4 which would be MIDI 72)
                        if pitch_name.startswith("Cb") or pitch_name.startswith("Cbb"):
                            octave += 1
                        elif pitch_name.startswith("B#") or pitch_name.startswith("B##"):
                            octave -= 1
                        result.append(f"{pitch_name}{octave}")
                    else:
                        # Fallback for chromatic passing tones
                        result.append(midi_to_pitch_name_in_key(midi, request.key.value))
                
                return result
                
            except (ValueError, KeyError):
                # Invalid scale type or not in spellings dict, fall back
                pass
        
        # Default: use key-signature-aware spelling
        key_name = request.key.value
        return [midi_to_pitch_name_in_key(p, key_name) for p in pitches]

    def _apply_pattern(
        self,
        pitches: List[int],
        request: GenerationRequest,
    ) -> List[int]:
        """Apply pattern algorithm to pitches if specified."""
        if request.pattern is None:
            return pitches
        
        # Store pattern to help mypy narrow the type
        pattern_name: str = request.pattern
        
        if request.content_type == GenerationType.SCALE:
            pattern = ScalePattern(pattern_name)
            
            # Check pattern constraints
            constraints = SCALE_PATTERN_CONSTRAINTS.get(pattern.value, {})
            
            # Validate asymmetric scale compatibility
            if constraints.get("requires_symmetric", False):
                try:
                    scale_type = ScaleType(request.definition)
                    if is_asymmetric_scale(scale_type):
                        raise ValueError(
                            f"Pattern '{pattern.value}' is incompatible with "
                            f"asymmetric scale '{scale_type.value}'. "
                            "This pattern requires a symmetric scale."
                        )
                except ValueError as e:
                    if "incompatible" in str(e):
                        raise
                    # Not a recognized scale type, allow it
            
            # Validate blocked scale types
            blocked_scales = constraints.get("blocked_scale_types", [])
            if blocked_scales and request.definition in blocked_scales:
                raise ValueError(
                    f"Pattern '{pattern.value}' is not compatible with "
                    f"scale type '{request.definition}'. "
                    "This pattern requires a diatonic scale structure."
                )
            
            # Apply octave limit from constraints
            max_octaves = constraints.get("max_octaves")
            if max_octaves is not None:
                # Calculate notes per octave based on actual scale type
                # e.g., diatonic = 7 notes/octave, chromatic = 12, pentatonic = 5
                try:
                    scale_type = ScaleType(request.definition)
                    notes_per_octave = get_scale_note_count(scale_type)
                except ValueError:
                    notes_per_octave = 7  # Default to diatonic
                
                # For N octaves: N * notes_per_octave + 1 (include top do)
                max_notes = max_octaves * notes_per_octave + 1
                pitches = pitches[:max_notes]
            
            # For asymmetric scales, generate descending pitches if needed
            descending_pitches: Optional[List[int]] = None
            try:
                scale_type = ScaleType(request.definition)
                if is_asymmetric_scale(scale_type):
                    # Generate descending pitches using descending intervals
                    descending_pitches = self._generate_descending_pitches(
                        pitches, scale_type, request
                    )
            except ValueError:
                pass  # Not a valid scale type, skip asymmetric handling
            
            return apply_scale_pattern(
                pitches, pattern, ascending=True, descending_pitches=descending_pitches
            )
        elif request.content_type == GenerationType.ARPEGGIO:
            arpeggio_pt = ArpeggioPattern(pattern_name)
            # Determine chord size from arpeggio type
            arpeggio_type = ArpeggioType(request.definition)
            chord_size = self._get_chord_size(arpeggio_type)
            return apply_arpeggio_pattern(
                pitches, arpeggio_pt, chord_size=chord_size, ascending=True
            )
        
        return pitches
    
    def _get_chord_size(self, arpeggio_type: ArpeggioType) -> int:
        """Determine chord size based on arpeggio type."""
        # Triads
        triads = {
            ArpeggioType.MAJOR, ArpeggioType.MINOR, 
            ArpeggioType.AUGMENTED, ArpeggioType.DIMINISHED,
            ArpeggioType.SUS4, ArpeggioType.SUS2,
        }
        if arpeggio_type in triads:
            return 3
        
        # 7th chords
        sevenths = {
            ArpeggioType.MAJOR_7, ArpeggioType.DOMINANT_7, ArpeggioType.MINOR_7,
            ArpeggioType.MINOR_MAJOR_7, ArpeggioType.HALF_DIMINISHED, 
            ArpeggioType.DIMINISHED_7, ArpeggioType.AUGMENTED_MAJOR_7, ArpeggioType.AUGMENTED_7,
            ArpeggioType.DOMINANT_7_SUS4,
        }
        if arpeggio_type in sevenths:
            return 4
        
        # Extended chords (9th, 11th, 13th)
        # These have 5+ notes but we treat pattern application at 4-note chunks
        return 4
    
    def _generate_descending_pitches(
        self,
        ascending_pitches: List[int],
        scale_type: ScaleType,
        request: GenerationRequest,
    ) -> List[int]:
        """Generate descending pitches for asymmetric scales.
        
        For scales like classical melodic minor, the descending form
        uses different intervals (natural minor) than the ascending form.
        
        Args:
            ascending_pitches: The ascending scale pitches.
            scale_type: The scale type (must be asymmetric).
            request: The generation request for key/octave info.
            
        Returns:
            List of MIDI pitches in descending order.
        """
        # Get descending intervals
        descending_intervals = get_scale_intervals_descending(scale_type)
        
        # Start from the top note and work down
        if not ascending_pitches:
            return []
        
        top_note = ascending_pitches[-1]
        
        # Build descending pitches from top
        # The intervals represent steps going UP, so we subtract going down
        result = [top_note]
        current = top_note
        
        # Number of octaves covered
        num_octaves = (len(ascending_pitches) - 1) // len(descending_intervals) + 1
        
        # For each octave, apply the descending intervals in reverse
        for _octave in range(num_octaves):
            # Go through intervals in reverse order to descend
            for interval in reversed(descending_intervals):
                current = current - interval
                if current >= ascending_pitches[0] - 12:  # Don't go too low
                    result.append(current)
        
        # Trim to match ascending length and ensure we end on the root
        root = ascending_pitches[0]
        # Find where the root is in our descending sequence
        result_trimmed = []
        for pitch in result:
            result_trimmed.append(pitch)
            if pitch == root:
                break
        
        return result_trimmed
    
    def _should_use_flats(self, key: MusicalKey) -> bool:
        """Determine if we should use flat notation for the key."""
        flat_keys = {
            MusicalKey.F, MusicalKey.B_FLAT, MusicalKey.E_FLAT,
            MusicalKey.A_FLAT, MusicalKey.D_FLAT, MusicalKey.G_FLAT,
        }
        return key in flat_keys
    
    def _apply_articulation(
        self,
        events: List[PitchEvent],
        articulation: ArticulationType,
    ) -> List[PitchEvent]:
        """Apply articulation marking to all events."""
        return [
            PitchEvent(
                midi_note=e.midi_note,
                pitch_name=e.pitch_name,
                duration_beats=e.duration_beats,
                offset_beats=e.offset_beats,
                velocity=e.velocity,
                articulation=articulation,
            )
            for e in events
        ]
    
    def _generate_title(self, request: GenerationRequest) -> str:
        """Generate a descriptive title for the content."""
        parts = [request.definition.replace("_", " ").title()]
        
        if request.content_type == GenerationType.SCALE:
            parts.append("Scale")
        elif request.content_type == GenerationType.ARPEGGIO:
            parts.append("Arpeggio")
        
        if request.pattern:
            parts.append(f"({request.pattern.replace('_', ' ')})")
        
        if request.key != MusicalKey.C:
            parts.insert(0, request.key.value)
        
        return " ".join(parts)
    
    def _compute_required_capabilities(
        self,
        request: GenerationRequest,
    ) -> Set[str]:
        """Compute capabilities required for the given generation request.
        
        Args:
            request: The generation request.
            
        Returns:
            Set of capability names required to perform this content.
        """
        calculator = get_valid_pool_calculator()
        required: Set[str] = set()
        
        # Track scale/arpeggio type for accidental calculation
        scale_type_for_accidentals: Optional[ScaleType] = None
        
        # Get interval capabilities based on content type and pattern
        if request.content_type == GenerationType.SCALE:
            try:
                scale_type = ScaleType(request.definition)
                scale_type_for_accidentals = scale_type
                pattern = ScalePattern(request.pattern) if request.pattern else ScalePattern.STRAIGHT_UP_DOWN
                interval_caps = calculator.get_required_capabilities_for_scale(scale_type, pattern)
                required.update(interval_caps)
            except ValueError:
                pass
        
        elif request.content_type == GenerationType.ARPEGGIO:
            try:
                arpeggio_type = ArpeggioType(request.definition)
                arp_pattern = ArpeggioPattern(request.pattern) if request.pattern else ArpeggioPattern.STRAIGHT_UP_DOWN
                interval_caps = calculator.get_required_capabilities_for_arpeggio(arpeggio_type, arp_pattern)
                required.update(interval_caps)
            except ValueError:
                pass
        
        # Add rhythm capabilities
        rhythm_caps = calculator.get_required_capabilities_for_rhythm(request.rhythm)
        required.update(rhythm_caps)
        
        # Add accidental capabilities based on scale + key combination
        if scale_type_for_accidentals is not None:
            accidental_caps = calculator.get_required_accidentals_for_scale_in_key(
                scale_type_for_accidentals, request.key
            )
            required.update(accidental_caps)
        else:
            # Fallback to basic key accidentals for arpeggios (for now)
            key_caps = calculator.get_required_capabilities_for_key(request.key)
            required.update(key_caps)
        
        return required


# Singleton instance for dependency injection
_generation_service: Optional[GenerationService] = None


def get_generation_service() -> GenerationService:
    """Get the generation service singleton.
    
    Returns:
        The GenerationService instance.
    """
    global _generation_service
    if _generation_service is None:
        _generation_service = GenerationService()
    return _generation_service
