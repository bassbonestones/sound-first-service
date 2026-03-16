"""
Tests for capabilities/detectors/dynamics_detectors.py

Tests for dynamics detection functions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestDynamicsDetectors:
    """Tests for dynamics detector functions."""

    def test_decrescendo_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.dynamics_detectors import detect_decrescendo
        
        result = detect_decrescendo({}, None)
        
        assert result is False


class TestSubitoDetector:
    """Tests for subito dynamics detection."""

    def test_subito_returns_false_for_none_score_and_empty_result(self):
        """Should return False when score is None and no dynamic_changes."""
        from app.capabilities.detectors.dynamics_detectors import detect_subito
        
        result = detect_subito({}, None)
        
        assert result is False

    def test_subito_from_extraction_result(self):
        """Should detect subito from extraction result dynamic_changes."""
        from app.capabilities.detectors.dynamics_detectors import detect_subito
        
        mock_extraction = Mock()
        mock_extraction.dynamic_changes = ["subito f", "crescendo"]
        
        result = detect_subito(mock_extraction, None)
        
        assert result is True

    def test_subito_not_found_in_extraction_result(self):
        """Should not detect subito when not in dynamic_changes."""
        from app.capabilities.detectors.dynamics_detectors import detect_subito
        
        mock_extraction = Mock()
        mock_extraction.dynamic_changes = ["crescendo", "diminuendo"]
        
        result = detect_subito(mock_extraction, None)
        
        assert result is False

    def test_subito_case_insensitive(self):
        """Should detect subito case-insensitively."""
        from app.capabilities.detectors.dynamics_detectors import detect_subito
        
        mock_extraction = Mock()
        mock_extraction.dynamic_changes = ["SUBITO pp"]
        
        result = detect_subito(mock_extraction, None)
        
        assert result is True


class TestDynamicsDetectorRegistry:
    """Tests for custom detector registration."""

    def test_detectors_are_registered(self):
        """Custom detectors should be registered."""
        from app.capabilities.detectors.dynamics_detectors import CUSTOM_DETECTORS
        
        assert "detect_decrescendo" in CUSTOM_DETECTORS
        assert "detect_subito" in CUSTOM_DETECTORS

    def test_registered_detectors_are_callable(self):
        """Registered detectors should be callable."""
        from app.capabilities.detectors.dynamics_detectors import CUSTOM_DETECTORS
        
        for name, detector in CUSTOM_DETECTORS.items():
            assert callable(detector), f"{name} should be callable"
