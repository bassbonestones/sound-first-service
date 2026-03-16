"""
Pattern Detectors

Detection functions for melodic pattern capabilities:
scale fragments, compound intervals.
"""

from typing import Any, Callable, Dict

CUSTOM_DETECTORS: Dict[str, Callable[..., bool]] = {}


def register_custom_detector(name: str) -> Callable[[Callable[..., bool]], Callable[..., bool]]:
    """Decorator to register a custom detection function."""
    def decorator(func: Callable[..., bool]) -> Callable[..., bool]:
        CUSTOM_DETECTORS[name] = func
        return func
    return decorator


@register_custom_detector("detect_compound_intervals")
def detect_compound_intervals(extraction_result: Any, score: Any) -> bool:
    """Detect compound intervals (9th or larger)."""
    for key, info in extraction_result.melodic_intervals.items():
        if info.semitones >= 13:  # More than an octave
            return True
    return False


# =============================================================================
# SCALE FRAGMENT DETECTORS
# =============================================================================

@register_custom_detector("detect_scale_fragment_2")
def detect_scale_fragment_2(extraction_result: Any, score: Any) -> bool:
    """Detect 2-note scale fragment (stepwise motion)."""
    for key, info in extraction_result.melodic_intervals.items():
        if info.semitones in [1, 2]:  # m2 or M2
            return True
    return False


@register_custom_detector("detect_scale_fragment_3")
def detect_scale_fragment_3(extraction_result: Any, score: Any) -> bool:
    """Detect 3-note scale fragment."""
    if score is None:
        return len(extraction_result.melodic_intervals) >= 2
    from music21 import note
    notes = list(score.recurse().getElementsByClass(note.Note))
    if len(notes) < 3:
        return False
    for i in range(len(notes) - 2):
        int1 = abs(notes[i+1].pitch.midi - notes[i].pitch.midi)
        int2 = abs(notes[i+2].pitch.midi - notes[i+1].pitch.midi)
        if int1 in [1, 2] and int2 in [1, 2]:
            return True
    return False


@register_custom_detector("detect_scale_fragment_4")
def detect_scale_fragment_4(extraction_result: Any, score: Any) -> bool:
    """Detect 4-note scale fragment."""
    if score is None:
        return False
    from music21 import note
    notes = list(score.recurse().getElementsByClass(note.Note))
    if len(notes) < 4:
        return False
    for i in range(len(notes) - 3):
        steps = [abs(notes[i+j+1].pitch.midi - notes[i+j].pitch.midi) for j in range(3)]
        if all(s in [1, 2] for s in steps):
            return True
    return False


@register_custom_detector("detect_scale_fragment_5")
def detect_scale_fragment_5(extraction_result: Any, score: Any) -> bool:
    """Detect 5-note scale fragment."""
    if score is None:
        return False
    from music21 import note
    notes = list(score.recurse().getElementsByClass(note.Note))
    if len(notes) < 5:
        return False
    for i in range(len(notes) - 4):
        steps = [abs(notes[i+j+1].pitch.midi - notes[i+j].pitch.midi) for j in range(4)]
        if all(s in [1, 2] for s in steps):
            return True
    return False


@register_custom_detector("detect_scale_fragment_6")
def detect_scale_fragment_6(extraction_result: Any, score: Any) -> bool:
    """Detect 6-note scale fragment."""
    if score is None:
        return False
    from music21 import note
    notes = list(score.recurse().getElementsByClass(note.Note))
    if len(notes) < 6:
        return False
    for i in range(len(notes) - 5):
        steps = [abs(notes[i+j+1].pitch.midi - notes[i+j].pitch.midi) for j in range(5)]
        if all(s in [1, 2] for s in steps):
            return True
    return False


@register_custom_detector("detect_scale_fragment_7")
def detect_scale_fragment_7(extraction_result: Any, score: Any) -> bool:
    """Detect 7-note scale fragment (full scale)."""
    if score is None:
        return False
    from music21 import note
    notes = list(score.recurse().getElementsByClass(note.Note))
    if len(notes) < 7:
        return False
    for i in range(len(notes) - 6):
        steps = [abs(notes[i+j+1].pitch.midi - notes[i+j].pitch.midi) for j in range(6)]
        if all(s in [1, 2] for s in steps):
            return True
    return False
