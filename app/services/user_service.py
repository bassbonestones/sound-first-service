"""
User service.

Handles business logic for user management, capability assignments, and journey tracking.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Tuple, Any
import datetime

from sqlalchemy.orm import Session as DbSession

from app.models.core import (
    User, Material, PracticeSession, MiniSession, 
    PracticeAttempt, CurriculumStep
)
from app.models.capability_schema import Capability, UserCapability, MaterialAnalysis, UserInstrument
from app.models.teaching_module import UserLessonProgress
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

# Mapping of semitones to range_span capability names
RANGE_SPAN_CAPS = {
    1: "range_span_minor_second",
    2: "range_span_major_second",
    3: "range_span_minor_third",
    4: "range_span_major_third",
    5: "range_span_perfect_fourth",
    6: "range_span_augmented_fourth",
    7: "range_span_perfect_fifth",
    8: "range_span_minor_sixth",
    9: "range_span_major_sixth",
    10: "range_span_minor_seventh",
    11: "range_span_major_seventh",
    12: "range_span_octave",
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
    metrics: Dict[str, Any]


class UserService:
    """Service for user-related business logic."""
    
    @classmethod
    def get_clef_capability(cls, instrument: Optional[str]) -> str:
        """Determine which clef capability based on instrument."""
        user_instrument = instrument or ""
        return "clef_bass" if user_instrument in BASS_CLEF_INSTRUMENTS else "clef_treble"
    
    @classmethod
    def grant_day0_capabilities(
        cls, 
        user: User, 
        db: DbSession, 
        instrument_id: Optional[int] = None,
        instrument_name: Optional[str] = None
    ) -> List[str]:
        """
        Grant all Day 0 capabilities to a user when they complete the first-note flow.
        
        For global capabilities (is_global=True): creates UserCapability with instrument_id=NULL
        if not already mastered. Skips if user already has a mastered global cap.
        
        For instrument-specific capabilities (is_global=False): creates UserCapability with
        the provided instrument_id.
        
        Args:
            user: The user
            db: Database session
            instrument_id: The UserInstrument.id for instrument-specific capabilities
            instrument_name: The instrument name (used to determine clef if not provided)
        
        Returns list of granted capability names.
        """
        # Determine clef capability based on instrument
        inst_name = instrument_name or str(user.instrument) if user.instrument else None
        clef_capability = cls.get_clef_capability(inst_name)
        capabilities_to_grant = DAY0_BASE_CAPABILITIES + [clef_capability]
        
        caps = db.query(Capability).filter(Capability.name.in_(capabilities_to_grant)).all()
        cap_map: Dict[str, Capability] = {str(c.name): c for c in caps}
        
        now = datetime.datetime.utcnow()
        granted = []
        
        for cap_name in capabilities_to_grant:
            cap = cap_map.get(cap_name)
            if not cap:
                continue
            
            # Determine if this capability is global or instrument-specific
            is_global = cap.is_global if cap.is_global is not None else True
            
            if is_global:
                # Global capability: look for existing record with instrument_id=NULL
                existing = db.query(UserCapability).filter(
                    UserCapability.user_id == user.id,
                    UserCapability.capability_id == cap.id,
                    UserCapability.instrument_id == None
                ).first()
                
                if existing:
                    # Already have this global cap - skip if mastered, otherwise master it
                    if not existing.mastered_at:
                        existing.mastered_at = now  # type: ignore[assignment]
                        existing.is_active = True  # type: ignore[assignment]
                        granted.append(cap_name)
                    # If already mastered, skip silently
                else:
                    # Create new global capability record (instrument_id=NULL)
                    user_cap = UserCapability(
                        user_id=user.id,
                        capability_id=cap.id,
                        instrument_id=None,  # Global cap
                        introduced_at=now,
                        mastered_at=now,
                        is_active=True,
                        evidence_count=1,
                    )
                    db.add(user_cap)
                    granted.append(cap_name)
            else:
                # Instrument-specific capability: look for existing record with matching instrument_id
                existing = db.query(UserCapability).filter(
                    UserCapability.user_id == user.id,
                    UserCapability.capability_id == cap.id,
                    UserCapability.instrument_id == instrument_id
                ).first()
                
                if existing:
                    if not existing.mastered_at:
                        existing.mastered_at = now  # type: ignore[assignment]
                        existing.is_active = True  # type: ignore[assignment]
                        granted.append(cap_name)
                else:
                    # Create new instrument-specific capability record
                    user_cap = UserCapability(
                        user_id=user.id,
                        capability_id=cap.id,
                        instrument_id=instrument_id,  # Tied to this instrument
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
            started_times = [s.started_at for s in sessions if s.started_at]
            first_session = min(started_times, default=None) if started_times else None  # type: ignore[type-var]
            if first_session:
                days_since_first = (datetime.datetime.now() - first_session).days
        
        # Average rating
        ratings = [float(a.rating) for a in attempts if a.rating is not None]
        avg_rating = sum(ratings) / len(ratings) if ratings else 0.0
        
        # Average fatigue
        fatigues = [float(a.fatigue) for a in attempts if a.fatigue is not None]
        avg_fatigue = sum(fatigues) / len(fatigues) if fatigues else 3.0
        
        # Build SR items for mastery counts
        materials = db.query(Material).all()
        attempt_history = cls._build_attempt_history(attempts)
        
        mastered_count = familiar_count = stabilizing_count = learning_count = 0
        
        for m in materials:
            mat_id = int(m.id)
            mat_attempts = attempt_history.get(mat_id, [])
            if not mat_attempts:
                continue
            sr_item = build_sr_item_from_db(mat_id, mat_attempts)
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
            factors=factors,  # type: ignore[arg-type]
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
        user.instrument = None  # type: ignore[assignment]
        user.resonant_note = None  # type: ignore[assignment]
        user.range_low = None  # type: ignore[assignment]
        user.range_high = None  # type: ignore[assignment]
        user.comfortable_capabilities = None  # type: ignore[assignment]
        user.max_melodic_interval = "M2"  # type: ignore[assignment]
        user.day0_completed = False  # type: ignore[assignment]
        user.day0_stage = 0  # type: ignore[assignment]
        
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
        
        # Delete user instruments
        db.query(UserInstrument).filter(UserInstrument.user_id == user_id).delete()
        
        # Delete teaching module progress
        db.query(UserLessonProgress).filter(UserLessonProgress.user_id == user_id).delete()
    
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
                existing.is_active = True  # type: ignore[assignment]
                existing.deactivated_at = None  # type: ignore[assignment]
                existing.mastered_at = datetime.datetime.now()  # type: ignore[assignment]
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
        cls._set_capability_bit(user, int(cap.bit_index) if cap.bit_index else None, True)
        
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
        
        existing.is_active = False  # type: ignore[assignment]
        existing.deactivated_at = datetime.datetime.now()  # type: ignore[assignment]
        
        # Update bitmask
        cls._set_capability_bit(user, int(cap.bit_index) if cap.bit_index else None, False)
        
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
    def _build_attempt_history(attempts: List[Any]) -> Dict[int, List[Dict[str, Any]]]:
        """Build attempt history dict from list of attempts."""
        history: Dict[int, List[Dict[str, Any]]] = {}
        for a in attempts:
            mat_id = int(a.material_id)
            if mat_id not in history:
                history[mat_id] = []
            history[mat_id].append({
                "rating": a.rating,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            })
        return history
    
    @classmethod
    def get_user_masks(cls, user: User) -> List[int]:
        """Get user's capability bitmasks."""
        return [getattr(user, attr) or 0 for attr in MASK_ATTRS]
    
    @classmethod
    def grant_range_span_capability(
        cls,
        db: DbSession,
        user_id: int,
        instrument_id: int,
        range_low: str,
        range_high: str
    ) -> List[str]:
        """
        Grant the range_span capability matching the user's current range span.
        
        Calculates the semitone span between range_low and range_high, and grants
        the corresponding range_span capability if not already mastered.
        
        Args:
            db: Database session
            user_id: User's ID
            instrument_id: UserInstrument's ID
            range_low: Low end of range (e.g., "C4")
            range_high: High end of range (e.g., "G4")
        
        Returns:
            List with the newly granted capability name, or empty list
        """
        from app.curriculum.utils import note_to_midi
        
        if not range_low or not range_high:
            return []
        
        try:
            low_midi = note_to_midi(range_low)
            high_midi = note_to_midi(range_high)
            span_semitones = high_midi - low_midi
        except (ValueError, KeyError):
            return []
        
        # Get the capability for this exact span
        cap_name = RANGE_SPAN_CAPS.get(span_semitones)
        if not cap_name:
            return []
        
        # Look up capability by name
        cap = db.query(Capability).filter(Capability.name == cap_name).first()
        if not cap:
            return []
        
        # Check if user already has this mastered for this instrument
        existing = db.query(UserCapability).filter(
            UserCapability.user_id == user_id,
            UserCapability.instrument_id == instrument_id,
            UserCapability.capability_id == cap.id,
            UserCapability.mastered_at != None
        ).first()
        
        if existing:
            return []  # Already mastered
        
        now = datetime.datetime.utcnow()
        
        # Check if user has this cap but not mastered
        user_cap = db.query(UserCapability).filter(
            UserCapability.user_id == user_id,
            UserCapability.instrument_id == instrument_id,
            UserCapability.capability_id == cap.id
        ).first()
        
        if user_cap:
            # Update to mastered
            user_cap.mastered_at = now  # type: ignore[assignment]
            user_cap.evidence_count = cap.evidence_required_count or 1  # type: ignore[assignment]
        else:
            # Create new mastered capability
            user_cap = UserCapability(
                user_id=user_id,
                capability_id=cap.id,
                instrument_id=instrument_id,
                is_active=True,
                introduced_at=now,
                mastered_at=now,
                evidence_count=cap.evidence_required_count or 1
            )
            db.add(user_cap)
        
        return [cap_name]


# Module-level singleton
_user_service = None


def get_user_service() -> UserService:
    """Get or create the user service singleton."""
    global _user_service
    if _user_service is None:
        _user_service = UserService()
    return _user_service
