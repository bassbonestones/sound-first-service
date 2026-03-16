"""History and analytics response schemas."""
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from datetime import datetime


class SpacedRepetitionStats(BaseModel):
    """Spaced repetition statistics."""
    total_items: int
    due_today: int
    overdue: int
    never_reviewed: int
    avg_ease_factor: float
    short_interval_count: int
    medium_interval_count: int
    long_interval_count: int


class JourneyStage(BaseModel):
    """User journey stage info."""
    stage: int
    stage_name: str


class HistorySummaryResponse(BaseModel):
    """Response for /history/summary endpoint."""
    total_sessions: int
    total_attempts: int
    current_streak_days: int
    average_rating: float
    spaced_repetition: SpacedRepetitionStats
    journey_stage: JourneyStage


class MaterialHistoryItem(BaseModel):
    """Single material practice history."""
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


class TimelineDay(BaseModel):
    """Single day in practice timeline."""
    date: str
    attempts: int
    avg_rating: float
    avg_fatigue: float


class FocusCardHistoryItem(BaseModel):
    """Focus card practice statistics."""
    focus_card_id: int
    focus_card_name: str
    category: str
    attempt_count: int
    average_rating: Optional[float]
    best_rating: Optional[int]
    recent_trend: str


class DueItem(BaseModel):
    """Material due for review."""
    material_id: int
    material_title: str
    mastery_level: str
    days_overdue: float
    is_due: bool
    interval_days: int
    ease_factor: float


# Analytics schemas

class TimeStats(BaseModel):
    """Time-related statistics."""
    total_minutes: float
    total_sessions: int
    avg_session_minutes: float


class DomainStats(BaseModel):
    """Domain-specific capability stats."""
    introduced: int
    mastered: int
    refreshed: int


class CapabilityProgressStats(BaseModel):
    """Capability progress statistics."""
    total_introduced: int
    total_available: int
    total_mastered: int
    mastery_rate: float
    by_domain: Dict[str, Any]  # Dynamic domain keys


class RatingDistribution(BaseModel):
    """Rating distribution counts."""
    one: int = 0
    two: int = 0
    three: int = 0
    four: int = 0
    five: int = 0

    class Config:
        # Allow using int keys in serialization
        populate_by_name = True


class QualityMetrics(BaseModel):
    """Quality-related metrics."""
    overall_avg_rating: float
    recent_avg_rating: float
    rating_trend: str
    overall_avg_fatigue: float
    recent_avg_fatigue: float
    fatigue_trend: str
    strain_count: int
    strain_rate: float
    rating_distribution: Dict[Any, Any]  # Keys are 1-5


class CompletionStats(BaseModel):
    """Completion statistics."""
    completed_mini_sessions: int
    total_mini_sessions: int
    completion_rate: float


class PracticeByDayItem(BaseModel):
    """Practice stats for a day of week."""
    day: str
    sessions: int
    minutes: float


class SessionAnalyticsOut(BaseModel):
    """Comprehensive session history analytics."""
    time_stats: TimeStats
    capability_progress: CapabilityProgressStats
    quality_metrics: QualityMetrics
    completion_stats: CompletionStats
    practice_by_day: List[PracticeByDayItem]
