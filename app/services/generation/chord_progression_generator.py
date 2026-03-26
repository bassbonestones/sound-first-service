"""Chord Progression Generator Service.

Generates musical content (scales, arpeggios, guide tones) over chord changes.
Uses the chord-scale mapping to determine appropriate scales/arpeggios for each chord.

Usage:
    from app.services.generation.chord_progression_generator import (
        generate_over_changes,
    )

    request = ChordProgressionRequest(
        content_type=ChordProgressionContentType.SCALES,
        chords=[
            ChordEvent(symbol="Dm7", duration_beats=4),
            ChordEvent(symbol="G7", duration_beats=4),
            ChordEvent(symbol="Cmaj7", duration_beats=4),
        ],
        rhythm=RhythmType.EIGHTH_NOTES,
    )
    response = generate_over_changes(request)
"""
import math
from typing import List, Optional, Tuple

from app.schemas.generation_schemas import (
    ArpeggioType,
    ChordEvent,
    ChordProgressionContentType,
    ChordProgressionRequest,
    ChordProgressionResponse,
    ChordSegmentResponse,
    GenerationType,
    MusicalKey,
    PitchEvent,
    RhythmType,
    ScaleType,
)
from app.services.chord_scale_mapping import (
    ChordCategory,
    get_scale_for_chord_simple,
    get_scales_for_chord,
)
from .pitch_generator import PitchSequenceGenerator, get_key_offset
from .rhythm_applicator import apply_rhythm, get_rhythm_note_duration
from .enharmonic_spelling import midi_to_pitch_name_in_key


# =============================================================================
# Constants
# =============================================================================

# Map chord root names to MusicalKey enum
# This handles enharmonic equivalents
ROOT_TO_KEY: dict[str, MusicalKey] = {
    "C": MusicalKey.C,
    "C#": MusicalKey.C_SHARP,
    "Db": MusicalKey.D_FLAT,
    "D": MusicalKey.D,
    "D#": MusicalKey.D_SHARP,
    "Eb": MusicalKey.E_FLAT,
    "E": MusicalKey.E,
    "F": MusicalKey.F,
    "F#": MusicalKey.F_SHARP,
    "Gb": MusicalKey.G_FLAT,
    "G": MusicalKey.G,
    "G#": MusicalKey.G_SHARP,
    "Ab": MusicalKey.A_FLAT,
    "A": MusicalKey.A,
    "A#": MusicalKey.A_SHARP,
    "Bb": MusicalKey.B_FLAT,
    "B": MusicalKey.B,
    # Edge cases
    "Cb": MusicalKey.B,  # Enharmonic to B
    "Fb": MusicalKey.E,  # Enharmonic to E
    "E#": MusicalKey.F,  # Enharmonic to F
    "B#": MusicalKey.C,  # Enharmonic to C
}

# Map chord categories to typical arpeggios
CATEGORY_TO_ARPEGGIO: dict[ChordCategory, ArpeggioType] = {
    ChordCategory.MAJOR: ArpeggioType.MAJOR,
    ChordCategory.MAJOR_7: ArpeggioType.MAJOR_7,
    ChordCategory.DOMINANT: ArpeggioType.DOMINANT_7,
    ChordCategory.MINOR: ArpeggioType.MINOR,
    ChordCategory.MINOR_7: ArpeggioType.MINOR_7,
    ChordCategory.MINOR_MAJOR_7: ArpeggioType.MINOR_MAJOR_7,
    ChordCategory.HALF_DIMINISHED: ArpeggioType.HALF_DIMINISHED,
    ChordCategory.DIMINISHED: ArpeggioType.DIMINISHED_7,
    ChordCategory.AUGMENTED: ArpeggioType.AUGMENTED,
    ChordCategory.SUSPENDED: ArpeggioType.SUS4,  # Default sus4
}

# Guide tone intervals from chord root (in semitones)
# Guide tones are typically the 3rd and 7th of the chord
GUIDE_TONE_INTERVALS: dict[ChordCategory, List[int]] = {
    ChordCategory.MAJOR: [4, 11],  # Major 3rd, Major 7th
    ChordCategory.MAJOR_7: [4, 11],  # Major 3rd, Major 7th
    ChordCategory.DOMINANT: [4, 10],  # Major 3rd, Minor 7th
    ChordCategory.MINOR: [3, 10],  # Minor 3rd, Minor 7th
    ChordCategory.MINOR_7: [3, 10],  # Minor 3rd, Minor 7th
    ChordCategory.MINOR_MAJOR_7: [3, 11],  # Minor 3rd, Major 7th
    ChordCategory.HALF_DIMINISHED: [3, 10],  # Minor 3rd, Minor 7th
    ChordCategory.DIMINISHED: [3, 9],  # Minor 3rd, Diminished 7th
    ChordCategory.AUGMENTED: [4, 8],  # Major 3rd, Augmented 5th (no 7th)
    ChordCategory.SUSPENDED: [5, 10],  # Perfect 4th, Minor 7th
}


# =============================================================================
# Helper Functions
# =============================================================================


def _root_to_key(root: str) -> MusicalKey:
    """Convert chord root string to MusicalKey enum.

    Args:
        root: Root note name like "C", "F#", "Bb"

    Returns:
        MusicalKey enum value

    Raises:
        ValueError: If root is not recognized
    """
    if root in ROOT_TO_KEY:
        return ROOT_TO_KEY[root]
    raise ValueError(f"Unrecognized chord root: {root}")


def _calculate_notes_for_duration(
    duration_beats: float,
    rhythm: RhythmType,
) -> int:
    """Calculate how many notes fit in a duration at the given rhythm.

    Args:
        duration_beats: Duration in beats
        rhythm: Rhythm type determining note value

    Returns:
        Number of notes that fit
    """
    note_duration = get_rhythm_note_duration(rhythm)
    return max(1, int(duration_beats / note_duration))


def _generate_scale_segment(
    root: str,
    scale_type: ScaleType,
    num_notes: int,
    rhythm: RhythmType,
    start_pitch: Optional[int] = None,
    range_low: Optional[int] = None,
    range_high: Optional[int] = None,
) -> Tuple[List[PitchEvent], int]:
    """Generate a scale segment for a chord duration.

    Args:
        root: Chord root note
        scale_type: Scale type to use
        num_notes: Number of notes to generate
        rhythm: Rhythm type for durations
        start_pitch: Starting MIDI pitch (for voice leading)
        range_low: Optional low range bound
        range_high: Optional high range bound

    Returns:
        Tuple of (list of PitchEvents, last MIDI note for voice leading)
    """
    key = _root_to_key(root)
    generator = PitchSequenceGenerator()

    # Generate enough scale pitches to cover the duration
    # We generate 2 octaves to have flexibility
    pitches = generator.generate_scale(
        scale_type=scale_type,
        octaves=2,
        key=key,
        range_low_midi=range_low,
        range_high_midi=range_high,
    )

    # If we have a start pitch, reorder scale to start near it
    if start_pitch is not None and pitches:
        # Find nearest pitch to start_pitch
        nearest_idx = min(
            range(len(pitches)),
            key=lambda i: abs(pitches[i] - start_pitch),
        )
        # Create a looping sequence from that point
        pitches = pitches[nearest_idx:] + pitches[:nearest_idx]

    # Build pitch sequence for the required number of notes
    # Simple approach: go up then down
    sequence = []
    ascending = True
    idx = 0

    for _ in range(num_notes):
        sequence.append(pitches[idx])

        # Move to next pitch
        if ascending:
            idx += 1
            if idx >= len(pitches):
                idx = len(pitches) - 2
                ascending = False
        else:
            idx -= 1
            if idx < 0:
                idx = 1
                ascending = True

    # Convert to pitch events with rhythm
    pitch_names = [
        midi_to_pitch_name_in_key(p, key) for p in sequence
    ]
    events = apply_rhythm(
        pitches=sequence,
        rhythm=rhythm,
        pitch_names=pitch_names,
    )

    # Trim to exact number of notes
    events = events[:num_notes]

    last_pitch = sequence[-1] if sequence else 60
    return events, last_pitch


def _generate_arpeggio_segment(
    root: str,
    arpeggio_type: ArpeggioType,
    num_notes: int,
    rhythm: RhythmType,
    start_pitch: Optional[int] = None,
    range_low: Optional[int] = None,
    range_high: Optional[int] = None,
) -> Tuple[List[PitchEvent], int]:
    """Generate an arpeggio segment for a chord duration.

    Args:
        root: Chord root note
        arpeggio_type: Arpeggio type to use
        num_notes: Number of notes to generate
        rhythm: Rhythm type for durations
        start_pitch: Starting MIDI pitch (for voice leading)
        range_low: Optional low range bound
        range_high: Optional high range bound

    Returns:
        Tuple of (list of PitchEvents, last MIDI note)
    """
    key = _root_to_key(root)
    generator = PitchSequenceGenerator()

    # Generate arpeggio pitches
    pitches = generator.generate_arpeggio(
        arpeggio_type=arpeggio_type,
        octaves=2,
        key=key,
        range_low_midi=range_low,
        range_high_midi=range_high,
    )

    if not pitches:
        # Fallback to root note
        pitches = [60 + get_key_offset(key)]

    # Build sequence looping through arpeggio
    sequence = []
    ascending = True
    idx = 0

    for _ in range(num_notes):
        sequence.append(pitches[idx % len(pitches)])
        if ascending:
            idx += 1
            if idx >= len(pitches):
                idx = len(pitches) - 2
                ascending = False
        else:
            idx -= 1
            if idx < 0:
                idx = 1
                ascending = True

    # Convert to pitch events
    pitch_names = [
        midi_to_pitch_name_in_key(p, key) for p in sequence
    ]
    events = apply_rhythm(
        pitches=sequence,
        rhythm=rhythm,
        pitch_names=pitch_names,
    )

    events = events[:num_notes]
    last_pitch = sequence[-1] if sequence else 60
    return events, last_pitch


def _generate_guide_tones_segment(
    root: str,
    category: ChordCategory,
    duration_beats: float,
    rhythm: RhythmType,
) -> Tuple[List[PitchEvent], int]:
    """Generate guide tones (3rd and 7th) for a chord.

    Args:
        root: Chord root note
        category: Chord category (determines intervals)
        duration_beats: Duration in beats
        rhythm: Rhythm type

    Returns:
        Tuple of (list of PitchEvents, last MIDI note)
    """
    key = _root_to_key(root)
    root_midi = 60 + get_key_offset(key)

    # Get guide tone intervals for this chord type
    intervals = GUIDE_TONE_INTERVALS.get(category, [4, 10])  # Default to dom7

    # Generate guide tones
    guide_tones = [root_midi + interval for interval in intervals]

    # For guide tones, we typically play each for half the duration
    note_duration = duration_beats / len(guide_tones)

    events = []
    for i, midi_note in enumerate(guide_tones):
        pitch_name = midi_to_pitch_name_in_key(midi_note, key)
        events.append(
            PitchEvent(
                midi_note=midi_note,
                pitch_name=pitch_name,
                duration_beats=note_duration,
                offset_beats=i * note_duration,
                velocity=80,
            )
        )

    last_pitch = guide_tones[-1] if guide_tones else root_midi
    return events, last_pitch


# =============================================================================
# Main Generation Function
# =============================================================================


def generate_over_changes(
    request: ChordProgressionRequest,
) -> ChordProgressionResponse:
    """Generate musical content over a chord progression.

    Args:
        request: The generation request with chords and parameters

    Returns:
        ChordProgressionResponse with events for each chord and combined events
    """
    segments: List[ChordSegmentResponse] = []
    all_events: List[PitchEvent] = []
    current_beat = 0.0
    last_pitch: Optional[int] = None

    for chord_event in request.chords:
        # Get chord analysis
        mapping = get_scales_for_chord(chord_event.symbol)
        root = mapping.root or "C"
        category = mapping.chord_category

        # Calculate notes for this duration
        num_notes = _calculate_notes_for_duration(
            chord_event.duration_beats,
            request.rhythm,
        )

        # Generate content based on type
        if request.content_type == ChordProgressionContentType.SCALES:
            # Get the best scale for this chord
            scale_type = get_scale_for_chord_simple(chord_event.symbol)
            events, last_pitch = _generate_scale_segment(
                root=root,
                scale_type=scale_type,
                num_notes=num_notes,
                rhythm=request.rhythm,
                start_pitch=last_pitch,
                range_low=request.range_low_midi,
                range_high=request.range_high_midi,
            )
            scale_used = scale_type.value

        elif request.content_type == ChordProgressionContentType.ARPEGGIOS:
            # Get the arpeggio for this chord type
            arpeggio_type = CATEGORY_TO_ARPEGGIO.get(
                category, ArpeggioType.MAJOR_7
            )
            events, last_pitch = _generate_arpeggio_segment(
                root=root,
                arpeggio_type=arpeggio_type,
                num_notes=num_notes,
                rhythm=request.rhythm,
                start_pitch=last_pitch,
                range_low=request.range_low_midi,
                range_high=request.range_high_midi,
            )
            scale_used = None

        else:  # GUIDE_TONES
            events, last_pitch = _generate_guide_tones_segment(
                root=root,
                category=category,
                duration_beats=chord_event.duration_beats,
                rhythm=request.rhythm,
            )
            scale_used = None

        # Offset event times to absolute position
        # Create new events with updated offset_beats
        offset_events = []
        for event in events:
            offset_events.append(
                PitchEvent(
                    midi_note=event.midi_note,
                    pitch_name=event.pitch_name,
                    duration_beats=event.duration_beats,
                    offset_beats=event.offset_beats + current_beat,
                    velocity=event.velocity,
                    articulation=event.articulation,
                )
            )
        events = offset_events

        # Build segment
        segment = ChordSegmentResponse(
            chord_symbol=chord_event.symbol,
            scale_used=scale_used,
            duration_beats=chord_event.duration_beats,
            events=events,
        )
        segments.append(segment)
        all_events.extend(events)
        current_beat += chord_event.duration_beats

    return ChordProgressionResponse(
        content_type=request.content_type,
        segments=segments,
        total_beats=current_beat,
        events=all_events,
    )
