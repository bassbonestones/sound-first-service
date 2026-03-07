"""User-related Pydantic models."""
from pydantic import BaseModel
from typing import Optional


class UserUpdateIn(BaseModel):
    day0_completed: Optional[bool] = None
    day0_stage: Optional[int] = None
    range_low: Optional[str] = None
    range_high: Optional[str] = None


class UserRangeIn(BaseModel):
    range_low: str  # e.g., "E3"
    range_high: str  # e.g., "C6"


class ClientLogIn(BaseModel):
    event: str
    data: dict
    timestamp: Optional[str] = None


class ConfigUpdateIn(BaseModel):
    capability_weights: Optional[dict] = None
    difficulty_weights: Optional[dict] = None
    novelty_reinforcement: Optional[dict] = None


class QuizResultIn(BaseModel):
    user_id: int
    passed: bool
    answer_given: Optional[str] = None
