"""
Tests for admin engine routes.

Tests engine configuration endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestGetEngineConfig:
    """Tests for GET /admin/engine/config endpoint."""
    
    def test_returns_200(self, client):
        """GET /admin/engine/config returns 200."""
        response = client.get("/admin/engine/config")
        assert response.status_code == 200
    
    def test_returns_config_structure(self, client):
        """GET /admin/engine/config returns expected structure."""
        response = client.get("/admin/engine/config")
        assert response.status_code == 200
        data = response.json()
        assert "capability_weights" in data
        assert "difficulty_weights" in data


class TestUpdateEngineConfig:
    """Tests for PUT /admin/engine/config endpoint."""
    
    def test_update_capability_weights(self, client):
        """PUT /admin/engine/config updates capability weights."""
        import app.session_config as session_config
        original = session_config.CAPABILITY_WEIGHTS.copy()
        
        try:
            response = client.put(
                "/admin/engine/config",
                json={"capability_weights": {"repertoire_fluency": 0.25}}
            )
            assert response.status_code == 200
            data = response.json()
            assert "changes_applied" in data
        finally:
            session_config.CAPABILITY_WEIGHTS.clear()
            session_config.CAPABILITY_WEIGHTS.update(original)
    
    def test_update_difficulty_weights(self, client):
        """PUT /admin/engine/config updates difficulty weights."""
        import app.session_config as session_config
        original = session_config.DIFFICULTY_WEIGHTS.copy()
        
        try:
            response = client.put(
                "/admin/engine/config",
                json={"difficulty_weights": {"easy": 0.4}}
            )
            assert response.status_code == 200
        finally:
            session_config.DIFFICULTY_WEIGHTS.clear()
            session_config.DIFFICULTY_WEIGHTS.update(original)
    
    def test_update_novelty_reinforcement(self, client):
        """PUT /admin/engine/config updates novelty reinforcement."""
        import app.session_config as session_config
        original = session_config.NOVELTY_REINFORCEMENT.copy()
        
        try:
            response = client.put(
                "/admin/engine/config",
                json={"novelty_reinforcement": {"novelty": 0.2}}
            )
            assert response.status_code == 200
        finally:
            session_config.NOVELTY_REINFORCEMENT.clear()
            session_config.NOVELTY_REINFORCEMENT.update(original)
    
    def test_update_intensity_weights(self, client):
        """PUT /admin/engine/config updates intensity weights."""
        import app.session_config as session_config
        original = session_config.INTENSITY_WEIGHTS.copy()
        
        try:
            response = client.put(
                "/admin/engine/config",
                json={"intensity_weights": {"small": 0.35}}
            )
            assert response.status_code == 200
        finally:
            session_config.INTENSITY_WEIGHTS.clear()
            session_config.INTENSITY_WEIGHTS.update(original)
    
    def test_update_time_budgets(self, client):
        """PUT /admin/engine/config updates time budgets."""
        import app.session_config as session_config
        original = session_config.AVG_MINI_SESSION_MINUTES.copy()
        
        try:
            response = client.put(
                "/admin/engine/config",
                json={"time_budgets": {"default": 5.0}}
            )
            assert response.status_code == 200
        finally:
            session_config.AVG_MINI_SESSION_MINUTES.clear()
            session_config.AVG_MINI_SESSION_MINUTES.update(original)
    
    def test_update_multiple_configs(self, client):
        """PUT /admin/engine/config can update multiple settings."""
        import app.session_config as session_config
        orig_cap = session_config.CAPABILITY_WEIGHTS.copy()
        orig_diff = session_config.DIFFICULTY_WEIGHTS.copy()
        
        try:
            response = client.put(
                "/admin/engine/config",
                json={
                    "capability_weights": {"repertoire_fluency": 0.2},
                    "difficulty_weights": {"easy": 0.45}
                }
            )
            assert response.status_code == 200
            data = response.json()
            # Should have multiple changes
            assert len(data.get("changes_applied", [])) >= 2
        finally:
            session_config.CAPABILITY_WEIGHTS.clear()
            session_config.CAPABILITY_WEIGHTS.update(orig_cap)
            session_config.DIFFICULTY_WEIGHTS.clear()
            session_config.DIFFICULTY_WEIGHTS.update(orig_diff)
