"""
Tests for app/routes/admin/users.py
Tests admin user management endpoints.
"""

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from fastapi import HTTPException


class TestAdminGetUserProgression:
    """Tests for admin_get_user_progression endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_user_not_found_returns_404(self, mock_db):
        """admin_get_user_progression returns 404 when user doesn't exist."""
        from app.routes.admin.users import admin_get_user_progression
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            admin_get_user_progression(user_id=999, db=mock_db)
        assert exc_info.value.status_code == 404
    
    def test_returns_full_progression_data(self, mock_db):
        """admin_get_user_progression returns complete progression response."""
        from app.routes.admin.users import admin_get_user_progression
        
        # Setup mock user
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"
        mock_user.instrument = "trombone"
        mock_user.resonant_note = "F3"
        mock_user.range_low = "E2"
        mock_user.range_high = "Bb4"
        mock_user.day0_completed = True
        mock_user.day0_stage = 4
        
        # Setup mock instrument
        mock_instrument = MagicMock()
        mock_instrument.id = 1
        mock_instrument.instrument_name = "trombone"
        mock_instrument.is_primary = True
        
        def query_side_effect(*models):
            mock_query = MagicMock()
            name = models[0].__name__ if hasattr(models[0], '__name__') else str(models[0])
            
            if 'User' in name:
                mock_query.filter_by.return_value.first.return_value = mock_user
            elif 'UserInstrument' in name:
                mock_query.filter.return_value.all.return_value = [mock_instrument]
            elif 'UserCapability' in name:
                mock_query.join.return_value.filter.return_value.filter.return_value.all.return_value = []
            elif 'SoftGateRule' in name:
                mock_query.all.return_value = []
            elif 'UserSoftGateState' in name:
                mock_query.filter.return_value.all.return_value = []
            elif 'PracticeAttempt' in name:
                mock_query.filter.return_value.count.return_value = 50
            else:
                mock_query.filter.return_value.all.return_value = []
            
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        result = admin_get_user_progression(user_id=1, db=mock_db)
        
        assert "user" in result
        assert result["user"]["id"] == 1


class TestAdminUpdateUserInfo:
    """Tests for admin_update_user_info endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_user_not_found_returns_404(self, mock_db):
        """admin_update_user_info returns 404 when user doesn't exist."""
        from app.routes.admin.users import admin_update_user_info, UserInfoUpdate
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        update = UserInfoUpdate(instrument="trumpet")
        
        with pytest.raises(HTTPException) as exc_info:
            admin_update_user_info(user_id=999, update=update, db=mock_db)
        assert exc_info.value.status_code == 404
    
    def test_updates_instrument_successfully(self, mock_db):
        """admin_update_user_info updates user instrument."""
        from app.routes.admin.users import admin_update_user_info, UserInfoUpdate
        
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.instrument = "trombone"
        mock_user.resonant_note = "F3"
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_user
        
        update = UserInfoUpdate(instrument="trumpet", resonant_note="C4")
        result = admin_update_user_info(user_id=1, update=update, db=mock_db)
        
        assert mock_user.instrument == "trumpet"
        mock_db.commit.assert_called()


class TestAdminUpdateSoftGate:
    """Tests for admin_update_soft_gate endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_user_not_found_returns_404(self, mock_db):
        """admin_update_soft_gate returns 404 when user doesn't exist."""
        from app.routes.admin.users import admin_update_soft_gate, SoftGateUpdate
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        update = SoftGateUpdate(frontier=10.0)
        
        with pytest.raises(HTTPException) as exc_info:
            admin_update_soft_gate(user_id=999, dimension_name="range", update=update, db=mock_db)
        assert exc_info.value.status_code == 404


class TestAdminAddUserCapability:
    """Tests for admin_add_user_capability endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_user_not_found_returns_404(self, mock_db):
        """admin_add_user_capability returns 404 when user doesn't exist."""
        from app.routes.admin.users import admin_add_user_capability, CapabilityAdd
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        data = CapabilityAdd(capability_id=1, mastered=True)
        
        with pytest.raises(HTTPException) as exc_info:
            admin_add_user_capability(user_id=999, data=data, db=mock_db)
        assert exc_info.value.status_code == 404


class TestAdminResetUser:
    """Tests for admin_reset_user endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_user_not_found_returns_404(self, mock_db):
        """admin_reset_user returns 404 when user doesn't exist."""
        from app.routes.admin.users import admin_reset_user
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            admin_reset_user(user_id=999, db=mock_db)
        assert exc_info.value.status_code == 404
    
    def test_resets_user_data_successfully(self, mock_db):
        """admin_reset_user clears all user progression data."""
        from app.routes.admin.users import admin_reset_user
        
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.day0_completed = True
        mock_user.day0_stage = 4
        
        def query_side_effect(*models):
            mock_query = MagicMock()
            name = models[0].__name__ if hasattr(models[0], '__name__') else str(models[0])
            
            if 'User' in name:
                mock_query.filter_by.return_value.first.return_value = mock_user
            else:
                mock_query.filter.return_value.delete.return_value = 5
            
            return mock_query
        
        mock_db.query.side_effect = query_side_effect
        
        result = admin_reset_user(user_id=1, db=mock_db)
        
        assert mock_user.day0_completed == False
        assert mock_user.day0_stage == 0
        mock_db.commit.assert_called()


class TestAdminGenerateDiagnosticSession:
    """Tests for admin_generate_diagnostic_session endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_user_not_found_returns_404(self, mock_db):
        """admin_generate_diagnostic_session returns 404 when user doesn't exist."""
        from app.routes.admin.users import admin_generate_diagnostic_session
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            admin_generate_diagnostic_session(user_id=999, db=mock_db)
        assert exc_info.value.status_code == 404
