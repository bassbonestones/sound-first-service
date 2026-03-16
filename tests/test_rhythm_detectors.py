"""
Tests for capabilities/detectors/rhythm_detectors.py

Tests for rhythm detection functions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestSyncopationDetector:
    """Tests for syncopation detection."""

    def test_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.rhythm_detectors import detect_syncopation
        
        mock_extraction = Mock()
        mock_extraction.has_ties = False
        
        result = detect_syncopation(mock_extraction, None)
        
        assert result is False

    def test_detects_syncopation_from_ties(self):
        """Should detect syncopation when has_ties is True."""
        from app.capabilities.detectors.rhythm_detectors import detect_syncopation
        
        mock_extraction = Mock()
        mock_extraction.has_ties = True
        
        mock_score = Mock()
        mock_score.parts = []
        
        result = detect_syncopation(mock_extraction, mock_score)
        
        assert result is True


class TestTiesDetector:
    """Tests for tie detection."""

    def test_detects_ties_when_present(self):
        """Should return True when has_ties is True."""
        from app.capabilities.detectors.rhythm_detectors import detect_ties
        
        mock_extraction = Mock()
        mock_extraction.has_ties = True
        
        result = detect_ties(mock_extraction, None)
        
        assert result is True

    def test_no_ties_when_absent(self):
        """Should return False when has_ties is False."""
        from app.capabilities.detectors.rhythm_detectors import detect_ties
        
        mock_extraction = Mock()
        mock_extraction.has_ties = False
        
        result = detect_ties(mock_extraction, None)
        
        assert result is False


class TestHemiolaDetector:
    """Tests for hemiola detection."""

    def test_hemiola_returns_false(self):
        """Hemiola detector is a stub and returns False."""
        from app.capabilities.detectors.rhythm_detectors import detect_hemiola
        
        result = detect_hemiola({}, None)
        
        assert result is False


class TestTupletDetectors:
    """Tests for tuplet detection functions."""

    def test_eighth_triplets_when_present(self):
        """Should detect eighth triplets from tuplets list."""
        from app.capabilities.detectors.rhythm_detectors import detect_eighth_triplets
        
        mock_extraction = Mock()
        mock_extraction.tuplets = ["tuplet_3_eighth", "other"]
        
        result = detect_eighth_triplets(mock_extraction, None)
        
        assert result is True

    def test_eighth_triplets_when_absent(self):
        """Should not detect eighth triplets when not present."""
        from app.capabilities.detectors.rhythm_detectors import detect_eighth_triplets
        
        mock_extraction = Mock()
        mock_extraction.tuplets = ["tuplet_4", "other"]
        
        result = detect_eighth_triplets(mock_extraction, None)
        
        assert result is False

    def test_quarter_triplets_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.rhythm_detectors import detect_quarter_triplets
        
        result = detect_quarter_triplets({}, None)
        
        assert result is False

    def test_duplet_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.rhythm_detectors import detect_duplet
        
        result = detect_duplet({}, None)
        
        assert result is False

    def test_quintuplet_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.rhythm_detectors import detect_quintuplet
        
        result = detect_quintuplet({}, None)
        
        assert result is False

    def test_sextuplet_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.rhythm_detectors import detect_sextuplet
        
        result = detect_sextuplet({}, None)
        
        assert result is False

    def test_septuplet_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.rhythm_detectors import detect_septuplet
        
        result = detect_septuplet({}, None)
        
        assert result is False


class TestRhythmDetectorRegistry:
    """Tests for custom detector registration."""

    def test_detectors_are_registered(self):
        """Custom detectors should be registered."""
        from app.capabilities.detectors.rhythm_detectors import CUSTOM_DETECTORS
        
        expected_detectors = [
            "detect_syncopation",
            "detect_ties",
            "detect_hemiola",
            "detect_eighth_triplets",
            "detect_quarter_triplets",
            "detect_duplet",
            "detect_quintuplet",
            "detect_sextuplet",
            "detect_septuplet",
        ]
        
        for detector_name in expected_detectors:
            assert detector_name in CUSTOM_DETECTORS, f"{detector_name} should be registered"

    def test_registered_detectors_are_callable(self):
        """Registered detectors should be callable."""
        from app.capabilities.detectors.rhythm_detectors import CUSTOM_DETECTORS
        
        for name, detector in CUSTOM_DETECTORS.items():
            assert callable(detector), f"{name} should be callable"
