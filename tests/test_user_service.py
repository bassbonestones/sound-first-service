"""
Tests for user_service module.

Tests user service utility methods and constants.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.services.user_service import (
    DAY0_BASE_CAPABILITIES,
    BASS_CLEF_INSTRUMENTS,
    MASK_ATTRS,
    JourneyStageResult,
    UserService,
)


# =============================================================================
# CONSTANT VALIDATION
# =============================================================================

class TestConstants:
    """Test user service constants."""
    
    def test_day0_base_capabilities(self):
        """Should have expected Day 0 capabilities."""
        expected = [
            "staff_basics",
            "ledger_lines",
            "note_basics",
            "first_note",
            "accidental_raise_pitch",
            "accidental_lower_pitch",
        ]
        assert DAY0_BASE_CAPABILITIES == expected
    
    def test_day0_capabilities_are_valid_strings(self):
        """All capabilities should be non-empty strings."""
        for cap in DAY0_BASE_CAPABILITIES:
            assert isinstance(cap, str), f"Capability should be string: {cap}"
            assert len(cap) > 0, f"Capability should be non-empty: {cap}"
            assert not cap.isspace(), f"Capability should not be whitespace: {cap}"
    
    def test_bass_clef_instruments_includes_trombone(self):
        """Bass clef instruments should include trombone."""
        assert "Tenor Trombone" in BASS_CLEF_INSTRUMENTS
        assert "trombone" in BASS_CLEF_INSTRUMENTS
    
    def test_bass_clef_instruments_includes_tuba(self):
        """Bass clef instruments should include tuba."""
        assert "Tuba" in BASS_CLEF_INSTRUMENTS
        assert "tuba" in BASS_CLEF_INSTRUMENTS
    
    def test_bass_clef_instruments_includes_cello(self):
        """Bass clef instruments should include cello."""
        assert "Cello" in BASS_CLEF_INSTRUMENTS
        assert "cello" in BASS_CLEF_INSTRUMENTS
    
    def test_mask_attrs_has_8_masks(self):
        """Should have exactly 8 capability mask attributes."""
        assert len(MASK_ATTRS) == 8
        for i in range(8):
            assert f'cap_mask_{i}' in MASK_ATTRS


# =============================================================================
# DATA CLASSES
# =============================================================================

class TestJourneyStageResult:
    """Test JourneyStageResult dataclass."""
    
    def test_create_journey_stage_result(self):
        """Should create JourneyStageResult with all fields."""
        result = JourneyStageResult(
            stage=2,
            stage_name="Intermediate",
            factors=["theory", "rhythm"],
            metrics={"lessons_completed": 5}
        )
        assert result.stage == 2
        assert result.stage_name == "Intermediate"
        assert result.factors == ["theory", "rhythm"]
        assert result.metrics["lessons_completed"] == 5
    
    def test_journey_stage_result_equality(self):
        """Equal results should be equal."""
        result1 = JourneyStageResult(
            stage=1,
            stage_name="Beginner",
            factors=[],
            metrics={}
        )
        result2 = JourneyStageResult(
            stage=1,
            stage_name="Beginner",
            factors=[],
            metrics={}
        )
        assert result1 == result2


# =============================================================================
# GET CLEF CAPABILITY
# =============================================================================

class TestGetClefCapability:
    """Test UserService.get_clef_capability method."""
    
    def test_trombone_gets_bass_clef(self):
        """Trombone should get bass clef."""
        assert UserService.get_clef_capability("Tenor Trombone") == "clef_bass"
    
    def test_trombone_lowercase_gets_bass_clef(self):
        """Lowercase trombone should get bass clef."""
        assert UserService.get_clef_capability("trombone") == "clef_bass"
    
    def test_bass_trombone_gets_bass_clef(self):
        """Bass trombone should get bass clef."""
        assert UserService.get_clef_capability("Bass Trombone") == "clef_bass"
    
    def test_euphonium_gets_bass_clef(self):
        """Euphonium should get bass clef."""
        assert UserService.get_clef_capability("Euphonium") == "clef_bass"
        assert UserService.get_clef_capability("euphonium") == "clef_bass"
    
    def test_tuba_gets_bass_clef(self):
        """Tuba should get bass clef."""
        assert UserService.get_clef_capability("Tuba") == "clef_bass"
        assert UserService.get_clef_capability("tuba") == "clef_bass"
    
    def test_bassoon_gets_bass_clef(self):
        """Bassoon should get bass clef."""
        assert UserService.get_clef_capability("Bassoon") == "clef_bass"
        assert UserService.get_clef_capability("bassoon") == "clef_bass"
    
    def test_cello_gets_bass_clef(self):
        """Cello should get bass clef."""
        assert UserService.get_clef_capability("Cello") == "clef_bass"
        assert UserService.get_clef_capability("cello") == "clef_bass"
    
    def test_double_bass_gets_bass_clef(self):
        """Double bass should get bass clef."""
        assert UserService.get_clef_capability("Double Bass") == "clef_bass"
        assert UserService.get_clef_capability("double_bass") == "clef_bass"
    
    def test_trumpet_gets_treble_clef(self):
        """Trumpet should get treble clef."""
        assert UserService.get_clef_capability("Trumpet") == "clef_treble"
    
    def test_flute_gets_treble_clef(self):
        """Flute should get treble clef."""
        assert UserService.get_clef_capability("Flute") == "clef_treble"
    
    def test_violin_gets_treble_clef(self):
        """Violin should get treble clef."""
        assert UserService.get_clef_capability("Violin") == "clef_treble"
    
    def test_saxophone_gets_treble_clef(self):
        """Saxophone should get treble clef."""
        assert UserService.get_clef_capability("Alto Saxophone") == "clef_treble"
        assert UserService.get_clef_capability("Tenor Saxophone") == "clef_treble"
    
    def test_clarinet_gets_treble_clef(self):
        """Clarinet should get treble clef."""
        assert UserService.get_clef_capability("Clarinet") == "clef_treble"
    
    def test_piano_gets_treble_clef(self):
        """Piano defaults to treble clef."""
        assert UserService.get_clef_capability("Piano") == "clef_treble"
    
    def test_none_instrument_gets_treble_clef(self):
        """None instrument defaults to treble clef."""
        assert UserService.get_clef_capability(None) == "clef_treble"
    
    def test_empty_string_gets_treble_clef(self):
        """Empty string defaults to treble clef."""
        assert UserService.get_clef_capability("") == "clef_treble"
    
    def test_unknown_instrument_gets_treble_clef(self):
        """Unknown instruments default to treble clef."""
        assert UserService.get_clef_capability("Kazoo") == "clef_treble"
        assert UserService.get_clef_capability("Recorder") == "clef_treble"


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestCapabilityGrantingLogic:
    """Test capability granting logic without database."""
    
    def test_day0_caps_plus_clef_for_trombone(self):
        """Trombone should get Day 0 caps plus bass clef."""
        base_caps = DAY0_BASE_CAPABILITIES.copy()
        clef = UserService.get_clef_capability("Tenor Trombone")
        all_caps = base_caps + [clef]
        
        assert "clef_bass" in all_caps
        assert "clef_treble" not in all_caps
        assert len(all_caps) == 7  # 6 base + 1 clef
    
    def test_day0_caps_plus_clef_for_trumpet(self):
        """Trumpet should get Day 0 caps plus treble clef."""
        base_caps = DAY0_BASE_CAPABILITIES.copy()
        clef = UserService.get_clef_capability("Trumpet")
        all_caps = base_caps + [clef]
        
        assert "clef_treble" in all_caps
        assert "clef_bass" not in all_caps
        assert len(all_caps) == 7  # 6 base + 1 clef
    
    def test_all_bass_clef_instruments_get_bass_clef(self):
        """All bass clef instruments should get bass clef capability."""
        for instrument in BASS_CLEF_INSTRUMENTS:
            assert UserService.get_clef_capability(instrument) == "clef_bass", (
                f"Instrument '{instrument}' should get bass clef"
            )


class TestMaskAttributes:
    """Test capability mask attribute definitions."""
    
    def test_mask_attrs_are_sequential(self):
        """Mask attributes should be sequentially numbered."""
        for i, attr in enumerate(MASK_ATTRS):
            assert attr == f'cap_mask_{i}'
    
    def test_mask_attrs_can_cover_256_capabilities(self):
        """8 64-bit masks can cover 512 capabilities."""
        # 8 masks * 64 bits = 512 capability slots
        assert len(MASK_ATTRS) * 64 >= 256


# =============================================================================
# SERVICE METHODS
# =============================================================================

class TestGrantDay0Capabilities:
    """Test grant_day0_capabilities class method."""
    
    def test_grant_global_capability_creates_new_record(self):
        """Test granting new global capability creates UserCapability."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.instrument = "Trombone"
        
        # Mock capability
        mock_cap = MagicMock()
        mock_cap.name = "note_quarter"
        mock_cap.is_global = True
        mock_cap.bit_index = 5
        
        # Set up capability query (filter returns all)
        cap_query = MagicMock()
        cap_query.all.return_value = [mock_cap]
        
        # Set up user capability query (filter returns first=None for new cap)
        user_cap_query = MagicMock()
        user_cap_query.first.return_value = None
        
        # Configure the query to return different things based on the model
        def query_side_effect(model):
            mock_query = MagicMock()
            if model.__name__ == 'Capability':
                mock_query.filter.return_value = cap_query
            else:  # UserCapability
                mock_query.filter.return_value = user_cap_query
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        # Patch DAY0 caps to just test one
        with patch('app.services.user_service.DAY0_BASE_CAPABILITIES', ["note_quarter"]):
            result = UserService.grant_day0_capabilities(
                mock_user, mock_db, instrument_id=10, instrument_name="Trombone"
            )
        
        # Should have created new user capability
        assert mock_db.add.called
        assert "note_quarter" in result
    
    def test_grant_instrument_specific_capability(self):
        """Test granting instrument-specific capability with instrument_id."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.instrument = "Trumpet"
        
        mock_cap = MagicMock()
        mock_cap.name = "range_span_3"
        mock_cap.is_global = False  # Instrument-specific
        mock_cap.bit_index = None
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_cap]
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch('app.services.user_service.DAY0_BASE_CAPABILITIES', ["range_span_3"]):
            result = UserService.grant_day0_capabilities(
                mock_user, mock_db, instrument_id=5, instrument_name="Trumpet"
            )
    
    def test_grant_existing_mastered_capability_skips(self):
        """Test that already mastered capability is skipped."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.instrument = None
        
        mock_cap = MagicMock()
        mock_cap.name = "note_quarter"
        mock_cap.is_global = True
        
        mock_existing = MagicMock()
        mock_existing.mastered_at = MagicMock()  # Already mastered
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_cap]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_existing
        
        with patch('app.services.user_service.DAY0_BASE_CAPABILITIES', ["note_quarter"]):
            result = UserService.grant_day0_capabilities(
                mock_user, mock_db, instrument_name="Flute"
            )
        
        # Should not have called add since capability already mastered
        assert "note_quarter" not in result


class TestBuildJourneyMetrics:
    """Test build_journey_metrics class method."""
    
    @patch.object(UserService, '_build_attempt_history')
    @patch('app.services.user_service.build_sr_item_from_db')
    @patch('app.services.user_service.estimate_mastery_level')
    def test_build_journey_metrics_basic(
        self, mock_estimate, mock_build_sr, mock_build_history
    ):
        """Test building basic journey metrics."""
        mock_db = MagicMock()
        
        # Mock empty queries
        mock_db.query.return_value.filter_by.return_value.all.return_value = []
        mock_db.query.return_value.filter_by.return_value.count.return_value = 0
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_build_history.return_value = {}
        
        result = UserService.build_journey_metrics(user_id=1, db=mock_db)
        
        assert result.total_sessions == 0
        assert result.total_attempts == 0
    
    @patch.object(UserService, '_build_attempt_history')
    @patch('app.services.user_service.build_sr_item_from_db')
    @patch('app.services.user_service.estimate_mastery_level')
    def test_build_journey_metrics_with_sessions(
        self, mock_estimate, mock_build_sr, mock_build_history
    ):
        """Test building metrics with sessions."""
        mock_db = MagicMock()
        
        # Mock sessions
        import datetime
        mock_session = MagicMock()
        mock_session.started_at = datetime.datetime.now() - datetime.timedelta(days=5)
        mock_session.practice_mode = "guided"
        
        mock_db.query.return_value.filter_by.return_value.all.return_value = [mock_session]
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_build_history.return_value = {}
        
        result = UserService.build_journey_metrics(user_id=1, db=mock_db)
        
        assert result.total_sessions == 1
        assert result.days_since_first_session >= 5
    
    @patch.object(UserService, '_build_attempt_history')
    @patch('app.services.user_service.build_sr_item_from_db')
    @patch('app.services.user_service.estimate_mastery_level')
    def test_build_journey_metrics_with_attempts(
        self, mock_estimate, mock_build_sr, mock_build_history
    ):
        """Test building metrics with attempts."""
        mock_db = MagicMock()
        
        mock_attempt = MagicMock()
        mock_attempt.rating = 4
        mock_attempt.fatigue = 2
        mock_attempt.material_id = 1
        
        mock_db.query.return_value.filter_by.return_value.all.side_effect = [
            [],  # sessions
            [mock_attempt]  # attempts
        ]
        mock_db.query.return_value.all.return_value = []
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        mock_build_history.return_value = {}
        
        result = UserService.build_journey_metrics(user_id=1, db=mock_db)
        
        assert result.total_attempts == 1
        assert result.average_rating == 4.0
        assert result.average_fatigue == 2.0


class TestResetUserData:
    """Test reset_user_data class method."""
    
    def test_reset_user_data_clears_profile(self):
        """Test that user profile fields are cleared."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.instrument = "Trombone"
        mock_user.resonant_note = "C4"
        
        mock_db.query.return_value.filter_by.return_value.all.return_value = []
        
        UserService.reset_user_data(mock_user, mock_db)
        
        assert mock_user.instrument is None
        assert mock_user.resonant_note is None
        assert mock_user.day0_completed == False
    
    def test_reset_user_data_deletes_attempts(self):
        """Test that practice attempts are deleted."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_db.query.return_value.filter_by.return_value.all.return_value = []
        
        UserService.reset_user_data(mock_user, mock_db)
        
        # Should have called delete on PracticeAttempt
        assert mock_db.query.return_value.filter_by.return_value.delete.called
    
    def test_reset_user_data_clears_bitmasks(self):
        """Test that capability bitmasks are reset."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_db.query.return_value.filter_by.return_value.all.return_value = []
        
        UserService.reset_user_data(mock_user, mock_db)
        
        # All mask attributes should be set to 0
        for attr in MASK_ATTRS:
            assert getattr(mock_user, attr) == 0


class TestGrantCapability:
    """Test grant_capability class method."""
    
    @patch.object(UserService, '_set_capability_bit')
    def test_grant_new_capability(self, mock_set_bit):
        """Test granting a new capability."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_cap = MagicMock()
        mock_cap.id = 10
        mock_cap.bit_index = 5
        
        # No existing capability
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        was_granted, message = UserService.grant_capability(mock_user, mock_cap, mock_db)
        
        assert was_granted == True
        assert message == "Capability granted"
        assert mock_db.add.called
        mock_set_bit.assert_called_once_with(mock_user, 5, True)
    
    @patch.object(UserService, '_set_capability_bit')
    def test_grant_already_active_capability(self, mock_set_bit):
        """Test granting already active capability returns false."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_cap = MagicMock()
        mock_cap.id = 10
        
        # Existing active capability
        mock_existing = MagicMock()
        mock_existing.is_active = True
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_existing
        
        was_granted, message = UserService.grant_capability(mock_user, mock_cap, mock_db)
        
        assert was_granted == False
        assert message == "Capability already granted"
    
    @patch.object(UserService, '_set_capability_bit')
    def test_grant_reactivates_deactivated_capability(self, mock_set_bit):
        """Test granting deactivated capability reactivates it."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_cap = MagicMock()
        mock_cap.id = 10
        mock_cap.bit_index = 5
        
        # Existing deactivated capability
        mock_existing = MagicMock()
        mock_existing.is_active = False
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_existing
        
        was_granted, message = UserService.grant_capability(mock_user, mock_cap, mock_db)
        
        assert was_granted == True
        assert mock_existing.is_active == True


class TestRevokeCapability:
    """Test revoke_capability class method."""
    
    @patch.object(UserService, '_set_capability_bit')
    def test_revoke_active_capability(self, mock_set_bit):
        """Test revoking an active capability."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_cap = MagicMock()
        mock_cap.id = 10
        mock_cap.bit_index = 5
        
        mock_existing = MagicMock()
        mock_existing.is_active = True
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_existing
        
        was_revoked, message = UserService.revoke_capability(mock_user, mock_cap, mock_db)
        
        assert was_revoked == True
        assert message == "Capability revoked"
        assert mock_existing.is_active == False
        mock_set_bit.assert_called_once_with(mock_user, 5, False)
    
    @patch.object(UserService, '_set_capability_bit')
    def test_revoke_nonexistent_capability(self, mock_set_bit):
        """Test revoking capability that doesn't exist."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_cap = MagicMock()
        mock_cap.id = 10
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        was_revoked, message = UserService.revoke_capability(mock_user, mock_cap, mock_db)
        
        assert was_revoked == False
        assert message == "Capability not currently active"
    
    @patch.object(UserService, '_set_capability_bit')
    def test_revoke_already_inactive_capability(self, mock_set_bit):
        """Test revoking already inactive capability."""
        mock_db = MagicMock()
        mock_user = MagicMock()
        mock_user.id = 1
        mock_cap = MagicMock()
        mock_cap.id = 10
        
        mock_existing = MagicMock()
        mock_existing.is_active = False
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_existing
        
        was_revoked, message = UserService.revoke_capability(mock_user, mock_cap, mock_db)
        
        assert was_revoked == False
        assert message == "Capability not currently active"


class TestSetCapabilityBit:
    """Test _set_capability_bit class method."""
    
    def test_set_capability_bit_none_index(self):
        """Test that None bit_index is handled."""
        mock_user = MagicMock()
        
        # Should not raise error when bit_index is None
        UserService._set_capability_bit(mock_user, None, True)
        
        # No setattr should be called
        assert not any(
            call[0][0] == 'cap_mask_0' 
            for call in mock_user.method_calls 
            if call[0] == '__setattr__'
        )
    
    def test_set_capability_bit_first_bucket(self):
        """Test setting bit in first bucket (0-63)."""
        mock_user = MagicMock()
        mock_user.cap_mask_0 = 0
        
        UserService._set_capability_bit(mock_user, 5, True)
        
        # Should set bit 5 in cap_mask_0
        assert mock_user.cap_mask_0 == (1 << 5)
    
    def test_set_capability_bit_second_bucket(self):
        """Test setting bit in second bucket (64-127)."""
        mock_user = MagicMock()
        mock_user.cap_mask_1 = 0
        
        UserService._set_capability_bit(mock_user, 64, True)  # Bucket 1, bit 0
        
        assert mock_user.cap_mask_1 == 1
    
    def test_clear_capability_bit(self):
        """Test clearing a capability bit."""
        mock_user = MagicMock()
        mock_user.cap_mask_0 = 0b11111111  # All bits set
        
        UserService._set_capability_bit(mock_user, 3, False)
        
        # Bit 3 should be cleared
        assert mock_user.cap_mask_0 == (0b11111111 & ~(1 << 3))


class TestBuildAttemptHistory:
    """Test _build_attempt_history static method."""
    
    def test_build_empty_history(self):
        """Test building history with no attempts."""
        result = UserService._build_attempt_history([])
        assert result == {}
    
    def test_build_history_single_attempt(self):
        """Test building history with single attempt."""
        mock_attempt = MagicMock()
        mock_attempt.material_id = 1
        mock_attempt.rating = 4
        mock_attempt.timestamp = None
        
        result = UserService._build_attempt_history([mock_attempt])
        
        assert 1 in result
        assert len(result[1]) == 1
        assert result[1][0]["rating"] == 4
    
    def test_build_history_multiple_materials(self):
        """Test building history with multiple materials."""
        mock_attempt1 = MagicMock()
        mock_attempt1.material_id = 1
        mock_attempt1.rating = 4
        mock_attempt1.timestamp = None
        
        mock_attempt2 = MagicMock()
        mock_attempt2.material_id = 2
        mock_attempt2.rating = 5
        mock_attempt2.timestamp = None
        
        result = UserService._build_attempt_history([mock_attempt1, mock_attempt2])
        
        assert 1 in result
        assert 2 in result


class TestGetUserMasks:
    """Test get_user_masks class method."""
    
    def test_get_user_masks_all_zero(self):
        """Test getting masks when all are zero."""
        mock_user = MagicMock()
        for i in range(8):
            setattr(mock_user, f'cap_mask_{i}', 0)
        
        result = UserService.get_user_masks(mock_user)
        
        assert len(result) == 8
        assert all(m == 0 for m in result)
    
    def test_get_user_masks_with_values(self):
        """Test getting masks with actual values."""
        mock_user = MagicMock()
        for i in range(8):
            setattr(mock_user, f'cap_mask_{i}', i * 100)
        
        result = UserService.get_user_masks(mock_user)
        
        assert result == [0, 100, 200, 300, 400, 500, 600, 700]
    
    def test_get_user_masks_handles_none(self):
        """Test getting masks when some are None."""
        mock_user = MagicMock()
        mock_user.cap_mask_0 = None
        mock_user.cap_mask_1 = 100
        for i in range(2, 8):
            setattr(mock_user, f'cap_mask_{i}', 0)
        
        result = UserService.get_user_masks(mock_user)
        
        assert result[0] == 0  # None converted to 0
        assert result[1] == 100


class TestGrantRangeSpanCapability:
    """Test grant_range_span_capability class method."""
    
    @patch('app.services.user_service.RANGE_SPAN_CAPS', {5: 'range_span_5'})
    @patch('app.curriculum.utils.note_to_midi')
    def test_grant_range_span_new_capability(self, mock_note_to_midi):
        """Test granting new range span capability."""
        mock_db = MagicMock()
        mock_note_to_midi.side_effect = [60, 65]  # C4=60, F4=65 -> span 5
        
        mock_cap = MagicMock()
        mock_cap.id = 10
        mock_cap.evidence_required_count = 3
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_cap,  # Capability lookup
            None,  # No existing mastered
            None,  # No existing unmastered
        ]
        
        result = UserService.grant_range_span_capability(
            db=mock_db,
            user_id=1,
            instrument_id=5,
            range_low="C4",
            range_high="F4"
        )
        
        assert result == ['range_span_5']
        assert mock_db.add.called
    
    @patch('app.services.user_service.RANGE_SPAN_CAPS', {5: 'range_span_5'})
    @patch('app.curriculum.utils.note_to_midi')
    def test_grant_range_span_already_mastered(self, mock_note_to_midi):
        """Test that already mastered capability returns empty."""
        mock_db = MagicMock()
        mock_note_to_midi.side_effect = [60, 65]
        
        mock_cap = MagicMock()
        mock_cap.id = 10
        
        mock_existing = MagicMock()
        mock_existing.mastered_at = MagicMock()
        
        mock_db.query.return_value.filter.return_value.first.side_effect = [
            mock_cap,
            mock_existing,  # Already mastered
        ]
        
        result = UserService.grant_range_span_capability(
            db=mock_db,
            user_id=1,
            instrument_id=5,
            range_low="C4",
            range_high="F4"
        )
        
        assert result == []
    
    def test_grant_range_span_empty_range(self):
        """Test that empty range returns empty list."""
        mock_db = MagicMock()
        
        result = UserService.grant_range_span_capability(
            db=mock_db,
            user_id=1,
            instrument_id=5,
            range_low=None,
            range_high="F4"
        )
        
        assert result == []
    
    @patch('app.curriculum.utils.note_to_midi')
    def test_grant_range_span_invalid_note(self, mock_note_to_midi):
        """Test that invalid note returns empty list."""
        mock_db = MagicMock()
        mock_note_to_midi.side_effect = ValueError("Invalid note")
        
        result = UserService.grant_range_span_capability(
            db=mock_db,
            user_id=1,
            instrument_id=5,
            range_low="InvalidNote",
            range_high="F4"
        )
        
        assert result == []


class TestGetUserService:
    """Test get_user_service function."""
    
    def test_get_user_service_creates_singleton(self):
        """Test that singleton is created."""
        from app.services.user_service import get_user_service
        import app.services.user_service as module
        
        module._user_service = None
        
        service = get_user_service()
        
        assert service is not None
    
    def test_get_user_service_returns_same_instance(self):
        """Test that same instance is returned."""
        from app.services.user_service import get_user_service
        import app.services.user_service as module
        
        module._user_service = None
        
        service1 = get_user_service()
        service2 = get_user_service()
        
        assert service1 is service2
