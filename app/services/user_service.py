"""
User service.

Handles business logic for user management, capability assignments, and journey tracking.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple
import datetime

from sqlalchemy.orm import Session as DbSession

from app.models.core import (
    User, Material, PracticeSession, MiniSession, 
    PracticeAttempt, CurriculumStep
)
from app.models.capability_schema import Capability, UserCapability, MaterialAnalysis
from app.models.teaching_module import UserLessonProgress, UserModuleProgress
from app.curriculum import JourneyMetrics, estimate_journey_stage
from app.spaced_repetition import build_sr_item_from_db, estimate_mastery_level


# --- Constants ---
DAY0_BASE_CAPABILITIES = [
    "staff_basics",
    "ledger_lines",
    "note_basics",
    "first_note",
    "accidental_raise_pitch",
    "accidental_lower_pitch",
]

BASS_CLEF_INSTRUMENTS = {
    "Tenor Trombone", "Bass Trombone", "Euphonium", "Tuba",
    "Bassoon", "Cello", "Double Bass", "Bass Voice",
    "trombone", "bass_trombone", "euphonium", "tuba",
    "bassoon", "cello", "double_bass", "bass_voice",
}

MASK_ATTRS = [
    'cap_mask_0', 'cap_mask_1', 'cap_mask_2', 'cap_mask_3',
    'cap_mask_4', 'cap_mask_5', 'cap_mask_6', 'cap_mask_7'
]


@dataclass
class JourneyStageResult:
    """Result from journey stage estimation."""
    stage: int
    stage_name: str
    factors: List[str]
    metrics: Dict


class UserService:
    """Service for user-related business logic."""
    
    @classmethod
    def get_clef_capability(cls, instrument: Optional[str]) -> str:
        """Determine which clef capability based on instrument."""
        user_instrument = instrument or ""
        return "clef_bass" if user_instrument in BASS_CLEF_INSTRUMENTS else "clef_treble"
    
    @classmethod
    def grant_day0_capabilities(cls, user: User, db: DbSession) -> List[str]:
        """
        Grant all Day 0 capabilities to a user when they complete the first-note flow.
        
        Returns list of granted capability names.
        """
        clef_capability = cls.get_clef_capability(user.instrument)
        capabilities_to_grant = DAY0_BASE_CAPABILITIES + [clef_capability]
        
        caps = db.query(Capability).filter(Capability.name.in_(capabilities_to_grant)).all()
        cap_map = {c.name: c for c in caps}
        
        now = datetime.datetime.utcnow()
        granted = []
        
        for cap_name in capabilities_to_grant:
            cap = cap_map.get(cap_name)
            if not cap:
                continue
            
            existing = db.query(UserCapability).filter_by(
                user_id=user.id,
                capability_id=cap.id
            ).first()
            
            if existing:
                if not existing.mastered_at:
                    existing.mastered_at = now
                    existing.is_active = True
                    granted.append(cap_name)
            else:
                user_cap = UserCapability(
                    user_id=user.id,
                    capability_id=cap.id,
                    introduced_at=now,
                    mastered_at=now,
                    is_active=True,
                    evidence_count=1,
                )
                db.add(user_cap)
                granted.append(cap_name)
        
        return granted
    
    @classmethod
    def build_journey_metrics(
        cls,
        user_id: int,
        db: DbSession
    ) -> JourneyMetrics:
        """Build journey metrics for a user from their practice history."""
        sessions = db.query(PracticeSession).filter_by(user_id=user_id).all()
        attempts = db.query(PracticeAttempt).filter_by(user_id=user_id).all()
        
        # Days since first session
        days_since_first = 0
        if sessions:
            first_session = min((s.started_at for s in sessions if s.started_at), default=None)
            if first_session:
                days_since_first = (datetime.datetime.now() - first_session).days
        
        # Average rating
        ratings = [a.rating for a in attempts if a.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        # Average fatigue
        fatigues = [a.fatigue for a in attempts if a.fatigue is not None]
        avg_fatigue = sum(fatigues) / len(fatigues) if fatigues else 3.0
        
        # Build SR items for mastery counts
        materials = db.query(Material).all()
        attempt_history = cls._build_attempt_history(attempts)
        
        mastered_count = familiar_count = stabilizing_count = learning_count = 0
        
        for m in materials:
            mat_attempts = attempt_history.get(m.id, [])
            if not mat_attempts:
                continue
            sr_item = build_sr_item_from_db(m.id, mat_attempts)
            mastery = estimate_mastery_level(sr_item)
            if mastery == "mastered":
                mastered_count += 1
            elif mastery == "familiar":
                familiar_count += 1
            elif mastery == "stabilizing":
                stabilizing_count += 1
            elif mastery in ("learning", "new"):
                learning_count += 1
        
        # Count unique keys
        mini_sessions = db.query(MiniSession).join(PracticeSession).filter(
            PracticeSession.user_id == user_id
        ).all()
        unique_keys = {ms.key for ms in mini_sessions if ms.key}
        
        # Count mastered capabilities
        cap_progress = db.query(UserCapability).filter(
            UserCapability.user_id == user_id,
            UserCapability.mastered_at.isnot(None)
        ).count()
        
        # Self-directed sessions
        self_directed_count = len([s for s in sessions if s.practice_mode == "self_directed"])
        
        return JourneyMetrics(
            total_sessions=len(sessions),
            total_attempts=len(attempts),
            days_since_first_session=days_since_first,
            average_rating=avg_rating,
            average_fatigue=avg_fatigue,
            mastered_count=mastered_count,
            familiar_count=familiar_count,
            stabilizing_count=stabilizing_count,
            learning_count=learning_count,
            unique_keys_practiced=len(unique_keys),
            capabilities_introduced=cap_progress,
            self_directed_sessions=self_directed_count,
        )
    
    @classmethod
    def estimate_journey_stage(cls, user_id: int, db: DbSession) -> JourneyStageResult:
        """Estimate user's journey stage based on practice history."""
        metrics = cls.build_journey_metrics(user_id, db)
        stage_num, stage_name, factors = estimate_journey_stage(metrics)
        
        return JourneyStageResult(
            stage=stage_num,
            stage_name=stage_name,
            factors=factors,
            metrics={
                "total_sessions": metrics.total_sessions,
                "total_attempts": metrics.total_attempts,
                "days_active": metrics.days_since_first_session,
                "average_rating": round(metrics.average_rating, 2),
                "mastered_count": metrics.mastered_count,
                "familiar_count": metrics.familiar_count,
                "stabilizing_count": metrics.stabilizing_count,
                "unique_keys": metrics.unique_keys_practiced,
                "capabilities_introduced": metrics.capabilities_introduced,
                "self_directed_sessions": metrics.self_directed_sessions,
            }
        )
    
    @classmethod
    def reset_user_data(cls, user: User, db: DbSession) -> None:
        """Reset all user data to start fresh."""
        user_id = user.id
        
        # Clear user profile data
        user.instrument = None
        user.resonant_note = None
        user.range_low = None
        user.range_high = None
        user.comfortable_capabilities = None
        user.max_melodic_interval = "M2"
        user.day0_completed = False
        user.day0_stage = 0
        
        # Reset capability bitmasks
        for attr in MASK_ATTRS:
            setattr(user, attr, 0)
        
        # Delete practice attempts
        db.query(PracticeAttempt).filter_by(user_id=user_id).delete()
        
        # Delete curriculum steps, mini-sessions, and sessions
        sessions = db.query(PracticeSession).filter_by(user_id=user_id).all()
        for session in sessions:
            mini_sessions = db.query(MiniSession).filter_by(practice_session_id=session.id).all()
            for ms in mini_sessions:
                db.query(CurriculumStep).filter_by(mini_session_id=ms.id).delete()
            db.query(MiniSession).filter_by(practice_session_id=session.id).delete()
        
        db.query(PracticeSession).filter_by(user_id=user_id).delete()
        
        # Delete user capabilities
        db.query(UserCapability).filter(UserCapability.user_id == user_id).delete()
        
        # Delete teaching module progress
        db.query(UserLessonProgress).filter(UserLessonProgress.user_id == user_id).delete()
        db.query(UserModuleProgress).filter(UserModuleProgress.user_id == user_id).delete()
    
    @classmethod
    def grant_capability(
        cls,
        user: User,
        cap: Capability,
        db: DbSession
    ) -> Tuple[bool, str]:
        """
        Grant a capability to a user.
        
        Returns (was_granted, message)
        """
        existing = db.query(UserCapability).filter_by(
            user_id=user.id, capability_id=cap.id
        ).first()
        
        if existing:
            if existing.is_active:
                return False, "Capability already granted"
            else:
                existing.is_active = True
                existing.deactivated_at = None
                existing.mastered_at = datetime.datetime.now()
        else:
            user_cap = UserCapability(
                user_id=user.id,
                capability_id=cap.id,
                introduced_at=datetime.datetime.now(),
                mastered_at=datetime.datetime.now(),
                is_active=True,
            )
            db.add(user_cap)
        
        # Update bitmask
        cls._set_capability_bit(user, cap.bit_index, True)
        
        return True, "Capability granted"
    
    @classmethod
    def revoke_capability(
        cls,
        user: User,
        cap: Capability,
        db: DbSession
    ) -> Tuple[bool, str]:
        """
        Revoke a capability from a user.
        
        Returns (was_revoked, message)
        """
        existing = db.query(UserCapability).filter_by(
            user_id=user.id, capability_id=cap.id
        ).first()
        
        if not existing or not existing.is_active:
            return False, "Capability not currently active"
        
        existing.is_active = False
        existing.deactivated_at = datetime.datetime.now()
        
        # Update bitmask
        cls._set_capability_bit(user, cap.bit_index, False)
        
        return True, "Capability revoked"
    
    @classmethod
    def _set_capability_bit(cls, user: User, bit_index: Optional[int], value: bool) -> None:
        """Set or clear a capability bit in the user's bitmask."""
        if bit_index is None:
            return
        
        bucket = bit_index // 64
        bit_position = bit_index % 64
        
        current_mask = getattr(user, MASK_ATTRS[bucket]) or 0
        
        if value:
            new_mask = current_mask | (1 << bit_position)
        else:
            new_mask = current_mask & ~(1 << bit_position)
        
        setattr(user, MASK_ATTRS[bucket], new_mask)
    
    @staticmethod
    def _build_attempt_history(attempts) -> Dict[int, List[Dict]]:
        """Build attempt history dict from list of attempts."""
        history = {}
        for a in attempts:
            if a.material_id not in history:
                history[a.material_id] = []
            history[a.material_id].append({
                "rating": a.rating,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            })
        return history
    
    @classmethod
    def get_user_masks(cls, user: User) -> List[int]:
        """Get user's capability bitmasks."""
        return [getattr(user, attr) or 0 for attr in MASK_ATTRS]


# Module-level singleton
_user_service = None


def get_user_service() -> UserService:
    """Get or create the user service singleton."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
