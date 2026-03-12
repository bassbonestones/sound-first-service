"""
Scoring Package

Facet-aware domain scoring for Sound First material analysis.

Each domain produces a DomainResult containing:
- profile: raw measurable musical features
- facet_scores: normalized 0.0-1.0 scores for meaningful subcomponents
- scores: domain summary {primary, hazard, overall}
- bands: derived stages {primary_stage, hazard_stage, overall_stage}
- flags: warning/info flags
- confidence: how reliable the analysis is (1.0 = full confidence)

Main Classes:
    DomainResult: Complete analysis result for a single domain
    AllDomainResults: Container for results from all domains

Type Definitions:
    DomainScores: TypedDict for {primary, hazard, overall}
    DomainBands: TypedDict for {primary_stage, hazard_stage, overall_stage}

Domain Analyzers:
    analyze_interval_domain(profile) → DomainResult
    analyze_rhythm_domain(profile) → DomainResult
    analyze_tonal_domain(profile) → DomainResult
    analyze_tempo_domain(profile) → DomainResult
    analyze_range_domain(profile) → DomainResult
    analyze_throughput_domain(profile) → DomainResult
    analyze_pattern_domain(profile) → DomainResult

Composite:
    analyze_all_domains(profiles) → AllDomainResults

Interactions:
    calculate_interaction_bonus, calculate_composite_difficulty
    InteractionResult, analyze_hazards

Utilities:
    clamp, normalize_linear, normalize_sigmoid
    score_to_stage, derive_bands, STAGE_THRESHOLDS
"""

# Models
from .models import (
    DomainScores,
    DomainBands,
    DomainResult,
)

# Utilities
from .utils import (
    clamp,
    normalize_linear,
    normalize_sigmoid,
    score_to_stage,
    derive_bands,
    STAGE_THRESHOLDS,
)

# Domain scorers
from .interval_scorer import analyze_interval_domain
from .rhythm_scorer import analyze_rhythm_domain
from .tonal_scorer import analyze_tonal_domain
from .tempo_scorer import analyze_tempo_domain
from .range_scorer import analyze_range_domain
from .throughput_scorer import analyze_throughput_domain
from .pattern_scorer import analyze_pattern_domain

# Composite
from .composite import (
    AllDomainResults,
    analyze_all_domains,
    # Legacy aliases
    interval_profile_to_scores,
    rhythm_profile_to_scores,
    tonal_profile_to_scores,
    tempo_profile_to_scores,
    range_profile_to_scores,
    throughput_profile_to_scores,
    pattern_profile_to_scores,
)

# Interactions
from .interactions import (
    INTERACTION_CONFIG,
    MAX_INTERACTION_BONUS,
    InteractionResult,
    calculate_interaction_bonus,
    get_interaction_flags,
    has_interaction_hazard,
    DEFAULT_DOMAIN_WEIGHTS,
    calculate_composite_difficulty,
    analyze_hazards,
)

# Stage derivation
from .stage_derivation import (
    DEFAULT_STAGE_THRESHOLDS,
    STAGE_LABELS,
    STAGE_LABELS_SHORT,
    DomainStages,
    AllDomainStages,
    score_to_stage as derivation_score_to_stage,
    stage_to_score_range,
    get_stage_label,
    derive_domain_stages,
    derive_all_stages,
    analyze_score_distribution,
    suggest_thresholds_from_distribution,
)

__all__ = [
    # Models
    'DomainScores',
    'DomainBands',
    'DomainResult',
    # Utilities
    'clamp',
    'normalize_linear',
    'normalize_sigmoid',
    'score_to_stage',
    'derive_bands',
    'STAGE_THRESHOLDS',
    # Domain analyzers
    'analyze_interval_domain',
    'analyze_rhythm_domain',
    'analyze_tonal_domain',
    'analyze_tempo_domain',
    'analyze_range_domain',
    'analyze_throughput_domain',
    'analyze_pattern_domain',
    # Composite
    'AllDomainResults',
    'analyze_all_domains',
    # Legacy aliases
    'interval_profile_to_scores',
    'rhythm_profile_to_scores',
    'tonal_profile_to_scores',
    'tempo_profile_to_scores',
    'range_profile_to_scores',
    'throughput_profile_to_scores',
    'pattern_profile_to_scores',
    # Interactions
    'INTERACTION_CONFIG',
    'MAX_INTERACTION_BONUS',
    'InteractionResult',
    'calculate_interaction_bonus',
    'get_interaction_flags',
    'has_interaction_hazard',
    'DEFAULT_DOMAIN_WEIGHTS',
    'calculate_composite_difficulty',
    'analyze_hazards',
    # Stage derivation
    'DEFAULT_STAGE_THRESHOLDS',
    'STAGE_LABELS',
    'STAGE_LABELS_SHORT',
    'DomainStages',
    'AllDomainStages',
    'derivation_score_to_stage',
    'stage_to_score_range',
    'get_stage_label',
    'derive_domain_stages',
    'derive_all_stages',
    'analyze_score_distribution',
    'suggest_thresholds_from_distribution',
]
