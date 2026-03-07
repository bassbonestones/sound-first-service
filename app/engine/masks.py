"""
Database capability mask helper functions.
"""
from typing import List


def get_user_capability_masks(user) -> List[int]:
    """Extract capability masks from user object."""
    return [
        user.cap_mask_0 or 0,
        user.cap_mask_1 or 0,
        user.cap_mask_2 or 0,
        user.cap_mask_3 or 0,
        user.cap_mask_4 or 0,
        user.cap_mask_5 or 0,
        user.cap_mask_6 or 0,
        user.cap_mask_7 or 0,
    ]


def get_material_capability_masks(material) -> List[int]:
    """Extract capability masks from material object."""
    return [
        material.req_cap_mask_0 or 0,
        material.req_cap_mask_1 or 0,
        material.req_cap_mask_2 or 0,
        material.req_cap_mask_3 or 0,
        material.req_cap_mask_4 or 0,
        material.req_cap_mask_5 or 0,
        material.req_cap_mask_6 or 0,
        material.req_cap_mask_7 or 0,
    ]


def set_capability_bit(masks: List[int], bit_index: int) -> List[int]:
    """Set a capability bit in the mask list."""
    if bit_index < 0 or bit_index >= 512:
        return masks
    
    mask_idx = bit_index // 64
    bit_pos = bit_index % 64
    
    new_masks = masks.copy()
    new_masks[mask_idx] = new_masks[mask_idx] | (1 << bit_pos)
    return new_masks


def has_capability_bit(masks: List[int], bit_index: int) -> bool:
    """Check if a capability bit is set in the mask list."""
    if bit_index < 0 or bit_index >= 512:
        return False
    
    mask_idx = bit_index // 64
    bit_pos = bit_index % 64
    
    return (masks[mask_idx] & (1 << bit_pos)) != 0
