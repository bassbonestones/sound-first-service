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
    
    def test_day0_capabilities_are_strings(self):
        """All capabilities should be strings."""
        for cap in DAY0_BASE_CAPABILITIES:
            assert isinstance(cap, str)
    
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
