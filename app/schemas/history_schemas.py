"""History and analytics response schemas."""
from pydantic import BaseModel
from typing import List, Optional
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
