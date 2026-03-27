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

def _is_stepwise_same_direction(notes: list[Any], start: int, count: int) -> bool:
    """Check if 'count' consecutive intervals from 'start' are stepwise and same direction."""
    intervals = []
    for j in range(count):
        diff = notes[start+j+1].pitch.midi - notes[start+j].pitch.midi
        # Must be stepwise (1 or 2 semitones) - check absolute value
        if abs(diff) not in [1, 2]:
            return False
        intervals.append(diff)
    
    # All must be same direction (all positive or all negative)
    if all(i > 0 for i in intervals) or all(i < 0 for i in intervals):
        return True
    return False


@register_custom_detector("detect_scale_fragment_2")
def detect_scale_fragment_2(extraction_result: Any, score: Any) -> bool:
    """Detect 2-note scale fragment (stepwise motion)."""
    for key, info in extraction_result.melodic_intervals.items():
        if info.semitones in [1, 2]:  # m2 or M2
            return True
    return False


@register_custom_detector("detect_scale_fragment_3")
def detect_scale_fragment_3(extraction_result: Any, score: Any) -> bool:
    """Detect 3-note scale fragment (2 consecutive steps in same direction)."""
    if score is None:
        return len(extraction_result.melodic_intervals) >= 2
    from music21 import note
    notes = list(score.recurse().getElementsByClass(note.Note))
    if len(notes) < 3:
        return False
    for i in range(len(notes) - 2):
        if _is_stepwise_same_direction(notes, i, 2):
            return True
    return False


@register_custom_detector("detect_scale_fragment_4")
def detect_scale_fragment_4(extraction_result: Any, score: Any) -> bool:
    """Detect 4-note scale fragment (3 consecutive steps in same direction)."""
    if score is None:
        return False
    from music21 import note
    notes = list(score.recurse().getElementsByClass(note.Note))
    if len(notes) < 4:
        return False
    for i in range(len(notes) - 3):
        if _is_stepwise_same_direction(notes, i, 3):
            return True
    return False


@register_custom_detector("detect_scale_fragment_5")
def detect_scale_fragment_5(extraction_result: Any, score: Any) -> bool:
    """Detect 5-note scale fragment (4 consecutive steps in same direction)."""
    if score is None:
        return False
    from music21 import note
    notes = list(score.recurse().getElementsByClass(note.Note))
    if len(notes) < 5:
        return False
    for i in range(len(notes) - 4):
        if _is_stepwise_same_direction(notes, i, 4):
            return True
    return False


@register_custom_detector("detect_scale_fragment_6")
def detect_scale_fragment_6(extraction_result: Any, score: Any) -> bool:
    """Detect 6-note scale fragment (5 consecutive steps in same direction)."""
    if score is None:
        return False
    from music21 import note
    notes = list(score.recurse().getElementsByClass(note.Note))
    if len(notes) < 6:
        return False
    for i in range(len(notes) - 5):
        if _is_stepwise_same_direction(notes, i, 5):
            return True
    return False


@register_custom_detector("detect_scale_fragment_7")
def detect_scale_fragment_7(extraction_result: Any, score: Any) -> bool:
    """Detect 7-note scale fragment (6 consecutive steps in same direction)."""
    if score is None:
        return False
    from music21 import note
    notes = list(score.recurse().getElementsByClass(note.Note))
    if len(notes) < 7:
        return False
    for i in range(len(notes) - 6):
        if _is_stepwise_same_direction(notes, i, 6):
            return True
    return False
