"""Admin-related Pydantic models."""
from pydantic import BaseModel
from typing import List, Optional


class FocusCardCreate(BaseModel):
    name: str
    category: str = ""
    description: str = ""
    attention_cue: str = ""
    micro_cues: List[str] = []
    prompts: dict = {}


class FocusCardUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    attention_cue: Optional[str] = None
    micro_cues: Optional[List[str]] = None
    prompts: Optional[dict] = None


class SoftGateRuleUpdate(BaseModel):
    dimension_name: Optional[str] = None
    frontier_buffer: Optional[float] = None
    promotion_step: Optional[float] = None
    min_attempts: Optional[int] = None
    success_rating_threshold: Optional[int] = None
    success_required_count: Optional[int] = None
    success_window_count: Optional[int] = None
    decay_halflife_days: Optional[float] = None


class SoftGateRuleCreate(BaseModel):
    dimension_name: str
    frontier_buffer: float
    promotion_step: float
    min_attempts: int
    success_rating_threshold: int = 4
    success_required_count: int
    success_window_count: Optional[int] = None
    decay_halflife_days: Optional[float] = None


class UserSoftGateStateUpdate(BaseModel):
    comfortable_value: Optional[float] = None
    max_demonstrated_value: Optional[float] = None
    frontier_success_ema: Optional[float] = None
    frontier_attempt_count_since_last_promo: Optional[int] = None


class UserSoftGateStateReset(BaseModel):
    user_id: int
    dimension_names: Optional[List[str]] = None  # None = reset all dimensions
