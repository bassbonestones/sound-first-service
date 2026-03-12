"""
Accidental/Tonal Detectors

Detection functions for pitch-related capabilities:
accidentals, chromatic approach tones, modulation.
"""

from typing import Callable, Dict

CUSTOM_DETECTORS: Dict[str, Callable] = {}


def register_custom_detector(name: str):
    """Decorator to register a custom detection function."""
    def decorator(func: Callable):
        CUSTOM_DETECTORS[name] = func
        return func
    return decorator


@register_custom_detector("detect_flat_accidentals")
def detect_flat_accidentals(extraction_result, score) -> bool:
    """Detect flat accidentals in the music."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().getElementsByClass(note.Note):
        if n.pitch.alter == -1:
            return True
    return False


@register_custom_detector("detect_sharp_accidentals")
def detect_sharp_accidentals(extraction_result, score) -> bool:
    """Detect sharp accidentals in the music."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().getElementsByClass(note.Note):
        if n.pitch.alter == 1:
            return True
    return False


@register_custom_detector("detect_natural_accidentals")
def detect_natural_accidentals(extraction_result, score) -> bool:
    """Detect natural accidentals (explicit naturals)."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().getElementsByClass(note.Note):
        if n.pitch.accidental and n.pitch.accidental.name == 'natural':
            return True
    return False


@register_custom_detector("detect_double_flat_accidentals")
def detect_double_flat_accidentals(extraction_result, score) -> bool:
    """Detect double-flat accidentals."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().getElementsByClass(note.Note):
        if n.pitch.alter == -2:
            return True
    return False


@register_custom_detector("detect_double_sharp_accidentals")
def detect_double_sharp_accidentals(extraction_result, score) -> bool:
    """Detect double-sharp accidentals."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().getElementsByClass(note.Note):
        if n.pitch.alter == 2:
            return True
    return False


@register_custom_detector("detect_chromatic_approach_tones")
def detect_chromatic_approach_tones(extraction_result, score) -> bool:
    """Detect chromatic approach tones (chromatic note approaching diatonic target by half-step)."""
    if score is None:
        return False
    
    from music21 import note as m21note, key as m21key
    
    notes = list(score.recurse().getElementsByClass(m21note.Note))
    if len(notes) < 2:
        return False
    
    key_obj = None
    for elem in score.recurse():
        if isinstance(elem, m21key.Key) or isinstance(elem, m21key.KeySignature):
            if isinstance(elem, m21key.KeySignature):
                key_obj = elem.asKey()
            else:
                key_obj = elem
            break
    
    if key_obj is None:
        try:
            key_obj = score.analyze('key')
        except (AttributeError, ValueError, TypeError) as e:
            return False
    
    if key_obj is None:
        return False
    
    try:
        scale = key_obj.getScale()
        scale_pitch_classes = set(p.pitchClass for p in scale.getPitches())
    except (AttributeError, ValueError, TypeError) as e:
        return False
    
    for i in range(len(notes) - 1):
        interval = abs(notes[i+1].pitch.midi - notes[i].pitch.midi)
        if interval == 1:
            first_pc = notes[i].pitch.pitchClass
            second_pc = notes[i+1].pitch.pitchClass
            
            if first_pc not in scale_pitch_classes and second_pc in scale_pitch_classes:
                return True
    
    return False


@register_custom_detector("detect_modulation")
def detect_modulation(extraction_result, score) -> bool:
    """Detect key change / modulation."""
    return len(extraction_result.key_signatures) > 1


@register_custom_detector("detect_any_key_signature")
def detect_any_key_signature(extraction_result, score) -> bool:
    """Detect presence of any key signature."""
    return len(extraction_result.key_signatures) > 0
