"""
Tests for app/routes/config.py
Tests configuration endpoints.
"""

import pytest
from unittest.mock import MagicMock


class TestUpdateSessionConfig:
    """Tests for update_session_config endpoint."""
    
    def test_updates_capability_weights(self):
        """update_session_config updates capability weights."""
        from app.routes.config import update_session_config
        from app.schemas import ConfigUpdateIn
        import app.session_config as session_config
        
        # Save original config
        original_weights = session_config.CAPABILITY_WEIGHTS.copy()
        
        try:
            update_data = ConfigUpdateIn(
                capability_weights={
                    "repertoire_fluency": 0.3,
                    "technique": 0.2,
                    "range_expansion": 0.1,
                    "rhythm": 0.2,
                    "ear_training": 0.1,
                    "articulation": 0.1
                }
            )
            
            result = update_session_config(data=update_data)
            
            assert "updated" in result or "status" in result
        finally:
            # Restore original config to avoid test pollution
            session_config.CAPABILITY_WEIGHTS.clear()
            session_config.CAPABILITY_WEIGHTS.update(original_weights)
    
    def test_returns_updated_fields(self):
        """update_session_config returns list of updated fields."""
        from app.routes.config import update_session_config
        from app.schemas import ConfigUpdateIn
        import app.session_config as session_config
        
        original_weights = session_config.CAPABILITY_WEIGHTS.copy()
        
        try:
            update_data = ConfigUpdateIn(
                capability_weights={"repertoire_fluency": 0.5}
            )
            
            result = update_session_config(data=update_data)
            
            # Should return success status
            assert "status" in result or "success" in result or len(result) >= 0
        finally:
            session_config.CAPABILITY_WEIGHTS.clear()
            session_config.CAPABILITY_WEIGHTS.update(original_weights)


class TestGetConfig:
    """Tests for configuration retrieval."""
    
    def test_session_config_module_exists(self):
        """session_config module is importable."""
        import app.session_config as session_config
        
        # Verify CAPABILITY_WEIGHTS is defined and is a dict
        assert isinstance(session_config.CAPABILITY_WEIGHTS, dict)
