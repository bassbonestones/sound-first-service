"""
Scoring Functions for Sound First — Facade Module

This module re-exports all scoring functionality from the app.scoring package.
All implementation has been moved to app/scoring/ for better organization.

See app/scoring/__init__.py for full documentation.
"""

# Re-export everything from the scoring package
from app.scoring import (
    # Models
    DomainScores,
    DomainBands,
    DomainResult,
    # Utilities
    clamp,
    normalize_linear,
    normalize_sigmoid,
    score_to_stage,
    derive_bands,
    STAGE_THRESHOLDS,
    # Domain analyzers
    analyze_interval_domain,
    analyze_rhythm_domain,
    analyze_tonal_domain,
    analyze_tempo_domain,
    analyze_range_domain,
    analyze_throughput_domain,
    analyze_pattern_domain,
    # Composite
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
]

