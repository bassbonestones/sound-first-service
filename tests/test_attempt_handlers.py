"""Tests for app/services/engine/attempt_handlers.py"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch, PropertyMock
from datetime import datetime

from app.services.engine.attempt_handlers import (
    handle_record_attempt,
    update_capability_evidence,
    update_capability_mastery,
    check_soft_gate_requirements,
    set_user_capability_bit,
    update_user_ability_scores,
    update_pitch_focus_stats,
    pitch_name_to_midi
)
from app.practice_engine import (
    EngineConfig, MaterialCandidate, CapabilityProgress, MaterialStatus,
    AttemptResult, DEFAULT_CONFIG
)


class TestPitchNameToMidi:
    """Test pitch_name_to_midi function."""
    
    def test_middle_c(self):
        """Test C4 = 60 (middle C)."""
        assert pitch_name_to_midi("C4") == 60
    
    def test_c5(self):
        """Test C5 = 72."""
        assert pitch_name_to_midi("C5") == 72
    
    def test_a4(self):
        """Test A4 = 69 (concert pitch)."""
        assert pitch_name_to_midi("A4") == 69
    
    def test_c_sharp(self):
        """Test C#4 = 61."""
        assert pitch_name_to_midi("C#4") == 61
    
    def test_b_flat(self):
        """Test Bb4 = 70."""
        assert pitch_name_to_midi("Bb4") == 70
    
    def test_double_sharp(self):
        """Test C##4 = 62."""
        assert pitch_name_to_midi("C##4") == 62
    
    def test_double_flat(self):
        """Test Dbb4 = 60."""
        assert pitch_name_to_midi("Dbb4") == 60
    
    def test_lowercase(self):
        """Test lowercase conversion."""
        assert pitch_name_to_midi("c4") == 60
    
    def test_empty_string(self):
        """Test empty string returns default 60."""
        assert pitch_name_to_midi("") == 60
    
    def test_none(self):
        """Test None returns default 60."""
        assert pitch_name_to_midi(None) == 60
    
    def test_invalid_octave(self):
        """Test invalid octave defaults to 4."""
        assert pitch_name_to_midi("Cx") == 60  # C4 equivalent


class TestCheckSoftGateRequirements:
    """Test check_soft_gate_requirements function."""
    
    def test_no_requirements(self):
        """Test returns True when no requirements."""
        mock_db = Mock()
        mock_cap = Mock()
        mock_cap.soft_gate_requirements = None
        
        result = check_soft_gate_requirements(mock_db, 1, mock_cap)
        assert result is True
    
    def test_invalid_json(self):
        """Test returns True on invalid JSON."""
        mock_db = Mock()
        mock_cap = Mock()
        mock_cap.soft_gate_requirements = "not valid json"
        
        result = check_soft_gate_requirements(mock_db, 1, mock_cap)
        assert result is True
    
    def test_non_dict_requirements(self):
        """Test returns True when requirements is not a dict."""
        mock_db = Mock()
        mock_cap = Mock()
        mock_cap.soft_gate_requirements = json.dumps([1, 2, 3])
        
        result = check_soft_gate_requirements(mock_db, 1, mock_cap)
        assert result is True
    
    def test_met_requirements(self):
        """Test returns True when requirements are met."""
        mock_db = Mock()
        mock_cap = Mock()
        mock_cap.soft_gate_requirements = json.dumps({"interval_velocity": 50.0})
        
        mock_state = Mock()
        mock_state.comfortable_value = 60.0
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        
        result = check_soft_gate_requirements(mock_db, 1, mock_cap)
        assert result is True
    
    def test_unmet_requirements(self):
        """Test returns False when requirements not met."""
        mock_db = Mock()
        mock_cap = Mock()
        mock_cap.soft_gate_requirements = json.dumps({"interval_velocity": 50.0})
        
        mock_state = Mock()
        mock_state.comfortable_value = 40.0  # Below threshold
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        
        result = check_soft_gate_requirements(mock_db, 1, mock_cap)
        assert result is False
    
    def test_missing_state(self):
        """Test returns False when state record doesn't exist."""
        mock_db = Mock()
        mock_cap = Mock()
        mock_cap.soft_gate_requirements = json.dumps({"interval_velocity": 50.0})
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        result = check_soft_gate_requirements(mock_db, 1, mock_cap)
        assert result is False


class TestSetUserCapabilityBit:
    """Test set_user_capability_bit function."""
    
    def test_set_bit_in_mask_0(self):
        """Test setting bit in first mask."""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.cap_mask_0 = 0
        mock_db.query.return_value.get.return_value = mock_user
        
        set_user_capability_bit(mock_db, 1, bit_index=5)
        
        assert mock_user.cap_mask_0 == (1 << 5)
    
    def test_set_bit_in_mask_1(self):
        """Test setting bit in second mask (bits 64-127)."""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.cap_mask_1 = 0
        mock_db.query.return_value.get.return_value = mock_user
        
        set_user_capability_bit(mock_db, 1, bit_index=65)
        
        assert mock_user.cap_mask_1 == (1 << 1)
    
    def test_no_user(self):
        """Test does nothing when user not found."""
        mock_db = Mock()
        mock_db.query.return_value.get.return_value = None
        
        # Should not raise
        set_user_capability_bit(mock_db, 1, bit_index=5)
    
    def test_preserve_existing_bits(self):
        """Test preserves existing bits."""
        mock_db = Mock()
        mock_user = Mock()
        mock_user.cap_mask_0 = 0b1010  # bits 1 and 3 set
        mock_db.query.return_value.get.return_value = mock_user
        
        set_user_capability_bit(mock_db, 1, bit_index=5)
        
        assert mock_user.cap_mask_0 == 0b101010  # bits 1, 3, and 5


class TestUpdateCapabilityEvidence:
    """Test update_capability_evidence function."""
    
    def test_creates_evidence_events(self):
        """Test creates evidence events for each capability."""
        mock_db = Mock()
        now = datetime.now()
        
        # Setup existing user cap
        mock_user_cap = Mock()
        mock_user_cap.evidence_count = 5
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user_cap
        
        update_capability_evidence(
            db=mock_db,
            user_id=1,
            material_id=10,
            attempt_id=100,
            rating=4,
            capability_ids=[1, 2, 3],
            is_off_course=False,
            now=now
        )
        
        # Should add 3 evidence events
        assert mock_db.add.call_count == 3
        # Should increment evidence count 3 times
        assert mock_user_cap.evidence_count == 8  # 5 + 3
    
    def test_handles_none_evidence_count(self):
        """Test handles None evidence count."""
        mock_db = Mock()
        now = datetime.now()
        
        mock_user_cap = Mock()
        mock_user_cap.evidence_count = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user_cap
        
        update_capability_evidence(
            db=mock_db,
            user_id=1,
            material_id=10,
            attempt_id=100,
            rating=4,
            capability_ids=[1],
            is_off_course=False,
            now=now
        )
        
        assert mock_user_cap.evidence_count == 1


class TestUpdateCapabilityMastery:
    """Test update_capability_mastery function."""
    
    @patch('app.services.engine.attempt_handlers.check_soft_gate_requirements')
    @patch('app.services.engine.attempt_handlers.set_user_capability_bit')
    def test_updates_mastery_when_requirements_met(self, mock_set_bit, mock_check_req):
        """Test updates mastery when soft gate requirements met."""
        mock_db = Mock()
        now = datetime.now()
        
        # Setup capability
        mock_cap = Mock()
        mock_cap.bit_index = 5
        mock_db.query.return_value.get.return_value = mock_cap
        
        # Setup user capability (not yet mastered)
        mock_user_cap = Mock()
        mock_user_cap.mastered_at = None
        mock_db.query.return_value.filter.return_value.first.return_value = mock_user_cap
        
        mock_check_req.return_value = True
        
        update_capability_mastery(mock_db, user_id=1, capability_ids=[1], now=now)
        
        assert mock_user_cap.mastered_at == now
        mock_set_bit.assert_called_once_with(mock_db, 1, 5)
    
    @patch('app.services.engine.attempt_handlers.check_soft_gate_requirements')
    def test_skips_when_requirements_not_met(self, mock_check_req):
        """Test skips mastery when soft gate requirements not met."""
        mock_db = Mock()
        now = datetime.now()
        
        mock_cap = Mock()
        mock_db.query.return_value.get.return_value = mock_cap
        
        mock_check_req.return_value = False
        
        mock_user_cap = Mock()
        mock_user_cap.mastered_at = None
        
        update_capability_mastery(mock_db, user_id=1, capability_ids=[1], now=now)
        
        # mastered_at should not be set
        assert mock_user_cap.mastered_at is None
    
    @patch('app.services.engine.attempt_handlers.check_soft_gate_requirements')
    def test_skips_when_capability_not_found(self, mock_check_req):
        """Test skips when capability not found."""
        mock_db = Mock()
        now = datetime.now()
        
        mock_db.query.return_value.get.return_value = None
        
        # Should not raise
        update_capability_mastery(mock_db, user_id=1, capability_ids=[999], now=now)
        mock_check_req.assert_not_called()


class TestUpdateUserAbilityScores:
    """Test update_user_ability_scores function."""
    
    @patch('app.services.engine.attempt_handlers.score_to_stage')
    def test_updates_scores_when_higher(self, mock_score_to_stage):
        """Test updates ability scores when material score is higher."""
        mock_db = Mock()
        
        # Setup analysis with scores
        mock_analysis = Mock()
        mock_analysis.interval_primary_score = 0.8
        mock_analysis.rhythm_primary_score = 0.6
        mock_analysis.tonal_primary_score = None  # Should be skipped
        mock_analysis.tempo_primary_score = 0.5
        mock_analysis.range_primary_score = 0.4
        mock_analysis.throughput_primary_score = 0.3
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_analysis, None]
        
        # Create new scores object
        mock_score_to_stage.return_value = 3
        
        update_user_ability_scores(mock_db, user_id=1, material_id=10)
        
        # Should have added new scores record
        mock_db.add.assert_called_once()
    
    def test_skips_when_no_analysis(self):
        """Test does nothing when analysis not found."""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        # Should not raise
        update_user_ability_scores(mock_db, user_id=1, material_id=10)
        mock_db.add.assert_not_called()
    
    @patch('app.services.engine.attempt_handlers.score_to_stage')
    def test_updates_existing_scores(self, mock_score_to_stage):
        """Test updates existing scores when higher."""
        mock_db = Mock()
        
        mock_analysis = Mock()
        mock_analysis.interval_primary_score = 0.8
        mock_analysis.rhythm_primary_score = None
        mock_analysis.tonal_primary_score = None
        mock_analysis.tempo_primary_score = None
        mock_analysis.range_primary_score = None
        mock_analysis.throughput_primary_score = None
        
        mock_scores = Mock()
        mock_scores.interval_ability_score = 0.5  # Lower than material score
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [mock_analysis, mock_scores]
        mock_score_to_stage.return_value = 4
        
        update_user_ability_scores(mock_db, user_id=1, material_id=10)
        
        assert mock_scores.interval_ability_score == 0.8
        assert mock_scores.interval_demonstrated_stage == 4


class TestUpdatePitchFocusStats:
    """Test update_pitch_focus_stats function."""
    
    @patch('app.services.engine.attempt_handlers.compute_ema')
    def test_creates_stats_for_both_contexts(self, mock_compute_ema):
        """Test creates stats for both MATERIAL and GLOBAL contexts."""
        mock_db = Mock()
        config = DEFAULT_CONFIG
        now = datetime.now()
        
        # No existing stats
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_compute_ema.return_value = 0.8
        
        update_pitch_focus_stats(
            db=mock_db,
            config=config,
            user_id=1,
            focus_card_id=2,
            pitch_midi=60,
            rating=4,
            material_id=10,
            now=now
        )
        
        # Should add 2 stats records (MATERIAL and GLOBAL)
        assert mock_db.add.call_count == 2
    
    @patch('app.services.engine.attempt_handlers.compute_ema')
    def test_updates_existing_stats(self, mock_compute_ema):
        """Test updates existing stats."""
        mock_db = Mock()
        config = DEFAULT_CONFIG
        now = datetime.now()
        
        mock_stat = Mock()
        mock_stat.ema_score = 0.5
        mock_stat.attempt_count = 10
        mock_db.query.return_value.filter.return_value.first.return_value = mock_stat
        mock_compute_ema.return_value = 0.6
        
        update_pitch_focus_stats(
            db=mock_db,
            config=config,
            user_id=1,
            focus_card_id=2,
            pitch_midi=60,
            rating=4,
            material_id=10,
            now=now
        )
        
        # EMA should be updated
        assert mock_stat.ema_score == 0.6
        # Attempt count incremented twice (MATERIAL and GLOBAL)
        assert mock_stat.attempt_count == 12
        assert mock_stat.last_attempt_at == now


class TestHandleRecordAttempt:
    """Test handle_record_attempt function."""
    
    @patch('app.services.engine.attempt_handlers.update_pitch_focus_stats')
    @patch('app.services.engine.attempt_handlers.update_user_ability_scores')
    @patch('app.services.engine.attempt_handlers.update_capability_mastery')
    @patch('app.services.engine.attempt_handlers.update_capability_evidence')
    @patch('app.services.engine.attempt_handlers.process_attempt')
    @patch('app.services.engine.attempt_handlers.UserMaterialState')
    def test_creates_new_material_state(
        self,
        mock_state_class,
        mock_process,
        mock_evidence,
        mock_mastery,
        mock_ability,
        mock_pitch_focus
    ):
        """Test creates new material state if none exists."""
        mock_db = Mock()
        config = DEFAULT_CONFIG
        
        # No existing state
        mock_db.query.return_value.filter.return_value.first.return_value = None
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        # Mock new state creation
        new_state = Mock()
        new_state.ema_score = 0.0
        new_state.attempt_count = 0
        new_state.status = MaterialStatus.UNEXPLORED.value
        new_state.guided_attempt_count = None
        new_state.manual_attempt_count = None
        mock_state_class.return_value = new_state
        
        # Setup process_attempt result
        mock_result = Mock(spec=AttemptResult)
        mock_result.new_ema = 0.8
        mock_result.new_attempt_count = 1
        mock_result.new_status = MaterialStatus.IN_PROGRESS
        mock_result.capability_evidence_added = []
        mock_result.capabilities_mastered = []
        mock_process.return_value = mock_result
        
        result = handle_record_attempt(
            db=mock_db,
            config=config,
            user_id=1,
            material_id=10,
            rating=4,
            cap_progress_dict={}
        )
        
        # Should add new state and attempt
        assert mock_db.add.call_count >= 2
        assert result == mock_result
    
    @patch('app.services.engine.attempt_handlers.update_pitch_focus_stats')
    @patch('app.services.engine.attempt_handlers.update_user_ability_scores')
    @patch('app.services.engine.attempt_handlers.update_capability_mastery')
    @patch('app.services.engine.attempt_handlers.update_capability_evidence')
    @patch('app.services.engine.attempt_handlers.process_attempt')
    def test_updates_existing_state(
        self,
        mock_process,
        mock_evidence,
        mock_mastery,
        mock_ability,
        mock_pitch_focus
    ):
        """Test updates existing material state."""
        mock_db = Mock()
        config = DEFAULT_CONFIG
        
        # Existing state
        mock_state = Mock()
        mock_state.ema_score = 0.5
        mock_state.attempt_count = 5
        mock_state.status = MaterialStatus.IN_PROGRESS.value  # Use enum value
        mock_state.guided_attempt_count = 3
        mock_state.manual_attempt_count = 2
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db.query.return_value.filter.return_value.all.return_value = [(1,)]
        
        mock_result = Mock(spec=AttemptResult)
        mock_result.new_ema = 0.6
        mock_result.new_attempt_count = 6
        mock_result.new_status = MaterialStatus.IN_PROGRESS
        mock_result.capability_evidence_added = []
        mock_result.capabilities_mastered = []
        mock_process.return_value = mock_result
        
        handle_record_attempt(
            db=mock_db,
            config=config,
            user_id=1,
            material_id=10,
            rating=4,
            cap_progress_dict={},
            is_off_course=False
        )
        
        assert mock_state.ema_score == 0.6
        assert mock_state.attempt_count == 6
        assert mock_state.guided_attempt_count == 4  # Incremented
    
    @patch('app.services.engine.attempt_handlers.update_pitch_focus_stats')
    @patch('app.services.engine.attempt_handlers.update_user_ability_scores')
    @patch('app.services.engine.attempt_handlers.update_capability_mastery')
    @patch('app.services.engine.attempt_handlers.update_capability_evidence')
    @patch('app.services.engine.attempt_handlers.process_attempt')
    def test_increments_manual_count_when_off_course(
        self,
        mock_process,
        mock_evidence,
        mock_mastery,
        mock_ability,
        mock_pitch_focus
    ):
        """Test increments manual_attempt_count when off course."""
        mock_db = Mock()
        config = DEFAULT_CONFIG
        
        mock_state = Mock()
        mock_state.ema_score = 0.5
        mock_state.attempt_count = 5
        mock_state.status = MaterialStatus.IN_PROGRESS.value  # Use enum value
        mock_state.guided_attempt_count = 3
        mock_state.manual_attempt_count = 2
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        mock_result = Mock(spec=AttemptResult)
        mock_result.new_ema = 0.6
        mock_result.new_attempt_count = 6
        mock_result.new_status = MaterialStatus.IN_PROGRESS
        mock_result.capability_evidence_added = []
        mock_result.capabilities_mastered = []
        mock_process.return_value = mock_result
        
        handle_record_attempt(
            db=mock_db,
            config=config,
            user_id=1,
            material_id=10,
            rating=4,
            cap_progress_dict={},
            is_off_course=True  # Off course
        )
        
        assert mock_state.manual_attempt_count == 3  # Incremented
    
    @patch('app.services.engine.attempt_handlers.update_pitch_focus_stats')
    @patch('app.services.engine.attempt_handlers.update_user_ability_scores')
    @patch('app.services.engine.attempt_handlers.update_capability_mastery')
    @patch('app.services.engine.attempt_handlers.update_capability_evidence')
    @patch('app.services.engine.attempt_handlers.process_attempt')
    def test_calls_ability_update_on_mastery(
        self,
        mock_process,
        mock_evidence,
        mock_mastery,
        mock_ability,
        mock_pitch_focus
    ):
        """Test calls update_user_ability_scores when material becomes mastered."""
        mock_db = Mock()
        config = DEFAULT_CONFIG
        
        mock_state = Mock()
        mock_state.ema_score = 0.9
        mock_state.attempt_count = 10
        mock_state.status = MaterialStatus.IN_PROGRESS.value  # Was not mastered
        mock_state.guided_attempt_count = 10
        mock_state.manual_attempt_count = 0
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        mock_result = Mock(spec=AttemptResult)
        mock_result.new_ema = 0.95
        mock_result.new_attempt_count = 11
        mock_result.new_status = MaterialStatus.MASTERED  # Now mastered
        mock_result.capability_evidence_added = []
        mock_result.capabilities_mastered = []
        mock_process.return_value = mock_result
        
        handle_record_attempt(
            db=mock_db,
            config=config,
            user_id=1,
            material_id=10,
            rating=5,
            cap_progress_dict={}
        )
        
        mock_ability.assert_called_once_with(mock_db, 1, 10)
    
    @patch('app.services.engine.attempt_handlers.update_pitch_focus_stats')
    @patch('app.services.engine.attempt_handlers.update_user_ability_scores')
    @patch('app.services.engine.attempt_handlers.update_capability_mastery')
    @patch('app.services.engine.attempt_handlers.update_capability_evidence')
    @patch('app.services.engine.attempt_handlers.process_attempt')
    def test_calls_pitch_focus_when_provided(
        self,
        mock_process,
        mock_evidence,
        mock_mastery,
        mock_ability,
        mock_pitch_focus
    ):
        """Test calls update_pitch_focus_stats when focus_card_id and pitch_midi provided."""
        mock_db = Mock()
        config = DEFAULT_CONFIG
        
        mock_state = Mock()
        mock_state.ema_score = 0.5
        mock_state.attempt_count = 5
        mock_state.status = MaterialStatus.IN_PROGRESS.value  # Use enum value
        mock_state.guided_attempt_count = 5
        mock_state.manual_attempt_count = 0
        mock_db.query.return_value.filter.return_value.first.return_value = mock_state
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        mock_result = Mock(spec=AttemptResult)
        mock_result.new_ema = 0.6
        mock_result.new_attempt_count = 6
        mock_result.new_status = MaterialStatus.IN_PROGRESS
        mock_result.capability_evidence_added = []
        mock_result.capabilities_mastered = []
        mock_process.return_value = mock_result
        
        handle_record_attempt(
            db=mock_db,
            config=config,
            user_id=1,
            material_id=10,
            rating=4,
            cap_progress_dict={},
            focus_card_id=2,
            pitch_midi=60
        )
        
        mock_pitch_focus.assert_called_once()
