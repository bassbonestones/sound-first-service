"""Admin-related Pydantic models."""
from pydantic import BaseModel, field_validator, model_validator
from typing import List, Optional, Dict, Any
from typing_extensions import Self
from datetime import datetime


# ============ Request Models ============

class FocusCardCreate(BaseModel):
    name: str
    category: str = ""
    description: str = ""
    attention_cue: str = ""
    micro_cues: List[str] = []
    prompts: Dict[str, Any] = {}


class FocusCardUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    attention_cue: Optional[str] = None
    micro_cues: Optional[List[str]] = None
    prompts: Optional[Dict[str, Any]] = None


class SoftGateRuleUpdate(BaseModel):
    dimension_name: Optional[str] = None
    frontier_buffer: Optional[float] = None
    promotion_step: Optional[float] = None
    min_attempts: Optional[int] = None
    success_rating_threshold: Optional[int] = None
    success_required_count: Optional[int] = None
    success_window_count: Optional[int] = None
    decay_halflife_days: Optional[float] = None

    @field_validator("frontier_buffer", "promotion_step")
    @classmethod
    def validate_positive_float(cls, v: Optional[float]) -> Optional[float]:
        """Validate floats are positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("Value must be positive")
        return v

    @field_validator("min_attempts", "success_required_count", "success_window_count")
    @classmethod
    def validate_positive_int(cls, v: Optional[int]) -> Optional[int]:
        """Validate integers are positive if provided."""
        if v is not None and v < 1:
            raise ValueError("Value must be at least 1")
        return v

    @field_validator("success_rating_threshold")
    @classmethod
    def validate_rating_threshold(cls, v: Optional[int]) -> Optional[int]:
        """Validate rating threshold is between 1 and 5."""
        if v is not None and (v < 1 or v > 5):
            raise ValueError("success_rating_threshold must be between 1 and 5")
        return v

    @field_validator("decay_halflife_days")
    @classmethod
    def validate_halflife(cls, v: Optional[float]) -> Optional[float]:
        """Validate decay halflife is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("decay_halflife_days must be positive")
        return v


class SoftGateRuleCreate(BaseModel):
    dimension_name: str
    frontier_buffer: float
    promotion_step: float
    min_attempts: int
    success_rating_threshold: int = 4
    success_required_count: int
    success_window_count: Optional[int] = None
    decay_halflife_days: Optional[float] = None

    @field_validator("frontier_buffer", "promotion_step")
    @classmethod
    def validate_positive_float(cls, v: float) -> float:
        """Validate floats are positive."""
        if v <= 0:
            raise ValueError("Value must be positive")
        return v

    @field_validator("min_attempts", "success_required_count")
    @classmethod
    def validate_positive_int(cls, v: int) -> int:
        """Validate integers are positive."""
        if v < 1:
            raise ValueError("Value must be at least 1")
        return v

    @field_validator("success_window_count")
    @classmethod
    def validate_window_count(cls, v: Optional[int]) -> Optional[int]:
        """Validate window count is positive if provided."""
        if v is not None and v < 1:
            raise ValueError("success_window_count must be at least 1")
        return v

    @field_validator("success_rating_threshold")
    @classmethod
    def validate_rating_threshold(cls, v: int) -> int:
        """Validate rating threshold is between 1 and 5."""
        if v < 1 or v > 5:
            raise ValueError("success_rating_threshold must be between 1 and 5")
        return v

    @field_validator("decay_halflife_days")
    @classmethod
    def validate_halflife(cls, v: Optional[float]) -> Optional[float]:
        """Validate decay halflife is positive if provided."""
        if v is not None and v <= 0:
            raise ValueError("decay_halflife_days must be positive")
        return v

    @model_validator(mode="after")
    def validate_window_vs_required(self) -> Self:
        """Validate window count is at least as large as required count."""
        if self.success_window_count is not None:
            if self.success_window_count < self.success_required_count:
                raise ValueError("success_window_count must be >= success_required_count")
        return self


class UserSoftGateStateUpdate(BaseModel):
    comfortable_value: Optional[float] = None
    max_demonstrated_value: Optional[float] = None
    frontier_success_ema: Optional[float] = None
    frontier_attempt_count_since_last_promo: Optional[int] = None


class UserSoftGateStateReset(BaseModel):
    user_id: int
    dimension_names: Optional[List[str]] = None  # None = reset all dimensions


# ============ Response Models ============

class FocusCardResponse(BaseModel):
    """Focus card response."""
    id: int
    name: str
    category: str
    description: Optional[str] = None
    attention_cue: Optional[str] = None
    micro_cues: List[str] = []


class SoftGateRuleResponse(BaseModel):
    """Soft gate rule response."""
    id: int
    dimension_name: str
    frontier_buffer: float
    promotion_step: float
    min_attempts: int
    success_rating_threshold: int
    success_required_count: int
    success_window_count: Optional[int] = None
    decay_halflife_days: Optional[float] = None


class SoftGateStateResponse(BaseModel):
    """User soft gate state response."""
    dimension_name: str
    comfortable_value: float
    max_demonstrated_value: float
    frontier_success_ema: float
    frontier_attempt_count_since_last_promo: int


class MessageResponse(BaseModel):
    """Simple message response."""
    message: str


class SuccessResponse(BaseModel):
    """Success response with optional details."""
    success: bool
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


# ============ Soft Gate Additional Response Models ============

class UserListItem(BaseModel):
    """User item for dropdown selection."""
    id: int
    email: Optional[str]
    name: Optional[str] = None
    instrument: Optional[str]


class SoftGateStateDetailResponse(BaseModel):
    """Detailed user soft gate state response with ID and timestamp."""
    id: int
    user_id: int
    dimension_name: str
    comfortable_value: float
    max_demonstrated_value: float
    frontier_success_ema: float
    frontier_attempt_count_since_last_promo: int
    updated_at: Optional[str] = None
