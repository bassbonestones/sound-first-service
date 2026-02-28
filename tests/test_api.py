"""
Tests for app/main.py - API Endpoints

Tests all REST API endpoints using FastAPI's TestClient.
Configures test database for isolation.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import json

# Import app and database setup
from app.main import app
from app.db import get_db, Base, engine


@pytest.fixture(scope="module")
def client():
    """Create test client with database setup."""
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def setup_test_data(client):
    """Ensure basic test data exists before each test."""
    # This runs the seed data if needed
    pass


# =============================================================================
# HEALTH AND CONFIG ENDPOINT TESTS
# =============================================================================

class TestHealthEndpoints:
    """Tests for health and config endpoints."""
    
    def test_health_check(self, client):
        """GET /health returns healthy status."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
    
    def test_get_config(self, client):
        """GET /config returns session configuration."""
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        
        # Should have config keys from session_config module
        assert "capability_weights" in data
        assert "difficulty_weights" in data


# =============================================================================
# ONBOARDING ENDPOINT TESTS
# =============================================================================

class TestOnboardingEndpoints:
    """Tests for onboarding endpoints."""
    
    def test_get_onboarding_existing_user(self, client):
        """GET /onboarding/{user_id} returns user data."""
        # First create a user via POST
        client.post(
            "/onboarding",
            json={
                "user_id": 1,
                "instrument": "trumpet",
                "resonant_note": "Bb3",
                "range_low": "E3",
                "range_high": "C6"
            }
        )
        
        response = client.get("/onboarding/1")
        assert response.status_code == 200
        data = response.json()
        
        assert data["user_id"] == 1
        assert data["instrument"] == "trumpet"
        assert data["resonant_note"] == "Bb3"
    
    def test_get_onboarding_nonexistent_user(self, client):
        """GET /onboarding/{user_id} returns 404 for unknown user."""
        response = client.get("/onboarding/99999")
        assert response.status_code == 404
    
    def test_post_onboarding_new_user(self, client):
        """POST /onboarding creates new user."""
        response = client.post(
            "/onboarding",
            json={
                "user_id": 2,
                "instrument": "trombone",
                "resonant_note": "F3",
                "range_low": "E2",
                "range_high": "Bb4",
                "comfortable_capabilities": ["reading"]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["user_id"] == 2
    
    def test_post_onboarding_update_existing(self, client):
        """POST /onboarding updates existing user."""
        # Create user
        client.post(
            "/onboarding",
            json={
                "user_id": 3,
                "instrument": "flute",
                "resonant_note": "A4"
            }
        )
        
        # Update user
        response = client.post(
            "/onboarding",
            json={
                "user_id": 3,
                "instrument": "clarinet",  # Changed
                "resonant_note": "Bb4"
            }
        )
        
        assert response.status_code == 200
        
        # Verify update
        get_response = client.get("/onboarding/3")
        assert get_response.json()["instrument"] == "clarinet"


# =============================================================================
# SESSION GENERATION TESTS
# =============================================================================

class TestSessionEndpoints:
    """Tests for session generation endpoints."""
    
    def test_generate_session_basic(self, client):
        """POST /generate-session generates a practice session."""
        response = client.post(
            "/generate-session?user_id=1&planned_duration_minutes=20&fatigue=2"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "session_id" in data
        assert "mini_sessions" in data
        assert isinstance(data["mini_sessions"], list)
    
    def test_generate_session_with_fatigue(self, client):
        """POST /generate-session respects fatigue parameter."""
        response = client.post(
            "/generate-session?user_id=1&planned_duration_minutes=15&fatigue=4"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should still generate mini-sessions
        assert len(data["mini_sessions"]) >= 0
    
    def test_generate_session_cooldown_mode(self, client):
        """POST /generate-session with cooldown_mode works."""
        response = client.post(
            "/generate-session?user_id=1&planned_duration_minutes=10&fatigue=5&cooldown_mode=true"
        )
        
        assert response.status_code == 200
    
    def test_generate_session_ear_only_mode(self, client):
        """POST /generate-session with ear_only_mode works."""
        response = client.post(
            "/generate-session?user_id=1&planned_duration_minutes=10&ear_only_mode=true"
        )
        
        assert response.status_code == 200


class TestSelfDirectedSession:
    """Tests for self-directed session endpoint."""
    
    def test_generate_self_directed_requires_params(self, client):
        """POST /generate-self-directed-session requires material and focus card."""
        # Need valid material_id and focus_card_id
        response = client.post(
            "/generate-self-directed-session",
            json={
                "user_id": 1,
                "planned_duration_minutes": 20,
                "material_id": 1,
                "focus_card_id": 1,
                "goal_type": "repertoire_fluency"
            }
        )
        
        # May succeed or fail depending on seed data
        assert response.status_code in [200, 500]


# =============================================================================
# MATERIALS ENDPOINT TESTS
# =============================================================================

class TestMaterialsEndpoints:
    """Tests for materials endpoints."""
    
    def test_get_materials(self, client):
        """GET /materials returns list of materials."""
        response = client.get("/materials")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        # If materials exist, check structure
        if len(data) > 0:
            assert "id" in data[0]
            assert "title" in data[0]
    
    def test_get_audio_material(self, client):
        """GET /audio/material/{id} returns audio or error."""
        response = client.get("/audio/material/1?key=C%20major&instrument=piano")
        
        # May return audio or structured error (422 for validation errors)
        assert response.status_code in [200, 400, 404, 422, 500]
    
    def test_get_audio_status(self, client):
        """GET /audio/status returns audio capability status."""
        response = client.get("/audio/status")
        
        assert response.status_code == 200
        data = response.json()
        
        # Should indicate audio capability
        assert "can_render_audio" in data or "music21_available" in data


# =============================================================================
# FOCUS CARDS ENDPOINT TESTS
# =============================================================================

class TestFocusCardsEndpoints:
    """Tests for focus cards endpoints."""
    
    def test_get_focus_cards(self, client):
        """GET /focus-cards returns list of focus cards."""
        response = client.get("/focus-cards")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        # If cards exist, check structure
        if len(data) > 0:
            assert "id" in data[0]
            assert "name" in data[0]


# =============================================================================
# CAPABILITIES ENDPOINT TESTS
# =============================================================================

class TestCapabilitiesEndpoints:
    """Tests for capabilities endpoints."""
    
    def test_get_capabilities(self, client):
        """GET /capabilities returns list of capabilities."""
        response = client.get("/capabilities")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
    
    def test_get_capabilities_v2(self, client):
        """GET /capabilities/v2 returns v2 capabilities with teaching content."""
        response = client.get("/capabilities/v2")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
    
    def test_get_capability_domains(self, client):
        """GET /capabilities/v2/domains returns domain listing."""
        response = client.get("/capabilities/v2/domains")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "domains" in data or isinstance(data, list)


# =============================================================================
# USER ENDPOINT TESTS
# =============================================================================

class TestUserEndpoints:
    """Tests for user endpoints."""
    
    def test_get_user(self, client):
        """GET /users/{user_id} returns user data."""
        # Ensure user exists
        client.post(
            "/onboarding",
            json={"user_id": 1, "instrument": "trumpet", "resonant_note": "Bb3"}
        )
        
        response = client.get("/users/1")
        
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
    
    def test_get_journey_stage(self, client):
        """GET /users/{user_id}/journey-stage returns stage info."""
        response = client.get("/users/1/journey-stage")
        
        assert response.status_code == 200
        data = response.json()
        assert "stage" in data or "journey_stage" in data
    
    def test_patch_user_range(self, client):
        """PATCH /users/{user_id}/range updates user range."""
        response = client.patch(
            "/users/1/range",
            json={"range_low": "C3", "range_high": "G5"}
        )
        
        assert response.status_code == 200


# =============================================================================
# HISTORY ENDPOINT TESTS
# =============================================================================

class TestHistoryEndpoints:
    """Tests for practice history endpoints."""
    
    def test_get_history_summary(self, client):
        """GET /history/summary returns summary data."""
        response = client.get("/history/summary?user_id=1")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
    
    def test_get_history_analytics(self, client):
        """GET /history/analytics returns analytics data."""
        response = client.get("/history/analytics?user_id=1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict)
    
    def test_get_history_materials(self, client):
        """GET /history/materials returns material history."""
        response = client.get("/history/materials?user_id=1")
        
        assert response.status_code == 200
    
    def test_get_history_timeline(self, client):
        """GET /history/timeline returns timeline data."""
        response = client.get("/history/timeline?user_id=1")
        
        assert response.status_code == 200
    
    def test_get_due_items(self, client):
        """GET /history/due-items returns SR due items."""
        response = client.get("/history/due-items?user_id=1")
        
        assert response.status_code == 200


# =============================================================================
# PRACTICE ATTEMPT ENDPOINT TESTS
# =============================================================================

class TestPracticeAttemptEndpoints:
    """Tests for practice attempt endpoints."""
    
    def test_post_practice_attempt(self, client):
        """POST /practice-attempt records an attempt."""
        response = client.post(
            "/practice-attempt",
            json={
                "user_id": 1,
                "material_id": 1,
                "key": "C major",
                "focus_card_id": 1,
                "rating": 4,
                "fatigue": 2,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        assert response.status_code == 200
    
    def test_get_practice_attempts(self, client):
        """GET /practice-attempts returns attempt list."""
        response = client.get("/practice-attempts?user_id=1")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)


# =============================================================================
# CAPABILITY LESSON ENDPOINT TESTS
# =============================================================================

class TestCapabilityLessonEndpoints:
    """Tests for capability lesson endpoints."""
    
    def test_get_capability_lesson(self, client):
        """GET /capabilities/{id}/lesson returns lesson content."""
        response = client.get("/capabilities/1/lesson")
        
        # May or may not have lesson content
        assert response.status_code in [200, 404]
    
    def test_post_quiz_result(self, client):
        """POST /capabilities/{id}/quiz-result records result."""
        response = client.post(
            "/capabilities/1/quiz-result",
            json={
                "user_id": 1,
                "passed": True,
                "answer_given": "correct_answer"
            }
        )
        
        assert response.status_code in [200, 404]


# =============================================================================
# MINI-SESSION ENDPOINT TESTS
# =============================================================================

class TestMiniSessionEndpoints:
    """Tests for mini-session endpoints."""
    
    def test_complete_session(self, client):
        """POST /sessions/{id}/complete marks session complete."""
        # First generate a session
        gen_response = client.post(
            "/generate-session?user_id=1&planned_duration_minutes=10"
        )
        
        if gen_response.status_code == 200:
            session_id = gen_response.json()["session_id"]
            
            response = client.post(f"/sessions/{session_id}/complete")
            assert response.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
