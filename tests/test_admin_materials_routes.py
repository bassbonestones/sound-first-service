"""
Tests for app/routes/admin/materials.py
Tests admin material management endpoints.
"""

import pytest
from unittest.mock import MagicMock
from datetime import datetime
from fastapi import HTTPException


class TestAdminGetMaterials:
    """Tests for admin_get_materials endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_returns_all_materials(self, mock_db):
        """admin_get_materials returns list of all materials."""
        from app.routes.admin.materials import admin_get_materials
        
        mock_material = MagicMock()
        mock_material.id = 1
        mock_material.title = "Test Song"
        
        mock_db.query.return_value.all.return_value = [mock_material]
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        mock_db.query.return_value.join.return_value.filter.return_value.all.return_value = []
        
        result = admin_get_materials(db=mock_db)
        
        assert "materials" in result
        assert "count" in result


class TestAdminCheckMaterialGates:
    """Tests for admin_check_material_gates endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_returns_404_when_material_not_found(self, mock_db):
        """admin_check_material_gates returns 404 when material doesn't exist."""
        from app.routes.admin.materials import admin_check_material_gates
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            admin_check_material_gates(material_id=999, user_id=1, db=mock_db)
        assert exc_info.value.status_code == 404
    
    def test_returns_404_when_user_not_found(self, mock_db):
        """admin_check_material_gates returns 404 when user doesn't exist."""
        from app.routes.admin.materials import admin_check_material_gates
        
        mock_material = MagicMock()
        
        call_count = [0]
        def query_side_effect(*models):
            mock_query = MagicMock()
            call_count[0] += 1
            
            if call_count[0] == 1:
                mock_query.filter_by.return_value.first.return_value = mock_material
            else:
                mock_query.filter_by.return_value.first.return_value = None
            
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        with pytest.raises(HTTPException) as exc_info:
            admin_check_material_gates(material_id=1, user_id=999, db=mock_db)
        assert exc_info.value.status_code == 404


class TestAdminTriggerAnalysis:
    """Tests for admin_trigger_analysis endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_returns_404_when_material_not_found(self, mock_db):
        """admin_trigger_analysis returns 404 when material doesn't exist."""
        from app.routes.admin.materials import admin_trigger_analysis
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            admin_trigger_analysis(material_id=999, db=mock_db)
        assert exc_info.value.status_code == 404
