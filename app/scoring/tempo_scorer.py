"""
Tempo Domain Scorer

Analyzes tempo complexity with facet-aware scoring.
"""

from typing import Dict, Any
from .models import DomainResult, DomainScores
from .utils import normalize_linear, clamp, derive_bands


# PROVISIONAL THRESHOLDS
TEMPO_SPEED_BPM_LOW = 60
TEMPO_SPEED_BPM_HIGH = 180
TEMPO_CONTROL_CHANGES_LOW = 0
TEMPO_CONTROL_CHANGES_HIGH = 6
TEMPO_VARIABILITY_VOLATILITY_HIGH = 0.5


def analyze_tempo_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze tempo complexity with facet-aware scoring.
    
    If no explicit tempo marking exists in the score, returns null scores
    with low confidence. We do not assume defaults.
    
    Profile fields:
        base_bpm: int|None - marked/initial BPM (None if not specified)
        effective_bpm: int|None - weighted average BPM
        tempo_is_explicit: bool - whether tempo was explicitly marked
        min_bpm: int - minimum BPM
        max_bpm: int - maximum BPM
        tempo_change_count: int - number of tempo changes
        tempo_volatility: float - magnitude × frequency of changes
        has_accelerando: bool - accelerando present
        has_ritardando: bool - ritardando present
        has_rubato: bool - rubato/flexible tempo indicated
        has_sudden_change: bool - sudden tempo change (subito)
        tempo_regions: int - distinct tempo sections
    
    Facet scores:
        speed_demand: how fast the sustained tempo is
        tempo_control_demand: precision needed for tempo changes
        tempo_variability: how much the tempo fluctuates
    
    Domain scores:
        primary: sustained tempo demand
        hazard: control volatility / abrupt change risk
        overall: blended tempo difficulty
    """
    tempo_is_explicit = profile.get('tempo_is_explicit', False)
    
    # If no explicit tempo, return empty scores with low confidence
    if not tempo_is_explicit:
        return DomainResult(
            profile=profile,
            facet_scores={
                'speed_demand': None,
                'tempo_control_demand': None,
                'tempo_variability': None,
            },
            scores=DomainScores(primary=None, hazard=None, overall=None),
            bands={'primary_stage': None, 'hazard_stage': None, 'overall_stage': None},
            flags=['no_tempo_marking'],
            confidence=0.0,
        )
    
    # Extract profile with defaults
    base_bpm = profile.get('base_bpm') or 120
    effective_bpm = profile.get('effective_bpm') or base_bpm
    min_bpm = profile.get('min_bpm') or effective_bpm
    max_bpm = profile.get('max_bpm') or effective_bpm
    tempo_change_count = profile.get('tempo_change_count') or 0
    tempo_volatility = profile.get('tempo_volatility') or 0.0
    has_accelerando = profile.get('has_accelerando', False)
    has_ritardando = profile.get('has_ritardando', False)
    has_rubato = profile.get('has_rubato', False)
    has_sudden_change = profile.get('has_sudden_change', False)
    tempo_regions = profile.get('tempo_regions') or 1
    
    # Calculate facet scores
    speed_demand = normalize_linear(effective_bpm, TEMPO_SPEED_BPM_LOW, TEMPO_SPEED_BPM_HIGH)
    
    # Control demand: changes + gradual modifications
    gradual_changes = (1 if has_accelerando else 0) + (1 if has_ritardando else 0)
    tempo_control_demand = clamp(
        normalize_linear(tempo_change_count + gradual_changes, TEMPO_CONTROL_CHANGES_LOW, TEMPO_CONTROL_CHANGES_HIGH) * 0.7 +
        (0.2 if has_rubato else 0.0) +
        (0.1 if has_sudden_change else 0.0)
    )
    
    # Variability: how much range and how volatile
    bpm_range_normalized = normalize_linear(max_bpm - min_bpm, 0, 60)
    tempo_variability = clamp(
        normalize_linear(tempo_volatility, 0, TEMPO_VARIABILITY_VOLATILITY_HIGH) * 0.6 +
        bpm_range_normalized * 0.4
    )
    
    facet_scores = {
        'speed_demand': round(speed_demand, 4),
        'tempo_control_demand': round(tempo_control_demand, 4),
        'tempo_variability': round(tempo_variability, 4),
    }
    
    # Derive domain scores from facets
    primary = clamp(
        speed_demand * 0.7 +
        tempo_control_demand * 0.3
    )
    
    hazard = clamp(
        tempo_variability * 0.5 +
        tempo_control_demand * 0.3 +
        (0.2 if has_sudden_change else 0.0)
    )
    
    overall = clamp(primary * 0.7 + hazard * 0.3)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if speed_demand > 0.7:
        flags.append('fast_tempo')
    if tempo_control_demand > 0.5:
        flags.append('tempo_changes_present')
    if has_sudden_change:
        flags.append('sudden_tempo_change')
    if has_rubato:
        flags.append('flexible_tempo_indicated')
    if tempo_variability > 0.5:
        flags.append('high_tempo_variability')
    
    # Confidence: lower if no tempo marking found
    confidence = 1.0 if profile.get('base_bpm') else 0.5
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=confidence,
    )
