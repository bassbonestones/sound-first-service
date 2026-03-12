"""
Tests for session_service module.

Tests session generation service static methods and data structures.
"""

import pytest
from unittest.mock import MagicMock, patch
from dataclasses import asdict

from app.services.session_service import (
    GOAL_LABEL_MAP,
    CAPABILITY_GOAL_MAP,
    CATEGORY_FOR_CAPABILITY,
    MiniSessionData,
    SessionState,
    SessionService,
)


# =============================================================================
# CONSTANT VALIDATION
# =============================================================================

class TestConstants:
    """Test session service constants."""
    
    def test_goal_label_map_entries(self):
        """All goal types should have labels."""
        expected_goals = [
            "repertoire_fluency",
            "fluency_through_keys",
            "range_expansion",
            "articulation_development",
            "tempo_build",
            "dynamic_control",
            "learn_by_ear",
            "musical_phrase_flow",
        ]
        for goal in expected_goals:
            assert goal in GOAL_LABEL_MAP, f"Missing label for {goal}"
    
    def test_goal_labels_are_human_readable(self):
        """Labels should be properly formatted."""
        for key, label in GOAL_LABEL_MAP.items():
            assert label[0].isupper(), f"Label '{label}' should start with uppercase"
            assert "_" not in label, f"Label '{label}' should not have underscores"
    
    def test_capability_goal_map_entries(self):
        """All capability types should have goal mappings."""
        expected_capabilities = [
            "repertoire_fluency",
            "technique",
            "range_expansion",
            "rhythm",
            "ear_training",
            "articulation",
        ]
        for cap in expected_capabilities:
            assert cap in CAPABILITY_GOAL_MAP, f"Missing goals for {cap}"
            assert len(CAPABILITY_GOAL_MAP[cap]) > 0, f"No goals for {cap}"
    
    def test_category_for_capability_entries(self):
        """All capabilities should map to categories."""
        for cap in CAPABILITY_GOAL_MAP.keys():
            assert cap in CATEGORY_FOR_CAPABILITY, f"Missing category for {cap}"
    
    def test_categories_are_valid(self):
        """Categories should be uppercase constants."""
        valid_categories = {"MUSICIANSHIP", "PHYSICAL", "TIME", "LISTENING"}
        for category in CATEGORY_FOR_CAPABILITY.values():
            assert category in valid_categories, f"Unknown category: {category}"


# =============================================================================
# DATA CLASSES
# =============================================================================

class TestMiniSessionData:
    """Test MiniSessionData dataclass."""
    
    @pytest.fixture
    def sample_mini_session_data(self):
        """Create sample mini session data."""
        return MiniSessionData(
            material_id=1,
            material_title="Test Material",
            focus_card_id=10,
            focus_card_name="Test Focus",
            focus_card_description="A test focus card",
            focus_card_category="PHYSICAL",
            focus_card_attention_cue="Listen carefully",
            focus_card_micro_cues=["Cue 1", "Cue 2"],
            focus_card_prompts={"before": "Setup", "after": "Reflect"},
            goal_type="repertoire_fluency",
            goal_label="Repertoire Fluency",
            show_notation=True,
            target_key="C major",
            original_key_center="C major",
            resolved_musicxml="<musicxml/>",
            starting_pitch="C4",
        )
    
    def test_create_mini_session_data(self, sample_mini_session_data):
        """Should create MiniSessionData with all fields."""
        assert sample_mini_session_data.material_id == 1
        assert sample_mini_session_data.material_title == "Test Material"
        assert sample_mini_session_data.focus_card_id == 10
        assert sample_mini_session_data.goal_type == "repertoire_fluency"
    
    def test_mini_session_has_required_fields(self, sample_mini_session_data):
        """Should have all required fields for mobile app."""
        data = asdict(sample_mini_session_data)
        required_fields = [
            "material_id",
            "material_title",
            "focus_card_id",
            "focus_card_name",
            "goal_type",
            "goal_label",
            "show_notation",
            "target_key",
            "starting_pitch",
        ]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"


class TestSessionState:
    """Test SessionState dataclass."""
    
    def test_create_session_state(self):
        """Should create SessionState with defaults."""
        state = SessionState(time_remaining=30.0)
        assert state.time_remaining == 30.0
        assert state.used_materials == set()
        assert state.used_focus_cards == set()
        assert state.recent_capabilities == []
        assert state.recent_keys == set()
        assert state.mini_sessions == []
    
    def test_session_state_tracks_used_materials(self):
        """Should track used materials."""
        state = SessionState(time_remaining=30.0)
        state.used_materials.add(1)
        state.used_materials.add(2)
        assert 1 in state.used_materials
        assert 2 in state.used_materials
        assert len(state.used_materials) == 2
    
    def test_session_state_tracks_recent_keys(self):
        """Should track recent keys played."""
        state = SessionState(time_remaining=30.0)
        state.recent_keys.add("C major")
        state.recent_keys.add("G major")
        assert "C major" in state.recent_keys
        assert "G major" in state.recent_keys


# =============================================================================
# SERVICE STATIC METHODS
# =============================================================================

class TestGetStartingPitch:
    """Test SessionService.get_starting_pitch method."""
    
    def test_tonal_material_returns_tonic(self):
        """Tonal material should return tonic as starting pitch."""
        material = MagicMock()
        material.pitch_reference_type = "TONAL"
        material.pitch_ref_json = '{"tonic": "G"}'
        
        result = SessionService.get_starting_pitch(material, None)
        assert result == "G4"
    
    def test_tonal_material_invalid_json_returns_C4(self):
        """Invalid JSON should default to C4."""
        material = MagicMock()
        material.pitch_reference_type = "TONAL"
        material.pitch_ref_json = "invalid json"
        
        result = SessionService.get_starting_pitch(material, None)
        assert result == "C4"
    
    def test_tonal_material_missing_tonic_returns_C4(self):
        """Missing tonic should default to C4."""
        material = MagicMock()
        material.pitch_reference_type = "TONAL"
        material.pitch_ref_json = '{"mode": "major"}'
        
        result = SessionService.get_starting_pitch(material, None)
        assert result == "C4"
    
    def test_anchor_interval_uses_target_key(self):
        """Anchor interval should use target key's tonic."""
        material = MagicMock()
        material.pitch_reference_type = "ANCHOR_INTERVAL"
        material.pitch_ref_json = None
        
        result = SessionService.get_starting_pitch(material, "G major")
        assert result == "G4"
    
    def test_anchor_interval_no_target_key_returns_C4(self):
        """Anchor interval without target key should default to C4."""
        material = MagicMock()
        material.pitch_reference_type = "ANCHOR_INTERVAL"
        material.pitch_ref_json = None
        
        result = SessionService.get_starting_pitch(material, None)
        assert result == "C4"
    
    def test_unknown_pitch_type_returns_C4(self):
        """Unknown pitch reference type should default to C4."""
        material = MagicMock()
        material.pitch_reference_type = "UNKNOWN"
        
        result = SessionService.get_starting_pitch(material, None)
        assert result == "C4"
    
    def test_none_pitch_type_returns_C4(self):
        """None pitch reference type should default to C4."""
        material = MagicMock()
        material.pitch_reference_type = None
        
        result = SessionService.get_starting_pitch(material, None)
        assert result == "C4"


class TestMaxMiniSessions:
    """Test SessionService constants."""
    
    def test_max_mini_sessions_is_reasonable(self):
        """MAX_MINI_SESSIONS should be a reasonable limit."""
        assert SessionService.MAX_MINI_SESSIONS > 0
        assert SessionService.MAX_MINI_SESSIONS <= 20


# =============================================================================
# BUILD MINI SESSION DATA
# =============================================================================

class TestBuildMiniSessionData:
    """Test SessionService.build_mini_session_data method."""
    
    @pytest.fixture
    def mock_material(self):
        """Create mock material."""
        material = MagicMock()
        material.id = 1
        material.title = "Test Tune"
        material.original_key_center = "C major"
        material.musicxml_canonical = "<musicxml/>"
        material.pitch_reference_type = "TONAL"
        material.pitch_ref_json = '{"tonic": "C"}'
        return material
    
    @pytest.fixture
    def mock_focus_card(self):
        """Create mock focus card."""
        focus_card = MagicMock()
        focus_card.id = 10
        focus_card.name = "Steady Beat"
        focus_card.description = "Keep a steady tempo"
        focus_card.category = "TIME"
        focus_card.attention_cue = "Feel the pulse"
        focus_card.micro_cues = '["Count internally", "Subdivide"]'
        focus_card.prompts = '{"before": "Set tempo", "after": "How was it?"}'
        return focus_card
    
    def test_builds_mini_session_with_defaults(self, mock_material, mock_focus_card):
        """Should build mini session data with defaults."""
        result = SessionService.build_mini_session_data(
            mock_material,
            mock_focus_card,
            "repertoire_fluency"
        )
        
        assert result.material_id == 1
        assert result.material_title == "Test Tune"
        assert result.focus_card_id == 10
        assert result.focus_card_name == "Steady Beat"
        assert result.goal_type == "repertoire_fluency"
        assert result.goal_label == "Repertoire Fluency"
        assert result.target_key == "C major"
    
    def test_uses_provided_target_key(self, mock_material, mock_focus_card):
        """Should use provided target key."""
        result = SessionService.build_mini_session_data(
            mock_material,
            mock_focus_card,
            "fluency_through_keys",
            target_key="G major"
        )
        
        assert result.target_key == "G major"
    
    def test_goal_label_from_map(self, mock_material, mock_focus_card):
        """Should use GOAL_LABEL_MAP for label."""
        result = SessionService.build_mini_session_data(
            mock_material,
            mock_focus_card,
            "tempo_build"
        )
        
        assert result.goal_label == "Tempo Building"
    
    def test_unknown_goal_gets_formatted_label(self, mock_material, mock_focus_card):
        """Unknown goal types should get formatted label."""
        result = SessionService.build_mini_session_data(
            mock_material,
            mock_focus_card,
            "custom_goal_type"
        )
        
        assert result.goal_label == "Custom Goal Type"
    
    def test_parses_micro_cues(self, mock_material, mock_focus_card):
        """Should parse JSON micro cues."""
        result = SessionService.build_mini_session_data(
            mock_material,
            mock_focus_card,
            "repertoire_fluency"
        )
        
        assert isinstance(result.focus_card_micro_cues, list)
    
    def test_parses_prompts(self, mock_material, mock_focus_card):
        """Should parse JSON prompts as dict."""
        result = SessionService.build_mini_session_data(
            mock_material,
            mock_focus_card,
            "repertoire_fluency"
        )
        
        assert isinstance(result.focus_card_prompts, dict)


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestGoalCapabilityIntegration:
    """Test that goals and capabilities are properly connected."""
    
    def test_all_capability_goals_exist_in_label_map(self):
        """All goals referenced by capabilities should have labels."""
        for capability, goals in CAPABILITY_GOAL_MAP.items():
            for goal in goals:
                assert goal in GOAL_LABEL_MAP, (
                    f"Goal '{goal}' from capability '{capability}' missing label"
                )
    
    def test_categories_cover_all_capabilities(self):
        """All capabilities should have a category."""
        for capability in CAPABILITY_GOAL_MAP.keys():
            assert capability in CATEGORY_FOR_CAPABILITY
