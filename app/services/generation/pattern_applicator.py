"""Pattern application layer for pitch sequences.

This module applies pattern algorithms to raw pitch sequences,
transforming a simple scale or arpeggio into more complex
practice patterns.
"""

from typing import List, Optional, Tuple

from app.schemas.generation_schemas import (
    ArpeggioPattern,
    ScalePattern,
)


# =============================================================================
# Scale Pattern Functions
# =============================================================================


def apply_scale_pattern(
    pitches: List[int],
    pattern: ScalePattern,
    ascending: bool = True,
    descending_pitches: Optional[List[int]] = None,
) -> List[int]:
    """Apply a pattern algorithm to a scale pitch sequence.
    
    Args:
        pitches: Raw scale pitches (assumed ascending, starting from root).
        pattern: The pattern algorithm to apply.
        ascending: Base direction for the pattern.
        descending_pitches: Optional different pitches for descending
            (used for asymmetric scales like classical melodic minor).
            If None, uses same pitches reversed.
        
    Returns:
        Transformed pitch sequence according to the pattern.
    """
    if len(pitches) < 2:
        return pitches.copy()
    
    # Get the appropriate pattern function
    pattern_fn = _SCALE_PATTERN_MAP.get(pattern)
    if pattern_fn is None:
        # Default to straight
        return pitches.copy() if ascending else list(reversed(pitches))
    
    result = pattern_fn(pitches, ascending, descending_pitches)
    return result


def _straight_up(pitches: List[int], _ascending: bool, _desc: Optional[List[int]] = None) -> List[int]:
    """Return pitches in ascending order."""
    return pitches.copy()


def _straight_down(pitches: List[int], _ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    """Return pitches in descending order."""
    if desc is not None:
        return desc.copy()
    return list(reversed(pitches))


def _straight_up_down(pitches: List[int], _ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    """Return pitches up then down (without repeating top note).
    
    For asymmetric scales (like classical melodic minor), uses
    different descending pitches if provided.
    """
    if len(pitches) < 2:
        return pitches.copy()
    up = pitches.copy()
    if desc is not None:
        # Use provided descending pitches, skip the top note (it's already in 'up')
        down = desc[1:]  # desc is already in descending order
    else:
        down = list(reversed(pitches[:-1]))  # Skip the top note on the way down
    return up + down


def _straight_down_up(pitches: List[int], _ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    """Return pitches down then up (without repeating bottom note).
    
    Example (7-note): 7 6 5 4 3 2 1 2 3 4 5 6 7
    For asymmetric scales, uses different descending pitches if provided.
    """
    if len(pitches) < 2:
        return pitches.copy()
    if desc is not None:
        down = desc.copy()
        up = pitches[1:]  # Skip the bottom note on the way up
    else:
        down = list(reversed(pitches))
        up = pitches[1:]  # Skip the bottom note on the way up
    return down + up


def _pyramid_ascend(pitches: List[int], _ascending: bool, _desc: Optional[List[int]] = None) -> List[int]:
    """Cumulative reach ascending pattern.
    
    Each iteration reaches one degree further, returns to start.
    Example (8 notes): 1-2-1-2-3-2-1-2-3-4-3-2-1-...-2-3-4-5-6-7-8-7-6-5-4-3-2-1
    No repeated tonic between iterations. Ends on tonic.
    """
    if len(pitches) < 2:
        return pitches.copy()
    
    result: List[int] = []
    n = len(pitches)
    
    # First iteration starts with tonic
    result.append(pitches[0])
    
    # Each iteration reaches from index 0 to index reach, then returns to 0
    for reach in range(1, n):
        # Go up to reach (skip index 0, already there from previous return)
        for i in range(1, reach + 1):
            result.append(pitches[i])
        # Come back down to start (including tonic)
        for i in range(reach - 1, -1, -1):
            result.append(pitches[i])
    
    return result


def _pyramid_descend(pitches: List[int], _ascending: bool, _desc: Optional[List[int]] = None) -> List[int]:
    """Cumulative reach descending pattern.
    
    Each iteration reaches one degree further down, returns to top.
    Example (8 notes): 8-7-8-7-6-7-8-7-6-5-6-7-8-...-7-6-5-4-3-2-1-2-3-4-5-6-7-8
    No repeated top note between iterations. Ends on top note.
    """
    if len(pitches) < 2:
        return pitches.copy()
    
    result: List[int] = []
    n = len(pitches)
    
    # First iteration starts with top note
    result.append(pitches[n - 1])
    
    # Work from top (last index) down
    for reach in range(1, n):
        # Go down (skip top, already there from previous return)
        for i in range(n - 2, n - 1 - reach - 1, -1):
            result.append(pitches[i])
        # Come back up to top (including top)
        for i in range(n - reach, n):
            result.append(pitches[i])
    
    return result


def _in_interval(pitches: List[int], interval: int, _ascending: bool, _desc: Optional[List[int]] = None) -> List[int]:
    """Play scale in intervals (3rds, 4ths, etc.) with extension.
    
    Traditional pattern that extends beyond the octave:
    - Ascending: play interval pairs until reaching extension above do
    - Descending: play interval pairs until reaching extension below do
    - End on do
    
    E.g., in 3rds: 1-3, 2-4, 3-5, 4-6, 5-7, 6-8, 7-9, 8-6, 7-5, 6-4, 5-3, 4-2, 3-1, 2-7, 1
    E.g., in 4ths: 1-4, 2-5, 3-6, 4-7, 5-8, 6-9, 7-10, 8-5, 7-4, 6-3, 5-2, 4-1, 3-7, 2-6, 1
    """
    n = len(pitches)
    if n < interval:
        return list(pitches)
    
    # Calculate extension needed: (interval - 2) notes above and below
    extension = max(0, interval - 2)
    
    # Calculate scale intervals from existing pitches
    intervals = [pitches[i+1] - pitches[i] for i in range(n - 1)]
    if not intervals:
        return list(pitches)
    
    # Extend pitches below (prepend notes going down the scale)
    extended = list(pitches)
    for i in range(extension):
        # Use the interval pattern from the bottom of the scale
        interval_idx = (n - 2 - i) % len(intervals)
        new_pitch = extended[0] - intervals[interval_idx]
        extended.insert(0, new_pitch)
    
    # Extend pitches above (append notes going up the scale)
    for i in range(extension):
        # Use the interval pattern from the top of the scale
        interval_idx = i % len(intervals)
        new_pitch = extended[-1] + intervals[interval_idx]
        extended.append(new_pitch)
    
    # Index of bottom do and top do in extended scale
    bottom_do = extension
    top_do = extension + n - 1
    
    result = []
    
    # Ascending phase: pairs starting from bottom do
    # Each pair is (pos, pos + interval - 1)
    pos = bottom_do
    while pos + interval - 1 <= len(extended) - 1:
        result.append(extended[pos])
        result.append(extended[pos + interval - 1])
        pos += 1
    
    # Descending phase: pairs starting from top do
    # Each pair is (pos, pos - interval + 1)
    pos = top_do
    while pos - interval + 1 >= 0:
        result.append(extended[pos])
        result.append(extended[pos - interval + 1])
        pos -= 1
    
    # Final: end on do
    result.append(extended[bottom_do])
    
    return result


def _in_3rds(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _in_interval(pitches, 3, ascending, desc)


def _in_4ths(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _in_interval(pitches, 4, ascending, desc)


def _in_5ths(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _in_interval(pitches, 5, ascending, desc)


def _in_6ths(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _in_interval(pitches, 6, ascending, desc)


def _in_7ths(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _in_interval(pitches, 7, ascending, desc)


def _in_octaves(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _in_interval(pitches, 8, ascending, desc)


def _groups_of_n(pitches: List[int], n: int, ascending: bool, _desc: Optional[List[int]] = None) -> List[int]:
    """Play groups of N consecutive notes, ascending then descending.
    
    Traditional scale practice pattern that extends beyond the octave:
    - Groups of 3: 1-2-3, 2-3-4, ..., 7-8-9, 8, 8-7-6, ..., 2-1-7, 1
    - Groups of 4: 1-2-3-4, 2-3-4-5, ..., 7-8-9-10, 8, 8-7-6-5, ..., 2-1-7-6, 1
    
    The pattern:
    1. Extends (n-2) notes ABOVE the top do (to include re, mi, etc.)
    2. Extends (n-2) notes BELOW the bottom do (to include ti, la, etc.)
    3. Ascends in overlapping groups until reaching above the octave
    4. Descends in overlapping groups until reaching below the starting note
    5. Ends on the starting note (do)
    """
    if len(pitches) < 2:
        return list(pitches)
    
    # Calculate extension needed above and below the scale
    extension = max(0, n - 2)
    
    # Calculate scale intervals from existing pitches
    intervals = [pitches[i+1] - pitches[i] for i in range(len(pitches) - 1)]
    if not intervals:
        return list(pitches)
    
    # Extend pitches below (prepend notes going down the scale)
    extended = list(pitches)
    for i in range(extension):
        # Use intervals in reverse order to go down
        interval_idx = -(i + 1) % len(intervals)
        new_pitch = extended[0] - intervals[interval_idx]
        extended.insert(0, new_pitch)
    
    # Extend pitches above (append notes continuing up the scale)
    for i in range(extension):
        interval_idx = i % len(intervals)
        new_pitch = extended[-1] + intervals[interval_idx]
        extended.append(new_pitch)
    
    # Indices of original start (do) and end (do') in extended scale
    first_idx = extension  # Original starting note
    last_idx = extension + len(pitches) - 1  # Original ending note (octave do)
    
    result = []
    
    # ASCENDING: play groups starting from first_idx
    # Each group of n notes, stepping by 1
    # Continue until the last group ends at or beyond last_idx
    for start in range(first_idx, last_idx):
        for offset in range(n):
            idx = start + offset
            if idx < len(extended):
                result.append(extended[idx])
    
    # DESCENDING: play groups starting from last_idx going down
    # Each group of n notes descending, stepping by 1
    # Continue until we go below first_idx
    for start in range(last_idx, first_idx, -1):
        for offset in range(n):
            idx = start - offset
            if idx >= 0:
                result.append(extended[idx])
    
    # End on the original starting note (do)
    result.append(extended[first_idx])
    
    return result


def _groups_of_3(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _groups_of_n(pitches, 3, ascending, desc)


def _groups_of_4(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _groups_of_n(pitches, 4, ascending, desc)


def _groups_of_5(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _groups_of_n(pitches, 5, ascending, desc)


def _groups_of_6(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _groups_of_n(pitches, 6, ascending, desc)


def _groups_of_7(pitches: List[int], ascending: bool, desc: Optional[List[int]] = None) -> List[int]:
    return _groups_of_n(pitches, 7, ascending, desc)


def _diatonic_triads(pitches: List[int], ascending: bool, _desc: Optional[List[int]] = None) -> List[int]:
    """Build triads on each scale degree with extension past the octave.
    
    Ascending through ALL degrees, descending back through all degrees, ends on do.
    Scales with number of octaves provided.
    
    1 octave: 7 triads up, 7 down, do
    2 octaves: 14 triads up, 14 down, do
    """
    n = len(pitches)
    if n < 5:
        return list(pitches)
    
    # Calculate scale intervals
    intervals = [pitches[i+1] - pitches[i] for i in range(n - 1)]
    if not intervals:
        return list(pitches)
    
    # Number of scale degrees = n - 1 (e.g., 8 notes = 7 degrees, 15 notes = 14 degrees)
    num_degrees = n - 1
    
    # Extend 3 notes above and below for triads
    extension = 3
    extended = list(pitches)
    
    for i in range(extension):
        interval_idx = (len(intervals) - 1 - (i % len(intervals)))
        new_pitch = extended[0] - intervals[interval_idx]
        extended.insert(0, new_pitch)
    
    for i in range(extension):
        interval_idx = i % len(intervals)
        new_pitch = extended[-1] + intervals[interval_idx]
        extended.append(new_pitch)
    
    bottom_do = extension
    top_do = extension + n - 1
    
    result = []
    
    # Ascending: build triads on all degrees from bottom do up
    for i in range(num_degrees):
        idx = bottom_do + i
        result.extend([extended[idx], extended[idx + 2], extended[idx + 4]])
    
    # Descending: build triads from upper do back down through all degrees
    for i in range(num_degrees):
        idx = top_do - i
        result.extend([extended[idx], extended[idx - 2], extended[idx - 4]])
    
    # End on do
    result.append(extended[bottom_do])
    
    return result


def _diatonic_7ths(pitches: List[int], ascending: bool, _desc: Optional[List[int]] = None) -> List[int]:
    """Build 7th chords on each scale degree with extension past the octave.
    
    Ascending through ALL degrees, descending back through all degrees, ends on do.
    Scales with number of octaves provided.
    """
    n = len(pitches)
    if n < 7:
        return list(pitches)
    
    # Calculate scale intervals
    intervals = [pitches[i+1] - pitches[i] for i in range(n - 1)]
    if not intervals:
        return list(pitches)
    
    # Number of scale degrees
    num_degrees = n - 1
    
    # Extend 5 notes above and below for 7th chords
    extension = 5
    extended = list(pitches)
    
    for i in range(extension):
        interval_idx = (len(intervals) - 1 - (i % len(intervals)))
        new_pitch = extended[0] - intervals[interval_idx]
        extended.insert(0, new_pitch)
    
    for i in range(extension):
        interval_idx = i % len(intervals)
        new_pitch = extended[-1] + intervals[interval_idx]
        extended.append(new_pitch)
    
    bottom_do = extension
    top_do = extension + n - 1
    
    result = []
    
    # Ascending: build 7th chords on all degrees from bottom do up
    for i in range(num_degrees):
        idx = bottom_do + i
        result.extend([extended[idx], extended[idx + 2], extended[idx + 4], extended[idx + 6]])
    
    # Descending: build 7th chords from upper do back down
    for i in range(num_degrees):
        idx = top_do - i
        result.extend([extended[idx], extended[idx - 2], extended[idx - 4], extended[idx - 6]])
    
    # End on do
    result.append(extended[bottom_do])
    
    return result


def _broken_chords(pitches: List[int], ascending: bool, _desc: Optional[List[int]] = None) -> List[int]:
    """Broken chords (1-5-3) on each degree with extension past the octave.
    
    Same as diatonic triads but in root-fifth-third order.
    Scales with number of octaves provided.
    """
    n = len(pitches)
    if n < 5:
        return list(pitches)
    
    # Calculate scale intervals
    intervals = [pitches[i+1] - pitches[i] for i in range(n - 1)]
    if not intervals:
        return list(pitches)
    
    # Number of scale degrees
    num_degrees = n - 1
    
    # Extend 3 notes above and below
    extension = 3
    extended = list(pitches)
    
    for i in range(extension):
        interval_idx = (len(intervals) - 1 - (i % len(intervals)))
        new_pitch = extended[0] - intervals[interval_idx]
        extended.insert(0, new_pitch)
    
    for i in range(extension):
        interval_idx = i % len(intervals)
        new_pitch = extended[-1] + intervals[interval_idx]
        extended.append(new_pitch)
    
    bottom_do = extension
    top_do = extension + n - 1
    
    result = []
    
    # Ascending: 1-5-3 pattern on all degrees
    for i in range(num_degrees):
        idx = bottom_do + i
        result.extend([extended[idx], extended[idx + 4], extended[idx + 2]])
    
    # Descending: 1-5-3 (inverted) from upper do back down
    for i in range(num_degrees):
        idx = top_do - i
        result.extend([extended[idx], extended[idx - 4], extended[idx - 2]])
    
    # End on do
    result.append(extended[bottom_do])
    
    return result


def _broken_thirds_neighbor(pitches: List[int], ascending: bool, _desc: Optional[List[int]] = None) -> List[int]:
    """Broken thirds with neighbor pattern (1 octave only).
    
    Pattern: do mi fa re | mi sol la fa | sol ti do la | ti re mi do |
             mi do ti re | do la sol ti | la fa mi sol | fa re do
    
    Ascending cell: [+0, +2, +3, +1] stepping by 2
    Descending cell: [+0, -2, -3, -1] stepping by 2
    
    Goes up to "mi above do", repeats that mi to turn around, comes back down to tonic.
    This pattern only works with 1 octave (8 notes for 7-note scales).
    """
    result = []
    n = len(pitches)
    
    if n < 4:
        return pitches.copy()
    
    # Extend scale by 2 degrees to reach "mi above do"
    extended = list(pitches)
    if n >= 2:
        interval_1 = pitches[1] - pitches[0]  # do-re interval
        extended.append(pitches[-1] + interval_1)  # re above top
    if n >= 3:
        interval_2 = pitches[2] - pitches[1]  # re-mi interval
        extended.append(extended[-1] + interval_2)  # mi above top
    
    n_ext = len(extended)
    mi_index = n_ext - 1  # mi is the last extended note
    
    # Ascending pass: step by 2, cells of [+0, +2, +3, +1]
    i = 0
    while i + 3 <= mi_index:
        result.extend([extended[i], extended[i + 2], extended[i + 3], extended[i + 1]])
        i += 2
    
    # Descending starts from mi
    i = mi_index
    while i - 3 > 0:
        result.extend([extended[i], extended[i - 2], extended[i - 3], extended[i - 1]])
        i -= 2
    
    # Final partial cell ending on tonic (index 0)
    if i >= 3:
        result.extend([extended[i], extended[i - 2], extended[i - 3]])
    
    return result


# Map of scale patterns to their implementation functions
_SCALE_PATTERN_MAP = {
    ScalePattern.STRAIGHT_UP: _straight_up,
    ScalePattern.STRAIGHT_DOWN: _straight_down,
    ScalePattern.STRAIGHT_UP_DOWN: _straight_up_down,
    ScalePattern.STRAIGHT_DOWN_UP: _straight_down_up,
    ScalePattern.PYRAMID_ASCEND: _pyramid_ascend,
    ScalePattern.PYRAMID_DESCEND: _pyramid_descend,
    ScalePattern.IN_3RDS: _in_3rds,
    ScalePattern.IN_4THS: _in_4ths,
    ScalePattern.IN_5THS: _in_5ths,
    ScalePattern.IN_6THS: _in_6ths,
    ScalePattern.IN_7THS: _in_7ths,
    ScalePattern.IN_OCTAVES: _in_octaves,
    ScalePattern.GROUPS_OF_3: _groups_of_3,
    ScalePattern.GROUPS_OF_4: _groups_of_4,
    ScalePattern.GROUPS_OF_5: _groups_of_5,
    ScalePattern.GROUPS_OF_6: _groups_of_6,
    ScalePattern.GROUPS_OF_7: _groups_of_7,
    ScalePattern.DIATONIC_TRIADS: _diatonic_triads,
    ScalePattern.DIATONIC_7THS: _diatonic_7ths,
    ScalePattern.BROKEN_CHORDS: _broken_chords,
    ScalePattern.BROKEN_THIRDS_NEIGHBOR: _broken_thirds_neighbor,
}


# =============================================================================
# Arpeggio Pattern Functions
# =============================================================================


def apply_arpeggio_pattern(
    pitches: List[int],
    pattern: ArpeggioPattern,
    chord_size: int = 3,
    ascending: bool = True,
) -> List[int]:
    """Apply a pattern algorithm to an arpeggio pitch sequence.
    
    Args:
        pitches: Raw arpeggio pitches (chord tones across octaves).
        pattern: The pattern algorithm to apply.
        chord_size: Number of chord tones (3 for triads, 4 for 7ths).
        ascending: Base direction for the pattern.
        
    Returns:
        Transformed pitch sequence according to the pattern.
    """
    if len(pitches) < 2:
        return pitches.copy()
    
    pattern_fn = _ARPEGGIO_PATTERN_MAP.get(pattern)
    if pattern_fn is None:
        return pitches.copy() if ascending else list(reversed(pitches))
    
    return pattern_fn(pitches, chord_size, ascending)


def _arp_straight_up(
    pitches: List[int], _chord_size: int, _ascending: bool
) -> List[int]:
    return pitches.copy()


def _arp_straight_down(
    pitches: List[int], _chord_size: int, _ascending: bool
) -> List[int]:
    return list(reversed(pitches))


def _arp_straight_up_down(
    pitches: List[int], _chord_size: int, _ascending: bool
) -> List[int]:
    if len(pitches) < 2:
        return pitches.copy()
    return pitches + list(reversed(pitches[:-1]))


def _arp_weaving_ascend(
    pitches: List[int], _chord_size: int, _ascending: bool
) -> List[int]:
    """Weaving up: 1-2-1, 2-3-2, ..."""
    result = []
    n = len(pitches)
    for i in range(n - 1):
        result.extend([pitches[i], pitches[i + 1], pitches[i]])
    result.append(pitches[-1])  # End on top
    return result


def _arp_weaving_descend(
    pitches: List[int], _chord_size: int, _ascending: bool
) -> List[int]:
    """Weaving down: 4-3-4, 3-2-3, ..."""
    result = []
    n = len(pitches)
    for i in range(n - 1, 0, -1):
        result.extend([pitches[i], pitches[i - 1], pitches[i]])
    result.append(pitches[0])  # End on bottom
    return result


def _arp_broken_skip_1(
    pitches: List[int], _chord_size: int, ascending: bool
) -> List[int]:
    """Broken: skip every other note. 1-3-2-4-3-5..."""
    result = []
    n = len(pitches)
    
    if ascending:
        for i in range(n - 2):
            result.append(pitches[i])
            result.append(pitches[i + 2])
    else:
        for i in range(n - 1, 1, -1):
            result.append(pitches[i])
            result.append(pitches[i - 2])
    
    return result


def _arp_inversion(
    pitches: List[int], chord_size: int, start_degree: int, ascending: bool
) -> List[int]:
    """Start arpeggio from a specific chord tone.
    
    For a triad: inversion 0=root, 1=1st inv, 2=2nd inv
    """
    if len(pitches) < chord_size:
        return pitches.copy()
    
    result = []
    # Rotate chord tones
    for octave_start in range(0, len(pitches) - chord_size + 1, chord_size):
        octave_pitches = pitches[octave_start:octave_start + chord_size]
        rotated = octave_pitches[start_degree:] + octave_pitches[:start_degree]
        result.extend(rotated)
    
    if not ascending:
        result = list(reversed(result))
    
    return result


def _arp_inversion_root(
    pitches: List[int], chord_size: int, ascending: bool
) -> List[int]:
    return _arp_inversion(pitches, chord_size, 0, ascending)


def _arp_inversion_1st(
    pitches: List[int], chord_size: int, ascending: bool
) -> List[int]:
    return _arp_inversion(pitches, chord_size, 1, ascending)


def _arp_inversion_2nd(
    pitches: List[int], chord_size: int, ascending: bool
) -> List[int]:
    return _arp_inversion(pitches, chord_size, 2, ascending)


def _arp_inversion_3rd(
    pitches: List[int], chord_size: int, ascending: bool
) -> List[int]:
    # Only valid for 7th chords
    if chord_size >= 4:
        return _arp_inversion(pitches, chord_size, 3, ascending)
    return pitches.copy() if ascending else list(reversed(pitches))


def _arp_rolling_alberti(
    pitches: List[int], chord_size: int, _ascending: bool
) -> List[int]:
    """Alberti bass pattern: low-high-mid-high for each chord group.
    
    For C-E-G: C-G-E-G
    """
    if chord_size < 3 or len(pitches) < 3:
        return pitches.copy()
    
    result = []
    for i in range(0, len(pitches) - chord_size + 1, chord_size):
        group = pitches[i:i + chord_size]
        if len(group) >= 3:
            # Pattern: low, high, mid, high
            result.extend([group[0], group[-1], group[1], group[-1]])
    
    return result


def _arp_spread_voicings(
    pitches: List[int], chord_size: int, ascending: bool
) -> List[int]:
    """Spread voicing: space chord tones across wider ranges.
    
    Instead of C4-E4-G4, spread to C4-G4-E5.
    """
    if chord_size < 3 or len(pitches) < chord_size * 2:
        return pitches.copy() if ascending else list(reversed(pitches))
    
    result = []
    # Take root, 5th from same octave, 3rd from next
    for i in range(0, len(pitches) - chord_size, chord_size):
        group = pitches[i:i + chord_size]
        next_group = pitches[i + chord_size:i + chord_size * 2]
        
        if len(group) >= 3 and len(next_group) >= 2:
            # root, 5th, next 3rd
            result.extend([group[0], group[2] if len(group) > 2 else group[-1]])
            result.append(next_group[1] if len(next_group) > 1 else next_group[0])
    
    if not ascending:
        result = list(reversed(result))
    
    return result


def _arp_approach_notes(
    pitches: List[int], _chord_size: int, ascending: bool
) -> List[int]:
    """Add chromatic approach from below each chord tone."""
    result = []
    
    if ascending:
        for p in pitches:
            result.append(p - 1)  # Half step below
            result.append(p)
    else:
        for p in reversed(pitches):
            result.append(p + 1)  # Half step above
            result.append(p)
    
    return result


def _arp_enclosures(
    pitches: List[int], _chord_size: int, ascending: bool
) -> List[int]:
    """Chromatic enclosure: above, below, target for each note."""
    result = []
    
    target_pitches = pitches if ascending else list(reversed(pitches))
    for p in target_pitches:
        result.extend([p + 1, p - 1, p])  # Above, below, target
    
    return result


def _arp_diatonic_sequence(
    pitches: List[int], chord_size: int, ascending: bool
) -> List[int]:
    """Play chord tones in groups, stepping through scale."""
    result = []
    n = len(pitches)
    
    if ascending:
        for i in range(n - chord_size + 1):
            result.extend(pitches[i:i + chord_size])
    else:
        for i in range(n - 1, chord_size - 2, -1):
            result.extend(pitches[i - chord_size + 1:i + 1][::-1])
    
    return result


def _arp_circle_4ths(
    pitches: List[int], _chord_size: int, _ascending: bool
) -> List[int]:
    """Circle of 4ths movement (placeholder - needs root tracking)."""
    # This pattern requires tracking chord roots, not just pitches
    # For now, return a 4th-interval skip pattern
    result = []
    n = len(pitches)
    
    # Approximate: jump by interval of 3 in the arpeggio
    for i in range(0, n, 3):
        if i < n:
            result.append(pitches[i])
    
    return result if result else pitches.copy()


def _arp_circle_5ths(
    pitches: List[int], _chord_size: int, _ascending: bool
) -> List[int]:
    """Circle of 5ths movement (placeholder - needs root tracking)."""
    result = []
    n = len(pitches)
    
    for i in range(0, n, 4):
        if i < n:
            result.append(pitches[i])
    
    return result if result else pitches.copy()


# Map of arpeggio patterns to their implementation functions
_ARPEGGIO_PATTERN_MAP = {
    ArpeggioPattern.STRAIGHT_UP: _arp_straight_up,
    ArpeggioPattern.STRAIGHT_DOWN: _arp_straight_down,
    ArpeggioPattern.STRAIGHT_UP_DOWN: _arp_straight_up_down,
    ArpeggioPattern.WEAVING_ASCEND: _arp_weaving_ascend,
    ArpeggioPattern.WEAVING_DESCEND: _arp_weaving_descend,
    ArpeggioPattern.BROKEN_SKIP_1: _arp_broken_skip_1,
    ArpeggioPattern.INVERSION_ROOT: _arp_inversion_root,
    ArpeggioPattern.INVERSION_1ST: _arp_inversion_1st,
    ArpeggioPattern.INVERSION_2ND: _arp_inversion_2nd,
    ArpeggioPattern.INVERSION_3RD: _arp_inversion_3rd,
    ArpeggioPattern.ROLLING_ALBERTI: _arp_rolling_alberti,
    ArpeggioPattern.SPREAD_VOICINGS: _arp_spread_voicings,
    ArpeggioPattern.APPROACH_NOTES: _arp_approach_notes,
    ArpeggioPattern.ENCLOSURES: _arp_enclosures,
    ArpeggioPattern.DIATONIC_SEQUENCE: _arp_diatonic_sequence,
    ArpeggioPattern.CIRCLE_4THS: _arp_circle_4ths,
    ArpeggioPattern.CIRCLE_5THS: _arp_circle_5ths,
}


# =============================================================================
# Helper Functions
# =============================================================================


def get_supported_scale_patterns() -> list[ScalePattern]:
    """Return list of all supported scale patterns."""
    return list(_SCALE_PATTERN_MAP.keys())


def get_supported_arpeggio_patterns() -> list[ArpeggioPattern]:
    """Return list of all supported arpeggio patterns."""
    return list(_ARPEGGIO_PATTERN_MAP.keys())
