"""
Tests for capabilities/detectors/accidental_detectors.py

Tests for accidental detection functions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestAccidentalDetectors:
    """Tests for accidental detector functions."""

    def test_flat_accidentals_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.accidental_detectors import detect_flat_accidentals
        
        result = detect_flat_accidentals({}, None)
        
        assert result is False

    def test_sharp_accidentals_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.accidental_detectors import detect_sharp_accidentals
        
        result = detect_sharp_accidentals({}, None)
        
        assert result is False

    def test_natural_accidentals_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.accidental_detectors import detect_natural_accidentals
        
        result = detect_natural_accidentals({}, None)
        
        assert result is False

    def test_double_flat_accidentals_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.accidental_detectors import detect_double_flat_accidentals
        
        result = detect_double_flat_accidentals({}, None)
        
        assert result is False

    def test_double_sharp_accidentals_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.accidental_detectors import detect_double_sharp_accidentals
        
        result = detect_double_sharp_accidentals({}, None)
        
        assert result is False

    def test_chromatic_approach_tones_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.accidental_detectors import detect_chromatic_approach_tones
        
        result = detect_chromatic_approach_tones({}, None)
        
        assert result is False


class TestCustomDetectorRegistry:
    """Tests for custom detector registration."""

    def test_detectors_are_registered(self):
        """Custom detectors should be registered."""
        from app.capabilities.detectors.accidental_detectors import CUSTOM_DETECTORS
        
        assert "detect_flat_accidentals" in CUSTOM_DETECTORS
        assert "detect_sharp_accidentals" in CUSTOM_DETECTORS
        assert "detect_natural_accidentals" in CUSTOM_DETECTORS
        assert "detect_double_flat_accidentals" in CUSTOM_DETECTORS
        assert "detect_double_sharp_accidentals" in CUSTOM_DETECTORS
        assert "detect_chromatic_approach_tones" in CUSTOM_DETECTORS

    def test_registered_detectors_are_callable(self):
        """Registered detectors should be callable."""
        from app.capabilities.detectors.accidental_detectors import CUSTOM_DETECTORS
        
        for name, detector in CUSTOM_DETECTORS.items():
            assert callable(detector), f"{name} should be callable"
