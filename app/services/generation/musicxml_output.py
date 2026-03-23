"""MusicXML output generator for pitch sequences.

This module converts PitchEvent lists into MusicXML format,
ready for playback and display in notation software.
"""

from typing import List, Optional, Tuple
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom

from app.schemas.generation_schemas import (
    ArticulationType,
    GenerationRequest,
    MusicalKey,
    PitchEvent,
    RhythmType,
)


# =============================================================================
# Duration Mapping
# =============================================================================

# Triplet durations
EIGHTH_TRIPLET_DURATION = 1.0 / 3.0
QUARTER_TRIPLET_DURATION = 2.0 / 3.0  # Triplet quarter = 2 triplet eighths

# Rhythm types that should use triplet notation
# Swing eighths use 2/3 and 1/3 durations but should NOT be notated as triplets
TRIPLET_NOTATION_RHYTHMS: set[RhythmType] = {RhythmType.EIGHTH_TRIPLETS}

# MusicXML duration types based on beats (quarter = 1.0)
DURATION_TYPES = [
    (4.0, "whole"),
    (3.0, "half", True),  # Dotted half
    (2.0, "half"),
    (1.5, "quarter", True),  # Dotted quarter
    (1.0, "quarter"),
    (0.75, "eighth", True),  # Dotted eighth
    (0.5, "eighth"),
    (0.375, "16th", True),  # Dotted 16th
    (0.25, "16th"),
    (0.125, "32nd"),
]


def _beats_to_type(beats: float) -> Tuple[str, bool]:
    """Convert duration in beats to MusicXML type and dotted flag.
    
    Args:
        beats: Duration in beats.
        
    Returns:
        Tuple of (type_name, is_dotted).
    """
    for entry in DURATION_TYPES:
        if len(entry) == 3:
            duration, type_name, dotted = entry
            if abs(beats - duration) < 0.01:
                return (type_name, True)
        else:
            duration, type_name = entry
            if abs(beats - duration) < 0.01:
                return (type_name, False)
    # Default to quarter
    return ("quarter", False)


# =============================================================================
# Pitch Helpers
# =============================================================================

# MIDI to pitch mapping
_PITCH_CLASSES = [
    ("C", 0), ("C", 1), ("D", 0), ("D", 1), ("E", 0), ("F", 0),
    ("F", 1), ("G", 0), ("G", 1), ("A", 0), ("A", 1), ("B", 0),
]

# Flat versions (used when key suggests flats)
_PITCH_CLASSES_FLAT = [
    ("C", 0), ("D", -1), ("D", 0), ("E", -1), ("E", 0), ("F", 0),
    ("G", -1), ("G", 0), ("A", -1), ("A", 0), ("B", -1), ("B", 0),
]

# Keys that prefer flats
FLAT_KEYS = {
    MusicalKey.F, MusicalKey.B_FLAT, MusicalKey.E_FLAT,
    MusicalKey.A_FLAT, MusicalKey.D_FLAT, MusicalKey.G_FLAT,
}


def _midi_to_pitch(midi: int, use_flats: bool = False) -> Tuple[str, int, int]:
    """Convert MIDI note to (step, octave, alter).
    
    Args:
        midi: MIDI note number.
        use_flats: If True, prefer flats over sharps.
        
    Returns:
        Tuple of (step, octave, alter) where alter is -1/0/1.
    """
    octave = (midi // 12) - 1
    pitch_class = midi % 12
    
    if use_flats:
        step, alter = _PITCH_CLASSES_FLAT[pitch_class]
    else:
        step, alter = _PITCH_CLASSES[pitch_class]
    
    return (step, octave, alter)


# Key signature fifths values
_KEY_FIFTHS = {
    MusicalKey.C: 0,
    MusicalKey.G: 1, MusicalKey.D: 2, MusicalKey.A: 3,
    MusicalKey.E: 4, MusicalKey.B: 5, MusicalKey.F_SHARP: 6,
    MusicalKey.C_SHARP: 7,
    MusicalKey.F: -1, MusicalKey.B_FLAT: -2, MusicalKey.E_FLAT: -3,
    MusicalKey.A_FLAT: -4, MusicalKey.D_FLAT: -5, MusicalKey.G_FLAT: -6,
    # Enharmonic equivalents
    MusicalKey.D_SHARP: 6, MusicalKey.G_SHARP: 6, MusicalKey.A_SHARP: 6,
}


def _key_to_fifths(key: MusicalKey) -> int:
    """Get the number of fifths for a key signature."""
    return _KEY_FIFTHS.get(key, 0)


# =============================================================================
# Articulation Mapping
# =============================================================================

_ARTICULATION_ELEMENTS = {
    ArticulationType.STACCATO: "staccato",
    ArticulationType.ACCENT: "accent",
    ArticulationType.TENUTO: "tenuto",
    ArticulationType.MARCATO: "strong-accent",
    # LEGATO is handled via slurs, not articulation elements
}


# =============================================================================
# Triplet Detection
# =============================================================================

def _is_eighth_triplet(duration: float) -> bool:
    """Check if duration is an eighth note triplet (1/3 beat)."""
    return abs(duration - EIGHTH_TRIPLET_DURATION) < 0.01


def _is_quarter_triplet(duration: float) -> bool:
    """Check if duration is a quarter note triplet (2/3 beat)."""
    return abs(duration - QUARTER_TRIPLET_DURATION) < 0.01


def _is_any_triplet(duration: float) -> bool:
    """Check if duration is any triplet note (1/3 or 2/3 beat)."""
    return _is_eighth_triplet(duration) or _is_quarter_triplet(duration)


def _get_triplet_info(duration: float) -> tuple[bool, str, int, int]:
    """Get triplet information for a note duration.
    
    Returns:
        Tuple of (is_triplet, note_type, actual_notes, normal_notes).
        For triplets: actual_notes=3, normal_notes=2.
    """
    if _is_eighth_triplet(duration):
        return (True, "eighth", 3, 2)
    if _is_quarter_triplet(duration):
        return (True, "quarter", 3, 2)
    return (False, "", 0, 0)


def _get_triplet_position(offset: float, triplet_duration: float) -> int:
    """Get position within a triplet group (0, 1, or 2).
    
    Args:
        offset: Beat offset of the note.
        triplet_duration: Duration of each triplet note.
        
    Returns:
        Position within the triplet group (0=first, 1=middle, 2=last).
    """
    # Calculate the beat position (0.0 to 1.0 within a beat)
    beat_position = offset % 1.0
    
    # Eighth triplets: one group per beat
    position_in_group = round(beat_position / triplet_duration) % 3
    
    return position_in_group


# =============================================================================
# MusicXML Generation
# =============================================================================


def _calculate_divisions(events: List[PitchEvent]) -> int:
    """Calculate optimal divisions value based on note durations.
    
    Returns a divisions value that can represent all durations precisely.
    For triplets, we need divisions divisible by 3.
    """
    has_triplets = any(_is_any_triplet(e.duration_beats) for e in events)
    # Use 12 for triplets (divisible by both 3 and 4), otherwise 4
    return 12 if has_triplets else 4


def events_to_musicxml(
    events: List[PitchEvent],
    title: str = "Generated Content",
    key: MusicalKey = MusicalKey.C,
    time_signature: Tuple[int, int] = (4, 4),
    divisions: Optional[int] = None,
    clef: str = "G",
    tempo_bpm: Optional[int] = None,
    part_name: str = "Part 1",
    rhythm: Optional[RhythmType] = None,
) -> str:
    """Convert a list of PitchEvents to MusicXML string.
    
    Args:
        events: List of PitchEvent objects.
        title: Work title.
        key: Musical key for key signature.
        time_signature: (beats_per_measure, beat_type).
        divisions: Divisions per quarter note. If None, auto-calculated.
        clef: Clef sign (G, F, C).
        rhythm: The rhythm type used for notation decisions (triplet vs swing).
        tempo_bpm: Optional tempo marking.
        part_name: Name for the part.
        
    Returns:
        MusicXML string.
    """
    if not events:
        return _empty_musicxml(title, key, time_signature)
    
    # Auto-calculate divisions if not specified
    if divisions is None:
        divisions = _calculate_divisions(events)
    
    use_flats = key in FLAT_KEYS
    beats_per_measure = time_signature[0]
    
    # Create root element
    root = Element("score-partwise", version="4.0")
    
    # Work title
    work = SubElement(root, "work")
    work_title = SubElement(work, "work-title")
    work_title.text = title
    
    # Part list
    part_list = SubElement(root, "part-list")
    score_part = SubElement(part_list, "score-part", id="P1")
    part_name_elem = SubElement(score_part, "part-name")
    part_name_elem.text = part_name
    
    # Part with measures
    part = SubElement(root, "part", id="P1")
    
    # Group events into measures
    measures = _group_into_measures(events, beats_per_measure)
    
    for measure_num, measure_events in enumerate(measures, start=1):
        measure = SubElement(part, "measure", number=str(measure_num))
        
        # First measure gets attributes
        if measure_num == 1:
            _add_attributes(
                measure, divisions, key, time_signature, clef
            )
            
            # Add tempo if specified
            if tempo_bpm:
                _add_tempo(measure, tempo_bpm)
        
        # Add notes with triplet grouping (only for triplet rhythms, not swing)
        use_triplet_notation = rhythm in TRIPLET_NOTATION_RHYTHMS if rhythm else True
        _add_notes_with_triplets(measure, measure_events, divisions, use_flats, use_triplet_notation)
        
        # Final barline on last measure
        if measure_num == len(measures):
            _add_final_barline(measure)
    
    return _prettify_xml(root)


def _add_notes_with_triplets(
    measure: Element,
    events: List[PitchEvent],
    divisions: int,
    use_flats: bool,
    use_triplet_notation: bool = True,
) -> None:
    """Add notes to a measure, handling triplet grouping.
    
    Detects triplet notes and adds appropriate beam, time-modification,
    and tuplet notation elements. Groups triplets by beat, allowing
    mixed durations (e.g., triplet eighth + triplet quarter in one beat).
    
    Args:
        use_triplet_notation: If False, skip triplet notation (for swing).
    """
    i = 0
    while i < len(events):
        event = events[i]
        # Only use triplet notation if the rhythm type supports it
        is_triplet = use_triplet_notation and _is_any_triplet(event.duration_beats)
        
        if is_triplet:
            # Find all consecutive triplet notes (any triplet duration)
            triplet_sequence = [event]
            j = i + 1
            while j < len(events):
                if _is_any_triplet(events[j].duration_beats):
                    triplet_sequence.append(events[j])
                    j += 1
                else:
                    break
            
            # Process triplets by beat - each beat is a triplet group
            seq_idx = 0
            while seq_idx < len(triplet_sequence):
                # Get beat number for this note (round to handle floating point)
                current_beat = int(round(triplet_sequence[seq_idx].offset_beats, 6))
                
                # Collect all triplet notes in this beat
                beat_group = []
                while seq_idx < len(triplet_sequence):
                    note_beat = int(round(triplet_sequence[seq_idx].offset_beats, 6))
                    if note_beat == current_beat:
                        beat_group.append(triplet_sequence[seq_idx])
                        seq_idx += 1
                    else:
                        break
                
                # Render the beat group with triplet notation
                for idx, triplet_event in enumerate(beat_group):
                    is_triplet_note, triplet_type, actual, normal = _get_triplet_info(
                        triplet_event.duration_beats
                    )
                    is_first = idx == 0
                    is_last = idx == len(beat_group) - 1
                    
                    # Only beam eighth triplets, not quarter triplets
                    include_beam = _is_eighth_triplet(triplet_event.duration_beats)
                    
                    _add_triplet_note(
                        measure, triplet_event, divisions, use_flats,
                        triplet_type, actual, normal,
                        is_first, 
                        is_last,
                        include_beam=include_beam
                    )
            
            i = j
        else:
            _add_note(measure, event, divisions, use_flats)
            i += 1


def _empty_musicxml(
    title: str,
    key: MusicalKey,
    time_signature: Tuple[int, int],
) -> str:
    """Generate minimal empty MusicXML."""
    root = Element("score-partwise", version="4.0")
    work = SubElement(root, "work")
    work_title = SubElement(work, "work-title")
    work_title.text = title
    
    part_list = SubElement(root, "part-list")
    score_part = SubElement(part_list, "score-part", id="P1")
    part_name = SubElement(score_part, "part-name")
    part_name.text = "Part"
    
    part = SubElement(root, "part", id="P1")
    measure = SubElement(part, "measure", number="1")
    _add_attributes(measure, 4, key, time_signature, "G")
    
    # Add a rest
    note = SubElement(measure, "note")
    SubElement(note, "rest")
    duration = SubElement(note, "duration")
    duration.text = str(time_signature[0] * 4)  # Whole measure rest
    note_type = SubElement(note, "type")
    note_type.text = "whole"
    
    _add_final_barline(measure)
    
    return _prettify_xml(root)


def _group_into_measures(
    events: List[PitchEvent],
    beats_per_measure: int,
) -> List[List[PitchEvent]]:
    """Group events into measures based on beat offsets."""
    if not events:
        return []
    
    measures: List[List[PitchEvent]] = []
    current_measure: List[PitchEvent] = []
    current_measure_num = 0
    
    for event in events:
        # Round offset to avoid floating point precision issues
        # (triplet eighths = 1/3 can't be represented exactly)
        rounded_offset = round(event.offset_beats, 6)
        
        # Determine which measure this event belongs to
        event_measure_num = int(rounded_offset // beats_per_measure)
        
        # If we've moved to a new measure, finalize previous and create empties
        while event_measure_num > current_measure_num:
            measures.append(current_measure)
            current_measure = []
            current_measure_num += 1
        
        current_measure.append(event)
    
    # Don't forget the last measure
    if current_measure:
        measures.append(current_measure)
    
    return measures


def _add_attributes(
    measure: Element,
    divisions: int,
    key: MusicalKey,
    time_signature: Tuple[int, int],
    clef: str,
) -> None:
    """Add attributes element to first measure."""
    attributes = SubElement(measure, "attributes")
    
    div = SubElement(attributes, "divisions")
    div.text = str(divisions)
    
    key_elem = SubElement(attributes, "key")
    fifths = SubElement(key_elem, "fifths")
    fifths.text = str(_key_to_fifths(key))
    mode = SubElement(key_elem, "mode")
    mode.text = "major"
    
    time = SubElement(attributes, "time")
    beats = SubElement(time, "beats")
    beats.text = str(time_signature[0])
    beat_type = SubElement(time, "beat-type")
    beat_type.text = str(time_signature[1])
    
    clef_elem = SubElement(attributes, "clef")
    sign = SubElement(clef_elem, "sign")
    sign.text = clef
    line = SubElement(clef_elem, "line")
    line.text = "2" if clef == "G" else "4"


def _add_tempo(measure: Element, tempo_bpm: int) -> None:
    """Add tempo direction to measure."""
    direction = SubElement(measure, "direction", placement="above")
    direction_type = SubElement(direction, "direction-type")
    metronome = SubElement(direction_type, "metronome")
    beat_unit = SubElement(metronome, "beat-unit")
    beat_unit.text = "quarter"
    per_minute = SubElement(metronome, "per-minute")
    per_minute.text = str(tempo_bpm)
    
    # Sound element for playback
    sound = SubElement(direction, "sound", tempo=str(tempo_bpm))


def _add_note(
    measure: Element,
    event: PitchEvent,
    divisions: int,
    use_flats: bool,
) -> None:
    """Add a note element to a measure."""
    note = SubElement(measure, "note")
    
    # Handle rest (midi_note == 0)
    if event.midi_note == 0:
        SubElement(note, "rest")
    else:
        # Pitch
        step, octave, alter = _midi_to_pitch(event.midi_note, use_flats)
        pitch = SubElement(note, "pitch")
        step_elem = SubElement(pitch, "step")
        step_elem.text = step
        if alter != 0:
            alter_elem = SubElement(pitch, "alter")
            alter_elem.text = str(alter)
        octave_elem = SubElement(pitch, "octave")
        octave_elem.text = str(octave)
    
    # Duration (in divisions)
    duration_elem = SubElement(note, "duration")
    duration_value = int(event.duration_beats * divisions)
    duration_elem.text = str(duration_value)
    
    # Type
    note_type, is_dotted = _beats_to_type(event.duration_beats)
    type_elem = SubElement(note, "type")
    type_elem.text = note_type
    
    if is_dotted:
        SubElement(note, "dot")
    
    # Articulation
    if event.articulation and event.articulation in _ARTICULATION_ELEMENTS:
        notations = SubElement(note, "notations")
        articulations = SubElement(notations, "articulations")
        SubElement(articulations, _ARTICULATION_ELEMENTS[event.articulation])


def _add_triplet_note(
    measure: Element,
    event: PitchEvent,
    divisions: int,
    use_flats: bool,
    note_type: str,
    actual_notes: int,
    normal_notes: int,
    is_first: bool,
    is_last: bool,
    include_beam: bool = True,
) -> None:
    """Add a triplet note element to a measure.
    
    Args:
        measure: Parent measure element.
        event: PitchEvent for this note.
        divisions: MusicXML divisions per quarter.
        use_flats: Whether to spell with flats.
        note_type: MusicXML note type (e.g., "eighth").
        actual_notes: Actual notes in tuplet (3 for triplet).
        normal_notes: Normal notes replaced (2 for triplet).
        is_first: True if this is the first note of a triplet group.
        is_last: True if this is the last note of a triplet group.
        include_beam: True to include beam element (False for orphan notes).
    """
    note = SubElement(measure, "note")
    
    # Handle rest (midi_note == 0)
    if event.midi_note == 0:
        SubElement(note, "rest")
    else:
        # Pitch
        step, octave, alter = _midi_to_pitch(event.midi_note, use_flats)
        pitch = SubElement(note, "pitch")
        step_elem = SubElement(pitch, "step")
        step_elem.text = step
        if alter != 0:
            alter_elem = SubElement(pitch, "alter")
            alter_elem.text = str(alter)
        octave_elem = SubElement(pitch, "octave")
        octave_elem.text = str(octave)
    
    # Duration (in divisions) - for triplets, this is fractional but we round
    duration_elem = SubElement(note, "duration")
    duration_value = round(event.duration_beats * divisions)
    duration_elem.text = str(max(1, duration_value))
    
    # Type
    type_elem = SubElement(note, "type")
    type_elem.text = note_type
    
    # Time modification (required for tuplets)
    time_mod = SubElement(note, "time-modification")
    actual_elem = SubElement(time_mod, "actual-notes")
    actual_elem.text = str(actual_notes)
    normal_elem = SubElement(time_mod, "normal-notes")
    normal_elem.text = str(normal_notes)
    
    # Beam (for eighth notes and shorter, skip for orphan notes)
    if include_beam and note_type in ("eighth", "16th", "32nd") and event.midi_note != 0:
        beam = SubElement(note, "beam", number="1")
        if is_first:
            beam.text = "begin"
        elif is_last:
            beam.text = "end"
        else:
            beam.text = "continue"
    
    # Notations (tuplet bracket with number)
    if is_first or is_last:
        notations = SubElement(note, "notations")
        tuplet = SubElement(notations, "tuplet")
        if is_first:
            tuplet.set("type", "start")
            tuplet.set("bracket", "yes")
            tuplet.set("show-number", "actual")
        else:
            tuplet.set("type", "stop")
        
        # Add articulation if present
        if event.articulation and event.articulation in _ARTICULATION_ELEMENTS:
            articulations = SubElement(notations, "articulations")
            SubElement(articulations, _ARTICULATION_ELEMENTS[event.articulation])
    elif event.articulation and event.articulation in _ARTICULATION_ELEMENTS:
        # Middle note with articulation
        notations = SubElement(note, "notations")
        articulations = SubElement(notations, "articulations")
        SubElement(articulations, _ARTICULATION_ELEMENTS[event.articulation])


def _add_final_barline(measure: Element) -> None:
    """Add final barline to measure."""
    barline = SubElement(measure, "barline", location="right")
    bar_style = SubElement(barline, "bar-style")
    bar_style.text = "light-heavy"


def _prettify_xml(root: Element) -> str:
    """Convert element to pretty-printed string with XML declaration."""
    rough_string = tostring(root, encoding="unicode")
    # Add XML declaration and DOCTYPE
    xml_declaration = '<?xml version="1.0" encoding="UTF-8"?>\n'
    doctype = '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 4.0 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">\n'
    
    # Pretty print
    try:
        dom = minidom.parseString(rough_string)
        pretty = dom.toprettyxml(indent="  ")
        # Remove the XML declaration from minidom (we add our own)
        lines = pretty.split("\n")
        if lines[0].startswith("<?xml"):
            lines = lines[1:]
        content = "\n".join(lines)
        return xml_declaration + doctype + content.strip()
    except Exception:
        return xml_declaration + doctype + rough_string


# =============================================================================
# Convenience Functions
# =============================================================================


def generate_musicxml_from_request(
    request: GenerationRequest,
    events: List[PitchEvent],
    title: Optional[str] = None,
) -> str:
    """Generate MusicXML from a generation request and events.
    
    Args:
        request: The original generation request.
        events: The generated PitchEvents.
        title: Optional title override.
        
    Returns:
        MusicXML string.
    """
    if title is None:
        # Generate a descriptive title
        title = f"{request.definition.title()} {request.content_type.value}"
        if request.key != MusicalKey.C:
            title += f" in {request.key.value}"
    
    return events_to_musicxml(
        events=events,
        title=title,
        key=request.key,
        time_signature=(4, 4),
        rhythm=request.rhythm,
    )


def midi_pitches_to_musicxml(
    pitches: List[int],
    title: str = "Generated Pitches",
    key: MusicalKey = MusicalKey.C,
    duration_beats: float = 1.0,
) -> str:
    """Quick conversion of MIDI pitches to MusicXML with uniform rhythm.
    
    Args:
        pitches: List of MIDI note numbers.
        title: Work title.
        key: Musical key.
        duration_beats: Duration for each note.
        
    Returns:
        MusicXML string.
    """
    use_flats = key in FLAT_KEYS
    events = []
    offset = 0.0
    
    for pitch in pitches:
        step, octave, alter = _midi_to_pitch(pitch, use_flats)
        pitch_name = step + str(octave)
        
        events.append(PitchEvent(
            midi_note=pitch,
            pitch_name=pitch_name,
            duration_beats=duration_beats,
            offset_beats=offset,
        ))
        offset += duration_beats
    
    return events_to_musicxml(events, title=title, key=key)
