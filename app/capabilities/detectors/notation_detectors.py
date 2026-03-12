"""
Notation Detectors

Detection functions for general notation capabilities:
clefs, time signatures, chord symbols, figured bass, grace notes, 
breath marks, multi-measure rests, voices.
"""

from typing import Callable, Dict

CUSTOM_DETECTORS: Dict[str, Callable] = {}


def register_custom_detector(name: str):
    """Decorator to register a custom detection function."""
    def decorator(func: Callable):
        CUSTOM_DETECTORS[name] = func
        return func
    return decorator


# =============================================================================
# CLEF DETECTORS
# =============================================================================

@register_custom_detector("detect_clef_bass_8va")
def detect_clef_bass_8va(extraction_result, score) -> bool:
    """Detect bass clef with octave transposition up."""
    if score is None:
        return False
    from music21 import clef
    for c in score.recurse().getElementsByClass(clef.Clef):
        if isinstance(c, clef.Bass8vaClef) or (hasattr(c, 'sign') and c.sign == 'F' and hasattr(c, 'octaveChange') and c.octaveChange == 1):
            return True
    return False


@register_custom_detector("detect_clef_treble_8vb")
def detect_clef_treble_8vb(extraction_result, score) -> bool:
    """Detect treble clef with octave transposition down."""
    if score is None:
        return False
    from music21 import clef
    for c in score.recurse().getElementsByClass(clef.Clef):
        if isinstance(c, clef.Treble8vbClef) or (hasattr(c, 'sign') and c.sign == 'G' and hasattr(c, 'octaveChange') and c.octaveChange == -1):
            return True
    return False


# =============================================================================
# TIME SIGNATURE DETECTORS
# =============================================================================

@register_custom_detector("detect_any_time_signature")
def detect_any_time_signature(extraction_result, score) -> bool:
    """Detect presence of any time signature."""
    return len(extraction_result.time_signatures) > 0


# =============================================================================
# NOTATION SYMBOL DETECTORS
# =============================================================================

@register_custom_detector("detect_chord_symbols")
def detect_chord_symbols(extraction_result, score) -> bool:
    """Detect chord symbols (lead sheet notation)."""
    if len(extraction_result.chord_symbols) > 0:
        return True
    if score is None:
        return False
    from music21 import harmony
    for h in score.recurse().getElementsByClass(harmony.ChordSymbol):
        return True
    return False


@register_custom_detector("detect_figured_bass")
def detect_figured_bass(extraction_result, score) -> bool:
    """Detect figured bass notation."""
    if extraction_result.figured_bass:
        return True
    if score is None:
        return False
    
    try:
        from music21 import figuredBass
        for fb in score.recurse().getElementsByClass(figuredBass.notation.Notation):
            return True
    except (ImportError, AttributeError, TypeError) as e:
        pass
    
    try:
        for fb in score.recurse().getElementsByClass('FiguredBass'):
            return True
    except (AttributeError, TypeError) as e:
        pass
    
    try:
        from music21.figuredBass import notation as figuredBassNotation
        for elem in score.recurse():
            if 'FiguredBass' in type(elem).__name__:
                return True
    except (ImportError, AttributeError, TypeError) as e:
        pass
    
    try:
        file_path = None
        if hasattr(score, 'filePath') and score.filePath:
            file_path = score.filePath
        elif hasattr(score, 'metadata') and hasattr(score.metadata, 'filePath') and score.metadata.filePath:
            file_path = score.metadata.filePath
        if file_path:
            import os
            if os.path.exists(file_path):
                with open(file_path, 'r') as f:
                    content = f.read()
                    if '<figured-bass>' in content or '<figure-number>' in content:
                        return True
    except (OSError, IOError, AttributeError) as e:
        pass
    return False


@register_custom_detector("detect_grace_note")
def detect_grace_note(extraction_result, score) -> bool:
    """Detect grace notes."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().getElementsByClass(note.Note):
        if n.duration.isGrace:
            return True
    return False


@register_custom_detector("detect_breath_mark")
def detect_breath_mark(extraction_result, score) -> bool:
    """Detect breath marks."""
    if extraction_result.breath_marks > 0:
        return True
    if score is None:
        return False
    from music21 import articulations
    for n in score.recurse().notes:
        for art in n.articulations:
            if isinstance(art, articulations.BreathMark):
                return True
    return False


@register_custom_detector("detect_multimeasure_rest")
def detect_multimeasure_rest(extraction_result, score) -> bool:
    """Detect multi-measure rest."""
    return extraction_result.has_multi_measure_rest


# =============================================================================
# TEXTURE DETECTORS
# =============================================================================

@register_custom_detector("detect_two_voices")
def detect_two_voices(extraction_result, score) -> bool:
    """Detect two-voice texture."""
    if score is None:
        return False
    voices = set()
    for p in score.parts:
        for m in p.getElementsByClass('Measure'):
            for v in m.voices:
                voices.add(v.id)
    return len(voices) >= 2 or len(score.parts) >= 2


@register_custom_detector("detect_three_voices")
def detect_three_voices(extraction_result, score) -> bool:
    """Detect three-voice texture."""
    if score is None:
        return False
    voices = set()
    for p in score.parts:
        for m in p.getElementsByClass('Measure'):
            for v in m.voices:
                voices.add(f"{p.id}_{v.id}")
    return len(voices) >= 3 or len(score.parts) >= 3


@register_custom_detector("detect_four_voices")
def detect_four_voices(extraction_result, score) -> bool:
    """Detect four-voice texture."""
    if score is None:
        return False
    voices = set()
    for p in score.parts:
        for m in p.getElementsByClass('Measure'):
            for v in m.voices:
                voices.add(f"{p.id}_{v.id}")
    return len(voices) >= 4 or len(score.parts) >= 4
