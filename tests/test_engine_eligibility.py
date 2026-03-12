"""
Tests for engine eligibility checking functions.

Tests capability bitmask and content dimension eligibility checks.
"""

import pytest
from app.engine.eligibility import (
    check_bitmask_eligibility,
    check_content_dimension_eligibility,
    is_material_eligible,
)


class TestCheckBitmaskEligibility:
    """Test check_bitmask_eligibility function."""
    
    def test_empty_masks_are_eligible(self):
        """Empty masks should be eligible."""
        assert check_bitmask_eligibility([], []) is True
    
    def test_user_has_all_required_bits(self):
        """User with all required bits should be eligible."""
        user_masks = [0b1111]  # User has bits 0,1,2,3
        material_masks = [0b0101]  # Material requires bits 0,2
        assert check_bitmask_eligibility(user_masks, material_masks) is True
    
    def test_user_missing_required_bit(self):
        """User missing a required bit should not be eligible."""
        user_masks = [0b0101]  # User has bits 0,2
        material_masks = [0b0111]  # Material requires bits 0,1,2
        assert check_bitmask_eligibility(user_masks, material_masks) is False
    
    def test_user_has_extra_bits(self):
        """User with extra bits beyond required should be eligible."""
        user_masks = [0b11111111]  # User has many bits
        material_masks = [0b00000011]  # Material only requires 2
        assert check_bitmask_eligibility(user_masks, material_masks) is True
    
    def test_multiple_mask_integers(self):
        """Should check across multiple mask integers."""
        user_masks = [0xFF, 0xFF]  # Full bits in both
        material_masks = [0x0F, 0x0F]  # Partial requirements
        assert check_bitmask_eligibility(user_masks, material_masks) is True
    
    def test_failure_in_second_mask(self):
        """Failure in second mask should still fail."""
        user_masks = [0xFF, 0x00]  # Second mask is empty
        material_masks = [0x0F, 0x01]  # Second mask has requirement
        assert check_bitmask_eligibility(user_masks, material_masks) is False
    
    def test_user_has_more_masks_than_material(self):
        """User having more mask ints should not cause issues."""
        user_masks = [0xFF, 0xFF, 0xFF]
        material_masks = [0x0F]
        assert check_bitmask_eligibility(user_masks, material_masks) is True
    
    def test_material_has_more_masks_than_user(self):
        """Handles when material has more masks than user."""
        user_masks = [0xFF]
        material_masks = [0x0F, 0x00]  # Extra mask but no requirements
        assert check_bitmask_eligibility(user_masks, material_masks) is True


class TestCheckContentDimensionEligibility:
    """Test check_content_dimension_eligibility function."""
    
    def test_empty_dicts_are_eligible(self):
        """Empty dicts should be eligible."""
        assert check_content_dimension_eligibility({}, {}) is True
    
    def test_within_limits(self):
        """Material stages within user limits should be eligible."""
        material = {'rhythm_complexity_stage': 2, 'range_usage_stage': 1}
        user = {'rhythm_complexity_stage': 3, 'range_usage_stage': 3}
        assert check_content_dimension_eligibility(material, user) is True
    
    def test_at_limit(self):
        """Material stages at user limits should be eligible."""
        material = {'rhythm_complexity_stage': 3}
        user = {'rhythm_complexity_stage': 3}
        assert check_content_dimension_eligibility(material, user) is True
    
    def test_exceeds_limit(self):
        """Material stages exceeding user limits should not be eligible."""
        material = {'rhythm_complexity_stage': 4}
        user = {'rhythm_complexity_stage': 3}
        assert check_content_dimension_eligibility(material, user) is False
    
    def test_one_dimension_exceeds(self):
        """One dimension exceeding should fail even if others pass."""
        material = {'rhythm_complexity_stage': 2, 'range_usage_stage': 5}
        user = {'rhythm_complexity_stage': 3, 'range_usage_stage': 3}
        assert check_content_dimension_eligibility(material, user) is False
    
    def test_material_has_extra_dimensions(self):
        """Material with dimensions not in user caps should pass."""
        material = {'rhythm_complexity_stage': 2, 'extra_dimension': 5}
        user = {'rhythm_complexity_stage': 3}  # No cap on extra_dimension
        assert check_content_dimension_eligibility(material, user) is True
    
    def test_none_stage_is_ignored(self):
        """None stage values should be ignored."""
        material = {'rhythm_complexity_stage': None, 'range_usage_stage': 2}
        user = {'rhythm_complexity_stage': 0, 'range_usage_stage': 3}
        # rhythm_complexity_stage is None, so ignored; range_usage_stage passes
        assert check_content_dimension_eligibility(material, user) is True


class TestIsMaterialEligible:
    """Test is_material_eligible combined check."""
    
    def test_no_license_fails(self):
        """Material without license should not be eligible."""
        assert is_material_eligible(
            user_masks=[0xFF],
            material_masks=[0x0F],
            has_license=False
        ) is False
    
    def test_with_license_passes_bitmask(self):
        """Material with license and matching bitmask should pass."""
        assert is_material_eligible(
            user_masks=[0xFF],
            material_masks=[0x0F],
            has_license=True
        ) is True
    
    def test_fails_bitmask_check(self):
        """Should fail if bitmask check fails."""
        assert is_material_eligible(
            user_masks=[0x00],  # No capabilities
            material_masks=[0x0F],  # Requires capabilities
            has_license=True
        ) is False
    
    def test_fails_dimension_check(self):
        """Should fail if dimension check fails."""
        assert is_material_eligible(
            user_masks=[0xFF],
            material_masks=[0x0F],
            material_stages={'rhythm_complexity_stage': 5},
            user_max_stages={'rhythm_complexity_stage': 3},
            has_license=True
        ) is False
    
    def test_passes_all_checks(self):
        """Should pass when all checks pass."""
        assert is_material_eligible(
            user_masks=[0xFF],
            material_masks=[0x0F],
            material_stages={'rhythm_complexity_stage': 2},
            user_max_stages={'rhythm_complexity_stage': 3},
            has_license=True
        ) is True
    
    def test_no_dimension_check_when_missing(self):
        """Should skip dimension check if stages not provided."""
        assert is_material_eligible(
            user_masks=[0xFF],
            material_masks=[0x0F],
            material_stages=None,
            user_max_stages=None,
            has_license=True
        ) is True
