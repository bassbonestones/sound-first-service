"""Tests for app/engine/targeting.py - Target capability selection and candidate pool building."""

import pytest
from unittest.mock import Mock, patch

from app.engine.targeting import (
    select_target_capabilities,
    build_candidate_pool,
    filter_candidates_by_bucket,
)
from app.engine.models import (
    Bucket,
    CapabilityProgress,
    MaterialCandidate,
    MaterialStatus,
    MaterialShelf,
)
from app.engine.config import EngineConfig


class TestBuildCandidatePool:
    """Tests for the build_candidate_pool function."""

    def test_returns_empty_pool_when_no_target_capabilities(self):
        """Returns empty list when no target capabilities provided."""
        result = build_candidate_pool(
            target_capabilities=[],
            materials_by_teaches={},
            material_states={},
            user_masks=[0],
            get_material_masks=lambda x: [0],
        )
        assert result == []

    def test_uses_default_config_when_none_provided(self):
        """Uses DEFAULT_CONFIG when config is None."""
        target = CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        
        with patch('app.engine.targeting.check_bitmask_eligibility') as mock_check:
            mock_check.return_value = False
            
            build_candidate_pool(
                target_capabilities=[target],
                materials_by_teaches={1: [100]},
                material_states={},
                user_masks=[0],
                get_material_masks=lambda x: [0],
                config=None,
            )
            
            # Should complete without error using default config
            assert mock_check.called

    def test_filters_ineligible_materials(self):
        """Only includes materials that pass bitmask eligibility check."""
        target = CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        
        with patch('app.engine.targeting.check_bitmask_eligibility') as mock_check:
            # Only material 100 is eligible
            mock_check.side_effect = lambda user, mat: mat == [100]
            
            result = build_candidate_pool(
                target_capabilities=[target],
                materials_by_teaches={1: [100, 200, 300]},
                material_states={100: MaterialCandidate(material_id=100)},
                user_masks=[0],
                get_material_masks=lambda x: [x],  # Return material ID as mask
            )
            
            assert len(result) == 1
            assert result[0].material_id == 100

    def test_samples_when_exceeds_candidates_per_capability(self):
        """Samples materials when count exceeds candidates_per_capability."""
        target = CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        config = EngineConfig(candidates_per_capability=2)
        
        with patch('app.engine.targeting.check_bitmask_eligibility') as mock_check, \
             patch('app.engine.targeting.random.sample') as mock_sample:
            mock_check.return_value = True
            mock_sample.return_value = [100, 200]  # Sampled 2 of 5
            
            build_candidate_pool(
                target_capabilities=[target],
                materials_by_teaches={1: [100, 200, 300, 400, 500]},
                material_states={},
                user_masks=[0],
                get_material_masks=lambda x: [0],
                config=config,
            )
            
            mock_sample.assert_called_once()
            args = mock_sample.call_args[0]
            assert len(args[0]) == 5  # 5 eligible materials
            assert args[1] == 2  # Sample 2

    def test_does_not_sample_when_under_candidates_per_capability(self):
        """Uses all materials when count is under candidates_per_capability."""
        target = CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        config = EngineConfig(candidates_per_capability=10)
        
        with patch('app.engine.targeting.check_bitmask_eligibility') as mock_check, \
             patch('app.engine.targeting.random.sample') as mock_sample:
            mock_check.return_value = True
            
            result = build_candidate_pool(
                target_capabilities=[target],
                materials_by_teaches={1: [100, 200]},  # Only 2 materials
                material_states={},
                user_masks=[0],
                get_material_masks=lambda x: [0],
                config=config,
            )
            
            # random.sample should not be called for this selection
            # (may be called for pool capping, but not for per-capability)
            assert len(result) == 2

    def test_caps_total_pool_size(self):
        """Caps pool size to max_candidates_pool."""
        targets = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False),
            CapabilityProgress(capability_id=2, difficulty_weight=1.0, is_mastered=False),
        ]
        config = EngineConfig(max_candidates_pool=3, candidates_per_capability=10)
        
        with patch('app.engine.targeting.check_bitmask_eligibility') as mock_check:
            mock_check.return_value = True
            
            result = build_candidate_pool(
                target_capabilities=targets,
                materials_by_teaches={
                    1: [100, 200, 300],  # 3 materials
                    2: [400, 500, 600],  # 3 more materials (total 6)
                },
                material_states={},
                user_masks=[0],
                get_material_masks=lambda x: [0],
                config=config,
            )
            
            # Should be capped at 3
            assert len(result) <= 3

    def test_uses_existing_material_states(self):
        """Uses MaterialCandidate from material_states when available."""
        target = CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        existing_candidate = MaterialCandidate(
            material_id=100,
            status=MaterialStatus.IN_PROGRESS,
            attempt_count=5,
            overall_score=0.7,
        )
        
        with patch('app.engine.targeting.check_bitmask_eligibility') as mock_check:
            mock_check.return_value = True
            
            result = build_candidate_pool(
                target_capabilities=[target],
                materials_by_teaches={1: [100]},
                material_states={100: existing_candidate},
                user_masks=[0],
                get_material_masks=lambda x: [0],
            )
            
            assert len(result) == 1
            assert result[0].material_id == 100
            assert result[0].status == MaterialStatus.IN_PROGRESS
            assert result[0].attempt_count == 5
            assert result[0].overall_score == 0.7

    def test_creates_default_candidate_when_not_in_states(self):
        """Creates default MaterialCandidate for materials not in material_states."""
        target = CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        
        with patch('app.engine.targeting.check_bitmask_eligibility') as mock_check:
            mock_check.return_value = True
            
            result = build_candidate_pool(
                target_capabilities=[target],
                materials_by_teaches={1: [100]},
                material_states={},  # Empty - no existing state
                user_masks=[0],
                get_material_masks=lambda x: [0],
            )
            
            assert len(result) == 1
            assert result[0].material_id == 100
            # Default MaterialCandidate attributes
            assert result[0].status == MaterialStatus.UNEXPLORED
            assert result[0].attempt_count == 0

    def test_handles_missing_capability_in_materials_by_teaches(self):
        """Handles capability not in materials_by_teaches gracefully."""
        target = CapabilityProgress(capability_id=999, difficulty_weight=1.0, is_mastered=False)
        
        result = build_candidate_pool(
            target_capabilities=[target],
            materials_by_teaches={},  # No materials for capability 999
            material_states={},
            user_masks=[0],
            get_material_masks=lambda x: [0],
        )
        
        assert result == []

    def test_deduplicates_materials_across_capabilities(self):
        """Materials shared by multiple capabilities appear only once in pool."""
        targets = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False),
            CapabilityProgress(capability_id=2, difficulty_weight=1.0, is_mastered=False),
        ]
        
        with patch('app.engine.targeting.check_bitmask_eligibility') as mock_check:
            mock_check.return_value = True
            
            result = build_candidate_pool(
                target_capabilities=targets,
                materials_by_teaches={
                    1: [100, 200],  # Both teach capability 1
                    2: [100, 300],  # 100 also teaches capability 2
                },
                material_states={},
                user_masks=[0],
                get_material_masks=lambda x: [0],
            )
            
            material_ids = [c.material_id for c in result]
            # 100 should appear only once
            assert material_ids.count(100) == 1
            # Should have 3 unique materials
            assert len(set(material_ids)) == 3

    def test_calls_get_material_masks_for_each_material(self):
        """Calls get_material_masks for each material being checked."""
        target = CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        get_masks = Mock(return_value=[0])
        
        with patch('app.engine.targeting.check_bitmask_eligibility') as mock_check:
            mock_check.return_value = True
            
            build_candidate_pool(
                target_capabilities=[target],
                materials_by_teaches={1: [100, 200, 300]},
                material_states={},
                user_masks=[0],
                get_material_masks=get_masks,
            )
            
            assert get_masks.call_count == 3
            get_masks.assert_any_call(100)
            get_masks.assert_any_call(200)
            get_masks.assert_any_call(300)

    def test_passes_user_masks_to_eligibility_check(self):
        """Passes correct user_masks to check_bitmask_eligibility."""
        target = CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        user_masks = [1, 2, 3]
        
        with patch('app.engine.targeting.check_bitmask_eligibility') as mock_check:
            mock_check.return_value = True
            
            build_candidate_pool(
                target_capabilities=[target],
                materials_by_teaches={1: [100]},
                material_states={},
                user_masks=user_masks,
                get_material_masks=lambda x: [0],
            )
            
            call_args = mock_check.call_args[0]
            assert call_args[0] == user_masks
