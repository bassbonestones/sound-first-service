"""
Scoring Models — Type Definitions for Domain Scoring

Contains the canonical data structures for domain analysis results.
"""

from typing import Dict, Any, TypedDict, List
from dataclasses import dataclass, field


class DomainScores(TypedDict):
    """Summary scores for a domain."""
    primary: float   # Sustained difficulty signal
    hazard: float    # Extreme spikes
    overall: float   # Blended interpretation


class DomainBands(TypedDict):
    """Derived stage bands for a domain."""
    primary_stage: int
    hazard_stage: int
    overall_stage: int


@dataclass
class DomainResult:
    """
    Complete analysis result for a single domain.
    
    This is the canonical output structure for all domain scoring functions.
    """
    profile: Dict[str, Any] = field(default_factory=dict)
    facet_scores: Dict[str, float] = field(default_factory=dict)
    scores: DomainScores = field(default_factory=lambda: DomainScores(primary=0.0, hazard=0.0, overall=0.0))
    bands: DomainBands = field(default_factory=lambda: DomainBands(primary_stage=0, hazard_stage=0, overall_stage=0))
    flags: List[str] = field(default_factory=list)
    confidence: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'profile': self.profile,
            'facet_scores': self.facet_scores,
            'scores': dict(self.scores),
            'bands': dict(self.bands),
            'flags': self.flags,
            'confidence': self.confidence,
        }
