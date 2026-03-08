"""
Type definitions and constants for tempo analysis.

Contains enums, dataclasses, and lookup tables for tempo term mapping.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum


# =============================================================================
# TEMPO TERM TO BPM MAPPING
# =============================================================================
# Standard Italian tempo terms mapped to approximate BPM ranges.
# We use the midpoint of conventional ranges. These can be refined.
# Sources: Various music dictionaries, conventional ranges
#
# NOTE: This mapping is isolated here for easy future tuning.

TEMPO_TERM_BPM: Dict[str, Tuple[int, int, int]] = {
    # (min_bpm, typical_bpm, max_bpm)
    "grave": (20, 35, 45),
    "largo": (40, 50, 60),
    "larghetto": (55, 63, 70),
    "lento": (40, 52, 60),
    "adagio": (55, 70, 80),
    "adagietto": (70, 75, 80),
    "andante": (73, 88, 108),
    "andantino": (80, 95, 108),
    "moderato": (100, 112, 120),
    "allegretto": (100, 116, 128),
    "allegro": (120, 138, 156),
    "vivace": (140, 160, 176),
    "vivacissimo": (170, 180, 190),
    "presto": (168, 184, 200),
    "prestissimo": (190, 208, 240),
}

# Terms that modify tempo but are not absolute tempos
TEMPO_MODIFIER_TERMS = {
    "accelerando": "accelerando",
    "accel": "accelerando",
    "accel.": "accelerando",
    "ritardando": "ritardando",
    "rit": "ritardando",
    "rit.": "ritardando",
    "ritard": "ritardando",
    "rallentando": "ritardando",
    "rall": "ritardando",
    "rall.": "ritardando",
    "a tempo": "a_tempo",
    "tempo i": "a_tempo",
    "tempo primo": "a_tempo", 
    "rubato": "rubato",
    "tempo rubato": "rubato",
    "meno mosso": "meno_mosso",
    "più mosso": "piu_mosso",
    "piu mosso": "piu_mosso",
    "stringendo": "accelerando",
    "string.": "accelerando",
    "calando": "ritardando",
    "morendo": "ritardando",
    "perdendosi": "ritardando",
    "smorzando": "ritardando",
    "allargando": "ritardando",
    "slentando": "ritardando",
}


# =============================================================================
# ENUMS
# =============================================================================

class TempoSourceType(str, Enum):
    """How the tempo was specified in the score."""
    METRONOME_MARK = "metronome_mark"    # Explicit BPM marking
    TEXT_TERM = "text_term"               # Italian tempo term
    TEXT_EXPRESSION = "text_expression"   # TextExpression element
    INFERRED = "inferred"                 # Derived from surrounding context
    DEFAULT = "default"                   # No tempo info, using default


class TempoChangeType(str, Enum):
    """Type of tempo change."""
    INITIAL = "initial"           # First tempo of piece
    STABLE = "stable"             # Continuation of previous tempo
    SUDDEN_CHANGE = "sudden_change"  # Abrupt tempo change
    ACCELERANDO = "accelerando"   # Gradual speeding up
    RITARDANDO = "ritardando"     # Gradual slowing down
    A_TEMPO = "a_tempo"           # Return to base tempo
    MENO_MOSSO = "meno_mosso"     # Slightly slower
    PIU_MOSSO = "piu_mosso"       # Slightly faster
    RUBATO = "rubato"             # Flexible phrasing tempo


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class TempoEvent:
    """
    A single tempo event parsed from the score.
    Used internally during parsing before building regions.
    """
    measure_number: int
    offset_in_measure: float  # quarterLength offset within measure
    bpm: Optional[int]        # Explicit BPM if available
    text: Optional[str]       # Raw text (e.g., "Allegro", "rit.")
    source_type: TempoSourceType
    change_type: TempoChangeType
    is_approximate: bool = False  # True if BPM was estimated from text term


@dataclass
class TempoRegion:
    """
    A contiguous region with a consistent tempo.
    """
    start_measure: int
    end_measure: int  # Inclusive
    bpm: Optional[int]  # Effective BPM for this region
    bpm_min: Optional[int]  # For ranges (e.g., accel from 80-120)
    bpm_max: Optional[int]
    source_type: TempoSourceType
    change_type: TempoChangeType
    text: Optional[str] = None  # Original tempo text if available
    is_approximate: bool = False  # True if BPM was estimated


@dataclass
class TempoProfile:
    """
    Complete tempo profile for a piece.
    """
    # Summary metrics
    base_bpm: Optional[int]       # First established tempo
    effective_bpm: Optional[int]  # Weighted average across piece
    min_bpm: Optional[int]        # Lowest BPM
    max_bpm: Optional[int]        # Highest BPM
    
    # Change tracking
    tempo_change_count: int       # Meaningful tempo changes
    
    # Boolean flags for tempo features
    has_accelerando: bool
    has_ritardando: bool
    has_a_tempo: bool
    has_rubato: bool
    has_sudden_change: bool
    has_tempo_marking: bool       # Whether any tempo info was found
    
    # Detailed regions
    tempo_regions: List[TempoRegion] = field(default_factory=list)
    
    # Confidence/provenance
    is_fully_explicit: bool = False  # All tempos had explicit BPM
    primary_source_type: TempoSourceType = TempoSourceType.DEFAULT
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        result = {
            "base_bpm": self.base_bpm,
            "effective_bpm": self.effective_bpm,
            "min_bpm": self.min_bpm,
            "max_bpm": self.max_bpm,
            "tempo_change_count": self.tempo_change_count,
            "has_accelerando": self.has_accelerando,
            "has_ritardando": self.has_ritardando,
            "has_a_tempo": self.has_a_tempo,
            "has_rubato": self.has_rubato,
            "has_sudden_change": self.has_sudden_change,
            "has_tempo_marking": self.has_tempo_marking,
            "is_fully_explicit": self.is_fully_explicit,
            "primary_source_type": self.primary_source_type.value,
            "tempo_regions": [
                {
                    "start_measure": r.start_measure,
                    "end_measure": r.end_measure,
                    "bpm": r.bpm,
                    "bpm_min": r.bpm_min,
                    "bpm_max": r.bpm_max,
                    "source_type": r.source_type.value,
                    "change_type": r.change_type.value,
                    "text": r.text,
                    "is_approximate": r.is_approximate,
                }
                for r in self.tempo_regions
            ],
        }
        return result


@dataclass 
class TempoDifficultyMetrics:
    """
    Difficulty metrics derived from tempo profile.
    These are placeholders for future refinement of the formulas.
    """
    tempo_speed_difficulty: Optional[float]    # 0-1, based on raw speed demands
    tempo_control_difficulty: Optional[float]  # 0-1, based on tempo changes/rubato
    
    # Raw values for debugging/tuning
    raw_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "tempo_speed_difficulty": self.tempo_speed_difficulty,
            "tempo_control_difficulty": self.tempo_control_difficulty,
            "raw_metrics": self.raw_metrics,
        }
