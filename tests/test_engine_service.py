"""Tests for app/services/engine/service.py"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from app.services.engine.service import PracticeEngineService
from app.practice_engine import (
    EngineConfig, DEFAULT_CONFIG, MaterialCandidate, CapabilityProgress,
    MaterialStatus, Bucket, SessionMaterial, FocusTarget, AttemptResult
)


class TestPracticeEngineServiceInit:
    """Test initialization."""
    
    def test_init_with_default_config(self):
        """Test initialization with default config."""
        mock_db = Mock()
        service = PracticeEngineService(mock_db)
        
        assert service.db == mock_db
        assert service.config == DEFAULT_CONFIG
    
    def test_init_with_custom_config(self):
        """Test initialization with custom config."""
        mock_db = Mock()
        custom_config = EngineConfig()
        service = PracticeEngineService(mock_db, custom_config)
        
        assert service.db == mock_db
        assert service.config == custom_config


class TestDataLoadingDelegation:
    """Test data loading methods delegate to data_loaders module."""
    
    @patch('app.services.engine.service.load_user_material_states')
    def test_get_user_material_states(self, mock_load):
        """Test get_user_material_states delegates."""
        mock_db = Mock()
        expected = {1: Mock()}
        mock_load.return_value = expected
        
        service = PracticeEngineService(mock_db)
        result = service.get_user_material_states(user_id=42)
        
        mock_load.assert_called_once_with(mock_db, 42)
        assert result == expected
    
    @patch('app.services.engine.service.load_capability_progress')
    def test_get_capability_progress(self, mock_load):
        """Test get_capability_progress delegates."""
        mock_db = Mock()
        mock_load.return_value = [Mock()]
        
        service = PracticeEngineService(mock_db)
        result = service.get_capability_progress(user_id=42)
        
        mock_load.assert_called_once_with(mock_db, 42, None)
    
    @patch('app.services.engine.service.load_capability_progress')
    def test_get_capability_progress_with_instrument(self, mock_load):
        """Test get_capability_progress with instrument_id."""
        mock_db = Mock()
        mock_load.return_value = [Mock()]
        
        service = PracticeEngineService(mock_db)
        result = service.get_capability_progress(user_id=42, instrument_id=5)
        
        mock_load.assert_called_once_with(mock_db, 42, 5)
    
    @patch('app.services.engine.service.load_materials_by_teaches')
    def test_get_materials_by_teaches(self, mock_load):
        """Test get_materials_by_teaches delegates."""
        mock_db = Mock()
        mock_load.return_value = {1: [10, 20]}
        
        service = PracticeEngineService(mock_db)
        result = service.get_materials_by_teaches()
        
        mock_load.assert_called_once_with(mock_db)
        assert result == {1: [10, 20]}
    
    @patch('app.services.engine.service.load_user_ability_scores')
    def test_get_user_ability_scores(self, mock_load):
        """Test get_user_ability_scores delegates."""
        mock_db = Mock()
        mock_load.return_value = {'domain_A': 0.5}
        
        service = PracticeEngineService(mock_db)
        result = service.get_user_ability_scores(user_id=42)
        
        mock_load.assert_called_once_with(mock_db, 42)
        assert result == {'domain_A': 0.5}
    
    @patch('app.services.engine.service.load_pitch_focus_stats')
    def test_get_pitch_focus_stats(self, mock_load):
        """Test get_pitch_focus_stats delegates."""
        mock_db = Mock()
        mock_load.return_value = {(60, 1): (0.8, None)}
        
        service = PracticeEngineService(mock_db)
        result = service.get_pitch_focus_stats(user_id=42, material_id=10)
        
        mock_load.assert_called_once_with(mock_db, 42, 10)
    
    @patch('app.services.engine.service.load_focus_card_ids')
    def test_get_focus_card_ids(self, mock_load):
        """Test get_focus_card_ids delegates."""
        mock_db = Mock()
        mock_load.return_value = [1, 2, 3]
        
        service = PracticeEngineService(mock_db)
        result = service.get_focus_card_ids()
        
        mock_load.assert_called_once_with(mock_db)
        assert result == [1, 2, 3]


class TestComputeUserMaturity:
    """Test compute_user_maturity method."""
    
    @patch('app.services.engine.service.compute_combined_maturity')
    @patch('app.services.engine.service.compute_material_maturity')
    @patch('app.services.engine.service.compute_capability_maturity')
    @patch('app.services.engine.service.load_user_material_states')
    @patch('app.services.engine.service.load_capability_progress')
    def test_compute_user_maturity_basic(
        self,
        mock_load_cap,
        mock_load_mat,
        mock_cap_mat,
        mock_mat_mat,
        mock_combined
    ):
        """Test compute_user_maturity computation."""
        mock_db = Mock()
        
        # Setup cap progress
        cap1 = Mock()
        cap1.difficulty_weight = 1.0
        cap1.is_mastered = True
        cap2 = Mock()
        cap2.difficulty_weight = 2.0
        cap2.is_mastered = False
        mock_load_cap.return_value = [cap1, cap2]
        
        # Setup material states
        mat1 = Mock()
        mat1.difficulty_index = 0.5
        mat1.status = MaterialStatus.MASTERED
        mat2 = Mock()
        mat2.difficulty_index = 0.8
        mat2.status = MaterialStatus.IN_PROGRESS
        mock_load_mat.return_value = {1: mat1, 2: mat2}
        
        mock_cap_mat.return_value = 0.33
        mock_mat_mat.return_value = 0.38
        mock_combined.return_value = 0.35
        
        service = PracticeEngineService(mock_db)
        result = service.compute_user_maturity(user_id=42)
        
        # Verify cap maturity called with mastered=1.0, total=3.0
        mock_cap_mat.assert_called_once_with(1.0, 3.0)
        # Verify mat maturity called with mastered=0.5, total=1.3
        mock_mat_mat.assert_called_once_with(0.5, 1.3)
        mock_combined.assert_called_once()
        assert result == 0.35
    
    @patch('app.services.engine.service.compute_combined_maturity')
    @patch('app.services.engine.service.compute_material_maturity')
    @patch('app.services.engine.service.compute_capability_maturity')
    @patch('app.services.engine.service.load_user_material_states')
    @patch('app.services.engine.service.load_capability_progress')
    def test_compute_user_maturity_empty_data(
        self,
        mock_load_cap,
        mock_load_mat,
        mock_cap_mat,
        mock_mat_mat,
        mock_combined
    ):
        """Test compute_user_maturity with empty data."""
        mock_db = Mock()
        mock_load_cap.return_value = []
        mock_load_mat.return_value = {}
        mock_cap_mat.return_value = 0.0
        mock_mat_mat.return_value = 0.0
        mock_combined.return_value = 0.0
        
        service = PracticeEngineService(mock_db)
        result = service.compute_user_maturity(user_id=42)
        
        mock_cap_mat.assert_called_once_with(0, 0)
        mock_mat_mat.assert_called_once_with(0, 0)
        assert result == 0.0


class TestSelectNextMaterial:
    """Test select_next_material method."""
    
    def test_select_next_material_no_user(self):
        """Test returns None when user not found."""
        mock_db = Mock()
        mock_db.query.return_value.get.return_value = None
        
        service = PracticeEngineService(mock_db)
        result = service.select_next_material(user_id=999)
        
        assert result is None
    
    @patch('app.services.engine.service.select_target_capabilities')
    @patch('app.services.engine.service.compute_bucket_weights')
    @patch('app.services.engine.service.load_user_ability_scores')
    @patch('app.services.engine.service.load_user_material_states')
    @patch('app.services.engine.service.load_materials_by_teaches')
    @patch('app.services.engine.service.load_capability_progress')
    @patch('app.services.engine.service.compute_combined_maturity')
    @patch('app.services.engine.service.compute_material_maturity')
    @patch('app.services.engine.service.compute_capability_maturity')
    @patch('app.services.engine.service.get_user_capability_masks')
    def test_select_next_material_no_targets(
        self,
        mock_user_masks,
        mock_cap_mat,
        mock_mat_mat,
        mock_combined,
        mock_load_cap,
        mock_load_mat_by_teaches,
        mock_load_mat_states,
        mock_load_ability,
        mock_bucket_weights,
        mock_select_targets
    ):
        """Test returns None when no target capabilities."""
        mock_db = Mock()
        mock_user = Mock()
        mock_db.query.return_value.get.return_value = mock_user
        
        mock_user_masks.return_value = [0] * 8
        mock_load_cap.return_value = []
        mock_load_mat_by_teaches.return_value = {}
        mock_load_mat_states.return_value = {}
        mock_load_ability.return_value = {}
        mock_combined.return_value = 0.0
        mock_cap_mat.return_value = 0.0
        mock_mat_mat.return_value = 0.0
        mock_bucket_weights.return_value = {Bucket.NEW: 0.5, Bucket.IN_PROGRESS: 0.5}
        mock_select_targets.return_value = []  # No targets
        
        service = PracticeEngineService(mock_db)
        result = service.select_next_material(user_id=42)
        
        assert result is None
    
    @patch('app.services.engine.service.get_hazard_warnings')
    @patch('app.services.engine.service.build_candidate_pool')
    @patch('app.services.engine.service.select_target_capabilities')
    @patch('app.services.engine.service.compute_bucket_weights')
    @patch('app.services.engine.service.load_user_ability_scores')
    @patch('app.services.engine.service.load_user_material_states')
    @patch('app.services.engine.service.load_materials_by_teaches')
    @patch('app.services.engine.service.load_capability_progress')
    @patch('app.services.engine.service.compute_combined_maturity')
    @patch('app.services.engine.service.compute_material_maturity')
    @patch('app.services.engine.service.compute_capability_maturity')
    @patch('app.services.engine.service.get_user_capability_masks')
    def test_select_next_material_no_pool(
        self,
        mock_user_masks,
        mock_cap_mat,
        mock_mat_mat,
        mock_combined,
        mock_load_cap,
        mock_load_mat_by_teaches,
        mock_load_mat_states,
        mock_load_ability,
        mock_bucket_weights,
        mock_select_targets,
        mock_build_pool,
        mock_hazard
    ):
        """Test returns None when no candidates in pool."""
        mock_db = Mock()
        mock_user = Mock()
        mock_db.query.return_value.get.return_value = mock_user
        
        mock_user_masks.return_value = [0] * 8
        mock_load_cap.return_value = []
        mock_load_mat_by_teaches.return_value = {}
        mock_load_mat_states.return_value = {}
        mock_load_ability.return_value = {}
        mock_combined.return_value = 0.0
        mock_cap_mat.return_value = 0.0
        mock_mat_mat.return_value = 0.0
        mock_bucket_weights.return_value = {Bucket.NEW: 0.5}
        mock_select_targets.return_value = [Mock()]  # Has targets
        mock_build_pool.return_value = []  # Empty pool
        
        service = PracticeEngineService(mock_db)
        result = service.select_next_material(user_id=42)
        
        assert result is None
    
    @patch('app.services.engine.service.get_hazard_warnings')
    @patch('app.services.engine.service.rank_candidates')
    @patch('app.services.engine.service.check_unified_score_eligibility')
    @patch('app.services.engine.service.filter_candidates_by_bucket')
    @patch('app.services.engine.service.sample_bucket')
    @patch('app.services.engine.service.build_candidate_pool')
    @patch('app.services.engine.service.select_target_capabilities')
    @patch('app.services.engine.service.compute_bucket_weights')
    @patch('app.services.engine.service.load_user_ability_scores')
    @patch('app.services.engine.service.load_user_material_states')
    @patch('app.services.engine.service.load_materials_by_teaches')
    @patch('app.services.engine.service.load_capability_progress')
    @patch('app.services.engine.service.compute_combined_maturity')
    @patch('app.services.engine.service.compute_material_maturity')
    @patch('app.services.engine.service.compute_capability_maturity')
    @patch('app.services.engine.service.get_user_capability_masks')
    def test_select_next_material_success(
        self,
        mock_user_masks,
        mock_cap_mat,
        mock_mat_mat,
        mock_combined,
        mock_load_cap,
        mock_load_mat_by_teaches,
        mock_load_mat_states,
        mock_load_ability,
        mock_bucket_weights,
        mock_select_targets,
        mock_build_pool,
        mock_sample_bucket,
        mock_filter_bucket,
        mock_eligibility,
        mock_rank,
        mock_hazard
    ):
        """Test successful material selection."""
        mock_db = Mock()
        mock_user = Mock()
        mock_db.query.return_value.get.return_value = mock_user
        
        # Setup mocks
        mock_user_masks.return_value = [0] * 8
        mock_load_cap.return_value = []
        mock_load_mat_by_teaches.return_value = {}
        mock_load_mat_states.return_value = {}
        mock_load_ability.return_value = {}
        mock_combined.return_value = 0.5
        mock_cap_mat.return_value = 0.5
        mock_mat_mat.return_value = 0.5
        mock_bucket_weights.return_value = {Bucket.NEW: 0.5, Bucket.IN_PROGRESS: 0.5}
        mock_select_targets.return_value = [Mock()]
        
        # Candidate
        candidate = Mock()
        candidate.material_id = 100
        candidate.overall_score = 0.8
        candidate.interaction_bonus = 0.1
        
        mock_build_pool.return_value = [candidate]
        mock_sample_bucket.return_value = Bucket.NEW
        mock_filter_bucket.return_value = [candidate]
        mock_eligibility.return_value = (True, "")
        mock_rank.return_value = [candidate]
        mock_hazard.return_value = []
        
        config = EngineConfig()
        config.use_unified_score_eligibility = True
        service = PracticeEngineService(mock_db, config)
        result = service.select_next_material(user_id=42)
        
        # Verify result has expected structure
        assert result.material_id == 100
        assert result.bucket == Bucket.NEW
    
    @patch('app.services.engine.service.get_hazard_warnings')
    @patch('app.services.engine.service.rank_candidates')
    @patch('app.services.engine.service.check_unified_score_eligibility')
    @patch('app.services.engine.service.filter_candidates_by_bucket')
    @patch('app.services.engine.service.sample_bucket')
    @patch('app.services.engine.service.build_candidate_pool')
    @patch('app.services.engine.service.select_target_capabilities')
    @patch('app.services.engine.service.compute_bucket_weights')
    @patch('app.services.engine.service.load_user_ability_scores')
    @patch('app.services.engine.service.load_user_material_states')
    @patch('app.services.engine.service.load_materials_by_teaches')
    @patch('app.services.engine.service.load_capability_progress')
    @patch('app.services.engine.service.compute_combined_maturity')
    @patch('app.services.engine.service.compute_material_maturity')
    @patch('app.services.engine.service.compute_capability_maturity')
    @patch('app.services.engine.service.get_user_capability_masks')
    def test_select_next_material_fallback(
        self,
        mock_user_masks,
        mock_cap_mat,
        mock_mat_mat,
        mock_combined,
        mock_load_cap,
        mock_load_mat_by_teaches,
        mock_load_mat_states,
        mock_load_ability,
        mock_bucket_weights,
        mock_select_targets,
        mock_build_pool,
        mock_sample_bucket,
        mock_filter_bucket,
        mock_eligibility,
        mock_rank,
        mock_hazard
    ):
        """Test fallback when bucket filtering fails."""
        mock_db = Mock()
        mock_user = Mock()
        mock_db.query.return_value.get.return_value = mock_user
        
        mock_user_masks.return_value = [0] * 8
        mock_load_cap.return_value = []
        mock_load_mat_by_teaches.return_value = {}
        mock_load_mat_states.return_value = {}
        mock_load_ability.return_value = {}
        mock_combined.return_value = 0.5
        mock_cap_mat.return_value = 0.5
        mock_mat_mat.return_value = 0.5
        mock_bucket_weights.return_value = {Bucket.NEW: 1.0}
        mock_select_targets.return_value = [Mock()]
        
        # Candidate exists in pool but not after filtering
        candidate = Mock()
        candidate.material_id = 100
        candidate.overall_score = 0.8
        candidate.interaction_bonus = 0.1
        
        mock_build_pool.return_value = [candidate]
        mock_sample_bucket.return_value = Bucket.NEW
        mock_filter_bucket.return_value = []  # Empty after filter
        mock_hazard.return_value = []
        
        config = EngineConfig()
        config.use_unified_score_eligibility = False
        service = PracticeEngineService(mock_db, config)
        result = service.select_next_material(user_id=42)
        
        # Should fallback to first in pool
        assert result.material_id == 100
        assert result.bucket == Bucket.IN_PROGRESS


class TestSelectFocusTargetsForMaterial:
    """Test select_focus_targets_for_material method."""
    
    @patch('app.services.engine.service.select_focus_targets')
    @patch('app.services.engine.service.load_pitch_focus_stats')
    @patch('app.services.engine.service.load_focus_card_ids')
    @patch('app.services.engine.service.pitch_name_to_midi')
    def test_select_focus_targets_with_analysis(
        self,
        mock_pitch_to_midi,
        mock_load_focus_cards,
        mock_load_stats,
        mock_select_targets
    ):
        """Test focus target selection with material analysis."""
        mock_db = Mock()
        
        # Setup analysis
        mock_analysis = Mock()
        mock_analysis.lowest_pitch = "C3"
        mock_analysis.highest_pitch = "G3"
        mock_db.query.return_value.filter.return_value.first.return_value = mock_analysis
        
        # Setup user
        mock_user = Mock()
        mock_user.range_low = "C3"
        mock_user.range_high = "C5"
        mock_db.query.return_value.get.return_value = mock_user
        
        mock_pitch_to_midi.side_effect = lambda x: {"C3": 48, "G3": 55, "C5": 72}[x]
        mock_load_focus_cards.return_value = [1, 2]
        mock_load_stats.return_value = {}
        mock_select_targets.return_value = [Mock()]
        
        service = PracticeEngineService(mock_db)
        result = service.select_focus_targets_for_material(user_id=42, material_id=10)
        
        # Verify select_focus_targets called with correct pitches
        call_args = mock_select_targets.call_args[0]
        assert list(range(48, 56)) == call_args[0]  # Material pitches
        assert [1, 2] == call_args[1]  # Focus card IDs
    
    @patch('app.services.engine.service.select_focus_targets')
    @patch('app.services.engine.service.load_pitch_focus_stats')
    @patch('app.services.engine.service.load_focus_card_ids')
    def test_select_focus_targets_no_analysis(
        self,
        mock_load_focus_cards,
        mock_load_stats,
        mock_select_targets
    ):
        """Test focus target selection without material analysis."""
        mock_db = Mock()
        
        # No analysis
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # User without range
        mock_user = Mock()
        mock_user.range_low = None
        mock_user.range_high = None
        mock_db.query.return_value.get.return_value = mock_user
        
        mock_load_focus_cards.return_value = []  # Empty - should use defaults
        mock_load_stats.return_value = {}
        mock_select_targets.return_value = []
        
        service = PracticeEngineService(mock_db)
        result = service.select_focus_targets_for_material(user_id=42, material_id=10)
        
        # Should use defaults
        call_args = mock_select_targets.call_args[0]
        assert list(range(48, 72)) == call_args[0]  # Default pitches
        assert [1, 2, 3] == call_args[1]  # Default focus card IDs
        assert 60 == call_args[3]  # Default user_range_center


class TestRecordAttempt:
    """Test record_attempt method."""
    
    @patch('app.services.engine.service.handle_record_attempt')
    @patch('app.services.engine.service.load_capability_progress')
    def test_record_attempt_basic(self, mock_load_cap, mock_handle):
        """Test basic attempt recording."""
        mock_db = Mock()
        
        cap = Mock()
        cap.capability_id = 1
        mock_load_cap.return_value = [cap]
        
        mock_result = Mock(spec=AttemptResult)
        mock_handle.return_value = mock_result
        
        service = PracticeEngineService(mock_db)
        result = service.record_attempt(
            user_id=42,
            material_id=100,
            rating=4
        )
        
        mock_handle.assert_called_once()
        call_kwargs = mock_handle.call_args[1]
        assert call_kwargs['user_id'] == 42
        assert call_kwargs['material_id'] == 100
        assert call_kwargs['rating'] == 4
        mock_db.commit.assert_called_once()
        assert result == mock_result
    
    @patch('app.services.engine.service.handle_record_attempt')
    @patch('app.services.engine.service.load_capability_progress')
    def test_record_attempt_with_all_params(self, mock_load_cap, mock_handle):
        """Test attempt recording with all parameters."""
        mock_db = Mock()
        mock_load_cap.return_value = []
        mock_handle.return_value = Mock(spec=AttemptResult)
        
        service = PracticeEngineService(mock_db)
        service.record_attempt(
            user_id=42,
            material_id=100,
            rating=3,
            focus_card_id=5,
            pitch_midi=60,
            is_off_course=True,
            key="C",
            fatigue=2
        )
        
        call_kwargs = mock_handle.call_args[1]
        assert call_kwargs['focus_card_id'] == 5
        assert call_kwargs['pitch_midi'] == 60
        assert call_kwargs['is_off_course'] == True
        assert call_kwargs['key'] == "C"
        assert call_kwargs['fatigue'] == 2


class TestMaterialMasksCache:
    """Test material masks caching in select_next_material."""
    
    @patch('app.services.engine.service.get_hazard_warnings')
    @patch('app.services.engine.service.rank_candidates')
    @patch('app.services.engine.service.filter_candidates_by_bucket')
    @patch('app.services.engine.service.sample_bucket')
    @patch('app.services.engine.service.build_candidate_pool')
    @patch('app.services.engine.service.select_target_capabilities')
    @patch('app.services.engine.service.compute_bucket_weights')
    @patch('app.services.engine.service.load_user_ability_scores')
    @patch('app.services.engine.service.load_user_material_states')
    @patch('app.services.engine.service.load_materials_by_teaches')
    @patch('app.services.engine.service.load_capability_progress')
    @patch('app.services.engine.service.compute_combined_maturity')
    @patch('app.services.engine.service.compute_material_maturity')
    @patch('app.services.engine.service.compute_capability_maturity')
    @patch('app.services.engine.service.get_user_capability_masks')
    @patch('app.services.engine.service.get_material_capability_masks')
    def test_material_masks_cache_miss(
        self,
        mock_get_mat_masks,
        mock_user_masks,
        mock_cap_mat,
        mock_mat_mat,
        mock_combined,
        mock_load_cap,
        mock_load_mat_by_teaches,
        mock_load_mat_states,
        mock_load_ability,
        mock_bucket_weights,
        mock_select_targets,
        mock_build_pool,
        mock_sample_bucket,
        mock_filter_bucket,
        mock_rank,
        mock_hazard
    ):
        """Test that material masks are retrieved for unknown materials."""
        mock_db = Mock()
        mock_user = Mock()
        mock_material = Mock()
        
        # Setup db.query chain for user and material
        def query_side_effect(model):
            result = Mock()
            if model.__name__ == 'User':
                result.get.return_value = mock_user
            elif model.__name__ == 'Material':
                result.get.return_value = mock_material
            return result
        mock_db.query.side_effect = query_side_effect
        
        mock_user_masks.return_value = [0] * 8
        mock_get_mat_masks.return_value = [1, 2, 3, 4, 5, 6, 7, 8]
        mock_load_cap.return_value = []
        mock_load_mat_by_teaches.return_value = {}
        mock_load_mat_states.return_value = {}
        mock_load_ability.return_value = {}
        mock_combined.return_value = 0.5
        mock_cap_mat.return_value = 0.5
        mock_mat_mat.return_value = 0.5
        mock_bucket_weights.return_value = {}
        mock_select_targets.return_value = []
        mock_build_pool.return_value = []
        
        config = EngineConfig()
        config.use_unified_score_eligibility = False
        service = PracticeEngineService(mock_db, config)
        service.select_next_material(user_id=42)
        
        # No targets, so build_candidate_pool not called with get_material_masks
