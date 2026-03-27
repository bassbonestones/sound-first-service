"""Import-related Pydantic models for file upload and OMR processing."""
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, field_validator


# ============================================================================
# Enums
# ============================================================================


class ImportSourceType(str, Enum):
    """Type of import source file."""

    PHOTO = "photo"
    IMAGE = "image"
    PDF = "pdf"
    MUSICXML = "musicxml"
    MXL = "mxl"


class OmrJobStatus(str, Enum):
    """Status of an OMR processing job."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


# ============================================================================
# Upload API
# ============================================================================


class SignedUrlRequest(BaseModel):
    """Request to get a signed URL for upload."""

    file_name: str = Field(..., description="Original filename")
    mime_type: str = Field(..., description="MIME type of the file")
    file_size: Optional[int] = Field(
        None, ge=0, description="File size in bytes (for validation)"
    )
    source_type: ImportSourceType = Field(
        ..., description="Source type for categorization"
    )

    @field_validator("file_name")
    @classmethod
    def validate_file_name(cls, v: str) -> str:
        """Validate filename is not empty."""
        if not v or not v.strip():
            raise ValueError("file_name cannot be empty")
        return v.strip()

    @field_validator("mime_type")
    @classmethod
    def validate_mime_type(cls, v: str) -> str:
        """Validate MIME type format."""
        if not v or "/" not in v:
            raise ValueError("Invalid MIME type format")
        return v.lower()


class SignedUrlResponse(BaseModel):
    """Response with signed URL for upload."""

    success: bool = Field(..., description="Whether the request succeeded")
    upload_url: Optional[str] = Field(
        None, description="Pre-signed URL for uploading the file"
    )
    asset_id: str = Field(..., description="Asset ID assigned by the backend")
    public_url: Optional[str] = Field(
        None, description="Public URL for the file after upload"
    )
    expires_at: Optional[int] = Field(
        None, description="URL expiration timestamp (Unix epoch)"
    )
    error: Optional[str] = Field(None, description="Error message if failed")


class UploadResponse(BaseModel):
    """Response from direct file upload."""

    success: bool = Field(..., description="Whether the upload succeeded")
    asset_id: str = Field(..., description="Assigned asset ID")
    url: Optional[str] = Field(None, description="URL where file can be accessed")
    stored_size: int = Field(..., description="File size as stored")
    uploaded_at: str = Field(..., description="Server timestamp (ISO format)")
    error: Optional[str] = Field(None, description="Error message if failed")


# ============================================================================
# OMR API
# ============================================================================


class OmrProcessingOptions(BaseModel):
    """Options for OMR processing."""

    language: str = Field(default="en", description="Language hint for text recognition")
    enhance_image: bool = Field(
        default=True, description="Apply image enhancement before processing"
    )
    detect_parts: bool = Field(
        default=True, description="Attempt to detect multiple parts"
    )
    generate_preview: bool = Field(
        default=True, description="Generate preview image of result"
    )


class OmrSubmitRequest(BaseModel):
    """Request to submit an OMR job."""

    asset_id: str = Field(..., description="Asset ID from upload")
    source_type: ImportSourceType = Field(
        ..., description="Source type (affects processing)"
    )
    options: Optional[OmrProcessingOptions] = Field(
        None, description="Processing options"
    )

    @field_validator("asset_id")
    @classmethod
    def validate_asset_id(cls, v: str) -> str:
        """Validate asset ID is not empty."""
        if not v or not v.strip():
            raise ValueError("asset_id cannot be empty")
        return v.strip()


class OmrSubmitResponse(BaseModel):
    """Response from OMR job submission."""

    success: bool = Field(..., description="Whether submission succeeded")
    job_id: Optional[str] = Field(None, description="Job ID for status polling")
    estimated_duration_ms: Optional[int] = Field(
        None, description="Estimated processing time in ms"
    )
    error: Optional[str] = Field(None, description="Error message if submission failed")


class MeasureConfidence(BaseModel):
    """Per-measure confidence data."""

    measure_number: int = Field(..., ge=1, description="Measure number (1-indexed)")
    part_index: int = Field(..., ge=0, description="Part index (0-indexed)")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")


class UncertainMeasure(BaseModel):
    """Details about an uncertain measure."""

    measure_number: int = Field(..., ge=1, description="Measure number (1-indexed)")
    part_index: int = Field(..., ge=0, description="Part index (0-indexed)")
    confidence: float = Field(..., ge=0, le=1, description="Confidence score (0-1)")
    reason: str = Field(..., description="Reason for uncertainty")
    region_image_url: Optional[str] = Field(
        None, description="Cropped image of the uncertain region"
    )


class ExtractedMetadata(BaseModel):
    """Metadata extracted from OMR."""

    title: Optional[str] = None
    composer: Optional[str] = None
    key_signature: Optional[str] = None
    time_signature: Optional[str] = None
    tempo: Optional[int] = None
    measure_count: int = Field(..., ge=0)
    part_count: int = Field(..., ge=1)
    page_count: int = Field(..., ge=1)


class OmrResult(BaseModel):
    """OMR processing result payload."""

    confidence: float = Field(
        ..., ge=0, le=1, description="Overall confidence score (0-1)"
    )
    music_xml: Optional[str] = Field(
        None, description="Generated MusicXML if available"
    )
    measure_confidence: List[MeasureConfidence] = Field(
        default_factory=list, description="Measure-level confidence scores"
    )
    uncertain_measures: List[UncertainMeasure] = Field(
        default_factory=list, description="Measures flagged for review"
    )
    preview_url: Optional[str] = Field(
        None, description="Preview image URL if generated"
    )
    metadata: Optional[ExtractedMetadata] = Field(
        None, description="Metadata extracted from the score"
    )


class OmrStatusResponse(BaseModel):
    """OMR job status response."""

    job_id: str = Field(..., description="Job ID")
    status: OmrJobStatus = Field(..., description="Current job status")
    progress: Optional[int] = Field(
        None, ge=0, le=100, description="Progress percentage"
    )
    result: Optional[OmrResult] = Field(None, description="Result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")


# ============================================================================
# Score Storage API
# ============================================================================


class SaveScoreRequest(BaseModel):
    """Request to save a processed score."""

    source_asset_id: str = Field(..., description="Asset ID of the source file")
    omr_job_id: Optional[str] = Field(None, description="OMR job ID if applicable")
    score_data: str = Field(..., description="Score data (serialized JSON)")
    metadata_overrides: Optional[Dict[str, Any]] = Field(
        None, description="User-provided metadata overrides"
    )

    @field_validator("source_asset_id")
    @classmethod
    def validate_source_asset_id(cls, v: str) -> str:
        """Validate source asset ID is not empty."""
        if not v or not v.strip():
            raise ValueError("source_asset_id cannot be empty")
        return v.strip()


class SaveScoreResponse(BaseModel):
    """Response from saving a score."""

    success: bool = Field(..., description="Whether the save succeeded")
    score_id: str = Field(..., description="Assigned score ID")
    saved_at: str = Field(..., description="Server timestamp (ISO format)")
    error: Optional[str] = Field(None, description="Error message if failed")


class SavedScore(BaseModel):
    """Saved score payload."""

    score_id: str
    source_asset_id: str
    score_data: str
    metadata: Dict[str, Any]
    created_at: str
    updated_at: str


class GetScoreResponse(BaseModel):
    """Response with score data."""

    success: bool
    score: Optional[SavedScore] = None
    error: Optional[str] = None


# ============================================================================
# Error Response
# ============================================================================


class ErrorDetail(BaseModel):
    """Error detail information."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None


class ApiErrorResponse(BaseModel):
    """Standard API error response."""

    success: bool = False
    error: ErrorDetail
