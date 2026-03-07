"""
Difficulty Interactions for Sound First

Computes interaction bonuses when multiple domains are simultaneously difficult.
Difficulty is multiplicative in certain combinations, not purely additive.

Key insight: Real music difficulty explodes when:
- Large leaps + complex rhythm (motor coordination)
- Complex rhythm + fast tempo (throughput pressure)  
- Large intervals + fast tempo (register control at speed)
- High throughput + complex rhythm (cognitive parsing)

Design principles:
- Interaction bonus is additive to composite score
- Max interaction bonus is capped (default 0.15) to prevent runaway effects
- Interaction flags help with UI warnings and targeted practice
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass


# =============================================================================
# INTERACTION CONFIGURATION
# =============================================================================

# PROVISIONAL THRESHOLDS - calibrate based on user experience data
INTERACTION_CONFIG = {
    # Leap + Rhythm interaction (motor coordination load)
    'interval_rhythm': {
        'interval_threshold': 0.55,  # interval.primary > this
        'rhythm_threshold': 0.55,    # rhythm.primary > this
        'bonus': 0.08,
        'flag': 'high_leap_rhythm_combo',
        'warning': 'Contains challenging leaps with complex rhythm',
    },
    
    # Tempo + Rhythm interaction (throughput pressure)
    'tempo_rhythm': {
        'tempo_threshold': 0.60,     # tempo.primary > this
        'rhythm_threshold': 0.60,    # rhythm.primary > this
        'bonus': 0.06,
        'flag': 'fast_complex_rhythm',
        'warning': 'Fast tempo with complex rhythmic patterns',
    },
    
    # Interval + Tempo interaction (register control at speed)
    'interval_tempo': {
        'interval_threshold': 0.60,  # interval.primary > this
        'tempo_threshold': 0.60,     # tempo.primary > this
        'bonus': 0.05,
        'flag': 'leaps_at_speed',
        'warning': 'Large intervals at fast tempo',
    },
    
    # Throughput + Rhythm interaction (cognitive parsing load)
    'throughput_rhythm': {
        'throughput_threshold': 0.65,  # throughput.primary > this
        'rhythm_threshold': 0.55,      # rhythm.primary > this
        'bonus': 0.07,
        'flag': 'dense_complex_rhythm',
        'warning': 'High note density with irregular patterns',
    },
    
    # Range + Interval interaction (embouchure/hand shift demands)
    'range_interval': {
        'range_threshold': 0.60,     # range.primary > this
        'interval_threshold': 0.55,  # interval.primary > this
        'bonus': 0.04,
        'flag': 'wide_range_with_leaps',
        'warning': 'Wide range with significant intervallic movement',
    },
    
    # Tonal + Rhythm interaction (cognitive load from chromaticism + rhythm)
    'tonal_rhythm': {
        'tonal_threshold': 0.60,   # tonal.primary > this
        'rhythm_threshold': 0.55,  # rhythm.primary > this
        'bonus': 0.04,
        'flag': 'chromatic_complex_rhythm',
        'warning': 'Chromatic content with complex rhythm',
    },
}

# Maximum total interaction bonus
MAX_INTERACTION_BONUS = 0.15


# =============================================================================
# INTERACTION CALCULATION
# =============================================================================

@dataclass
class InteractionResult:
    """Result of interaction analysis."""
    bonus: float
    flags: List[str]
    warnings: List[str]
    triggered_interactions: List[str]


def calculate_interaction_bonus(
    domain_scores: Dict[str, Dict[str, float]],
    config: Optional[Dict] = None,
    max_bonus: float = MAX_INTERACTION_BONUS
) -> InteractionResult:
    """
    Calculate interaction bonus from domain scores.
    
    Args:
        domain_scores: Dict mapping domain name to scores dict
            e.g., {
                "interval": {"primary": 0.65, "hazard": 0.70, "overall": 0.67},
                "rhythm": {"primary": 0.58, ...},
                ...
            }
        config: Optional custom interaction config (default: INTERACTION_CONFIG)
        max_bonus: Maximum total bonus (default: 0.15)
    
    Returns:
        InteractionResult with total bonus, flags, and warnings
    """
    if config is None:
        config = INTERACTION_CONFIG
    
    total_bonus = 0.0
    flags = []
    warnings = []
    triggered = []
    
    # Helper to get primary score for a domain (returns None if score is None/missing)
    def get_primary(domain: str) -> Optional[float]:
        primary = domain_scores.get(domain, {}).get('primary')
        return primary  # Keep None if the domain has no valid score
    
    # Check each interaction
    for name, interaction in config.items():
        # Parse interaction name to get domains
        domains = name.split('_')
        if len(domains) != 2:
            continue
        
        domain1, domain2 = domains
        
        # Get thresholds
        thresh1 = interaction.get(f'{domain1}_threshold', 1.0)
        thresh2 = interaction.get(f'{domain2}_threshold', 1.0)
        
        # Check if interaction is triggered (skip if either score is None)
        score1 = get_primary(domain1)
        score2 = get_primary(domain2)
        
        if score1 is None or score2 is None:
            continue
        
        if score1 > thresh1 and score2 > thresh2:
            bonus = interaction.get('bonus', 0.0)
            total_bonus += bonus
            triggered.append(name)
            
            if 'flag' in interaction:
                flags.append(interaction['flag'])
            if 'warning' in interaction:
                warnings.append(interaction['warning'])
    
    # Cap total bonus
    total_bonus = min(total_bonus, max_bonus)
    
    return InteractionResult(
        bonus=round(total_bonus, 4),
        flags=flags,
        warnings=warnings,
        triggered_interactions=triggered,
    )


def get_interaction_flags(domain_scores: Dict[str, Dict[str, float]]) -> List[str]:
    """
    Get just the flags for triggered interactions.
    
    Convenience function for quick flag checking.
    """
    result = calculate_interaction_bonus(domain_scores)
    return result.flags


def has_interaction_hazard(
    domain_scores: Dict[str, Dict[str, float]],
    threshold: float = 0.05
) -> bool:
    """
    Check if interactions contribute significant difficulty.
    
    Args:
        domain_scores: Domain scores dict
        threshold: Minimum bonus to consider hazardous
    
    Returns:
        True if interaction bonus exceeds threshold
    """
    result = calculate_interaction_bonus(domain_scores)
    return result.bonus >= threshold


# =============================================================================
# COMPOSITE DIFFICULTY CALCULATION
# =============================================================================

# Default weights for composite calculation
DEFAULT_DOMAIN_WEIGHTS = {
    'rhythm': 0.22,
    'interval': 0.18,
    'tonal': 0.14,
    'tempo': 0.14,
    'throughput': 0.14,
    'pattern': 0.10,   # Predictability/cognitive load
    'notation': 0.08,  # Future
}


def calculate_composite_difficulty(
    domain_scores: Dict[str, Dict[str, float]],
    weights: Optional[Dict[str, float]] = None,
    include_interactions: bool = True
) -> Dict[str, float]:
    """
    Calculate composite difficulty from domain scores.
    
    Args:
        domain_scores: Dict mapping domain name to scores dict
        weights: Optional custom domain weights (default: DEFAULT_DOMAIN_WEIGHTS)
        include_interactions: Whether to add interaction bonus
    
    Returns:
        Dict with:
            - 'weighted_sum': Base composite from domain weights
            - 'interaction_bonus': Bonus from domain interactions
            - 'overall': Final composite (capped at 1.0)
            - 'interaction_flags': List of triggered interaction flags
    """
    if weights is None:
        weights = DEFAULT_DOMAIN_WEIGHTS
    
    # Calculate weighted sum of domain overall scores
    # Skip domains with None scores (e.g., range without instrument context)
    weighted_sum = 0.0
    total_weight = 0.0
    
    for domain, weight in weights.items():
        if domain in domain_scores:
            overall = domain_scores[domain].get('overall')
            if overall is not None:
                weighted_sum += overall * weight
                total_weight += weight
    
    # Normalize if not all domains present
    if total_weight > 0 and total_weight < 1.0:
        weighted_sum = weighted_sum / total_weight
    
    # Calculate interaction bonus
    interaction_result = InteractionResult(bonus=0.0, flags=[], warnings=[], triggered_interactions=[])
    if include_interactions:
        interaction_result = calculate_interaction_bonus(domain_scores)
    
    # Compute final composite
    overall = min(1.0, weighted_sum + interaction_result.bonus)
    
    return {
        'weighted_sum': round(weighted_sum, 4),
        'interaction_bonus': round(interaction_result.bonus, 4),
        'overall': round(overall, 4),
        'interaction_flags': interaction_result.flags,
        'interaction_warnings': interaction_result.warnings,
    }


# =============================================================================
# HAZARD ANALYSIS
# =============================================================================

def analyze_hazards(
    domain_scores: Dict[str, Dict[str, float]],
    student_scores: Optional[Dict[str, float]] = None,
    tolerance: float = 0.15
) -> Dict[str, List[str]]:
    """
    Analyze hazards for a piece relative to student abilities.
    
    Args:
        domain_scores: Material's domain scores
        student_scores: Student's ability scores per domain (optional)
            e.g., {"interval": 0.45, "rhythm": 0.50, ...}
        tolerance: How much above student ability is considered hazardous
    
    Returns:
        Dict with:
            - 'domain_hazards': Domains where hazard is high
            - 'ability_hazards': Domains exceeding student ability + tolerance
            - 'interaction_hazards': Interaction hazards
    """
    hazards = {
        'domain_hazards': [],
        'ability_hazards': [],
        'interaction_hazards': [],
    }
    
    # Check domain hazard scores
    for domain, scores in domain_scores.items():
        hazard_score = scores.get('hazard', 0.0)
        if hazard_score >= 0.65:  # High hazard threshold
            hazards['domain_hazards'].append({
                'domain': domain,
                'hazard_score': hazard_score,
                'level': 'high' if hazard_score >= 0.80 else 'moderate',
            })
    
    # Check against student abilities if provided
    if student_scores:
        for domain, scores in domain_scores.items():
            piece_hazard = scores.get('hazard', 0.0)
            student_ability = student_scores.get(domain, 0.0)
            
            if piece_hazard > student_ability + tolerance:
                hazards['ability_hazards'].append({
                    'domain': domain,
                    'piece_hazard': piece_hazard,
                    'student_ability': student_ability,
                    'gap': round(piece_hazard - student_ability, 2),
                })
    
    # Check interaction hazards
    interaction_result = calculate_interaction_bonus(domain_scores)
    if interaction_result.flags:
        hazards['interaction_hazards'] = interaction_result.warnings
    
    return hazards
