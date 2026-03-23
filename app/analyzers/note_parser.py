from __future__ import annotations

"""
Note Parser

Extraction of notes, rests, tuplets, and related musical events from MusicXML.
"""

from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from music21 import stream
    from .extraction_models import ExtractionResult

from .capability_maps import NOTE_VALUE_CAPABILITY_MAP, REST_CAPABILITY_MAP


def extract_notes_and_rests(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract note values, rests, tuplets, ties, multi-voice."""
    from music21 import note, chord
    
    for element in score.recurse().notesAndRests:
        if isinstance(element, note.Note) or isinstance(element, chord.Chord):
            # Note value
            note_type = element.duration.type
            if note_type in NOTE_VALUE_CAPABILITY_MAP:
                cap_name = NOTE_VALUE_CAPABILITY_MAP[note_type]
                result.note_values[cap_name] = result.note_values.get(cap_name, 0) + 1
            
            # Dotted notes
            if element.duration.dots > 0:
                dotted_name = f"dotted_{note_type}"
                result.dotted_notes.add(dotted_name)
            
            # Double dots
            if element.duration.dots > 1:
                result.dotted_notes.add(f"double_dotted_{note_type}")
            
            # Ties
            if element.tie is not None:
                result.has_ties = True
            
            # Tuplets
            if element.duration.tuplets:
                for t in element.duration.tuplets:
                    tuplet_name = get_tuplet_name(t)
                    result.tuplets[tuplet_name] = result.tuplets.get(tuplet_name, 0) + 1
        
        elif isinstance(element, note.Rest):
            # Rest value
            rest_type = element.duration.type
            if rest_type in REST_CAPABILITY_MAP:
                cap_name = REST_CAPABILITY_MAP[rest_type]
                result.rest_values[cap_name] = result.rest_values.get(cap_name, 0) + 1
            
            # Multi-measure rest - check for actual multi-measure rest notation
            # (not just a rest that fills one measure)
            if hasattr(element, 'multiMeasureRestSpanner') and element.multiMeasureRestSpanner is not None:
                result.has_multi_measure_rest = True
    
    # Check for multi-voice
    _extract_voice_count(score, result)


def _extract_voice_count(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract maximum voice count from all measures."""
    for part in score.parts:
        for measure in part.getElementsByClass('Measure'):
            voices = measure.voices
            if len(voices) > result.max_voices:
                result.max_voices = len(voices)


def get_tuplet_name(tuplet: Any) -> str:
    """Convert tuplet to capability name."""
    actual = tuplet.numberNotesActual
    normal = tuplet.numberNotesNormal
    
    if actual == 3 and normal == 2:
        return 'tuplet_triplet'
    elif actual == 5 and normal == 4:
        return 'tuplet_quintuplet'
    elif actual == 6 and normal == 4:
        return 'tuplet_sextuplet'
    elif actual == 7 and normal == 4:
        return 'tuplet_septuplet'
    else:
        return f'tuplet_{actual}_{normal}'
