"""
Tests for app/routes/admin/capabilities/crud_routes.py module.

Tests CRUD operations for capability management.
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException


class TestAdminArchiveCapability:
    """Test archive capability endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_archive_capability_not_found(self, mock_db):
        """Should raise 404 when capability not found."""
        from app.routes.admin.capabilities.crud_routes import admin_archive_capability
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            admin_archive_capability(capability_id=999, db=mock_db)
        
        assert exc_info.value.status_code == 404
        assert "not found" in exc_info.value.detail.lower()
    
    def test_archive_already_archived(self, mock_db):
        """Should return message when already archived."""
        from app.routes.admin.capabilities.crud_routes import admin_archive_capability
        
        mock_cap = MagicMock()
        mock_cap.id = 1
        mock_cap.name = "test_cap"
        mock_cap.is_active = False  # Already archived
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_cap
        
        result = admin_archive_capability(capability_id=1, db=mock_db)
        
        assert result["success"] is True
        assert "already archived" in result["message"]
        assert result["is_active"] is False
    
    def test_archive_active_capability(self, mock_db):
        """Should archive an active capability."""
        from app.routes.admin.capabilities.crud_routes import admin_archive_capability
        
        mock_cap = MagicMock()
        mock_cap.id = 1
        mock_cap.name = "test_cap"
        mock_cap.is_active = True
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_cap
        
        result = admin_archive_capability(capability_id=1, db=mock_db)
        
        assert result["success"] is True
        assert result["is_active"] is False
        assert mock_cap.is_active is False
        mock_db.commit.assert_called_once()


class TestAdminRestoreCapability:
    """Test restore capability endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_restore_capability_not_found(self, mock_db):
        """Should raise 404 when capability not found."""
        from app.routes.admin.capabilities.crud_routes import admin_restore_capability
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            admin_restore_capability(capability_id=999, db=mock_db)
        
        assert exc_info.value.status_code == 404
    
    def test_restore_already_active(self, mock_db):
        """Should return message when already active."""
        from app.routes.admin.capabilities.crud_routes import admin_restore_capability
        
        mock_cap = MagicMock()
        mock_cap.id = 1
        mock_cap.name = "test_cap"
        mock_cap.is_active = True  # Already active
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_cap
        
        result = admin_restore_capability(capability_id=1, db=mock_db)
        
        assert result["success"] is True
        assert "already active" in result["message"]
        assert result["is_active"] is True
    
    def test_restore_archived_capability(self, mock_db):
        """Should restore an archived capability."""
        from app.routes.admin.capabilities.crud_routes import admin_restore_capability
        
        mock_cap = MagicMock()
        mock_cap.id = 1
        mock_cap.name = "test_cap"
        mock_cap.is_active = False
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_cap
        
        result = admin_restore_capability(capability_id=1, db=mock_db)
        
        assert result["success"] is True
        assert result["is_active"] is True
        assert mock_cap.is_active is True
        mock_db.commit.assert_called_once()


class TestAdminDeleteCapability:
    """Test delete capability endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_delete_capability_not_found(self, mock_db):
        """Should raise 404 when capability not found."""
        from app.routes.admin.capabilities.crud_routes import admin_delete_capability
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            admin_delete_capability(capability_id=999, db=mock_db)
        
        assert exc_info.value.status_code == 404
    
    def test_delete_capability_success(self, mock_db):
        """Should delete capability and return info."""
        from app.routes.admin.capabilities.crud_routes import admin_delete_capability
        
        mock_cap = MagicMock()
        mock_cap.id = 1
        mock_cap.name = "test_cap"
        mock_cap.domain = "test_domain"
        mock_cap.bit_index = 5
        
        # Setup the query chain for both filter_by (first cap) and all (other caps)
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_cap
        mock_db.query.return_value.all.return_value = []  # No other caps with prereqs
        
        result = admin_delete_capability(capability_id=1, db=mock_db)
        
        assert result["success"] is True
        assert result["capability_id"] == 1
        assert "message" in result  # Response uses message not name
        mock_db.delete.assert_called_once_with(mock_cap)
        mock_db.commit.assert_called()


class TestHelperFunctions:
    """Test helper functions used by CRUD routes."""
    
    def test_parse_prerequisite_ids_empty(self):
        """Should return empty list for no prerequisites."""
        from app.routes.admin.capabilities.crud_routes import parse_prerequisite_ids
        
        mock_cap = MagicMock()
        mock_cap.prerequisite_ids = None
        
        result = parse_prerequisite_ids(mock_cap)
        
        assert result == []
    
    def test_parse_prerequisite_ids_with_list(self):
        """Should parse JSON list of prerequisite IDs."""
        from app.routes.admin.capabilities.crud_routes import parse_prerequisite_ids
        import json
        
        mock_cap = MagicMock()
        mock_cap.prerequisite_ids = json.dumps([1, 2, 3])
        
        result = parse_prerequisite_ids(mock_cap)
        
        assert result == [1, 2, 3]
    
    def test_check_circular_dependency_no_cycle(self):
        """Should return None when no circular dependency."""
        from app.routes.admin.capabilities.crud_routes import check_circular_dependency
        
        mock_db = MagicMock()
        
        # Mock caps with no circular deps
        cap1 = MagicMock()
        cap1.id = 1
        cap1.prerequisite_ids = None
        
        cap2 = MagicMock()
        cap2.id = 2
        cap2.prerequisite_ids = "[1]"  # Depends on cap1
        
        mock_db.query.return_value.all.return_value = [cap1, cap2]
        
        # Check if adding cap1 as prereq to cap2 doesn't create cycle
        result = check_circular_dependency(2, [1], mock_db)
        
        # Should return None (no cycle)
        assert result is None
