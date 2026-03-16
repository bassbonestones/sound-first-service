"""
Tests for /admin/engine/* endpoints.

Tests admin engine configuration retrieval, updates,
and reset functionality.
"""

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db import Base, engine


@pytest.fixture(scope="module")
def client():
    """Create test client with database setup."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    
    from resources.seed_all import seed_all
    seed_all()
    
    with TestClient(app) as c:
        yield c


class TestGetEngineConfig:
    """Tests for GET /admin/engine/config endpoint."""
    
    def test_returns_200(self, client):
        """Should return 200 status code."""
        response = client.get("/admin/engine/config")
        
        assert response.status_code == 200
    
    def test_includes_capability_weights(self, client):
        """Should include capability_weights in response."""
        response = client.get("/admin/engine/config")
        
        data = response.json()
        assert "capability_weights" in data
        assert isinstance(data["capability_weights"], dict)
    
    def test_includes_difficulty_weights(self, client):
        """Should include difficulty_weights in response."""
        response = client.get("/admin/engine/config")
        
        data = response.json()
        assert "difficulty_weights" in data
        assert isinstance(data["difficulty_weights"], dict)
    
    def test_includes_time_budgets(self, client):
        """Should include time_budgets in response."""
        response = client.get("/admin/engine/config")
        
        data = response.json()
        assert "time_budgets" in data
        assert isinstance(data["time_budgets"], dict)
    
    def test_includes_anti_repetition(self, client):
        """Should include anti_repetition settings."""
        response = client.get("/admin/engine/config")
        
        data = response.json()
        assert "anti_repetition" in data
        assert "max_capability_streak" in data["anti_repetition"]
    
    def test_includes_notation_shown_percentage(self, client):
        """Should include notation_shown_percentage."""
        response = client.get("/admin/engine/config")
        
        data = response.json()
        assert "notation_shown_percentage" in data
        assert isinstance(data["notation_shown_percentage"], (int, float))


class TestUpdateEngineConfig:
    """Tests for PUT /admin/engine/config endpoint."""
    
    def test_returns_200(self, client):
        """Should return 200 for valid update."""
        data = {
            "notation_shown_percentage": 0.5
        }
        
        response = client.put("/admin/engine/config", json=data)
        
        assert response.status_code == 200
    
    def test_returns_success_status(self, client):
        """Should return success status."""
        data = {
            "wrap_up_threshold_minutes": 3.0
        }
        
        response = client.put("/admin/engine/config", json=data)
        
        result = response.json()
        assert result["success"] is True
    
    def test_returns_changes_applied(self, client):
        """Should return list of changes applied."""
        data = {
            "notation_shown_percentage": 0.75
        }
        
        response = client.put("/admin/engine/config", json=data)
        
        result = response.json()
        assert "changes_applied" in result
        assert isinstance(result["changes_applied"], list)
    
    def test_includes_note_about_persistence(self, client):
        """Should include note about in-memory changes."""
        data = {}
        
        response = client.put("/admin/engine/config", json=data)
        
        result = response.json()
        assert "note" in result


class TestResetEngineConfig:
    """Tests for POST /admin/engine/reset endpoint."""
    
    def test_returns_200(self, client):
        """Should return 200 status code."""
        response = client.post("/admin/engine/reset")
        
        assert response.status_code == 200
    
    def test_returns_success_status(self, client):
        """Should return success status."""
        response = client.post("/admin/engine/reset")
        
        result = response.json()
        assert result["success"] is True
    
    def test_returns_message(self, client):
        """Should return message about reset."""
        response = client.post("/admin/engine/reset")
        
        result = response.json()
        assert "message" in result
