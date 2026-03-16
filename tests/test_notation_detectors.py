"""
Tests for capabilities/detectors/notation_detectors.py

Tests for notation detection functions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestClefDetectors:
    """Tests for clef detection functions."""

    def test_bass_8va_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.notation_detectors import detect_clef_bass_8va
        
        result = detect_clef_bass_8va({}, None)
        
        assert result is False

    def test_treble_8vb_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.notation_detectors import detect_clef_treble_8vb
        
        result = detect_clef_treble_8vb({}, None)
        
        assert result is False


class TestTimeSignatureDetector:
    """Tests for time signature detection."""

    def test_detects_time_signature_when_present(self):
        """Should detect time signature when present in extraction."""
        from app.capabilities.detectors.notation_detectors import detect_any_time_signature
        
        mock_extraction = Mock()
        mock_extraction.time_signatures = ["4/4", "3/4"]
        
        result = detect_any_time_signature(mock_extraction, None)
        
        assert result is True

    def test_no_time_signature_when_empty(self):
        """Should return False when no time signatures."""
        from app.capabilities.detectors.notation_detectors import detect_any_time_signature
        
        mock_extraction = Mock()
        mock_extraction.time_signatures = []
        
        result = detect_any_time_signature(mock_extraction, None)
        
        assert result is False


class TestChordSymbolsDetector:
    """Tests for chord symbol detection."""

    def test_detects_from_extraction_result(self):
        """Should detect chord symbols from extraction result."""
        from app.capabilities.detectors.notation_detectors import detect_chord_symbols
        
        mock_extraction = Mock()
        mock_extraction.chord_symbols = ["Cmaj7", "Dm7"]
        
        result = detect_chord_symbols(mock_extraction, None)
        
        assert result is True

    def test_no_chord_symbols_when_empty(self):
        """Should return False when no chord symbols."""
        from app.capabilities.detectors.notation_detectors import detect_chord_symbols
        
        mock_extraction = Mock()
        mock_extraction.chord_symbols = []
        
        result = detect_chord_symbols(mock_extraction, None)
        
        assert result is False


class TestFiguredBassDetector:
    """Tests for figured bass detection."""

    def test_detects_from_extraction_result(self):
        """Should detect figured bass from extraction result."""
        from app.capabilities.detectors.notation_detectors import detect_figured_bass
        
        mock_extraction = Mock()
        mock_extraction.figured_bass = True
        
        result = detect_figured_bass(mock_extraction, None)
        
        assert result is True

    def test_no_figured_bass_in_extraction(self):
        """Should check score when not in extraction result."""
        from app.capabilities.detectors.notation_detectors import detect_figured_bass
        
        mock_extraction = Mock()
        mock_extraction.figured_bass = False
        
        result = detect_figured_bass(mock_extraction, None)
        
        assert result is False


class TestGraceNoteDetector:
    """Tests for grace note detection."""

    def test_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.notation_detectors import detect_grace_note
        
        result = detect_grace_note({}, None)
        
        assert result is False


class TestBreathMarkDetector:
    """Tests for breath mark detection."""

    def test_detects_from_extraction_result(self):
        """Should detect breath marks from extraction result."""
        from app.capabilities.detectors.notation_detectors import detect_breath_mark
        
        mock_extraction = Mock()
        mock_extraction.breath_marks = 1
        
        result = detect_breath_mark(mock_extraction, None)
        
        assert result is True

    def test_no_breath_marks(self):
        """Should return False when no breath marks."""
        from app.capabilities.detectors.notation_detectors import detect_breath_mark
        
        mock_extraction = Mock()
        mock_extraction.breath_marks = 0
        
        result = detect_breath_mark(mock_extraction, None)
        
        assert result is False


class TestMultiMeasureRestDetector:
    """Tests for multi-measure rest detection."""

    def test_detects_from_extraction_result(self):
        """Should detect multi-measure rests from extraction result."""
        from app.capabilities.detectors.notation_detectors import detect_multimeasure_rest
        
        mock_extraction = Mock()
        mock_extraction.has_multi_measure_rest = True
        
        result = detect_multimeasure_rest(mock_extraction, None)
        
        assert result is True

    def test_no_multi_measure_rest(self):
        """Should return False when no multi-measure rests."""
        from app.capabilities.detectors.notation_detectors import detect_multimeasure_rest
        
        mock_extraction = Mock()
        mock_extraction.has_multi_measure_rest = False
        
        result = detect_multimeasure_rest(mock_extraction, None)
        
        assert result is False


class TestMultiVoiceDetectors:
    """Tests for voice detection functions."""

    def test_detect_two_voices_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.notation_detectors import detect_two_voices
        
        result = detect_two_voices({}, None)
        
        assert result is False

    def test_detect_three_voices_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.notation_detectors import detect_three_voices
        
        result = detect_three_voices({}, None)
        
        assert result is False

    def test_detect_four_voices_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.notation_detectors import detect_four_voices
        
        result = detect_four_voices({}, None)
        
        assert result is False


class TestNotationDetectorRegistry:
    """Tests for custom detector registration."""

    def test_detectors_are_registered(self):
        """Custom detectors should be registered."""
        from app.capabilities.detectors.notation_detectors import CUSTOM_DETECTORS
        
        expected_detectors = [
            "detect_clef_bass_8va",
            "detect_clef_treble_8vb",
            "detect_any_time_signature",
            "detect_chord_symbols",
            "detect_figured_bass",
            "detect_grace_note",
            "detect_breath_mark",
            "detect_multimeasure_rest",
            "detect_two_voices",
            "detect_three_voices",
            "detect_four_voices",
        ]
        
        for detector_name in expected_detectors:
            assert detector_name in CUSTOM_DETECTORS, f"{detector_name} should be registered"

    def test_registered_detectors_are_callable(self):
        """Registered detectors should be callable."""
        from app.capabilities.detectors.notation_detectors import CUSTOM_DETECTORS
        
        for name, detector in CUSTOM_DETECTORS.items():
            assert callable(detector), f"{name} should be callable"
