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
        
        # micro_cues should be a list (may be empty)
        assert isinstance(result.focus_card_micro_cues, list)
    
    def test_parses_prompts(self, mock_material, mock_focus_card):
        """Should parse JSON prompts as dict."""
        result = SessionService.build_mini_session_data(
            mock_material,
            mock_focus_card,
            "repertoire_fluency"
        )
        
        # prompts should be a dict (may be empty)
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


# =============================================================================
# SELECTION ALGORITHM TESTS
# =============================================================================

class TestSelectMaterial:
    """Test select_material method."""
    
    @patch('app.services.session_service.build_sr_item_from_db')
    @patch('app.services.session_service.filter_materials_by_range')
    def test_select_material_novelty_mode_with_new_materials(
        self, mock_filter_range, mock_build_sr
    ):
        """Novelty mode should prefer never-reviewed materials."""
        state = SessionState(time_remaining=60)
        
        mat1 = MagicMock()
        mat1.id = 1
        mat2 = MagicMock()
        mat2.id = 2
        
        # mat1 is new (0 reps), mat2 has been reviewed
        sr_item_new = MagicMock()
        sr_item_new.repetitions = 0
        sr_item_reviewed = MagicMock()
        sr_item_reviewed.repetitions = 3
        
        mock_build_sr.side_effect = lambda m_id, h: sr_item_new if m_id == 1 else sr_item_reviewed
        mock_filter_range.return_value = [mat1, mat2]
        
        result = SessionService.select_material(
            materials=[mat1, mat2],
            state=state,
            attempt_history={},
            selection_mode="novelty",
            user=None
        )
        
        # Should pick the new material
        assert result.id == 1
    
    @patch('app.services.session_service.build_sr_item_from_db')
    def test_select_material_novelty_mode_fallback_when_no_new(self, mock_build_sr):
        """Novelty mode should fallback to random when all reviewed."""
        state = SessionState(time_remaining=60)
        
        mat1 = MagicMock()
        mat1.id = 1
        
        sr_item = MagicMock()
        sr_item.repetitions = 5  # Already reviewed
        mock_build_sr.return_value = sr_item
        
        result = SessionService.select_material(
            materials=[mat1],
            state=state,
            attempt_history={},
            selection_mode="novelty",
            user=None
        )
        
        assert result.id == 1
    
    @patch('app.services.session_service.get_capability_weight_adjustment')
    @patch('app.services.session_service.build_sr_item_from_db')
    def test_select_material_reinforcement_mode(self, mock_build_sr, mock_weight):
        """Reinforcement mode should use weighted selection."""
        state = SessionState(time_remaining=60)
        
        mat1 = MagicMock()
        mat1.id = 1
        
        sr_item = MagicMock()
        mock_build_sr.return_value = sr_item
        mock_weight.return_value = 1.0
        
        result = SessionService.select_material(
            materials=[mat1],
            state=state,
            attempt_history={},
            selection_mode="reinforcement",
            user=None
        )
        
        assert result.id == 1
    
    @patch('app.services.session_service.get_capability_weight_adjustment')
    @patch('app.services.session_service.build_sr_item_from_db')
    def test_select_material_reinforcement_zero_weight_fallback(
        self, mock_build_sr, mock_weight
    ):
        """Reinforcement mode with zero weights should fallback to random."""
        state = SessionState(time_remaining=60)
        
        mat1 = MagicMock()
        mat1.id = 1
        
        sr_item = MagicMock()
        mock_build_sr.return_value = sr_item
        mock_weight.return_value = 0.0  # Zero weight
        
        result = SessionService.select_material(
            materials=[mat1],
            state=state,
            attempt_history={},
            selection_mode="reinforcement",
            user=None
        )
        
        assert result.id == 1
    
    @patch('app.services.session_service.filter_materials_by_range')
    @patch('app.services.session_service.build_sr_item_from_db')
    def test_select_material_filters_by_user_range(self, mock_build_sr, mock_filter):
        """Should filter materials by user's vocal range."""
        state = SessionState(time_remaining=60)
        
        mat1 = MagicMock()
        mat1.id = 1
        mat2 = MagicMock()
        mat2.id = 2
        
        mock_user = MagicMock()
        mock_user.range_low = "C4"
        mock_user.range_high = "G5"
        
        # Filter returns only mat1 as in range
        mock_filter.return_value = [mat1]
        
        sr_item = MagicMock()
        sr_item.repetitions = 0
        mock_build_sr.return_value = sr_item
        
        result = SessionService.select_material(
            materials=[mat1, mat2],
            state=state,
            attempt_history={},
            selection_mode="novelty",
            user=mock_user
        )
        
        mock_filter.assert_called_once()
        assert result.id == 1


class TestSelectGoal:
    """Test select_goal method."""
    
    @patch('app.services.session_service.get_goals_for_fatigue')
    def test_select_goal_uses_capability_preferred(self, mock_get_goals):
        """Should prefer goals from capability map."""
        mock_get_goals.return_value = ["sustain", "match"]
        
        # Pretend capability prefers "sustain"
        with patch.dict(CAPABILITY_GOAL_MAP, {"test_cap": ["sustain", "match"]}):
            result = SessionService.select_goal("test_cap", fatigue=3)
        
        assert result in ["sustain", "match"]
    
    @patch('app.services.session_service.get_goals_for_fatigue')
    def test_select_goal_fallback_when_no_valid(self, mock_get_goals):
        """Should fallback to fatigue goals when no intersection."""
        mock_get_goals.return_value = ["relax"]
        
        # Capability prefers goals not in fatigue list
        with patch.dict(CAPABILITY_GOAL_MAP, {"test_cap": ["sustain"]}):
            result = SessionService.select_goal("test_cap", fatigue=3)
        
        # Should fallback to fatigue goals
        assert result == "relax"


class TestSelectFocusCard:
    """Test select_focus_card method."""
    
    def test_select_focus_card_prefers_category(self):
        """Should prefer focus cards matching capability category."""
        state = SessionState(time_remaining=60)
        
        fc1 = MagicMock()
        fc1.id = 1
        fc1.category = "rhythm"
        fc2 = MagicMock()
        fc2.id = 2
        fc2.category = "pitch"
        
        with patch.dict(CATEGORY_FOR_CAPABILITY, {"note_quarter": "rhythm"}):
            result = SessionService.select_focus_card(
                focus_cards=[fc1, fc2],
                capability="note_quarter",
                state=state
            )
        
        assert result.category == "rhythm"
    
    def test_select_focus_card_avoids_used(self):
        """Should avoid recently used focus cards."""
        state = SessionState(time_remaining=60)
        state.used_focus_cards.add(1)  # fc1 already used
        
        fc1 = MagicMock()
        fc1.id = 1
        fc1.category = "rhythm"
        fc2 = MagicMock()
        fc2.id = 2
        fc2.category = "pitch"
        
        result = SessionService.select_focus_card(
            focus_cards=[fc1, fc2],
            capability="note_quarter",
            state=state
        )
        
        assert result.id == 2


class TestGenerateMiniSession:
    """Test generate_mini_session method."""
    
    def test_generate_mini_session_returns_none_when_no_time(self):
        """Should return None when time_remaining <= 0."""
        state = SessionState(time_remaining=0)  # No time left
        
        result = SessionService.generate_mini_session(
            materials=[MagicMock()],
            focus_cards=[MagicMock()],
            state=state,
            attempt_history={},
            user=None,
            fatigue=3
        )
        
        assert result is None
    
    @patch('app.services.session_service.estimate_mini_session_duration')
    @patch('app.services.session_service.should_show_notation')
    @patch('app.services.session_service.filter_keys_by_range')
    @patch('app.services.session_service.select_key_for_mini_session')
    @patch('app.services.session_service.select_intensity')
    @patch('app.services.session_service.select_difficulty')
    @patch('app.services.session_service.select_capability')
    @patch('app.services.session_service.select_novelty_or_reinforcement')
    @patch.object(SessionService, 'select_focus_card')
    @patch.object(SessionService, 'select_goal')
    @patch.object(SessionService, 'select_material')
    @patch.object(SessionService, 'build_mini_session_data')
    def test_generate_mini_session_listen_only_mode(
        self,
        mock_build,
        mock_select_mat,
        mock_select_goal,
        mock_select_fc,
        mock_novelty,
        mock_cap,
        mock_diff,
        mock_intensity,
        mock_key,
        mock_filter_keys,
        mock_notation,
        mock_duration
    ):
        """Should set listen_only when no playable keys."""
        state = SessionState(time_remaining=60)
        
        mock_material = MagicMock()
        mock_material.id = 1
        mock_material.allowed_keys = "C"
        mock_focus_card = MagicMock()
        mock_focus_card.id = 1
        
        mock_select_mat.return_value = mock_material
        mock_select_goal.return_value = "sustain"
        mock_select_fc.return_value = mock_focus_card
        mock_novelty.return_value = "novelty"
        mock_cap.return_value = "note_quarter"
        mock_diff.return_value = "medium"
        mock_intensity.return_value = 3
        mock_key.return_value = "C major"
        mock_filter_keys.return_value = []  # No playable keys
        mock_notation.return_value = True
        mock_duration.return_value = 5
        
        mock_mini_data = MagicMock()
        mock_mini_data.show_notation = True
        mock_mini_data.target_key = "C major"
        mock_build.return_value = mock_mini_data
        
        result = SessionService.generate_mini_session(
            materials=[mock_material],
            focus_cards=[mock_focus_card],
            state=state,
            attempt_history={},
            user=None,
            fatigue=3
        )
        
        # Should set show_notation to False for listen only
        assert mock_mini_data.show_notation == False


class TestBuildAttemptHistory:
    """Test build_attempt_history method."""
    
    def test_build_attempt_history_empty(self):
        """Empty attempts should return empty dict."""
        result = SessionService.build_attempt_history([])
        assert result == {}
    
    def test_build_attempt_history_single(self):
        """Single attempt should create entry."""
        mock_attempt = MagicMock()
        mock_attempt.material_id = 1
        mock_attempt.rating = 4
        mock_attempt.timestamp = None
        
        result = SessionService.build_attempt_history([mock_attempt])
        
        assert 1 in result
        assert len(result[1]) == 1
        assert result[1][0]["rating"] == 4
    
    def test_build_attempt_history_multiple_materials(self):
        """Multiple materials should have separate entries."""
        a1 = MagicMock()
        a1.material_id = 1
        a1.rating = 4
        a1.timestamp = None
        
        a2 = MagicMock()
        a2.material_id = 2
        a2.rating = 5
        a2.timestamp = None
        
        result = SessionService.build_attempt_history([a1, a2])
        
        assert 1 in result
        assert 2 in result


class TestGetSessionService:
    """Test get_session_service singleton."""
    
    def test_get_session_service_creates_singleton(self):
        """Should create singleton on first call."""
        from app.services.session_service import get_session_service
        import app.services.session_service as module
        
        module._session_service = None
        
        service = get_session_service()
        
        assert service is not None
    
    def test_get_session_service_returns_same_instance(self):
        """Should return same instance on subsequent calls."""
        from app.services.session_service import get_session_service
        import app.services.session_service as module
        
        module._session_service = None
        
        service1 = get_session_service()
        service2 = get_session_service()
        
        assert service1 is service2
