"""
Tests for /onboarding/* endpoints.

Tests user onboarding flow including instrument selection,
range configuration, and initial capability setup.
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


@pytest.fixture
def test_user_id():
    """Test user ID (created by seed)."""
    return 1


class TestGetOnboarding:
    """Tests for GET /onboarding/{user_id} endpoint."""
    
    def test_returns_200_for_existing_user(self, client, test_user_id):
        """Should return 200 for existing user."""
        response = client.get(f"/onboarding/{test_user_id}")
        
        assert response.status_code == 200
    
    def test_returns_404_for_nonexistent_user(self, client):
        """Should return 404 for non-existent user."""
        response = client.get("/onboarding/999999")
        
        assert response.status_code == 404
    
    def test_includes_user_id(self, client, test_user_id):
        """Should include user ID in response."""
        response = client.get(f"/onboarding/{test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user_id
    
    def test_includes_instrument(self, client, test_user_id):
        """Should include instrument in response."""
        response = client.get(f"/onboarding/{test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "instrument" in data


class TestSaveOnboarding:
    """Tests for POST /onboarding endpoint."""
    
    def test_returns_200_for_valid_data(self, client):
        """Should return 200 for valid onboarding data."""
        data = {
            "user_id": 100,
            "instrument": "trumpet",
            "resonant_note": "C4",
            "range_low": "F#3",
            "range_high": "C6",
            "comfortable_capabilities": ["quarter_notes"],
        }
        response = client.post("/onboarding", json=data)
        
        assert response.status_code == 200
    
    def test_returns_success_status(self, client):
        """Should return success status."""
        data = {
            "user_id": 101,
            "instrument": "tuba",
            "resonant_note": "Bb1",
            "range_low": "E1",
            "range_high": "Bb3",
            "comfortable_capabilities": [],
        }
        response = client.post("/onboarding", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["status"] == "success"
    
    def test_returns_user_id(self, client):
        """Should return user ID."""
        data = {
            "user_id": 102,
            "instrument": "euphonium",
            "resonant_note": "Bb2",
            "range_low": "E2",
            "range_high": "Bb4",
            "comfortable_capabilities": [],
        }
        response = client.post("/onboarding", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert result["user_id"] == 102


class TestOnboardingValidation:
    """Tests for onboarding input validation."""
    
    def test_creates_user_without_user_id(self, client):
        """Should create new user when user_id is not provided."""
        data = {
            "instrument": "trumpet",
            "resonant_note": "C4",
            "range_low": "F#3",
            "range_high": "C6",
        }
        
        response = client.post("/onboarding", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert "user_id" in result
        assert result["user_id"] > 0
