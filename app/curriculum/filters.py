"""
Material and key filtering functions for curriculum generation.

Handles range-based filtering to ensure materials are playable
within the user's comfortable range.
"""

import json
import random
from typing import Any, List, Optional, Set, Tuple

from .utils import note_to_midi, KEY_TRANSPOSITION_OFFSET


def check_material_in_range(
    material_key: str,
    user_range_low: str,
    user_range_high: str
) -> bool:
    """
    Check if a material's key is within the user's comfortable range.
    
    This is a simplified check - real implementation would analyze
    the material's actual pitch content.
    """
    if not user_range_low or not user_range_high:
        return True  # No range set, allow all
    
    # Get the tonic of the key (e.g., "G minor" -> "G")
    if not material_key:
        return True
    
    key_tonic = material_key.split()[0] if material_key else "C"
    
    # For now, assume the material centers around octave 4
    test_note = f"{key_tonic}4"
    
    low_midi = note_to_midi(user_range_low)
    high_midi = note_to_midi(user_range_high)
    test_midi = note_to_midi(test_note)
    
    # Allow some leeway (material might go a bit outside tonic)
    return (low_midi - 5) <= test_midi <= (high_midi + 5)


def filter_materials_by_capabilities(
    materials: List[Any],
    user_capabilities: List[str]
) -> List[Any]:
    """
    Filter materials to only those the user has capabilities for.
    
    Args:
        materials: List of Material objects
        user_capabilities: List of capability names the user knows
        
    Returns:
        Filtered list of materials
    """
    if not user_capabilities:
        return materials  # No capabilities set, allow all
    
    filtered = []
    for material in materials:
        required = material.required_capability_ids
        if not required:
            filtered.append(material)
            continue
        
        # Parse required capabilities (comma-separated)
        required_caps = [c.strip() for c in required.split(",") if c.strip()]
        
        # Check if user has all required capabilities
        has_all = all(cap in user_capabilities for cap in required_caps)
        if has_all:
            filtered.append(material)
    
    return filtered


def filter_materials_by_range(
    materials: List[Any],
    user_range_low: str,
    user_range_high: str
) -> List[Any]:
    """
    Filter materials to only those within user's comfortable range.
    """
    if not user_range_low or not user_range_high:
        return materials
    
    return [
        m for m in materials 
        if check_material_in_range(m.original_key_center, user_range_low, user_range_high)
    ]


def estimate_material_pitch_range(
    material: Any,
    target_key: str,
    original_key: Optional[str] = None
) -> Tuple[int, int]:
    """
    Estimate the pitch range (low, high) in MIDI when material is transposed.
    
    This uses a simplified model based on pitch_ref_json if available,
    or estimates based on key transposition from original.
    
    Args:
        material: Material object with optional pitch_low_stored, pitch_high_stored
        target_key: Key to transpose to (e.g., "G", "Bb")
        original_key: Original key center (defaults to material.original_key_center)
    
    Returns:
        (low_midi, high_midi) tuple of estimated pitch range
    """
    # Default range if no stored data (assume typical melody range)
    default_low = note_to_midi("C4")  # MIDI 60
    default_high = note_to_midi("C5")  # MIDI 72
    
    # Try to get stored pitch range from material
    stored_low = getattr(material, 'pitch_low_stored', None)
    stored_high = getattr(material, 'pitch_high_stored', None)
    
    if stored_low and stored_high:
        base_low = note_to_midi(stored_low)
        base_high = note_to_midi(stored_high)
    else:
        # Try pitch_ref_json for range info
        try:
            if material.pitch_ref_json:
                ref = json.loads(material.pitch_ref_json)
                if ref.get("low") and ref.get("high"):
                    base_low = note_to_midi(ref["low"])
                    base_high = note_to_midi(ref["high"])
                else:
                    base_low, base_high = default_low, default_high
            else:
                base_low, base_high = default_low, default_high
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            base_low, base_high = default_low, default_high
    
    # Calculate transposition offset
    original = original_key or (material.original_key_center if material else None) or "C major"
    original_tonic = original.split()[0].strip() if original else "C"
    target_tonic = target_key.split()[0].strip() if target_key else "C"
    
    original_offset = KEY_TRANSPOSITION_OFFSET.get(original_tonic, 0)
    target_offset = KEY_TRANSPOSITION_OFFSET.get(target_tonic, 0)
    
    # Transposition shift (keep within octave to avoid extreme shifts)
    shift = target_offset - original_offset
    if shift > 6:
        shift -= 12  # Transpose down instead of way up
    elif shift < -6:
        shift += 12  # Transpose up instead of way down
    
    return (base_low + shift, base_high + shift)


def filter_keys_by_range(
    allowed_keys: List[str],
    material: Any,
    user_range_low: str,
    user_range_high: str,
    original_key: Optional[str] = None
) -> List[str]:
    """
    Filter a list of allowed keys to only those playable within user's range.
    
    Per spec: "For each material: 1) Generate candidate keys, 2) Transpose pitch set,
    3) Filter keys inside comfort range, 4) Select playable keys only."
    
    Args:
        allowed_keys: List of key strings (e.g., ["C", "G", "F", "Bb"])
        material: Material object for pitch range estimation
        user_range_low: User's comfortable low note (e.g., "Bb2")
        user_range_high: User's comfortable high note (e.g., "G5")
        original_key: Material's original key (optional)
    
    Returns:
        List of keys that fit within user's comfortable range
    """
    if not user_range_low or not user_range_high:
        return allowed_keys  # No range constraint
    
    if not allowed_keys:
        return []
    
    user_low_midi = note_to_midi(user_range_low)
    user_high_midi = note_to_midi(user_range_high)
    
    playable_keys = []
    for key in allowed_keys:
        mat_low, mat_high = estimate_material_pitch_range(material, key, original_key)
        
        # Key is playable if material range fits within user range
        # Allow small leeway (1 semitone) for passing tones
        if mat_low >= (user_low_midi - 1) and mat_high <= (user_high_midi + 1):
            playable_keys.append(key)
    
    return playable_keys


def select_key_for_mini_session(
    material: Any,
    user_range_low: str,
    user_range_high: str,
    used_keys: Optional[Set[str]] = None,
    prefer_original: bool = True
) -> str:
    """
    Select an appropriate key for a mini-session.
    
    Priority:
    1. Original key (if fits in range and prefer_original=True)
    2. Random key from allowed_keys that fits in range
    3. Original key (fallback, for listen/sing-only mode)
    
    Args:
        material: Material object with allowed_keys
        user_range_low: User's comfortable low note
        user_range_high: User's comfortable high note
        used_keys: Set of keys already used this session (anti-repetition)
        prefer_original: Whether to prefer the original key
        
    Returns:
        Selected key string, or original_key_center if nothing fits
    """
    if used_keys is None:
        used_keys = set()
    
    original_key = material.original_key_center or "C major"
    original_tonic = original_key.split()[0].strip() if original_key else "C"
    
    # Parse allowed_keys from material
    allowed_keys = []
    if material.allowed_keys:
        allowed_keys = [k.strip() for k in material.allowed_keys.split(",") if k.strip()]
    
    if not allowed_keys:
        allowed_keys = [original_tonic]
    
    # Filter keys by user's range
    playable_keys = filter_keys_by_range(
        allowed_keys, material, user_range_low, user_range_high, original_key
    )
    
    # If nothing is playable, return original (will be listen/sing-only mode)
    if not playable_keys:
        return original_key  # Caller should handle this case
    
    # Remove already-used keys for anti-repetition
    fresh_keys = [k for k in playable_keys if k not in used_keys]
    if not fresh_keys:
        fresh_keys = playable_keys  # Reset if all used
    
    # Prefer original key if requested and available
    if prefer_original and original_tonic in fresh_keys:
        return f"{original_tonic} major"  # Append mode for consistency
    
    # Random selection from playable keys
    selected = random.choice(fresh_keys)
    return f"{selected} major"
