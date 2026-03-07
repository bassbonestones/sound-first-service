"""
Range Domain Scorer

Analyzes pitch range - PROFILE-ONLY, no difficulty scoring.
Range difficulty is instrument-dependent.
"""

from typing import Dict, Any
from .models import DomainResult, DomainScores
from .utils import normalize_linear


# PROVISIONAL THRESHOLDS
# NOTE: Range is profile-only - scoring requires instrument context.
RANGE_SPAN_NARROW = 7      # P5 or less
RANGE_SPAN_WIDE = 36       # 3 octaves


def analyze_range_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Range domain - PROFILE-ONLY, no difficulty scoring.
    
    Range difficulty is instrument-dependent and cannot be meaningfully
    scored without knowing the target instrument. A 2-octave span is trivial
    for piano but demanding for trumpet.
    
    This domain captures the material's range characteristics for later
    comparison against the user's instrument-specific comfort envelope.
    
    Profile fields (all preserved for instrument-relative comparison):
        lowest_pitch: str - pitch name of lowest note
        highest_pitch: str - pitch name of highest note
        span_semitones: int - total range in semitones
        tessitura_span: int - p10-p90 working range in semitones
    
    Facet scores:
        span_breadth: normalized span (for relative comparison only)
    
    Domain scores:
        All set to None - scoring happens at assignment time with instrument context
    """
    # Extract profile
    span_semitones = profile.get('span_semitones')
    tessitura_span = profile.get('tessitura_span')
    
    # Only compute span_breadth as a relative measure (not a difficulty score)
    span_breadth = None
    if span_semitones is not None:
        span_breadth = normalize_linear(span_semitones, RANGE_SPAN_NARROW, RANGE_SPAN_WIDE)
    
    facet_scores = {
        'span_breadth': round(span_breadth, 4) if span_breadth is not None else None,
    }
    
    # No scoring - requires instrument context
    scores = DomainScores(primary=None, hazard=None, overall=None)
    
    # Generate flags based on raw values
    flags = ['requires_instrument_context']
    if span_semitones and span_semitones > 24:  # > 2 octaves
        flags.append('wide_range')
    if span_semitones and span_semitones > 36:  # > 3 octaves
        flags.append('very_wide_range')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands={'primary_stage': None, 'hazard_stage': None, 'overall_stage': None},
        flags=flags,
        confidence=0.0,  # Cannot score without instrument
    )
