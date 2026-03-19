"""
Main tempo analysis API.

Provides convenience functions for complete tempo analysis.
"""

from __future__ import annotations

from typing import Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from music21 import stream

try:
    from music21 import stream
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

from .types import TempoProfile, TempoDifficultyMetrics
from .profile import build_tempo_profile
from .difficulty import calculate_tempo_difficulty_metrics


def analyze_tempo(score: stream.Score) -> Tuple[TempoProfile, TempoDifficultyMetrics]:
    """
    Complete tempo analysis: profile + difficulty metrics.
    
    Args:
        score: music21 Score object
        
    Returns:
        Tuple of (TempoProfile, TempoDifficultyMetrics)
    """
    profile = build_tempo_profile(score)
    difficulty = calculate_tempo_difficulty_metrics(profile)
    return profile, difficulty


def get_legacy_tempo_bpm(profile: TempoProfile) -> Optional[int]:
    """
    Get a single BPM value for legacy compatibility.
    
    LEGACY: This returns effective_bpm instead of the old "last tempo" behavior.
    New code should use the full tempo profile instead.
    
    Args:
        profile: TempoProfile object
        
    Returns:
        effective_bpm if available, else base_bpm, else None
    """
    return profile.effective_bpm or profile.base_bpm
