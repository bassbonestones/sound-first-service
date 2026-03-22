"""Content generation engine.

Provides pure generators for scales, arpeggios, and musical patterns.
These generators are capability-agnostic - they produce what is requested.
Capability filtering is handled by a separate orchestration layer.
"""
from .scale_definitions import SCALE_INTERVALS, get_scale_intervals
from .arpeggio_definitions import ARPEGGIO_INTERVALS, get_arpeggio_intervals
from .pitch_generator import PitchSequenceGenerator
from .pattern_applicator import (
    apply_scale_pattern,
    apply_arpeggio_pattern,
    get_supported_scale_patterns,
    get_supported_arpeggio_patterns,
)
from .rhythm_applicator import (
    apply_rhythm,
    apply_rhythm_with_repeats,
    get_duration,
    get_cell_info,
    calculate_total_duration,
    calculate_measures,
    get_supported_rhythms,
    beats_to_seconds,
    seconds_to_beats,
    quantize_to_grid,
    create_rest_event,
    insert_rests_between_groups,
    RHYTHM_CELLS,
)
from .musicxml_output import (
    events_to_musicxml,
    generate_musicxml_from_request,
    midi_pitches_to_musicxml,
)
from .tempo_definitions import (
    TempoBounds,
    TEMPO_BOUNDS,
    get_tempo_bounds,
    get_default_tempo,
    validate_tempo_for_rhythm,
    get_supported_rhythms_with_bounds,
    MAX_NOTES_FOR_RHYTHM,
    get_max_notes_for_rhythm,
    validate_note_count_for_rhythm,
    get_compatible_rhythms_for_note_count,
)
from .service import GenerationService, get_generation_service

__all__ = [
    # Scale/arpeggio definitions
    "SCALE_INTERVALS",
    "get_scale_intervals",
    "ARPEGGIO_INTERVALS",
    "get_arpeggio_intervals",
    # Pitch generation
    "PitchSequenceGenerator",
    # Pattern application
    "apply_scale_pattern",
    "apply_arpeggio_pattern",
    "get_supported_scale_patterns",
    "get_supported_arpeggio_patterns",
    # Rhythm application
    "apply_rhythm",
    "apply_rhythm_with_repeats",
    "get_duration",
    "get_cell_info",
    "calculate_total_duration",
    "calculate_measures",
    "get_supported_rhythms",
    "beats_to_seconds",
    "seconds_to_beats",
    "quantize_to_grid",
    "create_rest_event",
    "insert_rests_between_groups",
    "RHYTHM_CELLS",
    # MusicXML output
    "events_to_musicxml",
    "generate_musicxml_from_request",
    "midi_pitches_to_musicxml",
    # Tempo definitions
    "TempoBounds",
    "TEMPO_BOUNDS",
    "get_tempo_bounds",
    "get_default_tempo",
    "validate_tempo_for_rhythm",
    "get_supported_rhythms_with_bounds",
    "MAX_NOTES_FOR_RHYTHM",
    "get_max_notes_for_rhythm",
    "validate_note_count_for_rhythm",
    "get_compatible_rhythms_for_note_count",
    # Service
    "GenerationService",
    "get_generation_service",
]
