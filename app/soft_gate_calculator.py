"""
Soft Gate Metrics Calculator for Sound First

Computes staged content dimensions and continuous metrics for adaptive
material filtering. These metrics enable the practice engine to select
appropriately challenging materials based on user's current abilities.

Dimensions:
- D1: Tonal Complexity Stage (0-5) - chromatic vs diatonic content
- D2: Interval Size Stage (0-6) - based on p90 melodic interval
- D3: Rhythm Complexity Score (0-1) - weighted composite
- D4: Range Usage Stage (0-6) - distinct note names A-G
- D5: Density - notes per second and notes per measure

Additional metrics:
- Interval Velocity Score (IVS) - big leaps + fast motion
- Tempo Difficulty Score - BPM × rhythm × interval velocity
"""

import math
import logging
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from collections import Counter

try:
    from music21 import converter, stream, note, chord, key, interval, pitch
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

logger = logging.getLogger(__name__)


# =============================================================================
# DATA CLASSES
# =============================================================================

@dataclass
class SoftGateMetrics:
    """Complete soft gate metrics for a material."""
    # Staged dimensions
    tonal_complexity_stage: int  # 0-5
    interval_size_stage: int  # 0-6
    rhythm_complexity_score: float  # 0.0-1.0 (global score)
    range_usage_stage: int  # 0-6
    
    # Windowed rhythm complexity (for pieces >= 32 qL)
    rhythm_complexity_peak: Optional[float] = None  # max window score
    rhythm_complexity_p95: Optional[float] = None   # 95th percentile window score
    
    # Continuous metrics
    density_notes_per_second: float = 0.0
    note_density_per_measure: float = 0.0
    tempo_difficulty_score: Optional[float] = None  # 0-1, None if no tempo specified
    interval_velocity_score: float = 0.0  # 0-1
    
    # Additional analysis
    unique_pitch_count: int = 0  # 0-12
    largest_interval_semitones: int = 0
    
    # Raw intermediate values (for debugging/tuning)
    raw_metrics: Dict[str, Any] = None


@dataclass
class NoteEvent:
    """Preprocessed note event for IVS calculation."""
    pitch_midi: int
    duration_ql: float  # quarterLength
    offset_ql: float  # onset time


# =============================================================================
# D1 — TONAL COMPLEXITY STAGE
# =============================================================================

def calculate_tonal_complexity_stage(
    pitch_class_count: int,
    accidental_count: int,
    total_note_count: int,
) -> Tuple[int, Dict]:
    """
    Calculate D1 tonal complexity stage (0-5).
    
    Args:
        pitch_class_count: Unique pitch classes (0-12)
        accidental_count: Notes with explicit accidentals
        total_note_count: All pitched notes
        
    Returns:
        Tuple of (stage, raw_metrics_dict)
    """
    if total_note_count == 0:
        return 0, {"accidental_rate": 0, "pitch_class_count": 0}
    
    accidental_rate = accidental_count / total_note_count
    
    raw = {
        "pitch_class_count": pitch_class_count,
        "accidental_count": accidental_count,
        "total_note_count": total_note_count,
        "accidental_rate": accidental_rate,
    }
    
    # Stage determination (each requires the one above)
    if pitch_class_count == 1:
        stage = 0  # Unison
    elif pitch_class_count <= 2 and accidental_rate <= 0.10:
        stage = 1  # Two-note neighbor
    elif pitch_class_count <= 5 and accidental_rate <= 0.10:
        stage = 2  # Diatonic small set
    elif pitch_class_count <= 7 and accidental_rate <= 0.10:
        stage = 3  # Diatonic broader
    elif accidental_rate <= 0.30:
        stage = 4  # Light chromatic
    else:
        stage = 5  # Chromatic
    
    return stage, raw


# =============================================================================
# D2 — INTERVAL SIZE STAGE
# =============================================================================

def calculate_interval_size_stage(
    interval_semitones: List[int],
) -> Tuple[int, Dict]:
    """
    Calculate D2 interval size stage (0-6) based on p90 interval.
    
    Args:
        interval_semitones: List of absolute melodic interval sizes in semitones
        
    Returns:
        Tuple of (stage, raw_metrics_dict)
    """
    if not interval_semitones:
        return 0, {"p90_interval": 0, "max_interval": 0, "interval_count": 0}
    
    # Calculate p90
    sorted_intervals = sorted(interval_semitones)
    p90_idx = int(len(sorted_intervals) * 0.90)
    p90_interval = sorted_intervals[min(p90_idx, len(sorted_intervals) - 1)]
    
    raw = {
        "p90_interval": p90_interval,
        "max_interval": max(interval_semitones),
        "mean_interval": sum(interval_semitones) / len(interval_semitones),
        "interval_count": len(interval_semitones),
    }
    
    # Stage determination based on p90
    if p90_interval <= 0:
        stage = 0  # Unison
    elif p90_interval <= 1:
        stage = 1  # Half step
    elif p90_interval <= 2:
        stage = 2  # Whole step
    elif p90_interval <= 4:
        stage = 3  # Thirds
    elif p90_interval <= 7:
        stage = 4  # Fourths/Fifths
    elif p90_interval <= 9:
        stage = 5  # Sixths
    else:
        stage = 6  # Sevenths/Octave+
    
    return stage, raw


# =============================================================================
# D3 — RHYTHM COMPLEXITY SCORE
# =============================================================================

def calculate_rhythm_complexity_score(
    note_durations: List[float],  # quarterLengths
    note_types: List[str],  # "quarter", "eighth", etc.
    has_dots: List[bool],
    has_tuplets: List[bool],
    has_ties: List[bool],
    pitch_changes: List[int],  # semitone changes between consecutive notes
    offsets: List[float],  # onset times
) -> Tuple[float, Dict]:
    """
    Calculate D3 rhythm complexity score (0-1).
    
    Weighted composite of:
    - F1: Subdivision difficulty (0.30)
    - F2: Rhythm variety (0.15)
    - F3: Switching/entropy (0.20)
    - F4: Irregular features (0.15)
    - F5: Pitch-motion coupling (0.20)
    
    Returns:
        Tuple of (score 0-1, raw_metrics_dict)
    """
    if not note_durations:
        return 0.0, {"f1": 0, "f2": 0, "f3": 0, "f4": 0, "f5": 0}
    
    n = len(note_durations)
    
    # F1: Subdivision difficulty
    subdivision_scores = {
        'whole': 0.0, 'half': 0.1, 'quarter': 0.2, 'eighth': 0.4,
        '16th': 0.6, '32nd': 0.8, '64th': 1.0
    }
    if note_types:
        type_scores = [subdivision_scores.get(t, 0.5) for t in note_types]
        base_score = max(type_scores) if type_scores else 0.2
        fast_notes = sum(1 for d in note_durations if d <= 0.25)
        fast_proportion = fast_notes / n
        f1 = 0.6 * base_score + 0.4 * fast_proportion
    else:
        f1 = 0.2
    
    # F2: Rhythm variety (Shannon entropy)
    if note_types:
        type_counts = Counter(note_types)
        total = len(note_types)
        entropy = -sum((c/total) * math.log2(c/total) for c in type_counts.values() if c > 0)
        max_entropy = math.log2(min(len(type_counts), 6)) if len(type_counts) > 1 else 1
        f2 = entropy / max_entropy if max_entropy > 0 else 0
    else:
        f2 = 0
    
    # F3: Switching rate
    if len(note_types) >= 2:
        switches = sum(1 for i in range(1, len(note_types)) if note_types[i] != note_types[i-1])
        f3 = switches / (len(note_types) - 1)
    else:
        f3 = 0
    
    # F4: Irregular features (dots, tuplets, ties)
    dot_rate = sum(has_dots) / n if has_dots else 0
    tuplet_rate = sum(has_tuplets) / n if has_tuplets else 0
    tie_rate = sum(has_ties) / n if has_ties else 0
    f4 = 0.3 * tie_rate + 0.3 * dot_rate + 0.4 * tuplet_rate
    
    # F5: Rhythm × pitch motion coupling
    if len(pitch_changes) >= 1 and len(offsets) >= 2:
        couplings = []
        for i in range(len(pitch_changes)):
            if i + 1 < len(offsets):
                dt = offsets[i + 1] - offsets[i]
                if dt > 0:
                    speed_factor = 1.0 / (1.0 + dt)
                    interval_factor = min(abs(pitch_changes[i]), 12) / 12
                    couplings.append(speed_factor * interval_factor)
        if couplings:
            # Use p75 to avoid outlier sensitivity
            sorted_couplings = sorted(couplings)
            p75_idx = int(len(sorted_couplings) * 0.75)
            f5 = sorted_couplings[min(p75_idx, len(sorted_couplings) - 1)]
        else:
            f5 = 0
    else:
        f5 = 0
    
    # Weighted composite
    raw_score = 0.30 * f1 + 0.15 * f2 + 0.20 * f3 + 0.15 * f4 + 0.20 * f5
    score = max(0.0, min(1.0, raw_score))
    
    raw = {"f1": f1, "f2": f2, "f3": f3, "f4": f4, "f5": f5, "raw_score": raw_score}
    
    return score, raw


# =============================================================================
# D3 WINDOWED — RHYTHM COMPLEXITY FOR LONG PIECES
# =============================================================================

# Windowing constants
RHYTHM_WINDOW_DURATION_QL = 16.0  # 4 measures of 4/4
RHYTHM_WINDOW_STEP_QL = 4.0       # 1 measure step
RHYTHM_WINDOW_MIN_PIECE_QL = 32.0 # 8 measures minimum for windowing


def calculate_rhythm_complexity_windowed(
    note_durations: List[float],
    note_types: List[str],
    has_dots: List[bool],
    has_tuplets: List[bool],
    has_ties: List[bool],
    pitch_changes: List[int],
    offsets: List[float],
) -> Tuple[Optional[float], Optional[float], Dict]:
    """
    Calculate windowed rhythm complexity for longer pieces.
    
    Uses sliding windows to find peak complexity regions, solving
    the "mostly easy except one hard passage" problem.
    
    Args:
        Same as calculate_rhythm_complexity_score
        
    Returns:
        Tuple of (peak_score, p95_score, raw_metrics_dict)
        Returns (None, None, {}) if piece is too short for windowing
    """
    if not offsets:
        return None, None, {"reason": "no_notes"}
    
    # Calculate piece total duration
    total_duration = max(offsets) + (note_durations[-1] if note_durations else 0)
    
    if total_duration < RHYTHM_WINDOW_MIN_PIECE_QL:
        return None, None, {"reason": "piece_too_short", "duration_ql": total_duration}
    
    # Build windows
    window_scores = []
    window_start = 0.0
    
    while window_start + RHYTHM_WINDOW_DURATION_QL <= total_duration + RHYTHM_WINDOW_STEP_QL:
        window_end = window_start + RHYTHM_WINDOW_DURATION_QL
        
        # Find notes in this window
        indices = [
            i for i, off in enumerate(offsets)
            if window_start <= off < window_end
        ]
        
        if len(indices) >= 2:  # Need at least 2 notes for meaningful analysis
            # Extract windowed data
            w_durations = [note_durations[i] for i in indices]
            w_types = [note_types[i] for i in indices] if note_types else []
            w_dots = [has_dots[i] for i in indices] if has_dots else []
            w_tuplets = [has_tuplets[i] for i in indices] if has_tuplets else []
            w_ties = [has_ties[i] for i in indices] if has_ties else []
            w_offsets = [offsets[i] for i in indices]
            
            # Pitch changes need special handling - they're between notes
            w_pitch_changes = []
            for i in indices[1:]:
                if i - 1 in indices and i - 1 < len(pitch_changes):
                    w_pitch_changes.append(pitch_changes[i - 1])
                elif i <= len(pitch_changes):
                    # Use the pitch change leading into this note
                    w_pitch_changes.append(pitch_changes[i - 1] if i > 0 else 0)
            
            # Calculate window score
            w_score, _ = calculate_rhythm_complexity_score(
                w_durations, w_types, w_dots, w_tuplets, w_ties,
                w_pitch_changes, w_offsets
            )
            window_scores.append(w_score)
        
        window_start += RHYTHM_WINDOW_STEP_QL
    
    if not window_scores:
        return None, None, {"reason": "no_valid_windows"}
    
    # Calculate peak and p95
    sorted_scores = sorted(window_scores)
    peak = max(window_scores)
    
    # P95: 95th percentile
    p95_idx = int(len(sorted_scores) * 0.95)
    p95 = sorted_scores[min(p95_idx, len(sorted_scores) - 1)]
    
    raw = {
        "window_count": len(window_scores),
        "total_duration_ql": total_duration,
        "window_duration_ql": RHYTHM_WINDOW_DURATION_QL,
        "window_step_ql": RHYTHM_WINDOW_STEP_QL,
        "min_window_score": min(window_scores),
        "max_window_score": peak,
        "mean_window_score": sum(window_scores) / len(window_scores),
    }
    
    return peak, p95, raw


# =============================================================================
# D4 — RANGE USAGE STAGE
# =============================================================================

def calculate_range_usage_stage(note_steps: List[str]) -> Tuple[int, Dict]:
    """
    Calculate D4 range usage stage (0-6) based on distinct note names.
    
    Args:
        note_steps: List of note step letters (A-G)
        
    Returns:
        Tuple of (stage, raw_metrics_dict)
    """
    unique_steps = set(note_steps)
    distinct_count = len(unique_steps)
    
    raw = {
        "distinct_note_names": distinct_count,
        "unique_steps": list(unique_steps),
    }
    
    # Stage = count - 1, capped at 6
    stage = min(max(distinct_count - 1, 0), 6)
    
    return stage, raw


# =============================================================================
# D5 — DENSITY
# =============================================================================

def calculate_density_metrics(
    total_notes: int,
    duration_seconds: float,
    measure_count: int,
) -> Tuple[float, float, Dict]:
    """
    Calculate D5 density metrics.
    
    Args:
        total_notes: Total note count
        duration_seconds: Estimated duration in seconds
        measure_count: Number of measures
        
    Returns:
        Tuple of (notes_per_second, notes_per_measure, raw_dict)
    """
    notes_per_second = total_notes / duration_seconds if duration_seconds > 0 else 0
    notes_per_measure = total_notes / measure_count if measure_count > 0 else 0
    
    raw = {
        "total_notes": total_notes,
        "duration_seconds": duration_seconds,
        "measure_count": measure_count,
    }
    
    return notes_per_second, notes_per_measure, raw


# =============================================================================
# INTERVAL VELOCITY SCORE (IVS)
# =============================================================================

def calculate_interval_velocity_score(
    note_events: List[NoteEvent],
    alpha: float = 1.0,
    beta: float = 1.5,
) -> Tuple[float, Dict]:
    """
    Calculate Interval Velocity Score (IVS).
    
    Intuition: Score increases when intervals are larger AND time
    between notes is smaller. A big leap on long notes is not as
    hard as the same leap in 16ths.
    
    Args:
        note_events: List of NoteEvent with pitch_midi, offset_ql
        alpha: Size exponent (default 1.0)
        beta: Speed exponent (default 1.5)
        
    Returns:
        Tuple of (IVS 0-1, raw_metrics_dict)
    """
    if len(note_events) < 2:
        return 0.0, {"interval_count": 0}
    
    contributions = []
    dt_ref = 1.0  # Reference: one quarter note
    
    for i in range(len(note_events) - 1):
        e1, e2 = note_events[i], note_events[i + 1]
        
        # Interval size (semitones)
        delta = abs(e2.pitch_midi - e1.pitch_midi)
        
        # Time between onsets
        dt = e2.offset_ql - e1.offset_ql
        if dt <= 0:
            continue
        
        # Normalize interval (cap at octave)
        size_norm = min(delta, 12) / 12
        
        # Normalize speed
        speed_norm = dt_ref / (dt_ref + dt)
        
        # Combined contribution
        contrib = (size_norm ** alpha) * (speed_norm ** beta)
        contributions.append(contrib)
    
    if not contributions:
        return 0.0, {"interval_count": 0}
    
    # Aggregate using mean + p90
    mean_contrib = sum(contributions) / len(contributions)
    sorted_contribs = sorted(contributions)
    p90_idx = int(len(sorted_contribs) * 0.90)
    p90_contrib = sorted_contribs[min(p90_idx, len(sorted_contribs) - 1)]
    
    ivs_raw = 0.7 * mean_contrib + 0.3 * p90_contrib
    ivs = max(0.0, min(1.0, ivs_raw))
    
    raw = {
        "interval_count": len(contributions),
        "mean_contrib": mean_contrib,
        "p90_contrib": p90_contrib,
        "ivs_raw": ivs_raw,
    }
    
    return ivs, raw


# =============================================================================
# TEMPO DIFFICULTY SCORE
# =============================================================================

def calculate_tempo_difficulty_score(
    bpm: Optional[int],
    rhythm_complexity: float,
    interval_velocity: float,
) -> Tuple[Optional[float], Dict]:
    """
    Calculate tempo difficulty score (0-1).
    
    Formula: normalize(bpm × rhythm_complexity × interval_velocity)
    
    Args:
        bpm: Tempo in BPM (None returns None - no assumed default)
        rhythm_complexity: D3 rhythm score (0-1)
        interval_velocity: IVS score (0-1)
        
    Returns:
        Tuple of (score 0-1 or None if no tempo, raw_dict)
    """
    if bpm is None:
        return None, {"bpm": None, "reason": "no tempo specified in score"}
    
    # Raw product
    raw_score = bpm * rhythm_complexity * interval_velocity
    
    # Normalize to 0-1 (assuming max practical = 200 BPM × 1.0 × 1.0 = 200)
    normalized = raw_score / 200
    score = max(0.0, min(1.0, normalized))
    
    raw = {
        "bpm": bpm,
        "rhythm_complexity": rhythm_complexity,
        "interval_velocity": interval_velocity,
        "raw_score": raw_score,
    }
    
    return score, raw


# =============================================================================
# MAIN CALCULATOR CLASS
# =============================================================================

class SoftGateCalculator:
    """
    Main calculator for soft gate metrics from music21 score.
    """
    
    def __init__(self):
        if not MUSIC21_AVAILABLE:
            raise ImportError("music21 is required for soft gate calculation")
    
    def calculate_from_score(self, score: stream.Score, tempo_bpm: Optional[int] = None) -> SoftGateMetrics:
        """
        Calculate all soft gate metrics from a music21 Score.
        
        Args:
            score: music21 Score object
            tempo_bpm: Override tempo BPM (uses score tempo if None)
            
        Returns:
            SoftGateMetrics dataclass
        """
        # Extract note data
        note_data = self._extract_note_data(score)
        
        # Get tempo
        if tempo_bpm is None:
            tempo_bpm = self._extract_tempo(score)
        
        # Get measure count
        measure_count = self._count_measures(score)
        
        # Calculate each dimension
        d1_stage, d1_raw = calculate_tonal_complexity_stage(
            note_data["pitch_class_count"],
            note_data["accidental_count"],
            note_data["total_notes"],
        )
        
        d2_stage, d2_raw = calculate_interval_size_stage(
            note_data["interval_semitones"],
        )
        
        d3_score, d3_raw = calculate_rhythm_complexity_score(
            note_data["durations"],
            note_data["types"],
            note_data["has_dots"],
            note_data["has_tuplets"],
            note_data["has_ties"],
            note_data["pitch_changes"],
            note_data["offsets"],
        )
        
        # Windowed rhythm complexity for longer pieces
        d3_peak, d3_p95, d3_windowed_raw = calculate_rhythm_complexity_windowed(
            note_data["durations"],
            note_data["types"],
            note_data["has_dots"],
            note_data["has_tuplets"],
            note_data["has_ties"],
            note_data["pitch_changes"],
            note_data["offsets"],
        )
        
        d4_stage, d4_raw = calculate_range_usage_stage(
            note_data["note_steps"],
        )
        
        # Estimate duration
        duration_seconds = self._estimate_duration(score, tempo_bpm or 100, measure_count)
        
        d5_nps, d5_npm, d5_raw = calculate_density_metrics(
            note_data["total_notes"],
            duration_seconds,
            measure_count,
        )
        
        # IVS
        ivs, ivs_raw = calculate_interval_velocity_score(
            note_data["note_events"],
        )
        
        # Tempo difficulty
        tempo_diff, tempo_raw = calculate_tempo_difficulty_score(
            tempo_bpm,
            d3_score,
            ivs,
        )
        
        # Largest interval
        largest_interval = max(note_data["interval_semitones"]) if note_data["interval_semitones"] else 0
        
        return SoftGateMetrics(
            tonal_complexity_stage=d1_stage,
            interval_size_stage=d2_stage,
            rhythm_complexity_score=d3_score,
            rhythm_complexity_peak=d3_peak,
            rhythm_complexity_p95=d3_p95,
            range_usage_stage=d4_stage,
            density_notes_per_second=d5_nps,
            note_density_per_measure=d5_npm,
            tempo_difficulty_score=tempo_diff,
            interval_velocity_score=ivs,
            unique_pitch_count=note_data["pitch_class_count"],
            largest_interval_semitones=largest_interval,
            raw_metrics={
                "d1": d1_raw,
                "d2": d2_raw,
                "d3": d3_raw,
                "d3_windowed": d3_windowed_raw,
                "d4": d4_raw,
                "d5": d5_raw,
                "ivs": ivs_raw,
                "tempo": tempo_raw,
            },
        )
    
    def calculate_from_musicxml(self, musicxml_content: str, tempo_bpm: Optional[int] = None) -> SoftGateMetrics:
        """
        Calculate metrics from MusicXML string.
        
        Args:
            musicxml_content: MusicXML string
            tempo_bpm: Override tempo BPM
            
        Returns:
            SoftGateMetrics dataclass
        """
        score = converter.parse(musicxml_content)
        return self.calculate_from_score(score, tempo_bpm)
    
    def _extract_note_data(self, score: stream.Score) -> Dict:
        """Extract all note-related data for calculations."""
        pitch_classes = set()
        note_steps = []
        accidental_count = 0
        total_notes = 0
        interval_semitones = []
        note_events = []
        
        durations = []
        types = []
        has_dots = []
        has_tuplets = []
        has_ties = []
        pitch_changes = []
        offsets = []
        
        prev_midi = None
        
        # Get key signature for accidental counting
        key_sigs = list(score.recurse().getElementsByClass(key.KeySignature))
        current_key = key_sigs[0] if key_sigs else key.KeySignature(0)
        
        if hasattr(current_key, 'asKey'):
            k = current_key.asKey()
            in_key_pitches = set(p.name for p in k.pitches)
        else:
            in_key_pitches = set(['C', 'D', 'E', 'F', 'G', 'A', 'B'])
        
        for n in score.recurse().notes:
            # Skip grace notes for main analysis
            if hasattr(n, 'duration') and n.duration.isGrace:
                continue
            
            if isinstance(n, note.Note):
                total_notes += 1
                
                # Pitch class
                pitch_classes.add(n.pitch.pitchClass)
                note_steps.append(n.pitch.step)
                
                # Accidentals outside key
                if n.pitch.name not in in_key_pitches:
                    accidental_count += 1
                
                # Interval from previous
                if prev_midi is not None:
                    intv = abs(n.pitch.midi - prev_midi)
                    interval_semitones.append(intv)
                    pitch_changes.append(n.pitch.midi - prev_midi)
                
                # Note event for IVS
                note_events.append(NoteEvent(
                    pitch_midi=n.pitch.midi,
                    duration_ql=n.duration.quarterLength,
                    offset_ql=n.offset,
                ))
                
                prev_midi = n.pitch.midi
                
                # Rhythm data
                durations.append(n.duration.quarterLength)
                types.append(n.duration.type)
                has_dots.append(n.duration.dots > 0)
                has_tuplets.append(bool(n.duration.tuplets))
                has_ties.append(n.tie is not None and n.tie.type in ('start', 'continue'))
                offsets.append(n.offset)
            
            elif isinstance(n, chord.Chord):
                # For chords, use highest note for melody tracking
                total_notes += len(n.pitches)
                for p in n.pitches:
                    pitch_classes.add(p.pitchClass)
                    note_steps.append(p.step)
                    if p.name not in in_key_pitches:
                        accidental_count += 1
                
                # Use top note for intervals
                top_pitch = max(n.pitches, key=lambda p: p.midi)
                if prev_midi is not None:
                    intv = abs(top_pitch.midi - prev_midi)
                    interval_semitones.append(intv)
                    pitch_changes.append(top_pitch.midi - prev_midi)
                
                note_events.append(NoteEvent(
                    pitch_midi=top_pitch.midi,
                    duration_ql=n.duration.quarterLength,
                    offset_ql=n.offset,
                ))
                
                prev_midi = top_pitch.midi
                
                # Rhythm data (once per chord)
                durations.append(n.duration.quarterLength)
                types.append(n.duration.type)
                has_dots.append(n.duration.dots > 0)
                has_tuplets.append(bool(n.duration.tuplets))
                has_ties.append(n.tie is not None)
                offsets.append(n.offset)
        
        return {
            "pitch_class_count": len(pitch_classes),
            "note_steps": note_steps,
            "accidental_count": accidental_count,
            "total_notes": total_notes,
            "interval_semitones": interval_semitones,
            "note_events": note_events,
            "durations": durations,
            "types": types,
            "has_dots": has_dots,
            "has_tuplets": has_tuplets,
            "has_ties": has_ties,
            "pitch_changes": pitch_changes,
            "offsets": offsets,
        }
    
    def _extract_tempo(self, score: stream.Score) -> Optional[int]:
        """Extract tempo BPM from score."""
        from music21 import tempo
        for mm in score.recurse().getElementsByClass(tempo.MetronomeMark):
            if mm.number:
                return int(mm.number)
        return None
    
    def _count_measures(self, score: stream.Score) -> int:
        """Count measures in score."""
        if score.parts:
            return len(score.parts[0].getElementsByClass('Measure'))
        return 0
    
    def _estimate_duration(self, score: stream.Score, bpm: int, measure_count: int) -> float:
        """Estimate duration in seconds."""
        if measure_count == 0 or bpm == 0:
            return 0
        
        # Get beats per measure from time signature
        time_sigs = list(score.recurse().getElementsByClass('TimeSignature'))
        if time_sigs:
            ts = time_sigs[0]
            beats_per_measure = ts.beatCount
            beat_duration = ts.beatDuration.quarterLength
        else:
            beats_per_measure = 4
            beat_duration = 1.0  # Quarter note
        
        # Total beats
        total_beats = measure_count * beats_per_measure
        
        # Seconds per beat
        seconds_per_beat = 60.0 / bpm
        
        # Total duration
        return total_beats * seconds_per_beat


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def calculate_soft_gates(musicxml_content: str, tempo_bpm: Optional[int] = None) -> SoftGateMetrics:
    """
    Convenience function to calculate soft gate metrics from MusicXML.
    
    Args:
        musicxml_content: MusicXML string
        tempo_bpm: Override tempo BPM
        
    Returns:
        SoftGateMetrics dataclass
    """
    calculator = SoftGateCalculator()
    return calculator.calculate_from_musicxml(musicxml_content, tempo_bpm)
