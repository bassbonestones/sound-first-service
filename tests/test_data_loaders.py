"""Tests for app/services/engine/data_loaders.py"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

from app.services.engine.data_loaders import (
    load_user_material_states,
    extract_hazard_data,
    load_capability_progress,
    load_materials_by_teaches,
    load_user_ability_scores,
    load_pitch_focus_stats,
    load_focus_card_ids
)
from app.practice_engine import MaterialStatus, MaterialShelf


class TestExtractHazardData:
    """Test extract_hazard_data function."""
    
    def test_extract_with_valid_json(self):
        """Test extracting hazard data from valid JSON."""
        mock_analysis = Mock()
        mock_analysis.interval_analysis_json = json.dumps({
            "scores": {"hazard": 0.3},
            "flags": ["high_velocity"]
        })
        mock_analysis.rhythm_analysis_json = json.dumps({
            "scores": {"hazard": 0.5},
            "flags": ["complex_pattern"]
        })
        mock_analysis.tonal_analysis_json = None
        mock_analysis.tempo_analysis_json = None
        mock_analysis.range_analysis_json = None
        mock_analysis.throughput_analysis_json = None
        
        hazard_scores, hazard_flags = extract_hazard_data(mock_analysis)
        
        assert hazard_scores["interval"] == 0.3
        assert hazard_scores["rhythm"] == 0.5
        assert "interval:high_velocity" in hazard_flags
        assert "rhythm:complex_pattern" in hazard_flags
    
    def test_extract_with_invalid_json(self):
        """Test handling invalid JSON gracefully."""
        mock_analysis = Mock()
        mock_analysis.interval_analysis_json = "not valid json"
        mock_analysis.rhythm_analysis_json = None
        mock_analysis.tonal_analysis_json = None
        mock_analysis.tempo_analysis_json = None
        mock_analysis.range_analysis_json = None
        mock_analysis.throughput_analysis_json = None
        
        hazard_scores, hazard_flags = extract_hazard_data(mock_analysis)
        
        assert hazard_scores == {}
        assert hazard_flags == []
    
    def test_extract_with_missing_scores(self):
        """Test handling JSON without scores key."""
        mock_analysis = Mock()
        mock_analysis.interval_analysis_json = json.dumps({
            "other_data": "value"
        })
        mock_analysis.rhythm_analysis_json = None
        mock_analysis.tonal_analysis_json = None
        mock_analysis.tempo_analysis_json = None
        mock_analysis.range_analysis_json = None
        mock_analysis.throughput_analysis_json = None
        
        hazard_scores, hazard_flags = extract_hazard_data(mock_analysis)
        
        assert hazard_scores.get("interval") is None


class TestLoadUserMaterialStates:
    """Test load_user_material_states function."""
    
    @patch('app.services.engine.data_loaders.extract_hazard_data')
    def test_load_empty_states(self, mock_extract):
        """Test loading when no states exist."""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        result = load_user_material_states(mock_db, user_id=1)
        
        assert result == {}
    
    @patch('app.services.engine.data_loaders.extract_hazard_data')
    def test_load_states_with_analysis(self, mock_extract):
        """Test loading states with analysis data."""
        mock_db = Mock()
        
        # Setup state
        mock_state = Mock()
        mock_state.material_id = 10
        mock_state.ema_score = 0.75
        mock_state.attempt_count = 5
        mock_state.last_attempt_at = datetime(2024, 1, 1)
        mock_state.status = "in_progress"
        mock_state.shelf = "default"
        
        # Setup analysis
        mock_analysis = Mock()
        mock_analysis.difficulty_index = 0.6
        mock_analysis.overall_score = 0.8
        mock_analysis.interaction_bonus = 0.1
        mock_analysis.interval_primary_score = 0.5
        mock_analysis.rhythm_primary_score = 0.4
        mock_analysis.tonal_primary_score = 0.3
        mock_analysis.tempo_primary_score = 0.2
        mock_analysis.range_primary_score = 0.1
        mock_analysis.throughput_primary_score = 0.15
        
        # Setup mock query chain
        mock_db.query.return_value.filter.return_value.all.side_effect = [
            [mock_state],  # UserMaterialState query
            [(1,), (2,)],  # MaterialTeachesCapability query
        ]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_analysis
        
        mock_extract.return_value = ({"interval": 0.3}, ["interval:flag1"])
        
        result = load_user_material_states(mock_db, user_id=1)
        
        assert 10 in result
        candidate = result[10]
        assert candidate.material_id == 10
        assert candidate.ema_score == 0.75
        assert candidate.status == MaterialStatus.IN_PROGRESS


class TestLoadCapabilityProgress:
    """Test load_capability_progress function."""
    
    def test_load_progress_global_only(self):
        """Test loading global capabilities only."""
        mock_db = Mock()
        
        # Setup capability
        mock_cap = Mock()
        mock_cap.id = 1
        mock_cap.is_global = True
        mock_cap.evidence_required_count = 5
        mock_cap.difficulty_weight = 1.5
        
        # Setup user capability
        mock_uc = Mock()
        mock_uc.capability_id = 1
        mock_uc.instrument_id = None
        mock_uc.evidence_count = 3
        mock_uc.mastered_at = None
        
        mock_db.query.return_value.all.side_effect = [[mock_cap], [mock_uc]]
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_uc]
        
        result = load_capability_progress(mock_db, user_id=1)
        
        assert len(result) == 1
        assert result[0].capability_id == 1
        assert result[0].evidence_count == 3
        assert result[0].required_count == 5
        assert result[0].is_mastered is False
    
    def test_load_progress_mastered(self):
        """Test loading mastered capability."""
        mock_db = Mock()
        
        mock_cap = Mock()
        mock_cap.id = 1
        mock_cap.is_global = True
        mock_cap.evidence_required_count = 3
        mock_cap.difficulty_weight = 1.0
        
        mock_uc = Mock()
        mock_uc.capability_id = 1
        mock_uc.instrument_id = None
        mock_uc.evidence_count = 5
        mock_uc.mastered_at = datetime(2024, 1, 1)  # Is mastered
        
        mock_db.query.return_value.all.side_effect = [[mock_cap], [mock_uc]]
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_uc]
        
        result = load_capability_progress(mock_db, user_id=1)
        
        assert result[0].is_mastered is True


class TestLoadMaterialsByTeaches:
    """Test load_materials_by_teaches function."""
    
    def test_load_materials_index(self):
        """Test building material index by capability."""
        mock_db = Mock()
        
        teach1 = Mock()
        teach1.capability_id = 1
        teach1.material_id = 10
        
        teach2 = Mock()
        teach2.capability_id = 1
        teach2.material_id = 20
        
        teach3 = Mock()
        teach3.capability_id = 2
        teach3.material_id = 30
        
        mock_db.query.return_value.all.return_value = [teach1, teach2, teach3]
        
        result = load_materials_by_teaches(mock_db)
        
        assert 1 in result
        assert 2 in result
        assert result[1] == [10, 20]
        assert result[2] == [30]
    
    def test_load_materials_empty(self):
        """Test empty result."""
        mock_db = Mock()
        mock_db.query.return_value.all.return_value = []
        
        result = load_materials_by_teaches(mock_db)
        
        assert result == {}


class TestLoadUserAbilityScores:
    """Test load_user_ability_scores function."""
    
    def test_load_with_scores(self):
        """Test loading existing scores."""
        mock_db = Mock()
        
        mock_scores = Mock()
        mock_scores.interval_ability_score = 0.5
        mock_scores.rhythm_ability_score = 0.6
        mock_scores.tonal_ability_score = 0.4
        mock_scores.tempo_ability_score = 0.3
        mock_scores.range_ability_score = 0.2
        mock_scores.throughput_ability_score = 0.1
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_scores
        
        result = load_user_ability_scores(mock_db, user_id=1)
        
        assert result["interval"] == 0.5
        assert result["rhythm"] == 0.6
        assert result["tonal"] == 0.4
    
    def test_load_with_no_scores(self):
        """Test loading when no scores exist."""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = load_user_ability_scores(mock_db, user_id=1)
        
        assert result["interval"] == 0.0
        assert result["rhythm"] == 0.0
    
    def test_load_with_none_values(self):
        """Test handling None score values."""
        mock_db = Mock()
        
        mock_scores = Mock()
        mock_scores.interval_ability_score = None
        mock_scores.rhythm_ability_score = 0.5
        mock_scores.tonal_ability_score = None
        mock_scores.tempo_ability_score = None
        mock_scores.range_ability_score = None
        mock_scores.throughput_ability_score = None
        
        mock_db.query.return_value.filter.return_value.first.return_value = mock_scores
        
        result = load_user_ability_scores(mock_db, user_id=1)
        
        assert result["interval"] == 0.0
        assert result["rhythm"] == 0.5


class TestLoadPitchFocusStats:
    """Test load_pitch_focus_stats function."""
    
    def test_load_global_stats(self):
        """Test loading global pitch focus stats."""
        mock_db = Mock()
        
        stat = Mock()
        stat.pitch_midi = 60
        stat.focus_card_id = 1
        stat.ema_score = 0.8
        stat.last_attempt_at = datetime(2024, 1, 1)
        
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [stat]
        
        result = load_pitch_focus_stats(mock_db, user_id=1)
        
        assert (60, 1) in result
        assert result[(60, 1)] == (0.8, datetime(2024, 1, 1))
    
    def test_load_material_stats(self):
        """Test loading material-specific pitch focus stats."""
        mock_db = Mock()
        
        stat = Mock()
        stat.pitch_midi = 60
        stat.focus_card_id = 1
        stat.ema_score = 0.7
        stat.last_attempt_at = None
        
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = [stat]
        
        result = load_pitch_focus_stats(mock_db, user_id=1, material_id=10)
        
        assert (60, 1) in result
        assert result[(60, 1)] == (0.7, None)
    
    def test_load_empty_stats(self):
        """Test empty stats."""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.filter.return_value.all.return_value = []
        
        result = load_pitch_focus_stats(mock_db, user_id=1)
        
        assert result == {}


class TestLoadFocusCardIds:
    """Test load_focus_card_ids function."""
    
    def test_load_focus_card_ids(self):
        """Test loading focus card IDs."""
        mock_db = Mock()
        mock_db.query.return_value.all.return_value = [(1,), (2,), (3,)]
        
        result = load_focus_card_ids(mock_db)
        
        assert result == [1, 2, 3]
    
    def test_load_empty_focus_cards(self):
        """Test empty focus cards."""
        mock_db = Mock()
        mock_db.query.return_value.all.return_value = []
        
        result = load_focus_card_ids(mock_db)
        
        assert result == []
