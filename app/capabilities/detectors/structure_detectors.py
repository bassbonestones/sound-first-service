"""
Structure/Repeat Detectors

Detection functions for form and repeat-related capabilities:
coda, da capo, dal segno, fine, segno, repeat signs, endings.
"""

from typing import Callable, Dict

CUSTOM_DETECTORS: Dict[str, Callable] = {}


def register_custom_detector(name: str):
    """Decorator to register a custom detection function."""
    def decorator(func: Callable):
        CUSTOM_DETECTORS[name] = func
        return func
    return decorator


@register_custom_detector("detect_coda")
def detect_coda(extraction_result, score) -> bool:
    """Detect coda marking."""
    if score is None:
        return "coda" in str(extraction_result.repeat_structures).lower()
    from music21 import repeat
    for el in score.recurse():
        if isinstance(el, repeat.Coda):
            return True
        if hasattr(el, 'text') and 'coda' in str(el.text).lower():
            return True
    return False


@register_custom_detector("detect_da_capo")
def detect_da_capo(extraction_result, score) -> bool:
    """Detect D.C. (Da Capo) marking."""
    if score is None:
        return "d.c." in str(extraction_result.repeat_structures).lower() or "da capo" in str(extraction_result.repeat_structures).lower()
    from music21 import repeat
    for el in score.recurse():
        if isinstance(el, repeat.DaCapo):
            return True
        if hasattr(el, 'text') and ('d.c.' in str(el.text).lower() or 'da capo' in str(el.text).lower()):
            return True
    return False


@register_custom_detector("detect_dal_segno")
def detect_dal_segno(extraction_result, score) -> bool:
    """Detect D.S. (Dal Segno) marking."""
    if score is None:
        return "d.s." in str(extraction_result.repeat_structures).lower() or "dal segno" in str(extraction_result.repeat_structures).lower()
    from music21 import repeat
    for el in score.recurse():
        if isinstance(el, repeat.DalSegno):
            return True
        if hasattr(el, 'text') and ('d.s.' in str(el.text).lower() or 'dal segno' in str(el.text).lower()):
            return True
    return False


@register_custom_detector("detect_fine")
def detect_fine(extraction_result, score) -> bool:
    """Detect Fine marking."""
    if score is None:
        return "fine" in str(extraction_result.repeat_structures).lower()
    from music21 import repeat
    for el in score.recurse():
        if isinstance(el, repeat.Fine):
            return True
        if hasattr(el, 'text') and 'fine' in str(el.text).lower():
            return True
    return False


@register_custom_detector("detect_segno")
def detect_segno(extraction_result, score) -> bool:
    """Detect Segno sign."""
    if score is None:
        return "segno" in str(extraction_result.repeat_structures).lower()
    from music21 import repeat
    for el in score.recurse():
        if isinstance(el, repeat.Segno):
            return True
    return False


@register_custom_detector("detect_repeat_sign")
def detect_repeat_sign(extraction_result, score) -> bool:
    """Detect repeat barlines."""
    if score is None:
        return "repeat" in str(extraction_result.repeat_structures).lower()
    from music21 import bar
    for b in score.recurse().getElementsByClass(bar.Barline):
        if 'repeat' in b.type.lower() if hasattr(b, 'type') and b.type else False:
            return True
    for b in score.recurse().getElementsByClass(bar.Repeat):
        return True
    return False


@register_custom_detector("detect_first_ending")
def detect_first_ending(extraction_result, score) -> bool:
    """Detect first ending bracket."""
    if score is None:
        return False
    from music21 import spanner
    for sp in score.recurse().getElementsByClass(spanner.RepeatBracket):
        if sp.number == '1' or sp.number == 1:
            return True
    return False


@register_custom_detector("detect_second_ending")
def detect_second_ending(extraction_result, score) -> bool:
    """Detect second ending bracket."""
    if score is None:
        return False
    from music21 import spanner
    for sp in score.recurse().getElementsByClass(spanner.RepeatBracket):
        if sp.number == '2' or sp.number == 2:
            return True
    return False
