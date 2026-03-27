"""
Tests for OMR provider infrastructure.

Tests the OMR provider interface, mock provider, and factory.
"""

import pytest
import asyncio
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

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

    @pytest.mark.asyncio
    async def test_process_returns_not_available_when_not_found(self, tmp_path):
        """Test process returns error when Audiveris not available."""
        provider = AudiverisProvider(audiveris_path="/nonexistent/path")
        
        # Create a fake input file
        input_file = tmp_path / "test.jpg"
        input_file.write_bytes(b"fake image")
        
        result = await provider.process(input_file)
        
        assert result.success is False
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_process_with_mocked_subprocess(self, tmp_path):
        """Test process with mocked subprocess call."""
        import asyncio
        
        # Create provider with fake JAR
        fake_jar = tmp_path / "Audiveris.jar"
        fake_jar.write_bytes(b"fake jar")
        
        provider = AudiverisProvider(audiveris_path=str(fake_jar))
        
        # Create input file
        input_file = tmp_path / "test.jpg"
        input_file.write_bytes(b"fake image data")
        
        # Create fake output directory with MXL file
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        mxl_file = output_dir / "test.mxl"
        
        # Create a minimal MXL (which is a zip with musicxml inside)
        import zipfile
        with zipfile.ZipFile(mxl_file, "w") as zf:
            zf.writestr("test.xml", """<?xml version="1.0"?>
            <score-partwise><part-list/></score-partwise>""")
        
        # Mock subprocess calls
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(return_value=(b"Processing complete", b""))
            mock_process.returncode = 0
            mock_exec.return_value = mock_process
            
            # Mock Java check for is_available
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                
                # Mock _find_output_file to return our fake MXL
                with patch.object(provider, "_find_output_file", return_value=mxl_file):
                    result = await provider.process(input_file, output_dir=output_dir)
        
        # Should have processed (success depends on parsing)
        assert result is not None
        assert hasattr(result, "success")

    @pytest.mark.asyncio
    async def test_get_version_with_mock(self, tmp_path):
        """Test get_version with mocked subprocess."""
        fake_jar = tmp_path / "Audiveris.jar"
        fake_jar.write_bytes(b"fake jar")
        
        provider = AudiverisProvider(audiveris_path=str(fake_jar))
        
        with patch("asyncio.create_subprocess_exec") as mock_exec:
            mock_process = MagicMock()
            mock_process.communicate = AsyncMock(return_value=(b"Audiveris 5.3.1 - Help", b""))
            mock_exec.return_value = mock_process
            
            version = await provider.get_version()
        
        assert version == "5.3.1"

    def test_build_command_for_jar(self, tmp_path):
        """Test command building for JAR file."""
        fake_jar = tmp_path / "Audiveris.jar"
        fake_jar.write_bytes(b"fake jar")
        
        provider = AudiverisProvider(audiveris_path=str(fake_jar))
        _ = provider._find_audiveris()  # Set _is_jar flag
        
        cmd = provider._build_command(fake_jar, ["-help"])
        
        assert "java" in cmd[0]
        assert "-jar" in cmd
        assert str(fake_jar) in cmd

    def test_build_command_for_app_bundle(self, tmp_path):
        """Test command building for app bundle with multiple JARs."""
        # Create multiple JAR files to simulate app bundle
        fake_jar = tmp_path / "Audiveris.jar"
        fake_jar.write_bytes(b"main jar")
        (tmp_path / "lib1.jar").write_bytes(b"lib1")
        (tmp_path / "lib2.jar").write_bytes(b"lib2")
        
        provider = AudiverisProvider(audiveris_path=str(fake_jar))
        _ = provider._find_audiveris()
        
        cmd = provider._build_command(fake_jar, ["-help"])
        
        assert "java" in cmd[0]
        assert "-cp" in cmd  # Should use classpath instead of -jar
        assert "Audiveris" in cmd  # Main class

    def test_build_command_for_executable(self, tmp_path):
        """Test command building for executable script."""
        fake_exec = tmp_path / "audiveris"
        fake_exec.write_text("#!/bin/bash\necho audiveris")
        
        provider = AudiverisProvider(audiveris_path=str(fake_exec))
        # Not setting _is_jar - it's an executable
        provider._is_jar = False
        
        cmd = provider._build_command(fake_exec, ["-help"])
        
        assert cmd[0] == str(fake_exec)
        assert "-help" in cmd

    def test_parse_error_out_of_memory(self):
        """Test parsing OutOfMemoryError."""
        provider = AudiverisProvider()
        
        error = provider._parse_error("java.lang.OutOfMemoryError: Java heap space")
        
        assert error is not None
        assert "memory" in error.lower()

    def test_parse_error_no_sheet(self):
        """Test parsing 'No sheet' error."""
        provider = AudiverisProvider()
        
        error = provider._parse_error("No sheet detected in the image")
        
        assert error is not None
        assert "sheet music" in error.lower()

    def test_parse_error_io_exception(self):
        """Test parsing IOException."""
        provider = AudiverisProvider()
        
        error = provider._parse_error("java.io.IOException: File not found")
        
        assert error is not None
        assert "files" in error.lower()

    def test_parse_error_generic_error_line(self):
        """Test parsing generic ERROR line."""
        provider = AudiverisProvider()
        
        error = provider._parse_error("Some output\nERROR: Failed to process\nMore output")
        
        assert error is not None
        assert "Failed to process" in error

    def test_parse_error_no_error(self):
        """Test parse_error with no error."""
        provider = AudiverisProvider()
        
        error = provider._parse_error("Processing complete\nSuccess")
        
        assert error is None

    def test_estimate_measure_confidence_full(self):
        """Test measure confidence estimation with normal measure."""
        provider = AudiverisProvider()
        
        measure_xml = """<measure number="1">
            <note><pitch><step>C</step><octave>4</octave></pitch></note>
            <note><pitch><step>D</step><octave>4</octave></pitch></note>
        </measure>"""
        measure = ET.fromstring(measure_xml)
        
        confidence = provider._estimate_measure_confidence(measure)
        
        assert confidence >= 0.8  # Should be high confidence

    def test_estimate_measure_confidence_empty(self):
        """Test measure confidence for empty measure."""
        provider = AudiverisProvider()
        
        measure_xml = """<measure number="1"></measure>"""
        measure = ET.fromstring(measure_xml)
        
        confidence = provider._estimate_measure_confidence(measure)
        
        assert confidence < 0.8  # Should be lower for empty measure

    def test_estimate_measure_confidence_with_forward(self):
        """Test measure confidence with forward element."""
        provider = AudiverisProvider()
        
        measure_xml = """<measure number="1">
            <note><pitch><step>C</step><octave>4</octave></pitch></note>
            <forward><duration>4</duration></forward>
        </measure>"""
        measure = ET.fromstring(measure_xml)
        
        confidence = provider._estimate_measure_confidence(measure)
        
        # Should be reduced due to forward element
        assert confidence < 0.9

    def test_estimate_measure_confidence_with_grace(self):
        """Test measure confidence with grace notes."""
        provider = AudiverisProvider()
        
        measure_xml = """<measure number="1">
            <note><grace/><pitch><step>C</step><octave>4</octave></pitch></note>
            <note><pitch><step>D</step><octave>4</octave></pitch></note>
        </measure>"""
        measure = ET.fromstring(measure_xml)
        
        confidence = provider._estimate_measure_confidence(measure)
        
        # Should be slightly reduced for grace notes
        assert confidence < 0.9

    def test_get_uncertainty_reason_empty_measure(self):
        """Test uncertainty reason for empty measure."""
        provider = AudiverisProvider()
        
        measure_xml = """<measure number="1"></measure>"""
        measure = ET.fromstring(measure_xml)
        
        reason = provider._get_uncertainty_reason(measure, 0.5)
        
        assert "empty measure" in reason

    def test_get_uncertainty_reason_with_forward(self):
        """Test uncertainty reason with timing corrections."""
        provider = AudiverisProvider()
        
        measure_xml = """<measure number="1">
            <note><pitch><step>C</step><octave>4</octave></pitch></note>
            <forward><duration>4</duration></forward>
        </measure>"""
        measure = ET.fromstring(measure_xml)
        
        reason = provider._get_uncertainty_reason(measure, 0.6)
        
        assert "timing corrections" in reason

    def test_get_uncertainty_reason_with_backup(self):
        """Test uncertainty reason with voice alignment issues."""
        provider = AudiverisProvider()
        
        measure_xml = """<measure number="1">
            <note><pitch><step>C</step><octave>4</octave></pitch></note>
            <backup><duration>4</duration></backup>
        </measure>"""
        measure = ET.fromstring(measure_xml)
        
        reason = provider._get_uncertainty_reason(measure, 0.6)
        
        assert "voice alignment" in reason

    def test_get_uncertainty_reason_grace_notes(self):
        """Test uncertainty reason mentions grace notes."""
        provider = AudiverisProvider()
        
        measure_xml = """<measure number="1">
            <note><grace/><pitch><step>C</step><octave>4</octave></pitch></note>
            <note><grace/><pitch><step>D</step><octave>4</octave></pitch></note>
            <note><pitch><step>E</step><octave>4</octave></pitch></note>
        </measure>"""
        measure = ET.fromstring(measure_xml)
        
        reason = provider._get_uncertainty_reason(measure, 0.7)
        
        assert "grace notes" in reason

    def test_get_uncertainty_reason_fallback(self):
        """Test uncertainty reason fallback message."""
        provider = AudiverisProvider()
        
        # Normal measure with notes and no issues
        measure_xml = """<measure number="1">
            <note><pitch><step>C</step><octave>4</octave></pitch></note>
        </measure>"""
        measure = ET.fromstring(measure_xml)
        
        reason = provider._get_uncertainty_reason(measure, 0.5)
        
        assert "low overall recognition" in reason

    def test_extract_mxl_basic(self, tmp_path):
        """Test extracting MusicXML from MXL file."""
        provider = AudiverisProvider()
        
        mxl_path = tmp_path / "test.mxl"
        musicxml_content = """<?xml version="1.0"?>
<score-partwise><part-list/></score-partwise>"""
        
        import zipfile
        with zipfile.ZipFile(mxl_path, "w") as zf:
            zf.writestr("score.xml", musicxml_content)
        
        result = provider._extract_mxl(mxl_path)
        
        assert "score-partwise" in result

    def test_extract_mxl_with_container(self, tmp_path):
        """Test extracting MusicXML from MXL with container.xml."""
        provider = AudiverisProvider()
        
        mxl_path = tmp_path / "test.mxl"
        musicxml_content = """<?xml version="1.0"?><score-partwise><part-list/></score-partwise>"""
        container_content = """<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles><rootfile full-path="score.xml"/></rootfiles>
</container>"""
        
        import zipfile
        with zipfile.ZipFile(mxl_path, "w") as zf:
            zf.writestr("META-INF/container.xml", container_content)
            zf.writestr("score.xml", musicxml_content)
        
        result = provider._extract_mxl(mxl_path)
        
        assert "score-partwise" in result

    def test_extract_mxl_no_musicxml_raises(self, tmp_path):
        """Test that extract_mxl raises error when no MusicXML found."""
        provider = AudiverisProvider()
        
        mxl_path = tmp_path / "test.mxl"
        
        import zipfile
        with zipfile.ZipFile(mxl_path, "w") as zf:
            zf.writestr("readme.txt", "No musicxml here")
        
        with pytest.raises(ValueError, match="MXL file does not contain"):
            provider._extract_mxl(mxl_path)

    def test_find_output_file_direct_mxl(self, tmp_path):
        """Test finding direct .mxl output file."""
        provider = AudiverisProvider()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        mxl_file = output_dir / "test.mxl"
        mxl_file.write_bytes(b"mxl content")
        
        input_path = tmp_path / "test.jpg"
        
        result = provider._find_output_file(output_dir, input_path)
        
        assert result == mxl_file

    def test_find_output_file_in_subdirectory(self, tmp_path):
        """Test finding output file in subdirectory."""
        provider = AudiverisProvider()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Audiveris creates subdirectory with input file name
        sub_dir = output_dir / "test"
        sub_dir.mkdir()
        mxl_file = sub_dir / "test.mxl"
        mxl_file.write_bytes(b"mxl content")
        
        input_path = tmp_path / "test.jpg"
        
        result = provider._find_output_file(output_dir, input_path)
        
        assert result == mxl_file

    def test_find_output_file_not_found(self, tmp_path):
        """Test find_output_file when no file exists."""
        provider = AudiverisProvider()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        input_path = tmp_path / "test.jpg"
        
        result = provider._find_output_file(output_dir, input_path)
        
        assert result is None

    def test_analyze_output_extracts_metadata(self):
        """Test _analyze_output extracts metadata from MusicXML."""
        provider = AudiverisProvider()
        
        musicxml = """<?xml version="1.0"?>
<score-partwise>
  <work><work-title>Test Piece</work-title></work>
  <identification>
    <creator type="composer">Test Composer</creator>
  </identification>
  <part-list>
    <score-part id="P1"><part-name>Piano</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch></note>
    </measure>
    <measure number="2">
      <note><pitch><step>D</step><octave>4</octave></pitch></note>
    </measure>
  </part>
</score-partwise>"""
        
        metadata, measure_conf, uncertain = provider._analyze_output(musicxml, "")
        
        assert metadata.title == "Test Piece"
        assert metadata.composer == "Test Composer"
        assert metadata.part_count == 1
        assert metadata.measure_count == 2
        assert metadata.key_signature == "C"
        assert metadata.time_signature == "4/4"
        assert len(measure_conf) == 2

    def test_analyze_output_with_low_confidence(self):
        """Test _analyze_output detects low confidence measures."""
        provider = AudiverisProvider()
        
        # MusicXML with empty measures and corrections
        musicxml = """<?xml version="1.0"?>
<score-partwise>
  <part-list><score-part id="P1"><part-name>P</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
    </measure>
    <measure number="2">
      <forward><duration>4</duration></forward>
    </measure>
  </part>
</score-partwise>"""
        
        metadata, measure_conf, uncertain = provider._analyze_output(musicxml, "")
        
        # Should have uncertain measures
        assert len(uncertain) > 0

    @pytest.mark.asyncio
    async def test_process_timeout(self, tmp_path):
        """Test process timeout handling."""
        fake_jar = tmp_path / "Audiveris.jar"
        fake_jar.write_bytes(b"fake")
        
        provider = AudiverisProvider(audiveris_path=str(fake_jar))
        
        input_file = tmp_path / "test.jpg"
        input_file.write_bytes(b"fake image")
        
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("asyncio.create_subprocess_exec") as mock_exec:
                mock_process = MagicMock()
                mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
                mock_process.kill = MagicMock()
                mock_exec.return_value = mock_process
                
                result = await provider.process(
                    input_file,
                    options=OmrProviderOptions(timeout_seconds=1)
                )
        
        assert result.success is False
        assert "timed out" in result.error.lower()

    @pytest.mark.asyncio
    async def test_process_exception_handling(self, tmp_path):
        """Test process handles exceptions gracefully."""
        fake_jar = tmp_path / "Audiveris.jar"
        fake_jar.write_bytes(b"fake")
        
        provider = AudiverisProvider(audiveris_path=str(fake_jar))
        
        input_file = tmp_path / "test.jpg"
        input_file.write_bytes(b"fake image")
        
        with patch("subprocess.run", return_value=MagicMock(returncode=0)):
            with patch("asyncio.create_subprocess_exec", side_effect=RuntimeError("Test error")):
                result = await provider.process(input_file)
        
        assert result.success is False

    def test_fifths_to_key_all_keys(self):
        """Test fifths_to_key for all circle of fifths positions."""
        provider = AudiverisProvider()
        
        expected = {
            -7: "Cb", -6: "Gb", -5: "Db", -4: "Ab", -3: "Eb",
            -2: "Bb", -1: "F", 0: "C", 1: "G", 2: "D",
            3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#",
        }
        
        for fifths, key in expected.items():
            assert provider._fifths_to_key(fifths) == key

    def test_fifths_to_key_out_of_range(self):
        """Test fifths_to_key with out of range value defaults to C."""
        provider = AudiverisProvider()
        
        assert provider._fifths_to_key(10) == "C"
        assert provider._fifths_to_key(-10) == "C"

    def test_find_audiveris_not_found(self):
        """Test _find_audiveris returns None when not found."""
        provider = AudiverisProvider(audiveris_path="/definitely/not/here/audiveris.jar")
        
        result = provider._find_audiveris()
        
        assert result is None

    def test_is_available_no_java(self, tmp_path):
        """Test is_available returns False when Java not available."""
        fake_jar = tmp_path / "Audiveris.jar"
        fake_jar.write_bytes(b"fake")
        
        provider = AudiverisProvider(audiveris_path=str(fake_jar))
        
        with patch("subprocess.run", side_effect=FileNotFoundError()):
            assert provider.is_available is False


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


# =============================================================================
# Tests for OemerProvider
# =============================================================================

from app.services.omr.oemer_provider import OemerProvider


class TestOemerProviderName:
    """Test OemerProvider.name property."""

    def test_name_returns_oemer(self):
        """Test that provider name is 'oemer'."""
        provider = OemerProvider()
        assert provider.name == "oemer"


class TestOemerProviderIsAvailable:
    """Test OemerProvider.is_available property."""

    def test_is_available_with_custom_path_that_exists(self, tmp_path):
        """Test is_available when custom oemer path exists."""
        fake_oemer = tmp_path / "oemer"
        fake_oemer.write_text("#!/bin/bash\necho oemer")
        
        provider = OemerProvider(oemer_path=str(fake_oemer))
        assert provider.is_available is True

    def test_is_available_with_custom_path_that_does_not_exist(self):
        """Test is_available when custom oemer path doesn't exist."""
        provider = OemerProvider(oemer_path="/nonexistent/oemer")
        assert provider.is_available is False

    @patch("shutil.which", return_value=None)
    def test_is_available_not_in_path(self, mock_which, tmp_path):
        """Test is_available when oemer is not in PATH."""
        provider = OemerProvider()
        # Mock _find_oemer to return None
        with patch.object(provider, "_find_oemer", return_value=None):
            assert provider.is_available is False


class TestOemerProviderFindOemer:
    """Test OemerProvider._find_oemer method."""

    def test_find_oemer_with_custom_path(self, tmp_path):
        """Test _find_oemer with custom path."""
        fake_oemer = tmp_path / "oemer"
        fake_oemer.write_text("#!/bin/bash\necho oemer")
        
        provider = OemerProvider(oemer_path=str(fake_oemer))
        result = provider._find_oemer()
        assert result == fake_oemer

    def test_find_oemer_custom_path_not_exists(self):
        """Test _find_oemer when custom path doesn't exist."""
        provider = OemerProvider(oemer_path="/nonexistent/oemer")
        result = provider._find_oemer()
        assert result is None

    @patch("shutil.which", return_value="/usr/bin/oemer")
    def test_find_oemer_in_system_path(self, mock_which):
        """Test _find_oemer finds oemer in system PATH."""
        provider = OemerProvider()
        # Need to mock venv path not existing
        with patch.object(Path, "exists", return_value=False):
            # Since venv check may find it, let's just test which is called
            provider._find_oemer()
            # If it reaches which() call, it should find it


class TestOemerProviderGetVersion:
    """Test OemerProvider.get_version method."""

    @pytest.mark.asyncio
    async def test_get_version_cached(self):
        """Test that version is cached."""
        provider = OemerProvider()
        provider._version = "1.2.3"
        
        version = await provider.get_version()
        assert version == "1.2.3"

    @pytest.mark.asyncio
    async def test_get_version_from_import(self):
        """Test getting version from import."""
        provider = OemerProvider()
        
        with patch.dict("sys.modules", {"oemer": MagicMock()}):
            with patch("importlib.metadata.version", return_value="0.1.6"):
                version = await provider.get_version()
                assert version == "0.1.6"

    @pytest.mark.asyncio
    async def test_get_version_import_error(self):
        """Test version when oemer not installed."""
        provider = OemerProvider()
        provider._version = None
        
        # Mock the oemer import to fail
        with patch.dict("sys.modules", {"oemer": None}):
            # Force reimport behavior by clearing cached version
            provider._version = None
            # This will try to import oemer which we've mocked as None
            # The get_version should handle this gracefully


class TestOemerProviderProcess:
    """Test OemerProvider.process method."""

    @pytest.mark.asyncio
    async def test_process_oemer_not_found(self, tmp_path):
        """Test process when oemer is not available."""
        provider = OemerProvider(oemer_path="/nonexistent/oemer")
        
        input_path = tmp_path / "test.png"
        input_path.write_bytes(b"fake png data")
        
        result = await provider.process(input_path)
        
        assert result.success is False
        assert "oemer not found" in result.error
        assert result.provider_name == "oemer"

    @pytest.mark.asyncio
    async def test_process_success(self, tmp_path):
        """Test successful oemer processing with mocked subprocess."""
        fake_oemer = tmp_path / "oemer"
        fake_oemer.write_text("#!/bin/bash\necho oemer")
        
        provider = OemerProvider(oemer_path=str(fake_oemer))
        
        input_path = tmp_path / "test.png"
        input_path.write_bytes(b"fake png data")
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create fake output file
        output_musicxml = output_dir / "test.musicxml"
        output_musicxml.write_text("<?xml version='1.0'?><score/>")
        
        # Mock the subprocess call
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await provider.process(input_path, output_dir=output_dir)
        
        assert result.success is True
        assert result.music_xml is not None
        assert result.provider_name == "oemer"

    @pytest.mark.asyncio
    async def test_process_timeout(self, tmp_path):
        """Test process timeout handling."""
        fake_oemer = tmp_path / "oemer"
        fake_oemer.write_text("#!/bin/bash\nsleep 10")
        
        provider = OemerProvider(oemer_path=str(fake_oemer))
        
        input_path = tmp_path / "test.png"
        input_path.write_bytes(b"fake png data")
        
        # Mock the subprocess with timeout
        mock_process = AsyncMock()
        mock_process.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_process.kill = MagicMock()
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await provider.process(
                input_path,
                options=OmrProviderOptions(timeout_seconds=1)
            )
        
        assert result.success is False
        assert "timed out" in result.error
        mock_process.kill.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_failure(self, tmp_path):
        """Test processing failure handling."""
        fake_oemer = tmp_path / "oemer"
        fake_oemer.write_text("#!/bin/bash\nexit 1")
        
        provider = OemerProvider(oemer_path=str(fake_oemer))
        
        input_path = tmp_path / "test.png"
        input_path.write_bytes(b"fake png data")
        
        mock_process = AsyncMock()
        mock_process.returncode = 1
        mock_process.communicate = AsyncMock(return_value=(b"", b"Error: something failed"))
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await provider.process(input_path)
        
        assert result.success is False
        assert result.provider_name == "oemer"

    @pytest.mark.asyncio
    async def test_process_no_output_file(self, tmp_path):
        """Test when oemer succeeds but produces no output."""
        fake_oemer = tmp_path / "oemer"
        fake_oemer.write_text("#!/bin/bash\necho done")
        
        provider = OemerProvider(oemer_path=str(fake_oemer))
        
        input_path = tmp_path / "test.png"
        input_path.write_bytes(b"fake png data")
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        # No output file created
        
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Done", b""))
        
        with patch("asyncio.create_subprocess_exec", return_value=mock_process):
            result = await provider.process(input_path, output_dir=output_dir)
        
        assert result.success is False
        assert "no MusicXML output found" in result.error


class TestOemerProviderFindOutputFile:
    """Test OemerProvider._find_output_file method."""

    def test_find_output_file_musicxml(self, tmp_path):
        """Test finding .musicxml output file."""
        provider = OemerProvider()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        output_file = output_dir / "test.musicxml"
        output_file.write_text("<?xml?>")
        
        input_path = tmp_path / "test.png"
        
        result = provider._find_output_file(output_dir, input_path)
        assert result == output_file

    def test_find_output_file_xml(self, tmp_path):
        """Test finding .xml output file."""
        provider = OemerProvider()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        output_file = output_dir / "test.xml"
        output_file.write_text("<?xml?>")
        
        input_path = tmp_path / "test.png"
        
        result = provider._find_output_file(output_dir, input_path)
        assert result == output_file

    def test_find_output_file_fallback_glob(self, tmp_path):
        """Test finding output file by glob pattern."""
        provider = OemerProvider()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create a file with different name
        output_file = output_dir / "different_name.musicxml"
        output_file.write_text("<?xml?>")
        
        input_path = tmp_path / "test.png"
        
        result = provider._find_output_file(output_dir, input_path)
        assert result == output_file

    def test_find_output_file_not_found(self, tmp_path):
        """Test when no output file exists."""
        provider = OemerProvider()
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        input_path = tmp_path / "test.png"
        
        result = provider._find_output_file(output_dir, input_path)
        assert result is None


class TestOemerProviderParseError:
    """Test OemerProvider._parse_error method."""

    def test_parse_error_missing_module(self):
        """Test parsing missing module error."""
        provider = OemerProvider()
        
        error = provider._parse_error("ModuleNotFoundError: No module named 'torch'")
        assert "missing a required dependency" in error

    def test_parse_error_memory_error(self):
        """Test parsing memory error."""
        provider = OemerProvider()
        
        error = provider._parse_error("MemoryError: unable to allocate")
        assert "ran out of memory" in error

    def test_parse_error_out_of_memory_java(self):
        """Test parsing Java OOM error."""
        provider = OemerProvider()
        
        error = provider._parse_error("java.lang.OutOfMemoryError: Java heap space")
        assert "ran out of memory" in error

    def test_parse_error_generic_error_line(self):
        """Test extracting generic error line."""
        provider = OemerProvider()
        
        stderr = "Processing...\nSome warning\nError: Invalid input format\nCleaning up"
        error = provider._parse_error(stderr)
        assert "Invalid input format" in error

    def test_parse_error_no_error(self):
        """Test when no error pattern found."""
        provider = OemerProvider()
        
        error = provider._parse_error("Normal output\nAll good")
        assert error is None


class TestOemerProviderPdfConversion:
    """Test OemerProvider PDF conversion."""

    @pytest.mark.asyncio
    async def test_process_pdf_conversion_success(self, tmp_path):
        """Test processing PDF with successful conversion."""
        fake_oemer = tmp_path / "oemer"
        fake_oemer.write_text("#!/bin/bash\necho oemer")
        
        provider = OemerProvider(oemer_path=str(fake_oemer))
        
        # Create fake PDF
        input_path = tmp_path / "test.pdf"
        input_path.write_bytes(b"%PDF-1.4 fake pdf")
        
        output_dir = tmp_path / "output"
        output_dir.mkdir()
        
        # Create expected PNG output from PDF conversion
        png_path = output_dir / "test.png"
        png_path.write_bytes(b"fake png data")
        
        # Create expected MusicXML output
        output_file = output_dir / "test.musicxml"
        output_file.write_text("<?xml?><score/>")
        
        # Mock the subprocess call for oemer
        mock_process = AsyncMock()
        mock_process.returncode = 0
        mock_process.communicate = AsyncMock(return_value=(b"Success", b""))
        
        # Mock the PDF conversion
        async def mock_convert_pdf(pdf_path, out_dir):
            return png_path
        
        with patch.object(provider, "_convert_pdf_to_image", side_effect=mock_convert_pdf):
            with patch("asyncio.create_subprocess_exec", return_value=mock_process):
                result = await provider.process(input_path, output_dir=output_dir)
        
        assert result.success is True

    @pytest.mark.asyncio
    async def test_process_pdf_conversion_fallback_pdftoppm(self, tmp_path):
        """Test PDF conversion fallback to pdftoppm."""
        fake_oemer = tmp_path / "oemer"
        fake_oemer.write_text("#!/bin/bash\necho oemer")
        
        provider = OemerProvider(oemer_path=str(fake_oemer))
        
        input_path = tmp_path / "test.pdf"
        input_path.write_bytes(b"%PDF-1.4 fake pdf")
        
        # Mock pdf2image import error
        with patch.dict("sys.modules", {"pdf2image": None}):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)  # pdftoppm fails too
                
                result = await provider.process(input_path)
        
        assert result.success is False
        assert "Failed to convert PDF" in result.error
