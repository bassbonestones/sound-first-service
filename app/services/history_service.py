"""
History service.

Handles business logic for practice history, analytics, and spaced repetition tracking.
"""
from dataclasses import dataclass
from typing import Dict, List, Any, Optional, cast
import datetime

from sqlalchemy.orm import Session as DbSession

from app.models.core import Material, FocusCard, PracticeSession, PracticeAttempt
from app.models.capability_schema import Capability, UserCapability
from app.services.spaced_repetition import (
    build_sr_item_from_db,
    get_review_stats,
    estimate_mastery_level,
    SpacedRepetitionItem,
)


@dataclass
class HistorySummary:
    """Summary of user's practice history."""
    total_sessions: int
    total_attempts: int
    current_streak_days: int
    average_rating: float
    spaced_repetition: Dict[str, Any]
    journey_stage: Dict[str, Any]


@dataclass
class MaterialHistoryData:
    """History data for a single material."""
    material_id: int
    material_title: str
    attempt_count: int
    average_rating: Optional[float]
    last_practiced: Optional[str]
    mastery_level: str
    ease_factor: float
    interval_days: int
    next_review: Optional[str]
    is_due: bool


@dataclass
class TimelineDayData:
    """Practice data for a single day."""
    date: str
    attempts: int
    avg_rating: float
    avg_fatigue: float


@dataclass
class FocusCardHistoryData:
    """History data for a focus card."""
    focus_card_id: int
    focus_card_name: str
    category: str
    attempt_count: int
    average_rating: Optional[float]
    last_practiced: Optional[str]


class HistoryService:
    """Service for practice history and analytics."""
    
    @staticmethod
    def build_attempt_history(attempts: List[PracticeAttempt]) -> Dict[int, List[Dict[str, Any]]]:
        """
        Build attempt history dict from list of attempts.
        
        Groups attempts by material_id for efficient lookup.
        
        Args:
            attempts: List of PracticeAttempt records
            
        Returns:
            Dict mapping material_id to list of attempt details
        """
        history: Dict[int, List[Dict[str, Any]]] = {}
        for a in attempts:
            mat_id = int(a.material_id) if a.material_id else 0
            if mat_id not in history:
                history[mat_id] = []
            history[mat_id].append({
                "id": getattr(a, 'id', None),
                "rating": a.rating,
                "timestamp": a.timestamp,
                "fatigue": a.fatigue,
                "key": getattr(a, 'key', None),
            })
        return history
    
    @staticmethod
    def calculate_streak(sessions: List[PracticeSession]) -> int:
        """
        Calculate current practice streak in days.
        
        Counts consecutive days with practice sessions ending today.
        
        Args:
            sessions: List of PracticeSession records
            
        Returns:
            Number of consecutive practice days
        """
        if not sessions:
            return 0
        
        today = datetime.datetime.now().date()
        session_dates = {s.started_at.date() for s in sessions if s.started_at}
        
        streak = 0
        check_date = today
        while check_date in session_dates:
            streak += 1
            check_date -= datetime.timedelta(days=1)
        
        return streak
    
    @classmethod
    def build_sr_items_with_mastery(
        cls,
        materials: List[Material],
        attempt_history: Dict[int, List[Dict[str, Any]]]
    ) -> tuple[List[SpacedRepetitionItem], Dict[str, int]]:
        """
        Build spaced repetition items and calculate mastery counts.
        
        Args:
            materials: List of Material records
            attempt_history: Pre-built attempt history dict
            
        Returns:
            Tuple of (sr_items list, mastery_counts dict)
        """
        sr_items = []
        mastery_counts = {"mastered": 0, "familiar": 0, "stabilizing": 0, "learning": 0}
        
        for m in materials:
            m_id = int(m.id)
            mat_attempts = attempt_history.get(m_id, [])
            sr_data = [{"rating": a["rating"], "timestamp": a["timestamp"]} for a in mat_attempts]
            sr_item = build_sr_item_from_db(m_id, sr_data)
            sr_items.append(sr_item)
            
            if mat_attempts:
                mastery = estimate_mastery_level(sr_item)
                if mastery in mastery_counts:
                    mastery_counts[mastery] += 1
                elif mastery == "new":
                    mastery_counts["learning"] += 1
        
        return sr_items, mastery_counts
    
    @classmethod
    def get_material_history(
        cls,
        materials: List[Material],
        attempt_history: Dict[int, List[Dict[str, Any]]]
    ) -> List[MaterialHistoryData]:
        """
        Get practice history for each material with mastery level.
        
        Args:
            materials: List of Material records
            attempt_history: Pre-built attempt history dict
            
        Returns:
            List of MaterialHistoryData, sorted by due status
        """
        result = []
        
        for m in materials:
            m_id = int(m.id)
            mat_attempts = attempt_history.get(m_id, [])
            sr_data = [{"rating": a["rating"], "timestamp": a["timestamp"]} for a in mat_attempts]
            sr_item = build_sr_item_from_db(m_id, sr_data)
            
            ratings = [a["rating"] for a in mat_attempts if a["rating"] is not None]
            avg_rating = sum(ratings) / len(ratings) if ratings else None
            last_practiced = max(
                (a["timestamp"] for a in mat_attempts if a["timestamp"]), 
                default=None
            )
            
            result.append(MaterialHistoryData(
                material_id=m_id,
                material_title=str(m.title),
                attempt_count=len(mat_attempts),
                average_rating=round(avg_rating, 2) if avg_rating else None,
                last_practiced=last_practiced.isoformat() if last_practiced else None,
                mastery_level=estimate_mastery_level(sr_item),
                ease_factor=round(sr_item.ease_factor, 2),
                interval_days=sr_item.interval,
                next_review=sr_item.next_review.isoformat() if sr_item.next_review else None,
                is_due=sr_item.is_due(),
            ))
        
        # Sort by due status (due first), then by next_review date
        result.sort(key=lambda x: (not x.is_due, x.next_review or "9999"))
        return result
    
    @classmethod
    def get_practice_timeline(
        cls,
        attempts: List[PracticeAttempt],
        days: int = 30
    ) -> List[TimelineDayData]:
        """
        Get practice activity over time for visualization.
        
        Args:
            attempts: List of PracticeAttempt records (filtered to date range)
            days: Not used directly - assumes attempts already filtered
            
        Returns:
            List of TimelineDayData sorted by date
        """
        daily_stats: Dict[str, Dict[str, Any]] = {}
        
        for a in attempts:
            if not a.timestamp:
                continue
            date_str = a.timestamp.date().isoformat()
            if date_str not in daily_stats:
                daily_stats[date_str] = {"attempts": 0, "total_rating": 0, "fatigue_sum": 0}
            daily_stats[date_str]["attempts"] += 1
            daily_stats[date_str]["total_rating"] += a.rating or 0
            daily_stats[date_str]["fatigue_sum"] += a.fatigue or 0
        
        return [
            TimelineDayData(
                date=date_str,
                attempts=stats["attempts"],
                avg_rating=round(stats["total_rating"] / stats["attempts"], 2) if stats["attempts"] else 0,
                avg_fatigue=round(stats["fatigue_sum"] / stats["attempts"], 2) if stats["attempts"] else 0,
            )
            for date_str, stats in sorted(daily_stats.items())
        ]
    
    @classmethod
    def get_focus_card_history(
        cls,
        attempts: List[PracticeAttempt],
        focus_cards: List[FocusCard]
    ) -> List[FocusCardHistoryData]:
        """
        Get practice history grouped by focus card.
        
        Args:
            attempts: List of PracticeAttempt records
            focus_cards: List of FocusCard records
            
        Returns:
            List of FocusCardHistoryData sorted by attempt count descending
        """
        fc_map: Dict[int, FocusCard] = {int(fc.id): fc for fc in focus_cards}
        fc_stats: Dict[int, Dict[str, Any]] = {}
        
        for a in attempts:
            fc_id = int(a.focus_card_id) if a.focus_card_id else 0
            if fc_id not in fc_stats:
                fc = fc_map.get(fc_id)
                fc_stats[fc_id] = {
                    "focus_card_id": fc_id,
                    "focus_card_name": str(fc.name) if fc else "Unknown",
                    "category": str(fc.category) if fc else "",
                    "ratings": [],
                    "timestamps": [],
                }
            fc_stats[fc_id]["ratings"].append(a.rating)
            if a.timestamp:
                fc_stats[fc_id]["timestamps"].append(a.timestamp)
        
        result = []
        for fc_id, stats in fc_stats.items():
            ratings = [r for r in stats["ratings"] if r is not None]
            avg_rating = sum(ratings) / len(ratings) if ratings else None
            last_practiced = max(stats["timestamps"]) if stats["timestamps"] else None
            
            result.append(FocusCardHistoryData(
                focus_card_id=stats["focus_card_id"],
                focus_card_name=stats["focus_card_name"],
                category=stats["category"],
                attempt_count=len(stats["ratings"]),
                average_rating=round(avg_rating, 2) if avg_rating else None,
                last_practiced=last_practiced.isoformat() if last_practiced else None,
            ))
        
        result.sort(key=lambda x: x.attempt_count, reverse=True)
        return result
    
    @classmethod
    def get_due_items(
        cls,
        materials: List[Material],
        attempt_history: Dict[int, List[Dict[str, Any]]],
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Get materials due for review.
        
        Args:
            materials: List of Material records
            attempt_history: Pre-built attempt history dict
            limit: Maximum number of items to return
            
        Returns:
            List of due items with SR data
        """
        due_items = []
        
        for m in materials:
            m_id = int(m.id)
            mat_attempts = attempt_history.get(m_id, [])
            sr_data = [{"rating": a["rating"], "timestamp": a["timestamp"]} for a in mat_attempts]
            sr_item = build_sr_item_from_db(m_id, sr_data)
            
            if sr_item.is_due():
                due_items.append({
                    "material_id": m_id,
                    "material_title": str(m.title),
                    "days_overdue": round(sr_item.days_overdue(), 1),
                    "ease_factor": round(sr_item.ease_factor, 2),
                    "interval_days": sr_item.interval,
                    "mastery_level": estimate_mastery_level(sr_item),
                })
        
        # Sort by most overdue first
        due_items.sort(key=lambda x: cast(float, x["days_overdue"]), reverse=True)
        return due_items[:limit]


# Module-level singleton
_history_service: Optional[HistoryService] = None


def get_history_service() -> HistoryService:
    """Get or create the history service singleton."""
    global _history_service
    if _history_service is None:
        _history_service = HistoryService()
    return _history_service
