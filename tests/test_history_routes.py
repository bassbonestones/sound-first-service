"""
Tests for /history/* endpoints.

Tests practice history, spaced repetition, and analytics functionality.
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


class TestHistorySummary:
    """Tests for GET /history/summary endpoint."""
    
    def test_returns_200_for_valid_user(self, client, test_user_id):
        """Should return 200 with summary data for valid user."""
        response = client.get(f"/history/summary?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
        assert "total_attempts" in data
        assert "current_streak_days" in data
        assert "average_rating" in data
    
    def test_includes_spaced_repetition_stats(self, client, test_user_id):
        """Should include spaced repetition statistics."""
        response = client.get(f"/history/summary?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "spaced_repetition" in data


class TestMaterialHistory:
    """Tests for GET /history/materials endpoint."""
    
    def test_returns_200_for_valid_user(self, client, test_user_id):
        """Should return 200 with material history."""
        response = client.get(f"/history/materials?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_includes_material_details(self, client, test_user_id):
        """Should include material title and ID."""
        response = client.get(f"/history/materials?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        for item in data:
            assert "material_id" in item
            assert "material_title" in item


class TestPracticeTimeline:
    """Tests for GET /history/timeline endpoint."""
    
    def test_returns_200_for_valid_user(self, client, test_user_id):
        """Should return 200 with timeline data."""
        response = client.get(f"/history/timeline?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_accepts_days_parameter(self, client, test_user_id):
        """Should accept days parameter to limit range."""
        response = client.get(f"/history/timeline?user_id={test_user_id}&days=7")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestFocusCardHistory:
    """Tests for GET /history/focus-cards endpoint."""
    
    def test_returns_200_for_valid_user(self, client, test_user_id):
        """Should return 200 with focus card history."""
        response = client.get(f"/history/focus-cards?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestDueItems:
    """Tests for GET /history/due-items endpoint."""
    
    def test_returns_200_for_valid_user(self, client, test_user_id):
        """Should return 200 with due items."""
        response = client.get(f"/history/due-items?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_accepts_limit_parameter(self, client, test_user_id):
        """Should accept limit parameter."""
        response = client.get(f"/history/due-items?user_id={test_user_id}&limit=5")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 5


class TestSessionAnalytics:
    """Tests for GET /history/analytics endpoint."""
    
    def test_returns_200_for_valid_user(self, client, test_user_id):
        """Should return 200 with analytics data."""
        response = client.get(f"/history/analytics?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
