"""
Session Configuration - All configurable weights and parameters
Per spec: Practice Session Selection Logic v1
"""

# =============================================================================
# CAPABILITY WEIGHTS (Macro Allocation)
# Controls which type of practice is selected
# =============================================================================
CAPABILITY_WEIGHTS = {
    "repertoire_fluency": 0.30,    # Tunes / repertoire work (highest priority per spec)
    "technique": 0.20,             # Technique / articulation
    "range_expansion": 0.10,       # Range expansion (limited due to fatigue risk)
    "rhythm": 0.15,                # Rhythm work
    "ear_training": 0.15,          # Ear-only mini-sessions
    "articulation": 0.10,          # Articulation clarity
}

# =============================================================================
# DIFFICULTY WEIGHTS
# "Distance from comfort" - not general skill level
# =============================================================================
DIFFICULTY_WEIGHTS = {
    "easy": 0.50,      # Well within comfort zone
    "medium": 0.35,    # Slight stretch
    "hard": 0.15,      # Just outside comfort (not punishing)
}

# =============================================================================
# NOVELTY VS REINFORCEMENT
# Novelty = new material, new key, new focus card, new note target
# Reinforcement = revisit known material still being stabilized
# =============================================================================
NOVELTY_REINFORCEMENT = {
    "novelty": 0.20,        # 20% new material
    "reinforcement": 0.80,  # 80% review/stabilize
}

# =============================================================================
# FATIGUE ROUTING ADJUSTMENTS
# Modifies weights based on fatigue level
# User's model:
#   1-2: Normal operation (no changes)
#   3-4: Avoid playing that could cause bad habits (reduce intensity)
#   5: Prompt for stop, cooldown, or ear training only
# =============================================================================
FATIGUE_CAPABILITY_MODIFIERS = {
    # Fatigue 1-2: Normal operation (no changes)
    1: {},
    2: {},
    # Fatigue 3-4: Avoid playing that could cause bad habits
    # Reduce physical intensity, favor ear work and easy playing
    3: {
        "range_expansion": 0.0,     # No range work when fatigue sets in
        "technique": 0.6,           # Reduce intense technique work
        "articulation": 0.7,        # Lighter articulation focus
        "ear_training": 1.4,        # Boost ear work
        "repertoire_fluency": 1.2,  # Favor familiar material
        "rhythm": 1.0,              # Rhythm OK (less physical)
    },
    4: {
        "range_expansion": 0.0,     # Never at fatigue 4
        "technique": 0.3,           # Strongly reduce technique
        "articulation": 0.4,        # Reduce articulation intensity
        "ear_training": 1.8,        # Strong boost to ear work
        "repertoire_fluency": 1.0,  # Easy, familiar playing OK
        "rhythm": 0.8,              # Light rhythm work
    },
    # Fatigue 5: Should prompt user - if they continue, ear-only mode
    5: {
        "range_expansion": 0.0,
        "technique": 0.0,
        "articulation": 0.0,
        "ear_training": 3.0,        # Heavily favor ear training
        "repertoire_fluency": 0.3,  # Only very light playing
        "rhythm": 0.2,              # Minimal
    },
}

# =============================================================================
# TIME BUDGETING
# Average durations for mini-sessions by capability
# =============================================================================
AVG_MINI_SESSION_MINUTES = {
    "repertoire_fluency": 5.0,
    "technique": 4.0,
    "range_expansion": 3.0,
    "rhythm": 4.0,
    "ear_training": 3.0,
    "articulation": 4.0,
    "default": 4.0,
}

# Minimum time remaining before switching to wrap-up mode
WRAP_UP_THRESHOLD_MINUTES = 3.0

# =============================================================================
# INTENSITY SETTINGS
# Controls curriculum size per intensity level
# =============================================================================
INTENSITY_WEIGHTS = {
    "small": 0.40,
    "medium": 0.45,
    "large": 0.15,
}

# Keys per intensity level (for key-based goals)
KEYS_PER_INTENSITY = {
    "small": 2,
    "medium": 4,
    "large": 6,
}

# =============================================================================
# ANTI-REPETITION RULES
# =============================================================================
MAX_CAPABILITY_STREAK = 2          # Don't do same capability more than 2x in a row
MAX_MATERIAL_REPEATS_PER_SESSION = 1  # Material can only appear once per session
MAX_KEY_REPEATS_PER_MINI_SESSION = 1  # Key can only appear once within a mini-session

# =============================================================================
# NOTATION / SHEET MUSIC DISPLAY
# =============================================================================
NOTES_SHOWN_PERCENTAGE = 0.20  # Show notation 20% of the time

# =============================================================================
# RANGE SAFETY LIMITS
# =============================================================================
MAX_RANGE_ATTEMPTS_PER_MINI_SESSION = 3
RANGE_RECOVERY_AFTER_ATTEMPTS = 1  # Insert recovery after every N PLAY steps

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
import random
from typing import Any, Dict, List, Optional

def weighted_choice(weights_dict: Dict[str, float]) -> str:
    """Select a key from a dict of {key: weight} probabilistically."""
    items = list(weights_dict.keys())
    weights = list(weights_dict.values())
    total = sum(weights)
    if total == 0:
        return items[0] if items else ""
    normalized = [w / total for w in weights]
    return str(random.choices(items, weights=normalized, k=1)[0])


def get_adjusted_capability_weights(fatigue: int) -> Dict[str, float]:
    """Get capability weights adjusted for current fatigue level."""
    base_weights = CAPABILITY_WEIGHTS.copy()
    modifiers = FATIGUE_CAPABILITY_MODIFIERS.get(fatigue, {})
    
    for capability, modifier in modifiers.items():
        if capability in base_weights:
            base_weights[capability] *= modifier
    
    return base_weights


def select_novelty_or_reinforcement() -> str:
    """Probabilistically choose novelty vs reinforcement mode."""
    return weighted_choice(NOVELTY_REINFORCEMENT)


def select_difficulty() -> str:
    """Probabilistically choose difficulty level."""
    return weighted_choice(DIFFICULTY_WEIGHTS)


def select_intensity(time_remaining: Optional[float] = None) -> str:
    """Select intensity, constrained by time remaining."""
    weights = INTENSITY_WEIGHTS.copy()
    
    # If low on time, prefer smaller intensities
    if time_remaining is not None:
        if time_remaining < 5:
            weights["large"] = 0
            weights["medium"] *= 0.5
        elif time_remaining < 10:
            weights["large"] *= 0.3
    
    return weighted_choice(weights)


def select_capability(fatigue: int, recent_capabilities: Optional[List[str]] = None, time_remaining: Optional[float] = None) -> str:
    """
    Select next capability bucket probabilistically.
    Considers fatigue, anti-repetition, and time constraints.
    """
    weights = get_adjusted_capability_weights(fatigue)
    
    # Anti-repetition: reduce weight if capability was used recently
    if recent_capabilities:
        # Check for streaks
        if len(recent_capabilities) >= MAX_CAPABILITY_STREAK:
            last_n = recent_capabilities[-MAX_CAPABILITY_STREAK:]
            if len(set(last_n)) == 1:  # All the same
                # Strongly reduce this capability
                streak_cap = last_n[0]
                if streak_cap in weights:
                    weights[streak_cap] *= 0.1
    
    # Time constraint: if wrapping up, prefer ear training or light work
    if time_remaining is not None and time_remaining < WRAP_UP_THRESHOLD_MINUTES:
        weights["range_expansion"] = 0
        weights["technique"] *= 0.3
        weights["ear_training"] *= 2.0
    
    return weighted_choice(weights)


def estimate_mini_session_duration(capability: str, intensity: str) -> float:
    """Estimate how long a mini-session will take."""
    base = AVG_MINI_SESSION_MINUTES.get(capability, AVG_MINI_SESSION_MINUTES["default"])
    
    intensity_multipliers = {
        "small": 0.7,
        "medium": 1.0,
        "large": 1.5,
    }
    
    return base * intensity_multipliers.get(intensity, 1.0)


def should_show_notation() -> bool:
    """Decide whether to show notation based on configured percentage."""
    return random.random() < NOTES_SHOWN_PERCENTAGE
