"""
Tests for OMR provider infrastructure.

Tests the OMR provider interface, mock provider, and factory.
"""

import pytest
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock

from app.services.omr.base import (
    OmrProvider,
    OmrProviderOptions,
    OmrProviderResult,
    OmrProviderType,
    MeasureConfidenceResult,
    UncertainMeasureResult,
    ExtractedMetadataResult,
)
from app.services.omr.mock_provider import MockOmrProvider
from app.services.omr.audiveris_provider import AudiverisProvider
from app.services.omr.factory import get_omr_provider, list_available_providers


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_provider():
    """Create a mock OMR provider."""
    return MockOmrProvider()


@pytest.fixture
def mock_provider_failing():
    """Create a mock OMR provider that fails."""
    return MockOmrProvider(success=False, error_message="Test failure")


@pytest.fixture
def mock_provider_slow():
    """Create a mock OMR provider with simulated delay."""
    return MockOmrProvider(simulate_delay_ms=100)


@pytest.fixture
def audiveris_provider():
    """Create an Audiveris provider (may not be available)."""
    return AudiverisProvider()


@pytest.fixture
def sample_image_path(tmp_path):
    """Create a sample image file for testing."""
    image_path = tmp_path / "test_score.jpg"
    # Create a minimal file (actual OMR would need real image)
    image_path.write_bytes(b"fake image content")
    return image_path


# =============================================================================
# OmrProviderOptions Tests
# =============================================================================


class TestOmrProviderOptions:
    """Tests for OmrProviderOptions dataclass."""

    def test_default_options(self):
        """Test default option values."""
        options = OmrProviderOptions()

        assert options.language == "en"
        assert options.enhance_image is True
        assert options.detect_parts is True
        assert options.generate_preview is True
        assert options.output_format == "musicxml"
        assert options.timeout_seconds == 300

    def test_custom_options(self):
        """Test custom option values."""
        options = OmrProviderOptions(
            language="de",
            enhance_image=False,
            timeout_seconds=600,
        )

        assert options.language == "de"
        assert options.enhance_image is False
        assert options.timeout_seconds == 600


# =============================================================================
# MockOmrProvider Tests
# =============================================================================


class TestMockOmrProvider:
    """Tests for MockOmrProvider."""

    def test_name(self, mock_provider):
        """Test provider name."""
        assert mock_provider.name == "mock"

    def test_is_available(self, mock_provider):
        """Test availability check."""
        assert mock_provider.is_available is True

    @pytest.mark.asyncio
    async def test_get_version(self, mock_provider):
        """Test version retrieval."""
        version = await mock_provider.get_version()
        assert version == "mock-1.0.0"

    @pytest.mark.asyncio
    async def test_process_success(self, mock_provider, sample_image_path):
        """Test successful processing."""
        result = await mock_provider.process(sample_image_path)

        assert result.success is True
        assert result.confidence == 0.85
        assert result.music_xml is not None
        assert "<score-partwise" in result.music_xml
        assert result.provider_name == "mock"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_process_failure(self, mock_provider_failing, sample_image_path):
        """Test failed processing."""
        result = await mock_provider_failing.process(sample_image_path)

        assert result.success is False
        assert result.error == "Test failure"
        assert result.music_xml is None

    @pytest.mark.asyncio
    async def test_process_with_delay(self, mock_provider_slow, sample_image_path):
        """Test processing with simulated delay."""
        result = await mock_provider_slow.process(sample_image_path)

        assert result.success is True
        assert result.processing_time_ms >= 100

    @pytest.mark.asyncio
    async def test_process_returns_metadata(self, mock_provider, sample_image_path):
        """Test that metadata is extracted."""
        result = await mock_provider.process(sample_image_path)

        assert result.metadata is not None
        assert result.metadata.key_signature == "C"
        assert result.metadata.time_signature == "4/4"
        assert result.metadata.measure_count == 4
        assert result.metadata.part_count == 1

    @pytest.mark.asyncio
    async def test_process_returns_measure_confidence(self, mock_provider, sample_image_path):
        """Test that measure confidence is returned."""
        result = await mock_provider.process(sample_image_path)

        assert len(result.measure_confidence) == 4
        for mc in result.measure_confidence:
            assert mc.measure_number >= 1
            assert 0 <= mc.confidence <= 1


# =============================================================================
# AudiverisProvider Tests
# =============================================================================


class TestAudiverisProvider:
    """Tests for AudiverisProvider."""

    def test_name(self, audiveris_provider):
        """Test provider name."""
        assert audiveris_provider.name == "audiveris"

    def test_is_available_check(self, audiveris_provider):
        """Test that availability check doesn't crash."""
        # This may or may not be available depending on system
        result = audiveris_provider.is_available
        assert isinstance(result, bool)

    def test_default_options(self, audiveris_provider):
        """Test Audiveris-specific default options."""
        options = audiveris_provider.get_default_options()

        assert options.generate_preview is False  # Audiveris doesn't do previews by default
        assert options.timeout_seconds == 300

    def test_find_audiveris_with_custom_path(self, tmp_path):
        """Test finding Audiveris with custom path."""
        fake_jar = tmp_path / "Audiveris.jar"
        fake_jar.write_bytes(b"fake")

        provider = AudiverisProvider(audiveris_path=str(fake_jar))
        found_path = provider._find_audiveris()

        assert found_path == fake_jar
        assert provider._is_jar is True

    def test_fifths_to_key(self, audiveris_provider):
        """Test circle of fifths conversion."""
        assert audiveris_provider._fifths_to_key(0) == "C"
        assert audiveris_provider._fifths_to_key(1) == "G"
        assert audiveris_provider._fifths_to_key(-1) == "F"
        assert audiveris_provider._fifths_to_key(5) == "B"
        assert audiveris_provider._fifths_to_key(-5) == "Db"

    @pytest.mark.asyncio
    async def test_process_missing_input(self, audiveris_provider, tmp_path):
        """Test processing with missing input file."""
        fake_path = tmp_path / "nonexistent.jpg"

        result = await audiveris_provider.process(fake_path)

        assert result.success is False
        assert "not found" in result.error.lower()


# =============================================================================
# Factory Tests
# =============================================================================


class TestOmrProviderFactory:
    """Tests for the provider factory."""

    def test_get_mock_provider(self):
        """Test getting mock provider."""
        with patch("app.services.omr.factory.settings") as mock_settings:
            mock_settings.omr_provider = "mock"
            provider = get_omr_provider(force_new=True)

            assert isinstance(provider, MockOmrProvider)
            assert provider.name == "mock"

    def test_get_audiveris_provider(self):
        """Test getting Audiveris provider."""
        with patch("app.services.omr.factory.settings") as mock_settings:
            mock_settings.omr_provider = "audiveris"
            provider = get_omr_provider(force_new=True)

            assert isinstance(provider, AudiverisProvider)
            assert provider.name == "audiveris"

    def test_get_unknown_provider_raises_error(self):
        """Test that unknown provider raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_omr_provider("unknown_provider", force_new=True)

        assert "Unknown OMR provider" in str(exc_info.value)

    def test_provider_caching(self):
        """Test that providers are cached."""
        with patch("app.services.omr.factory.settings") as mock_settings:
            mock_settings.omr_provider = "mock"
            
            # Clear cache
            from app.services.omr.factory import _provider_cache
            _provider_cache.clear()
            
            provider1 = get_omr_provider()
            provider2 = get_omr_provider()

            assert provider1 is provider2

    def test_force_new_bypasses_cache(self):
        """Test that force_new creates new instance."""
        with patch("app.services.omr.factory.settings") as mock_settings:
            mock_settings.omr_provider = "mock"
            
            provider1 = get_omr_provider()
            provider2 = get_omr_provider(force_new=True)

            assert provider1 is not provider2

    def test_list_available_providers(self):
        """Test listing available providers."""
        with patch("app.services.omr.factory.settings") as mock_settings:
            mock_settings.omr_provider = "mock"
            availability = list_available_providers()

            assert "mock" in availability
            assert availability["mock"] is True
            # Audiveris may or may not be available
            assert "audiveris" in availability


# =============================================================================
# OmrProviderResult Tests
# =============================================================================


class TestOmrProviderResult:
    """Tests for OmrProviderResult dataclass."""

    def test_success_result(self):
        """Test creating a success result."""
        result = OmrProviderResult(
            success=True,
            confidence=0.9,
            music_xml="<score-partwise>...</score-partwise>",
            provider_name="test",
        )

        assert result.success is True
        assert result.error is None

    def test_failure_result(self):
        """Test creating a failure result."""
        result = OmrProviderResult(
            success=False,
            error="Processing failed",
            provider_name="test",
        )

        assert result.success is False
        assert result.error == "Processing failed"
        assert result.music_xml is None

    def test_measure_confidence_list(self):
        """Test measure confidence list."""
        result = OmrProviderResult(
            success=True,
            measure_confidence=[
                MeasureConfidenceResult(measure_number=1, part_index=0, confidence=0.9),
                MeasureConfidenceResult(measure_number=2, part_index=0, confidence=0.85),
            ],
            provider_name="test",
        )

        assert len(result.measure_confidence) == 2

    def test_uncertain_measures(self):
        """Test uncertain measures list."""
        result = OmrProviderResult(
            success=True,
            uncertain_measures=[
                UncertainMeasureResult(
                    measure_number=5,
                    part_index=0,
                    confidence=0.4,
                    reason="Complex rhythm",
                ),
            ],
            provider_name="test",
        )

        assert len(result.uncertain_measures) == 1
        assert result.uncertain_measures[0].reason == "Complex rhythm"


# =============================================================================
# Integration Tests (requires actual infrastructure)
# =============================================================================


@pytest.mark.integration
class TestOmrIntegration:
    """Integration tests requiring actual OMR infrastructure.

    Skip these in CI - run locally with: pytest -m integration
    """

    @pytest.mark.asyncio
    async def test_audiveris_real_processing(self):
        """Test real Audiveris processing (requires Audiveris installed)."""
        provider = AudiverisProvider()

        if not provider.is_available:
            pytest.skip("Audiveris not available")

        # Would need a real test image here
        # For now, just verify the provider is set up correctly
        version = await provider.get_version()
        assert version is not None
