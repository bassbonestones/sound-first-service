"""
Range Usage Calculator

D4 — Range Usage Stage (0-6) based on distinct note names.
"""

from typing import Any, Dict, List, Tuple


def calculate_range_usage_stage(note_steps: List[str]) -> Tuple[int, Dict[str, Any]]:
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
