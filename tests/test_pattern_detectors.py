"""
Tests for capabilities/detectors/pattern_detectors.py

Tests for melodic pattern detection functions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestCompoundIntervalsDetector:
    """Tests for compound interval detection."""

    def test_detects_compound_interval(self):
        """Should detect compound intervals >= 13 semitones."""
        from app.capabilities.detectors.pattern_detectors import detect_compound_intervals
        
        mock_extraction = Mock()
        mock_interval_info = Mock()
        mock_interval_info.semitones = 15  # 9th
        mock_extraction.melodic_intervals = {"m9": mock_interval_info}
        
        result = detect_compound_intervals(mock_extraction, None)
        
        assert result is True

    def test_no_compound_interval_for_octave(self):
        """Should not detect compound for exactly octave."""
        from app.capabilities.detectors.pattern_detectors import detect_compound_intervals
        
        mock_extraction = Mock()
        mock_interval_info = Mock()
        mock_interval_info.semitones = 12  # Octave
        mock_extraction.melodic_intervals = {"P8": mock_interval_info}
        
        result = detect_compound_intervals(mock_extraction, None)
        
        assert result is False

    def test_no_compound_interval_for_small_intervals(self):
        """Should not detect compound for small intervals."""
        from app.capabilities.detectors.pattern_detectors import detect_compound_intervals
        
        mock_extraction = Mock()
        mock_interval_info = Mock()
        mock_interval_info.semitones = 5  # P4
        mock_extraction.melodic_intervals = {"P4": mock_interval_info}
        
        result = detect_compound_intervals(mock_extraction, None)
        
        assert result is False

    def test_empty_intervals(self):
        """Should return False for empty intervals."""
        from app.capabilities.detectors.pattern_detectors import detect_compound_intervals
        
        mock_extraction = Mock()
        mock_extraction.melodic_intervals = {}
        
        result = detect_compound_intervals(mock_extraction, None)
        
        assert result is False


class TestScaleFragment2Detector:
    """Tests for 2-note scale fragment detection."""

    def test_detects_step_interval(self):
        """Should detect stepwise motion (m2 or M2)."""
        from app.capabilities.detectors.pattern_detectors import detect_scale_fragment_2
        
        mock_extraction = Mock()
        mock_interval_info = Mock()
        mock_interval_info.semitones = 2  # M2
        mock_extraction.melodic_intervals = {"M2": mock_interval_info}
        
        result = detect_scale_fragment_2(mock_extraction, None)
        
        assert result is True

    def test_detects_minor_second(self):
        """Should detect minor second."""
        from app.capabilities.detectors.pattern_detectors import detect_scale_fragment_2
        
        mock_extraction = Mock()
        mock_interval_info = Mock()
        mock_interval_info.semitones = 1  # m2
        mock_extraction.melodic_intervals = {"m2": mock_interval_info}
        
        result = detect_scale_fragment_2(mock_extraction, None)
        
        assert result is True

    def test_no_scale_for_third(self):
        """Should not detect scale fragment for third."""
        from app.capabilities.detectors.pattern_detectors import detect_scale_fragment_2
        
        mock_extraction = Mock()
        mock_interval_info = Mock()
        mock_interval_info.semitones = 3  # m3
        mock_extraction.melodic_intervals = {"m3": mock_interval_info}
        
        result = detect_scale_fragment_2(mock_extraction, None)
        
        assert result is False


class TestScaleFragment3Detector:
    """Tests for 3-note scale fragment detection."""

    def test_with_none_score_and_two_intervals(self):
        """Should detect from intervals when score is None."""
        from app.capabilities.detectors.pattern_detectors import detect_scale_fragment_3
        
        mock_extraction = Mock()
        mock_extraction.melodic_intervals = {"m2": Mock(), "M2": Mock()}
        
        result = detect_scale_fragment_3(mock_extraction, None)
        
        assert result is True

    def test_with_none_score_and_one_interval(self):
        """Should not detect with only one interval."""
        from app.capabilities.detectors.pattern_detectors import detect_scale_fragment_3
        
        mock_extraction = Mock()
        mock_extraction.melodic_intervals = {"m2": Mock()}
        
        result = detect_scale_fragment_3(mock_extraction, None)
        
        assert result is False


class TestScaleFragment4Detector:
    """Tests for 4-note scale fragment detection."""

    def test_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.pattern_detectors import detect_scale_fragment_4
        
        result = detect_scale_fragment_4({}, None)
        
        assert result is False


class TestScaleFragment5Detector:
    """Tests for 5-note scale fragment detection."""

    def test_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.pattern_detectors import detect_scale_fragment_5
        
        result = detect_scale_fragment_5({}, None)
        
        assert result is False


class TestScaleFragment6Detector:
    """Tests for 6-note scale fragment detection."""

    def test_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.pattern_detectors import detect_scale_fragment_6
        
        result = detect_scale_fragment_6({}, None)
        
        assert result is False


class TestPatternDetectorRegistry:
    """Tests for custom detector registration."""

    def test_detectors_are_registered(self):
        """Custom detectors should be registered."""
        from app.capabilities.detectors.pattern_detectors import CUSTOM_DETECTORS
        
        expected_detectors = [
            "detect_compound_intervals",
            "detect_scale_fragment_2",
            "detect_scale_fragment_3",
            "detect_scale_fragment_4",
            "detect_scale_fragment_5",
            "detect_scale_fragment_6",
        ]
        
        for detector_name in expected_detectors:
            assert detector_name in CUSTOM_DETECTORS, f"{detector_name} should be registered"

    def test_registered_detectors_are_callable(self):
        """Registered detectors should be callable."""
        from app.capabilities.detectors.pattern_detectors import CUSTOM_DETECTORS
        
        for name, detector in CUSTOM_DETECTORS.items():
            assert callable(detector), f"{name} should be callable"
