"""Mock OMR provider for testing.

Returns instant results with configurable behavior,
useful for unit tests and development without Audiveris.
"""

import asyncio
import time
from pathlib import Path
from typing import Optional

from .base import (
    OmrProvider,
    OmrProviderOptions,
    OmrProviderResult,
    MeasureConfidenceResult,
    ExtractedMetadataResult,
)


class MockOmrProvider(OmrProvider):
    """Mock OMR provider that returns configurable test results.

    Useful for:
    - Unit tests (instant, deterministic results)
    - Development without Audiveris installed
    - UI testing with various result states
    """

    def __init__(
        self,
        *,
        simulate_delay_ms: int = 0,
        success: bool = True,
        confidence: float = 0.85,
        error_message: Optional[str] = None,
    ):
        """Initialize mock provider.

        Args:
            simulate_delay_ms: Artificial delay to simulate processing
            success: Whether processing should succeed
            confidence: Confidence score to return
            error_message: Error message if success=False
        """
        self._simulate_delay_ms = simulate_delay_ms
        self._success = success
        self._confidence = confidence
        self._error_message = error_message

    @property
    def name(self) -> str:
        return "mock"

    @property
    def is_available(self) -> bool:
        return True  # Always available

    async def get_version(self) -> Optional[str]:
        return "mock-1.0.0"

    async def process(
        self,
        input_path: Path,
        options: Optional[OmrProviderOptions] = None,
        output_dir: Optional[Path] = None,
    ) -> OmrProviderResult:
        """Return mock OMR results.

        Simulates processing with configurable delay and results.
        """
        start_time = time.time()
        options = options or self.get_default_options()

        # Simulate processing time
        if self._simulate_delay_ms > 0:
            await asyncio.sleep(self._simulate_delay_ms / 1000)

        processing_time_ms = int((time.time() - start_time) * 1000)

        # Return error if configured to fail
        if not self._success:
            return OmrProviderResult(
                success=False,
                error=self._error_message or "Mock processing failed",
                processing_time_ms=processing_time_ms,
                provider_name=self.name,
            )

        # Generate mock MusicXML
        mock_musicxml = self._generate_mock_musicxml(input_path.stem)

        # Generate mock metadata
        metadata = ExtractedMetadataResult(
            title=f"Imported: {input_path.stem}",
            composer=None,
            key_signature="C",
            time_signature="4/4",
            tempo=120,
            measure_count=4,
            part_count=1,
            page_count=1,
        )

        # Generate mock measure confidence
        measure_confidence = [
            MeasureConfidenceResult(
                measure_number=i + 1,
                part_index=0,
                confidence=self._confidence - (0.02 * i),  # Slight variation
            )
            for i in range(4)
        ]

        return OmrProviderResult(
            success=True,
            confidence=self._confidence,
            music_xml=mock_musicxml,
            measure_confidence=measure_confidence,
            uncertain_measures=[],  # No uncertain measures in mock
            metadata=metadata,
            processing_time_ms=processing_time_ms,
            provider_name=self.name,
        )

    def _generate_mock_musicxml(self, title: str) -> str:
        """Generate a simple mock MusicXML document."""
        return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"
    "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work>
    <work-title>{title}</work-title>
  </work>
  <identification>
    <creator type="composer">Unknown</creator>
    <encoding>
      <software>Sound First Mock OMR</software>
      <encoding-date>2026-03-17</encoding-date>
    </encoding>
  </identification>
  <part-list>
    <score-part id="P1">
      <part-name>Piano</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
    </measure>
    <measure number="2">
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
    </measure>
    <measure number="3">
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>2</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>half</type>
      </note>
    </measure>
    <measure number="4">
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>whole</type>
      </note>
      <barline location="right">
        <bar-style>light-heavy</bar-style>
      </barline>
    </measure>
  </part>
</score-partwise>'''
