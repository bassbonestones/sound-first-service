"""
Scoring Functions for Sound First — Facet-Aware Architecture

Each domain produces a DomainResult containing:
- profile: raw measurable musical features
- facet_scores: normalized 0.0-1.0 scores for meaningful subcomponents
- scores: domain summary {primary, hazard, overall}
- bands: derived stages {primary_stage, hazard_stage, overall_stage}
- flags: warning/info flags
- confidence: how reliable the analysis is (1.0 = full confidence)

Score semantics:
- 0.0 = trivial / no difficulty
- 1.0 = extreme difficulty
- Scores are normalized to [0.0, 1.0] for easy weighting and combining

Design principles:
- Functions are pure (no side effects, no DB access)
- All thresholds are clearly marked as PROVISIONAL
- Functions are modular for easy testing and refinement
- Facets preserve subskill structure for learner/material models
"""

from typing import Dict, Optional, Any, TypedDict, List
from dataclasses import dataclass, field
import math


# =============================================================================
# TYPE DEFINITIONS
# =============================================================================

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


# =============================================================================
# NORMALIZATION UTILITIES
# =============================================================================

def clamp(value: float, min_val: float = 0.0, max_val: float = 1.0) -> float:
    """Clamp value to [min_val, max_val]."""
    return max(min_val, min(max_val, value))


def normalize_linear(value: float, low: float, high: float) -> float:
    """
    Linear normalization to [0, 1].
    
    Args:
        value: Raw value to normalize
        low: Value that maps to 0.0
        high: Value that maps to 1.0
    
    Returns:
        Normalized value in [0, 1]
    """
    if high <= low:
        return 0.0
    return clamp((value - low) / (high - low))


def normalize_sigmoid(value: float, midpoint: float, steepness: float = 1.0) -> float:
    """
    Sigmoid normalization centered at midpoint.
    
    Useful when difficulty increases non-linearly.
    """
    return 1.0 / (1.0 + math.exp(-steepness * (value - midpoint)))


# =============================================================================
# STAGE DERIVATION (PROVISIONAL THRESHOLDS)
# =============================================================================

# PROVISIONAL: Stage thresholds — calibrate after corpus analysis
STAGE_THRESHOLDS = [0.15, 0.30, 0.45, 0.60, 0.75, 0.90]


def score_to_stage(score: float) -> int:
    """
    Convert a 0.0-1.0 score to a 0-6 stage.
    
    PROVISIONAL thresholds:
        0.00-0.14 → Stage 0
        0.15-0.29 → Stage 1
        0.30-0.44 → Stage 2
        0.45-0.59 → Stage 3
        0.60-0.74 → Stage 4
        0.75-0.89 → Stage 5
        0.90-1.00 → Stage 6
    """
    score = clamp(score)
    for stage, threshold in enumerate(STAGE_THRESHOLDS):
        if score < threshold:
            return stage
    return 6


def derive_bands(scores: DomainScores) -> DomainBands:
    """Derive stage bands from domain scores."""
    return DomainBands(
        primary_stage=score_to_stage(scores['primary']),
        hazard_stage=score_to_stage(scores['hazard']),
        overall_stage=score_to_stage(scores['overall']),
    )


# =============================================================================
# INTERVAL DOMAIN
# =============================================================================

# PROVISIONAL THRESHOLDS (widened for realistic pieces)
INTERVAL_STEP_SKIP_P75_LOW = 2      # minor 2nd
INTERVAL_STEP_SKIP_P75_HIGH = 12    # octave (was 7)
INTERVAL_SUSTAINED_LEAP_P90_LOW = 5 # P4
INTERVAL_SUSTAINED_LEAP_P90_HIGH = 19  # octave + 5th (was 15)
INTERVAL_EXTREME_LEAP_MAX_LOW = 12  # octave
INTERVAL_EXTREME_LEAP_MAX_HIGH = 36 # 3 octaves (was 24)
INTERVAL_CLUSTER_WINDOW_LOW = 1
INTERVAL_CLUSTER_WINDOW_HIGH = 8    # (was 5)


def analyze_interval_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze interval complexity with facet-aware scoring.
    
    Profile fields:
        interval_p50: int - median interval (semitones)
        interval_p75: int - 75th percentile interval
        interval_p90: int - 90th percentile interval
        interval_max: int - maximum interval
        step_ratio: float - proportion of steps (0-2 semitones)
        skip_ratio: float - proportion of skips (3-5 semitones)
        leap_ratio: float - proportion of leaps (6-11 semitones)
        large_leap_ratio: float - proportion of large leaps (12-17 semitones)
        extreme_leap_ratio: float - proportion of extreme leaps (18+ semitones)
        max_large_leaps_in_window: int - maximum large leaps in sliding window
        max_extreme_leaps_in_window: int - maximum extreme leaps in sliding window
    
    Facet scores:
        step_skip_complexity: complexity from step/skip patterns
        sustained_leap_complexity: typical leap demand (p75/p90)
        extreme_leap_hazard: danger from maximum intervals
        clustered_leap_hazard: danger from clustered leaps
    
    Domain scores:
        primary: sustained melodic difficulty
        hazard: extreme + clustered leap danger
        overall: blended interval difficulty
    """
    # Extract profile with defaults
    p50 = profile.get('interval_p50', 0)
    p75 = profile.get('interval_p75', 0)
    p90 = profile.get('interval_p90', 0)
    max_interval = profile.get('interval_max', 0)
    step_ratio = profile.get('step_ratio', 1.0)
    skip_ratio = profile.get('skip_ratio', 0.0)
    leap_ratio = profile.get('leap_ratio', 0.0)
    large_leap_ratio = profile.get('large_leap_ratio', 0.0)
    extreme_leap_ratio = profile.get('extreme_leap_ratio', 0.0)
    max_large_in_window = profile.get('max_large_leaps_in_window', 0)
    max_extreme_in_window = profile.get('max_extreme_leaps_in_window', 0)
    
    # Calculate facet scores
    step_skip_complexity = normalize_linear(p75, INTERVAL_STEP_SKIP_P75_LOW, INTERVAL_STEP_SKIP_P75_HIGH)
    
    sustained_leap_complexity = normalize_linear(p90, INTERVAL_SUSTAINED_LEAP_P90_LOW, INTERVAL_SUSTAINED_LEAP_P90_HIGH)
    # Modest boost if large leaps are frequent
    if large_leap_ratio > 0.05:
        sustained_leap_complexity = clamp(sustained_leap_complexity + large_leap_ratio)
    
    extreme_leap_hazard = normalize_linear(max_interval, INTERVAL_EXTREME_LEAP_MAX_LOW, INTERVAL_EXTREME_LEAP_MAX_HIGH)
    # Modest boost if extreme leaps exist at all
    if extreme_leap_ratio > 0:
        extreme_leap_hazard = clamp(extreme_leap_hazard + extreme_leap_ratio * 2)
    
    clustered_leap_hazard = normalize_linear(
        max_large_in_window + max_extreme_in_window,  # removed *2 multiplier
        INTERVAL_CLUSTER_WINDOW_LOW,
        INTERVAL_CLUSTER_WINDOW_HIGH
    )
    
    facet_scores = {
        'step_skip_complexity': round(step_skip_complexity, 4),
        'sustained_leap_complexity': round(sustained_leap_complexity, 4),
        'extreme_leap_hazard': round(extreme_leap_hazard, 4),
        'clustered_leap_hazard': round(clustered_leap_hazard, 4),
    }
    
    # Derive domain scores from facets
    primary = clamp(
        step_skip_complexity * 0.3 +
        sustained_leap_complexity * 0.7
    )
    
    hazard = clamp(
        extreme_leap_hazard * 0.6 +
        clustered_leap_hazard * 0.4
    )
    
    overall = clamp(primary * 0.6 + hazard * 0.4)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if extreme_leap_hazard > 0.5:
        flags.append('extreme_intervals_present')
    if clustered_leap_hazard > 0.6:
        flags.append('clustered_leaps_warning')
    if hazard > primary + 0.2:
        flags.append('interval_hazard_spike')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=1.0 if profile.get('total_intervals', 0) > 10 else 0.8,
    )


# =============================================================================
# RHYTHM DOMAIN
# =============================================================================

# PROVISIONAL THRESHOLDS
RHYTHM_SUBDIVISION_FASTEST_QL_HIGH = 0.125  # 32nd note
RHYTHM_SUBDIVISION_FASTEST_QL_LOW = 1.0     # Quarter note
RHYTHM_SYNCOPATION_HIGH = 0.4
RHYTHM_TUPLET_HIGH = 0.2
RHYTHM_DOT_TIE_HIGH = 0.3
RHYTHM_UNIQUENESS_LOW = 0.1
RHYTHM_UNIQUENESS_HIGH = 0.8


def analyze_rhythm_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze rhythm complexity with facet-aware scoring.
    
    Profile fields:
        shortest_duration: float - shortest note duration (quarterLength)
        note_value_diversity: float - variety of note values
        tuplet_ratio: float - proportion in tuplets
        dot_ratio: float - proportion dotted
        tie_ratio: float - proportion tied
        syncopation_ratio: float - proportion syncopated
        rhythm_measure_uniqueness_ratio: float - unique patterns / total measures
        rhythm_measure_repetition_ratio: float - 1 - uniqueness
        subdivision_entropy: float - (future) variety of subdivisions
        pattern_irregularity: float - (future) uneven distribution
    
    Facet scores:
        subdivision_complexity: how fine the subdivisions get
        syncopation_complexity: off-beat complexity
        tuplet_complexity: tuplet handling demand
        dot_tie_complexity: tied/dotted note handling
        pattern_novelty: how many unique patterns to track
    
    Domain scores:
        primary: main rhythmic demand
        hazard: bursty/local rhythmic spikes
        overall: blended rhythmic difficulty
    """
    # Extract profile with defaults
    shortest_ql = profile.get('shortest_duration', 1.0)
    if shortest_ql is None or shortest_ql <= 0:
        shortest_ql = 1.0
    note_value_diversity = profile.get('note_value_diversity', 0.3)
    tuplet_ratio = profile.get('tuplet_ratio', 0.0)
    dot_ratio = profile.get('dot_ratio', 0.0)
    tie_ratio = profile.get('tie_ratio', 0.0)
    syncopation_ratio = profile.get('syncopation_ratio', 0.0)
    uniqueness_ratio = profile.get('rhythm_measure_uniqueness_ratio', 0.5)
    repetition_ratio = profile.get('rhythm_measure_repetition_ratio', 0.5)
    subdivision_entropy = profile.get('subdivision_entropy', None)  # Future
    pattern_irregularity = profile.get('pattern_irregularity', None)  # Future
    
    # Calculate facet scores
    # Subdivision: shorter notes = harder (reciprocal scale)
    fastest_normalized = 1.0 / max(shortest_ql, 0.0625)  # Cap at 64th notes
    subdivision_complexity = normalize_linear(fastest_normalized, 1, 16)  # 1 = quarter, 16 = 64th
    
    syncopation_complexity = normalize_linear(syncopation_ratio, 0, RHYTHM_SYNCOPATION_HIGH)
    
    tuplet_complexity = normalize_linear(tuplet_ratio, 0, RHYTHM_TUPLET_HIGH)
    
    dot_tie_complexity = normalize_linear(dot_ratio + tie_ratio, 0, RHYTHM_DOT_TIE_HIGH)
    
    pattern_novelty = normalize_linear(uniqueness_ratio, RHYTHM_UNIQUENESS_LOW, RHYTHM_UNIQUENESS_HIGH)
    
    facet_scores = {
        'subdivision_complexity': round(subdivision_complexity, 4),
        'syncopation_complexity': round(syncopation_complexity, 4),
        'tuplet_complexity': round(tuplet_complexity, 4),
        'dot_tie_complexity': round(dot_tie_complexity, 4),
        'pattern_novelty': round(pattern_novelty, 4),
    }
    
    # Derive domain scores from facets
    primary = clamp(
        subdivision_complexity * 0.25 +
        syncopation_complexity * 0.20 +
        tuplet_complexity * 0.15 +
        dot_tie_complexity * 0.10 +
        pattern_novelty * 0.30
    )
    
    # Hazard: irregular bursts, high novelty combined with fast subdivisions
    hazard_base = pattern_novelty * 0.5 + syncopation_complexity * 0.3
    if subdivision_complexity > 0.6 and pattern_novelty > 0.5:
        hazard_base = clamp(hazard_base + 0.15)  # Boost for fast + novel
    
    hazard = clamp(hazard_base + tuplet_complexity * 0.2)
    
    overall = clamp(primary * 0.7 + hazard * 0.3)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if tuplet_complexity > 0.5:
        flags.append('complex_tuplets')
    if syncopation_complexity > 0.6:
        flags.append('heavy_syncopation')
    if pattern_novelty > 0.7:
        flags.append('highly_unpredictable_rhythm')
    if subdivision_complexity > 0.7 and hazard > 0.5:
        flags.append('fast_irregular_bursts')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=1.0,
    )


# =============================================================================
# TONAL DOMAIN
# =============================================================================

# PROVISIONAL THRESHOLDS
# NOTE: pitch_class_count is NOT used as a primary facet — it's too naive.
# Tonal facets focus on chromatic departure, accidental burden, and instability.
TONAL_CHROMATIC_RATIO_HIGH = 0.3
TONAL_ACCIDENTAL_HIGH = 0.4


def analyze_tonal_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze tonal complexity with facet-aware scoring.
    
    NOTE: We do NOT use pitch_class_count as a primary facet because
    most tonal pieces use 7 pitch classes, making it meaningless noise.
    
    Profile fields:
        accidental_rate: float - proportion of accidentals
        chromatic_ratio: float - proportion of chromatic notes
        diatonic_predictability_proxy: float - (future) adherence to scale
        modulation_count: int - (future) number of key changes
        key_center_ambiguity: float - (future) tonal center clarity
    
    Facet scores:
        chromatic_complexity: complexity from chromatic departures
        accidental_load: reading burden from accidentals
        tonal_instability: unpredictability / lack of diatonic stability
    
    Domain scores:
        primary: overall tonal reading/hearing complexity
        hazard: instability/chromatic spikes
        overall: blended tonal difficulty
    """
    # Extract profile with defaults
    accidental_rate = profile.get('accidental_rate', 0.0) or 0.0
    chromatic_ratio = profile.get('chromatic_ratio', 0.0) or 0.0
    diatonic_predictability = profile.get('diatonic_predictability_proxy', 1.0)  # Default stable
    modulation_count = profile.get('modulation_count', 0) or 0
    key_center_ambiguity = profile.get('key_center_ambiguity', 0.0) or 0.0  # Future hook
    
    # Calculate facet scores
    # Chromatic: proportion of non-diatonic notes
    chromatic_complexity = normalize_linear(chromatic_ratio, 0, TONAL_CHROMATIC_RATIO_HIGH)
    
    # Accidental load: reading burden from sharps/flats/naturals
    accidental_load = normalize_linear(accidental_rate, 0, TONAL_ACCIDENTAL_HIGH)
    
    # Instability: lack of diatonic predictability + modulations + ambiguity
    tonal_instability = clamp(
        (1.0 - diatonic_predictability) * 0.5 +
        normalize_linear(modulation_count, 0, 4) * 0.3 +
        key_center_ambiguity * 0.2
    )
    
    facet_scores = {
        'chromatic_complexity': round(chromatic_complexity, 4),
        'accidental_load': round(accidental_load, 4),
        'tonal_instability': round(tonal_instability, 4),
    }
    
    # Derive domain scores from facets
    primary = clamp(
        accidental_load * 0.35 +
        chromatic_complexity * 0.35 +
        tonal_instability * 0.30
    )
    
    hazard = clamp(
        chromatic_complexity * 0.5 +
        tonal_instability * 0.5
    )
    
    overall = clamp(primary * 0.6 + hazard * 0.4)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if chromatic_complexity > 0.5:
        flags.append('highly_chromatic')
    if accidental_load > 0.6:
        flags.append('heavy_accidentals')
    if tonal_instability > 0.5:
        flags.append('tonal_instability_warning')
    if modulation_count > 0:
        flags.append(f'modulations_detected_{modulation_count}')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=1.0,
    )


# =============================================================================
# TEMPO DOMAIN
# =============================================================================

# PROVISIONAL THRESHOLDS
TEMPO_SPEED_BPM_LOW = 60
TEMPO_SPEED_BPM_HIGH = 180
TEMPO_CONTROL_CHANGES_LOW = 0
TEMPO_CONTROL_CHANGES_HIGH = 6
TEMPO_VARIABILITY_VOLATILITY_HIGH = 0.5


def analyze_tempo_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze tempo complexity with facet-aware scoring.
    
    If no explicit tempo marking exists in the score, returns null scores
    with low confidence. We do not assume defaults.
    
    Profile fields:
        base_bpm: int|None - marked/initial BPM (None if not specified)
        effective_bpm: int|None - weighted average BPM
        tempo_is_explicit: bool - whether tempo was explicitly marked
        min_bpm: int - minimum BPM
        max_bpm: int - maximum BPM
        tempo_change_count: int - number of tempo changes
        tempo_volatility: float - magnitude × frequency of changes
        has_accelerando: bool - accelerando present
        has_ritardando: bool - ritardando present
        has_rubato: bool - rubato/flexible tempo indicated
        has_sudden_change: bool - sudden tempo change (subito)
        tempo_regions: int - distinct tempo sections
    
    Facet scores:
        speed_demand: how fast the sustained tempo is
        tempo_control_demand: precision needed for tempo changes
        tempo_variability: how much the tempo fluctuates
    
    Domain scores:
        primary: sustained tempo demand
        hazard: control volatility / abrupt change risk
        overall: blended tempo difficulty
    """
    tempo_is_explicit = profile.get('tempo_is_explicit', False)
    
    # If no explicit tempo, return empty scores with low confidence
    if not tempo_is_explicit:
        return DomainResult(
            profile=profile,
            facet_scores={
                'speed_demand': None,
                'tempo_control_demand': None,
                'tempo_variability': None,
            },
            scores=DomainScores(primary=None, hazard=None, overall=None),
            bands={'primary_stage': None, 'hazard_stage': None, 'overall_stage': None},
            flags=['no_tempo_marking'],
            confidence=0.0,
        )
    
    # Extract profile with defaults
    base_bpm = profile.get('base_bpm') or 120
    effective_bpm = profile.get('effective_bpm') or base_bpm
    min_bpm = profile.get('min_bpm') or effective_bpm
    max_bpm = profile.get('max_bpm') or effective_bpm
    tempo_change_count = profile.get('tempo_change_count') or 0
    tempo_volatility = profile.get('tempo_volatility') or 0.0
    has_accelerando = profile.get('has_accelerando', False)
    has_ritardando = profile.get('has_ritardando', False)
    has_rubato = profile.get('has_rubato', False)
    has_sudden_change = profile.get('has_sudden_change', False)
    tempo_regions = profile.get('tempo_regions') or 1
    
    # Calculate facet scores
    speed_demand = normalize_linear(effective_bpm, TEMPO_SPEED_BPM_LOW, TEMPO_SPEED_BPM_HIGH)
    
    # Control demand: changes + gradual modifications
    gradual_changes = (1 if has_accelerando else 0) + (1 if has_ritardando else 0)
    tempo_control_demand = clamp(
        normalize_linear(tempo_change_count + gradual_changes, TEMPO_CONTROL_CHANGES_LOW, TEMPO_CONTROL_CHANGES_HIGH) * 0.7 +
        (0.2 if has_rubato else 0.0) +
        (0.1 if has_sudden_change else 0.0)
    )
    
    # Variability: how much range and how volatile
    bpm_range_normalized = normalize_linear(max_bpm - min_bpm, 0, 60)
    tempo_variability = clamp(
        normalize_linear(tempo_volatility, 0, TEMPO_VARIABILITY_VOLATILITY_HIGH) * 0.6 +
        bpm_range_normalized * 0.4
    )
    
    facet_scores = {
        'speed_demand': round(speed_demand, 4),
        'tempo_control_demand': round(tempo_control_demand, 4),
        'tempo_variability': round(tempo_variability, 4),
    }
    
    # Derive domain scores from facets
    primary = clamp(
        speed_demand * 0.7 +
        tempo_control_demand * 0.3
    )
    
    hazard = clamp(
        tempo_variability * 0.5 +
        tempo_control_demand * 0.3 +
        (0.2 if has_sudden_change else 0.0)
    )
    
    overall = clamp(primary * 0.7 + hazard * 0.3)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if speed_demand > 0.7:
        flags.append('fast_tempo')
    if tempo_control_demand > 0.5:
        flags.append('tempo_changes_present')
    if has_sudden_change:
        flags.append('sudden_tempo_change')
    if has_rubato:
        flags.append('flexible_tempo_indicated')
    if tempo_variability > 0.5:
        flags.append('high_tempo_variability')
    
    # Confidence: lower if no tempo marking found
    confidence = 1.0 if profile.get('base_bpm') else 0.5
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=confidence,
    )


# =============================================================================
# RANGE DOMAIN
# =============================================================================

# PROVISIONAL THRESHOLDS
# NOTE: Range is profile-only - scoring requires instrument context.
RANGE_SPAN_NARROW = 7      # P5 or less
RANGE_SPAN_WIDE = 36       # 3 octaves


def analyze_range_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Range domain - PROFILE-ONLY, no difficulty scoring.
    
    Range difficulty is instrument-dependent and cannot be meaningfully
    scored without knowing the target instrument. A 2-octave span is trivial
    for piano but demanding for trumpet.
    
    This domain captures the material's range characteristics for later
    comparison against the user's instrument-specific comfort envelope.
    
    Profile fields (all preserved for instrument-relative comparison):
        lowest_pitch: str - pitch name of lowest note
        highest_pitch: str - pitch name of highest note
        span_semitones: int - total range in semitones
        tessitura_span: int - p10-p90 working range in semitones
    
    Facet scores:
        span_breadth: normalized span (for relative comparison only)
    
    Domain scores:
        All set to None - scoring happens at assignment time with instrument context
    """
    # Extract profile
    span_semitones = profile.get('span_semitones')
    tessitura_span = profile.get('tessitura_span')
    
    # Only compute span_breadth as a relative measure (not a difficulty score)
    span_breadth = None
    if span_semitones is not None:
        span_breadth = normalize_linear(span_semitones, RANGE_SPAN_NARROW, RANGE_SPAN_WIDE)
    
    facet_scores = {
        'span_breadth': round(span_breadth, 4) if span_breadth is not None else None,
    }
    
    # No scoring - requires instrument context
    scores = DomainScores(primary=None, hazard=None, overall=None)
    
    # Generate flags based on raw values
    flags = ['requires_instrument_context']
    if span_semitones and span_semitones > 24:  # > 2 octaves
        flags.append('wide_range')
    if span_semitones and span_semitones > 36:  # > 3 octaves
        flags.append('very_wide_range')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands={'primary_stage': None, 'hazard_stage': None, 'overall_stage': None},
        flags=flags,
        confidence=0.0,  # Cannot score without instrument
    )


# =============================================================================
# THROUGHPUT (DENSITY) DOMAIN
# =============================================================================

# PROVISIONAL THRESHOLDS
THROUGHPUT_NPS_LOW = 1.0
THROUGHPUT_NPS_SUSTAINED_HIGH = 6.0
THROUGHPUT_NPS_PEAK_HIGH = 12.0
THROUGHPUT_VOLATILITY_HIGH = 0.5


def analyze_throughput_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze throughput (density) complexity with facet-aware scoring.
    
    Profile fields:
        notes_per_second: float - average note rate
        peak_notes_per_second: float - maximum note rate in any window
        notes_per_measure: float - average notes per measure
        throughput_volatility: float - variation in local notes-per-second across windows
    
    Facet scores:
        sustained_density: typical note rate demand
        peak_density: maximum burst demand
        adaptation_pressure: cognitive load from changing density
            (how much the player must adapt to varying throughput)
    
    Domain scores:
        primary: sustained throughput demand
        hazard: local throughput spikes
        overall: blended throughput difficulty
    """
    # Extract profile with defaults
    nps = profile.get('notes_per_second', 2.0) or 2.0
    peak_nps = profile.get('peak_notes_per_second') or nps
    notes_per_measure = profile.get('notes_per_measure', 8.0)
    volatility = profile.get('throughput_volatility', 0.0) or 0.0
    
    # Calculate facet scores
    sustained_density = normalize_linear(nps, THROUGHPUT_NPS_LOW, THROUGHPUT_NPS_SUSTAINED_HIGH)
    
    peak_density = normalize_linear(peak_nps, THROUGHPUT_NPS_LOW, THROUGHPUT_NPS_PEAK_HIGH)
    
    # Adaptation pressure: how much density varies across the piece
    adaptation_pressure = normalize_linear(volatility, 0, THROUGHPUT_VOLATILITY_HIGH)
    
    facet_scores = {
        'sustained_density': round(sustained_density, 4),
        'peak_density': round(peak_density, 4),
        'adaptation_pressure': round(adaptation_pressure, 4),
    }
    
    # Derive domain scores from facets
    primary = clamp(
        sustained_density * 0.8 +
        adaptation_pressure * 0.2
    )
    
    hazard = clamp(
        peak_density * 0.7 +
        adaptation_pressure * 0.3
    )
    
    overall = clamp(primary * 0.7 + hazard * 0.3)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if sustained_density > 0.6:
        flags.append('high_sustained_density')
    if peak_density > 0.7:
        flags.append('dense_passages')
    if peak_density > sustained_density + 0.3:
        flags.append('throughput_burst_warning')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=1.0 if profile.get('notes_per_second') is not None else 0.7,
    )


# =============================================================================
# PATTERN / PREDICTABILITY DOMAIN
# =============================================================================

# PROVISIONAL: Pattern domain thresholds
# NOTE: This domain is INVERTED - high predictability = easier
PATTERN_UNIQUENESS_LOW = 0.2    # 20% unique = very repetitive = easy
PATTERN_UNIQUENESS_HIGH = 0.9   # 90% unique = unpredictable = hard
PATTERN_SEQUENCE_COVERAGE_LOW = 0.0
PATTERN_SEQUENCE_COVERAGE_HIGH = 0.5   # 50% coverage = very predictable


def analyze_pattern_domain(profile: Dict[str, Any]) -> DomainResult:
    """
    Analyze pattern/predictability complexity with facet-aware scoring.
    
    NOTE: This domain is INVERTED - high predictability (repetition) = easier.
    The "primary" score represents DIFFICULTY, so:
    - High uniqueness = high difficulty score
    - High repetition = low difficulty score
    
    Profile fields:
        total_melodic_motifs: int - count of detected interval patterns
        unique_melodic_motifs: int - count of distinct patterns
        melodic_motif_uniqueness_ratio: float - unique/total
        melodic_motif_repetition_ratio: float - 1 - uniqueness_ratio
        sequence_count: int - number of repeated phrases
        sequence_coverage_ratio: float - fraction of notes in repeated sequences
        rhythm_uniqueness_ratio: float - from rhythm pattern analysis
        rhythm_repetition_ratio: float - 1 - rhythm_uniqueness_ratio
    
    Facet scores:
        melodic_predictability: inverse of melodic uniqueness (0=random, 1=highly repetitive)
        rhythmic_predictability: inverse of rhythm uniqueness
        structural_regularity: based on sequence repetition
    
    Domain scores (DIFFICULTY oriented):
        primary: cognitive load from unpredictability
        hazard: irregularity spikes that break expectations
        overall: blended unpredictability difficulty
    """
    # Extract melodic pattern metrics
    melodic_uniqueness = profile.get('melodic_motif_uniqueness_ratio', 0.5) or 0.5
    melodic_repetition = profile.get('melodic_motif_repetition_ratio', 0.5) or 0.5
    sequence_coverage = profile.get('sequence_coverage_ratio', 0.0) or 0.0
    
    # Extract rhythmic pattern metrics
    rhythm_uniqueness = profile.get('rhythm_uniqueness_ratio', 0.5) or 0.5
    rhythm_repetition = profile.get('rhythm_repetition_ratio', 0.5) or 0.5
    
    # Calculate facet scores (PREDICTABILITY - higher = more predictable = easier)
    # These are "ease" scores, not difficulty scores
    melodic_predictability = melodic_repetition  # Direct: more repetition = more predictable
    rhythmic_predictability = rhythm_repetition
    structural_regularity = normalize_linear(
        sequence_coverage, 
        PATTERN_SEQUENCE_COVERAGE_LOW, 
        PATTERN_SEQUENCE_COVERAGE_HIGH
    )
    
    facet_scores = {
        'melodic_predictability': round(melodic_predictability, 4),
        'rhythmic_predictability': round(rhythmic_predictability, 4),
        'structural_regularity': round(structural_regularity, 4),
    }
    
    # Convert predictability (ease) to DIFFICULTY for domain scores
    # Invert: high predictability = low difficulty
    melodic_difficulty = 1.0 - melodic_predictability
    rhythmic_difficulty = 1.0 - rhythmic_predictability
    structural_difficulty = 1.0 - structural_regularity
    
    # Primary: sustained cognitive load from unpredictability
    primary = clamp(
        melodic_difficulty * 0.5 +
        rhythmic_difficulty * 0.3 +
        structural_difficulty * 0.2
    )
    
    # Hazard: unpredictability that might cause errors
    # High uniqueness in any facet is a hazard
    hazard = clamp(
        max(melodic_difficulty, rhythmic_difficulty) * 0.7 +
        structural_difficulty * 0.3
    )
    
    overall = clamp(primary * 0.7 + hazard * 0.3)
    
    scores = DomainScores(
        primary=round(primary, 4),
        hazard=round(hazard, 4),
        overall=round(overall, 4),
    )
    
    # Generate flags
    flags = []
    if melodic_uniqueness > 0.8:
        flags.append('high_melodic_variety')
    if melodic_repetition > 0.8:
        flags.append('highly_repetitive_melody')
    if rhythm_uniqueness > 0.8:
        flags.append('high_rhythmic_variety')
    if sequence_coverage > 0.4:
        flags.append('strong_sequence_patterns')
    
    return DomainResult(
        profile=profile,
        facet_scores=facet_scores,
        scores=scores,
        bands=derive_bands(scores),
        flags=flags,
        confidence=1.0 if profile.get('melodic_motif_uniqueness_ratio') is not None else 0.7,
    )


# =============================================================================
# CONVENIENCE / AGGREGATION
# =============================================================================

@dataclass
class AllDomainResults:
    """Container for results from all domains."""
    interval: Optional[DomainResult] = None
    rhythm: Optional[DomainResult] = None
    tonal: Optional[DomainResult] = None
    tempo: Optional[DomainResult] = None
    range: Optional[DomainResult] = None
    throughput: Optional[DomainResult] = None
    pattern: Optional[DomainResult] = None
    
    def to_dict(self) -> Dict[str, Dict[str, Any]]:
        """Convert all domain results to dictionary."""
        result = {}
        if self.interval:
            result['interval'] = self.interval.to_dict()
        if self.rhythm:
            result['rhythm'] = self.rhythm.to_dict()
        if self.tonal:
            result['tonal'] = self.tonal.to_dict()
        if self.tempo:
            result['tempo'] = self.tempo.to_dict()
        if self.range:
            result['range'] = self.range.to_dict()
        if self.throughput:
            result['throughput'] = self.throughput.to_dict()
        if self.pattern:
            result['pattern'] = self.pattern.to_dict()
        return result


def analyze_all_domains(profiles: Dict[str, Dict[str, Any]]) -> AllDomainResults:
    """
    Analyze all domains from their profiles.
    
    Args:
        profiles: Dict mapping domain name to profile dict
            e.g., {"interval": {...}, "rhythm": {...}, ...}
    
    Returns:
        AllDomainResults with results for each domain present in profiles
    """
    results = AllDomainResults()
    
    if 'interval' in profiles:
        results.interval = analyze_interval_domain(profiles['interval'])
    if 'rhythm' in profiles:
        results.rhythm = analyze_rhythm_domain(profiles['rhythm'])
    if 'tonal' in profiles:
        results.tonal = analyze_tonal_domain(profiles['tonal'])
    if 'tempo' in profiles:
        results.tempo = analyze_tempo_domain(profiles['tempo'])
    if 'range' in profiles:
        results.range = analyze_range_domain(profiles['range'])
    if 'throughput' in profiles:
        results.throughput = analyze_throughput_domain(profiles['throughput'])
    if 'pattern' in profiles:
        results.pattern = analyze_pattern_domain(profiles['pattern'])
    
    return results


# =============================================================================
# BACKWARD COMPATIBILITY ALIASES
# =============================================================================

def interval_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_interval_domain(profile).scores


def rhythm_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_rhythm_domain(profile).scores


def tonal_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_tonal_domain(profile).scores


def tempo_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_tempo_domain(profile).scores


def range_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_range_domain(profile).scores


def throughput_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_throughput_domain(profile).scores


def pattern_profile_to_scores(profile: Dict[str, Any]) -> DomainScores:
    """Legacy alias: returns just the scores portion."""
    return analyze_pattern_domain(profile).scores
