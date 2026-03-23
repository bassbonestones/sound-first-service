"""Rhythm application layer for pitch sequences.

This module applies rhythm templates to pitch sequences,
converting raw MIDI pitches into timed musical events.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple

from app.schemas.generation_schemas import (
    PitchEvent,
    RhythmType,
)


# =============================================================================
# Duration Constants (in beats, quarter note = 1.0)
# =============================================================================

WHOLE_NOTE = 4.0
HALF_NOTE = 2.0
DOTTED_HALF_NOTE = 3.0
QUARTER_NOTE = 1.0
DOTTED_QUARTER = 1.5
EIGHTH_NOTE = 0.5
DOTTED_EIGHTH = 0.75
SIXTEENTH_NOTE = 0.25
EIGHTH_TRIPLET = 1.0 / 3.0  # 3 per beat

# Swing ratio (standard: 2:1, sometimes 3:1 for harder swing)
SWING_LONG = 2.0 / 3.0  # First note of swing pair
SWING_SHORT = 1.0 / 3.0  # Second note of swing pair


# =============================================================================
# Rhythm Pattern Definitions
# =============================================================================

@dataclass
class RhythmCell:
    """A rhythmic cell - a repeating pattern of durations."""
    durations: Tuple[float, ...]
    
    @property
    def cell_length(self) -> float:
        """Total length of the cell in beats."""
        return sum(self.durations)
    
    @property
    def notes_per_cell(self) -> int:
        """Number of notes in the cell."""
        return len(self.durations)


# Define rhythm cells for each rhythm type
RHYTHM_CELLS: dict[RhythmType, RhythmCell] = {
    # Sustained
    RhythmType.WHOLE_NOTES: RhythmCell((WHOLE_NOTE,)),
    RhythmType.HALF_NOTES: RhythmCell((HALF_NOTE,)),
    
    # Pulse
    RhythmType.QUARTER_NOTES: RhythmCell((QUARTER_NOTE,)),
    
    # Subdivisions
    RhythmType.EIGHTH_NOTES: RhythmCell((EIGHTH_NOTE,)),
    RhythmType.SIXTEENTH_NOTES: RhythmCell((SIXTEENTH_NOTE,)),
    
    # Triplets
    RhythmType.EIGHTH_TRIPLETS: RhythmCell((EIGHTH_TRIPLET,)),
    
    # Swing (pairs: long-short)
    RhythmType.SWING_EIGHTHS: RhythmCell((SWING_LONG, SWING_SHORT)),
    
    # Scotch snap (short-long)
    RhythmType.SCOTCH_SNAP: RhythmCell((SIXTEENTH_NOTE, DOTTED_EIGHTH)),
    
    # Dotted patterns
    RhythmType.DOTTED_QUARTER_EIGHTH: RhythmCell((DOTTED_QUARTER, EIGHTH_NOTE)),
    RhythmType.DOTTED_EIGHTH_SIXTEENTH: RhythmCell((DOTTED_EIGHTH, SIXTEENTH_NOTE)),
    
    # Compound cells (multi-note patterns)
    RhythmType.SIXTEENTH_EIGHTH_SIXTEENTH: RhythmCell(
        (SIXTEENTH_NOTE, EIGHTH_NOTE, SIXTEENTH_NOTE)
    ),
    RhythmType.EIGHTH_SIXTEENTH_SIXTEENTH: RhythmCell(
        (EIGHTH_NOTE, SIXTEENTH_NOTE, SIXTEENTH_NOTE)
    ),
    RhythmType.SIXTEENTH_SIXTEENTH_EIGHTH: RhythmCell(
        (SIXTEENTH_NOTE, SIXTEENTH_NOTE, EIGHTH_NOTE)
    ),
    
    # Syncopated: 8th-quarter-quarter-quarter-8th = 4 beats (one measure)
    # Creates off-beat feel with notes landing on "and"s
    RhythmType.SYNCOPATED: RhythmCell(
        (EIGHTH_NOTE, QUARTER_NOTE, QUARTER_NOTE, QUARTER_NOTE, EIGHTH_NOTE)
    ),
}


# =============================================================================
# Core Functions
# =============================================================================


def apply_rhythm(
    pitches: List[int],
    rhythm: RhythmType,
    time_signature: Tuple[int, int] = (4, 4),
    pitch_names: Optional[List[str]] = None,
    min_final_duration: float = QUARTER_NOTE,
) -> List[PitchEvent]:
    """Apply a rhythm pattern to a pitch sequence.
    
    Global rule: If the final note ends NOT on a beat, it is extended to fill
    to the next beat, and a quarter note "do" (tonic) is added on that beat.
    
    Args:
        pitches: List of MIDI pitch values.
        rhythm: The rhythm type to apply.
        time_signature: (beats_per_measure, beat_unit) - used for alignment.
        pitch_names: Optional pitch names corresponding to pitches.
        min_final_duration: Minimum duration for the final note (default: quarter note).
        
    Returns:
        List of PitchEvent objects with timing information.
    """
    if not pitches:
        return []
    
    cell = RHYTHM_CELLS.get(rhythm)
    if cell is None:
        # Default to quarter notes
        cell = RHYTHM_CELLS[RhythmType.QUARTER_NOTES]
    
    # The "tonic" (do) is the final pitch in the scale - used for final sustained note
    final_tonic_pitch = pitches[-1]
    final_tonic_name = pitch_names[-1] if pitch_names else _midi_to_name(final_tonic_pitch)
    
    events = []
    offset = 0.0
    cell_index = 0
    
    for i, pitch in enumerate(pitches):
        # Get duration from current position in cell
        duration = cell.durations[cell_index]
        
        # Get pitch name if available, or generate a placeholder
        name = pitch_names[i] if pitch_names and i < len(pitch_names) else _midi_to_name(pitch)
        
        events.append(PitchEvent(
            midi_note=pitch,
            pitch_name=name,
            duration_beats=duration,
            offset_beats=offset,
        ))
        
        # Advance offset
        offset += duration
        
        # Move to next position in cell
        cell_index = (cell_index + 1) % cell.notes_per_cell
    
    # ==========================================================================
    # GLOBAL RULE: If final note STARTS off-beat, adjust to end on beat + add quarter do
    # ==========================================================================
    # This applies to ALL scales/rhythms:
    # - If the last note STARTS off-beat (on the "and"), adjust its duration to
    #   END exactly on the next beat, then add a quarter note "do" on that beat
    # - This could mean extending (short notes), no change, or shortening (syncopated)
    # - If the last note STARTS on-beat but is too short, just extend to min
    #
    # Skip if min_final_duration is 0 (disabled)
    if events and min_final_duration > 0:
        last_event = events[-1]
        start_position_in_beat = round(last_event.offset_beats % 1.0, 6)
        
        # Check if the note STARTS off a beat (not at 0.0 or very close to 1.0)
        starts_off_beat = start_position_in_beat > 0.01 and start_position_in_beat < 0.99
        
        if starts_off_beat:
            # Note starts off-beat - adjust duration to end exactly on next beat
            next_beat = int(last_event.offset_beats) + 1
            duration_to_next_beat = next_beat - last_event.offset_beats
            
            # Set duration to fill exactly to next beat (extend, no-op, or shorten)
            if abs(last_event.duration_beats - duration_to_next_beat) > 0.001:
                events[-1] = PitchEvent(
                    midi_note=last_event.midi_note,
                    pitch_name=last_event.pitch_name,
                    duration_beats=duration_to_next_beat,
                    offset_beats=last_event.offset_beats,
                )
            
            # Add a quarter note "do" on the next beat
            events.append(PitchEvent(
                midi_note=final_tonic_pitch,
                pitch_name=final_tonic_name,
                duration_beats=min_final_duration,
                offset_beats=float(next_beat),
            ))
            offset = next_beat + min_final_duration
        else:
            # Note starts on beat - if too short, just extend to minimum
            if last_event.duration_beats < min_final_duration:
                events[-1] = PitchEvent(
                    midi_note=last_event.midi_note,
                    pitch_name=last_event.pitch_name,
                    duration_beats=min_final_duration,
                    offset_beats=last_event.offset_beats,
                )
                offset = last_event.offset_beats + min_final_duration
    
    # Fill incomplete final measure with rests
    beats_per_measure = time_signature[0]
    events = _fill_measure_with_rests(events, offset, beats_per_measure)
    
    return events


def _fill_gap_with_rests(
    events: List[PitchEvent],
    gap_start: float,
    gap_end: float,
    beats_per_measure: int,
) -> List[PitchEvent]:
    """Fill a gap between two time positions with rests.
    
    Uses whole, half, quarter, and eighth note rests as needed.
    """
    if gap_end <= gap_start:
        return events
    
    result = list(events)
    current = gap_start
    
    while current < gap_end - 0.001:
        remaining = gap_end - current
        
        # Choose appropriate rest duration
        if remaining >= beats_per_measure and current % beats_per_measure < 0.001:
            duration = beats_per_measure  # whole rest
        elif remaining >= 2.0 and current % 2.0 < 0.001:
            duration = 2.0  # half rest
        elif remaining >= 1.0 and current % 1.0 < 0.001:
            duration = 1.0  # quarter rest
        elif remaining >= 0.5:
            duration = 0.5  # eighth rest
        else:
            duration = remaining  # whatever's left
        
        result.append(PitchEvent(
            midi_note=0,
            pitch_name="rest",
            duration_beats=duration,
            offset_beats=current,
        ))
        current += duration
    
    return result


def _get_half_measure_boundary(beats_per_measure: int) -> Optional[float]:
    """Get the half-measure boundary for a given time signature.
    
    In most time signatures, half rests should not cross the middle of the measure
    unless they start exactly at beat 0 or at the boundary.
    
    Args:
        beats_per_measure: Number of beats per measure.
        
    Returns:
        Beat position of the half-measure boundary, or None if not applicable.
    """
    # 4/4: boundary at beat 2
    # 3/4: no boundary (can't evenly split)
    # 2/4: boundary at beat 1
    # 6/8: would be at beat 3 if treating eighth as beat unit
    if beats_per_measure == 4:
        return 2.0
    if beats_per_measure == 2:
        return 1.0
    return None


def _fill_measure_with_rests(
    events: List[PitchEvent],
    current_offset: float,
    beats_per_measure: int,
) -> List[PitchEvent]:
    """Add rests to complete an incomplete final measure.
    
    Respects the half-measure boundary: rests should not cross the middle
    of the measure (beat 2 in 4/4) unless starting exactly at beat 0 or beat 2.
    
    Args:
        events: List of existing events.
        current_offset: Current time position in beats.
        beats_per_measure: Number of beats per measure.
        
    Returns:
        Events list with rests appended if needed.
    """
    # Calculate position within measure
    position_in_measure = current_offset % beats_per_measure
    
    # If already at measure boundary, no rests needed
    if position_in_measure < 0.001:
        return events
    
    # How much time remains in the measure
    remaining = beats_per_measure - position_in_measure
    
    # Get half-measure boundary
    boundary = _get_half_measure_boundary(beats_per_measure)
    
    # Rest values in descending order
    rest_values = [2.0, 1.0, 0.5, 0.25, 0.125]
    
    offset = current_offset
    while remaining > 0.001:
        # Calculate position within measure for this rest
        pos_in_measure = offset % beats_per_measure
        
        # Find largest rest that fits AND doesn't cross boundary inappropriately
        rest_duration = None
        for duration in rest_values:
            if duration > remaining + 0.001:
                continue
            
            # Check if this duration would cross the boundary inappropriately
            # ANY rest that crosses the half-measure boundary is forbidden
            # unless starting at beat 0 or exactly at the boundary
            if boundary is not None:
                at_or_past_boundary = pos_in_measure >= boundary - 0.001
                at_measure_start = pos_in_measure < 0.001
                rest_end = pos_in_measure + duration
                would_cross = (
                    not at_or_past_boundary 
                    and not at_measure_start 
                    and rest_end > boundary + 0.001
                )
                if would_cross:
                    # Can't use this rest here, try smaller
                    continue
            
            rest_duration = duration
            break
        
        if rest_duration is None:
            # Remaining is too small, just stop
            break
        
        events.append(PitchEvent(
            midi_note=0,  # Rest
            pitch_name="rest",
            duration_beats=rest_duration,
            offset_beats=offset,
        ))
        
        offset += rest_duration
        remaining -= rest_duration
    
    return events


def _midi_to_name(midi: int) -> str:
    """Convert MIDI note number to pitch name (e.g., 60 -> 'C4')."""
    if midi == 0:
        return "rest"
    note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (midi // 12) - 1
    note = note_names[midi % 12]
    return f"{note}{octave}"


def apply_rhythm_with_repeats(
    pitches: List[int],
    rhythm: RhythmType,
    repeat_count: int = 1,
    pitch_names: Optional[List[str]] = None,
) -> List[PitchEvent]:
    """Apply rhythm and optionally repeat the entire pattern.
    
    Args:
        pitches: List of MIDI pitch values.
        rhythm: The rhythm type to apply.
        repeat_count: Number of times to repeat (1 = no repeat).
        pitch_names: Optional pitch names.
        
    Returns:
        List of PitchEvent objects.
    """
    if repeat_count < 1:
        repeat_count = 1
    
    # Apply rhythm to original pitches
    events = apply_rhythm(pitches, rhythm, pitch_names=pitch_names)
    
    if repeat_count == 1 or not events:
        return events
    
    # Get only note events (exclude rests) for calculating content duration
    note_events = [e for e in events if e.midi_note != 0]
    if not note_events:
        return events
    
    # Calculate total duration from actual content (excluding trailing rests)
    last_note = note_events[-1]
    content_duration = last_note.offset_beats + last_note.duration_beats
    
    all_events = list(events)  # First pass (including rests)
    
    # Repeat only the note events, not the rests
    for rep in range(1, repeat_count):
        offset_adjustment = content_duration * rep
        for event in note_events:
            all_events.append(PitchEvent(
                midi_note=event.midi_note,
                pitch_name=event.pitch_name,
                duration_beats=event.duration_beats,
                offset_beats=event.offset_beats + offset_adjustment,
            ))
    
    # Re-fill the final measure with rests after all repeats
    final_offset = all_events[-1].offset_beats + all_events[-1].duration_beats
    all_events = _fill_measure_with_rests(all_events, final_offset, 4)
    
    return all_events


def get_duration(rhythm: RhythmType) -> float:
    """Get the base duration for a rhythm type (first note of cell).
    
    Args:
        rhythm: The rhythm type.
        
    Returns:
        Duration in beats.
    """
    cell = RHYTHM_CELLS.get(rhythm)
    if cell is None:
        return QUARTER_NOTE
    return cell.durations[0]


def get_cell_info(rhythm: RhythmType) -> Tuple[float, int]:
    """Get cell information for a rhythm type.
    
    Args:
        rhythm: The rhythm type.
        
    Returns:
        Tuple of (cell_length_beats, notes_per_cell).
    """
    cell = RHYTHM_CELLS.get(rhythm)
    if cell is None:
        cell = RHYTHM_CELLS[RhythmType.QUARTER_NOTES]
    return (cell.cell_length, cell.notes_per_cell)


def calculate_total_duration(
    num_pitches: int,
    rhythm: RhythmType,
) -> float:
    """Calculate total duration for a given number of pitches.
    
    Args:
        num_pitches: Number of pitches to be played.
        rhythm: The rhythm type.
        
    Returns:
        Total duration in beats.
    """
    if num_pitches <= 0:
        return 0.0
    
    cell = RHYTHM_CELLS.get(rhythm)
    if cell is None:
        cell = RHYTHM_CELLS[RhythmType.QUARTER_NOTES]
    
    total = 0.0
    cell_index = 0
    
    for _ in range(num_pitches):
        total += cell.durations[cell_index]
        cell_index = (cell_index + 1) % cell.notes_per_cell
    
    return total


def calculate_measures(
    num_pitches: int,
    rhythm: RhythmType,
    beats_per_measure: int = 4,
) -> float:
    """Calculate how many measures the content will span.
    
    Args:
        num_pitches: Number of pitches.
        rhythm: The rhythm type.
        beats_per_measure: Beats per measure (default 4).
        
    Returns:
        Number of measures (fractional).
    """
    total_beats = calculate_total_duration(num_pitches, rhythm)
    return total_beats / beats_per_measure


# =============================================================================
# Utility Functions
# =============================================================================


def get_supported_rhythms() -> List[RhythmType]:
    """Return list of all supported rhythm types."""
    return list(RHYTHM_CELLS.keys())


def beats_to_seconds(beats: float, tempo_bpm: float) -> float:
    """Convert beats to seconds at a given tempo.
    
    Args:
        beats: Number of beats.
        tempo_bpm: Tempo in beats per minute.
        
    Returns:
        Duration in seconds.
    """
    if tempo_bpm <= 0:
        raise ValueError("Tempo must be positive")
    return beats * 60.0 / tempo_bpm


def seconds_to_beats(seconds: float, tempo_bpm: float) -> float:
    """Convert seconds to beats at a given tempo.
    
    Args:
        seconds: Duration in seconds.
        tempo_bpm: Tempo in beats per minute.
        
    Returns:
        Number of beats.
    """
    if tempo_bpm <= 0:
        raise ValueError("Tempo must be positive")
    return seconds * tempo_bpm / 60.0


def quantize_to_grid(
    offset_beats: float,
    grid_resolution: float = SIXTEENTH_NOTE,
) -> float:
    """Quantize an offset to the nearest grid position.
    
    Args:
        offset_beats: The offset to quantize.
        grid_resolution: The grid resolution in beats.
        
    Returns:
        Quantized offset.
    """
    return round(offset_beats / grid_resolution) * grid_resolution


def create_rest_event(duration_beats: float, offset_beats: float) -> PitchEvent:
    """Create a rest (midi_note=0 indicates rest).
    
    Args:
        duration_beats: Duration of the rest.
        offset_beats: When the rest starts.
        
    Returns:
        PitchEvent with midi_note=0.
    """
    return PitchEvent(
        midi_note=0,  # Convention: 0 = rest
        pitch_name="rest",
        duration_beats=duration_beats,
        offset_beats=offset_beats,
    )


def insert_rests_between_groups(
    events: List[PitchEvent],
    group_size: int,
    rest_duration: float,
) -> List[PitchEvent]:
    """Insert rests between groups of events.
    
    Useful for patterns like "play 4, rest 1, play 4, rest 1".
    
    Args:
        events: List of PitchEvents.
        group_size: Number of events per group.
        rest_duration: Duration of rest between groups.
        
    Returns:
        New list of events with rests inserted.
    """
    if not events or group_size <= 0:
        return events.copy()
    
    result = []
    offset_adjustment = 0.0
    
    for i, event in enumerate(events):
        # Create adjusted event
        result.append(PitchEvent(
            midi_note=event.midi_note,
            pitch_name=event.pitch_name,
            duration_beats=event.duration_beats,
            offset_beats=event.offset_beats + offset_adjustment,
        ))
        
        # Check if we should insert a rest after this event
        if (i + 1) % group_size == 0 and i < len(events) - 1:
            # Calculate where the rest should go
            rest_offset = event.offset_beats + offset_adjustment + event.duration_beats
            result.append(create_rest_event(rest_duration, rest_offset))
            offset_adjustment += rest_duration
    
    return result
