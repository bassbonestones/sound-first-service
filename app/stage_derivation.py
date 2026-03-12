"""
Stage Derivation for Sound First — FACADE MODULE

This module re-exports all stage derivation functionality from
app.scoring.stage_derivation for backwards compatibility.

The actual implementation is in app/scoring/stage_derivation.py.

For new code, prefer importing directly from app.scoring.

Derives discrete stages (0-6) from continuous scores (0.0-1.0).
Stages are for:
- UI labels
- Broad assignment bands
- Capability mapping
- Teacher readability
"""

# Re-export everything from the scoring module
from app.scoring.stage_derivation import (
    DEFAULT_STAGE_THRESHOLDS,
    STAGE_LABELS,
    STAGE_LABELS_SHORT,
    DomainStages,
    AllDomainStages,
    score_to_stage,
    stage_to_score_range,
    get_stage_label,
    derive_domain_stages,
    derive_all_stages,
    analyze_score_distribution,
    suggest_thresholds_from_distribution,
)

__all__ = [
    "DEFAULT_STAGE_THRESHOLDS",
    "STAGE_LABELS",
    "STAGE_LABELS_SHORT",
    "DomainStages",
    "AllDomainStages",
    "score_to_stage",
    "stage_to_score_range",
    "get_stage_label",
    "derive_domain_stages",
    "derive_all_stages",
    "analyze_score_distribution",
    "suggest_thresholds_from_distribution",
]
