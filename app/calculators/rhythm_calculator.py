"""
Rhythm Complexity Calculator

D3 — Rhythm Complexity Score (0-1) with global and windowed analysis.
"""

import math
from typing import Any, Dict, List, Optional, Tuple
from collections import Counter


# =============================================================================
# WINDOWING CONSTANTS
# =============================================================================

RHYTHM_WINDOW_DURATION_QL = 16.0  # 4 measures of 4/4
RHYTHM_WINDOW_STEP_QL = 4.0       # 1 measure step
RHYTHM_WINDOW_MIN_PIECE_QL = 32.0 # 8 measures minimum for windowing


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
) -> Tuple[float, Dict[str, Any]]:
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

def calculate_rhythm_complexity_windowed(
    note_durations: List[float],
    note_types: List[str],
    has_dots: List[bool],
    has_tuplets: List[bool],
    has_ties: List[bool],
    pitch_changes: List[int],
    offsets: List[float],
) -> Tuple[Optional[float], Optional[float], Dict[str, Any]]:
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
