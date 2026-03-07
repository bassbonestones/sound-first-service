"""
Engine models: enums and dataclasses for practice engine.
"""
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional


class MaterialStatus(Enum):
    """Material practice status."""
    UNEXPLORED = "unexplored"
    IN_PROGRESS = "in_progress"
    MASTERED = "mastered"


class MaterialShelf(Enum):
    """Material shelf assignment."""
    DEFAULT = "default"
    MAINTENANCE = "maintenance"
    ARCHIVE = "archive"


class Bucket(Enum):
    """Practice session bucket types."""
    NEW = "new"
    IN_PROGRESS = "in_progress"
    MAINTENANCE = "maintenance"


@dataclass
class MaterialCandidate:
    """
    A material being considered for practice.
    
    Includes practice history and unified scoring metadata (Phase 6).
    """
    material_id: int
    teaches_capabilities: List[int] = field(default_factory=list)
    difficulty_index: float = 0.0
    ema_score: float = 3.0  # Default middle of 1-5 scale
    attempt_count: int = 0
    status: MaterialStatus = MaterialStatus.UNEXPLORED
    shelf: MaterialShelf = MaterialShelf.DEFAULT
    last_attempt_at: Optional[datetime] = None
    # Unified scoring fields (Phase 6)
    overall_score: Optional[float] = None
    primary_scores: Dict[str, float] = field(default_factory=dict)
    hazard_scores: Dict[str, float] = field(default_factory=dict)
    hazard_flags: List[str] = field(default_factory=list)
    interaction_bonus: float = 0.0


@dataclass
class CapabilityProgress:
    """Tracks progress toward unlocking a capability."""
    capability_id: int
    evidence_count: int = 0
    required_count: int = 3
    is_mastered: bool = False
    difficulty_weight: float = 1.0
    
    @property
    def progress_ratio(self) -> float:
        """Progress toward mastery (0-1)."""
        if self.required_count == 0:
            return 1.0
        return min(1.0, self.evidence_count / self.required_count)


@dataclass
class FocusTarget:
    """A pitch/focus-card combination to emphasize."""
    pitch_midi: int
    focus_card_id: int
    ema_score: float = 0.0
    score: float = 0.0  # Computed targeting score


@dataclass
class SessionMaterial:
    """Selected material for a session with focus targets."""
    material_id: int
    bucket: Bucket
    focus_targets: List[FocusTarget] = field(default_factory=list)
    # Unified scoring hazard warnings (Phase 6)
    hazard_warnings: List[str] = field(default_factory=list)
    overall_score: Optional[float] = None
    interaction_bonus: float = 0.0


@dataclass
class AttemptResult:
    """Result of processing a practice attempt."""
    new_ema: float
    new_attempt_count: int
    new_status: MaterialStatus
    capability_evidence_added: List[int] = field(default_factory=list)
    capabilities_mastered: List[int] = field(default_factory=list)
