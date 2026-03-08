"""
Journey stage estimation and adaptive weights.

Estimates user's journey stage based on practice metrics and
provides adaptive weights for session generation.
"""

from typing import Tuple

from .types import JOURNEY_STAGES, JourneyMetrics


def estimate_journey_stage(metrics: JourneyMetrics) -> Tuple[int, str, dict]:
    """
    Estimate user's journey stage based on practice metrics.
    
    IMPORTANT: Per spec, users are never told which stage they are in.
    This is used internally for adaptive behavior only.
    
    Args:
        metrics: JourneyMetrics dataclass with user's practice statistics
        
    Returns:
        Tuple of (stage_number, stage_name, contributing_factors)
    """
    factors = {}
    
    # Stage 6: Lifelong Practice Companion
    # 100+ sessions, 30+ mastered, 6+ months tenure
    if (metrics.total_sessions >= 100 and 
        metrics.mastered_count >= 30 and 
        metrics.days_since_first_session >= 180):
        factors["sessions_threshold"] = "100+ sessions"
        factors["mastery_threshold"] = "30+ mastered materials"
        factors["tenure_threshold"] = "6+ months active"
        return (6, JOURNEY_STAGES[6]["name"], factors)
    
    # Stage 5: Independent Fluency
    # 50+ sessions, 20+ mastered, 3+ self-directed, avg rating >= 4.2
    if (metrics.total_sessions >= 50 and 
        metrics.mastered_count >= 20 and 
        metrics.self_directed_sessions >= 3 and
        metrics.average_rating >= 4.2):
        factors["sessions_threshold"] = "50+ sessions"
        factors["mastery_threshold"] = "20+ mastered materials"
        factors["self_directed"] = "3+ self-directed sessions"
        factors["rating_threshold"] = "avg rating >= 4.2"
        return (5, JOURNEY_STAGES[5]["name"], factors)
    
    # Stage 4: Expanding Musical Identity
    # 30+ sessions, 10+ familiar/mastered, 5+ keys, 15+ caps, avg rating >= 4.0
    familiar_or_better = metrics.familiar_count + metrics.mastered_count
    if (metrics.total_sessions >= 30 and 
        familiar_or_better >= 10 and 
        metrics.unique_keys_practiced >= 5 and
        metrics.capabilities_introduced >= 15 and
        metrics.average_rating >= 4.0):
        factors["sessions_threshold"] = "30+ sessions"
        factors["familiarity_threshold"] = "10+ familiar/mastered materials"
        factors["key_diversity"] = "5+ unique keys practiced"
        factors["capability_breadth"] = "15+ capabilities introduced"
        factors["rating_threshold"] = "avg rating >= 4.0"
        return (4, JOURNEY_STAGES[4]["name"], factors)
    
    # Stage 3: Guided Growth
    # 10+ sessions, 3+ stabilizing+, avg rating >= 3.5
    stabilizing_or_better = metrics.stabilizing_count + metrics.familiar_count + metrics.mastered_count
    if (metrics.total_sessions >= 10 and 
        stabilizing_or_better >= 3 and 
        metrics.average_rating >= 3.5):
        factors["sessions_threshold"] = "10+ sessions"
        factors["stabilizing_threshold"] = "3+ stabilizing/familiar/mastered materials"
        factors["rating_threshold"] = "avg rating >= 3.5"
        return (3, JOURNEY_STAGES[3]["name"], factors)
    
    # Stage 2: Orientation
    # 3+ sessions OR 7+ days since first session
    if metrics.total_sessions >= 3 or metrics.days_since_first_session >= 7:
        if metrics.total_sessions >= 3:
            factors["sessions_threshold"] = "3+ sessions completed"
        if metrics.days_since_first_session >= 7:
            factors["tenure_threshold"] = "7+ days since first session"
        return (2, JOURNEY_STAGES[2]["name"], factors)
    
    # Stage 1: Arrival (default)
    factors["new_user"] = "< 3 sessions, < 7 days"
    return (1, JOURNEY_STAGES[1]["name"], factors)


def get_stage_adaptive_weights(stage: int) -> dict:
    """
    Get adaptive weights for session generation based on journey stage.
    
    These weights adjust curriculum behavior invisibly as the user progresses.
    
    Args:
        stage: Journey stage number (1-6)
        
    Returns:
        Dict of adaptive weights/modifiers
    """
    weights = {
        1: {  # Arrival
            "reinforcement_bias": 0.9,  # Heavy reinforcement
            "novelty_bias": 0.1,
            "max_keys_per_session": 2,
            "preferred_goals": ["learn_by_ear", "fluency_through_keys"],
            "avoid_goals": ["range_expansion", "tempo_build"],
        },
        2: {  # Orientation
            "reinforcement_bias": 0.75,
            "novelty_bias": 0.25,
            "max_keys_per_session": 3,
            "preferred_goals": ["learn_by_ear", "fluency_through_keys", "musical_phrase_flow"],
            "avoid_goals": ["range_expansion"],
        },
        3: {  # Guided Growth
            "reinforcement_bias": 0.6,
            "novelty_bias": 0.4,
            "max_keys_per_session": 4,
            "preferred_goals": None,  # All goals available
            "avoid_goals": [],
        },
        4: {  # Expanding Musical Identity
            "reinforcement_bias": 0.5,
            "novelty_bias": 0.5,
            "max_keys_per_session": 5,
            "preferred_goals": None,
            "avoid_goals": [],
        },
        5: {  # Independent Fluency
            "reinforcement_bias": 0.4,
            "novelty_bias": 0.6,
            "max_keys_per_session": 6,
            "preferred_goals": None,
            "avoid_goals": [],
        },
        6: {  # Lifelong Companion
            "reinforcement_bias": 0.3,
            "novelty_bias": 0.7,
            "max_keys_per_session": 8,
            "preferred_goals": None,
            "avoid_goals": [],
        },
    }
    return weights.get(stage, weights[1])
