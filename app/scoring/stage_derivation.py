"""
Stage Derivation for Sound First

Derives discrete stages (0-6) from continuous scores (0.0-1.0).
Stages are for:
- UI labels
- Broad assignment bands  
- Capability mapping
- Teacher readability

Design principles:
- Stages are derived, not stored as primary data
- Thresholds are PROVISIONAL and should be calibrated from corpus analysis
- All domains use consistent 0-6 range
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict


# =============================================================================
# STAGE THRESHOLDS
# =============================================================================

# PROVISIONAL: These thresholds should be calibrated after analyzing real materials
# Current: equal-width bands
DEFAULT_STAGE_THRESHOLDS = [
    0.15,  # Stage 0 → 1 boundary
    0.30,  # Stage 1 → 2 boundary
    0.45,  # Stage 2 → 3 boundary
    0.60,  # Stage 3 → 4 boundary
    0.75,  # Stage 4 → 5 boundary
    0.90,  # Stage 5 → 6 boundary
]

# Score ranges for reference:
# Stage 0: [0.00, 0.15)  - Trivial
# Stage 1: [0.15, 0.30)  - Beginner
# Stage 2: [0.30, 0.45)  - Early Intermediate
# Stage 3: [0.45, 0.60)  - Intermediate
# Stage 4: [0.60, 0.75)  - Late Intermediate
# Stage 5: [0.75, 0.90)  - Advanced
# Stage 6: [0.90, 1.00]  - Expert

# Stage labels for UI display
STAGE_LABELS = {
    0: "Trivial",
    1: "Beginner",
    2: "Early Intermediate",
    3: "Intermediate",
    4: "Late Intermediate",
    5: "Advanced",
    6: "Expert",
}

# Short labels
STAGE_LABELS_SHORT = {
    0: "I",
    1: "II",
    2: "III",
    3: "IV",
    4: "V",
    5: "VI",
    6: "VII",
}


# =============================================================================
# CORE DERIVATION FUNCTION
# =============================================================================

def score_to_stage(
    score: float,
    thresholds: Optional[List[float]] = None
) -> int:
    """
    Convert a continuous score (0.0-1.0) to a discrete stage (0-6).
    
    Args:
        score: Normalized score in [0.0, 1.0]
        thresholds: List of 6 boundaries. If None, uses DEFAULT_STAGE_THRESHOLDS.
    
    Returns:
        Integer stage 0-6
    
    Example:
        >>> score_to_stage(0.42)
        2
        >>> score_to_stage(0.75)
        5
    """
    if thresholds is None:
        thresholds = DEFAULT_STAGE_THRESHOLDS
    
    # Clamp score to valid range
    score = max(0.0, min(1.0, score))
    
    # Find stage by comparing against thresholds
    for stage, threshold in enumerate(thresholds):
        if score < threshold:
            return stage
    return 6


def stage_to_score_range(
    stage: int, 
    thresholds: Optional[List[float]] = None
) -> Tuple[float, float]:
    """
    Get the score range for a given stage.
    
    Args:
        stage: Integer stage 0-6
        thresholds: List of 6 boundaries. If None, uses DEFAULT_STAGE_THRESHOLDS.
    
    Returns:
        Tuple of (low, high) score bounds
    
    Example:
        >>> stage_to_score_range(2)
        (0.30, 0.45)
    """
    if thresholds is None:
        thresholds = DEFAULT_STAGE_THRESHOLDS
    
    stage = max(0, min(6, stage))
    
    low = 0.0 if stage == 0 else thresholds[stage - 1]
    high = 1.0 if stage == 6 else thresholds[stage]
    
    return (low, high)


def get_stage_label(stage: int, short: bool = False) -> str:
    """
    Get human-readable label for a stage.
    
    Args:
        stage: Integer stage 0-6
        short: If True, return short label (Roman numeral)
    
    Returns:
        Stage label string
    """
    stage = max(0, min(6, stage))
    if short:
        return STAGE_LABELS_SHORT.get(stage, str(stage))
    return STAGE_LABELS.get(stage, f"Stage {stage}")


# =============================================================================
# DOMAIN-SPECIFIC STAGING
# =============================================================================

@dataclass
class DomainStages:
    """Stages derived from domain scores."""
    primary_stage: int
    hazard_stage: int
    overall_stage: int


def derive_domain_stages(
    scores: Dict[str, float],
    thresholds: Optional[List[float]] = None
) -> DomainStages:
    """
    Derive stages from domain scores.
    
    Args:
        scores: Dict with keys 'primary', 'hazard', 'overall'
        thresholds: Optional custom thresholds
    
    Returns:
        DomainStages with all three stages
    """
    return DomainStages(
        primary_stage=score_to_stage(scores.get('primary', 0.0), thresholds),
        hazard_stage=score_to_stage(scores.get('hazard', 0.0), thresholds),
        overall_stage=score_to_stage(scores.get('overall', 0.0), thresholds),
    )


# =============================================================================
# COMPLETE ANALYSIS STAGING
# =============================================================================

@dataclass
class AllDomainStages:
    """Stages for all analysis domains."""
    interval: Optional[DomainStages] = None
    rhythm: Optional[DomainStages] = None
    tonal: Optional[DomainStages] = None
    tempo: Optional[DomainStages] = None
    range: Optional[DomainStages] = None
    throughput: Optional[DomainStages] = None


def derive_all_stages(
    all_scores: Dict[str, Dict[str, float]],
    thresholds: Optional[List[float]] = None
) -> AllDomainStages:
    """
    Derive stages for all domains from their scores.
    
    Args:
        all_scores: Dict mapping domain name to scores dict
            e.g., {"interval": {"primary": 0.5, "hazard": 0.7, "overall": 0.55}, ...}
        thresholds: Optional custom thresholds (same for all domains)
    
    Returns:
        AllDomainStages with stages for each domain present
    """
    stages = AllDomainStages()
    
    if 'interval' in all_scores:
        stages.interval = derive_domain_stages(all_scores['interval'], thresholds)
    if 'rhythm' in all_scores:
        stages.rhythm = derive_domain_stages(all_scores['rhythm'], thresholds)
    if 'tonal' in all_scores:
        stages.tonal = derive_domain_stages(all_scores['tonal'], thresholds)
    if 'tempo' in all_scores:
        stages.tempo = derive_domain_stages(all_scores['tempo'], thresholds)
    if 'range' in all_scores:
        stages.range = derive_domain_stages(all_scores['range'], thresholds)
    if 'throughput' in all_scores:
        stages.throughput = derive_domain_stages(all_scores['throughput'], thresholds)
    
    return stages


# =============================================================================
# CALIBRATION UTILITIES
# =============================================================================

def analyze_score_distribution(scores: List[float]) -> Dict[str, Any]:
    """
    Analyze score distribution for threshold calibration.
    
    Args:
        scores: List of scores from a corpus of materials
    
    Returns:
        Dict with statistics useful for calibration
    """
    if not scores:
        return {
            'count': 0,
            'min': None,
            'max': None,
            'mean': None,
            'median': None,
            'percentiles': {},
        }
    
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    
    def percentile(p: float) -> float:
        k = (n - 1) * p / 100
        f = int(k)
        c = f + 1 if f + 1 < n else f
        return sorted_scores[f] + (sorted_scores[c] - sorted_scores[f]) * (k - f)
    
    return {
        'count': n,
        'min': sorted_scores[0],
        'max': sorted_scores[-1],
        'mean': sum(sorted_scores) / n,
        'median': percentile(50),
        'percentiles': {
            'p10': percentile(10),
            'p25': percentile(25),
            'p50': percentile(50),
            'p75': percentile(75),
            'p90': percentile(90),
            'p95': percentile(95),
        },
        'stage_distribution': {
            stage: sum(1 for s in scores if score_to_stage(s) == stage)
            for stage in range(7)
        },
    }


def suggest_thresholds_from_distribution(
    scores: List[float],
    target_distribution: Optional[Dict[int, float]] = None
) -> List[float]:
    """
    Suggest threshold values based on observed score distribution.
    
    Args:
        scores: List of scores from corpus
        target_distribution: Optional desired proportion per stage
            e.g., {0: 0.10, 1: 0.15, 2: 0.20, 3: 0.25, 4: 0.15, 5: 0.10, 6: 0.05}
    
    Returns:
        List of 6 suggested thresholds
    """
    if not scores:
        return DEFAULT_STAGE_THRESHOLDS.copy()
    
    if target_distribution is None:
        # Default: roughly even distribution with fewer at extremes
        target_distribution = {
            0: 0.10,  # 10% in Stage 0
            1: 0.15,  # 15% in Stage 1
            2: 0.20,  # 20% in Stage 2
            3: 0.25,  # 25% in Stage 3
            4: 0.15,  # 15% in Stage 4
            5: 0.10,  # 10% in Stage 5
            6: 0.05,  # 5% in Stage 6
        }
    
    sorted_scores = sorted(scores)
    n = len(sorted_scores)
    
    # Calculate cumulative target proportions
    thresholds = []
    cumulative = 0.0
    
    for stage in range(6):  # 6 thresholds for 7 stages
        cumulative += target_distribution.get(stage, 1/7)
        idx = min(int(cumulative * n), n - 1)
        thresholds.append(sorted_scores[idx])
    
    return thresholds
