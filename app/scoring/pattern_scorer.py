"""
Pattern / Predictability Domain Scorer

Analyzes melodic and rhythmic pattern predictability with facet-aware scoring.
NOTE: This domain is INVERTED - high predictability = easier.
"""

from typing import Dict, Any
from .models import DomainResult, DomainScores
from .utils import normalize_linear, clamp, derive_bands


# PROVISIONAL: Pattern domain thresholds
# NOTE: This domain is INVERTED - high predictability = easier
PATTERN_UNIQUENESS_LOW = 0.2    # 20% unique = very repetitive = easy
PATTERN_UNIQUENESS_HIGH = 0.9   # 90% unique = unpredictable = hard
PATTERN_SEQUENCE_COVERAGE_LOW = 0.0
PATTERN_SEQUENCE_COVERAGE_HIGH = 0.5   # 50% coverage = very predictable


def analyze_pattern_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze pattern/predictability complexity with facet-aware scoring.
    
    NOTE: This domain is INVERTED - high predictability (repetition) = easier.
    The "primary" score represents DIFFICULTY, so:
    - High uniqueness = high difficulty score
    - High repetition = low difficulty score
    
    Profile fields:
        total_melodic_motifs: int - count of detected interval patterns
        unique_melodic_motifs: int - count of distinct patterns
        melodic_motif_uniqueness_ratio: float - unique/total
        melodic_motif_repetition_ratio: float - 1 - uniqueness_ratio
        sequence_count: int - number of repeated phrases
        sequence_coverage_ratio: float - fraction of notes in repeated sequences
        rhythm_uniqueness_ratio: float - from rhythm pattern analysis
        rhythm_repetition_ratio: float - 1 - rhythm_uniqueness_ratio
    
    Facet scores:
        melodic_predictability: inverse of melodic uniqueness (0=random, 1=highly repetitive)
        rhythmic_predictability: inverse of rhythm uniqueness
        structural_regularity: based on sequence repetition
    
    Domain scores (DIFFICULTY oriented):
        primary: cognitive load from unpredictability
        hazard: irregularity spikes that break expectations
        overall: blended unpredictability difficulty
    """
    # Extract melodic pattern metrics
    melodic_uniqueness = profile.get('melodic_motif_uniqueness_ratio', 0.5) or 0.5
    melodic_repetition = profile.get('melodic_motif_repetition_ratio', 0.5) or 0.5
    sequence_coverage = profile.get('sequence_coverage_ratio', 0.0) or 0.0
    
    # Extract rhythmic pattern metrics
    rhythm_uniqueness = profile.get('rhythm_uniqueness_ratio', 0.5) or 0.5
    rhythm_repetition = profile.get('rhythm_repetition_ratio', 0.5) or 0.5
    
    # Calculate facet scores (PREDICTABILITY - higher = more predictable = easier)
    # These are "ease" scores, not difficulty scores
    melodic_predictability = melodic_repetition  # Direct: more repetition = more predictable
    rhythmic_predictability = rhythm_repetition
    structural_regularity = normalize_linear(
        sequence_coverage, 
        PATTERN_SEQUENCE_COVERAGE_LOW, 
        PATTERN_SEQUENCE_COVERAGE_HIGH
    )
    
    facet_scores = {
        'melodic_predictability': round(melodic_predictability, 4),
        'rhythmic_predictability': round(rhythmic_predictability, 4),
        'structural_regularity': round(structural_regularity, 4),
    }
    
    # Convert predictability (ease) to DIFFICULTY for domain scores
    # Invert: high predictability = low difficulty
    melodic_difficulty = 1.0 - melodic_predictability
    rhythmic_difficulty = 1.0 - rhythmic_predictability
    structural_difficulty = 1.0 - structural_regularity
    
    # Primary: sustained cognitive load from unpredictability
    primary = clamp(
        melodic_difficulty * 0.5 +
        rhythmic_difficulty * 0.3 +
        structural_difficulty * 0.2
    )
    
    # Hazard: unpredictability that might cause errors
    # High uniqueness in any facet is a hazard
    hazard = clamp(
        max(melodic_difficulty, rhythmic_difficulty) * 0.7 +
        structural_difficulty * 0.3
    )
    
    overall = clamp(primary * 0.7 + hazard * 0.3)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if melodic_uniqueness > 0.8:
        flags.append('high_melodic_variety')
    if melodic_repetition > 0.8:
        flags.append('highly_repetitive_melody')
    if rhythm_uniqueness > 0.8:
        flags.append('high_rhythmic_variety')
    if sequence_coverage > 0.4:
        flags.append('strong_sequence_patterns')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=1.0 if profile.get('melodic_motif_uniqueness_ratio') is not None else 0.7,
    )
