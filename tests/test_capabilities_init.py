"""Tests for app/capabilities/__init__.py - Global registry and detection engine access."""

import pytest
from unittest.mock import Mock, patch, MagicMock


class TestGetRegistry:
    """Tests for the get_registry function."""

    def test_creates_registry_when_none_exists(self):
        """Creates new CapabilityRegistry when _registry is None."""
        import app.capabilities as cap_module
        
        # Reset global state
        cap_module._registry = None
        
        with patch.object(cap_module, 'CapabilityRegistry') as MockRegistry:
            mock_instance = Mock()
            mock_instance.load.return_value = {"errors": [], "warnings": []}
            MockRegistry.return_value = mock_instance
            
            result = cap_module.get_registry()
            
            MockRegistry.assert_called_once()
            mock_instance.load.assert_called_once()
            assert result == mock_instance

    def test_returns_existing_registry_on_subsequent_calls(self):
        """Returns cached registry on subsequent calls."""
        import app.capabilities as cap_module
        
        mock_registry = Mock()
        cap_module._registry = mock_registry
        
        result = cap_module.get_registry()
        
        assert result == mock_registry

    def test_logs_errors_from_registry_load(self):
        """Logs errors returned from registry.load()."""
        import app.capabilities as cap_module
        
        cap_module._registry = None
        
        with patch.object(cap_module, 'CapabilityRegistry') as MockRegistry, \
             patch.object(cap_module, 'logger') as mock_logger:
            mock_instance = Mock()
            mock_instance.load.return_value = {
                "errors": ["Error 1", "Error 2"],
                "warnings": []
            }
            MockRegistry.return_value = mock_instance
            
            cap_module.get_registry()
            
            assert mock_logger.error.call_count == 2
            mock_logger.error.assert_any_call("Error 1")
            mock_logger.error.assert_any_call("Error 2")

    def test_no_error_logs_when_load_successful(self):
        """Does not log errors when load returns no errors."""
        import app.capabilities as cap_module
        
        cap_module._registry = None
        
        with patch.object(cap_module, 'CapabilityRegistry') as MockRegistry, \
             patch.object(cap_module, 'logger') as mock_logger:
            mock_instance = Mock()
            mock_instance.load.return_value = {"errors": [], "warnings": []}
            MockRegistry.return_value = mock_instance
            
            cap_module.get_registry()
            
            mock_logger.error.assert_not_called()


class TestGetDetectionEngine:
    """Tests for the get_detection_engine function."""

    def test_creates_detection_engine_with_registry(self):
        """Creates DetectionEngine using get_registry."""
        import app.capabilities as cap_module
        
        mock_registry = Mock()
        
        with patch.object(cap_module, 'get_registry') as mock_get_registry, \
             patch.object(cap_module, 'DetectionEngine') as MockEngine:
            mock_get_registry.return_value = mock_registry
            mock_engine_instance = Mock()
            MockEngine.return_value = mock_engine_instance
            
            result = cap_module.get_detection_engine()
            
            mock_get_registry.assert_called_once()
            MockEngine.assert_called_once_with(mock_registry)
            assert result == mock_engine_instance

    def test_returns_new_engine_each_call(self):
        """Returns a new DetectionEngine instance each call."""
        import app.capabilities as cap_module
        
        mock_registry = Mock()
        cap_module._registry = mock_registry
        
        with patch.object(cap_module, 'DetectionEngine') as MockEngine:
            MockEngine.side_effect = [Mock(), Mock()]
            
            engine1 = cap_module.get_detection_engine()
            engine2 = cap_module.get_detection_engine()
            
            # Should create two different instances
            assert MockEngine.call_count == 2
