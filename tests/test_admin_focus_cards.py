"""
Tests for /admin/focus-cards/* endpoints.

Tests admin CRUD operations for focus cards including
categories, creation, updates, and deletion.
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


class TestFocusCardCategories:
    """Tests for GET /admin/focus-cards/categories endpoint."""
    
    def test_returns_200(self, client):
        """Should return 200 status code."""
        response = client.get("/admin/focus-cards/categories")
        
        assert response.status_code == 200
    
    def test_returns_list(self, client):
        """Should return a list of categories."""
        response = client.get("/admin/focus-cards/categories")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_categories_are_strings(self, client):
        """Should return list of string categories."""
        response = client.get("/admin/focus-cards/categories")
        
        data = response.json()
        if len(data) > 0:
            assert all(isinstance(cat, str) for cat in data)


class TestCreateFocusCard:
    """Tests for POST /admin/focus-cards endpoint."""
    
    def test_returns_200_for_valid_data(self, client):
        """Should return 200 for valid focus card data."""
        data = {
            "name": "Test Focus Card Create",
            "category": "test_category",
            "description": "A test focus card",
            "attention_cue": "Focus on this",
            "micro_cues": ["cue1", "cue2"],
            "prompts": {"key": "value"},
        }
        
        response = client.post("/admin/focus-cards", json=data)
        
        assert response.status_code == 200
    
    def test_returns_created_card_with_id(self, client):
        """Should return created card with ID."""
        data = {
            "name": "Test Focus Card With ID",
            "category": "test_category",
            "description": "Another test card",
        }
        
        response = client.post("/admin/focus-cards", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert "id" in result
        assert result["id"] > 0
    
    def test_returns_400_for_duplicate_name(self, client):
        """Should return 400 for duplicate focus card name."""
        data = {
            "name": "Duplicate Test Card",
            "category": "test",
        }
        
        # Create first
        client.post("/admin/focus-cards", json=data)
        
        # Try to create duplicate
        response = client.post("/admin/focus-cards", json=data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestUpdateFocusCard:
    """Tests for PUT /admin/focus-cards/{id} endpoint."""
    
    def test_returns_404_for_nonexistent_card(self, client):
        """Should return 404 for non-existent focus card."""
        data = {"name": "Updated Name"}
        
        response = client.put("/admin/focus-cards/999999", json=data)
        
        assert response.status_code == 404
    
    def test_updates_category(self, client):
        """Should update focus card category."""
        # Create a card first
        create_data = {
            "name": "Card To Update Category",
            "category": "original_category",
        }
        create_response = client.post("/admin/focus-cards", json=create_data)
        card_id = create_response.json()["id"]
        
        # Update it
        update_data = {"category": "updated_category"}
        response = client.put(f"/admin/focus-cards/{card_id}", json=update_data)
        
        assert response.status_code == 200
        assert response.json()["category"] == "updated_category"
    
    def test_updates_description(self, client):
        """Should update focus card description."""
        # Create a card first
        create_data = {
            "name": "Card To Update Desc",
            "description": "Original description",
        }
        create_response = client.post("/admin/focus-cards", json=create_data)
        card_id = create_response.json()["id"]
        
        # Update it
        update_data = {"description": "Updated description"}
        response = client.put(f"/admin/focus-cards/{card_id}", json=update_data)
        
        assert response.status_code == 200
        assert response.json()["description"] == "Updated description"


class TestDeleteFocusCard:
    """Tests for DELETE /admin/focus-cards/{id} endpoint."""
    
    def test_returns_404_for_nonexistent_card(self, client):
        """Should return 404 for non-existent focus card."""
        response = client.delete("/admin/focus-cards/999999")
        
        assert response.status_code == 404
    
    def test_deletes_unreferenced_card(self, client):
        """Should delete focus card that is not referenced."""
        # Create a card
        create_data = {
            "name": "Card To Delete",
            "category": "deletable",
        }
        create_response = client.post("/admin/focus-cards", json=create_data)
        card_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(f"/admin/focus-cards/{card_id}")
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"]
