"""Oemer OMR provider.

Uses oemer (OpenCV-based End-to-end Music Recognition) for optical music recognition.
oemer is a Python-native neural network based OMR engine.

Requirements:
- oemer package (pip install oemer)

See: https://github.com/BreezeWhite/oemer
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from .base import (
    OmrProvider,
    OmrProviderOptions,
    OmrProviderResult,
    MeasureConfidenceResult,
    UncertainMeasureResult,
    ExtractedMetadataResult,
)

logger = logging.getLogger(__name__)


class OemerProvider(OmrProvider):
    """Oemer OMR provider using subprocess execution.

    Uses the oemer CLI to process images and output MusicXML.
    """

    def __init__(
        self,
        oemer_path: Optional[str] = None,
    ):
        """Initialize Oemer provider.

        Args:
            oemer_path: Path to oemer executable. Auto-detected if None.
        """
        self._oemer_path = oemer_path
        self._version: Optional[str] = None

    @property
    def name(self) -> str:
        return "oemer"

    @property
    def is_available(self) -> bool:
        """Check if oemer is available."""
        path = self._find_oemer()
        return path is not None

    def _find_oemer(self) -> Optional[Path]:
        """Find oemer executable."""
        if self._oemer_path:
            path = Path(self._oemer_path)
            if path.exists():
                return path
            return None

        # Check in venv bin directory (typical installation)
        venv_oemer = Path(__file__).parent.parent.parent.parent / "venv" / "bin" / "oemer"
        if venv_oemer.exists():
            return venv_oemer

        # Check if oemer is in PATH
        import shutil
        oemer_in_path = shutil.which("oemer")
        if oemer_in_path:
            return Path(oemer_in_path)

        return None

    async def get_version(self) -> Optional[str]:
        """Get oemer version string."""
        if self._version:
            return self._version

        try:
            import oemer
            # oemer doesn't have __version__, check package metadata
            try:
                from importlib.metadata import version
                self._version = version("oemer")
            except Exception:
                self._version = "unknown"
            return self._version
        except ImportError:
            return None

    async def process(
        self,
        input_path: Path,
        options: Optional[OmrProviderOptions] = None,
        output_dir: Optional[Path] = None,
    ) -> OmrProviderResult:
        """Process an image with oemer.

        Args:
            input_path: Path to input image (PNG, JPG) or PDF
            options: Processing options
            output_dir: Output directory (temp if None)

        Returns:
            OmrProviderResult with recognition results
        """
        options = options or OmrProviderOptions()
        start_time = time.time()

        oemer_path = self._find_oemer()
        if not oemer_path:
            return OmrProviderResult(
                success=False,
                error="oemer not found. Install it with: pip install oemer",
                provider_name=self.name,
            )

        # Create temp output dir if not provided
        if output_dir is None:
            output_dir = Path(tempfile.mkdtemp(prefix="oemer_"))

        # Convert PDF to image if needed
        actual_input = input_path
        if input_path.suffix.lower() == ".pdf":
            actual_input = await self._convert_pdf_to_image(input_path, output_dir)
            if actual_input is None:
                return OmrProviderResult(
                    success=False,
                    error="Failed to convert PDF to image",
                    provider_name=self.name,
                )

        try:
            result = await self._run_oemer(
                oemer_path, actual_input, output_dir, options
            )
            result.processing_time_ms = int((time.time() - start_time) * 1000)
            return result
        except Exception as e:
            logger.exception("oemer processing failed")
            return OmrProviderResult(
                success=False,
                error=str(e),
                provider_name=self.name,
            )

    async def _convert_pdf_to_image(
        self, pdf_path: Path, output_dir: Path
    ) -> Optional[Path]:
        """Convert PDF to PNG image for oemer processing."""
        try:
            # Use pdf2image or poppler
            from pdf2image import convert_from_path
            images = convert_from_path(pdf_path, dpi=300, first_page=1, last_page=1)
            if images:
                output_path = output_dir / f"{pdf_path.stem}.png"
                images[0].save(output_path, "PNG")
                return output_path
        except ImportError:
            logger.warning("pdf2image not installed, trying pdftoppm")
            # Fallback to pdftoppm CLI
            output_prefix = output_dir / pdf_path.stem
            try:
                result = subprocess.run(
                    ["pdftoppm", "-png", "-r", "300", "-singlefile", str(pdf_path), str(output_prefix)],
                    capture_output=True,
                    timeout=60,
                )
                if result.returncode == 0:
                    output_path = Path(f"{output_prefix}.png")
                    if output_path.exists():
                        return output_path
            except Exception as e:
                logger.error(f"pdftoppm failed: {e}")
        except Exception as e:
            logger.error(f"PDF conversion failed: {e}")
        
        return None

    async def _run_oemer(
        self,
        oemer_path: Path,
        input_path: Path,
        output_dir: Path,
        options: OmrProviderOptions,
    ) -> OmrProviderResult:
        """Run oemer CLI."""
        # Build command
        cmd = [
            str(oemer_path),
            "-o", str(output_dir),
            str(input_path),
        ]

        logger.info(f"Running oemer: {' '.join(cmd)}")

        # Run oemer
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(output_dir),
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=options.timeout_seconds or 300,  # 5 min default
            )
        except asyncio.TimeoutError:
            process.kill()
            return OmrProviderResult(
                success=False,
                error="oemer timed out",
                provider_name=self.name,
            )

        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        raw_output = f"STDOUT:\n{stdout_str}\n\nSTDERR:\n{stderr_str}"

        if process.returncode != 0:
            error_msg = self._parse_error(stderr_str) or f"oemer failed with code {process.returncode}"
            return OmrProviderResult(
                success=False,
                error=error_msg,
                provider_name=self.name,
                raw_output=raw_output,
            )

        # Find output MusicXML file
        musicxml_path = self._find_output_file(output_dir, input_path)
        if not musicxml_path:
            return OmrProviderResult(
                success=False,
                error="oemer completed but no MusicXML output found",
                provider_name=self.name,
                raw_output=raw_output,
            )

        # Read MusicXML
        try:
            music_xml = musicxml_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            music_xml = musicxml_path.read_text(encoding="latin-1")

        # oemer doesn't provide confidence scores, use default
        return OmrProviderResult(
            success=True,
            confidence=0.85,  # Default confidence for oemer
            music_xml=music_xml,
            output_path=musicxml_path,
            measure_confidence=[],
            uncertain_measures=[],
            metadata=ExtractedMetadataResult(),
            provider_name=self.name,
            raw_output=raw_output,
        )

    def _find_output_file(self, output_dir: Path, input_path: Path) -> Optional[Path]:
        """Find the MusicXML output file."""
        base_name = input_path.stem

        # oemer outputs to <input_name>.musicxml
        possible_paths = [
            output_dir / f"{base_name}.musicxml",
            output_dir / f"{base_name}.xml",
            output_dir / f"{base_name}.mxl",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # Search for any musicxml file
        for pattern in ["*.musicxml", "*.xml", "*.mxl"]:
            files = list(output_dir.glob(pattern))
            if files:
                return files[0]

        return None

    def _parse_error(self, stderr: str) -> Optional[str]:
        """Extract meaningful error message from stderr."""
        if "No module named" in stderr:
            return "oemer is missing a required dependency"
        if "OutOfMemoryError" in stderr or "MemoryError" in stderr:
            return "oemer ran out of memory"

        # Extract first error line
        for line in stderr.split("\n"):
            if "error" in line.lower() or "exception" in line.lower():
                return line.strip()

        return None
