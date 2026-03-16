"""
Extraction model dataclasses for MusicXML analysis.
"""
from dataclasses import dataclass, field, asdict
from typing import Dict, Set, Optional, Any

# Import tempo analyzer types
from app.tempo_analyzer import TempoProfile


def format_pitch_name(pitch_str: str) -> str:
    """Convert music21 pitch notation to standard notation.
    
    music21 uses '-' for flat (e.g., 'E-5' for Eb5).
    Convert to 'b' notation (e.g., 'Eb5').
    """
    return pitch_str.replace('-', 'b')


@dataclass
class IntervalInfo:
    """Information about an interval occurrence."""
    name: str  # e.g., "M3" for major third
    direction: str  # "ascending", "descending", "unison"
    quality: str  # "major", "minor", "perfect", "augmented", "diminished"
    semitones: int
    is_melodic: bool  # True for melodic, False for harmonic
    count: int = 1


@dataclass
class RhythmPatternAnalysis:
    """Rhythm pattern analysis for sight-reading difficulty prediction.
    
    Measures how many unique rhythm patterns exist vs total measures.
    Lower uniqueness = more repetition = easier sight-reading.
    """
    total_measures: int
    unique_rhythm_patterns: int
    rhythm_measure_uniqueness_ratio: float  # unique / total (0.0-1.0)
    rhythm_measure_repetition_ratio: float  # 1.0 - uniqueness_ratio
    # Pattern frequency: how often each pattern appears
    pattern_counts: Dict[str, int] = field(default_factory=dict)
    # Most common pattern for diagnostics
    most_common_pattern: Optional[str] = None
    most_common_count: int = 0


@dataclass
class MelodicPatternAnalysis:
    """Melodic pattern/motif analysis for predictability scoring (Phase 8).
    
    Measures how many unique melodic motifs exist vs total.
    Higher repetition = more predictable = easier sight-reading.
    
    Motifs are detected using sliding windows of 3-4 notes,
    encoded as interval direction sequences (e.g., "+2_-3_+1").
    """
    total_motifs: int  # Total 3-note and 4-note windows analyzed
    unique_motifs: int  # Distinct melodic patterns found
    motif_uniqueness_ratio: float  # unique / total (0.0-1.0)
    motif_repetition_ratio: float  # 1.0 - uniqueness_ratio
    # Sequence detection: repeated sequences of 4+ notes
    sequence_count: int = 0  # Number of detected sequences
    sequence_total_notes: int = 0  # Total notes in detected sequences
    sequence_coverage_ratio: float = 0.0  # sequence_notes / total_notes
    # Most common motif for diagnostics
    most_common_motif: Optional[str] = None
    most_common_count: int = 0


@dataclass 
class RangeAnalysis:
    """Pitch range analysis with density information."""
    lowest_pitch: str  # e.g., "E3"
    highest_pitch: str  # e.g., "G5"
    lowest_midi: int
    highest_midi: int
    range_semitones: int
    # Density: what % of notes fall in each third of the range
    density_low: float  # lower 33%
    density_mid: float  # middle 33%
    density_high: float  # upper 33%
    # For trills
    trill_lowest: Optional[str] = None
    trill_highest: Optional[str] = None


@dataclass
class ExtractionResult:
    """Complete extraction result from MusicXML analysis."""
    
    # Basic identification
    title: Optional[str] = None
    composer: Optional[str] = None
    
    # Clefs found
    clefs: Set[str] = field(default_factory=set)  # "treble", "bass", "alto", "tenor"
    
    # Time signatures
    time_signatures: Set[str] = field(default_factory=set)  # "4/4", "3/4", "6/8"
    
    # Key signatures (for reading capability, not ear-playing)
    key_signatures: Set[str] = field(default_factory=set)  # "C major", "G major", "D minor"
    
    # Note values
    note_values: Dict[str, int] = field(default_factory=dict)  # {"quarter": 45, "eighth": 22}
    dotted_notes: Set[str] = field(default_factory=set)  # "dotted_quarter", "dotted_half"
    has_ties: bool = False
    
    # Rests
    rest_values: Dict[str, int] = field(default_factory=dict)
    has_multi_measure_rest: bool = False
    
    # Tuplets
    tuplets: Dict[str, int] = field(default_factory=dict)  # {"triplet": 8, "quintuplet": 2}
    
    # Intervals
    melodic_intervals: Dict[str, IntervalInfo] = field(default_factory=dict)
    harmonic_intervals: Dict[str, IntervalInfo] = field(default_factory=dict)
    
    # Dynamics
    dynamics: Set[str] = field(default_factory=set)  # "p", "f", "mf", "sfz"
    dynamic_changes: Set[str] = field(default_factory=set)  # "crescendo", "diminuendo"
    
    # Articulations
    articulations: Set[str] = field(default_factory=set)  # "staccato", "accent", "tenuto"
    
    # Ornaments
    ornaments: Set[str] = field(default_factory=set)  # "trill", "mordent", "turn", "grace_note"
    
    # Tempo and expression
    tempo_markings: Set[str] = field(default_factory=set)  # "Allegro", "Andante"
    tempo_bpm: Optional[int] = None  # LEGACY: Use tempo_profile.effective_bpm instead
    tempo_profile: Optional[TempoProfile] = None  # Full tempo analysis
    expression_terms: Set[str] = field(default_factory=set)  # "dolce", "cantabile"
    
    # Repeat structures
    repeat_structures: Set[str] = field(default_factory=set)  # "repeat_sign", "coda", "dc"
    
    # Other notation
    fermatas: int = 0
    breath_marks: int = 0
    chord_symbols: Set[str] = field(default_factory=set)
    figured_bass: bool = False
    
    # Multi-voice
    max_voices: int = 1
    
    # Range analysis
    range_analysis: Optional[RangeAnalysis] = None
    
    # Rhythm pattern analysis (sight-reading predictor)
    rhythm_pattern_analysis: Optional[RhythmPatternAnalysis] = None
    
    # Melodic pattern analysis (Phase 8 - predictability)
    melodic_pattern_analysis: Optional[MelodicPatternAnalysis] = None
    
    # Chromatic analysis
    accidentals_outside_key: Dict[str, int] = field(default_factory=dict)  # {"F#": 3, "Bb": 1}
    chromatic_complexity_score: float = 0.0
    
    # Structure
    measure_count: int = 0
    estimated_duration_seconds: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, handling sets and dataclasses."""
        result: Dict[str, Any] = {}
        for k, v in self.__dict__.items():
            if isinstance(v, set):
                result[k] = list(v)
            elif isinstance(v, dict):
                # Handle IntervalInfo objects in dicts
                result[k] = {ik: (asdict(iv) if hasattr(iv, '__dataclass_fields__') else iv) 
                            for ik, iv in v.items()}
            elif hasattr(v, 'to_dict'):
                # Handle TempoProfile and other objects with to_dict
                result[k] = v.to_dict()
            elif hasattr(v, '__dataclass_fields__'):
                result[k] = asdict(v)
            else:
                result[k] = v
        return result
