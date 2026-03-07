"""
Practice Engine Database Service

This module provides database integration for the practice engine,
connecting the algorithm layer to SQLAlchemy models.
"""

import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import and_, func

from .models.core import (
    User, Material, FocusCard, PracticeAttempt, PracticeSession, MiniSession
)
from .models.capability_schema import (
    Capability, MaterialCapability, MaterialTeachesCapability,
    MaterialAnalysis, UserCapability, UserMaterialState,
    UserPitchFocusStats, UserCapabilityEvidenceEvent, UserLicense,
    UserSoftGateState, UserComplexityScores
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
    check_material_mastery, check_capability_mastery, set_capability_bit,
    get_hazard_warnings, check_unified_score_eligibility
)
from .scoring_functions import score_to_stage


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
            
            # Get analysis data including unified scores
            analysis = self.db.query(MaterialAnalysis).filter(
                MaterialAnalysis.material_id == s.material_id
            ).first()
            
            # Extract unified scoring data
            primary_scores = {}
            hazard_scores = {}
            hazard_flags = []
            overall_score = None
            interaction_bonus = 0.0
            difficulty_index = 0.5
            
            if analysis:
                difficulty_index = analysis.difficulty_index or 0.5
                overall_score = analysis.overall_score
                interaction_bonus = analysis.interaction_bonus or 0.0
                
                # Extract primary scores
                primary_scores = {
                    'interval': analysis.interval_primary_score,
                    'rhythm': analysis.rhythm_primary_score,
                    'tonal': analysis.tonal_primary_score,
                    'tempo': analysis.tempo_primary_score,
                    'range': analysis.range_primary_score,
                    'throughput': analysis.throughput_primary_score,
                }
                
                # Extract hazard scores from JSON analysis columns
                hazard_scores, hazard_flags = self._extract_hazard_data(analysis)
            
            result[s.material_id] = MaterialCandidate(
                material_id=s.material_id,
                teaches_capabilities=[t[0] for t in teaches],
                difficulty_index=difficulty_index,
                ema_score=s.ema_score or 0.0,
                attempt_count=s.attempt_count or 0,
                last_attempt_at=s.last_attempt_at,
                status=MaterialStatus(s.status) if s.status else MaterialStatus.UNEXPLORED,
                shelf=MaterialShelf(s.shelf) if s.shelf else MaterialShelf.DEFAULT,
                overall_score=overall_score,
                primary_scores=primary_scores,
                hazard_scores=hazard_scores,
                interaction_bonus=interaction_bonus,
                hazard_flags=hazard_flags,
            )
        
        return result
    
    def _extract_hazard_data(self, analysis: MaterialAnalysis) -> tuple:
        """Extract hazard scores and flags from analysis JSON columns."""
        hazard_scores = {}
        hazard_flags = []
        
        # Domain JSON column mapping
        domain_columns = [
            ('interval', analysis.interval_analysis_json),
            ('rhythm', analysis.rhythm_analysis_json),
            ('tonal', analysis.tonal_analysis_json),
            ('tempo', analysis.tempo_analysis_json),
            ('range', analysis.range_analysis_json),
            ('throughput', analysis.throughput_analysis_json),
        ]
        
        for domain, json_str in domain_columns:
            if not json_str:
                continue
            try:
                data = json.loads(json_str)
                # Extract hazard score
                scores = data.get('scores', {})
                hazard_scores[domain] = scores.get('hazard')
                
                # Extract flags
                flags = data.get('flags', [])
                for flag in flags:
                    hazard_flags.append(f"{domain}:{flag}")
            except (json.JSONDecodeError, TypeError):
                continue
        
        return hazard_scores, hazard_flags
    
    def get_capability_progress(self, user_id: int) -> List[CapabilityProgress]:
        """Load capability progress for a user."""
        # Get all capabilities with evidence profiles
        capabilities = self.db.query(Capability).all()
        
        # Get user's capability states
        user_caps = self.db.query(UserCapability).filter(
            UserCapability.user_id == user_id
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
    
    def get_user_ability_scores(self, user_id: int) -> Dict[str, float]:
        """
        Get user's unified ability scores for eligibility checking.
        
        Returns a dict mapping domain name to ability score (0.0-1.0).
        """
        scores = self.db.query(UserComplexityScores).filter(
            UserComplexityScores.user_id == user_id
        ).first()
        
        if not scores:
            # Return zeros for new users
            return {
                'interval': 0.0,
                'rhythm': 0.0,
                'tonal': 0.0,
                'tempo': 0.0,
                'range': 0.0,
                'throughput': 0.0,
            }
        
        return {
            'interval': scores.interval_ability_score or 0.0,
            'rhythm': scores.rhythm_ability_score or 0.0,
            'tonal': scores.tonal_ability_score or 0.0,
            'tempo': scores.tempo_ability_score or 0.0,
            'range': scores.range_ability_score or 0.0,
            'throughput': scores.throughput_ability_score or 0.0,
        }
    
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
            
            # Apply unified score eligibility filter (Phase 7)
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
        
        # Detect material mastery transition
        was_mastered = (candidate.status == MaterialStatus.MASTERED)
        is_now_mastered = (result.new_status == MaterialStatus.MASTERED)
        material_newly_mastered = is_now_mastered and not was_mastered
        
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
            user_cap = self.db.query(UserCapability).filter(
                and_(
                    UserCapability.user_id == user_id,
                    UserCapability.capability_id == cap_id
                )
            ).first()
            
            if user_cap:
                user_cap.evidence_count = (user_cap.evidence_count or 0) + 1
        
        # Update capability mastery
        for cap_id in result.capabilities_mastered:
            cap = self.db.query(Capability).get(cap_id)
            if not cap:
                continue
            
            # Check soft gate requirements before granting mastery
            # Evidence accumulates regardless, but mastery requires meeting soft gate thresholds
            if not self._check_soft_gate_requirements(user_id, cap):
                continue
            
            user_cap = self.db.query(UserCapability).filter(
                and_(
                    UserCapability.user_id == user_id,
                    UserCapability.capability_id == cap_id
                )
            ).first()
            
            if user_cap and not user_cap.mastered_at:
                user_cap.mastered_at = now
                
                # Update user's capability bitmask
                if cap.bit_index is not None:
                    self._set_user_capability_bit(user_id, cap.bit_index)
        
        # Update user ability scores if material newly mastered (Phase 7)
        if material_newly_mastered:
            self._update_user_ability_scores(user_id, material_id)
        
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
    
    def _check_soft_gate_requirements(self, user_id: int, capability: Capability) -> bool:
        """
        Check if user meets soft gate requirements for a capability.
        
        Returns True if:
        - Capability has no soft_gate_requirements, OR
        - User's comfortable_value >= threshold for ALL required dimensions
        
        This is a hard gate (no frontier buffer) - user must have already
        promoted their comfort zone to the required level.
        """
        if not capability.soft_gate_requirements:
            return True
        
        try:
            requirements = json.loads(capability.soft_gate_requirements)
            if not isinstance(requirements, dict):
                return True
        except (json.JSONDecodeError, TypeError):
            return True
        
        for dimension_name, threshold in requirements.items():
            state = self.db.query(UserSoftGateState).filter(
                and_(
                    UserSoftGateState.user_id == user_id,
                    UserSoftGateState.dimension_name == dimension_name
                )
            ).first()
            
            comfortable_value = state.comfortable_value if state else 0.0
            if comfortable_value < threshold:
                return False
        
        return True

    def _update_user_ability_scores(self, user_id: int, material_id: int):
        """
        Update user's unified ability scores when a material is mastered.
        
        For each domain, updates the user's ability score to:
            max(current_ability, material_primary_score)
        
        Also updates the derived stage columns.
        """
        # Get material analysis
        analysis = self.db.query(MaterialAnalysis).filter(
            MaterialAnalysis.material_id == material_id
        ).first()
        
        if not analysis:
            return
        
        # Get or create user complexity scores
        scores = self.db.query(UserComplexityScores).filter(
            UserComplexityScores.user_id == user_id
        ).first()
        
        if not scores:
            scores = UserComplexityScores(user_id=user_id)
            self.db.add(scores)
        
        # Domain mapping: (analysis_column, ability_column, stage_column)
        domains = [
            (analysis.interval_primary_score, 'interval_ability_score', 'interval_demonstrated_stage'),
            (analysis.rhythm_primary_score, 'rhythm_ability_score', 'rhythm_demonstrated_stage'),
            (analysis.tonal_primary_score, 'tonal_ability_score', 'tonal_demonstrated_stage'),
            (analysis.tempo_primary_score, 'tempo_ability_score', 'tempo_demonstrated_stage'),
            (analysis.range_primary_score, 'range_ability_score', 'range_demonstrated_stage'),
            (analysis.throughput_primary_score, 'throughput_ability_score', 'throughput_demonstrated_stage'),
        ]
        
        for material_score, ability_col, stage_col in domains:
            if material_score is None:
                continue
            
            current_ability = getattr(scores, ability_col) or 0.0
            new_ability = max(current_ability, material_score)
            
            if new_ability > current_ability:
                setattr(scores, ability_col, new_ability)
                setattr(scores, stage_col, score_to_stage(new_ability))
        
        scores.updated_at = datetime.now()

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
