"""
Interval utilities for Sound First

Provides ordering and comparison functions for melodic intervals.
Used with User.max_melodic_interval field for progressive interval expansion.

Interval naming convention:
- m2 = minor 2nd (1 semitone)
- M2 = major 2nd (2 semitones)
- m3 = minor 3rd (3 semitones)
- M3 = major 3rd (4 semitones)
- P4 = perfect 4th (5 semitones)
- A4 = augmented 4th / tritone (6 semitones)
- P5 = perfect 5th (7 semitones)
- m6 = minor 6th (8 semitones)
- M6 = major 6th (9 semitones)
- m7 = minor 7th (10 semitones)
- M7 = major 7th (11 semitones)
- P8 = perfect 8th / octave (12 semitones)
"""

# Ordered list of intervals from smallest to largest
# When user masters an interval, they can play materials with that interval or smaller
INTERVAL_ORDER = [
    "m2",   # 1 semitone - half step
    "M2",   # 2 semitones - whole step
    "m3",   # 3 semitones
    "M3",   # 4 semitones
    "P4",   # 5 semitones
    "A4",   # 6 semitones - tritone
    "P5",   # 7 semitones
    "m6",   # 8 semitones
    "M6",   # 9 semitones
    "m7",   # 10 semitones
    "M7",   # 11 semitones
    "P8",   # 12 semitones - octave
]

# Map interval name to semitone count
INTERVAL_SEMITONES = {
    "m2": 1, "M2": 2, "m3": 3, "M3": 4, "P4": 5, "A4": 6,
    "P5": 7, "m6": 8, "M6": 9, "m7": 10, "M7": 11, "P8": 12,
}

# Map interval name to its index in the learning order
INTERVAL_INDEX = {interval: i for i, interval in enumerate(INTERVAL_ORDER)}


def interval_to_semitones(interval: str) -> int:
    """Convert interval name to semitone count."""
    return INTERVAL_SEMITONES.get(interval, 0)


def semitones_to_interval(semitones: int) -> str:
    """Convert semitone count to interval name. Returns None for invalid."""
    for name, st in INTERVAL_SEMITONES.items():
        if st == semitones:
            return name
    return None


def can_play_interval(user_max: str, material_largest: str) -> bool:
    """
    Check if a user can play a material based on interval requirements.
    
    Args:
        user_max: User's max_melodic_interval (e.g., "P5")
        material_largest: Largest interval in the material (e.g., "m6")
    
    Returns:
        True if user can handle the material's intervals
    """
    if not user_max or not material_largest:
        return True  # No restriction if not specified
    
    user_idx = INTERVAL_INDEX.get(user_max, -1)
    material_idx = INTERVAL_INDEX.get(material_largest, -1)
    
    if user_idx < 0 or material_idx < 0:
        return True  # Unknown intervals, allow by default
    
    return user_idx >= material_idx


def get_next_interval(current: str) -> str:
    """
    Get the next interval to learn after mastering current.
    
    Returns None if already at max (P8).
    """
    idx = INTERVAL_INDEX.get(current, -1)
    if idx < 0 or idx >= len(INTERVAL_ORDER) - 1:
        return None
    return INTERVAL_ORDER[idx + 1]


def get_previous_interval(current: str) -> str:
    """
    Get the interval before the current one.
    
    Returns None if already at min (m2).
    """
    idx = INTERVAL_INDEX.get(current, -1)
    if idx <= 0:
        return None
    return INTERVAL_ORDER[idx - 1]


def get_intervals_up_to(interval: str) -> list:
    """
    Get all intervals up to and including the given interval.
    
    Useful for querying all materials the user can handle.
    """
    idx = INTERVAL_INDEX.get(interval, -1)
    if idx < 0:
        return []
    return INTERVAL_ORDER[:idx + 1]


# Default starting interval for new users
DEFAULT_MAX_INTERVAL = "M2"  # Start with whole steps

# Suggested progression milestones
INTERVAL_MILESTONES = {
    "beginner": "M3",      # Up to major 3rd
    "intermediate": "P5",  # Up to perfect 5th
    "advanced": "M7",      # Up to major 7th
    "complete": "P8",      # Octaves and beyond
}
