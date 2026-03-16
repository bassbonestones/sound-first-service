"""
Focus targeting functions.
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from .config import DEFAULT_CONFIG, EngineConfig
from .models import FocusTarget


def compute_focus_score(
    pitch_midi: int,
    ema_score: float,
    last_attempt_at: Optional[datetime],
    user_range_center: int,
    now: Optional[datetime] = None,
    config: Optional[EngineConfig] = None
) -> float:
    """
    Compute focus targeting score for a pitch/focus combo.
    
    focusScore = 1.0*badness + 0.3*spacing - 0.3*extremePenalty
    
    Where:
    - badness = 1 - normalize(ema)
    - spacing = daysSince(last_attempt)
    - extremePenalty = distance from range center * avoid_extremes_factor
    """
    if config is None:
        config = DEFAULT_CONFIG
    if now is None:
        now = datetime.now()
    
    # Badness (lower EMA = higher badness)
    normalized_ema = (ema_score - 1.0) / 4.0 if ema_score > 0 else 0.0
    normalized_ema = max(0.0, min(1.0, normalized_ema))
    badness = 1.0 - normalized_ema
    
    # Spacing (days since last attempt)
    if last_attempt_at is None:
        spacing = 7.0  # Default for never attempted
    else:
        spacing = (now - last_attempt_at).total_seconds() / 86400
    spacing = min(spacing, 30.0)  # Cap at 30 days
    spacing = spacing / 30.0  # Normalize to 0-1
    
    # Extreme penalty (distance from center)
    distance = abs(pitch_midi - user_range_center)
    max_distance = 24  # 2 octaves
    extreme_penalty = (distance / max_distance) * config.avoid_extremes_factor
    
    return 1.0 * badness + 0.3 * spacing - 0.3 * extreme_penalty


def select_focus_targets(
    material_pitches: List[int],
    focus_card_ids: List[int],
    pitch_focus_stats: Dict[Tuple[int, int], Tuple[float, Optional[datetime]]],
    user_range_center: int,
    config: Optional[EngineConfig] = None
) -> List[FocusTarget]:
    """
    Select pitch/focus combinations to emphasize in this material.
    
    Returns top FOCUS_TARGETS_PER_MATERIAL by score.
    """
    if config is None:
        config = DEFAULT_CONFIG
    
    now = datetime.now()
    
    # Score all pitch/focus combinations
    candidates = []
    for pitch in material_pitches:
        for focus_id in focus_card_ids:
            key = (pitch, focus_id)
            ema, last_attempt = pitch_focus_stats.get(key, (0.0, None))
            
            score = compute_focus_score(
                pitch, ema, last_attempt, user_range_center, now, config
            )
            
            candidates.append(FocusTarget(
                pitch_midi=pitch,
                focus_card_id=focus_id,
                ema_score=ema,
                score=score
            ))
    
    # Sort by score (descending) and return top N
    candidates.sort(key=lambda x: x.score, reverse=True)
    return candidates[:config.focus_targets_per_material]
