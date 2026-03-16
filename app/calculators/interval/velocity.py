"""
Interval Velocity Score (IVS) Calculation

Measures interval difficulty considering both size and speed.
"""

from typing import Any, Dict, List, Optional, Tuple

from app.calculators.models import NoteEvent


# Windowing constants for IVS
IVS_WINDOW_DURATION_QL = 16.0  # 4 measures of 4/4
IVS_WINDOW_STEP_QL = 4.0       # 1 measure step
IVS_WINDOW_MIN_PIECE_QL = 32.0 # 8 measures minimum for windowing


def calculate_interval_velocity_score(
    note_events: List[NoteEvent],
    alpha: float = 1.0,
    beta: float = 1.5,
) -> Tuple[float, Dict[str, Any]]:
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


def calculate_interval_velocity_windowed(
    note_events: List[NoteEvent],
    alpha: float = 1.0,
    beta: float = 1.5,
) -> Tuple[Optional[float], Optional[float], Dict[str, Any]]:
    """
    Calculate windowed interval velocity score for longer pieces.
    
    Uses sliding windows to find peak IVS regions, solving
    the "mostly easy except one hard passage" problem.
    
    Args:
        note_events: List of NoteEvent with pitch_midi, offset_ql
        alpha: Size exponent (default 1.0)
        beta: Speed exponent (default 1.5)
        
    Returns:
        Tuple of (peak_score, p95_score, raw_metrics_dict)
        Returns (None, None, {}) if piece is too short for windowing
    """
    if len(note_events) < 2:
        return None, None, {"reason": "no_events"}
    
    # Calculate piece total duration from last note offset + duration
    total_duration = max(e.offset_ql + e.duration_ql for e in note_events)
    
    if total_duration < IVS_WINDOW_MIN_PIECE_QL:
        return None, None, {"reason": "piece_too_short", "duration_ql": total_duration}
    
    # Build windows
    window_scores = []
    window_start = 0.0
    
    while window_start + IVS_WINDOW_DURATION_QL <= total_duration + IVS_WINDOW_STEP_QL:
        window_end = window_start + IVS_WINDOW_DURATION_QL
        
        # Find notes in this window
        window_events = [
            e for e in note_events
            if window_start <= e.offset_ql < window_end
        ]
        
        if len(window_events) >= 2:
            # Calculate window IVS
            w_score, _ = calculate_interval_velocity_score(window_events, alpha, beta)
            window_scores.append(w_score)
        
        window_start += IVS_WINDOW_STEP_QL
    
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
        "window_duration_ql": IVS_WINDOW_DURATION_QL,
        "window_step_ql": IVS_WINDOW_STEP_QL,
        "min_window_score": min(window_scores),
        "max_window_score": peak,
        "mean_window_score": sum(window_scores) / len(window_scores),
    }
    
    return peak, p95, raw
