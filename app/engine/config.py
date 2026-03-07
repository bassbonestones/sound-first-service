"""
Engine configuration: EngineConfig dataclass and defaults.
"""
from dataclasses import dataclass


@dataclass
class EngineConfig:
    """
    Configuration parameters for the practice engine.
    
    Centralizes all tunable weights, thresholds, and parameters
    to avoid magic numbers scattered through the codebase.
    """
    # EMA parameters
    ema_alpha: float = 0.3  # Weight for new data in EMA
    
    # Mastery thresholds
    mastery_threshold: float = 4.0  # EMA threshold for mastery (1-5 scale)
    min_attempts_for_mastery: int = 5  # Minimum attempts before mastery possible
    
    # Candidate pool parameters
    candidates_per_capability: int = 10  # Materials to sample per target capability
    max_candidates_pool: int = 50  # Max total candidates to score
    target_capability_count: int = 3  # Target capabilities per session
    
    # Bucket parameters
    min_bucket_new: float = 0.10  # Minimum weight for NEW bucket
    min_bucket_in_progress: float = 0.20  # Minimum weight for IN_PROGRESS bucket
    min_bucket_maintenance: float = 0.05  # Minimum weight for MAINTENANCE bucket
    
    # Maturity parameters
    maturity_cap_weight: float = 0.6  # Weight for capability maturity
    maturity_mat_weight: float = 0.4  # Weight for material maturity
    
    # Fatigue parameters
    fatigue_tau_days: float = 3.0  # Time constant for fatigue decay (days)
    
    # Focus targeting
    focus_targets_per_material: int = 3  # Max focus targets per material
    avoid_extremes_factor: float = 0.5  # Penalty for extreme pitches
    
    # Unified scoring parameters (Phase 6)
    use_unified_score_eligibility: bool = True  # Use unified scores for eligibility
    max_primary_score_delta: float = 0.3  # Max allowed primary score delta
    max_hazard_score: float = 0.7  # Max allowed hazard score (blocking)
    hazard_tolerance_maintenance: float = 0.9  # Relaxed hazard cap for maintenance
    
    # Unified scoring ranking weights (Phase 6)
    ranking_overall_score_weight: float = 0.2  # Weight for overall score match
    ranking_interaction_bonus_weight: float = 0.1  # Weight for interaction bonus


# Default configuration instance
DEFAULT_CONFIG = EngineConfig()
