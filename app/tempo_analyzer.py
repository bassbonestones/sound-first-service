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

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any, Tuple
from enum import Enum

try:
    from music21 import stream, tempo, expressions
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False


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


# =============================================================================
# PARSING FUNCTIONS
# =============================================================================

def estimate_bpm_from_term(term: str) -> Tuple[Optional[int], bool]:
    """
    Estimate BPM from an Italian tempo term.
    
    Args:
        term: The tempo term (case insensitive)
        
    Returns:
        Tuple of (estimated_bpm, is_approximate)
        If term not recognized, returns (None, False)
    """
    term_lower = term.lower().strip()
    
    # Check for exact matches first
    if term_lower in TEMPO_TERM_BPM:
        _, typical, _ = TEMPO_TERM_BPM[term_lower]
        return (typical, True)
    
    # Check for partial matches (term might be combined like "Allegro ma non troppo")
    for tempo_term, (_, typical, _) in TEMPO_TERM_BPM.items():
        if tempo_term in term_lower:
            return (typical, True)
    
    return (None, False)


def classify_tempo_term(text: str) -> Optional[TempoChangeType]:
    """
    Classify a text string as a tempo modifier type.
    
    Args:
        text: The tempo text to classify
        
    Returns:
        TempoChangeType or None if not a modifier
    """
    text_lower = text.lower().strip()
    
    for term, change_type in TEMPO_MODIFIER_TERMS.items():
        if term in text_lower:
            return TempoChangeType(change_type)
    
    return None


def parse_tempo_events(score: stream.Score) -> List[TempoEvent]:
    """
    Parse all tempo events from a music21 score in order.
    
    Args:
        score: music21 Score object
        
    Returns:
        List of TempoEvent objects in measure order
    """
    events: List[TempoEvent] = []
    
    if score is None:
        return events
    
    # Get all measures to map offsets to measure numbers
    parts = list(score.parts)
    if not parts:
        return events
    
    # Use first part for measure mapping
    first_part = parts[0]
    measures = list(first_part.getElementsByClass(stream.Measure))
    
    # Build offset -> measure number map
    measure_map = {}  # offset -> measure_number
    for m in measures:
        if m.measureNumber is not None:
            measure_map[m.offset] = m.measureNumber
    
    def get_measure_number(offset: float) -> int:
        """Get measure number for a given offset."""
        # Find the measure that contains this offset
        for meas_offset, meas_num in sorted(measure_map.items()):
            if offset >= meas_offset:
                best = meas_num
            else:
                break
        return best if 'best' in dir() else 1
    
    # Parse MetronomeMark objects
    for t in score.recurse().getElementsByClass(tempo.MetronomeMark):
        measure_num = get_measure_number(t.getOffsetInHierarchy(score))
        offset_in_meas = t.offset if hasattr(t, 'offset') else 0.0
        
        bpm = int(t.number) if t.number else None
        text = t.text if t.text else None
        
        # Determine source type
        if bpm is not None:
            source_type = TempoSourceType.METRONOME_MARK
            is_approx = False
        elif text:
            source_type = TempoSourceType.TEXT_TERM
            # Try to estimate BPM from text
            estimated, is_approx = estimate_bpm_from_term(text)
            if estimated:
                bpm = estimated
            else:
                is_approx = True
        else:
            continue  # No useful info
        
        # Classify change type
        change_type = TempoChangeType.INITIAL if not events else TempoChangeType.SUDDEN_CHANGE
        if text:
            modifier = classify_tempo_term(text)
            if modifier:
                change_type = modifier
        
        events.append(TempoEvent(
            measure_number=measure_num,
            offset_in_measure=offset_in_meas,
            bpm=bpm,
            text=text,
            source_type=source_type,
            change_type=change_type,
            is_approximate=is_approx if bpm else True,
        ))
    
    # Parse TempoText objects
    for t in score.recurse().getElementsByClass(tempo.TempoText):
        if not t.text:
            continue
            
        measure_num = get_measure_number(t.getOffsetInHierarchy(score))
        offset_in_meas = t.offset if hasattr(t, 'offset') else 0.0
        text = t.text
        
        # Check if this is a modifier (rit., accel., a tempo)
        modifier = classify_tempo_term(text)
        
        # Try to get BPM from term
        estimated, is_approx = estimate_bpm_from_term(text)
        
        if modifier:
            change_type = modifier
        elif estimated:
            change_type = TempoChangeType.SUDDEN_CHANGE if events else TempoChangeType.INITIAL
        else:
            # Unknown text, skip
            continue
        
        events.append(TempoEvent(
            measure_number=measure_num,
            offset_in_measure=offset_in_meas,
            bpm=estimated,
            text=text,
            source_type=TempoSourceType.TEXT_TERM,
            change_type=change_type,
            is_approximate=is_approx,
        ))
    
    # Parse TextExpression objects for tempo indications
    for te in score.recurse().getElementsByClass(expressions.TextExpression):
        if not te.content:
            continue
            
        text = te.content
        text_lower = text.lower()
        
        # Check if it's a tempo-related expression
        modifier = classify_tempo_term(text)
        estimated, is_approx = estimate_bpm_from_term(text)
        
        if not modifier and not estimated:
            # Not tempo-related
            continue
        
        measure_num = get_measure_number(te.getOffsetInHierarchy(score))
        offset_in_meas = te.offset if hasattr(te, 'offset') else 0.0
        
        if modifier:
            change_type = modifier
        else:
            change_type = TempoChangeType.SUDDEN_CHANGE if events else TempoChangeType.INITIAL
        
        events.append(TempoEvent(
            measure_number=measure_num,
            offset_in_measure=offset_in_meas,
            bpm=estimated,
            text=text,
            source_type=TempoSourceType.TEXT_EXPRESSION,
            change_type=change_type,
            is_approximate=is_approx,
        ))
    
    # Sort by measure number, then offset
    events.sort(key=lambda e: (e.measure_number, e.offset_in_measure))
    
    # Deduplicate (same measure, same type)
    deduped = []
    for event in events:
        if not deduped:
            deduped.append(event)
        elif (deduped[-1].measure_number == event.measure_number and
              deduped[-1].change_type == event.change_type and
              deduped[-1].bpm == event.bpm):
            # Skip duplicate
            continue
        else:
            deduped.append(event)
    
    return deduped


# =============================================================================
# REGION BUILDING
# =============================================================================

def build_tempo_regions(events: List[TempoEvent], total_measures: int) -> List[TempoRegion]:
    """
    Convert tempo events into contiguous regions.
    
    Args:
        events: Parsed tempo events in order
        total_measures: Total measure count in the piece
        
    Returns:
        List of TempoRegion objects covering the piece
    """
    if not events:
        # No tempo info - return single default region
        return [TempoRegion(
            start_measure=1,
            end_measure=total_measures,
            bpm=None,
            bpm_min=None,
            bpm_max=None,
            source_type=TempoSourceType.DEFAULT,
            change_type=TempoChangeType.INITIAL,
            text=None,
            is_approximate=True,
        )]
    
    regions: List[TempoRegion] = []
    base_bpm = None  # Track base tempo for a_tempo returns
    
    for i, event in enumerate(events):
        # Handle first event  
        if event.change_type == TempoChangeType.INITIAL or not regions:
            if event.bpm:
                base_bpm = event.bpm
        
        # Determine end measure (next event's start - 1, or end of piece)
        if i < len(events) - 1:
            end_meas = events[i + 1].measure_number - 1
            if end_meas < event.measure_number:
                end_meas = event.measure_number
        else:
            end_meas = total_measures
        
        # Handle a_tempo - restore base_bpm
        effective_bpm = event.bpm
        if event.change_type == TempoChangeType.A_TEMPO and base_bpm:
            effective_bpm = base_bpm
        
        # Handle gradual changes (accel/rit) - they span to next event
        bpm_min = effective_bpm
        bpm_max = effective_bpm
        if event.change_type == TempoChangeType.ACCELERANDO and i < len(events) - 1:
            next_bpm = events[i + 1].bpm
            if next_bpm and effective_bpm:
                bpm_min = min(effective_bpm, next_bpm)
                bpm_max = max(effective_bpm, next_bpm)
        elif event.change_type == TempoChangeType.RITARDANDO and i < len(events) - 1:
            next_bpm = events[i + 1].bpm
            if next_bpm and effective_bpm:
                bpm_min = min(effective_bpm, next_bpm)
                bpm_max = max(effective_bpm, next_bpm)
        
        region = TempoRegion(
            start_measure=event.measure_number,
            end_measure=end_meas,
            bpm=effective_bpm,
            bpm_min=bpm_min,
            bpm_max=bpm_max,
            source_type=event.source_type,
            change_type=event.change_type,
            text=event.text,
            is_approximate=event.is_approximate,
        )
        regions.append(region)
    
    # Merge adjacent stable regions with same tempo
    merged = []
    for region in regions:
        if merged and (
            merged[-1].bpm == region.bpm and
            merged[-1].change_type == TempoChangeType.STABLE and
            region.change_type == TempoChangeType.STABLE
        ):
            merged[-1].end_measure = region.end_measure
        else:
            merged.append(region)
    
    return merged


# =============================================================================
# PROFILE CALCULATION
# =============================================================================

def calculate_effective_bpm(regions: List[TempoRegion]) -> Optional[int]:
    """
    Calculate weighted effective BPM based on region measure spans.
    
    Longer regions contribute more to the effective tempo.
    
    Args:
        regions: List of tempo regions
        
    Returns:
        Weighted average BPM, or None if no BPM info
    """
    total_weighted = 0.0
    total_measures = 0
    
    for region in regions:
        if region.bpm is None:
            continue
        
        span = region.end_measure - region.start_measure + 1
        
        # For tempo-changing regions (accel/rit), use midpoint
        if region.bpm_min and region.bpm_max and region.bpm_min != region.bpm_max:
            region_bpm = (region.bpm_min + region.bpm_max) / 2
        else:
            region_bpm = region.bpm
        
        total_weighted += region_bpm * span
        total_measures += span
    
    if total_measures == 0:
        return None
    
    return round(total_weighted / total_measures)


def build_tempo_profile(score: stream.Score) -> TempoProfile:
    """
    Build complete tempo profile from a music21 score.
    
    Args:
        score: music21 Score object
        
    Returns:
        TempoProfile with all metrics and regions
    """
    # Count measures
    parts = list(score.parts) if score else []
    if parts:
        measures = list(parts[0].getElementsByClass(stream.Measure))
        total_measures = len(measures) if measures else 1
    else:
        total_measures = 1
    
    # Parse events
    events = parse_tempo_events(score)
    
    # Build regions
    regions = build_tempo_regions(events, total_measures)
    
    # Calculate summary metrics
    bpm_values = [r.bpm for r in regions if r.bpm is not None]
    bpm_ranges = []
    for r in regions:
        if r.bpm_min is not None:
            bpm_ranges.append(r.bpm_min)
        if r.bpm_max is not None:
            bpm_ranges.append(r.bpm_max)
        if r.bpm is not None:
            bpm_ranges.append(r.bpm)
    
    base_bpm = bpm_values[0] if bpm_values else None
    min_bpm = min(bpm_ranges) if bpm_ranges else None
    max_bpm = max(bpm_ranges) if bpm_ranges else None
    effective_bpm = calculate_effective_bpm(regions)
    
    # Count meaningful tempo changes (exclude initial)
    change_types = [r.change_type for r in regions]
    tempo_change_count = sum(1 for ct in change_types if ct not in [
        TempoChangeType.INITIAL, TempoChangeType.STABLE
    ])
    
    # Boolean flags
    has_accelerando = TempoChangeType.ACCELERANDO in change_types
    has_ritardando = TempoChangeType.RITARDANDO in change_types
    has_a_tempo = TempoChangeType.A_TEMPO in change_types
    has_rubato = TempoChangeType.RUBATO in change_types
    has_sudden_change = TempoChangeType.SUDDEN_CHANGE in change_types
    has_tempo_marking = len(events) > 0
    
    # Confidence metrics
    is_fully_explicit = all(
        r.source_type == TempoSourceType.METRONOME_MARK 
        for r in regions if r.bpm is not None
    )
    
    # Primary source type
    if events:
        source_counts: Dict[TempoSourceType, int] = {}
        for e in events:
            source_counts[e.source_type] = source_counts.get(e.source_type, 0) + 1
        primary_source_type = max(source_counts, key=source_counts.get)
    else:
        primary_source_type = TempoSourceType.DEFAULT
    
    return TempoProfile(
        base_bpm=base_bpm,
        effective_bpm=effective_bpm,
        min_bpm=min_bpm,
        max_bpm=max_bpm,
        tempo_change_count=tempo_change_count,
        has_accelerando=has_accelerando,
        has_ritardando=has_ritardando,
        has_a_tempo=has_a_tempo,
        has_rubato=has_rubato,
        has_sudden_change=has_sudden_change,
        has_tempo_marking=has_tempo_marking,
        tempo_regions=regions,
        is_fully_explicit=is_fully_explicit,
        primary_source_type=primary_source_type,
    )


# =============================================================================
# DIFFICULTY METRICS
# =============================================================================
# NOTE: These formulas are initial placeholders for future refinement.
# The structure supports later tuning of the calculation logic.

def calculate_tempo_speed_difficulty(
    profile: TempoProfile,
    note_density_per_measure: Optional[float] = None,
) -> Optional[float]:
    """
    Calculate tempo speed difficulty (0-1).
    
    Based primarily on:
    - Effective BPM (main factor)
    - Max BPM (peak speed demand)
    - Note density at peak speed (future enhancement)
    
    Args:
        profile: TempoProfile object
        note_density_per_measure: Optional density metric for weighting
        
    Returns:
        Difficulty score 0-1, or None if insufficient data
    
    NOTE: This is a placeholder formula for future refinement.
    """
    if profile.effective_bpm is None:
        return None
    
    # Use effective BPM as primary factor
    # Normalize: 40 BPM = 0.0, 200 BPM = 1.0
    MIN_BPM = 40
    MAX_BPM = 200
    
    eff_score = (profile.effective_bpm - MIN_BPM) / (MAX_BPM - MIN_BPM)
    eff_score = max(0.0, min(1.0, eff_score))
    
    # Boost if max BPM is significantly higher than effective
    max_boost = 0.0
    if profile.max_bpm and profile.effective_bpm:
        range_ratio = (profile.max_bpm - profile.effective_bpm) / profile.effective_bpm
        max_boost = min(0.15, range_ratio * 0.3)  # Up to 15% boost
    
    # Combine (primarily effective, with max boost)
    speed_diff = eff_score * 0.85 + max_boost
    speed_diff = max(0.0, min(1.0, speed_diff))
    
    return round(speed_diff, 3)


def calculate_tempo_control_difficulty(profile: TempoProfile) -> Optional[float]:
    """
    Calculate tempo control difficulty (0-1).
    
    Based on:
    - Number of tempo changes
    - Types of changes (gradual vs sudden)
    - A tempo returns
    - Rubato sections
    
    Args:
        profile: TempoProfile object
        
    Returns:
        Difficulty score 0-1, or None if insufficient data
        
    NOTE: This is a placeholder formula for future refinement.
    """
    if not profile.has_tempo_marking:
        return None
    
    # Base score from change count
    # 0 changes = 0, 5+ changes = 0.5 base
    change_score = min(0.5, profile.tempo_change_count * 0.1)
    
    # Add for specific change types
    type_score = 0.0
    if profile.has_accelerando:
        type_score += 0.15
    if profile.has_ritardando:
        type_score += 0.15
    if profile.has_a_tempo:
        type_score += 0.1
    if profile.has_rubato:
        type_score += 0.2
    if profile.has_sudden_change:
        type_score += 0.1
    
    control_diff = change_score + type_score
    control_diff = max(0.0, min(1.0, control_diff))
    
    return round(control_diff, 3)


def calculate_tempo_difficulty_metrics(
    profile: TempoProfile,
    note_density_per_measure: Optional[float] = None,
) -> TempoDifficultyMetrics:
    """
    Calculate both tempo difficulty metrics from profile.
    
    Args:
        profile: TempoProfile object
        note_density_per_measure: Optional density for weighting
        
    Returns:
        TempoDifficultyMetrics with both scores
    """
    speed_diff = calculate_tempo_speed_difficulty(profile, note_density_per_measure)
    control_diff = calculate_tempo_control_difficulty(profile)
    
    raw = {
        "base_bpm": profile.base_bpm,
        "effective_bpm": profile.effective_bpm,
        "min_bpm": profile.min_bpm,
        "max_bpm": profile.max_bpm,
        "tempo_change_count": profile.tempo_change_count,
        "has_accelerando": profile.has_accelerando,
        "has_ritardando": profile.has_ritardando,
        "has_rubato": profile.has_rubato,
    }
    
    return TempoDifficultyMetrics(
        tempo_speed_difficulty=speed_diff,
        tempo_control_difficulty=control_diff,
        raw_metrics=raw,
    )


# =============================================================================
# CONVENIENCE FUNCTION
# =============================================================================

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


# =============================================================================
# LEGACY COMPATIBILITY
# =============================================================================
# These functions maintain backward compatibility with code expecting
# a single BPM value. They should be phased out over time.

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
