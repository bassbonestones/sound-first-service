"""Base OMR provider interface and types.

Defines the abstract interface that all OMR providers must implement,
ensuring a consistent API regardless of the underlying OMR engine.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import List, Optional


class OmrProviderType(str, Enum):
    """Available OMR provider types."""

    MOCK = "mock"
    AUDIVERIS = "audiveris"
    OEMER = "oemer"
    COMMERCIAL = "commercial"


@dataclass
class OmrProviderOptions:
    """Options for OMR processing.

    These options are provider-agnostic and will be translated
    to provider-specific settings as needed.
    """

    language: str = "en"
    """Hint for text recognition (titles, lyrics, etc.)."""

    enhance_image: bool = True
    """Apply preprocessing to improve recognition."""

    detect_parts: bool = True
    """Attempt to detect and separate multiple parts/staves."""

    generate_preview: bool = True
    """Generate a preview image of the recognized score."""

    output_format: str = "musicxml"
    """Output format: 'musicxml', 'mxl', or 'mei'."""

    # Advanced options
    staff_line_height: Optional[int] = None
    """Expected staff line height in pixels (auto-detect if None)."""

    max_pages: Optional[int] = None
    """Maximum pages to process (None = all)."""

    timeout_seconds: int = 300
    """Maximum processing time per page."""


@dataclass
class MeasureConfidenceResult:
    """Confidence score for a single measure."""

    measure_number: int
    part_index: int
    confidence: float  # 0.0 to 1.0


@dataclass
class UncertainMeasureResult:
    """Details about a measure with low confidence."""

    measure_number: int
    part_index: int
    confidence: float
    reason: str
    region_image_path: Optional[str] = None
    """Path to cropped image of the uncertain region."""


@dataclass
class ExtractedMetadataResult:
    """Metadata extracted from the score."""

    title: Optional[str] = None
    composer: Optional[str] = None
    key_signature: Optional[str] = None
    time_signature: Optional[str] = None
    tempo: Optional[int] = None
    measure_count: int = 0
    part_count: int = 1
    page_count: int = 1


@dataclass
class OmrProviderResult:
    """Result from OMR processing.

    This is the standardized output format that all providers
    must return, regardless of their internal representations.
    """

    success: bool
    """Whether processing completed successfully."""

    confidence: float = 0.0
    """Overall confidence score (0.0 to 1.0)."""

    music_xml: Optional[str] = None
    """Generated MusicXML content."""

    output_path: Optional[Path] = None
    """Path to the output file (if saved to disk)."""

    measure_confidence: List[MeasureConfidenceResult] = field(default_factory=list)
    """Per-measure confidence scores."""

    uncertain_measures: List[UncertainMeasureResult] = field(default_factory=list)
    """Measures flagged for manual review."""

    preview_path: Optional[Path] = None
    """Path to preview image (if generated)."""

    metadata: Optional[ExtractedMetadataResult] = None
    """Extracted metadata from the score."""

    error: Optional[str] = None
    """Error message if processing failed."""

    processing_time_ms: int = 0
    """Time taken to process in milliseconds."""

    provider_name: str = ""
    """Name of the provider that processed this request."""

    raw_output: Optional[str] = None
    """Raw output from the provider (for debugging)."""


class OmrProvider(ABC):
    """Abstract base class for OMR providers.

    All OMR providers must implement this interface to ensure
    consistent behavior across different engines.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the provider name (e.g., 'audiveris', 'oemer')."""
        pass

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and properly configured."""
        pass

    @abstractmethod
    async def process(
        self,
        input_path: Path,
        options: Optional[OmrProviderOptions] = None,
        output_dir: Optional[Path] = None,
    ) -> OmrProviderResult:
        """Process an image/PDF and return recognized music.

        Args:
            input_path: Path to the input file (image or PDF)
            options: Processing options (uses defaults if None)
            output_dir: Directory for output files (temp dir if None)

        Returns:
            OmrProviderResult with the recognition results
        """
        pass

    @abstractmethod
    async def get_version(self) -> Optional[str]:
        """Get the provider/engine version string."""
        pass

    def get_default_options(self) -> OmrProviderOptions:
        """Get default options for this provider.

        Subclasses can override to provide provider-specific defaults.
        """
        return OmrProviderOptions()
