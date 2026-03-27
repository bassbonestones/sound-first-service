"""
Tests for app/routes/admin/materials.py
Tests admin material management endpoints.
"""

import pytest
from unittest.mock import MagicMock, patch
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

    def test_returns_empty_list_when_no_materials(self, mock_db):
        """admin_get_materials returns empty list when no materials exist."""
        from app.routes.admin.materials import admin_get_materials
        
        mock_db.query.return_value.all.return_value = []
        
        result = admin_get_materials(db=mock_db)
        
        assert result["materials"] == []
        assert result["count"] == 0

    def test_includes_material_analysis(self, mock_db):
        """admin_get_materials includes analysis data when available."""
        from app.routes.admin.materials import admin_get_materials
        
        mock_material = MagicMock()
        mock_material.id = 1
        mock_material.title = "Test Song"
        mock_material.musicxml_canonical = "<score/>"
        
        mock_analysis = MagicMock()
        mock_analysis.chromatic_complexity = 0.5
        mock_analysis.tonal_complexity_stage = 2
        mock_analysis.interval_size_stage = 1
        mock_analysis.interval_sustained_stage = 1
        mock_analysis.interval_hazard_stage = 0
        mock_analysis.legacy_interval_size_stage = 1
        mock_analysis.rhythm_complexity_stage = 2
        mock_analysis.range_usage_stage = 1
        mock_analysis.difficulty_index = 3.5
        
        def query_side_effect(*models):
            mock_query = MagicMock()
            # First: Material query
            mock_query.all.return_value = [mock_material]
            # For analysis
            mock_query.filter_by.return_value.first.return_value = mock_analysis
            mock_query.join.return_value.filter.return_value.all.return_value = []
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        result = admin_get_materials(db=mock_db)
        
        assert "materials" in result
        assert len(result["materials"]) == 1


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

    def test_passes_when_user_has_required_capabilities(self, mock_db):
        """admin_check_material_gates passes when user has all required capabilities."""
        from app.routes.admin.materials import admin_check_material_gates
        
        mock_material = MagicMock()
        mock_material.id = 1
        mock_material.title = "Test Material"
        
        mock_user = MagicMock()
        mock_user.id = 1
        
        mock_user_cap = MagicMock()
        mock_user_cap.mastered_at = datetime.now()
        
        call_count = [0]
        def query_side_effect(*models):
            mock_query = MagicMock()
            call_count[0] += 1
            
            if call_count[0] == 1:  # Material
                mock_query.filter_by.return_value.first.return_value = mock_material
            elif call_count[0] == 2:  # User
                mock_query.filter_by.return_value.first.return_value = mock_user
            elif call_count[0] == 3:  # MaterialCapability join
                mock_query.join.return_value.filter.return_value.all.return_value = []
            elif call_count[0] == 4:  # UserCapability
                mock_query.filter_by.return_value.first.return_value = mock_user_cap
            elif call_count[0] == 5:  # MaterialAnalysis
                mock_query.filter_by.return_value.first.return_value = None
            else:  # SoftGateRule
                mock_query.all.return_value = []
            
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        result = admin_check_material_gates(material_id=1, user_id=1, db=mock_db)
        
        assert result["passes_hard_gates"] is True
        assert result["hard_gate_failures"] == []


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

    def test_returns_400_when_no_musicxml(self, mock_db):
        """admin_trigger_analysis returns 400 when material has no MusicXML."""
        from app.routes.admin.materials import admin_trigger_analysis
        
        mock_material = MagicMock()
        mock_material.musicxml_canonical = None
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_material
        
        with pytest.raises(HTTPException) as exc_info:
            admin_trigger_analysis(material_id=1, db=mock_db)
        assert exc_info.value.status_code == 400
        assert "no MusicXML" in str(exc_info.value.detail)

    def test_successful_analysis(self, mock_db):
        """admin_trigger_analysis successfully analyzes material."""
        from app.routes.admin.materials import admin_trigger_analysis
        
        mock_material = MagicMock()
        mock_material.id = 1
        mock_material.musicxml_canonical = "<score/>"
        
        mock_extraction_result = MagicMock()
        mock_extraction_result.to_dict.return_value = {"chromatic_complexity": 0.5}
        mock_extraction_result.chromatic_complexity_score = 0.5
        mock_extraction_result.measure_count = 4
        
        # First query returns material, second returns existing analysis
        call_count = [0]
        def query_side_effect(*models):
            mock_query = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                mock_query.filter_by.return_value.first.return_value = mock_material
            else:
                mock_query.filter_by.return_value.first.return_value = None  # No existing analysis
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        with patch('app.musicxml_analyzer.analyze_musicxml') as mock_analyze:
            mock_analyze.return_value = (mock_extraction_result, None)
            
            result = admin_trigger_analysis(material_id=1, db=mock_db)
        
        assert result["message"] == "Analysis completed"
        assert "analysis" in result
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_updates_existing_analysis(self, mock_db):
        """admin_trigger_analysis updates existing analysis."""
        from app.routes.admin.materials import admin_trigger_analysis
        
        mock_material = MagicMock()
        mock_material.id = 1
        mock_material.musicxml_canonical = "<score/>"
        
        mock_existing_analysis = MagicMock()
        
        mock_extraction_result = MagicMock()
        mock_extraction_result.to_dict.return_value = {"chromatic_complexity": 0.7}
        
        call_count = [0]
        def query_side_effect(*models):
            mock_query = MagicMock()
            call_count[0] += 1
            if call_count[0] == 1:
                mock_query.filter_by.return_value.first.return_value = mock_material
            else:
                mock_query.filter_by.return_value.first.return_value = mock_existing_analysis
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        with patch('app.musicxml_analyzer.analyze_musicxml') as mock_analyze:
            mock_analyze.return_value = (mock_extraction_result, None)
            
            result = admin_trigger_analysis(material_id=1, db=mock_db)
        
        assert result["message"] == "Analysis completed"
        # Should not add new, just commit updates
        mock_db.add.assert_not_called()
        mock_db.commit.assert_called_once()

    def test_returns_500_on_analysis_error(self, mock_db):
        """admin_trigger_analysis returns 500 when analysis fails."""
        from app.routes.admin.materials import admin_trigger_analysis
        
        mock_material = MagicMock()
        mock_material.id = 1
        mock_material.musicxml_canonical = "<score/>"
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_material
        
        with patch('app.musicxml_analyzer.analyze_musicxml') as mock_analyze:
            mock_analyze.side_effect = Exception("Analysis failed")
            
            with pytest.raises(HTTPException) as exc_info:
                admin_trigger_analysis(material_id=1, db=mock_db)
        
        assert exc_info.value.status_code == 500
        assert "Analysis failed" in str(exc_info.value.detail)
