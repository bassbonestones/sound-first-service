"""
Tempo event parsing functions.

Parses tempo-related elements from music21 scores into structured TempoEvent objects.
"""

from typing import List, Optional, Tuple

try:
    from music21 import stream, tempo, expressions
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

from .types import (
    TEMPO_TERM_BPM,
    TEMPO_MODIFIER_TERMS,
    TempoSourceType,
    TempoChangeType,
    TempoEvent,
)


def estimate_bpm_from_term(term: str) -> Tuple[Optional[int], bool]:
    """
    Estimate BPM from an Italian tempo term.
    
    Args:
        term: The tempo term (case insensitive)
        
    Returns:
        Tuple of (estimated_bpm, is_approximate)
        If term not recognized, returns (None, False)
    """
    term_lower = term.lower().strip()
    
    # Check for exact matches first
    if term_lower in TEMPO_TERM_BPM:
        _, typical, _ = TEMPO_TERM_BPM[term_lower]
        return (typical, True)
    
    # Check for partial matches (term might be combined like "Allegro ma non troppo")
    for tempo_term, (_, typical, _) in TEMPO_TERM_BPM.items():
        if tempo_term in term_lower:
            return (typical, True)
    
    return (None, False)


def classify_tempo_term(text: str) -> Optional[TempoChangeType]:
    """
    Classify a text string as a tempo modifier type.
    
    Args:
        text: The tempo text to classify
        
    Returns:
        TempoChangeType or None if not a modifier
    """
    text_lower = text.lower().strip()
    
    for term, change_type in TEMPO_MODIFIER_TERMS.items():
        if term in text_lower:
            return TempoChangeType(change_type)
    
    return None


def parse_tempo_events(score: stream.Score) -> List[TempoEvent]:
    """
    Parse all tempo events from a music21 score in order.
    
    Args:
        score: music21 Score object
        
    Returns:
        List of TempoEvent objects in measure order
    """
    events: List[TempoEvent] = []
    
    if score is None:
        return events
    
    # Get all measures to map offsets to measure numbers
    parts = list(score.parts)
    if not parts:
        return events
    
    # Use first part for measure mapping
    first_part = parts[0]
    measures = list(first_part.getElementsByClass(stream.Measure))
    
    # Build offset -> measure number map
    measure_map = {}  # offset -> measure_number
    for m in measures:
        if m.measureNumber is not None:
            measure_map[m.offset] = m.measureNumber
    
    def get_measure_number(offset: float) -> int:
        """Get measure number for a given offset."""
        # Find the measure that contains this offset
        for meas_offset, meas_num in sorted(measure_map.items()):
            if offset >= meas_offset:
                best = meas_num
            else:
                break
        return best if 'best' in dir() else 1
    
    # Parse MetronomeMark objects
    for t in score.recurse().getElementsByClass(tempo.MetronomeMark):
        measure_num = get_measure_number(t.getOffsetInHierarchy(score))
        offset_in_meas = t.offset if hasattr(t, 'offset') else 0.0
        
        bpm = int(t.number) if t.number else None
        text = t.text if t.text else None
        
        # Determine source type
        if bpm is not None:
            source_type = TempoSourceType.METRONOME_MARK
            is_approx = False
        elif text:
            source_type = TempoSourceType.TEXT_TERM
            # Try to estimate BPM from text
            estimated, is_approx = estimate_bpm_from_term(text)
            if estimated:
                bpm = estimated
            else:
                is_approx = True
        else:
            continue  # No useful info
        
        # Classify change type
        change_type = TempoChangeType.INITIAL if not events else TempoChangeType.SUDDEN_CHANGE
        if text:
            modifier = classify_tempo_term(text)
            if modifier:
                change_type = modifier
        
        events.append(TempoEvent(
            measure_number=measure_num,
            offset_in_measure=offset_in_meas,
            bpm=bpm,
            text=text,
            source_type=source_type,
            change_type=change_type,
            is_approximate=is_approx if bpm else True,
        ))
    
    # Parse TempoText objects
    for t in score.recurse().getElementsByClass(tempo.TempoText):
        if not t.text:
            continue
            
        measure_num = get_measure_number(t.getOffsetInHierarchy(score))
        offset_in_meas = t.offset if hasattr(t, 'offset') else 0.0
        text = t.text
        
        # Check if this is a modifier (rit., accel., a tempo)
        modifier = classify_tempo_term(text)
        
        # Try to get BPM from term
        estimated, is_approx = estimate_bpm_from_term(text)
        
        if modifier:
            change_type = modifier
        elif estimated:
            change_type = TempoChangeType.SUDDEN_CHANGE if events else TempoChangeType.INITIAL
        else:
            # Unknown text, skip
            continue
        
        events.append(TempoEvent(
            measure_number=measure_num,
            offset_in_measure=offset_in_meas,
            bpm=estimated,
            text=text,
            source_type=TempoSourceType.TEXT_TERM,
            change_type=change_type,
            is_approximate=is_approx,
        ))
    
    # Parse TextExpression objects for tempo indications
    for te in score.recurse().getElementsByClass(expressions.TextExpression):
        if not te.content:
            continue
            
        text = te.content
        text_lower = text.lower()
        
        # Check if it's a tempo-related expression
        modifier = classify_tempo_term(text)
        estimated, is_approx = estimate_bpm_from_term(text)
        
        if not modifier and not estimated:
            # Not tempo-related
            continue
        
        measure_num = get_measure_number(te.getOffsetInHierarchy(score))
        offset_in_meas = te.offset if hasattr(te, 'offset') else 0.0
        
        if modifier:
            change_type = modifier
        else:
            change_type = TempoChangeType.SUDDEN_CHANGE if events else TempoChangeType.INITIAL
        
        events.append(TempoEvent(
            measure_number=measure_num,
            offset_in_measure=offset_in_meas,
            bpm=estimated,
            text=text,
            source_type=TempoSourceType.TEXT_EXPRESSION,
            change_type=change_type,
            is_approximate=is_approx,
        ))
    
    # Sort by measure number, then offset
    events.sort(key=lambda e: (e.measure_number, e.offset_in_measure))
    
    # Deduplicate (same measure, same type)
    deduped = []
    for event in events:
        if not deduped:
            deduped.append(event)
        elif (deduped[-1].measure_number == event.measure_number and
              deduped[-1].change_type == event.change_type and
              deduped[-1].bpm == event.bpm):
            # Skip duplicate
            continue
        else:
            deduped.append(event)
    
    return deduped
