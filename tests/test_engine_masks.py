"""
Tests for engine/masks.py

Tests for capability mask helper functions.
"""

import pytest
from dataclasses import dataclass

from app.engine.masks import (
    get_user_capability_masks,
    get_material_capability_masks,
    set_capability_bit,
    has_capability_bit,
)


@dataclass
class MockUser:
    """Mock user object for testing."""
    cap_mask_0: int = 0
    cap_mask_1: int = 0
    cap_mask_2: int = 0
    cap_mask_3: int = 0
    cap_mask_4: int = 0
    cap_mask_5: int = 0
    cap_mask_6: int = 0
    cap_mask_7: int = 0


@dataclass
class MockMaterial:
    """Mock material object for testing."""
    req_cap_mask_0: int = 0
    req_cap_mask_1: int = 0
    req_cap_mask_2: int = 0
    req_cap_mask_3: int = 0
    req_cap_mask_4: int = 0
    req_cap_mask_5: int = 0
    req_cap_mask_6: int = 0
    req_cap_mask_7: int = 0


class TestGetUserCapabilityMasks:
    """Tests for get_user_capability_masks function."""

    def test_all_zeros(self):
        """Should return all zeros for new user."""
        user = MockUser()
        masks = get_user_capability_masks(user)
        
        assert len(masks) == 8
        assert all(m == 0 for m in masks)

    def test_extracts_all_masks(self):
        """Should extract all 8 capability masks."""
        user = MockUser(
            cap_mask_0=1,
            cap_mask_1=2,
            cap_mask_2=4,
            cap_mask_3=8,
            cap_mask_4=16,
            cap_mask_5=32,
            cap_mask_6=64,
            cap_mask_7=128
        )
        masks = get_user_capability_masks(user)
        
        assert masks == [1, 2, 4, 8, 16, 32, 64, 128]

    def test_handles_none_values(self):
        """Should treat None as 0."""
        user = MockUser()
        user.cap_mask_0 = None
        user.cap_mask_1 = 42
        
        masks = get_user_capability_masks(user)
        
        assert masks[0] == 0
        assert masks[1] == 42


class TestGetMaterialCapabilityMasks:
    """Tests for get_material_capability_masks function."""

    def test_extracts_required_masks(self):
        """Should extract required capability masks."""
        material = MockMaterial(
            req_cap_mask_0=15,
            req_cap_mask_1=31
        )
        masks = get_material_capability_masks(material)
        
        assert len(masks) == 8
        assert masks[0] == 15
        assert masks[1] == 31

    def test_handles_none_values(self):
        """Should treat None as 0."""
        material = MockMaterial()
        material.req_cap_mask_0 = None
        material.req_cap_mask_2 = 99
        
        masks = get_material_capability_masks(material)
        
        assert masks[0] == 0
        assert masks[2] == 99


class TestSetCapabilityBit:
    """Tests for set_capability_bit function."""

    def test_set_bit_in_first_mask(self):
        """Should set bit in first mask (0-63)."""
        masks = [0] * 8
        result = set_capability_bit(masks, 5)
        
        assert result[0] == (1 << 5)
        assert result[1:] == [0] * 7

    def test_set_bit_in_second_mask(self):
        """Should set bit in second mask (64-127)."""
        masks = [0] * 8
        result = set_capability_bit(masks, 70)  # 70 = 64 + 6
        
        assert result[0] == 0
        assert result[1] == (1 << 6)

    def test_set_bit_preserves_existing(self):
        """Should preserve existing bits."""
        masks = [1, 0, 0, 0, 0, 0, 0, 0]
        result = set_capability_bit(masks, 5)
        
        assert result[0] == (1 | (1 << 5))

    def test_negative_index_ignored(self):
        """Should ignore negative bit index."""
        masks = [0] * 8
        result = set_capability_bit(masks, -1)
        
        assert result == masks

    def test_out_of_range_index_ignored(self):
        """Should ignore bit index >= 512."""
        masks = [0] * 8
        result = set_capability_bit(masks, 512)
        
        assert result == masks

    def test_does_not_modify_original(self):
        """Should not modify original mask list."""
        masks = [0] * 8
        result = set_capability_bit(masks, 10)
        
        assert masks == [0] * 8
        assert result[0] == (1 << 10)


class TestHasCapabilityBit:
    """Tests for has_capability_bit function."""

    def test_bit_is_set(self):
        """Should return True when bit is set."""
        masks = [0] * 8
        masks[0] = 1 << 5
        
        assert has_capability_bit(masks, 5) is True

    def test_bit_not_set(self):
        """Should return False when bit not set."""
        masks = [0] * 8
        
        assert has_capability_bit(masks, 5) is False

    def test_check_in_second_mask(self):
        """Should check bit in second mask."""
        masks = [0] * 8
        masks[1] = 1 << 10
        
        assert has_capability_bit(masks, 64 + 10) is True
        assert has_capability_bit(masks, 64 + 11) is False

    def test_negative_index(self):
        """Should return False for negative index."""
        masks = [255] * 8
        
        assert has_capability_bit(masks, -1) is False

    def test_out_of_range_index(self):
        """Should return False for index >= 512."""
        masks = [255] * 8
        
        assert has_capability_bit(masks, 512) is False

    def test_multiple_bits_set(self):
        """Should work with multiple bits set."""
        masks = [0] * 8
        masks[0] = 0b11010  # bits 1, 3, 4 set
        
        assert has_capability_bit(masks, 0) is False
        assert has_capability_bit(masks, 1) is True
        assert has_capability_bit(masks, 2) is False
        assert has_capability_bit(masks, 3) is True
        assert has_capability_bit(masks, 4) is True
