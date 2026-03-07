"""
Practice Engine Module

Provides material selection, candidate ranking, and progression tracking
for music practice sessions.

All public symbols are re-exported here for backward compatibility.
"""

# Configuration
from .config import DEFAULT_CONFIG, EngineConfig

# Models
from .models import (
    AttemptResult,
    Bucket,
    CapabilityProgress,
    FocusTarget,
    MaterialCandidate,
    MaterialShelf,
    MaterialStatus,
    SessionMaterial,
)

# EMA and mastery
from .ema import (
    check_capability_mastery,
    check_material_mastery,
    compute_ema,
)

# Eligibility
from .eligibility import (
    check_bitmask_eligibility,
    check_content_dimension_eligibility,
    check_unified_score_eligibility,
    get_hazard_warnings,
    is_material_eligible,
)

# Maturity and buckets
from .maturity import (
    compute_bucket_weights,
    compute_capability_maturity,
    compute_combined_maturity,
    compute_material_maturity,
    sample_bucket,
)

# Targeting
from .targeting import (
    build_candidate_pool,
    filter_candidates_by_bucket,
    select_target_capabilities,
)

# Ranking
from .ranking import (
    compute_difficulty_match_value,
    compute_fatigue_penalty,
    compute_maintenance_value,
    compute_novelty_value,
    compute_progress_value,
    rank_candidates,
    score_candidate,
)

# Selection
from .selection import select_material

# Focus
from .focus import (
    compute_focus_score,
    select_focus_targets,
)

# Attempt processing
from .attempt import (
    process_attempt,
    update_pitch_focus_stats,
)

# Mask helpers
from .masks import (
    get_material_capability_masks,
    get_user_capability_masks,
    has_capability_bit,
    set_capability_bit,
)


__all__ = [
    # Config
    "EngineConfig",
    "DEFAULT_CONFIG",
    # Models
    "MaterialStatus",
    "MaterialShelf",
    "Bucket",
    "MaterialCandidate",
    "CapabilityProgress",
    "FocusTarget",
    "SessionMaterial",
    "AttemptResult",
    # EMA
    "compute_ema",
    "check_material_mastery",
    "check_capability_mastery",
    # Eligibility
    "check_bitmask_eligibility",
    "check_content_dimension_eligibility",
    "is_material_eligible",
    "check_unified_score_eligibility",
    "get_hazard_warnings",
    # Maturity
    "compute_material_maturity",
    "compute_capability_maturity",
    "compute_combined_maturity",
    "compute_bucket_weights",
    "sample_bucket",
    # Targeting
    "select_target_capabilities",
    "build_candidate_pool",
    "filter_candidates_by_bucket",
    # Ranking
    "compute_fatigue_penalty",
    "compute_progress_value",
    "compute_maintenance_value",
    "compute_novelty_value",
    "compute_difficulty_match_value",
    "score_candidate",
    "rank_candidates",
    # Selection
    "select_material",
    # Focus
    "compute_focus_score",
    "select_focus_targets",
    # Attempt
    "process_attempt",
    "update_pitch_focus_stats",
    # Masks
    "get_user_capability_masks",
    "get_material_capability_masks",
    "set_capability_bit",
    "has_capability_bit",
]
