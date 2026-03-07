"""
Throughput (Density) Domain Scorer

Analyzes note density and throughput complexity with facet-aware scoring.
"""

from typing import Dict, Any
from .models import DomainResult, DomainScores
from .utils import normalize_linear, clamp, derive_bands


# PROVISIONAL THRESHOLDS
THROUGHPUT_NPS_LOW = 1.0
THROUGHPUT_NPS_SUSTAINED_HIGH = 6.0
THROUGHPUT_NPS_PEAK_HIGH = 12.0
THROUGHPUT_VOLATILITY_HIGH = 0.5


def analyze_throughput_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze throughput (density) complexity with facet-aware scoring.
    
    Profile fields:
        notes_per_second: float - average note rate
        peak_notes_per_second: float - maximum note rate in any window
        notes_per_measure: float - average notes per measure
        throughput_volatility: float - variation in local notes-per-second across windows
    
    Facet scores:
        sustained_density: typical note rate demand
        peak_density: maximum burst demand
        adaptation_pressure: cognitive load from changing density
            (how much the player must adapt to varying throughput)
    
    Domain scores:
        primary: sustained throughput demand
        hazard: local throughput spikes
        overall: blended throughput difficulty
    """
    # Extract profile with defaults
    nps = profile.get('notes_per_second', 2.0) or 2.0
    peak_nps = profile.get('peak_notes_per_second') or nps
    notes_per_measure = profile.get('notes_per_measure', 8.0)
    volatility = profile.get('throughput_volatility', 0.0) or 0.0
    
    # Calculate facet scores
    sustained_density = normalize_linear(nps, THROUGHPUT_NPS_LOW, THROUGHPUT_NPS_SUSTAINED_HIGH)
    
    peak_density = normalize_linear(peak_nps, THROUGHPUT_NPS_LOW, THROUGHPUT_NPS_PEAK_HIGH)
    
    # Adaptation pressure: how much density varies across the piece
    adaptation_pressure = normalize_linear(volatility, 0, THROUGHPUT_VOLATILITY_HIGH)
    
    facet_scores = {
        'sustained_density': round(sustained_density, 4),
        'peak_density': round(peak_density, 4),
        'adaptation_pressure': round(adaptation_pressure, 4),
    }
    
    # Derive domain scores from facets
    primary = clamp(
        sustained_density * 0.8 +
        adaptation_pressure * 0.2
    )
    
    hazard = clamp(
        peak_density * 0.7 +
        adaptation_pressure * 0.3
    )
    
    overall = clamp(primary * 0.7 + hazard * 0.3)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if sustained_density > 0.6:
        flags.append('high_sustained_density')
    if peak_density > 0.7:
        flags.append('dense_passages')
    if peak_density > sustained_density + 0.3:
        flags.append('throughput_burst_warning')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=1.0 if profile.get('notes_per_second') is not None else 0.7,
    )
