from __future__ import annotations

"""
Score Data Extraction

Extracts note data from music21 Score objects for metric calculations.
"""

from typing import Any, Dict, List

try:
    from music21 import stream, note, chord, key
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

from ..models import NoteEvent


def extract_note_data(score: stream.Score) -> Dict[str, Any]:
    """
    Extract all note-related data from a music21 Score for calculations.
    
    Args:
        score: music21 Score object
        
    Returns:
        Dictionary containing pitch, interval, rhythm data for calculations
    """
    pitch_classes = set()
    note_steps = []
    accidental_count = 0
    total_notes = 0
    interval_semitones = []
    interval_offsets = []      # Offset of second note in each interval
    interval_measure_numbers = []  # Measure number for each interval
    note_events = []
    note_measure_numbers = []  # Track measure number for each note (for density calculation)
    
    durations = []
    types = []
    has_dots = []
    has_tuplets = []
    has_ties = []
    pitch_changes = []
    offsets = []
    
    prev_midi = None
    
    # Get key signature for accidental counting
    key_sigs = list(score.recurse().getElementsByClass(key.KeySignature))
    current_key = key_sigs[0] if key_sigs else key.KeySignature(0)
    
    if hasattr(current_key, 'asKey'):
        k = current_key.asKey()
        in_key_pitches = set(p.name for p in k.pitches)
    else:
        in_key_pitches = set(['C', 'D', 'E', 'F', 'G', 'A', 'B'])
    
    for n in score.recurse().notes:
        # Skip grace notes for main analysis
        if hasattr(n, 'duration') and n.duration.isGrace:
            continue
        
        if isinstance(n, note.Note):
            total_notes += 1
            
            # Pitch class
            pitch_classes.add(n.pitch.pitchClass)
            note_steps.append(n.pitch.step)
            
            # Accidentals outside key
            if n.pitch.name not in in_key_pitches:
                accidental_count += 1
            
            # Get measure number for this note
            try:
                measure_num = n.measureNumber if hasattr(n, 'measureNumber') and n.measureNumber else 1
            except (AttributeError, TypeError):
                measure_num = 1
            note_measure_numbers.append(measure_num)
            
            # Interval from previous
            if prev_midi is not None:
                intv = abs(n.pitch.midi - prev_midi)
                interval_semitones.append(intv)
                interval_offsets.append(n.offset)
                interval_measure_numbers.append(measure_num)
                pitch_changes.append(n.pitch.midi - prev_midi)
            
            # Note event for IVS
            note_events.append(NoteEvent(
                pitch_midi=int(n.pitch.midi),
                duration_ql=float(n.duration.quarterLength),
                offset_ql=float(n.offset),
            ))
            
            prev_midi = n.pitch.midi
            
            # Rhythm data
            durations.append(n.duration.quarterLength)
            types.append(n.duration.type)
            has_dots.append(n.duration.dots > 0)
            has_tuplets.append(bool(n.duration.tuplets))
            has_ties.append(n.tie is not None and n.tie.type in ('start', 'continue'))
            offsets.append(n.offset)
        
        elif isinstance(n, chord.Chord):
            # For chords, use highest note for melody tracking
            total_notes += len(n.pitches)
            for p in n.pitches:
                pitch_classes.add(p.pitchClass)
                note_steps.append(p.step)
                if p.name not in in_key_pitches:
                    accidental_count += 1
            
            # Get measure number for this chord
            try:
                measure_num = n.measureNumber if hasattr(n, 'measureNumber') and n.measureNumber else 1
            except (AttributeError, TypeError):
                measure_num = 1
            # Count all pitches in chord for density (matches total_notes counting)
            for _ in n.pitches:
                note_measure_numbers.append(measure_num)
            
            # Use top note for intervals
            top_pitch = max(n.pitches, key=lambda p: p.midi)
            if prev_midi is not None:
                intv = abs(top_pitch.midi - prev_midi)
                interval_semitones.append(intv)
                interval_offsets.append(n.offset)
                interval_measure_numbers.append(measure_num)
                pitch_changes.append(top_pitch.midi - prev_midi)
            
            note_events.append(NoteEvent(
                pitch_midi=int(top_pitch.midi),
                duration_ql=float(n.duration.quarterLength),
                offset_ql=float(n.offset),
            ))
            
            prev_midi = top_pitch.midi
            
            # Rhythm data (once per chord)
            durations.append(n.duration.quarterLength)
            types.append(n.duration.type)
            has_dots.append(n.duration.dots > 0)
            has_tuplets.append(bool(n.duration.tuplets))
            has_ties.append(n.tie is not None)
            offsets.append(n.offset)
    
    return {
        "pitch_class_count": len(pitch_classes),
        "note_steps": note_steps,
        "accidental_count": accidental_count,
        "total_notes": total_notes,
        "interval_semitones": interval_semitones,
        "interval_offsets": interval_offsets,
        "interval_measure_numbers": interval_measure_numbers,
        "note_events": note_events,
        "note_measure_numbers": note_measure_numbers,
        "durations": durations,
        "types": types,
        "has_dots": has_dots,
        "has_tuplets": has_tuplets,
        "has_ties": has_ties,
        "pitch_changes": pitch_changes,
        "offsets": offsets,
    }
