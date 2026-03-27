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


class TestCalculateTrend:
    """Tests for _calculate_trend helper function."""
    
    def test_stable_when_fewer_than_3_values(self):
        """Returns 'stable' when fewer than 3 values."""
        from app.routes.history import _calculate_trend
        
        assert _calculate_trend([]) == "stable"
        assert _calculate_trend([1]) == "stable"
        assert _calculate_trend([1, 2]) == "stable"
    
    def test_improving_when_last_greater_than_third_last(self):
        """Returns 'improving' when last value > third-to-last."""
        from app.routes.history import _calculate_trend
        
        assert _calculate_trend([3, 4, 5]) == "improving"
        assert _calculate_trend([1, 2, 3, 4, 5]) == "improving"
    
    def test_declining_when_last_less_than_third_last(self):
        """Returns 'declining' when last value < third-to-last."""
        from app.routes.history import _calculate_trend
        
        assert _calculate_trend([5, 4, 3]) == "declining"
        assert _calculate_trend([5, 4, 3, 2, 1]) == "declining"
    
    def test_stable_when_last_equals_third_last(self):
        """Returns 'stable' when last value = third-to-last."""
        from app.routes.history import _calculate_trend
        
        assert _calculate_trend([4, 5, 4]) == "stable"
        assert _calculate_trend([5, 1, 5]) == "stable"
