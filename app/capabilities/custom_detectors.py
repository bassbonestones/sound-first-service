"""
Custom detection functions for capability detection.

These functions are registered with the @register_custom_detector decorator
and can be referenced in capabilities.json via the "custom" detection type.
"""

import logging
from typing import Callable, Dict

logger = logging.getLogger(__name__)


# Registry for custom detection functions
# Each function takes (extraction_result, score) and returns bool
CUSTOM_DETECTORS: Dict[str, Callable] = {}


def register_custom_detector(name: str):
    """Decorator to register a custom detection function."""
    def decorator(func: Callable):
        CUSTOM_DETECTORS[name] = func
        return func
    return decorator


# =============================================================================
# RHYTHM PATTERN DETECTORS
# =============================================================================

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
    # Try multiple approaches for figured bass detection
    try:
        from music21 import figuredBass
        for fb in score.recurse().getElementsByClass(figuredBass.notation.Notation):
            return True
    except:
        pass
    # Also check for FiguredBassIndication from music21.figuredBass.realizer
    try:
        for fb in score.recurse().getElementsByClass('FiguredBass'):
            return True
    except:
        pass
    # Check for standalone figured bass elements (music21 FiguredBassLine)
    try:
        from music21.figuredBass import notation as figuredBassNotation
        for elem in score.recurse():
            if 'FiguredBass' in type(elem).__name__:
                return True
    except:
        pass
    # music21 may not fully parse figured-bass XML, so check the raw source
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
    except:
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
    # Check note articulations
    for n in score.recurse().notes:
        for art in n.articulations:
            if isinstance(art, articulations.BreathMark):
                return True
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
    """Detect chromatic approach tones (chromatic note approaching diatonic target by half-step)."""
    if score is None:
        return False
    
    from music21 import note as m21note, key as m21key
    
    # Get all notes
    notes = list(score.recurse().getElementsByClass(m21note.Note))
    if len(notes) < 2:
        return False
    
    # Determine the key
    key_obj = None
    for elem in score.recurse():
        if isinstance(elem, m21key.Key) or isinstance(elem, m21key.KeySignature):
            if isinstance(elem, m21key.KeySignature):
                key_obj = elem.asKey()
            else:
                key_obj = elem
            break
    
    if key_obj is None:
        # Try to analyze
        try:
            key_obj = score.analyze('key')
        except:
            return False
    
    if key_obj is None:
        return False
    
    # Get scale pitches (pitch classes 0-11)
    try:
        scale = key_obj.getScale()
        scale_pitch_classes = set(p.pitchClass for p in scale.getPitches())
    except:
        return False
    
    # Look for chromatic approach: chromatic note -> diatonic note by half-step
    for i in range(len(notes) - 1):
        interval = abs(notes[i+1].pitch.midi - notes[i].pitch.midi)
        if interval == 1:  # Semitone
            first_pc = notes[i].pitch.pitchClass
            second_pc = notes[i+1].pitch.pitchClass
            
            # Chromatic approach: first note is NOT in scale, second note IS in scale
            if first_pc not in scale_pitch_classes and second_pc in scale_pitch_classes:
                return True
    
    return False


@register_custom_detector("detect_modulation")
def detect_modulation(extraction_result, score) -> bool:
    """Detect key change / modulation."""
    # Simple heuristic: multiple key signatures detected
    return len(extraction_result.key_signatures) > 1
