"""
Rhythm Domain Scorer

Analyzes rhythm complexity with facet-aware scoring.
"""

from typing import Dict, Any
from .models import DomainResult, DomainScores
from .utils import normalize_linear, clamp, derive_bands


# PROVISIONAL THRESHOLDS
RHYTHM_SUBDIVISION_FASTEST_QL_HIGH = 0.125  # 32nd note
RHYTHM_SUBDIVISION_FASTEST_QL_LOW = 1.0     # Quarter note
RHYTHM_SYNCOPATION_HIGH = 0.4
RHYTHM_TUPLET_HIGH = 0.2
RHYTHM_DOT_TIE_HIGH = 0.3
RHYTHM_UNIQUENESS_LOW = 0.1
RHYTHM_UNIQUENESS_HIGH = 0.8


def analyze_rhythm_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze rhythm complexity with facet-aware scoring.
    
    Profile fields:
        shortest_duration: float - shortest note duration (quarterLength)
        note_value_diversity: float - variety of note values
        tuplet_ratio: float - proportion in tuplets
        dot_ratio: float - proportion dotted
        tie_ratio: float - proportion tied
        syncopation_ratio: float - proportion syncopated
        rhythm_measure_uniqueness_ratio: float - unique patterns / total measures
        rhythm_measure_repetition_ratio: float - 1 - uniqueness
        subdivision_entropy: float - (future) variety of subdivisions
        pattern_irregularity: float - (future) uneven distribution
    
    Facet scores:
        subdivision_complexity: how fine the subdivisions get
        syncopation_complexity: off-beat complexity
        tuplet_complexity: tuplet handling demand
        dot_tie_complexity: tied/dotted note handling
        pattern_novelty: how many unique patterns to track
    
    Domain scores:
        primary: main rhythmic demand
        hazard: bursty/local rhythmic spikes
        overall: blended rhythmic difficulty
    """
    # Extract profile with defaults
    shortest_ql = profile.get('shortest_duration', 1.0)
    if shortest_ql is None or shortest_ql <= 0:
        shortest_ql = 1.0
    note_value_diversity = profile.get('note_value_diversity', 0.3)
    tuplet_ratio = profile.get('tuplet_ratio', 0.0)
    dot_ratio = profile.get('dot_ratio', 0.0)
    tie_ratio = profile.get('tie_ratio', 0.0)
    syncopation_ratio = profile.get('syncopation_ratio', 0.0)
    uniqueness_ratio = profile.get('rhythm_measure_uniqueness_ratio', 0.5)
    repetition_ratio = profile.get('rhythm_measure_repetition_ratio', 0.5)
    subdivision_entropy = profile.get('subdivision_entropy', None)  # Future
    pattern_irregularity = profile.get('pattern_irregularity', None)  # Future
    
    # Calculate facet scores
    # Subdivision: shorter notes = harder (reciprocal scale)
    fastest_normalized = 1.0 / max(shortest_ql, 0.0625)  # Cap at 64th notes
    subdivision_complexity = normalize_linear(fastest_normalized, 1, 16)  # 1 = quarter, 16 = 64th
    
    syncopation_complexity = normalize_linear(syncopation_ratio, 0, RHYTHM_SYNCOPATION_HIGH)
    
    tuplet_complexity = normalize_linear(tuplet_ratio, 0, RHYTHM_TUPLET_HIGH)
    
    dot_tie_complexity = normalize_linear(dot_ratio + tie_ratio, 0, RHYTHM_DOT_TIE_HIGH)
    
    pattern_novelty = normalize_linear(uniqueness_ratio, RHYTHM_UNIQUENESS_LOW, RHYTHM_UNIQUENESS_HIGH)
    
    facet_scores = {
        'subdivision_complexity': round(subdivision_complexity, 4),
        'syncopation_complexity': round(syncopation_complexity, 4),
        'tuplet_complexity': round(tuplet_complexity, 4),
        'dot_tie_complexity': round(dot_tie_complexity, 4),
        'pattern_novelty': round(pattern_novelty, 4),
    }
    
    # Derive domain scores from facets
    primary = clamp(
        subdivision_complexity * 0.25 +
        syncopation_complexity * 0.20 +
        tuplet_complexity * 0.15 +
        dot_tie_complexity * 0.10 +
        pattern_novelty * 0.30
    )
    
    # Hazard: irregular bursts, high novelty combined with fast subdivisions
    hazard_base = pattern_novelty * 0.5 + syncopation_complexity * 0.3
    if subdivision_complexity > 0.6 and pattern_novelty > 0.5:
        hazard_base = clamp(hazard_base + 0.15)  # Boost for fast + novel
    
    hazard = clamp(hazard_base + tuplet_complexity * 0.2)
    
    overall = clamp(primary * 0.7 + hazard * 0.3)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if tuplet_complexity > 0.5:
        flags.append('complex_tuplets')
    if syncopation_complexity > 0.6:
        flags.append('heavy_syncopation')
    if pattern_novelty > 0.7:
        flags.append('highly_unpredictable_rhythm')
    if subdivision_complexity > 0.7 and hazard > 0.5:
        flags.append('fast_irregular_bursts')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=1.0,
    )
