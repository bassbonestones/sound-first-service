"""Audiveris OMR provider.

Runs Audiveris as a subprocess for optical music recognition.
Audiveris is an open-source OMR engine written in Java.

Requirements:
- Java 17+ runtime
- Audiveris JAR file (downloaded automatically or manually)

See: https://github.com/Audiveris/audiveris
"""

import asyncio
import logging
import os
import re
import shutil
import subprocess
import tempfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional, Tuple

from .base import (
    OmrProvider,
    OmrProviderOptions,
    OmrProviderResult,
    MeasureConfidenceResult,
    UncertainMeasureResult,
    ExtractedMetadataResult,
)

logger = logging.getLogger(__name__)


class AudiverisProvider(OmrProvider):
    """Audiveris OMR provider using subprocess execution.

    Runs Audiveris CLI to process images/PDFs and extract MusicXML.
    """

    # Default paths to look for Audiveris
    DEFAULT_AUDIVERIS_PATHS = [
        "/usr/local/bin/audiveris",
        "/opt/audiveris/bin/audiveris",
        "~/audiveris/bin/audiveris",
        # JAR file locations
        "/opt/audiveris/Audiveris.jar",
        "~/audiveris/Audiveris.jar",
        "./tools/audiveris/Audiveris.jar",
    ]

    # Minimum confidence to pass without flagging
    CONFIDENCE_THRESHOLD = 0.75

    def __init__(
        self,
        audiveris_path: Optional[str] = None,
        java_path: str = "java",
        java_opts: Optional[list] = None,
    ):
        """Initialize Audiveris provider.

        Args:
            audiveris_path: Path to Audiveris executable or JAR.
                          Auto-detected if None.
            java_path: Path to Java executable (default: 'java')
            java_opts: Additional JVM options (e.g., ['-Xmx4g'])
        """
        self._audiveris_path = audiveris_path
        self._java_path = java_path
        self._java_opts = java_opts or ["-Xmx2g"]
        self._version: Optional[str] = None
        self._is_jar: bool = False

    @property
    def name(self) -> str:
        return "audiveris"

    @property
    def is_available(self) -> bool:
        """Check if Audiveris is available."""
        path = self._find_audiveris()
        if path is None:
            return False

        # Also check Java is available
        try:
            result = subprocess.run(
                [self._java_path, "-version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _find_audiveris(self) -> Optional[Path]:
        """Find Audiveris executable or JAR file."""
        if self._audiveris_path:
            path = Path(self._audiveris_path).expanduser()
            if path.exists():
                self._is_jar = path.suffix.lower() == ".jar"
                return path
            return None

        # Search default locations
        for default_path in self.DEFAULT_AUDIVERIS_PATHS:
            path = Path(default_path).expanduser()
            if path.exists():
                self._is_jar = path.suffix.lower() == ".jar"
                return path

        # Check if 'audiveris' is in PATH
        audiveris_in_path = shutil.which("audiveris")
        if audiveris_in_path:
            return Path(audiveris_in_path)

        return None

    async def get_version(self) -> Optional[str]:
        """Get Audiveris version string."""
        if self._version:
            return self._version

        path = self._find_audiveris()
        if not path:
            return None

        try:
            cmd = self._build_command(path, ["-help"])
            result = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                result.communicate(), timeout=30
            )

            # Parse version from output
            output = stdout.decode() + stderr.decode()
            version_match = re.search(r"Audiveris\s+(\d+\.\d+\.\d+)", output)
            if version_match:
                self._version = version_match.group(1)
            else:
                self._version = "unknown"

            return self._version
        except Exception as e:
            logger.error(f"Failed to get Audiveris version: {e}")
            return None

    def _build_command(self, audiveris_path: Path, args: list) -> list:
        """Build command to run Audiveris."""
        if self._is_jar:
            # Running as JAR file
            cmd = [self._java_path] + self._java_opts + ["-jar", str(audiveris_path)]
        else:
            # Running as executable script
            cmd = [str(audiveris_path)]
        return cmd + args

    async def process(
        self,
        input_path: Path,
        options: Optional[OmrProviderOptions] = None,
        output_dir: Optional[Path] = None,
    ) -> OmrProviderResult:
        """Process an image/PDF with Audiveris.

        Args:
            input_path: Path to input image or PDF
            options: Processing options
            output_dir: Output directory (temp if None)

        Returns:
            OmrProviderResult with recognition results
        """
        start_time = time.time()
        options = options or self.get_default_options()

        # Find Audiveris
        audiveris_path = self._find_audiveris()
        if not audiveris_path:
            return OmrProviderResult(
                success=False,
                error="Audiveris not found. Install it or set audiveris_path.",
                processing_time_ms=0,
                provider_name=self.name,
            )

        # Validate input
        if not input_path.exists():
            return OmrProviderResult(
                success=False,
                error=f"Input file not found: {input_path}",
                processing_time_ms=0,
                provider_name=self.name,
            )

        # Create output directory
        temp_dir = None
        if output_dir is None:
            temp_dir = tempfile.mkdtemp(prefix="audiveris_")
            output_dir = Path(temp_dir)
        else:
            output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Run Audiveris
            result = await self._run_audiveris(
                audiveris_path, input_path, output_dir, options
            )

            processing_time_ms = int((time.time() - start_time) * 1000)
            result.processing_time_ms = processing_time_ms

            return result

        except asyncio.TimeoutError:
            processing_time_ms = int((time.time() - start_time) * 1000)
            return OmrProviderResult(
                success=False,
                error=f"Audiveris timed out after {options.timeout_seconds}s",
                processing_time_ms=processing_time_ms,
                provider_name=self.name,
            )
        except Exception as e:
            processing_time_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Audiveris processing failed: {e}")
            return OmrProviderResult(
                success=False,
                error=str(e),
                processing_time_ms=processing_time_ms,
                provider_name=self.name,
            )
        finally:
            # Clean up temp directory if we created one
            if temp_dir and not output_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

    async def _run_audiveris(
        self,
        audiveris_path: Path,
        input_path: Path,
        output_dir: Path,
        options: OmrProviderOptions,
    ) -> OmrProviderResult:
        """Execute Audiveris and parse results."""

        # Build Audiveris command
        # -batch: Run without GUI
        # -export: Export to MusicXML
        # -output: Output directory
        args = [
            "-batch",
            "-export",
            "-output", str(output_dir),
            str(input_path),
        ]

        cmd = self._build_command(audiveris_path, args)
        logger.info(f"Running Audiveris: {' '.join(cmd)}")

        # Run Audiveris
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ, "AUDIVERIS_BATCH": "true"},
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(),
            timeout=options.timeout_seconds,
        )

        stdout_str = stdout.decode("utf-8", errors="replace")
        stderr_str = stderr.decode("utf-8", errors="replace")
        raw_output = f"STDOUT:\n{stdout_str}\nSTDERR:\n{stderr_str}"

        # Check for errors
        if process.returncode != 0:
            error_msg = self._parse_error(stderr_str) or f"Audiveris failed with code {process.returncode}"
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
                error="Audiveris completed but no MusicXML output found",
                provider_name=self.name,
                raw_output=raw_output,
            )

        # Read and parse MusicXML
        music_xml = musicxml_path.read_text(encoding="utf-8")

        # Extract metadata and confidence
        metadata, measure_confidence, uncertain_measures = self._analyze_output(
            music_xml, stdout_str
        )

        # Calculate overall confidence
        if measure_confidence:
            overall_confidence = sum(m.confidence for m in measure_confidence) / len(
                measure_confidence
            )
        else:
            overall_confidence = 0.8  # Default if we can't calculate

        return OmrProviderResult(
            success=True,
            confidence=overall_confidence,
            music_xml=music_xml,
            output_path=musicxml_path,
            measure_confidence=measure_confidence,
            uncertain_measures=uncertain_measures,
            metadata=metadata,
            provider_name=self.name,
            raw_output=raw_output,
        )

    def _find_output_file(self, output_dir: Path, input_path: Path) -> Optional[Path]:
        """Find the MusicXML output file."""
        # Audiveris creates a directory with the input filename
        base_name = input_path.stem

        # Look for .mxl or .xml files
        possible_paths = [
            output_dir / base_name / f"{base_name}.mxl",
            output_dir / base_name / f"{base_name}.xml",
            output_dir / f"{base_name}.mxl",
            output_dir / f"{base_name}.xml",
        ]

        for path in possible_paths:
            if path.exists():
                return path

        # Search for any .mxl or .xml file
        for pattern in ["**/*.mxl", "**/*.xml"]:
            files = list(output_dir.glob(pattern))
            if files:
                return files[0]

        return None

    def _parse_error(self, stderr: str) -> Optional[str]:
        """Extract meaningful error message from stderr."""
        # Look for common Audiveris errors
        if "OutOfMemoryError" in stderr:
            return "Audiveris ran out of memory. Try increasing -Xmx."
        if "No sheet" in stderr:
            return "Could not detect any sheet music in the image."
        if "IOException" in stderr:
            return "Failed to read or write files."

        # Extract first meaningful error line
        for line in stderr.split("\n"):
            if "ERROR" in line or "Exception" in line:
                return line.strip()

        return None

    def _analyze_output(
        self, music_xml: str, stdout: str
    ) -> Tuple[
        ExtractedMetadataResult,
        list[MeasureConfidenceResult],
        list[UncertainMeasureResult],
    ]:
        """Analyze MusicXML output and Audiveris logs for quality metrics."""

        metadata = ExtractedMetadataResult()
        measure_confidence: list[MeasureConfidenceResult] = []
        uncertain_measures: list[UncertainMeasureResult] = []

        try:
            root = ET.fromstring(music_xml)

            # Extract metadata
            work_title = root.find(".//work-title")
            if work_title is not None and work_title.text:
                metadata.title = work_title.text

            composer = root.find(".//creator[@type='composer']")
            if composer is not None and composer.text:
                metadata.composer = composer.text

            # Count parts
            parts = root.findall(".//part")
            metadata.part_count = len(parts)

            # Count measures and analyze confidence
            measure_count = 0
            for part_idx, part in enumerate(parts):
                measures = part.findall("measure")
                for measure in measures:
                    measure_num = int(measure.get("number", measure_count + 1))
                    measure_count = max(measure_count, measure_num)

                    # Estimate confidence based on content
                    # (Audiveris doesn't provide direct confidence scores)
                    confidence = self._estimate_measure_confidence(measure)

                    measure_confidence.append(
                        MeasureConfidenceResult(
                            measure_number=measure_num,
                            part_index=part_idx,
                            confidence=confidence,
                        )
                    )

                    if confidence < self.CONFIDENCE_THRESHOLD:
                        uncertain_measures.append(
                            UncertainMeasureResult(
                                measure_number=measure_num,
                                part_index=part_idx,
                                confidence=confidence,
                                reason=self._get_uncertainty_reason(measure, confidence),
                            )
                        )

            metadata.measure_count = measure_count

            # Extract key and time signature from first measure
            first_measure = root.find(".//measure")
            if first_measure is not None:
                key = first_measure.find(".//key/fifths")
                if key is not None and key.text:
                    metadata.key_signature = self._fifths_to_key(int(key.text))

                time_beats = first_measure.find(".//time/beats")
                time_type = first_measure.find(".//time/beat-type")
                if time_beats is not None and time_type is not None:
                    metadata.time_signature = f"{time_beats.text}/{time_type.text}"

        except ET.ParseError as e:
            logger.warning(f"Failed to parse MusicXML for analysis: {e}")

        return metadata, measure_confidence, uncertain_measures

    def _estimate_measure_confidence(self, measure: ET.Element) -> float:
        """Estimate confidence for a measure based on content analysis.

        Since Audiveris doesn't provide direct confidence scores,
        we infer quality from structural indicators:
        - Presence of notes
        - Consistent note durations
        - No forward/backup elements (which indicate corrections)
        """
        confidence = 0.9  # Start with high confidence

        notes = measure.findall("note")
        if not notes:
            confidence -= 0.2  # Empty measure is suspicious

        # Check for forward/backup (often indicates Audiveris corrections)
        if measure.find("forward") is not None or measure.find("backup") is not None:
            confidence -= 0.15

        # Check for grace notes or complex notation (harder to recognize)
        for note in notes:
            if note.find("grace") is not None:
                confidence -= 0.05
            if note.find("chord") is not None:
                confidence -= 0.02

        return max(0.0, min(1.0, confidence))

    def _get_uncertainty_reason(self, measure: ET.Element, confidence: float) -> str:
        """Generate a human-readable reason for low confidence."""
        reasons = []

        if not measure.findall("note"):
            reasons.append("empty measure")
        if measure.find("forward") is not None:
            reasons.append("timing corrections detected")
        if measure.find("backup") is not None:
            reasons.append("voice alignment issues")

        grace_notes = measure.findall(".//grace")
        if grace_notes:
            reasons.append(f"{len(grace_notes)} grace notes")

        if not reasons:
            reasons.append("low overall recognition quality")

        return "; ".join(reasons)

    def _fifths_to_key(self, fifths: int) -> str:
        """Convert circle of fifths position to key name."""
        keys = {
            -7: "Cb", -6: "Gb", -5: "Db", -4: "Ab", -3: "Eb",
            -2: "Bb", -1: "F", 0: "C", 1: "G", 2: "D",
            3: "A", 4: "E", 5: "B", 6: "F#", 7: "C#",
        }
        return keys.get(fifths, "C")

    def get_default_options(self) -> OmrProviderOptions:
        """Return Audiveris-optimized default options."""
        return OmrProviderOptions(
            enhance_image=True,
            detect_parts=True,
            generate_preview=False,  # Audiveris doesn't generate previews by default
            output_format="musicxml",
            timeout_seconds=300,  # 5 minutes max per job
        )
