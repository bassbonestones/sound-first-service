"""
Tonal Complexity Calculator

D1 — Tonal Complexity Stage (0-5) based on chromatic vs diatonic content.
"""

from typing import Any, Dict, Tuple


def calculate_tonal_complexity_stage(
    pitch_class_count: int,
    accidental_count: int,
    total_note_count: int,
) -> Tuple[int, Dict[str, Any]]:
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
