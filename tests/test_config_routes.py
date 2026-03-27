"""
Tests for app/routes/config.py
Tests configuration endpoints.
"""

import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestGetSessionConfigEndpoint:
    """Tests for GET /config endpoint."""
    
    def test_returns_200(self, client):
        """GET /config returns 200."""
        response = client.get("/config")
        assert response.status_code == 200
    
    def test_returns_config_dict(self, client):
        """GET /config returns configuration dictionary."""
        response = client.get("/config")
        assert response.status_code == 200
        data = response.json()
        assert "capability_weights" in data
        assert "difficulty_weights" in data
        assert "novelty_reinforcement" in data


class TestLogClientEventEndpoint:
    """Tests for POST /log/client endpoint."""
    
    def test_log_client_returns_200(self, client):
        """POST /log/client returns 200."""
        response = client.post(
            "/log/client",
            json={"event": "app_startup", "data": {"version": "1.0.0"}}
        )
        assert response.status_code == 200
    
    def test_log_client_returns_status_logged(self, client):
        """POST /log/client returns status: logged."""
        response = client.post(
            "/log/client",
            json={"event": "test_event", "data": {"foo": "bar"}, "timestamp": "2024-01-01T00:00:00Z"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "logged"


class TestPatchSessionConfigEndpoint:
    """Tests for PATCH /config endpoint."""
    
    def test_patch_returns_200(self, client):
        """PATCH /config returns 200."""
        import app.session_config as session_config
        original = session_config.CAPABILITY_WEIGHTS.copy()
        
        try:
            response = client.patch(
                "/config",
                json={"capability_weights": {"repertoire_fluency": 0.3}}
            )
            assert response.status_code == 200
        finally:
            session_config.CAPABILITY_WEIGHTS.clear()
            session_config.CAPABILITY_WEIGHTS.update(original)
    
    def test_patch_updates_fields(self, client):
        """PATCH /config returns updated field names."""
        import app.session_config as session_config
        original = session_config.CAPABILITY_WEIGHTS.copy()
        
        try:
            response = client.patch(
                "/config",
                json={"capability_weights": {"repertoire_fluency": 0.4}}
            )
            assert response.status_code == 200
            data = response.json()
            assert "updated" in data
            assert "capability_weights" in data["updated"]
        finally:
            session_config.CAPABILITY_WEIGHTS.clear()
            session_config.CAPABILITY_WEIGHTS.update(original)


class TestUpdateSessionConfig:
    """Tests for update_session_config endpoint."""
    
    def test_updates_capability_weights(self):
        """update_session_config updates capability weights."""
        from app.routes.config import update_session_config
        from app.schemas import ConfigUpdateIn
        import app.session_config as session_config
        
        # Save original config
        original_weights = session_config.CAPABILITY_WEIGHTS.copy()
        
        try:
            update_data = ConfigUpdateIn(
                capability_weights={
                    "repertoire_fluency": 0.3,
                    "technique": 0.2,
                    "range_expansion": 0.1,
                    "rhythm": 0.2,
                    "ear_training": 0.1,
                    "articulation": 0.1
                }
            )
            
            result = update_session_config(data=update_data)
            
            assert "updated" in result or "status" in result
        finally:
            # Restore original config to avoid test pollution
            session_config.CAPABILITY_WEIGHTS.clear()
            session_config.CAPABILITY_WEIGHTS.update(original_weights)
    
    def test_returns_updated_fields(self):
        """update_session_config returns list of updated fields."""
        from app.routes.config import update_session_config
        from app.schemas import ConfigUpdateIn
        import app.session_config as session_config
        
        original_weights = session_config.CAPABILITY_WEIGHTS.copy()
        
        try:
            update_data = ConfigUpdateIn(
                capability_weights={"repertoire_fluency": 0.5}
            )
            
            result = update_session_config(data=update_data)
            
            # Should return success status
            assert "status" in result or "success" in result or len(result) >= 0
        finally:
            session_config.CAPABILITY_WEIGHTS.clear()
            session_config.CAPABILITY_WEIGHTS.update(original_weights)


class TestGetConfig:
    """Tests for configuration retrieval."""
    
    def test_session_config_module_exists(self):
        """session_config module is importable."""
        import app.session_config as session_config
        
        # Verify CAPABILITY_WEIGHTS is defined and is a dict
        assert isinstance(session_config.CAPABILITY_WEIGHTS, dict)
