from __future__ import annotations

"""
Notation Parser

Extraction of notation elements: clefs, time/key signatures, dynamics,
articulations, ornaments, tempo/expression, and repeat structures.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music21 import stream
    from .extraction_models import ExtractionResult

from app.tempo_analyzer import build_tempo_profile, get_legacy_tempo_bpm
from .capability_maps import (
    CLEF_CAPABILITY_MAP, DYNAMIC_CAPABILITY_MAP, 
    ARTICULATION_CAPABILITY_MAP, ORNAMENT_CAPABILITY_MAP,
    TEMPO_TERMS, EXPRESSION_TERMS, TEXT_TO_ARTICULATION_MAP,
)


def extract_metadata(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract title, composer, etc."""
    if score.metadata:
        result.title = score.metadata.title
        result.composer = score.metadata.composer


def extract_clefs(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract all clefs used in the score."""
    from music21 import clef
    
    for c in score.recurse().getElementsByClass(clef.Clef):
        clef_type = type(c).__name__
        if clef_type in CLEF_CAPABILITY_MAP:
            result.clefs.add(CLEF_CAPABILITY_MAP[clef_type])
        else:
            # Generic clef handling
            if hasattr(c, 'sign') and c.sign:
                result.clefs.add(f"clef_{c.sign.lower()}")


def extract_time_signatures(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract all time signatures."""
    from music21 import meter
    
    for ts in score.recurse().getElementsByClass(meter.TimeSignature):  # type: ignore[attr-defined]
        ts_str = f"{ts.numerator}_{ts.denominator}"
        result.time_signatures.add(f"time_sig_{ts_str}")


def extract_key_signatures(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract all key signatures."""
    from music21 import key
    
    for ks in score.recurse().getElementsByClass(key.KeySignature):
        # Get the key name
        if hasattr(ks, 'asKey'):
            k = ks.asKey()
            mode = 'major' if k.mode == 'major' else 'minor'
            tonic = k.tonic.name.replace('#', '_sharp').replace('-', '_flat')
            result.key_signatures.add(f"key_{tonic}_{mode}")
        else:
            # Just sharps/flats count
            sharps = ks.sharps
            result.key_signatures.add(f"key_sig_{sharps}_sharps" if sharps >= 0 else f"key_sig_{abs(sharps)}_flats")


def extract_dynamics(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract dynamics and dynamic changes."""
    from music21 import dynamics, expressions
    
    for d in score.recurse().getElementsByClass(dynamics.Dynamic):
        dyn_val = d.value
        if dyn_val in DYNAMIC_CAPABILITY_MAP:
            result.dynamics.add(DYNAMIC_CAPABILITY_MAP[dyn_val])
        else:
            result.dynamics.add(f"dynamic_{dyn_val}")
    
    # Dynamic wedges (crescendo/diminuendo)
    for s in score.recurse().getElementsByClass(dynamics.DynamicWedge):
        if isinstance(s, dynamics.Crescendo):
            result.dynamic_changes.add('dynamic_change_crescendo')
        elif isinstance(s, dynamics.Diminuendo):
            result.dynamic_changes.add('dynamic_change_diminuendo')
    
    # Also check for text-based cresc/dim
    for tw in score.recurse().getElementsByClass(expressions.TextExpression):
        text = tw.content.lower() if tw.content else ''
        if 'cresc' in text:
            result.dynamic_changes.add('dynamic_change_crescendo')
        if 'dim' in text or 'decresc' in text:
            result.dynamic_changes.add('dynamic_change_diminuendo')
        if 'subito' in text:
            result.dynamic_changes.add('dynamic_change_subito')


def extract_articulations(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract articulations."""
    for n in score.recurse().notes:
        for art in n.articulations:
            art_type = type(art).__name__
            if art_type in ARTICULATION_CAPABILITY_MAP:
                result.articulations.add(ARTICULATION_CAPABILITY_MAP[art_type])
            else:
                result.articulations.add(f"articulation_{art_type.lower()}")


def extract_ornaments(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract ornaments."""
    from music21 import expressions
    
    for n in score.recurse().notes:
        for expr in n.expressions:
            expr_type = type(expr).__name__
            
            if expr_type in ORNAMENT_CAPABILITY_MAP:
                result.ornaments.add(ORNAMENT_CAPABILITY_MAP[expr_type])
            elif isinstance(expr, expressions.Fermata):
                result.fermatas += 1
            elif 'Grace' in expr_type:
                result.ornaments.add('ornament_grace_note')
            elif 'Appoggiatura' in expr_type:
                result.ornaments.add('ornament_appoggiatura')


def extract_tempo_expression(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract tempo markings, expression terms, and build tempo profile."""
    from music21 import tempo, expressions
    
    # Build comprehensive tempo profile using tempo_analyzer
    result.tempo_profile = build_tempo_profile(score)
    
    # Set legacy tempo_bpm from effective_bpm (was: last tempo found)
    # LEGACY COMPATIBILITY: This field is deprecated, use tempo_profile instead
    result.tempo_bpm = get_legacy_tempo_bpm(result.tempo_profile)
    
    # Still populate tempo_markings for capability detection
    # This ensures backward compatibility with detection rules
    for t in score.recurse().getElementsByClass(tempo.MetronomeMark):
        if t.text:
            text_lower = t.text.lower()
            for term in TEMPO_TERMS:
                if term in text_lower:
                    result.tempo_markings.add(f"tempo_{term.replace(' ', '_')}")
    
    for tt in score.recurse().getElementsByClass(tempo.TempoText):
        if tt.text:
            text_lower = tt.text.lower()
            for term in TEMPO_TERMS:
                if term in text_lower:
                    result.tempo_markings.add(f"tempo_{term.replace(' ', '_')}")
    
    # Expression text (including tempo terms since they can appear as TextExpression)
    for te in score.recurse().getElementsByClass(expressions.TextExpression):
        if te.content:
            text_lower = te.content.lower()
            # Check for tempo terms in TextExpression too
            for term in TEMPO_TERMS:
                if term in text_lower:
                    result.tempo_markings.add(f"tempo_{term.replace(' ', '_')}")
            # Check for expression terms
            for term in EXPRESSION_TERMS:
                if term in text_lower:
                    result.expression_terms.add(f"expression_{term.replace(' ', '_')}")
            # Check for articulation text directions (e.g., "legato", "staccato")
            for term, articulation_cap in TEXT_TO_ARTICULATION_MAP.items():
                if term in text_lower:
                    result.articulations.add(articulation_cap)


def extract_repeats(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract repeat structures."""
    from music21 import repeat, expressions, spanner
    
    # Repeat signs
    for r in score.recurse().getElementsByClass(repeat.RepeatMark):  # type: ignore[type-var]
        result.repeat_structures.add('repeat_sign')
    
    # Barlines with repeats
    for b in score.recurse().getElementsByClass('Barline'):
        if hasattr(b, 'type'):
            if 'repeat' in str(b.type).lower():
                result.repeat_structures.add('repeat_sign')
    
    # Da Capo, Dal Segno, Coda, etc.
    for te in score.recurse().getElementsByClass(expressions.TextExpression):
        if te.content:
            text = te.content.lower()
            if 'd.c.' in text or 'da capo' in text:
                result.repeat_structures.add('repeat_dc')
            if 'd.s.' in text or 'dal segno' in text:
                result.repeat_structures.add('repeat_ds')
            if 'coda' in text:
                result.repeat_structures.add('repeat_coda')
            if 'segno' in text:
                result.repeat_structures.add('repeat_segno')
            if 'fine' in text:
                result.repeat_structures.add('repeat_fine')
    
    # First/second endings
    for s in score.recurse().getElementsByClass(spanner.RepeatBracket):
        result.repeat_structures.add('repeat_first_ending')
        result.repeat_structures.add('repeat_second_ending')


def extract_other_notation(score: "stream.Score", result: "ExtractionResult") -> None:
    """Extract fermatas, breath marks, chord symbols, etc."""
    from music21 import expressions
    
    # Breath marks
    for te in score.recurse().getElementsByClass(expressions.TextExpression):
        if te.content and 'breath' in te.content.lower():
            result.breath_marks += 1
    
    # Also check for BreathMark class
    for n in score.recurse().notes:
        for expr in n.expressions:
            if type(expr).__name__ == 'BreathMark':
                result.breath_marks += 1
    
    # Chord symbols (jazz)
    for cs in score.recurse().getElementsByClass('ChordSymbol'):
        if hasattr(cs, 'figure'):
            result.chord_symbols.add(str(cs.figure))
    
    # Figured bass
    for fb in score.recurse().getElementsByClass('FiguredBass'):
        result.figured_bass = True
