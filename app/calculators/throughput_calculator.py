"""
Throughput Calculator

D5 — Density metrics (notes per second, per measure, peak, volatility)
Also includes tempo difficulty score calculation.
"""

from typing import Any, Dict, List, Optional, Tuple


def calculate_density_metrics(
    total_notes: int,
    duration_seconds: float,
    measure_count: int,
    notes_per_measure_list: Optional[List[int]] = None,
    tempo_bpm: int = 120,
    beats_per_measure: float = 4.0,
) -> Tuple[float, float, float, float, Dict[str, Any]]:
    """
    Calculate D5 density metrics including per-measure peak and volatility.
    
    Args:
        total_notes: Total note count
        duration_seconds: Estimated duration in seconds
        measure_count: Number of measures
        notes_per_measure_list: List of note counts per measure (for peak/volatility)
        tempo_bpm: Tempo for converting quarter lengths to seconds
        beats_per_measure: Quarter notes per measure (for NPS calculation)
        
    Returns:
        Tuple of (notes_per_second, notes_per_measure, peak_nps, volatility, raw_dict)
    """
    notes_per_second = total_notes / duration_seconds if duration_seconds > 0 else 0
    notes_per_measure = total_notes / measure_count if measure_count > 0 else 0
    
    # Calculate per-measure density for peak and volatility
    peak_nps = notes_per_second  # Default to average if no per-measure data
    volatility = 0.0
    
    if notes_per_measure_list and len(notes_per_measure_list) > 0:
        # Calculate seconds per measure
        seconds_per_beat = 60.0 / tempo_bpm
        seconds_per_measure = beats_per_measure * seconds_per_beat
        
        # Calculate NPS for each measure
        measure_nps_values = [
            count / seconds_per_measure 
            for count in notes_per_measure_list
            if count > 0  # Skip empty measures (rests)
        ]
        
        if measure_nps_values:
            peak_nps = max(measure_nps_values)
            
            # Volatility = coefficient of variation (std / mean)
            if len(measure_nps_values) > 1:
                mean_nps = sum(measure_nps_values) / len(measure_nps_values)
                if mean_nps > 0:
                    variance = sum((x - mean_nps) ** 2 for x in measure_nps_values) / len(measure_nps_values)
                    std_nps = variance ** 0.5
                    volatility = std_nps / mean_nps
    
    raw = {
        "total_notes": total_notes,
        "duration_seconds": duration_seconds,
        "measure_count": measure_count,
        "peak_nps": round(peak_nps, 4),
        "volatility": round(volatility, 4),
    }
    
    return notes_per_second, notes_per_measure, peak_nps, volatility, raw


def calculate_tempo_difficulty_score(
    bpm: Optional[int],
    rhythm_complexity: float,
    interval_velocity: float,
) -> Tuple[Optional[float], Dict[str, Any]]:
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
