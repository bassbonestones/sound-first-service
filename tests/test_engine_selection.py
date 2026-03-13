"""Tests for app/engine/selection.py - End-to-end material selection."""

import pytest
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock

from app.engine.selection import select_material
from app.engine.models import (
    Bucket,
    CapabilityProgress,
    MaterialCandidate,
    MaterialStatus,
    MaterialShelf,
    SessionMaterial,
)
from app.engine.config import EngineConfig


class TestSelectMaterial:
    """Tests for the select_material function."""

    def test_returns_none_when_no_target_capabilities(self):
        """When all capabilities mastered, returns None."""
        with patch('app.engine.selection.select_target_capabilities') as mock_targets:
            mock_targets.return_value = []
            
            result = select_material(
                user_masks=[0],
                capability_progress=[],
                materials_by_teaches={},
                material_states={},
                get_material_masks=lambda x: [0],
            )
            
            assert result is None

    def test_returns_none_when_no_candidates_in_pool(self):
        """When no eligible materials found, returns None."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        ]
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.build_candidate_pool') as mock_pool:
            mock_targets.return_value = progress
            mock_pool.return_value = []
            
            result = select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={1: [100]},
                material_states={},
                get_material_masks=lambda x: [0],
            )
            
            assert result is None

    def test_uses_default_config_when_none_provided(self):
        """Uses DEFAULT_CONFIG when config is None."""
        with patch('app.engine.selection.select_target_capabilities') as mock_targets:
            mock_targets.return_value = []
            
            select_material(
                user_masks=[0],
                capability_progress=[],
                materials_by_teaches={},
                material_states={},
                get_material_masks=lambda x: [0],
                config=None,
            )
            
            # Verify called with default config
            assert mock_targets.called

    def test_computes_maturity_when_not_provided(self):
        """Computes maturity from capability progress when not provided."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=True),
            CapabilityProgress(capability_id=2, difficulty_weight=1.0, is_mastered=False),
        ]
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.compute_capability_maturity') as mock_maturity, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights:
            mock_targets.return_value = []
            mock_maturity.return_value = 0.5
            mock_weights.return_value = {Bucket.NEW: 0.5, Bucket.IN_PROGRESS: 0.5}
            
            select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={},
                material_states={},
                get_material_masks=lambda x: [0],
                maturity=None,
            )
            
            # Should compute maturity: mastered_weight=1.0, total_weight=2.0
            mock_maturity.assert_called_once_with(1.0, 2.0)

    def test_uses_provided_maturity(self):
        """Uses provided maturity value instead of computing."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=True),
        ]
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.compute_capability_maturity') as mock_maturity, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights:
            mock_targets.return_value = []
            mock_weights.return_value = {}
            
            select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={},
                material_states={},
                get_material_masks=lambda x: [0],
                maturity=0.75,
            )
            
            # Should not compute maturity when provided
            mock_maturity.assert_not_called()

    def test_returns_session_material_on_successful_selection(self):
        """Returns SessionMaterial when material successfully selected."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        ]
        candidate = MaterialCandidate(
            material_id=100,
            status=MaterialStatus.IN_PROGRESS,
            attempt_count=1,
            overall_score=0.8,
            interaction_bonus=0.1,
        )
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.build_candidate_pool') as mock_pool, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights, \
             patch('app.engine.selection.sample_bucket') as mock_sample, \
             patch('app.engine.selection.filter_candidates_by_bucket') as mock_filter, \
             patch('app.engine.selection.rank_candidates') as mock_rank, \
             patch('app.engine.selection.get_hazard_warnings') as mock_hazards:
            
            mock_targets.return_value = progress
            mock_pool.return_value = [candidate]
            mock_weights.return_value = {Bucket.IN_PROGRESS: 1.0}
            mock_sample.return_value = Bucket.IN_PROGRESS
            mock_filter.return_value = [candidate]
            mock_rank.return_value = [candidate]
            mock_hazards.return_value = []
            
            result = select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={1: [100]},
                material_states={100: candidate},
                get_material_masks=lambda x: [0],
                maturity=0.5,
            )
            
            assert result is not None
            assert isinstance(result, SessionMaterial)
            assert result.material_id == 100
            assert result.bucket == Bucket.IN_PROGRESS
            assert result.overall_score == 0.8
            assert result.interaction_bonus == 0.1

    def test_tries_multiple_buckets_before_fallback(self):
        """Tries up to 3 buckets before falling back."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        ]
        candidate = MaterialCandidate(
            material_id=100,
            status=MaterialStatus.IN_PROGRESS,
        )
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.build_candidate_pool') as mock_pool, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights, \
             patch('app.engine.selection.sample_bucket') as mock_sample, \
             patch('app.engine.selection.filter_candidates_by_bucket') as mock_filter, \
             patch('app.engine.selection.get_hazard_warnings') as mock_hazards:
            
            mock_targets.return_value = progress
            mock_pool.return_value = [candidate]
            mock_weights.return_value = {Bucket.NEW: 0.5, Bucket.IN_PROGRESS: 0.5}
            mock_sample.side_effect = [Bucket.NEW, Bucket.NEW, Bucket.NEW]
            mock_filter.return_value = []  # No candidates match any bucket
            mock_hazards.return_value = []
            
            result = select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={1: [100]},
                material_states={100: candidate},
                get_material_masks=lambda x: [0],
                maturity=0.5,
            )
            
            # Should have tried 3 times
            assert mock_sample.call_count == 3
            # Should fall back to pool[0]
            assert result is not None
            assert result.material_id == 100
            assert result.bucket == Bucket.IN_PROGRESS  # Fallback bucket

    def test_fallback_when_no_ranked_candidates(self):
        """Falls back when ranking returns empty list."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        ]
        candidate = MaterialCandidate(
            material_id=100,
            status=MaterialStatus.IN_PROGRESS,
            overall_score=0.5,
        )
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.build_candidate_pool') as mock_pool, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights, \
             patch('app.engine.selection.sample_bucket') as mock_sample, \
             patch('app.engine.selection.filter_candidates_by_bucket') as mock_filter, \
             patch('app.engine.selection.rank_candidates') as mock_rank, \
             patch('app.engine.selection.get_hazard_warnings') as mock_hazards:
            
            mock_targets.return_value = progress
            mock_pool.return_value = [candidate]
            mock_weights.return_value = {Bucket.IN_PROGRESS: 1.0}
            mock_sample.return_value = Bucket.IN_PROGRESS
            mock_filter.return_value = [candidate]
            mock_rank.return_value = []  # Ranking returns empty
            mock_hazards.return_value = []
            
            result = select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={1: [100]},
                material_states={100: candidate},
                get_material_masks=lambda x: [0],
                maturity=0.5,
            )
            
            # Should fall back
            assert result is not None
            assert result.material_id == 100

    def test_bucket_weights_passed_to_sample_bucket(self):
        """Bucket weights are computed and passed to sample_bucket."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        ]
        candidate = MaterialCandidate(material_id=100)
        config = EngineConfig()
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.build_candidate_pool') as mock_pool, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights, \
             patch('app.engine.selection.sample_bucket') as mock_sample, \
             patch('app.engine.selection.filter_candidates_by_bucket') as mock_filter, \
             patch('app.engine.selection.get_hazard_warnings') as mock_hazards:
            
            mock_targets.return_value = progress
            mock_pool.return_value = [candidate]
            expected_weights = {Bucket.NEW: 0.3, Bucket.IN_PROGRESS: 0.5, Bucket.MAINTENANCE: 0.2}
            mock_weights.return_value = expected_weights
            mock_sample.return_value = Bucket.NEW
            mock_filter.return_value = []
            mock_hazards.return_value = []
            
            select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={1: [100]},
                material_states={100: candidate},
                get_material_masks=lambda x: [0],
                maturity=0.5,
                config=config,
            )
            
            mock_weights.assert_called_once_with(0.5, config)
            mock_sample.assert_called_with(expected_weights)

    def test_rank_candidates_receives_maturity(self):
        """Maturity is passed to rank_candidates."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        ]
        candidate = MaterialCandidate(
            material_id=100,
            status=MaterialStatus.IN_PROGRESS,
        )
        config = EngineConfig()
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.build_candidate_pool') as mock_pool, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights, \
             patch('app.engine.selection.sample_bucket') as mock_sample, \
             patch('app.engine.selection.filter_candidates_by_bucket') as mock_filter, \
             patch('app.engine.selection.rank_candidates') as mock_rank, \
             patch('app.engine.selection.get_hazard_warnings') as mock_hazards:
            
            mock_targets.return_value = progress
            mock_pool.return_value = [candidate]
            mock_weights.return_value = {Bucket.IN_PROGRESS: 1.0}
            mock_sample.return_value = Bucket.IN_PROGRESS
            mock_filter.return_value = [candidate]
            mock_rank.return_value = [candidate]
            mock_hazards.return_value = []
            
            select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={1: [100]},
                material_states={100: candidate},
                get_material_masks=lambda x: [0],
                maturity=0.75,
                config=config,
            )
            
            # Verify maturity passed to rank_candidates
            call_args = mock_rank.call_args
            assert call_args is not None
            assert call_args[0][-1] == 0.75  # Last positional arg is maturity

    def test_hazard_warnings_included_in_result(self):
        """Hazard warnings are included in the result."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        ]
        candidate = MaterialCandidate(
            material_id=100,
            status=MaterialStatus.IN_PROGRESS,
        )
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.build_candidate_pool') as mock_pool, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights, \
             patch('app.engine.selection.sample_bucket') as mock_sample, \
             patch('app.engine.selection.filter_candidates_by_bucket') as mock_filter, \
             patch('app.engine.selection.rank_candidates') as mock_rank, \
             patch('app.engine.selection.get_hazard_warnings') as mock_hazards:
            
            mock_targets.return_value = progress
            mock_pool.return_value = [candidate]
            mock_weights.return_value = {Bucket.IN_PROGRESS: 1.0}
            mock_sample.return_value = Bucket.IN_PROGRESS
            mock_filter.return_value = [candidate]
            mock_rank.return_value = [candidate]
            mock_hazards.return_value = ["long_since_seen", "hard_material"]
            
            result = select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={1: [100]},
                material_states={100: candidate},
                get_material_masks=lambda x: [0],
                maturity=0.5,
            )
            
            assert result.hazard_warnings == ["long_since_seen", "hard_material"]

    def test_capability_progress_dict_built_correctly(self):
        """Capability progress is correctly converted to dict for lookup."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False),
            CapabilityProgress(capability_id=2, difficulty_weight=2.0, is_mastered=True),
        ]
        candidate = MaterialCandidate(
            material_id=100,
            status=MaterialStatus.IN_PROGRESS,
        )
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.build_candidate_pool') as mock_pool, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights, \
             patch('app.engine.selection.sample_bucket') as mock_sample, \
             patch('app.engine.selection.filter_candidates_by_bucket') as mock_filter, \
             patch('app.engine.selection.rank_candidates') as mock_rank, \
             patch('app.engine.selection.get_hazard_warnings') as mock_hazards:
            
            mock_targets.return_value = progress
            mock_pool.return_value = [candidate]
            mock_weights.return_value = {Bucket.IN_PROGRESS: 1.0}
            mock_sample.return_value = Bucket.IN_PROGRESS
            mock_filter.return_value = [candidate]
            mock_rank.return_value = [candidate]
            mock_hazards.return_value = []
            
            select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={1: [100]},
                material_states={100: candidate},
                get_material_masks=lambda x: [0],
                maturity=0.5,
            )
            
            # Verify cap_progress_dict passed to rank_candidates
            call_args = mock_rank.call_args
            cap_dict = call_args[0][2]
            assert 1 in cap_dict
            assert 2 in cap_dict
            assert cap_dict[1].difficulty_weight == 1.0
            assert cap_dict[2].difficulty_weight == 2.0

    def test_selects_first_ranked_candidate(self):
        """Returns the first candidate from ranked list."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        ]
        candidate1 = MaterialCandidate(material_id=100, status=MaterialStatus.IN_PROGRESS, overall_score=0.9)
        candidate2 = MaterialCandidate(material_id=200, status=MaterialStatus.IN_PROGRESS, overall_score=0.7)
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.build_candidate_pool') as mock_pool, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights, \
             patch('app.engine.selection.sample_bucket') as mock_sample, \
             patch('app.engine.selection.filter_candidates_by_bucket') as mock_filter, \
             patch('app.engine.selection.rank_candidates') as mock_rank, \
             patch('app.engine.selection.get_hazard_warnings') as mock_hazards:
            
            mock_targets.return_value = progress
            mock_pool.return_value = [candidate1, candidate2]
            mock_weights.return_value = {Bucket.IN_PROGRESS: 1.0}
            mock_sample.return_value = Bucket.IN_PROGRESS
            mock_filter.return_value = [candidate1, candidate2]
            mock_rank.return_value = [candidate1, candidate2]  # candidate1 ranked first
            mock_hazards.return_value = []
            
            result = select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={1: [100, 200]},
                material_states={100: candidate1, 200: candidate2},
                get_material_masks=lambda x: [0],
                maturity=0.5,
            )
            
            assert result.material_id == 100
            assert result.overall_score == 0.9

    def test_successful_bucket_selection_doesnt_fallback(self):
        """When a bucket has candidates, doesn't try other buckets."""
        progress = [
            CapabilityProgress(capability_id=1, difficulty_weight=1.0, is_mastered=False)
        ]
        candidate = MaterialCandidate(
            material_id=100,
            status=MaterialStatus.IN_PROGRESS,
        )
        
        with patch('app.engine.selection.select_target_capabilities') as mock_targets, \
             patch('app.engine.selection.build_candidate_pool') as mock_pool, \
             patch('app.engine.selection.compute_bucket_weights') as mock_weights, \
             patch('app.engine.selection.sample_bucket') as mock_sample, \
             patch('app.engine.selection.filter_candidates_by_bucket') as mock_filter, \
             patch('app.engine.selection.rank_candidates') as mock_rank, \
             patch('app.engine.selection.get_hazard_warnings') as mock_hazards:
            
            mock_targets.return_value = progress
            mock_pool.return_value = [candidate]
            mock_weights.return_value = {Bucket.IN_PROGRESS: 1.0}
            mock_sample.return_value = Bucket.IN_PROGRESS
            mock_filter.return_value = [candidate]
            mock_rank.return_value = [candidate]
            mock_hazards.return_value = []
            
            select_material(
                user_masks=[0],
                capability_progress=progress,
                materials_by_teaches={1: [100]},
                material_states={100: candidate},
                get_material_masks=lambda x: [0],
                maturity=0.5,
            )
            
            # Should only sample once if successful
            assert mock_sample.call_count == 1
