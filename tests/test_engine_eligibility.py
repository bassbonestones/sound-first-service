"""
Tests for engine eligibility checking functions.

Tests capability bitmask and content dimension eligibility checks.
"""

import pytest
from app.engine.eligibility import (
    check_bitmask_eligibility,
    check_content_dimension_eligibility,
    is_material_eligible,
    check_unified_score_eligibility,
    get_hazard_warnings,
)
from app.engine.models import Bucket, MaterialCandidate
from app.engine.config import EngineConfig


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


class TestCheckUnifiedScoreEligibility:
    """Tests for check_unified_score_eligibility function."""

    def test_returns_eligible_when_unified_scoring_disabled(self):
        """Returns (True, []) when use_unified_score_eligibility is False."""
        config = EngineConfig(use_unified_score_eligibility=False)
        candidate = MaterialCandidate(material_id=1)
        
        is_eligible, reasons = check_unified_score_eligibility(
            material_candidate=candidate,
            user_ability_scores={},
            config=config
        )
        
        assert is_eligible is True
        assert reasons == []

    def test_uses_default_config_when_none(self):
        """Uses DEFAULT_CONFIG when config is None."""
        candidate = MaterialCandidate(material_id=1)
        
        is_eligible, reasons = check_unified_score_eligibility(
            material_candidate=candidate,
            user_ability_scores={},
            config=None
        )
        
        assert isinstance(is_eligible, bool)
        assert isinstance(reasons, list)

    def test_blocks_when_primary_score_delta_exceeded(self):
        """Returns ineligible when material score exceeds user by too much."""
        candidate = MaterialCandidate(
            material_id=1,
            primary_scores={'rhythm': 0.9}
        )
        config = EngineConfig(
            use_unified_score_eligibility=True,
            max_primary_score_delta=0.2
        )
        
        is_eligible, reasons = check_unified_score_eligibility(
            material_candidate=candidate,
            user_ability_scores={'rhythm': 0.5},
            config=config
        )
        
        assert is_eligible is False
        assert len(reasons) == 1
        assert 'rhythm_too_hard' in reasons[0]

    def test_eligible_when_primary_score_within_delta(self):
        """Returns eligible when primary score delta is acceptable."""
        candidate = MaterialCandidate(
            material_id=1,
            primary_scores={'rhythm': 0.6}
        )
        config = EngineConfig(
            use_unified_score_eligibility=True,
            max_primary_score_delta=0.3
        )
        
        is_eligible, reasons = check_unified_score_eligibility(
            material_candidate=candidate,
            user_ability_scores={'rhythm': 0.5},
            config=config
        )
        
        assert is_eligible is True
        assert reasons == []

    def test_blocks_when_hazard_score_exceeds_cap(self):
        """Returns ineligible when hazard score exceeds max."""
        candidate = MaterialCandidate(
            material_id=1,
            hazard_scores={'tempo': 0.9}
        )
        config = EngineConfig(
            use_unified_score_eligibility=True,
            max_hazard_score=0.7
        )
        
        is_eligible, reasons = check_unified_score_eligibility(
            material_candidate=candidate,
            user_ability_scores={},
            config=config
        )
        
        assert is_eligible is False
        assert len(reasons) == 1
        assert 'tempo_hazard_too_high' in reasons[0]

    def test_relaxed_hazard_tolerance_for_maintenance_bucket(self):
        """Uses higher hazard tolerance for maintenance bucket."""
        candidate = MaterialCandidate(
            material_id=1,
            hazard_scores={'tempo': 0.85}
        )
        config = EngineConfig(
            use_unified_score_eligibility=True,
            max_hazard_score=0.7,
            hazard_tolerance_maintenance=0.9
        )
        
        is_eligible_normal, _ = check_unified_score_eligibility(
            material_candidate=candidate,
            user_ability_scores={},
            bucket=Bucket.NEW,
            config=config
        )
        
        is_eligible_maintenance, _ = check_unified_score_eligibility(
            material_candidate=candidate,
            user_ability_scores={},
            bucket=Bucket.MAINTENANCE,
            config=config
        )
        
        assert is_eligible_normal is False
        assert is_eligible_maintenance is True

    def test_skips_none_primary_scores(self):
        """Skips domains with None primary score."""
        candidate = MaterialCandidate(
            material_id=1,
            primary_scores={'rhythm': None, 'melody': 0.5}
        )
        config = EngineConfig(
            use_unified_score_eligibility=True,
            max_primary_score_delta=0.2
        )
        
        is_eligible, _ = check_unified_score_eligibility(
            material_candidate=candidate,
            user_ability_scores={'rhythm': 0.1, 'melody': 0.4},
            config=config
        )
        
        assert is_eligible is True

    def test_skips_none_hazard_scores(self):
        """Skips domains with None hazard score."""
        candidate = MaterialCandidate(
            material_id=1,
            hazard_scores={'tempo': None}
        )
        config = EngineConfig(
            use_unified_score_eligibility=True,
            max_hazard_score=0.1
        )
        
        is_eligible, reasons = check_unified_score_eligibility(
            material_candidate=candidate,
            user_ability_scores={},
            config=config
        )
        
        assert is_eligible is True
        assert reasons == []

    def test_uses_zero_for_missing_user_ability(self):
        """Uses 0.0 for user ability score when domain not in dict."""
        candidate = MaterialCandidate(
            material_id=1,
            primary_scores={'new_domain': 0.5}
        )
        config = EngineConfig(
            use_unified_score_eligibility=True,
            max_primary_score_delta=0.3
        )
        
        is_eligible, reasons = check_unified_score_eligibility(
            material_candidate=candidate,
            user_ability_scores={},
            config=config
        )
        
        assert is_eligible is False


class TestGetHazardWarnings:
    """Tests for get_hazard_warnings function."""

    def test_returns_copy_of_hazard_flags(self):
        """Returns existing hazard flags."""
        candidate = MaterialCandidate(
            material_id=1,
            hazard_flags=['long_since_seen', 'unusual_key']
        )
        
        warnings = get_hazard_warnings(candidate)
        
        assert 'long_since_seen' in warnings
        assert 'unusual_key' in warnings

    def test_adds_elevated_hazard_warnings(self):
        """Adds warning for hazard scores above 80% of threshold."""
        candidate = MaterialCandidate(
            material_id=1,
            hazard_scores={'tempo': 0.65}
        )
        config = EngineConfig(max_hazard_score=0.7)
        
        warnings = get_hazard_warnings(candidate, config)
        
        assert any('tempo_elevated_hazard' in w for w in warnings)

    def test_no_warning_for_low_hazard_scores(self):
        """No warning for hazard scores below 80% of threshold."""
        candidate = MaterialCandidate(
            material_id=1,
            hazard_scores={'tempo': 0.4}
        )
        config = EngineConfig(max_hazard_score=0.7)
        
        warnings = get_hazard_warnings(candidate, config)
        
        assert not any('tempo_elevated_hazard' in w for w in warnings)

    def test_skips_none_hazard_scores(self):
        """Skips domains with None hazard score."""
        candidate = MaterialCandidate(
            material_id=1,
            hazard_scores={'tempo': None, 'rhythm': 0.65}
        )
        config = EngineConfig(max_hazard_score=0.7)
        
        warnings = get_hazard_warnings(candidate, config)
        
        assert any('rhythm_elevated_hazard' in w for w in warnings)
        assert not any('tempo' in w for w in warnings)

    def test_uses_default_config_when_none(self):
        """Uses DEFAULT_CONFIG when config is None."""
        candidate = MaterialCandidate(material_id=1)
        
        warnings = get_hazard_warnings(candidate, config=None)
        
        assert isinstance(warnings, list)

    def test_combines_flags_and_score_warnings(self):
        """Returns both existing flags and score-based warnings."""
        candidate = MaterialCandidate(
            material_id=1,
            hazard_flags=['existing_flag'],
            hazard_scores={'tempo': 0.9}
        )
        config = EngineConfig(max_hazard_score=0.7)
        
        warnings = get_hazard_warnings(candidate, config)
        
        assert 'existing_flag' in warnings
        assert any('tempo_elevated_hazard' in w for w in warnings)
