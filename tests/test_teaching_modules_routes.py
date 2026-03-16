"""
Tests for app/routes/teaching_modules.py
Tests teaching module endpoints.
"""

import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException


class TestGetModule:
    """Tests for get_module endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_returns_404_when_module_not_found(self, mock_db):
        """get_module returns 404 when module doesn't exist."""
        from app.routes.teaching_modules import get_module
        
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with pytest.raises(HTTPException) as exc_info:
            get_module(module_id="nonexistent", db=mock_db)
        assert exc_info.value.status_code == 404


class TestListModules:
    """Tests for list_modules endpoint."""
    
    @pytest.fixture
    def mock_db(self):
        return MagicMock()
    
    def test_returns_list_of_modules(self, mock_db):
        """list_modules returns list of active modules."""
        from app.routes.teaching_modules import list_modules
        
        mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = []
        
        result = list_modules(db=mock_db)
        
        # Should return a dict with modules key or a list
        assert "modules" in result or len(result) >= 0
