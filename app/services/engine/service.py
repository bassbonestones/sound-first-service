"""
Practice Engine Service

Database-integrated practice engine service that coordinates data loading,
material selection, and attempt processing.
"""

from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.core import User, Material, FocusCard
from app.models.capability_schema import (
    Capability, MaterialTeachesCapability, MaterialAnalysis,
    UserCapability, UserMaterialState
)
from app.practice_engine import (
    EngineConfig, DEFAULT_CONFIG, MaterialCandidate, CapabilityProgress,
    MaterialStatus, MaterialShelf, Bucket, SessionMaterial, FocusTarget,
    AttemptResult,
    get_user_capability_masks, get_material_capability_masks,
    compute_combined_maturity, compute_capability_maturity, compute_material_maturity,
    select_target_capabilities, build_candidate_pool, compute_bucket_weights,
    sample_bucket, filter_candidates_by_bucket, rank_candidates,
    select_focus_targets, process_attempt, compute_ema,
    get_hazard_warnings, check_unified_score_eligibility
)

from .data_loaders import (
    load_user_material_states,
    load_capability_progress,
    load_materials_by_teaches,
    load_user_ability_scores,
    load_pitch_focus_stats,
    load_focus_card_ids
)
from .attempt_handlers import (
    handle_record_attempt,
    pitch_name_to_midi
)


class PracticeEngineService:
    """
    Database-integrated practice engine.
    
    Wraps the pure-logic PracticeEngine with SQLAlchemy data access,
    providing a complete service for session generation and attempt tracking.
    """
    
    def __init__(self, db: Session, config: EngineConfig = None):
        """Initialize with database session and optional config."""
        self.db = db
        self.config = config or DEFAULT_CONFIG
    
    # ─────────────────────────────────────────────────────────────────────────────
    #  Data Loading (delegates to data_loaders module)
    # ─────────────────────────────────────────────────────────────────────────────
    
    def get_user_material_states(self, user_id: int) -> Dict[int, MaterialCandidate]:
        """Load all material states for a user."""
        return load_user_material_states(self.db, user_id)
    
    def get_capability_progress(self, user_id: int, instrument_id: int = None) -> List[CapabilityProgress]:
        """Load capability progress for a user.
        
        Args:
            user_id: User ID
            instrument_id: Optional instrument ID for instrument-specific capabilities
        """
        return load_capability_progress(self.db, user_id, instrument_id)
    
    def get_materials_by_teaches(self) -> Dict[int, List[int]]:
        """Build index of materials by capability they teach."""
        return load_materials_by_teaches(self.db)
    
    def get_user_ability_scores(self, user_id: int) -> Dict[str, float]:
        """Get user's unified ability scores for eligibility checking."""
        return load_user_ability_scores(self.db, user_id)
    
    def get_pitch_focus_stats(
        self,
        user_id: int,
        material_id: Optional[int] = None
    ) -> Dict[Tuple[int, int], Tuple[float, Optional[datetime]]]:
        """Load pitch/focus stats for a user."""
        return load_pitch_focus_stats(self.db, user_id, material_id)
    
    def get_focus_card_ids(self) -> List[int]:
        """Get all focus card IDs."""
        return load_focus_card_ids(self.db)
    
    # ─────────────────────────────────────────────────────────────────────────────
    #  User Maturity Computation
    # ─────────────────────────────────────────────────────────────────────────────
    
    def compute_user_maturity(self, user_id: int) -> float:
        """Compute combined maturity for a user."""
        cap_progress = self.get_capability_progress(user_id)
        mat_states = self.get_user_material_states(user_id)
        
        # Capability maturity
        mastered_cap_weight = sum(
            cp.difficulty_weight for cp in cap_progress if cp.is_mastered
        )
        total_cap_weight = sum(cp.difficulty_weight for cp in cap_progress)
        cap_maturity = compute_capability_maturity(mastered_cap_weight, total_cap_weight)
        
        # Material maturity (from eligible materials only)
        mastered_mat_diff = sum(
            m.difficulty_index for m in mat_states.values()
            if m.status == MaterialStatus.MASTERED
        )
        total_mat_diff = sum(m.difficulty_index for m in mat_states.values())
        mat_maturity = compute_material_maturity(mastered_mat_diff, total_mat_diff)
        
        return compute_combined_maturity(cap_maturity, mat_maturity, self.config)
    
    # ─────────────────────────────────────────────────────────────────────────────
    #  Material Selection
    # ─────────────────────────────────────────────────────────────────────────────
    
    def select_next_material(self, user_id: int, instrument_id: int = None) -> Optional[SessionMaterial]:
        """Select the next material for a practice session.
        
        Args:
            user_id: User ID
            instrument_id: Optional instrument ID for instrument-specific capability filtering
        """
        user = self.db.query(User).get(user_id)
        if not user:
            return None
        
        user_masks = get_user_capability_masks(user)
        cap_progress = self.get_capability_progress(user_id, instrument_id)
        materials_by_teaches = self.get_materials_by_teaches()
        material_states = self.get_user_material_states(user_id)
        maturity = self.compute_user_maturity(user_id)
        user_ability_scores = self.get_user_ability_scores(user_id)
        
        # Create mask lookup function
        material_masks_cache = {}
        def get_material_masks(material_id: int) -> List[int]:
            if material_id not in material_masks_cache:
                material = self.db.query(Material).get(material_id)
                if material:
                    material_masks_cache[material_id] = get_material_capability_masks(material)
                else:
                    material_masks_cache[material_id] = [0] * 8
            return material_masks_cache[material_id]
        
        # Convert cap_progress to dict for engine
        cap_progress_dict = {cp.capability_id: cp for cp in cap_progress}
        
        # Compute bucket weights
        bucket_weights = compute_bucket_weights(maturity, self.config)
        
        # Select target capabilities
        targets = select_target_capabilities(cap_progress, self.config)
        if not targets:
            return None
        
        # Build candidate pool
        pool = build_candidate_pool(
            targets,
            materials_by_teaches,
            material_states,
            user_masks,
            get_material_masks,
            self.config
        )
        
        if not pool:
            return None
        
        # Try buckets
        now = datetime.now()
        for _ in range(3):
            bucket = sample_bucket(bucket_weights)
            candidates = filter_candidates_by_bucket(pool, bucket)
            
            # Apply unified score eligibility filter
            if self.config.use_unified_score_eligibility:
                candidates = [
                    c for c in candidates
                    if check_unified_score_eligibility(c, user_ability_scores, bucket, self.config)[0]
                ]
            
            if candidates:
                ranked = rank_candidates(candidates, bucket, cap_progress_dict, now, self.config, maturity)
                if ranked:
                    selected = ranked[0]
                    return SessionMaterial(
                        material_id=selected.material_id,
                        bucket=bucket,
                        hazard_warnings=get_hazard_warnings(selected, self.config),
                        overall_score=selected.overall_score,
                        interaction_bonus=selected.interaction_bonus,
                    )
        
        # Fallback
        if pool:
            selected = pool[0]
            return SessionMaterial(
                material_id=selected.material_id,
                bucket=Bucket.IN_PROGRESS,
                hazard_warnings=get_hazard_warnings(selected, self.config),
                overall_score=selected.overall_score,
                interaction_bonus=selected.interaction_bonus,
            )
        
        return None
    
    # ─────────────────────────────────────────────────────────────────────────────
    #  Focus Target Selection
    # ─────────────────────────────────────────────────────────────────────────────
    
    def select_focus_targets_for_material(
        self,
        user_id: int,
        material_id: int
    ) -> List[FocusTarget]:
        """Select focus targets for a selected material."""
        # Get material pitches from analysis
        analysis = self.db.query(MaterialAnalysis).filter(
            MaterialAnalysis.material_id == material_id
        ).first()
        
        # Generate pitches from range
        if analysis and analysis.lowest_pitch and analysis.highest_pitch:
            low_midi = pitch_name_to_midi(analysis.lowest_pitch)
            high_midi = pitch_name_to_midi(analysis.highest_pitch)
            material_pitches = list(range(low_midi, high_midi + 1))
        else:
            # Default range
            material_pitches = list(range(48, 72))  # C3 to C5
        
        # Get user's range center
        user = self.db.query(User).get(user_id)
        if user and user.range_low and user.range_high:
            low = pitch_name_to_midi(user.range_low)
            high = pitch_name_to_midi(user.range_high)
            user_range_center = (low + high) // 2
        else:
            user_range_center = 60  # Middle C
        
        # Get focus cards
        focus_card_ids = self.get_focus_card_ids()
        if not focus_card_ids:
            focus_card_ids = [1, 2, 3]  # Default IDs
        
        # Get pitch/focus stats
        pitch_focus_stats = self.get_pitch_focus_stats(user_id, material_id)
        
        return select_focus_targets(
            material_pitches,
            focus_card_ids,
            pitch_focus_stats,
            user_range_center,
            self.config
        )
    
    # ─────────────────────────────────────────────────────────────────────────────
    #  Attempt Recording (delegates to attempt_handlers module)
    # ─────────────────────────────────────────────────────────────────────────────
    
    def record_attempt(
        self,
        user_id: int,
        material_id: int,
        rating: int,
        focus_card_id: Optional[int] = None,
        pitch_midi: Optional[int] = None,
        is_off_course: bool = False,
        key: Optional[str] = None,
        fatigue: Optional[int] = None
    ) -> AttemptResult:
        """
        Record a practice attempt and update all relevant stats.
        """
        cap_progress = self.get_capability_progress(user_id)
        cap_progress_dict = {cp.capability_id: cp for cp in cap_progress}
        
        result = handle_record_attempt(
            db=self.db,
            config=self.config,
            user_id=user_id,
            material_id=material_id,
            rating=rating,
            cap_progress_dict=cap_progress_dict,
            focus_card_id=focus_card_id,
            pitch_midi=pitch_midi,
            is_off_course=is_off_course,
            key=key,
            fatigue=fatigue
        )
        
        self.db.commit()
        return result
