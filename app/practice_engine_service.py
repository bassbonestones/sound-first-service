"""
Practice Engine Database Service

This module provides database integration for the practice engine,
connecting the algorithm layer to SQLAlchemy models.
"""

from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from .models.core import (
    User, Material, FocusCard, PracticeAttempt, PracticeSession, MiniSession
)
from .models.capability_schema import (
    CapabilityV2, MaterialCapability, MaterialTeachesCapability,
    MaterialAnalysis, UserCapabilityV2, UserMaterialState,
    UserPitchFocusStats, UserCapabilityEvidenceEvent, UserLicense
)
from .practice_engine import (
    EngineConfig, DEFAULT_CONFIG, MaterialCandidate, CapabilityProgress,
    MaterialStatus, MaterialShelf, Bucket, SessionMaterial, FocusTarget,
    AttemptResult,
    get_user_capability_masks, get_material_capability_masks,
    compute_combined_maturity, compute_capability_maturity, compute_material_maturity,
    select_target_capabilities, build_candidate_pool, compute_bucket_weights,
    sample_bucket, filter_candidates_by_bucket, rank_candidates,
    select_focus_targets, process_attempt, compute_ema,
    check_material_mastery, check_capability_mastery, set_capability_bit
)


class PracticeEngineService:
    """Database-integrated practice engine service."""
    
    def __init__(self, db: Session, config: EngineConfig = None):
        self.db = db
        self.config = config or DEFAULT_CONFIG
    
    # =========================================================================
    # DATA LOADING
    # =========================================================================
    
    def get_user_material_states(self, user_id: int) -> Dict[int, MaterialCandidate]:
        """Load all material states for a user."""
        states = self.db.query(UserMaterialState).filter(
            UserMaterialState.user_id == user_id
        ).all()
        
        result = {}
        for s in states:
            # Get teaches capabilities for this material
            teaches = self.db.query(MaterialTeachesCapability.capability_id).filter(
                MaterialTeachesCapability.material_id == s.material_id
            ).all()
            
            # Get difficulty index from analysis
            analysis = self.db.query(MaterialAnalysis).filter(
                MaterialAnalysis.material_id == s.material_id
            ).first()
            
            result[s.material_id] = MaterialCandidate(
                material_id=s.material_id,
                teaches_capabilities=[t[0] for t in teaches],
                difficulty_index=analysis.difficulty_index if analysis and analysis.difficulty_index else 0.5,
                ema_score=s.ema_score or 0.0,
                attempt_count=s.attempt_count or 0,
                last_attempt_at=s.last_attempt_at,
                status=MaterialStatus(s.status) if s.status else MaterialStatus.UNEXPLORED,
                shelf=MaterialShelf(s.shelf) if s.shelf else MaterialShelf.DEFAULT,
            )
        
        return result
    
    def get_capability_progress(self, user_id: int) -> List[CapabilityProgress]:
        """Load capability progress for a user."""
        # Get all capabilities with evidence profiles
        capabilities = self.db.query(CapabilityV2).all()
        
        # Get user's capability states
        user_caps = self.db.query(UserCapabilityV2).filter(
            UserCapabilityV2.user_id == user_id
        ).all()
        user_cap_map = {uc.capability_id: uc for uc in user_caps}
        
        result = []
        for cap in capabilities:
            uc = user_cap_map.get(cap.id)
            
            result.append(CapabilityProgress(
                capability_id=cap.id,
                evidence_count=uc.evidence_count if uc else 0,
                required_count=cap.evidence_required_count or 1,
                is_mastered=uc.mastered_at is not None if uc else False,
                difficulty_weight=cap.difficulty_weight or 1.0,
            ))
        
        return result
    
    def get_materials_by_teaches(self) -> Dict[int, List[int]]:
        """Build index of materials by capability they teach."""
        teaches = self.db.query(MaterialTeachesCapability).all()
        
        result: Dict[int, List[int]] = {}
        for t in teaches:
            if t.capability_id not in result:
                result[t.capability_id] = []
            result[t.capability_id].append(t.material_id)
        
        return result
    
    def get_pitch_focus_stats(
        self, 
        user_id: int, 
        material_id: Optional[int] = None
    ) -> Dict[Tuple[int, int], Tuple[float, Optional[datetime]]]:
        """Load pitch/focus stats for a user."""
        query = self.db.query(UserPitchFocusStats).filter(
            UserPitchFocusStats.user_id == user_id
        )
        
        if material_id:
            query = query.filter(
                and_(
                    UserPitchFocusStats.context_type == 'MATERIAL',
                    UserPitchFocusStats.context_id == material_id
                )
            )
        else:
            query = query.filter(UserPitchFocusStats.context_type == 'GLOBAL')
        
        stats = query.all()
        
        return {
            (s.pitch_midi, s.focus_card_id): (s.ema_score or 0.0, s.last_attempt_at)
            for s in stats
        }
    
    def get_focus_card_ids(self) -> List[int]:
        """Get all focus card IDs."""
        cards = self.db.query(FocusCard.id).all()
        return [c[0] for c in cards]
    
    # =========================================================================
    # MATURITY CALCULATION
    # =========================================================================
    
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
    
    # =========================================================================
    # MATERIAL SELECTION
    # =========================================================================
    
    def select_next_material(self, user_id: int) -> Optional[SessionMaterial]:
        """Select the next material for a practice session."""
        user = self.db.query(User).get(user_id)
        if not user:
            return None
        
        user_masks = get_user_capability_masks(user)
        cap_progress = self.get_capability_progress(user_id)
        materials_by_teaches = self.get_materials_by_teaches()
        material_states = self.get_user_material_states(user_id)
        maturity = self.compute_user_maturity(user_id)
        
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
            
            if candidates:
                ranked = rank_candidates(candidates, bucket, cap_progress_dict, now, self.config)
                if ranked:
                    return SessionMaterial(
                        material_id=ranked[0].material_id,
                        bucket=bucket
                    )
        
        # Fallback
        if pool:
            return SessionMaterial(
                material_id=pool[0].material_id,
                bucket=Bucket.IN_PROGRESS
            )
        
        return None
    
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
        
        # For now, generate pitches from range (later: extract from MusicXML)
        if analysis and analysis.lowest_pitch and analysis.highest_pitch:
            # Convert pitch names to MIDI (simplified)
            low_midi = self._pitch_name_to_midi(analysis.lowest_pitch)
            high_midi = self._pitch_name_to_midi(analysis.highest_pitch)
            material_pitches = list(range(low_midi, high_midi + 1))
        else:
            # Default range
            material_pitches = list(range(48, 72))  # C3 to C5
        
        # Get user's range center
        user = self.db.query(User).get(user_id)
        if user and user.range_low and user.range_high:
            low = self._pitch_name_to_midi(user.range_low)
            high = self._pitch_name_to_midi(user.range_high)
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
    
    # =========================================================================
    # ATTEMPT PROCESSING
    # =========================================================================
    
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
        
        This is the main entry point for processing attempts.
        """
        now = datetime.now()
        
        # Get or create material state
        state = self.db.query(UserMaterialState).filter(
            and_(
                UserMaterialState.user_id == user_id,
                UserMaterialState.material_id == material_id
            )
        ).first()
        
        if not state:
            state = UserMaterialState(
                user_id=user_id,
                material_id=material_id,
                ema_score=0.0,
                attempt_count=0,
                status='UNEXPLORED',
                shelf='DEFAULT'
            )
            self.db.add(state)
        
        # Get teaches capabilities
        teaches = self.db.query(MaterialTeachesCapability.capability_id).filter(
            MaterialTeachesCapability.material_id == material_id
        ).all()
        teaches_ids = [t[0] for t in teaches]
        
        # Get capability progress
        cap_progress = {
            cp.capability_id: cp 
            for cp in self.get_capability_progress(user_id)
        }
        
        # Create MaterialCandidate for processing
        candidate = MaterialCandidate(
            material_id=material_id,
            ema_score=state.ema_score or 0.0,
            attempt_count=state.attempt_count or 0,
            status=MaterialStatus(state.status) if state.status else MaterialStatus.UNEXPLORED
        )
        
        # Process the attempt
        result = process_attempt(
            rating=rating,
            material_state=candidate,
            teaches_capability_ids=teaches_ids,
            capability_progress=cap_progress,
            is_off_course=is_off_course,
            config=self.config
        )
        
        # Update material state
        state.ema_score = result.new_ema
        state.attempt_count = result.new_attempt_count
        state.last_attempt_at = now
        state.status = result.new_status.value
        
        if is_off_course:
            state.manual_attempt_count = (state.manual_attempt_count or 0) + 1
        else:
            state.guided_attempt_count = (state.guided_attempt_count or 0) + 1
        
        # Record practice attempt
        attempt = PracticeAttempt(
            user_id=user_id,
            material_id=material_id,
            key=key,
            focus_card_id=focus_card_id,
            rating=rating,
            fatigue=fatigue,
            timestamp=now,
            is_off_course=is_off_course,
            was_eligible=not is_off_course
        )
        self.db.add(attempt)
        self.db.flush()  # Get attempt ID
        
        # Update capability evidence
        for cap_id in result.capability_evidence_added:
            event = UserCapabilityEvidenceEvent(
                user_id=user_id,
                capability_id=cap_id,
                material_id=material_id,
                practice_attempt_id=attempt.id,
                rating=rating,
                credited_at=now,
                is_off_course=is_off_course
            )
            self.db.add(event)
            
            # Update cached evidence count
            user_cap = self.db.query(UserCapabilityV2).filter(
                and_(
                    UserCapabilityV2.user_id == user_id,
                    UserCapabilityV2.capability_id == cap_id
                )
            ).first()
            
            if user_cap:
                user_cap.evidence_count = (user_cap.evidence_count or 0) + 1
        
        # Update capability mastery
        for cap_id in result.capabilities_mastered:
            user_cap = self.db.query(UserCapabilityV2).filter(
                and_(
                    UserCapabilityV2.user_id == user_id,
                    UserCapabilityV2.capability_id == cap_id
                )
            ).first()
            
            if user_cap and not user_cap.mastered_at:
                user_cap.mastered_at = now
                
                # Update user's capability bitmask
                cap = self.db.query(CapabilityV2).get(cap_id)
                if cap and cap.bit_index is not None:
                    self._set_user_capability_bit(user_id, cap.bit_index)
        
        # Update pitch/focus stats if provided
        if focus_card_id and pitch_midi:
            self._update_pitch_focus_stats(
                user_id, focus_card_id, pitch_midi, rating, material_id, now
            )
        
        self.db.commit()
        return result
    
    def _update_pitch_focus_stats(
        self,
        user_id: int,
        focus_card_id: int,
        pitch_midi: int,
        rating: int,
        material_id: int,
        now: datetime
    ):
        """Update pitch/focus stats for both GLOBAL and MATERIAL contexts."""
        for context_type, context_id in [('GLOBAL', None), ('MATERIAL', material_id)]:
            stat = self.db.query(UserPitchFocusStats).filter(
                and_(
                    UserPitchFocusStats.user_id == user_id,
                    UserPitchFocusStats.focus_card_id == focus_card_id,
                    UserPitchFocusStats.pitch_midi == pitch_midi,
                    UserPitchFocusStats.context_type == context_type,
                    UserPitchFocusStats.context_id == context_id
                )
            ).first()
            
            if not stat:
                stat = UserPitchFocusStats(
                    user_id=user_id,
                    focus_card_id=focus_card_id,
                    pitch_midi=pitch_midi,
                    context_type=context_type,
                    context_id=context_id,
                    ema_score=0.0,
                    attempt_count=0
                )
                self.db.add(stat)
            
            stat.ema_score = compute_ema(float(rating), stat.ema_score or 0.0, config=self.config)
            stat.attempt_count = (stat.attempt_count or 0) + 1
            stat.last_attempt_at = now
    
    def _set_user_capability_bit(self, user_id: int, bit_index: int):
        """Set a capability bit on the user's mask."""
        user = self.db.query(User).get(user_id)
        if not user:
            return
        
        mask_idx = bit_index // 64
        bit_pos = bit_index % 64
        
        mask_attrs = [
            'cap_mask_0', 'cap_mask_1', 'cap_mask_2', 'cap_mask_3',
            'cap_mask_4', 'cap_mask_5', 'cap_mask_6', 'cap_mask_7'
        ]
        
        if 0 <= mask_idx < len(mask_attrs):
            current = getattr(user, mask_attrs[mask_idx]) or 0
            setattr(user, mask_attrs[mask_idx], current | (1 << bit_pos))
    
    def _pitch_name_to_midi(self, pitch_name: str) -> int:
        """Convert pitch name like 'C4' to MIDI number."""
        if not pitch_name:
            return 60  # Default to middle C
        
        # Parse note and octave
        note_map = {
            'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11
        }
        
        pitch_name = pitch_name.upper().strip()
        
        # Handle accidentals
        note = pitch_name[0]
        idx = 1
        accidental = 0
        
        while idx < len(pitch_name) and pitch_name[idx] in '#bB':
            if pitch_name[idx] == '#':
                accidental += 1
            elif pitch_name[idx].lower() == 'b':
                accidental -= 1
            idx += 1
        
        # Parse octave
        try:
            octave = int(pitch_name[idx:])
        except:
            octave = 4  # Default
        
        base = note_map.get(note, 0)
        return (octave + 1) * 12 + base + accidental
