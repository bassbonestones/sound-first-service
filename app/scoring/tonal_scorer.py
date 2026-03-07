"""
Tonal Domain Scorer

Analyzes tonal complexity with facet-aware scoring.
"""

from typing import Dict, Any
from .models import DomainResult, DomainScores
from .utils import normalize_linear, clamp, derive_bands


# PROVISIONAL THRESHOLDS
# NOTE: pitch_class_count is NOT used as a primary facet — it's too naive.
# Tonal facets focus on chromatic departure, accidental burden, and instability.
TONAL_CHROMATIC_RATIO_HIGH = 0.3
TONAL_ACCIDENTAL_HIGH = 0.4


def analyze_tonal_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze tonal complexity with facet-aware scoring.
    
    NOTE: We do NOT use pitch_class_count as a primary facet because
    most tonal pieces use 7 pitch classes, making it meaningless noise.
    
    Profile fields:
        accidental_rate: float - proportion of accidentals
        chromatic_ratio: float - proportion of chromatic notes
        diatonic_predictability_proxy: float - (future) adherence to scale
        modulation_count: int - (future) number of key changes
        key_center_ambiguity: float - (future) tonal center clarity
    
    Facet scores:
        chromatic_complexity: complexity from chromatic departures
        accidental_load: reading burden from accidentals
        tonal_instability: unpredictability / lack of diatonic stability
    
    Domain scores:
        primary: overall tonal reading/hearing complexity
        hazard: instability/chromatic spikes
        overall: blended tonal difficulty
    """
    # Extract profile with defaults
    accidental_rate = profile.get('accidental_rate', 0.0) or 0.0
    chromatic_ratio = profile.get('chromatic_ratio', 0.0) or 0.0
    diatonic_predictability = profile.get('diatonic_predictability_proxy', 1.0)  # Default stable
    modulation_count = profile.get('modulation_count', 0) or 0
    key_center_ambiguity = profile.get('key_center_ambiguity', 0.0) or 0.0  # Future hook
    
    # Calculate facet scores
    # Chromatic: proportion of non-diatonic notes
    chromatic_complexity = normalize_linear(chromatic_ratio, 0, TONAL_CHROMATIC_RATIO_HIGH)
    
    # Accidental load: reading burden from sharps/flats/naturals
    accidental_load = normalize_linear(accidental_rate, 0, TONAL_ACCIDENTAL_HIGH)
    
    # Instability: lack of diatonic predictability + modulations + ambiguity
    tonal_instability = clamp(
        (1.0 - diatonic_predictability) * 0.5 +
        normalize_linear(modulation_count, 0, 4) * 0.3 +
        key_center_ambiguity * 0.2
    )
    
    facet_scores = {
        'chromatic_complexity': round(chromatic_complexity, 4),
        'accidental_load': round(accidental_load, 4),
        'tonal_instability': round(tonal_instability, 4),
    }
    
    # Derive domain scores from facets
    primary = clamp(
        accidental_load * 0.35 +
        chromatic_complexity * 0.35 +
        tonal_instability * 0.30
    )
    
    hazard = clamp(
        chromatic_complexity * 0.5 +
        tonal_instability * 0.5
    )
    
    overall = clamp(primary * 0.6 + hazard * 0.4)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if chromatic_complexity > 0.5:
        flags.append('highly_chromatic')
    if accidental_load > 0.6:
        flags.append('heavy_accidentals')
    if tonal_instability > 0.5:
        flags.append('tonal_instability_warning')
    if modulation_count > 0:
        flags.append(f'modulations_detected_{modulation_count}')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=1.0,
    )
