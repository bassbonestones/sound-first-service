"""
Dynamics Detectors

Detection functions for dynamics-related capabilities:
decrescendo, subito dynamics.
"""

from typing import Callable, Dict

CUSTOM_DETECTORS: Dict[str, Callable] = {}


def register_custom_detector(name: str):
    """Decorator to register a custom detection function."""
    def decorator(func: Callable):
        CUSTOM_DETECTORS[name] = func
        return func
    return decorator


@register_custom_detector("detect_decrescendo")
def detect_decrescendo(extraction_result, score) -> bool:
    """Detect decrescendo (diminuendo wedge or text)."""
    if score is None:
        return False
    from music21 import dynamics, expressions
    
    for dyn in score.recurse().getElementsByClass(dynamics.Diminuendo):
        return True
    
    for el in score.recurse():
        if hasattr(el, 'content') and isinstance(el.content, str):
            if 'decresc' in el.content.lower():
                return True
        if isinstance(el, expressions.TextExpression):
            if 'decresc' in el.content.lower():
                return True
    return False


@register_custom_detector("detect_subito")
def detect_subito(extraction_result, score) -> bool:
    """Detect subito (sudden) dynamic change."""
    if hasattr(extraction_result, 'dynamic_changes'):
        changes = extraction_result.dynamic_changes or []
        for change in changes:
            if 'subito' in str(change).lower():
                return True
    
    if score is None:
        return False
    from music21 import expressions
    for el in score.recurse():
        if isinstance(el, expressions.TextExpression):
            if 'subito' in el.content.lower():
                return True
        if hasattr(el, 'content') and isinstance(el.content, str):
            if 'subito' in el.content.lower():
                return True
    return False
