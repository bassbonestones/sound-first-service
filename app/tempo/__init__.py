"""
Tempo Profile Analyzer for Sound First

Analyzes MusicXML scores to build comprehensive tempo profiles including:
- Multiple tempo regions with boundaries
- Base, min, max, and weighted effective BPM
- Tempo change classification (gradual vs sudden, a tempo returns, etc.)
- Foundation for tempo speed and control difficulty metrics

This module replaces the simplistic "last tempo wins" approach with a
proper temporal model of tempo events.
"""

# Types and constants
from .types import (
    TEMPO_TERM_BPM,
    TEMPO_MODIFIER_TERMS,
    TempoSourceType,
    TempoChangeType,
    TempoEvent,
    TempoRegion,
    TempoProfile,
    TempoDifficultyMetrics,
)

# Parsing functions
from .parsing import (
    estimate_bpm_from_term,
    classify_tempo_term,
    parse_tempo_events,
)

# Region building
from .regions import (
    build_tempo_regions,
    calculate_effective_bpm,
)

# Profile building
from .profile import build_tempo_profile

# Difficulty calculations
from .difficulty import (
    calculate_tempo_speed_difficulty,
    calculate_tempo_control_difficulty,
    calculate_tempo_difficulty_metrics,
)

# Main API
from .analyzer import (
    analyze_tempo,
    get_legacy_tempo_bpm,
)

# Check for music21 availability
try:
    from music21 import stream
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False


__all__ = [
    # Constants
    "TEMPO_TERM_BPM",
    "TEMPO_MODIFIER_TERMS",
    "MUSIC21_AVAILABLE",
    # Types
    "TempoSourceType",
    "TempoChangeType",
    "TempoEvent",
    "TempoRegion",
    "TempoProfile",
    "TempoDifficultyMetrics",
    # Parsing
    "estimate_bpm_from_term",
    "classify_tempo_term",
    "parse_tempo_events",
    # Regions
    "build_tempo_regions",
    "calculate_effective_bpm",
    # Profile
    "build_tempo_profile",
    # Difficulty
    "calculate_tempo_speed_difficulty",
    "calculate_tempo_control_difficulty",
    "calculate_tempo_difficulty_metrics",
    # Main API
    "analyze_tempo",
    "get_legacy_tempo_bpm",
]
