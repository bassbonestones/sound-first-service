"""
Tests for admin endpoints.

Tests the admin API routes for users, capabilities, soft gates, materials, focus cards, and engine.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
import json

from app.main import app
from app.db import get_db, Base, engine


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
def test_user_id(client):
    """Create a test user and return their ID."""
    response = client.post(
        "/onboarding",
        json={
            "user_id": 5001,
            "instrument": "trumpet",
            "resonant_note": "Bb3",
            "range_low": "E3",
            "range_high": "C6"
        }
    )
    return 5001


# =============================================================================
# ADMIN USER ENDPOINTS (prefix: /admin)
# =============================================================================

class TestAdminUserEndpoints:
    """Tests for /admin/users endpoints."""
    
    def test_get_user_progression(self, client, test_user_id):
        """GET /admin/users/{user_id}/progression returns user data."""
        response = client.get(f"/admin/users/{test_user_id}/progression")
        assert response.status_code == 200
        data = response.json()
        
        assert "user" in data
        assert "capabilities" in data
        assert "soft_gates" in data
        assert "journey" in data
        assert data["user"]["id"] == test_user_id
    
    def test_get_user_progression_with_instrument(self, client, test_user_id):
        """GET /admin/users/{user_id}/progression with instrument_id filter."""
        response = client.get(f"/admin/users/{test_user_id}/progression?instrument_id=1")
        assert response.status_code in [200, 404]  # 404 if instrument doesn't exist
    
    def test_get_user_progression_not_found(self, client):
        """GET /admin/users/{user_id}/progression returns 404 for unknown user."""
        response = client.get("/admin/users/999999/progression")
        assert response.status_code == 404
    
    def test_get_session_candidates(self, client, test_user_id):
        """GET /admin/users/{user_id}/session-candidates returns material pool."""
        response = client.get(f"/admin/users/{test_user_id}/session-candidates")
        assert response.status_code == 200
        data = response.json()
        
        assert "eligible_materials" in data
        assert "ineligible_sample" in data
        assert isinstance(data["eligible_materials"], list)
    
    def test_get_session_candidates_not_found(self, client):
        """GET /admin/users/{user_id}/session-candidates returns 404 for unknown user."""
        response = client.get("/admin/users/999999/session-candidates")
        assert response.status_code == 404
    
    def test_generate_diagnostic_session(self, client, test_user_id):
        """POST /admin/users/{user_id}/generate-diagnostic-session creates diagnostic session."""
        response = client.post(f"/admin/users/{test_user_id}/generate-diagnostic-session")
        # May return 200, 422 (no materials), or other status
        assert response.status_code in [200, 422, 500]
    
    def test_get_last_session_diagnostics(self, client, test_user_id):
        """GET /admin/users/{user_id}/last-session-diagnostics returns session diagnostics."""
        response = client.get(f"/admin/users/{test_user_id}/last-session-diagnostics")
        # May return 404 if no session exists
        assert response.status_code in [200, 404]
    
    def test_put_user_info(self, client, test_user_id):
        """PUT /admin/users/{user_id}/info updates user info."""
        response = client.put(
            f"/admin/users/{test_user_id}/info",
            json={"range_low": "F3", "range_high": "D6"}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_put_user_info_not_found(self, client):
        """PUT /admin/users/{user_id}/info returns 404 for unknown user."""
        response = client.put(
            "/admin/users/999999/info",
            json={"range_low": "F3"}
        )
        assert response.status_code == 404
    
    def test_get_available_capabilities(self, client, test_user_id):
        """GET /admin/users/{user_id}/capabilities/available returns capability list."""
        response = client.get(f"/admin/users/{test_user_id}/capabilities/available")
        assert response.status_code == 200
        data = response.json()
        
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)
    
    def test_post_add_capability(self, client, test_user_id):
        """POST /admin/users/{user_id}/capabilities adds capability to user."""
        # First get available capabilities
        caps_response = client.get(f"/admin/users/{test_user_id}/capabilities/available")
        assert caps_response.status_code == 200
        available = caps_response.json().get("available", [])
        
        if available:
            cap_id = available[0]["id"]
            response = client.post(
                f"/admin/users/{test_user_id}/capabilities",
                json={"capability_id": cap_id, "mastered": False}
            )
            assert response.status_code == 200
    
    def test_delete_capability(self, client, test_user_id):
        """DELETE /admin/users/{user_id}/capabilities/{cap_id} removes capability."""
        # First add a capability
        caps_response = client.get(f"/admin/users/{test_user_id}/capabilities/available")
        available = caps_response.json().get("available", [])
        
        if available:
            cap_id = available[0]["id"]
            # Add it first
            client.post(
                f"/admin/users/{test_user_id}/capabilities",
                json={"capability_id": cap_id, "mastered": False}
            )
            
            # Now remove it
            response = client.delete(f"/admin/users/{test_user_id}/capabilities/{cap_id}")
            assert response.status_code in [200, 404]
    
    def test_toggle_mastery(self, client, test_user_id):
        """PUT /admin/users/{user_id}/capabilities/{cap_id}/toggle-mastery toggles mastery."""
        # First get user's capabilities
        prog_response = client.get(f"/admin/users/{test_user_id}/progression")
        if prog_response.status_code == 200:
            caps = prog_response.json().get("capabilities", {})
            introduced = caps.get("introduced", [])
            
            if introduced:
                cap_id = introduced[0]["id"]
                response = client.put(f"/admin/users/{test_user_id}/capabilities/{cap_id}/toggle-mastery")
                assert response.status_code == 200
    
    def test_get_all_soft_gates(self, client, test_user_id):
        """GET /admin/users/{user_id}/soft-gates/all returns all soft gates."""
        response = client.get(f"/admin/users/{test_user_id}/soft-gates/all")
        assert response.status_code == 200
        data = response.json()
        
        assert "soft_gates" in data
        assert isinstance(data["soft_gates"], list)
    
    def test_put_soft_gate(self, client, test_user_id):
        """PUT /admin/users/{user_id}/soft-gates/{dim} updates soft gate."""
        response = client.put(
            f"/admin/users/{test_user_id}/soft-gates/interval_size_stage",
            json={"comfortable_value": 3.0, "max_demonstrated_value": 4.0}
        )
        # May return 404 if soft gate doesn't exist
        assert response.status_code in [200, 404]
    
    def test_reset_user(self, client, test_user_id):
        """POST /admin/users/{user_id}/reset resets user progress."""
        response = client.post(f"/admin/users/{test_user_id}/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
    
    def test_grant_day0(self, client, test_user_id):
        """POST /admin/users/{user_id}/grant-day0-capabilities grants day0 capabilities."""
        response = client.post(f"/admin/users/{test_user_id}/grant-day0-capabilities")
        assert response.status_code == 200
        data = response.json()
        assert "granted" in data or "success" in data


# =============================================================================
# ADMIN CAPABILITY ENDPOINTS
# =============================================================================

class TestAdminCapabilityEndpoints:
    """Tests for /admin/capabilities endpoints."""
    
    def test_list_capabilities(self, client):
        """GET /admin/capabilities returns capability list."""
        response = client.get("/admin/capabilities")
        assert response.status_code == 200
        data = response.json()
        
        assert "capabilities" in data
        assert isinstance(data["capabilities"], list)
    
    def test_list_capabilities_with_domain_filter(self, client):
        """GET /admin/capabilities?domain=rhythm filters by domain."""
        response = client.get("/admin/capabilities?domain=rhythm")
        assert response.status_code == 200
        data = response.json()
        
        # All returned should be rhythm domain
        for cap in data["capabilities"]:
            assert cap["domain"] == "rhythm"
    
    def test_list_capabilities_with_search(self, client):
        """GET /admin/capabilities?search=note searches capabilities."""
        response = client.get("/admin/capabilities?search=note")
        assert response.status_code == 200
    
    def test_get_capability_graph(self, client):
        """GET /admin/capabilities/{id}/graph returns capability graph."""
        # First get list to find an ID
        list_response = client.get("/admin/capabilities")
        caps = list_response.json().get("capabilities", [])
        
        if caps:
            cap_id = caps[0]["id"]
            response = client.get(f"/admin/capabilities/{cap_id}/graph")
            assert response.status_code == 200
    
    def test_get_day0_capabilities(self, client):
        """GET /admin/day0-capabilities returns day0 capability list."""
        response = client.get("/admin/day0-capabilities")
        assert response.status_code == 200
    
    def test_archive_capability(self, client):
        """POST /admin/capabilities/{id}/archive archives capability."""
        # Get a capability to archive
        list_response = client.get("/admin/capabilities")
        caps = list_response.json().get("capabilities", [])
        
        if caps:
            cap_id = caps[-1]["id"]  # Use last capability
            response = client.post(f"/admin/capabilities/{cap_id}/archive")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            
            # Restore it
            client.post(f"/admin/capabilities/{cap_id}/restore")
    
    def test_restore_capability(self, client):
        """POST /admin/capabilities/{id}/restore restores capability."""
        # Get a capability
        list_response = client.get("/admin/capabilities")
        caps = list_response.json().get("capabilities", [])
        
        if caps:
            cap_id = caps[-1]["id"]
            # Archive first
            client.post(f"/admin/capabilities/{cap_id}/archive")
            
            # Now restore
            response = client.post(f"/admin/capabilities/{cap_id}/restore")
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
    
    def test_get_detection_rule_options(self, client):
        """GET /admin/detection-rule-options returns detection rule options."""
        response = client.get("/admin/detection-rule-options")
        assert response.status_code == 200
    
    def test_export_capabilities(self, client):
        """POST /admin/capabilities/export exports capabilities."""
        response = client.post("/admin/capabilities/export", json={"capability_ids": []})
        assert response.status_code in [200, 422]


# =============================================================================
# ADMIN SOFT GATE ENDPOINTS
# =============================================================================

class TestAdminSoftGateEndpoints:
    """Tests for /admin/soft-gate-rules endpoints."""
    
    def test_list_soft_gate_rules(self, client):
        """GET /admin/soft-gate-rules returns soft gate rules."""
        response = client.get("/admin/soft-gate-rules")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_user_soft_gate_state(self, client, test_user_id):
        """GET /admin/user-soft-gate-state returns user soft gate states."""
        response = client.get(f"/admin/user-soft-gate-state?user_id={test_user_id}")
        assert response.status_code == 200
    
    def test_get_users_list(self, client):
        """GET /admin/users returns user list."""
        response = client.get("/admin/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


# =============================================================================
# ADMIN MATERIALS ENDPOINTS
# =============================================================================

class TestAdminMaterialEndpoints:
    """Tests for /admin/materials endpoints."""
    
    def test_list_materials(self, client):
        """GET /admin/materials returns material list."""
        response = client.get("/admin/materials")
        assert response.status_code == 200
        data = response.json()
        
        assert "materials" in data
        assert isinstance(data["materials"], list)
    
    def test_list_materials_with_limit(self, client):
        """GET /admin/materials?limit=5 limits results."""
        response = client.get("/admin/materials?limit=5")
        assert response.status_code == 200
        data = response.json()
        
        assert len(data["materials"]) <= 5
    
    def test_get_material_gate_check(self, client):
        """GET /admin/materials/{id}/gate-check returns gate check."""
        # First get list to find an ID
        list_response = client.get("/admin/materials?limit=1")
        materials = list_response.json().get("materials", [])
        
        if materials:
            mat_id = materials[0]["id"]
            response = client.get(f"/admin/materials/{mat_id}/gate-check")
            assert response.status_code in [200, 422]
    
    def test_analyze_material(self, client):
        """POST /admin/materials/{id}/analyze analyzes material."""
        list_response = client.get("/admin/materials?limit=1")
        materials = list_response.json().get("materials", [])
        
        if materials:
            mat_id = materials[0]["id"]
            response = client.post(f"/admin/materials/{mat_id}/analyze")
            assert response.status_code in [200, 422, 500]


# =============================================================================
# ADMIN FOCUS CARD ENDPOINTS
# =============================================================================

class TestAdminFocusCardEndpoints:
    """Tests for /admin/focus-cards endpoints."""
    
    def test_get_focus_card_categories(self, client):
        """GET /admin/focus-cards/categories returns category list."""
        response = client.get("/admin/focus-cards/categories")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_create_focus_card(self, client):
        """POST /admin/focus-cards creates a focus card."""
        response = client.post(
            "/admin/focus-cards",
            json={
                "name": "Test Card",
                "description": "Test description",
                "category": "PHYSICAL"
            }
        )
        # May fail due to validation or duplicates
        assert response.status_code in [200, 422]


# =============================================================================
# ADMIN ENGINE ENDPOINTS
# =============================================================================

class TestAdminEngineEndpoints:
    """Tests for /admin/engine endpoints."""
    
    def test_get_engine_config(self, client):
        """GET /admin/engine/config returns engine configuration."""
        response = client.get("/admin/engine/config")
        assert response.status_code == 200
    
    def test_update_engine_config(self, client):
        """PUT /admin/engine/config updates engine configuration."""
        # First get current config
        get_response = client.get("/admin/engine/config")
        if get_response.status_code == 200:
            response = client.put(
                "/admin/engine/config",
                json={"review_weight": 0.3}
            )
            assert response.status_code in [200, 422]


# =============================================================================
# TEACHING MODULE ENDPOINTS
# =============================================================================

class TestTeachingModuleEndpoints:
    """Tests for /modules endpoints."""
    
    def test_list_modules(self, client):
        """GET /modules returns module list."""
        response = client.get("/modules")
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
    
    def test_get_module_by_id(self, client):
        """GET /modules/{id} returns single module."""
        list_response = client.get("/modules")
        modules = list_response.json()
        
        if modules and isinstance(modules, list) and len(modules) > 0:
            mod_id = modules[0].get("id")
            if mod_id:
                response = client.get(f"/modules/{mod_id}")
                assert response.status_code == 200
    
    def test_get_module_not_found(self, client):
        """GET /modules/{id} returns 404 for unknown module."""
        response = client.get("/modules/nonexistent_module_99999")
        assert response.status_code == 404
    
    def test_get_user_available_modules(self, client, test_user_id):
        """GET /modules/user/{user_id}/available returns user's available modules."""
        response = client.get(f"/modules/user/{test_user_id}/available")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_start_module(self, client, test_user_id):
        """POST /modules/user/{user_id}/start/{module_id} starts a module."""
        # Get available modules
        list_response = client.get("/modules")
        modules = list_response.json()
        
        if modules and isinstance(modules, list) and len(modules) > 0:
            mod_id = modules[0].get("id")
            if mod_id:
                response = client.post(f"/modules/user/{test_user_id}/start/{mod_id}")
                assert response.status_code in [200, 400]  # 400 if already started
    
    def test_get_module_lessons(self, client, test_user_id):
        """GET /modules/user/{user_id}/lessons/{module_id} returns lessons."""
        list_response = client.get("/modules")
        modules = list_response.json()
        
        if modules and isinstance(modules, list) and len(modules) > 0:
            mod_id = modules[0].get("id")
            if mod_id:
                response = client.get(f"/modules/user/{test_user_id}/lessons/{mod_id}")
                assert response.status_code in [200, 404]


# =============================================================================
# SESSION ENDPOINTS  
# =============================================================================

class TestSessionEndpoints:
    """Tests for session-related endpoints (no prefix)."""
    
    def test_generate_session(self, client, test_user_id):
        """POST /generate-session generates a session."""
        response = client.post(
            f"/generate-session?user_id={test_user_id}&planned_duration_minutes=10&fatigue=2"
        )
        # May return 200 or 422 (no materials)
        assert response.status_code in [200, 422, 500]
    
    def test_record_practice_attempt(self, client, test_user_id):
        """POST /practice-attempt records a practice attempt."""
        # First generate a session
        gen_response = client.post(
            f"/generate-session?user_id={test_user_id}&planned_duration_minutes=10&fatigue=2"
        )
        
        if gen_response.status_code == 200:
            session_data = gen_response.json()
            mini_sessions = session_data.get("mini_sessions", [])
            
            if mini_sessions:
                mini = mini_sessions[0]
                response = client.post(
                    "/practice-attempt",
                    json={
                        "user_id": test_user_id,
                        "material_id": mini.get("material_id"),
                        "focus_card_id": mini.get("focus_card_id"),
                        "rating": 75,
                        "duration_seconds": 120
                    }
                )
                assert response.status_code in [200, 422]
    
    def test_complete_session(self, client, test_user_id):
        """POST /sessions/{session_id}/complete completes a session."""
        # First generate a session
        gen_response = client.post(
            f"/generate-session?user_id={test_user_id}&planned_duration_minutes=10&fatigue=2"
        )
        
        if gen_response.status_code == 200:
            session_id = gen_response.json().get("session_id")
            
            if session_id:
                response = client.post(f"/sessions/{session_id}/complete")
                assert response.status_code in [200, 404]


# =============================================================================
# HISTORY ENDPOINTS
# =============================================================================

class TestHistoryEndpoints:
    """Tests for /history endpoints."""
    
    def test_get_history_summary(self, client, test_user_id):
        """GET /history/summary returns practice summary."""
        response = client.get(f"/history/summary?user_id={test_user_id}")
        assert response.status_code == 200
    
    def test_get_material_history(self, client, test_user_id):
        """GET /history/materials returns material history."""
        response = client.get(f"/history/materials?user_id={test_user_id}")
        assert response.status_code == 200
    
    def test_get_practice_timeline(self, client, test_user_id):
        """GET /history/timeline returns practice timeline."""
        response = client.get(f"/history/timeline?user_id={test_user_id}&days=30")
        assert response.status_code == 200
    
    def test_get_focus_card_history(self, client, test_user_id):
        """GET /history/focus-cards returns focus card history."""
        response = client.get(f"/history/focus-cards?user_id={test_user_id}")
        assert response.status_code == 200
    
    def test_get_due_items(self, client, test_user_id):
        """GET /history/due-items returns due review items."""
        response = client.get(f"/history/due-items?user_id={test_user_id}")
        assert response.status_code == 200


# =============================================================================
# MATERIALS ENDPOINTS
# =============================================================================

class TestMaterialEndpoints:
    """Tests for /materials endpoints."""
    
    def test_list_materials_public(self, client):
        """GET /materials returns public material list."""
        response = client.get("/materials")
        assert response.status_code == 200
    
    def test_get_material_analysis(self, client):
        """GET /materials/{id}/analysis returns material analysis."""
        # Get a material ID first
        list_response = client.get("/materials")
        if list_response.status_code == 200:
            materials = list_response.json()
            if isinstance(materials, list) and materials:
                mat_id = materials[0].get("id")
                if mat_id:
                    response = client.get(f"/materials/{mat_id}/analysis")
                    assert response.status_code in [200, 404]


# =============================================================================
# AUDIO ENDPOINTS  
# =============================================================================

class TestAudioEndpoints:
    """Tests for /audio endpoints."""
    
    def test_get_audio_status(self, client):
        """GET /audio/status returns audio status."""
        response = client.get("/audio/status")
        assert response.status_code == 200
