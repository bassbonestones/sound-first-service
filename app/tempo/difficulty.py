"""
Tempo difficulty metric calculations.

Calculates speed and control difficulty scores from tempo profile.

NOTE: These formulas are initial placeholders for future refinement.
The structure supports later tuning of the calculation logic.
"""

from typing import Optional

from .types import TempoProfile, TempoDifficultyMetrics


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
