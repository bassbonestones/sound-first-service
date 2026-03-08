"""
Rhythm Detectors

Detection functions for rhythm-related capabilities:
syncopation, ties, hemiola, tuplets, triplets.
"""

from typing import Callable, Dict

# Inherited registry
CUSTOM_DETECTORS: Dict[str, Callable] = {}


def register_custom_detector(name: str):
    """Decorator to register a custom detection function."""
    def decorator(func: Callable):
        CUSTOM_DETECTORS[name] = func
        return func
    return decorator


@register_custom_detector("detect_syncopation")
def detect_syncopation(extraction_result, score) -> bool:
    """Detect syncopation patterns in the music.
    
    Syncopation occurs when notes start on weak beats and continue to strong beats,
    or when emphasis is placed on off-beats. Common patterns:
    - Eighth-quarter-eighth pattern (short-long-short)
    - Notes starting on "and" of the beat
    - Ties from weak to strong beats
    """
    if score is None:
        return False
    
    from music21 import note
    
    for part in score.parts:
        notes_and_rests = list(part.recurse().notesAndRests)
        
        for i in range(len(notes_and_rests) - 2):
            n1 = notes_and_rests[i]
            n2 = notes_and_rests[i + 1]
            n3 = notes_and_rests[i + 2]
            
            if not all(isinstance(n, note.Note) for n in [n1, n2, n3]):
                continue
            
            ql1 = n1.duration.quarterLength
            ql2 = n2.duration.quarterLength
            ql3 = n3.duration.quarterLength
            
            if ql1 > 0 and ql3 > 0:
                if (ql2 > ql1 and ql2 > ql3):
                    if (ql1 == 0.5 and ql2 == 1.0 and ql3 == 0.5):
                        return True
                    if (ql1 == 0.25 and ql2 == 0.5 and ql3 == 0.25):
                        return True
    
    if extraction_result.has_ties:
        return True
    
    return False


@register_custom_detector("detect_ties")
def detect_ties(extraction_result, score) -> bool:
    """Detect presence of tied notes."""
    return extraction_result.has_ties


@register_custom_detector("detect_hemiola")
def detect_hemiola(extraction_result, score) -> bool:
    """Detect hemiola patterns (3 against 2)."""
    return False  # Stub - would need to analyze rhythm groupings


# =============================================================================
# TUPLET DETECTORS
# =============================================================================

@register_custom_detector("detect_eighth_triplets")
def detect_eighth_triplets(extraction_result, score) -> bool:
    """Detect eighth note triplets."""
    return "tuplet_3_eighth" in extraction_result.tuplets


@register_custom_detector("detect_quarter_triplets")
def detect_quarter_triplets(extraction_result, score) -> bool:
    """Detect quarter note triplets (3 quarters in time of 2)."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().notesAndRests:
        if isinstance(n, note.Note):
            tuplets = n.duration.tuplets
            if tuplets:
                for t in tuplets:
                    if t.numberNotesActual == 3 and t.numberNotesNormal == 2:
                        if n.duration.type == 'quarter':
                            return True
    return False


@register_custom_detector("detect_duplet")
def detect_duplet(extraction_result, score) -> bool:
    """Detect duplets (2 notes in space of 3)."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().notesAndRests:
        tuplets = n.duration.tuplets
        if tuplets and any(t.numberNotesActual == 2 for t in tuplets):
            return True
    return False


@register_custom_detector("detect_quintuplet")
def detect_quintuplet(extraction_result, score) -> bool:
    """Detect quintuplets (5 notes in space of 4)."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().notesAndRests:
        tuplets = n.duration.tuplets
        if tuplets and any(t.numberNotesActual == 5 for t in tuplets):
            return True
    return False


@register_custom_detector("detect_sextuplet")
def detect_sextuplet(extraction_result, score) -> bool:
    """Detect sextuplets (6 notes)."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().notesAndRests:
        tuplets = n.duration.tuplets
        if tuplets and any(t.numberNotesActual == 6 for t in tuplets):
            return True
    return False


@register_custom_detector("detect_septuplet")
def detect_septuplet(extraction_result, score) -> bool:
    """Detect septuplets (7 notes)."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().notesAndRests:
        tuplets = n.duration.tuplets
        if tuplets and any(t.numberNotesActual == 7 for t in tuplets):
            return True
    return False


@register_custom_detector("detect_triplet_general")
def detect_triplet_general(extraction_result, score) -> bool:
    """Detect any triplet figure (3 notes in time of 2)."""
    if "tuplet_triplet" in extraction_result.tuplets:
        return True
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().notesAndRests:
        tuplets = n.duration.tuplets
        if tuplets:
            for t in tuplets:
                if t.numberNotesActual == 3 and t.numberNotesNormal == 2:
                    return True
    return False


@register_custom_detector("detect_triplet_eighth_rest")
def detect_triplet_eighth_rest(extraction_result, score) -> bool:
    """Detect eighth note rest within a triplet."""
    if score is None:
        return False
    from music21 import note
    for r in score.recurse().getElementsByClass(note.Rest):
        if r.duration.type == 'eighth':
            tuplets = r.duration.tuplets
            if tuplets and any(t.numberNotesActual == 3 for t in tuplets):
                return True
    return False


@register_custom_detector("detect_tuplet_3_quarter_rest")
def detect_tuplet_3_quarter_rest(extraction_result, score) -> bool:
    """Detect quarter note rest within a triplet."""
    if score is None:
        return False
    from music21 import note
    for r in score.recurse().getElementsByClass(note.Rest):
        if r.duration.type == 'quarter':
            tuplets = r.duration.tuplets
            if tuplets and any(t.numberNotesActual == 3 for t in tuplets):
                return True
    return False
