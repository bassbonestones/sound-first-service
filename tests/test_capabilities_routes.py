"""
Tests for capabilities and focus cards endpoints.

Tests capability listing, focus cards, and help menu functionality.
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


class TestFocusCardsEndpoint:
    """Tests for GET /focus-cards endpoint."""
    
    def test_returns_200(self, client):
        """Should return 200 status code."""
        response = client.get("/focus-cards")
        
        assert response.status_code == 200
    
    def test_returns_list(self, client):
        """Should return a list of focus cards."""
        response = client.get("/focus-cards")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_includes_required_fields(self, client):
        """Should include all required fields."""
        response = client.get("/focus-cards")
        
        assert response.status_code == 200
        data = response.json()
        for card in data:
            assert "id" in card
            assert "name" in card


class TestCapabilitiesEndpoint:
    """Tests for GET /capabilities endpoint (legacy)."""
    
    def test_returns_200(self, client):
        """Should return 200 status code."""
        response = client.get("/capabilities")
        
        assert response.status_code == 200
    
    def test_returns_list(self, client):
        """Should return a list of capabilities."""
        response = client.get("/capabilities")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_includes_basic_fields(self, client):
        """Should include id, name, and domain."""
        response = client.get("/capabilities")
        
        assert response.status_code == 200
        data = response.json()
        for cap in data:
            assert "id" in cap
            assert "name" in cap
            assert "domain" in cap


class TestCapabilitiesV2Endpoint:
    """Tests for GET /capabilities/v2 endpoint."""
    
    def test_returns_200(self, client):
        """Should return 200 status code."""
        response = client.get("/capabilities/v2")
        
        assert response.status_code == 200
    
    def test_returns_list(self, client):
        """Should return a list of capabilities."""
        response = client.get("/capabilities/v2")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_filters_by_domain(self, client):
        """Should filter capabilities by domain."""
        response = client.get("/capabilities/v2?domain=rhythm")
        
        assert response.status_code == 200
        data = response.json()
        for cap in data:
            assert cap["domain"] == "rhythm"


class TestDeprecatedEndpoints:
    """Tests for deprecated capability endpoints."""
    
    def test_lesson_endpoint_returns_410(self, client):
        """GET /capabilities/{id}/lesson should return 410 Gone."""
        response = client.get("/capabilities/1/lesson")
        
        assert response.status_code == 410
    
    def test_quiz_result_endpoint_returns_410(self, client):
        """POST /capabilities/{id}/quiz-result should return 410 Gone."""
        response = client.post(
            "/capabilities/1/quiz-result",
            json={"user_id": 1, "passed": True}
        )
        
        assert response.status_code == 410


class TestMaterialHelpCapabilities:
    """Tests for GET /materials/{id}/help-capabilities endpoint."""
    
    def test_returns_404_for_nonexistent_material(self, client):
        """Should return 404 for non-existent material."""
        response = client.get("/materials/9999/help-capabilities")
        
        assert response.status_code == 404
    
    def test_returns_200_for_valid_material(self, client):
        """Should return 200 for valid material."""
        # First get a valid material ID
        materials_response = client.get("/materials")
        if materials_response.status_code == 200:
            materials = materials_response.json()
            if materials and len(materials) > 0:
                material_id = materials[0]["id"]
                response = client.get(f"/materials/{material_id}/help-capabilities")
                assert response.status_code == 200
