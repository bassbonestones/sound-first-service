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


class TestAdminCreateCapability:
    """Tests for admin_create_capability endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_rejects_duplicate_name(self, mock_db):
        """Should return 400 when capability name already exists."""
        from app.routes.admin.capabilities.crud_routes import admin_create_capability
        from app.routes.admin.capabilities.schemas import CapabilityCreateRequest
        
        # Existing capability found
        mock_cap = MagicMock()
        mock_cap.name = "existing_cap"
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_cap
        
        create_data = CapabilityCreateRequest(
            name="existing_cap",
            display_name="Existing Cap",
            domain="rhythm",
            difficulty_tier=1,
        )
        
        with pytest.raises(HTTPException) as exc_info:
            admin_create_capability(create_data=create_data, db=mock_db)
        
        assert exc_info.value.status_code == 400
        assert "already exists" in exc_info.value.detail
    
    def test_creates_capability_in_new_domain(self, mock_db):
        """Should create capability and assign correct bit_index for new domain."""
        from app.routes.admin.capabilities.crud_routes import admin_create_capability
        from app.routes.admin.capabilities.schemas import CapabilityCreateRequest
        from unittest.mock import PropertyMock
        
        # No existing capability with this name
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        # No existing capabilities
        mock_db.query.return_value.order_by.return_value.all.return_value = []
        
        # Max bit_index query
        mock_db.query.return_value.scalar.return_value = None  # No existing caps
        
        # Mock add/commit/refresh
        created_cap = MagicMock()
        created_cap.id = 1
        created_cap.name = "new_cap"
        created_cap.display_name = "New Cap"
        created_cap.domain = "rhythm"
        created_cap.bit_index = 0
        
        def capture_add(cap):
            for attr in ['id', 'name', 'display_name', 'domain', 'bit_index']:
                setattr(created_cap, attr, getattr(cap, attr, getattr(created_cap, attr)))
        
        mock_db.add = capture_add
        mock_db.refresh = lambda x: None
        
        create_data = CapabilityCreateRequest(
            name="new_cap",
            display_name="New Cap",
            domain="rhythm",
            difficulty_tier=1,
        )
        
        result = admin_create_capability(create_data=create_data, db=mock_db)
        
        assert result["success"] is True
        assert "Created capability" in result["message"]


class TestAdminUpdateCapability:
    """Tests for admin_update_capability endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        return MagicMock()
    
    def test_returns_404_for_nonexistent(self, mock_db):
        """Should return 404 when capability not found."""
        from app.routes.admin.capabilities.crud_routes import admin_update_capability
        from app.routes.admin.capabilities.schemas import CapabilityUpdateRequest
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        update_data = CapabilityUpdateRequest(
            name="updated_name",
            display_name="Updated",
            domain="rhythm",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            admin_update_capability(capability_id=999, update_data=update_data, db=mock_db)
        
        assert exc_info.value.status_code == 404
    
    def test_validates_name_format(self, mock_db):
        """Should reject invalid name format."""
        from app.routes.admin.capabilities.crud_routes import admin_update_capability
        from app.routes.admin.capabilities.schemas import CapabilityUpdateRequest
        
        mock_cap = MagicMock()
        mock_cap.id = 1
        mock_cap.name = "existing_cap"
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_cap
        
        # Name with invalid characters (uppercase)
        update_data = CapabilityUpdateRequest(
            name="InvalidName",
            display_name="Invalid Name",
            domain="rhythm",
        )
        
        with pytest.raises(HTTPException) as exc_info:
            admin_update_capability(capability_id=1, update_data=update_data, db=mock_db)
        
        assert exc_info.value.status_code == 422
        assert "lowercase" in str(exc_info.value.detail)
    
    def test_updates_valid_capability(self, mock_db):
        """Should update capability with valid data."""
        from app.routes.admin.capabilities.crud_routes import admin_update_capability
        from app.routes.admin.capabilities.schemas import CapabilityUpdateRequest
        
        mock_cap = MagicMock()
        mock_cap.id = 1
        mock_cap.name = "existing_cap"
        mock_cap.display_name = "Existing Cap"
        mock_cap.domain = "rhythm"
        mock_cap.prerequisite_ids = None
        mock_cap.is_active = True
        
        # First query returns the cap
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_cap
        # For duplicate check, return None
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        update_data = CapabilityUpdateRequest(
            name="updated_cap",
            display_name="Updated Cap",
            domain="rhythm",
        )
        
        result = admin_update_capability(capability_id=1, update_data=update_data, db=mock_db)
        
        assert result["success"] is True
