"""
Adaptive Practice Engine for Sound First (v1)

This module implements the core algorithms for:
- Session generation
- Target capability selection
- Candidate material generation (scalable to 100k+ materials)
- Bucketing + bucket weights
- Ranking within buckets
- Mastery updates (EMA + min attempts gate)
- Capability evidence updates
- Focus targeting after material selection

Key Principles:
- Capabilities drive progression
- Content dimensions govern difficulty
- Materials are interchangeable vehicles
- Focus cards provide micro-targeting inside any material
- No global scoring over the full library per session
"""

import math
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_


# =============================================================================
# CONFIGURATION (All parameters adjustable)
# =============================================================================

@dataclass
class EngineConfig:
    """Configurable parameters for the practice engine."""
    
    # EMA and mastery thresholds
    ema_alpha: float = 0.35  # Weight for new scores in EMA
    min_attempts_for_mastery: int = 5  # Minimum attempts before mastery possible
    mastery_threshold: float = 4.0  # EMA threshold for mastery (1-5 scale)
    
    # Target capability selection
    target_capability_count: int = 10  # How many target capabilities to consider
    
    # Candidate generation
    candidates_per_capability: int = 20  # Candidates to sample per target capability
    max_candidates_pool: int = 300  # Maximum total candidate pool size
    
    # Fatigue/recency
    fatigue_tau_days: float = 2.0  # Soft recency penalty decay constant
    
    # Bucket weight minimums
    min_bucket_new: float = 0.10
    min_bucket_in_progress: float = 0.15
    min_bucket_maintenance: float = 0.05
    
    # Focus targeting
    focus_targets_per_material: int = 3  # Pitch/focus combos to target
    avoid_extremes_factor: float = 0.7  # Soft penalty near range extremes
    
    # Maturity calculation weights
    maturity_cap_weight: float = 0.6
    maturity_mat_weight: float = 0.4


# Global default config (can be overridden)
DEFAULT_CONFIG = EngineConfig()


# =============================================================================
# ENUMS AND DATA CLASSES
# =============================================================================

class MaterialStatus(Enum):
    """Status buckets for materials."""
    UNEXPLORED = "UNEXPLORED"
    IN_PROGRESS = "IN_PROGRESS"
    MASTERED = "MASTERED"


class MaterialShelf(Enum):
    """Shelf organization for mastered materials."""
    DEFAULT = "DEFAULT"
    MAINTENANCE = "MAINTENANCE"
    ARCHIVE = "ARCHIVE"


class Bucket(Enum):
    """Session bucket types."""
    NEW = "NEW"  # Eligible + never attempted
    IN_PROGRESS = "IN_PROGRESS"  # Eligible + attempted + not mastered
    MAINTENANCE = "MAINTENANCE"  # Eligible + mastered + shelf=MAINTENANCE


@dataclass
class MaterialCandidate:
    """A material candidate for session selection."""
    material_id: int
    teaches_capabilities: List[int] = field(default_factory=list)
    difficulty_index: float = 0.5
    ema_score: float = 0.0
    attempt_count: int = 0
    last_attempt_at: Optional[datetime] = None
    status: MaterialStatus = MaterialStatus.UNEXPLORED
    shelf: MaterialShelf = MaterialShelf.DEFAULT


@dataclass
class CapabilityProgress:
    """Progress tracking for a capability."""
    capability_id: int
    evidence_count: int = 0
    required_count: int = 1
    is_mastered: bool = False
    difficulty_weight: float = 1.0
    
    @property
    def progress_ratio(self) -> float:
        """How close to unlocking (0.0 to 1.0+)."""
        if self.required_count == 0:
            return 1.0
        return self.evidence_count / self.required_count


@dataclass
class FocusTarget:
    """A pitch/focus combination to emphasize."""
    pitch_midi: int
    focus_card_id: int
    ema_score: float = 0.0
    score: float = 0.0  # Computed targeting score


@dataclass
class SessionMaterial:
    """Selected material for a session with focus targets."""
    material_id: int
    bucket: Bucket
    focus_targets: List[FocusTarget] = field(default_factory=list)


# =============================================================================
# EMA AND MASTERY CALCULATIONS
# =============================================================================

def compute_ema(
    current_score: float,
    previous_ema: float,
    alpha: float = None,
    config: EngineConfig = None
) -> float:
    """
    Compute exponential moving average.
    
    EMA_new = alpha * current_score + (1 - alpha) * EMA_previous
    """
    if config is None:
        config = DEFAULT_CONFIG
    if alpha is None:
        alpha = config.ema_alpha
    
    return alpha * current_score + (1 - alpha) * previous_ema


def check_material_mastery(
    ema_score: float,
    attempt_count: int,
    config: EngineConfig = None
) -> bool:
    """
    Check if material is mastered based on EMA + minimum attempts gate.
    
    mastered = attempt_count >= MIN_ATTEMPTS AND ema_score >= MASTERY_THRESHOLD
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    return (
        attempt_count >= config.min_attempts_for_mastery
        and ema_score >= config.mastery_threshold
    )


def check_capability_mastery(
    evidence_count: int,
    required_count: int,
    distinct_materials_required: bool = False,
    distinct_material_count: int = 0
) -> bool:
    """
    Check if capability is mastered based on evidence profile.
    
    For simple count: evidence_count >= required_count
    For distinct materials: also check distinct_material_count >= required_count
    """
    if distinct_materials_required:
        return distinct_material_count >= required_count
    return evidence_count >= required_count


# =============================================================================
# ELIGIBILITY CHECKING
# =============================================================================

def check_bitmask_eligibility(
    user_masks: List[int],
    material_masks: List[int]
) -> bool:
    """
    Fast O(1) check for capability eligibility using bitmasks.
    
    Returns True if every required capability bit is set in user's mask.
    """
    for i in range(min(len(user_masks), len(material_masks))):
        # If any required bit is NOT in user's mask, not eligible
        if (material_masks[i] & ~user_masks[i]) != 0:
            return False
    return True


def check_content_dimension_eligibility(
    material_stages: Dict[str, int],
    user_max_stages: Dict[str, int]
) -> bool:
    """
    Check if material's content dimensions are within user's caps.
    
    material_stages: e.g., {'rhythm_complexity_stage': 3, 'range_usage_stage': 2}
    user_max_stages: e.g., {'rhythm_complexity_stage': 4, 'range_usage_stage': 3}
    """
    for dimension, stage in material_stages.items():
        if stage is None:
            continue
        max_stage = user_max_stages.get(dimension)
        if max_stage is not None and stage > max_stage:
            return False
    return True


def is_material_eligible(
    user_masks: List[int],
    material_masks: List[int],
    material_stages: Dict[str, int] = None,
    user_max_stages: Dict[str, int] = None,
    has_license: bool = True
) -> bool:
    """
    Single source of truth for material eligibility (guided mode).
    
    Checks:
    1. License/access
    2. Capability bitmasks
    3. Content dimension caps
    """
    if not has_license:
        return False
    
    if not check_bitmask_eligibility(user_masks, material_masks):
        return False
    
    if material_stages and user_max_stages:
        if not check_content_dimension_eligibility(material_stages, user_max_stages):
            return False
    
    return True


# =============================================================================
# MATURITY CALCULATION
# =============================================================================

def compute_material_maturity(
    mastered_difficulty_sum: float,
    total_difficulty_sum: float
) -> float:
    """
    Compute material maturity as difficulty-weighted ratio.
    
    mat_maturity = Σ difficulty_index(mastered) / Σ difficulty_index(eligible)
    """
    if total_difficulty_sum == 0:
        return 0.0
    return mastered_difficulty_sum / total_difficulty_sum


def compute_capability_maturity(
    mastered_weight_sum: float,
    total_weight_sum: float
) -> float:
    """
    Compute capability maturity as difficulty-weighted ratio.
    
    cap_maturity = Σ difficulty_weight(mastered) / Σ difficulty_weight(eligible)
    """
    if total_weight_sum == 0:
        return 0.0
    return mastered_weight_sum / total_weight_sum


def compute_combined_maturity(
    cap_maturity: float,
    mat_maturity: float,
    config: EngineConfig = None
) -> float:
    """
    Compute combined maturity score.
    
    maturity = 0.6 * cap_maturity + 0.4 * mat_maturity
    Clamped to [0, 1].
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    maturity = (
        config.maturity_cap_weight * cap_maturity
        + config.maturity_mat_weight * mat_maturity
    )
    return max(0.0, min(1.0, maturity))


# =============================================================================
# BUCKET WEIGHTS
# =============================================================================

def compute_bucket_weights(
    maturity: float,
    config: EngineConfig = None
) -> Dict[Bucket, float]:
    """
    Compute bucket weights based on maturity.
    
    Early learners: more IN_PROGRESS + NEW
    Advanced learners: more MAINTENANCE
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Base curves (tunable)
    w_in_progress = 0.65 - 0.30 * maturity  # 0.65 -> 0.35
    w_maintenance = 0.10 + 0.35 * maturity  # 0.10 -> 0.45
    w_new = 1.0 - w_in_progress - w_maintenance
    
    # Apply minimums
    w_new = max(w_new, config.min_bucket_new)
    w_in_progress = max(w_in_progress, config.min_bucket_in_progress)
    w_maintenance = max(w_maintenance, config.min_bucket_maintenance)
    
    # Normalize to sum to 1
    total = w_new + w_in_progress + w_maintenance
    
    return {
        Bucket.NEW: w_new / total,
        Bucket.IN_PROGRESS: w_in_progress / total,
        Bucket.MAINTENANCE: w_maintenance / total,
    }


def sample_bucket(weights: Dict[Bucket, float]) -> Bucket:
    """Randomly sample a bucket based on weights."""
    r = random.random()
    cumulative = 0.0
    for bucket, weight in weights.items():
        cumulative += weight
        if r < cumulative:
            return bucket
    return Bucket.IN_PROGRESS  # Fallback


# =============================================================================
# TARGET CAPABILITY SELECTION
# =============================================================================

def select_target_capabilities(
    capability_progress: List[CapabilityProgress],
    config: EngineConfig = None
) -> List[CapabilityProgress]:
    """
    Select target capabilities for this session.
    
    Prioritize:
    1. Highest progress_ratio (near unlock)
    2. Tie-break by difficulty_weight
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Filter to non-mastered capabilities
    candidates = [cp for cp in capability_progress if not cp.is_mastered]
    
    # Sort by progress ratio (descending), then difficulty weight (descending)
    candidates.sort(
        key=lambda cp: (cp.progress_ratio, cp.difficulty_weight),
        reverse=True
    )
    
    return candidates[:config.target_capability_count]


# =============================================================================
# CANDIDATE MATERIAL GENERATION
# =============================================================================

def build_candidate_pool(
    target_capabilities: List[CapabilityProgress],
    materials_by_teaches: Dict[int, List[int]],
    material_states: Dict[int, MaterialCandidate],
    user_masks: List[int],
    get_material_masks: callable,
    config: EngineConfig = None
) -> List[MaterialCandidate]:
    """
    Build candidate pool by sampling from materials that teach target capabilities.
    
    Never score the full library - only score sampled candidates.
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    pool_ids: Set[int] = set()
    
    for cap in target_capabilities:
        # Get materials that teach this capability
        material_ids = materials_by_teaches.get(cap.capability_id, [])
        
        # Filter to eligible materials
        eligible_ids = []
        for mid in material_ids:
            material_masks = get_material_masks(mid)
            if check_bitmask_eligibility(user_masks, material_masks):
                eligible_ids.append(mid)
        
        # Sample up to candidates_per_capability
        if len(eligible_ids) > config.candidates_per_capability:
            sampled = random.sample(eligible_ids, config.candidates_per_capability)
        else:
            sampled = eligible_ids
        
        pool_ids.update(sampled)
    
    # Cap total pool size
    if len(pool_ids) > config.max_candidates_pool:
        pool_ids = set(random.sample(list(pool_ids), config.max_candidates_pool))
    
    # Convert to MaterialCandidate objects
    pool = []
    for mid in pool_ids:
        if mid in material_states:
            pool.append(material_states[mid])
        else:
            # Create default state if not tracked yet
            pool.append(MaterialCandidate(material_id=mid))
    
    return pool


def filter_candidates_by_bucket(
    candidates: List[MaterialCandidate],
    bucket: Bucket
) -> List[MaterialCandidate]:
    """Filter candidates to those belonging to a specific bucket."""
    result = []
    
    for c in candidates:
        if bucket == Bucket.NEW:
            # Eligible + never attempted
            if c.status == MaterialStatus.UNEXPLORED and c.attempt_count == 0:
                result.append(c)
        elif bucket == Bucket.IN_PROGRESS:
            # Eligible + attempted + not mastered
            if c.status == MaterialStatus.IN_PROGRESS:
                result.append(c)
        elif bucket == Bucket.MAINTENANCE:
            # Eligible + mastered + shelf=MAINTENANCE
            if c.status == MaterialStatus.MASTERED and c.shelf == MaterialShelf.MAINTENANCE:
                result.append(c)
    
    return result


# =============================================================================
# RANKING WITHIN BUCKETS
# =============================================================================

def compute_fatigue_penalty(
    last_attempt_at: Optional[datetime],
    now: datetime = None,
    config: EngineConfig = None
) -> float:
    """
    Compute soft fatigue penalty based on recency.
    
    fatiguePenalty = exp(-daysSince / FATIGUE_TAU_DAYS)
    Returns 0 if never attempted.
    """
    if config is None:
        config = DEFAULT_CONFIG
    if now is None:
        now = datetime.now()
    
    if last_attempt_at is None:
        return 0.0
    
    days_since = (now - last_attempt_at).total_seconds() / 86400
    return math.exp(-days_since / config.fatigue_tau_days)


def compute_progress_value(
    candidate: MaterialCandidate,
    capability_progress: Dict[int, CapabilityProgress]
) -> float:
    """
    Compute progress value for a material.
    
    progressValue = max(progress_ratio(cap)) for caps the material teaches
    """
    if not candidate.teaches_capabilities:
        return 0.0
    
    max_progress = 0.0
    for cap_id in candidate.teaches_capabilities:
        cp = capability_progress.get(cap_id)
        if cp and not cp.is_mastered:
            max_progress = max(max_progress, cp.progress_ratio)
    
    return max_progress


def compute_maintenance_value(candidate: MaterialCandidate) -> float:
    """
    Compute maintenance value (prefer weaker mastered items).
    
    maintenanceValue = 1 - normalized_ema
    Where EMA is normalized to 0-1 (from 1-5 scale).
    """
    # Normalize EMA from 1-5 scale to 0-1
    normalized_ema = (candidate.ema_score - 1.0) / 4.0
    normalized_ema = max(0.0, min(1.0, normalized_ema))
    return 1.0 - normalized_ema


def compute_novelty_value(candidate: MaterialCandidate) -> float:
    """Return 1 if unexplored, 0 otherwise."""
    if candidate.status == MaterialStatus.UNEXPLORED:
        return 1.0
    return 0.0


def score_candidate(
    candidate: MaterialCandidate,
    bucket: Bucket,
    capability_progress: Dict[int, CapabilityProgress],
    now: datetime = None,
    config: EngineConfig = None
) -> float:
    """
    Score a candidate based on its bucket.
    
    NEW: 1.0*progressValue + 0.5*noveltyValue - 0.3*fatiguePenalty
    IN_PROGRESS: 1.0*progressValue + 0.8*maintenanceValue - 0.3*fatiguePenalty
    MAINTENANCE: 0.6*maintenanceValue + 0.3*progressValue - 0.3*fatiguePenalty
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    progress_val = compute_progress_value(candidate, capability_progress)
    maintenance_val = compute_maintenance_value(candidate)
    novelty_val = compute_novelty_value(candidate)
    fatigue_pen = compute_fatigue_penalty(candidate.last_attempt_at, now, config)
    
    if bucket == Bucket.NEW:
        return 1.0 * progress_val + 0.5 * novelty_val - 0.3 * fatigue_pen
    elif bucket == Bucket.IN_PROGRESS:
        return 1.0 * progress_val + 0.8 * maintenance_val - 0.3 * fatigue_pen
    else:  # MAINTENANCE
        return 0.6 * maintenance_val + 0.3 * progress_val - 0.3 * fatigue_pen


def rank_candidates(
    candidates: List[MaterialCandidate],
    bucket: Bucket,
    capability_progress: Dict[int, CapabilityProgress],
    now: datetime = None,
    config: EngineConfig = None
) -> List[MaterialCandidate]:
    """Rank candidates by score within a bucket."""
    scored = [
        (c, score_candidate(c, bucket, capability_progress, now, config))
        for c in candidates
    ]
    scored.sort(key=lambda x: x[1], reverse=True)
    return [c for c, _ in scored]


# =============================================================================
# MATERIAL SELECTION (END-TO-END)
# =============================================================================

def select_material(
    user_masks: List[int],
    capability_progress: List[CapabilityProgress],
    materials_by_teaches: Dict[int, List[int]],
    material_states: Dict[int, MaterialCandidate],
    get_material_masks: callable,
    maturity: float = None,
    config: EngineConfig = None
) -> Optional[SessionMaterial]:
    """
    End-to-end material selection for a session.
    
    1. Compute maturity (if not provided)
    2. Compute bucket weights
    3. Select target capabilities
    4. Build candidate pool
    5. Sample bucket
    6. Filter candidates by bucket
    7. Rank and select
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Convert to dict for easier lookup
    cap_progress_dict = {cp.capability_id: cp for cp in capability_progress}
    
    # Compute maturity if not provided
    if maturity is None:
        mastered_weight = sum(cp.difficulty_weight for cp in capability_progress if cp.is_mastered)
        total_weight = sum(cp.difficulty_weight for cp in capability_progress)
        maturity = compute_capability_maturity(mastered_weight, total_weight)
    
    # Compute bucket weights
    bucket_weights = compute_bucket_weights(maturity, config)
    
    # Select target capabilities
    targets = select_target_capabilities(capability_progress, config)
    if not targets:
        return None
    
    # Build candidate pool
    pool = build_candidate_pool(
        targets,
        materials_by_teaches,
        material_states,
        user_masks,
        get_material_masks,
        config
    )
    
    if not pool:
        return None
    
    # Try buckets in weighted order
    now = datetime.now()
    for _ in range(3):  # Try up to 3 buckets
        bucket = sample_bucket(bucket_weights)
        candidates = filter_candidates_by_bucket(pool, bucket)
        
        if candidates:
            ranked = rank_candidates(candidates, bucket, cap_progress_dict, now, config)
            if ranked:
                return SessionMaterial(
                    material_id=ranked[0].material_id,
                    bucket=bucket
                )
    
    # Fallback: pick anything from pool
    if pool:
        return SessionMaterial(
            material_id=pool[0].material_id,
            bucket=Bucket.IN_PROGRESS
        )
    
    return None


# =============================================================================
# FOCUS TARGETING (AFTER MATERIAL SELECTED)
# =============================================================================

def compute_focus_score(
    pitch_midi: int,
    ema_score: float,
    last_attempt_at: Optional[datetime],
    user_range_center: int,
    now: datetime = None,
    config: EngineConfig = None
) -> float:
    """
    Compute focus targeting score for a pitch/focus combo.
    
    focusScore = 1.0*badness + 0.3*spacing - 0.3*extremePenalty
    
    Where:
    - badness = 1 - normalize(ema)
    - spacing = daysSince(last_attempt)
    - extremePenalty = distance from range center * avoid_extremes_factor
    """
    if config is None:
        config = DEFAULT_CONFIG
    if now is None:
        now = datetime.now()
    
    # Badness (lower EMA = higher badness)
    normalized_ema = (ema_score - 1.0) / 4.0 if ema_score > 0 else 0.0
    normalized_ema = max(0.0, min(1.0, normalized_ema))
    badness = 1.0 - normalized_ema
    
    # Spacing (days since last attempt)
    if last_attempt_at is None:
        spacing = 7.0  # Default for never attempted
    else:
        spacing = (now - last_attempt_at).total_seconds() / 86400
    spacing = min(spacing, 30.0)  # Cap at 30 days
    spacing = spacing / 30.0  # Normalize to 0-1
    
    # Extreme penalty (distance from center)
    distance = abs(pitch_midi - user_range_center)
    max_distance = 24  # 2 octaves
    extreme_penalty = (distance / max_distance) * config.avoid_extremes_factor
    
    return 1.0 * badness + 0.3 * spacing - 0.3 * extreme_penalty


def select_focus_targets(
    material_pitches: List[int],
    focus_card_ids: List[int],
    pitch_focus_stats: Dict[Tuple[int, int], Tuple[float, Optional[datetime]]],
    user_range_center: int,
    config: EngineConfig = None
) -> List[FocusTarget]:
    """
    Select pitch/focus combinations to emphasize in this material.
    
    Returns top FOCUS_TARGETS_PER_MATERIAL by score.
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    now = datetime.now()
    
    # Score all pitch/focus combinations
    candidates = []
    for pitch in material_pitches:
        for focus_id in focus_card_ids:
            key = (pitch, focus_id)
            ema, last_attempt = pitch_focus_stats.get(key, (0.0, None))
            
            score = compute_focus_score(
                pitch, ema, last_attempt, user_range_center, now, config
            )
            
            candidates.append(FocusTarget(
                pitch_midi=pitch,
                focus_card_id=focus_id,
                ema_score=ema,
                score=score
            ))
    
    # Sort by score (descending) and return top N
    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates[:config.focus_targets_per_material]


# =============================================================================
# ATTEMPT COMPLETION UPDATES
# =============================================================================

@dataclass
class AttemptResult:
    """Result of processing a practice attempt."""
    new_ema: float
    new_attempt_count: int
    new_status: MaterialStatus
    capability_evidence_added: List[int] = field(default_factory=list)
    capabilities_mastered: List[int] = field(default_factory=list)


def process_attempt(
    rating: int,
    material_state: MaterialCandidate,
    teaches_capability_ids: List[int],
    capability_progress: Dict[int, CapabilityProgress],
    is_off_course: bool = False,
    config: EngineConfig = None
) -> AttemptResult:
    """
    Process a practice attempt and return updates.
    
    Updates:
    1. Material EMA and attempt count
    2. Material status
    3. Capability evidence (if not off-course)
    4. Capability mastery
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    # Update EMA
    new_ema = compute_ema(float(rating), material_state.ema_score, config=config)
    new_attempt_count = material_state.attempt_count + 1
    
    # Update status
    if check_material_mastery(new_ema, new_attempt_count, config):
        new_status = MaterialStatus.MASTERED
    elif new_attempt_count > 0:
        new_status = MaterialStatus.IN_PROGRESS
    else:
        new_status = MaterialStatus.UNEXPLORED
    
    result = AttemptResult(
        new_ema=new_ema,
        new_attempt_count=new_attempt_count,
        new_status=new_status
    )
    
    # Update capability evidence (only if not off-course)
    if not is_off_course:
        for cap_id in teaches_capability_ids:
            cp = capability_progress.get(cap_id)
            if cp and not cp.is_mastered:
                # Check if rating meets acceptance threshold
                # (Using default threshold of 4 if not specified)
                if rating >= 4:
                    result.capability_evidence_added.append(cap_id)
                    
                    # Check if this tips the capability to mastered
                    new_evidence = cp.evidence_count + 1
                    if new_evidence >= cp.required_count:
                        result.capabilities_mastered.append(cap_id)
    
    return result


def update_pitch_focus_stats(
    pitch_midi: int,
    focus_card_id: int,
    rating: int,
    current_ema: float,
    current_attempts: int,
    config: EngineConfig = None
) -> Tuple[float, int]:
    """
    Update pitch/focus stats after an attempt.
    
    Returns (new_ema, new_attempt_count).
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    new_ema = compute_ema(float(rating), current_ema, config=config)
    new_attempts = current_attempts + 1
    
    return new_ema, new_attempts


# =============================================================================
# DATABASE INTEGRATION HELPERS
# =============================================================================

def get_user_capability_masks(user) -> List[int]:
    """Extract capability masks from user object."""
    return [
        user.cap_mask_0 or 0,
        user.cap_mask_1 or 0,
        user.cap_mask_2 or 0,
        user.cap_mask_3 or 0,
        user.cap_mask_4 or 0,
        user.cap_mask_5 or 0,
        user.cap_mask_6 or 0,
        user.cap_mask_7 or 0,
    ]


def get_material_capability_masks(material) -> List[int]:
    """Extract capability masks from material object."""
    return [
        material.req_cap_mask_0 or 0,
        material.req_cap_mask_1 or 0,
        material.req_cap_mask_2 or 0,
        material.req_cap_mask_3 or 0,
        material.req_cap_mask_4 or 0,
        material.req_cap_mask_5 or 0,
        material.req_cap_mask_6 or 0,
        material.req_cap_mask_7 or 0,
    ]


def set_capability_bit(masks: List[int], bit_index: int) -> List[int]:
    """Set a capability bit in the mask list."""
    if bit_index < 0 or bit_index >= 512:
        return masks
    
    mask_idx = bit_index // 64
    bit_pos = bit_index % 64
    
    new_masks = masks.copy()
    new_masks[mask_idx] = new_masks[mask_idx] | (1 << bit_pos)
    return new_masks


def has_capability_bit(masks: List[int], bit_index: int) -> bool:
    """Check if a capability bit is set in the mask list."""
    if bit_index < 0 or bit_index >= 512:
        return False
    
    mask_idx = bit_index // 64
    bit_pos = bit_index % 64
    
    return (masks[mask_idx] & (1 << bit_pos)) != 0
