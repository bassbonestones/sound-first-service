"""
Capability Registry for Sound First

Manages capability detection rules loaded from capabilities.json.
Validates rules at startup and provides a detection engine that
applies rules to MusicXML extraction results.

Detection Types:
- element: Direct music21 class presence check
- value_match: Field comparison on source objects
- compound: Multiple conditions (AND logic)
- interval: Melodic/harmonic interval detection
- text_match: TextExpression content matching
- time_signature: Time signature numerator/denominator match
- range: Interval size range check
- custom: Python function fallback
- null: Not auto-detectable (foundational capabilities)
"""

import json
import logging
from typing import Dict, List, Optional, Set, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


# =============================================================================
# DETECTION TYPES ENUM
# =============================================================================

class DetectionType(str, Enum):
    ELEMENT = "element"
    VALUE_MATCH = "value_match"
    COMPOUND = "compound"
    INTERVAL = "interval"
    TEXT_MATCH = "text_match"
    TIME_SIGNATURE = "time_signature"
    RANGE = "range"
    CUSTOM = "custom"


# =============================================================================
# DETECTION RULE SCHEMA
# =============================================================================

@dataclass
class DetectionRule:
    """Validated detection rule for a capability."""
    capability_name: str
    detection_type: Optional[DetectionType]
    config: Dict[str, Any]
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


# =============================================================================
# VALID SOURCES FOR VALUE_MATCH, COMPOUND, TEXT_MATCH
# =============================================================================

VALID_SOURCES = {
    "notes",
    "dynamics", 
    "tempos",
    "expressions",
    "articulations",
    "clefs",
    "key_signatures",
    "time_signatures",
    "intervals",
    "ornaments",
    "rests",
}


# =============================================================================
# REGISTRY FOR CUSTOM DETECTION FUNCTIONS
# =============================================================================

# Custom detection functions are registered here
# Each function takes (extraction_result, score) and returns bool
CUSTOM_DETECTORS: Dict[str, Callable] = {}


def register_custom_detector(name: str):
    """Decorator to register a custom detection function."""
    def decorator(func: Callable):
        CUSTOM_DETECTORS[name] = func
        return func
    return decorator


# Example custom detectors (can be expanded)
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
    
    # Look for common syncopation patterns by examining note sequences
    for part in score.parts:
        notes_and_rests = list(part.recurse().notesAndRests)
        
        for i in range(len(notes_and_rests) - 2):
            n1 = notes_and_rests[i]
            n2 = notes_and_rests[i + 1]
            n3 = notes_and_rests[i + 2]
            
            # All must be notes (not rests)
            if not all(isinstance(n, note.Note) for n in [n1, n2, n3]):
                continue
            
            # Get quarter lengths
            ql1 = n1.duration.quarterLength
            ql2 = n2.duration.quarterLength
            ql3 = n3.duration.quarterLength
            
            # Check for syncopation patterns:
            # 1. eighth-quarter-eighth (0.5-1.0-0.5)
            # 2. short-long-short where middle is longer than surrounding
            if ql1 > 0 and ql3 > 0:
                if (ql2 > ql1 and ql2 > ql3):
                    # Middle note is longer - possible syncopation
                    # Common case: eighth-quarter-eighth
                    if (ql1 == 0.5 and ql2 == 1.0 and ql3 == 0.5):
                        return True
                    # Also check for sixteenth-eighth-sixteenth
                    if (ql1 == 0.25 and ql2 == 0.5 and ql3 == 0.25):
                        return True
    
    # Also check for ties which often create syncopation
    if extraction_result.has_ties:
        # Having ties suggests potential syncopation
        return True
    
    return False


@register_custom_detector("detect_any_key_signature")
def detect_any_key_signature(extraction_result, score) -> bool:
    """Detect presence of any key signature."""
    return len(extraction_result.key_signatures) > 0


@register_custom_detector("detect_ties")
def detect_ties(extraction_result, score) -> bool:
    """Detect presence of tied notes."""
    return extraction_result.has_ties


@register_custom_detector("detect_hemiola")
def detect_hemiola(extraction_result, score) -> bool:
    """Detect hemiola patterns (3 against 2)."""
    # Stub - would need to analyze rhythm groupings
    return False


# =============================================================================
# ACCIDENTAL DETECTORS
# =============================================================================

@register_custom_detector("detect_flat_accidentals")
def detect_flat_accidentals(extraction_result, score) -> bool:
    """Detect flat accidentals in the music."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().getElementsByClass(note.Note):
        if n.pitch.alter == -1:  # flat
            return True
    return False


@register_custom_detector("detect_sharp_accidentals")
def detect_sharp_accidentals(extraction_result, score) -> bool:
    """Detect sharp accidentals in the music."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().getElementsByClass(note.Note):
        if n.pitch.alter == 1:  # sharp
            return True
    return False


@register_custom_detector("detect_natural_accidentals")
def detect_natural_accidentals(extraction_result, score) -> bool:
    """Detect natural accidentals (explicit naturals)."""
    if score is None:
        return False
    from music21 import note, pitch
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
        if n.pitch.alter == -2:  # double flat
            return True
    return False


@register_custom_detector("detect_double_sharp_accidentals")
def detect_double_sharp_accidentals(extraction_result, score) -> bool:
    """Detect double-sharp accidentals."""
    if score is None:
        return False
    from music21 import note
    for n in score.recurse().getElementsByClass(note.Note):
        if n.pitch.alter == 2:  # double sharp
            return True
    return False


# =============================================================================
# DYNAMICS DETECTORS
# =============================================================================

@register_custom_detector("detect_decrescendo")
def detect_decrescendo(extraction_result, score) -> bool:
    """Detect decrescendo (diminuendo wedge or text)."""
    if score is None:
        return False
    from music21 import dynamics, expressions
    # Check for diminuendo wedge (decrescendo and diminuendo are synonymous)
    for dyn in score.recurse().getElementsByClass(dynamics.Diminuendo):
        return True
    # Also check for text "decresc" in expressions
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
    # Check extraction result for dynamic_change_subito
    if hasattr(extraction_result, 'dynamic_changes'):
        changes = extraction_result.dynamic_changes or []
        for change in changes:
            if 'subito' in str(change).lower():
                return True
    # Also check score text expressions
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
# FORM/REPEAT DETECTORS
# =============================================================================

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


# =============================================================================
# INTERVAL DETECTORS
# =============================================================================

@register_custom_detector("detect_compound_intervals")
def detect_compound_intervals(extraction_result, score) -> bool:
    """Detect compound intervals (9th or larger)."""
    for key, info in extraction_result.melodic_intervals.items():
        if info.semitones >= 13:  # More than an octave
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
    if extraction_result.chord_symbols > 0:
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
    if score is None:
        return False
    from music21 import figuredBass
    try:
        for fb in score.recurse().getElementsByClass(figuredBass.notation.Notation):
            return True
    except:
        pass
    return False


# =============================================================================
# REST DETECTORS
# =============================================================================

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


@register_custom_detector("detect_multimeasure_rest")
def detect_multimeasure_rest(extraction_result, score) -> bool:
    """Detect multi-measure rest."""
    return extraction_result.has_multi_measure_rest


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


# =============================================================================
# RHYTHM/TUPLET DETECTORS
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
                    # Check for triplet (3:2) with quarter note type
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
    # Check extraction result tuplets for triplet key
    if "tuplet_triplet" in extraction_result.tuplets:
        return True
    # Also check with music21 directly
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


# =============================================================================
# TONAL CONTEXT DETECTORS
# =============================================================================

@register_custom_detector("detect_scale_fragment_2")
def detect_scale_fragment_2(extraction_result, score) -> bool:
    """Detect 2-note scale fragment (stepwise motion)."""
    for key, info in extraction_result.melodic_intervals.items():
        if info.semitones in [1, 2]:  # m2 or M2
            return True
    return False


@register_custom_detector("detect_scale_fragment_3")
def detect_scale_fragment_3(extraction_result, score) -> bool:
    """Detect 3-note scale fragment."""
    # Check for consecutive stepwise intervals
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
def detect_scale_fragment_4(extraction_result, score) -> bool:
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
def detect_scale_fragment_5(extraction_result, score) -> bool:
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
def detect_scale_fragment_6(extraction_result, score) -> bool:
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
def detect_scale_fragment_7(extraction_result, score) -> bool:
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


@register_custom_detector("detect_chromatic_approach_tones")
def detect_chromatic_approach_tones(extraction_result, score) -> bool:
    """Detect chromatic approach tones (half-step motion to target)."""
    # Check for semitone intervals
    for key, info in extraction_result.melodic_intervals.items():
        if info.semitones == 1:
            return True
    return False


@register_custom_detector("detect_modulation")
def detect_modulation(extraction_result, score) -> bool:
    """Detect key change / modulation."""
    # Simple heuristic: multiple key signatures detected
    return len(extraction_result.key_signatures) > 1


# =============================================================================
# VALIDATION FUNCTIONS
# =============================================================================

def validate_detection_rule(capability_name: str, rule_config: Optional[Dict]) -> DetectionRule:
    """
    Validate a detection rule configuration.
    
    Returns a DetectionRule with is_valid=False and errors if invalid.
    """
    errors = []
    
    # Null/missing detection = not auto-detectable
    if rule_config is None:
        return DetectionRule(
            capability_name=capability_name,
            detection_type=None,
            config={},
            is_valid=True,
        )
    
    # Must have a type
    rule_type = rule_config.get("type")
    if not rule_type:
        errors.append("Missing 'type' field")
        return DetectionRule(
            capability_name=capability_name,
            detection_type=None,
            config=rule_config,
            is_valid=False,
            validation_errors=errors,
        )
    
    # Validate type is known
    try:
        detection_type = DetectionType(rule_type)
    except ValueError:
        errors.append(f"Unknown detection type: {rule_type}")
        return DetectionRule(
            capability_name=capability_name,
            detection_type=None,
            config=rule_config,
            is_valid=False,
            validation_errors=errors,
        )
    
    # Type-specific validation
    if detection_type == DetectionType.ELEMENT:
        if "class" not in rule_config:
            errors.append("'element' type requires 'class' field")
    
    elif detection_type == DetectionType.VALUE_MATCH:
        if "source" not in rule_config:
            errors.append("'value_match' type requires 'source' field")
        elif rule_config["source"] not in VALID_SOURCES:
            errors.append(f"Invalid source: {rule_config['source']}")
        if "field" not in rule_config:
            errors.append("'value_match' type requires 'field' field")
        if not any(k in rule_config for k in ["eq", "contains", "gte", "lte"]):
            errors.append("'value_match' type requires one of: eq, contains, gte, lte")
    
    elif detection_type == DetectionType.COMPOUND:
        if "source" not in rule_config:
            errors.append("'compound' type requires 'source' field")
        elif rule_config["source"] not in VALID_SOURCES:
            errors.append(f"Invalid source: {rule_config['source']}")
        if "conditions" not in rule_config or not isinstance(rule_config["conditions"], list):
            errors.append("'compound' type requires 'conditions' array")
    
    elif detection_type == DetectionType.INTERVAL:
        if "quality" not in rule_config:
            errors.append("'interval' type requires 'quality' field")
    
    elif detection_type == DetectionType.TEXT_MATCH:
        if "source" not in rule_config:
            errors.append("'text_match' type requires 'source' field")
        if "contains" not in rule_config and "equals" not in rule_config:
            errors.append("'text_match' type requires 'contains' or 'equals' field")
    
    elif detection_type == DetectionType.TIME_SIGNATURE:
        if "numerator" not in rule_config:
            errors.append("'time_signature' type requires 'numerator' field")
        if "denominator" not in rule_config:
            errors.append("'time_signature' type requires 'denominator' field")
    
    elif detection_type == DetectionType.RANGE:
        if "min_semitones" not in rule_config and "max_semitones" not in rule_config:
            errors.append("'range' type requires at least one of: min_semitones, max_semitones")
    
    elif detection_type == DetectionType.CUSTOM:
        if "function" not in rule_config:
            errors.append("'custom' type requires 'function' field")
        elif rule_config["function"] not in CUSTOM_DETECTORS:
            errors.append(f"Unknown custom function: {rule_config['function']}")
    
    return DetectionRule(
        capability_name=capability_name,
        detection_type=detection_type,
        config=rule_config,
        is_valid=len(errors) == 0,
        validation_errors=errors,
    )


# =============================================================================
# CAPABILITY REGISTRY CLASS
# =============================================================================

class CapabilityRegistry:
    """
    Registry for capability detection rules.
    
    Loads rules from capabilities.json, validates them at startup,
    and provides detection against MusicXML extraction results.
    """
    
    def __init__(self, capabilities_path: Optional[str] = None):
        """
        Initialize the registry.
        
        Args:
            capabilities_path: Path to capabilities.json. If None, uses default.
        """
        self.capabilities_path = capabilities_path or self._default_path()
        self.rules: Dict[str, DetectionRule] = {}
        self.capabilities_by_domain: Dict[str, List[str]] = {}
        self._loaded = False
    
    def _default_path(self) -> str:
        """Get default path to capabilities.json."""
        base = Path(__file__).parent.parent
        return str(base / "resources" / "capabilities.json")
    
    def load(self) -> Dict[str, List[str]]:
        """
        Load and validate all capability detection rules.
        
        Returns:
            Dict of validation issues: {"warnings": [...], "errors": [...]}
        """
        issues = {"warnings": [], "errors": []}
        
        try:
            with open(self.capabilities_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            issues["errors"].append(f"Failed to load capabilities.json: {e}")
            return issues
        
        capabilities = data.get("capabilities", [])
        
        for cap in capabilities:
            name = cap.get("name")
            if not name:
                issues["errors"].append(f"Capability missing 'name': {cap}")
                continue
            
            # Get detection rule (may be None/missing)
            detection_config = cap.get("music21_detection")
            
            # Validate the rule
            rule = validate_detection_rule(name, detection_config)
            self.rules[name] = rule
            
            # Track by domain
            domain = cap.get("domain", "unknown")
            if domain not in self.capabilities_by_domain:
                self.capabilities_by_domain[domain] = []
            self.capabilities_by_domain[domain].append(name)
            
            # Log validation issues
            if not rule.is_valid:
                for error in rule.validation_errors:
                    msg = f"Capability '{name}': {error}"
                    issues["warnings"].append(msg)
                    logger.warning(msg)
        
        self._loaded = True
        
        # Summary
        total = len(self.rules)
        detectable = sum(1 for r in self.rules.values() if r.detection_type is not None)
        invalid = sum(1 for r in self.rules.values() if not r.is_valid)
        
        logger.info(f"Loaded {total} capabilities: {detectable} detectable, {total - detectable} not auto-detectable, {invalid} invalid rules")
        
        return issues
    
    def get_rule(self, capability_name: str) -> Optional[DetectionRule]:
        """Get detection rule for a capability."""
        return self.rules.get(capability_name)
    
    def get_detectable_capabilities(self) -> List[str]:
        """Get list of capabilities that have valid detection rules."""
        return [
            name for name, rule in self.rules.items()
            if rule.detection_type is not None and rule.is_valid
        ]
    
    def get_capabilities_by_type(self, detection_type: DetectionType) -> List[str]:
        """Get capabilities using a specific detection type."""
        return [
            name for name, rule in self.rules.items()
            if rule.detection_type == detection_type and rule.is_valid
        ]


# =============================================================================
# DETECTION ENGINE
# =============================================================================

class DetectionEngine:
    """
    Engine for detecting capabilities in MusicXML extraction results.
    """
    
    def __init__(self, registry: CapabilityRegistry):
        """
        Initialize with a capability registry.
        
        Args:
            registry: CapabilityRegistry with loaded detection rules
        """
        self.registry = registry
    
    def detect_capabilities(
        self,
        extraction_result,  # ExtractionResult from musicxml_analyzer
        score=None,  # Optional music21 score for custom detectors
    ) -> Set[str]:
        """
        Detect all capabilities present in the extraction result.
        
        Args:
            extraction_result: ExtractionResult from MusicXMLAnalyzer
            score: Optional music21 Score for custom detection functions
            
        Returns:
            Set of detected capability names
        """
        detected = set()
        
        for name, rule in self.registry.rules.items():
            if not rule.is_valid or rule.detection_type is None:
                continue
            
            try:
                if self._check_rule(rule, extraction_result, score):
                    detected.add(name)
            except Exception as e:
                logger.warning(f"Error checking rule for '{name}': {e}")
        
        return detected
    
    def _check_rule(
        self,
        rule: DetectionRule,
        result,  # ExtractionResult
        score,
    ) -> bool:
        """Check if a single detection rule matches."""
        
        if rule.detection_type == DetectionType.ELEMENT:
            return self._check_element(rule.config, result, score)
        
        elif rule.detection_type == DetectionType.VALUE_MATCH:
            return self._check_value_match(rule.config, result)
        
        elif rule.detection_type == DetectionType.COMPOUND:
            return self._check_compound(rule.config, result)
        
        elif rule.detection_type == DetectionType.INTERVAL:
            return self._check_interval(rule.config, result)
        
        elif rule.detection_type == DetectionType.TEXT_MATCH:
            return self._check_text_match(rule.config, result)
        
        elif rule.detection_type == DetectionType.TIME_SIGNATURE:
            return self._check_time_signature(rule.config, result)
        
        elif rule.detection_type == DetectionType.RANGE:
            return self._check_range(rule.config, result)
        
        elif rule.detection_type == DetectionType.CUSTOM:
            return self._check_custom(rule.config, result, score)
        
        return False
    
    def _check_element(self, config: Dict, result, score=None) -> bool:
        """Check for music21 element class presence."""
        class_name = config.get("class", "")
        
        # Map class names to ExtractionResult fields
        # e.g., "music21.clef.TrebleClef" -> check if "clef_treble" in result.clefs
        
        # Clefs
        clef_map = {
            "music21.clef.TrebleClef": "clef_treble",
            "music21.clef.BassClef": "clef_bass",
            "music21.clef.AltoClef": "clef_alto",
            "music21.clef.TenorClef": "clef_tenor",
            "music21.clef.Treble8vbClef": "clef_treble_8vb",
            "music21.clef.Bass8vaClef": "clef_bass_8va",
        }
        if class_name in clef_map:
            return clef_map[class_name] in result.clefs
        
        # Articulations
        articulation_map = {
            "music21.articulations.Staccato": "articulation_staccato",
            "music21.articulations.Staccatissimo": "articulation_staccatissimo",
            "music21.articulations.Accent": "articulation_accent",
            "music21.articulations.StrongAccent": "articulation_marcato",
            "music21.articulations.Tenuto": "articulation_tenuto",
            "music21.articulations.DetachedLegato": "articulation_portato",
            "music21.articulations.BreathMark": "notation_breath_mark",
        }
        if class_name in articulation_map:
            mapped = articulation_map[class_name]
            if mapped in result.articulations:
                return True
            # Also check for breath marks specifically
            if mapped == "notation_breath_mark" and result.breath_marks > 0:
                return True
            return False
        
        # Ornaments
        ornament_map = {
            "music21.expressions.Trill": "ornament_trill",
            "music21.expressions.Mordent": "ornament_mordent",
            "music21.expressions.InvertedMordent": "ornament_inverted_mordent",
            "music21.expressions.Turn": "ornament_turn",
            "music21.expressions.InvertedTurn": "ornament_inverted_turn",
            "music21.expressions.Tremolo": "ornament_tremolo",
        }
        if class_name in ornament_map:
            return ornament_map[class_name] in result.ornaments
        
        # Other symbols
        if class_name == "music21.expressions.Fermata":
            return result.fermatas > 0
        
        # Spanners and dynamics that require score access
        if score is not None:
            try:
                # Slurs for legato
                if class_name == "music21.spanner.Slur":
                    from music21 import spanner
                    for sp in score.recurse().getElementsByClass(spanner.Slur):
                        return True
                    return False
                
                # Glissando
                if class_name == "music21.spanner.Glissando":
                    from music21 import spanner
                    for sp in score.recurse().getElementsByClass(spanner.Glissando):
                        return True
                    return False
                
                # Crescendo / Decrescendo / Diminuendo
                if class_name == "music21.dynamics.Crescendo":
                    from music21 import dynamics
                    for d in score.recurse().getElementsByClass(dynamics.Crescendo):
                        return True
                    # Also check for wedges/hairpins
                    from music21 import spanner
                    for sp in score.recurse().getElementsByClass(spanner.Spanner):
                        if hasattr(sp, 'type') and sp.type == 'crescendo':
                            return True
                    return "crescendo" in str(result.dynamic_changes).lower()
                
                if class_name == "music21.dynamics.Decrescendo":
                    from music21 import dynamics
                    for d in score.recurse().getElementsByClass(dynamics.Decrescendo):
                        return True
                    from music21 import spanner
                    for sp in score.recurse().getElementsByClass(spanner.Spanner):
                        if hasattr(sp, 'type') and sp.type == 'decrescendo':
                            return True
                    return "decrescendo" in str(result.dynamic_changes).lower()
                
                if class_name == "music21.dynamics.Diminuendo":
                    from music21 import dynamics
                    for d in score.recurse().getElementsByClass(dynamics.Diminuendo):
                        return True
                    return "diminuendo" in str(result.dynamic_changes).lower()
                    
            except Exception as e:
                logger.debug(f"Error checking element {class_name}: {e}")
        
        logger.debug(f"Unknown element class: {class_name}")
        return False
    
    def _check_value_match(self, config: Dict, result) -> bool:
        """Check for field value match on source objects."""
        source = config.get("source")
        field_path = config.get("field", "")
        
        # Get the source data from ExtractionResult
        source_data = self._get_source_data(source, result)
        if not source_data:
            return False
        
        # Check each item
        for item in source_data:
            if self._check_value_condition(item, field_path, config):
                return True
        
        return False
    
    def _check_compound(self, config: Dict, result) -> bool:
        """Check multiple conditions (AND logic)."""
        source = config.get("source")
        conditions = config.get("conditions", [])
        
        source_data = self._get_source_data(source, result)
        if not source_data:
            return False
        
        # An item must satisfy ALL conditions
        for item in source_data:
            all_match = True
            for cond in conditions:
                field_path = cond.get("field", "")
                if not self._check_value_condition(item, field_path, cond):
                    all_match = False
                    break
            if all_match:
                return True
        
        return False
    
    def _check_interval(self, config: Dict, result) -> bool:
        """Check for interval quality/direction."""
        quality = config.get("quality")  # e.g., "M3", "P5"
        melodic = config.get("melodic", True)
        direction = config.get("direction")  # "ascending", "descending", or None (any)
        
        intervals = result.melodic_intervals if melodic else result.harmonic_intervals
        
        for key, info in intervals.items():
            if info.name == quality:
                if direction is None or info.direction == direction:
                    return True
        
        return False
    
    def _check_text_match(self, config: Dict, result) -> bool:
        """Check for text content in expressions/tempos."""
        source = config.get("source")
        contains = config.get("contains", "").lower()
        equals = config.get("equals", "").lower()
        
        # Get text items based on source
        if source in ("tempos", "tempo_markings"):
            texts = result.tempo_markings
        elif source in ("expressions", "expression_terms"):
            texts = result.expression_terms
        elif source == "dynamics":
            texts = result.dynamics
        else:
            return False
        
        # For expression_terms, items are stored as capability names like "expression_con_brio"
        # So we also need to check the underscore-converted form
        contains_underscore = contains.replace(" ", "_")
        equals_underscore = equals.replace(" ", "_")
        
        for text in texts:
            text_lower = text.lower()
            if equals and text_lower == equals:
                return True
            if contains and contains in text_lower:
                return True
            # Also check with underscore conversion for capability-style names
            if equals_underscore and equals_underscore in text_lower:
                return True
            if contains_underscore and contains_underscore in text_lower:
                return True
        
        return False
    
    def _check_time_signature(self, config: Dict, result) -> bool:
        """Check for time signature match."""
        numerator = config.get("numerator")
        denominator = config.get("denominator")
        
        expected = f"time_sig_{numerator}_{denominator}"
        return expected in result.time_signatures
    
    def _check_range(self, config: Dict, result) -> bool:
        """Check for interval size range."""
        min_semi = config.get("min_semitones", 0)
        max_semi = config.get("max_semitones", 999)
        
        if not result.range_analysis:
            return False
        
        range_semi = result.range_analysis.range_semitones
        return min_semi <= range_semi <= max_semi
    
    def _check_custom(self, config: Dict, result, score) -> bool:
        """Execute custom detection function."""
        func_name = config.get("function")
        if func_name not in CUSTOM_DETECTORS:
            return False
        
        return CUSTOM_DETECTORS[func_name](result, score)
    
    def _get_source_data(self, source: str, result) -> List[Any]:
        """Get source data from ExtractionResult as a list of items."""
        # For value_match/compound, we need to return pseudo-items
        # that can have their fields checked
        
        # Map internal note type names to match detection rule conventions
        # Note: music21 uses "16th" but rules might use "sixteenth"
        # We normalize to match what the detection rules expect
        NOTE_TYPE_MAP = {
            "thirty_second": "32nd",
            "sixty_fourth": "64th",
            "16th": "sixteenth",  # music21 uses "16th", rules use "sixteenth"
        }
        
        if source == "notes":
            # Return note value info as pseudo-objects
            items = []
            for note_type, count in result.note_values.items():
                clean_type = note_type.replace("note_", "")
                # Normalize to match detection rule naming convention
                normalized = NOTE_TYPE_MAP.get(clean_type, clean_type)
                items.append({"type": normalized, "count": count, "dots": 0})
            # Add dotted notes - provide BOTH formats to support different rule styles:
            # 1. Rules using type: "dotted_half" (basic dotted rhythm detection)
            # 2. Rules using type: "half" + dots >= 1 (compound conditions)
            for dotted in result.dotted_notes:
                # Add full name format (e.g., "dotted_half", "double_dotted_half")
                # Normalize 16th -> sixteenth in full name too
                full_name = dotted
                for old, new in [("16th", "sixteenth"), ("32nd", "thirty_second")]:
                    full_name = full_name.replace(old, new)
                items.append({"type": full_name, "dots": 1 if "double" not in dotted else 2})
                
                # Also add parsed format (e.g., type: "half", dots: 1)
                if dotted.startswith("double_dotted_"):
                    base_type = dotted.replace("double_dotted_", "")
                    normalized_base = NOTE_TYPE_MAP.get(base_type, base_type)
                    items.append({"type": normalized_base, "dots": 2})
                elif dotted.startswith("dotted_"):
                    base_type = dotted.replace("dotted_", "")
                    normalized_base = NOTE_TYPE_MAP.get(base_type, base_type)
                    items.append({"type": normalized_base, "dots": 1})
            return items
        
        elif source == "dynamics":
            return [{"value": d.replace("dynamic_", "")} for d in result.dynamics]
        
        elif source == "rests":
            items = []
            for rest_type, count in result.rest_values.items():
                clean_type = rest_type.replace("rest_", "")
                normalized = NOTE_TYPE_MAP.get(clean_type, clean_type)
                items.append({"type": normalized, "count": count})
            return items
        
        elif source == "articulations":
            return [{"name": a.replace("articulation_", "")} for a in result.articulations]
        
        elif source == "ornaments":
            return [{"name": o.replace("ornament_", "")} for o in result.ornaments]
        
        elif source == "clefs":
            return [{"name": c.replace("clef_", "")} for c in result.clefs]
        
        elif source == "time_signatures":
            items = []
            for ts in result.time_signatures:
                # Parse "time_sig_4_4" -> {"numerator": 4, "denominator": 4}
                parts = ts.replace("time_sig_", "").split("_")
                if len(parts) == 2:
                    items.append({"numerator": int(parts[0]), "denominator": int(parts[1])})
            return items
        
        elif source == "key_signatures":
            return [{"name": k} for k in result.key_signatures]
        
        elif source == "intervals":
            items = []
            for key, info in result.melodic_intervals.items():
                items.append({
                    "name": info.name,
                    "direction": info.direction,
                    "semitones": info.semitones,
                    "quality": info.quality,
                    "is_melodic": True,
                })
            for key, info in result.harmonic_intervals.items():
                items.append({
                    "name": info.name,
                    "semitones": info.semitones,
                    "quality": info.quality,
                    "is_melodic": False,
                })
            return items
        
        return []
    
    def _check_value_condition(self, item: Any, field_path: str, config: Dict) -> bool:
        """Check a single value condition against an item."""
        # Get the value from the item using dot-notation field path
        value = self._get_nested_value(item, field_path)
        
        if value is None:
            return False
        
        # Check conditions
        if "eq" in config:
            return value == config["eq"]
        if "contains" in config:
            return config["contains"].lower() in str(value).lower()
        if "gte" in config:
            return value >= config["gte"]
        if "lte" in config:
            return value <= config["lte"]
        
        return False
    
    def _get_nested_value(self, item: Any, field_path: str) -> Any:
        """Get value from item using dot-notation path."""
        if not field_path:
            return item
        
        parts = field_path.split(".")
        current = item
        
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
            
            if current is None:
                return None
        
        return current


# =============================================================================
# GLOBAL REGISTRY INSTANCE
# =============================================================================

_registry: Optional[CapabilityRegistry] = None


def get_registry() -> CapabilityRegistry:
    """Get or create the global capability registry."""
    global _registry
    if _registry is None:
        _registry = CapabilityRegistry()
        issues = _registry.load()
        if issues["errors"]:
            for error in issues["errors"]:
                logger.error(error)
    return _registry


def get_detection_engine() -> DetectionEngine:
    """Get a detection engine with the global registry."""
    return DetectionEngine(get_registry())
