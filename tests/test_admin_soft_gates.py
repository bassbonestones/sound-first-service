"""
Tests for /admin/soft-gate-rules and /admin/user-soft-gate-state endpoints.

Tests admin CRUD operations for soft gate rules and
user soft gate state management.
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


class TestGetSoftGateRules:
    """Tests for GET /admin/soft-gate-rules endpoint."""
    
    def test_returns_200(self, client):
        """Should return 200 status code."""
        response = client.get("/admin/soft-gate-rules")
        
        assert response.status_code == 200
    
    def test_returns_list(self, client):
        """Should return a list of rules."""
        response = client.get("/admin/soft-gate-rules")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_rules_have_required_fields(self, client):
        """Should return rules with required fields."""
        response = client.get("/admin/soft-gate-rules")
        
        data = response.json()
        if len(data) > 0:
            rule = data[0]
            assert "id" in rule
            assert "dimension_name" in rule
            assert "frontier_buffer" in rule


class TestCreateSoftGateRule:
    """Tests for POST /admin/soft-gate-rules endpoint."""
    
    def test_returns_200_for_valid_data(self, client):
        """Should return 200 for valid rule data."""
        data = {
            "dimension_name": "test_dimension_create",
            "frontier_buffer": 0.5,
            "promotion_step": 0.1,
            "min_attempts": 3,
            "success_required_count": 2,
        }
        
        response = client.post("/admin/soft-gate-rules", json=data)
        
        assert response.status_code == 200
    
    def test_returns_created_rule_with_id(self, client):
        """Should return created rule with ID."""
        data = {
            "dimension_name": "test_dimension_with_id",
            "frontier_buffer": 0.5,
            "promotion_step": 0.2,
            "min_attempts": 5,
            "success_required_count": 3,
        }
        
        response = client.post("/admin/soft-gate-rules", json=data)
        
        assert response.status_code == 200
        result = response.json()
        assert "id" in result
        assert result["id"] > 0
    
    def test_returns_400_for_duplicate_dimension(self, client):
        """Should return 400 for duplicate dimension name."""
        data = {
            "dimension_name": "duplicate_dimension_test",
            "frontier_buffer": 0.5,
            "promotion_step": 0.1,
            "min_attempts": 3,
            "success_required_count": 2,
        }
        
        # Create first
        client.post("/admin/soft-gate-rules", json=data)
        
        # Try to create duplicate
        response = client.post("/admin/soft-gate-rules", json=data)
        
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]


class TestUpdateSoftGateRule:
    """Tests for PUT /admin/soft-gate-rules/{id} endpoint."""
    
    def test_returns_404_for_nonexistent_rule(self, client):
        """Should return 404 for non-existent rule."""
        data = {"frontier_buffer": 1.0}
        
        response = client.put("/admin/soft-gate-rules/999999", json=data)
        
        assert response.status_code == 404
    
    def test_updates_frontier_buffer(self, client):
        """Should update frontier buffer."""
        # Create a rule first
        create_data = {
            "dimension_name": "rule_to_update_buffer",
            "frontier_buffer": 0.5,
            "promotion_step": 0.1,
            "min_attempts": 3,
            "success_required_count": 2,
        }
        create_response = client.post("/admin/soft-gate-rules", json=create_data)
        rule_id = create_response.json()["id"]
        
        # Update it
        update_data = {"frontier_buffer": 0.8}
        response = client.put(f"/admin/soft-gate-rules/{rule_id}", json=update_data)
        
        assert response.status_code == 200
        assert response.json()["frontier_buffer"] == 0.8


class TestDeleteSoftGateRule:
    """Tests for DELETE /admin/soft-gate-rules/{id} endpoint."""
    
    def test_returns_404_for_nonexistent_rule(self, client):
        """Should return 404 for non-existent rule."""
        response = client.delete("/admin/soft-gate-rules/999999")
        
        assert response.status_code == 404
    
    def test_deletes_rule(self, client):
        """Should delete soft gate rule."""
        # Create a rule
        create_data = {
            "dimension_name": "rule_to_delete",
            "frontier_buffer": 0.5,
            "promotion_step": 0.1,
            "min_attempts": 3,
            "success_required_count": 2,
        }
        create_response = client.post("/admin/soft-gate-rules", json=create_data)
        rule_id = create_response.json()["id"]
        
        # Delete it
        response = client.delete(f"/admin/soft-gate-rules/{rule_id}")
        
        assert response.status_code == 200
        assert "deleted" in response.json()["message"]


class TestGetAdminUsers:
    """Tests for GET /admin/users endpoint."""
    
    def test_returns_200(self, client):
        """Should return 200 status code."""
        response = client.get("/admin/users")
        
        assert response.status_code == 200
    
    def test_returns_list(self, client):
        """Should return a list of users."""
        response = client.get("/admin/users")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_users_have_required_fields(self, client):
        """Should return users with required fields."""
        response = client.get("/admin/users")
        
        data = response.json()
        if len(data) > 0:
            user = data[0]
            assert "id" in user
            assert "email" in user


class TestGetUserSoftGateState:
    """Tests for GET /admin/user-soft-gate-state endpoint."""
    
    def test_returns_200_for_existing_user(self, client, test_user_id):
        """Should return 200 for existing user."""
        response = client.get(f"/admin/user-soft-gate-state?user_id={test_user_id}")
        
        assert response.status_code == 200
    
    def test_returns_404_for_nonexistent_user(self, client):
        """Should return 404 for non-existent user."""
        response = client.get("/admin/user-soft-gate-state?user_id=999999")
        
        assert response.status_code == 404
    
    def test_returns_list(self, client, test_user_id):
        """Should return a list of states."""
        response = client.get(f"/admin/user-soft-gate-state?user_id={test_user_id}")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)
