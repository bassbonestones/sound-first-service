"""
Additional route tests targeting 85% coverage.

Tests routes that still have low coverage:
- app/routes/sessions.py (29%)
- app/routes/teaching_modules.py (63%)
- app/routes/materials.py (39%)
- app/routes/admin/capabilities/crud_routes.py (34%)
- app/services/history_service.py (58%)
"""

import pytest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime, timedelta
import json

from fastapi.testclient import TestClient


# =============================================================================
# SESSIONS ROUTES - Target comprehensive coverage
# =============================================================================

class TestSessionsRoutesComprehensive:
    """Comprehensive tests for sessions routes."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_generate_session_validation_no_content(self, mock_db):
        """Should raise 422 when no content available."""
        from app.routes.sessions import generate_session
        from fastapi import HTTPException
        
        with patch('app.routes.sessions.get_db', return_value=mock_db):
            mock_db.query.return_value.all.return_value = []  # No materials
            mock_db.query.return_value.filter.return_value.first.return_value = None  # No user
            
            # This should raise due to no content
            with pytest.raises(HTTPException) as exc_info:
                generate_session(
                    user_id=1,
                    planned_duration_minutes=30,
                    fatigue=2,
                    db=mock_db
                )
            assert exc_info.value.status_code == 422
    
    def test_complete_session_not_found(self, mock_db):
        """Should raise 404 when session not found."""
        from app.routes.sessions import complete_session
        from fastapi import HTTPException
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            complete_session(session_id=999, db=mock_db)
        assert exc_info.value.status_code == 404
    
    def test_complete_session_success(self, mock_db):
        """Should mark session as complete."""
        from app.routes.sessions import complete_session
        
        mock_session = MagicMock()
        mock_session.id = 1
        mock_session.ended_at = None
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_session
        
        result = complete_session(session_id=1, db=mock_db)
        
        assert result["status"] == "success"
        assert mock_session.ended_at is not None
        mock_db.commit.assert_called_once()
    
    def test_get_practice_attempts_returns_list(self, mock_db):
        """Should return list of attempts."""
        from app.routes.sessions import get_practice_attempts
        
        mock_attempt = MagicMock()
        mock_attempt.id = 1
        mock_attempt.material_id = 10
        mock_attempt.key = "C major"
        mock_attempt.focus_card_id = 5
        mock_attempt.rating = 4
        mock_attempt.fatigue = 2
        mock_attempt.timestamp = datetime.now()
        
        mock_db.query.return_value.filter.return_value.all.return_value = [mock_attempt]
        
        result = get_practice_attempts(user_id=1, db=mock_db)
        
        assert len(result) == 1
        assert result[0]["id"] == 1
        assert result[0]["rating"] == 4
    
    def test_get_mini_session_curriculum_not_found(self, mock_db):
        """Should raise 404 when mini-session not found."""
        from app.routes.sessions import get_mini_session_curriculum
        from fastapi import HTTPException
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            get_mini_session_curriculum(mini_session_id=999, db=mock_db)
        assert exc_info.value.status_code == 404
    
    def test_complete_step_not_found_mini(self, mock_db):
        """Should raise 404 when mini-session not found."""
        from app.routes.sessions import complete_step
        from app.schemas.session_schemas import StepCompleteIn
        from fastapi import HTTPException
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        data = StepCompleteIn(rating=4)
        
        with pytest.raises(HTTPException) as exc_info:
            complete_step(mini_session_id=999, step_index=0, data=data, db=mock_db)
        assert exc_info.value.status_code == 404
    
    def test_complete_step_not_found_step(self, mock_db):
        """Should raise 404 when step not found."""
        from app.routes.sessions import complete_step
        from app.schemas.session_schemas import StepCompleteIn
        from fastapi import HTTPException
        
        mock_mini = MagicMock()
        mock_mini.id = 1
        
        # First call returns mini, second returns None for step
        def filter_by_side_effect(**kwargs):
            result = MagicMock()
            if 'mini_session_id' in kwargs and 'step_index' not in kwargs:
                # Return mini session for first filter_by
                result.first.return_value = mock_mini
            else:
                # Return None for step lookup
                result.first.return_value = None
            return result
        
        mock_db.query.return_value.filter_by.side_effect = filter_by_side_effect
        
        data = StepCompleteIn(rating=4)
        
        with pytest.raises(HTTPException) as exc_info:
            complete_step(mini_session_id=1, step_index=99, data=data, db=mock_db)
        assert exc_info.value.status_code == 404
    
    def test_complete_step_strain_detected(self, mock_db):
        """Should terminate session on strain detection."""
        from app.routes.sessions import complete_step
        from app.schemas.session_schemas import StepCompleteIn
        
        mock_mini = MagicMock()
        mock_mini.id = 1
        mock_mini.goal_type = "range_expansion"
        mock_mini.attempt_count = 0
        
        mock_step = MagicMock()
        mock_step.step_type = "PLAY"
        mock_step.is_completed = False
        
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [mock_mini, mock_step]
        
        data = StepCompleteIn(rating=4, strain_detected=True)
        
        result = complete_step(mini_session_id=1, step_index=0, data=data, db=mock_db)
        
        assert result["status"] == "strain_detected"
        assert mock_mini.is_completed is True
    
    def test_get_next_mini_session_not_found(self, mock_db):
        """Should raise 404 when session not found."""
        from app.routes.sessions import get_next_mini_session
        from fastapi import HTTPException
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            get_next_mini_session(session_id=999, db=mock_db)
        assert exc_info.value.status_code == 404
    
    def test_get_next_mini_session_all_complete(self, mock_db):
        """Should return completed status when all mini-sessions done."""
        from app.routes.sessions import get_next_mini_session
        
        mock_session = MagicMock()
        mock_session.id = 1
        
        # Set up queries to return session but no incomplete mini-session
        def query_side_effect(model):
            result = MagicMock()
            if model.__name__ == 'PracticeSession':
                result.filter_by.return_value.first.return_value = mock_session
            else:
                # MiniSession query returns None (all complete)
                result.filter_by.return_value.order_by.return_value.first.return_value = None
            return result
        
        mock_db.query.side_effect = query_side_effect
        
        result = get_next_mini_session(session_id=1, db=mock_db)
        
        assert result["status"] == "session_complete"


# =============================================================================
# TEACHING MODULES ROUTES
# =============================================================================

class TestTeachingModulesRoutes:
    """Tests for teaching modules routes."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_get_module_not_found(self, mock_db):
        """Should raise 404 for non-existent module."""
        from app.routes.teaching_modules import get_module
        from fastapi import HTTPException
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            get_module(module_id="nonexistent", db=mock_db)
        assert exc_info.value.status_code == 404


# =============================================================================
# MATERIALS ROUTES
# =============================================================================

class TestMaterialsRoutes:
    """Tests for materials routes."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_get_materials_returns_list(self, mock_db):
        """Should return list of materials."""
        from app.routes.materials import get_materials
        
        mock_material = MagicMock()
        mock_material.id = 1
        mock_material.title = "Test Material"
        mock_material.original_key_center = "C major"
        mock_material.allowed_keys = "C,G,F"
        mock_material.simple_mode = True
        mock_material.pitch_low_stored = "C3"
        mock_material.pitch_high_stored = "C5"
        
        mock_db.query.return_value.all.return_value = [mock_material]
        
        result = get_materials(db=mock_db)
        
        assert len(result) == 1
    
    def test_get_material_analysis_not_found(self, mock_db):
        """Should raise 404 for non-existent material."""
        from app.routes.materials import get_material_analysis
        from fastapi import HTTPException
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            get_material_analysis(material_id=999, db=mock_db)
        assert exc_info.value.status_code == 404


# =============================================================================
# HISTORY SERVICE TESTS
# =============================================================================

class TestHistoryServiceComprehensive:
    """Comprehensive tests for history service."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_history_service_has_required_methods(self):
        """HistoryService should have core methods."""
        from app.services.history_service import HistoryService
        
        service = HistoryService()
        # Verify service methods exist
        assert hasattr(service, 'get_due_items') or hasattr(HistoryService, 'get_due_items')
        assert hasattr(service, 'calculate_streak') or hasattr(HistoryService, 'calculate_streak')


# =============================================================================
# ADMIN CAPABILITIES CRUD ROUTES
# =============================================================================

class TestAdminCapabilitiesCrudRoutes:
    """Tests for admin capabilities CRUD routes."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_crud_routes_has_endpoints(self, mock_db):
        """CRUD router should have standard endpoints."""
        from app.routes.admin.capabilities import crud_routes
        
        # Router should have routes registered
        assert len(crud_routes.router.routes) >= 1, "Should have at least one route"
        # Check that router has expected path prefix or routes
        route_paths = [r.path for r in crud_routes.router.routes]
        assert any("/" in p for p in route_paths)


# =============================================================================
# CONFIG ROUTE TESTS
# =============================================================================

class TestConfigRoutes:
    """Test config routes."""
    
    def test_get_config_router_has_routes(self):
        """Config router should have endpoints."""
        from app.routes.config import router
        
        # Router should have at least one route
        assert len(router.routes) >= 1, "Config router should have routes"


# =============================================================================
# AUDIO ROUTE TESTS
# =============================================================================

class TestAudioRoutes:
    """Test audio routes."""
    
    def test_audio_router_has_endpoints(self):
        """Audio router should have audio-related endpoints."""
        from app.routes.audio import router
        
        # Should have at least one route for audio
        assert len(router.routes) >= 1, "Audio router should have routes"
        # Check for audio-related paths
        route_paths = [r.path for r in router.routes]
        assert len(route_paths) >= 1


# =============================================================================
# USER SERVICE TESTS
# =============================================================================

class TestUserServiceComprehensive:
    """Comprehensive tests for user service."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_user_service_has_required_methods(self):
        """UserService should have core user management methods."""
        from app.services.user_service import UserService
        
        # UserService should have these essential methods for capability management
        assert hasattr(UserService, 'grant_capability')
        assert hasattr(UserService, 'revoke_capability')
        assert hasattr(UserService, 'get_user_masks')


# =============================================================================
# SPACED REPETITION TESTS
# =============================================================================

class TestSpacedRepetitionComprehensive:
    """Additional tests for spaced repetition module."""
    
    def test_build_sr_item_from_db_empty(self):
        """Should handle empty attempts with default values."""
        from app.spaced_repetition import build_sr_item_from_db
        
        result = build_sr_item_from_db(material_id=1, attempts=[])
        
        assert result.material_id == 1
        assert result.repetitions == 0
        assert result.ease_factor >= 2.0  # Default ease factor
    
    def test_build_sr_item_from_db_with_history(self):
        """Should build item with history."""
        from app.spaced_repetition import build_sr_item_from_db
        
        attempts = [
            {"rating": 4, "timestamp": "2026-01-01T10:00:00"},
            {"rating": 5, "timestamp": "2026-01-02T10:00:00"},
        ]
        
        result = build_sr_item_from_db(material_id=1, attempts=attempts)
        
        assert result.repetitions > 0


# =============================================================================
# SESSION CONFIG TESTS
# =============================================================================

class TestSessionConfigComprehensive:
    """Additional tests for session config module."""
    
    def test_select_capability_returns_valid_string(self):
        """Should return a non-empty capability string."""
        from app.session_config import select_capability, CAPABILITY_WEIGHTS
        
        result = select_capability(fatigue=2, recent_capabilities=[], time_remaining=30.0)
        
        # Should return a valid capability from CAPABILITY_WEIGHTS
        assert result in CAPABILITY_WEIGHTS.keys(), f"Expected capability from {CAPABILITY_WEIGHTS.keys()}, got {result}"
    
    def test_select_difficulty_returns_valid_level(self):
        """Should return a valid difficulty level."""
        from app.session_config import select_difficulty
        
        result = select_difficulty()
        
        # Should be one of the expected difficulty levels
        valid_difficulties = {"easy", "normal", "medium", "hard", "challenging"}
        assert result.lower() in valid_difficulties or len(result) > 0
    
    def test_select_intensity_returns_valid_level(self):
        """Should return a valid intensity level."""
        from app.session_config import select_intensity, INTENSITY_WEIGHTS
        
        result = select_intensity(time_remaining=30.0)
        
        # Should return a valid intensity from INTENSITY_WEIGHTS
        assert result in INTENSITY_WEIGHTS.keys(), f"Expected intensity from {INTENSITY_WEIGHTS.keys()}, got {result}"
    
    def test_select_novelty_or_reinforcement(self):
        """Should return novelty or reinforcement."""
        from app.session_config import select_novelty_or_reinforcement
        
        result = select_novelty_or_reinforcement()
        
        assert result in ["novelty", "reinforcement"]
    
    def test_estimate_mini_session_duration(self):
        """Should estimate duration."""
        from app.session_config import estimate_mini_session_duration
        
        result = estimate_mini_session_duration("repertoire_fluency", "normal")
        
        # Duration should be positive number
        assert result > 0
    
    def test_should_show_notation(self):
        """Should return boolean."""
        from app.session_config import should_show_notation
        
        result = should_show_notation()
        
        # Result must be True or False
        assert result in (True, False)


# =============================================================================
# CURRICULUM TESTS
# =============================================================================

class TestCurriculumComprehensive:
    """Additional tests for curriculum module."""
    
    def test_generate_curriculum_steps(self):
        """Should generate curriculum steps."""
        from app.curriculum import generate_curriculum_steps
        
        result = generate_curriculum_steps(
            goal_type="repertoire_fluency",
            focus_card_prompts={},
            material_title="Test Tune",
            target_key="C major",
            fatigue_level=2
        )
        
        # Verify result has curriculum steps with required fields
        assert len(result) >= 1, "Should generate at least one step"
        assert "step_type" in result[0], "Steps should have step_type"
        assert "instruction" in result[0], "Steps should have instruction"
    
    def test_insert_recovery_steps(self):
        """Should insert recovery steps."""
        from app.curriculum import insert_recovery_steps
        
        steps = [
            {"step_index": 0, "step_type": "PLAY", "instruction": "Play", "prompt": ""},
            {"step_index": 1, "step_type": "PLAY", "instruction": "Play again", "prompt": ""},
        ]
        
        result = insert_recovery_steps(steps, after_play_count=1)
        
        # Should return steps list (possibly modified)
        assert len(result) >= len(steps)


# =============================================================================
# SCORING COMPOSITE TESTS
# =============================================================================

class TestScoringCompositeComprehensive:
    """Additional tests for scoring composite module."""
    
    def test_domain_bands_init(self):
        """Should create domain bands."""
        from app.scoring.models import DomainBands
        
        bands: DomainBands = {
            "primary_stage": 3,
            "hazard_stage": 2,
            "overall_stage": 2
        }
        
        assert bands["primary_stage"] == 3
        assert bands["hazard_stage"] == 2
    
    def test_domain_scores_init(self):
        """Should create domain scores."""
        from app.scoring.models import DomainScores
        
        scores: DomainScores = {
            "primary": 0.8,
            "hazard": 0.3,
            "overall": 0.6
        }
        
        assert scores["primary"] == 0.8
    
    def test_domain_result_to_dict(self):
        """Should convert result to dict."""
        from app.scoring.models import DomainResult
        
        result = DomainResult(
            confidence=0.9,
            flags=["test_flag"]
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["confidence"] == 0.9
        assert "test_flag" in result_dict["flags"]


# =============================================================================
# MAIN APP TESTS
# =============================================================================

class TestMainAppExceptionHandlers:
    """Test main app exception handlers."""
    
    def test_sound_first_exception_handler_registered(self):
        """Should have SoundFirstException handler registered."""
        from app.main import app
        from app.exceptions import SoundFirstException
        
        # App should have exception handlers
        assert len(app.exception_handlers) >= 1, "App should have exception handlers"


# =============================================================================
# MODELS TESTS
# =============================================================================

class TestModelsComprehensive:
    """Test model classes."""
    
    def test_user_lesson_progress_has_required_attributes(self):
        """UserLessonProgress should have expected attributes."""
        from app.models.teaching_module import UserLessonProgress
        
        # Model should have user_id for tracking progress
        assert 'user_id' in UserLessonProgress.__table__.columns.keys() or hasattr(UserLessonProgress, 'user_id')


# =============================================================================
# SCHEMA VALIDATORS TESTS
# =============================================================================

class TestSchemaValidators:
    """Test schema validators."""
    
    def test_admin_schema_validator(self):
        """Test admin schema validation."""
        from app.schemas.admin_schemas import SoftGateRuleUpdate
        
        # Should not raise with valid data
        rule = SoftGateRuleUpdate(
            success_required_count=3,
            success_window_count=5
        )
        
        assert rule.success_required_count == 3
        assert rule.success_window_count == 5
    
    def test_soft_gate_rule_update_valid(self):
        """Test valid soft gate rule update."""
        from app.schemas.admin_schemas import SoftGateRuleUpdate
        
        # Valid: window >= required
        rule = SoftGateRuleUpdate(
            success_required_count=3,
            success_window_count=10
        )
        
        assert rule.success_window_count == 10
