"""
Tests for capabilities/detectors/structure_detectors.py

Tests for structure and repeat detection functions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch


class TestCodaDetector:
    """Tests for coda detection."""

    def test_detects_coda_from_extraction_result(self):
        """Should detect coda from extraction result."""
        from app.capabilities.detectors.structure_detectors import detect_coda
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["Coda", "repeat"]
        
        result = detect_coda(mock_extraction, None)
        
        assert result is True

    def test_no_coda_when_absent(self):
        """Should return False when no coda in extraction."""
        from app.capabilities.detectors.structure_detectors import detect_coda
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["repeat"]
        
        result = detect_coda(mock_extraction, None)
        
        assert result is False


class TestDaCapoDetector:
    """Tests for Da Capo detection."""

    def test_detects_dc_from_extraction_result(self):
        """Should detect D.C. from extraction result."""
        from app.capabilities.detectors.structure_detectors import detect_da_capo
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["D.C.", "repeat"]
        
        result = detect_da_capo(mock_extraction, None)
        
        assert result is True

    def test_detects_da_capo_full_text(self):
        """Should detect 'da capo' text."""
        from app.capabilities.detectors.structure_detectors import detect_da_capo
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["Da Capo al Fine"]
        
        result = detect_da_capo(mock_extraction, None)
        
        assert result is True

    def test_no_da_capo_when_absent(self):
        """Should return False when no Da Capo."""
        from app.capabilities.detectors.structure_detectors import detect_da_capo
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["repeat"]
        
        result = detect_da_capo(mock_extraction, None)
        
        assert result is False


class TestDalSegnoDetector:
    """Tests for Dal Segno detection."""

    def test_detects_ds_from_extraction_result(self):
        """Should detect D.S. from extraction result."""
        from app.capabilities.detectors.structure_detectors import detect_dal_segno
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["D.S.", "coda"]
        
        result = detect_dal_segno(mock_extraction, None)
        
        assert result is True

    def test_detects_dal_segno_full_text(self):
        """Should detect 'dal segno' text."""
        from app.capabilities.detectors.structure_detectors import detect_dal_segno
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["Dal Segno al Coda"]
        
        result = detect_dal_segno(mock_extraction, None)
        
        assert result is True

    def test_no_dal_segno_when_absent(self):
        """Should return False when no Dal Segno."""
        from app.capabilities.detectors.structure_detectors import detect_dal_segno
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["repeat"]
        
        result = detect_dal_segno(mock_extraction, None)
        
        assert result is False


class TestFineDetector:
    """Tests for Fine detection."""

    def test_detects_fine_from_extraction_result(self):
        """Should detect Fine from extraction result."""
        from app.capabilities.detectors.structure_detectors import detect_fine
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["Fine"]
        
        result = detect_fine(mock_extraction, None)
        
        assert result is True

    def test_no_fine_when_absent(self):
        """Should return False when no Fine."""
        from app.capabilities.detectors.structure_detectors import detect_fine
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["repeat"]
        
        result = detect_fine(mock_extraction, None)
        
        assert result is False


class TestSegnoDetector:
    """Tests for Segno detection."""

    def test_detects_segno_from_extraction_result(self):
        """Should detect Segno from extraction result."""
        from app.capabilities.detectors.structure_detectors import detect_segno
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["Segno", "D.S."]
        
        result = detect_segno(mock_extraction, None)
        
        assert result is True

    def test_no_segno_when_absent(self):
        """Should return False when no Segno."""
        from app.capabilities.detectors.structure_detectors import detect_segno
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["repeat"]
        
        result = detect_segno(mock_extraction, None)
        
        assert result is False


class TestRepeatSignDetector:
    """Tests for repeat sign detection."""

    def test_detects_repeat_from_extraction_result(self):
        """Should detect repeat from extraction result."""
        from app.capabilities.detectors.structure_detectors import detect_repeat_sign
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["repeat_start", "repeat_end"]
        
        result = detect_repeat_sign(mock_extraction, None)
        
        assert result is True

    def test_no_repeat_when_absent(self):
        """Should return False when no repeat signs."""
        from app.capabilities.detectors.structure_detectors import detect_repeat_sign
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["Fine"]
        
        result = detect_repeat_sign(mock_extraction, None)
        
        assert result is False


class TestFirstEndingDetector:
    """Tests for first ending detection."""

    def test_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.structure_detectors import detect_first_ending
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["first_ending"]
        
        result = detect_first_ending(mock_extraction, None)
        
        assert result is False


class TestSecondEndingDetector:
    """Tests for second ending detection."""

    def test_returns_false_for_none_score(self):
        """Should return False when score is None."""
        from app.capabilities.detectors.structure_detectors import detect_second_ending
        
        mock_extraction = Mock()
        mock_extraction.repeat_structures = ["second_ending"]
        
        result = detect_second_ending(mock_extraction, None)
        
        assert result is False


class TestStructureDetectorRegistry:
    """Tests for custom detector registration."""

    def test_detectors_are_registered(self):
        """Custom detectors should be registered."""
        from app.capabilities.detectors.structure_detectors import CUSTOM_DETECTORS
        
        expected_detectors = [
            "detect_coda",
            "detect_da_capo",
            "detect_dal_segno",
            "detect_fine",
            "detect_segno",
            "detect_repeat_sign",
            "detect_first_ending",
            "detect_second_ending",
        ]
        
        for detector_name in expected_detectors:
            assert detector_name in CUSTOM_DETECTORS, f"{detector_name} should be registered"

    def test_registered_detectors_are_callable(self):
        """Registered detectors should be callable."""
        from app.capabilities.detectors.structure_detectors import CUSTOM_DETECTORS
        
        for name, detector in CUSTOM_DETECTORS.items():
            assert callable(detector), f"{name} should be callable"
