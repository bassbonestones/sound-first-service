"""Import API routes for file upload and OMR processing."""
import logging
import os
import uuid
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.db import get_db
from app.settings import settings
from app.schemas.import_schemas import (
    ImportSourceType,
    OmrJobStatus,
    SignedUrlRequest,
    SignedUrlResponse,
    UploadResponse,
    OmrSubmitRequest,
    OmrSubmitResponse,
    OmrStatusResponse,
    OmrResult,
    ExtractedMetadata,
    SaveScoreRequest,
    SaveScoreResponse,
    GetScoreResponse,
    SavedScore,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/imports", tags=["imports"])

# In-memory stores for fallback when Redis is unavailable (e.g., tests)
_omr_jobs: Dict[str, Any] = {}
_saved_scores: Dict[str, Any] = {}

# Flag to track if Redis is available
_redis_available: Optional[bool] = None


def _is_redis_available() -> bool:
    """Check if Redis is available for job storage."""
    global _redis_available
    
    # Cache the result to avoid repeated connection attempts
    if _redis_available is not None:
        return _redis_available
    
    try:
        from app.worker.job_store import job_store
        job_store.redis.ping()
        _redis_available = True
        logger.info("Redis is available, using Redis job store")
    except Exception as e:
        _redis_available = False
        logger.warning(f"Redis not available ({e}), using in-memory job store")
    
    return _redis_available


def _get_job_store() -> Any:
    """Get the appropriate job store based on Redis availability."""
    if _is_redis_available():
        from app.worker.job_store import job_store
        return job_store
    return None  # Use in-memory fallback


# ============================================================================
# Helper Functions
# ============================================================================


def _generate_asset_id() -> str:
    """Generate a unique asset ID."""
    return f"asset_{uuid.uuid4().hex[:16]}"


def _generate_job_id() -> str:
    """Generate a unique job ID."""
    return f"omr_{uuid.uuid4().hex[:16]}"


def _generate_score_id() -> str:
    """Generate a unique score ID."""
    return f"score_{uuid.uuid4().hex[:16]}"


def _get_storage_path() -> Path:
    """Get the storage directory path, creating it if needed."""
    storage_path = Path(settings.local_storage_path)
    storage_path.mkdir(parents=True, exist_ok=True)
    return storage_path


def _get_asset_path(asset_id: str, extension: str = "") -> Path:
    """Get the path for an asset file."""
    return _get_storage_path() / f"{asset_id}{extension}"


def _extension_from_mime(mime_type: str) -> str:
    """Get file extension from MIME type."""
    mime_map = {
        "image/jpeg": ".jpg",
        "image/png": ".png",
        "image/heic": ".heic",
        "application/pdf": ".pdf",
        "application/xml": ".xml",
        "text/xml": ".xml",
        "application/vnd.recordare.musicxml+xml": ".musicxml",
        "application/vnd.recordare.musicxml": ".mxl",
        "application/zip": ".mxl",
    }
    return mime_map.get(mime_type.lower(), "")


# ============================================================================
# Upload Endpoints
# ============================================================================


@router.post(
    "/upload/signed-url",
    response_model=SignedUrlResponse,
    description="Get a signed URL for file upload",
)
async def get_signed_url(request: SignedUrlRequest) -> SignedUrlResponse:
    """
    Get a signed URL for file upload.

    For local storage, this returns a direct upload URL.
    For S3 storage, this returns a pre-signed URL.
    """
    asset_id = _generate_asset_id()

    if settings.storage_provider == "local":
        # For local storage, return the direct upload endpoint URL
        upload_url = f"/api/imports/upload/direct/{asset_id}"
        public_url = f"/api/imports/files/{asset_id}"
        expires_at = int(time.time()) + settings.signed_url_expiry

        return SignedUrlResponse(
            success=True,
            upload_url=upload_url,
            asset_id=asset_id,
            public_url=public_url,
            expires_at=expires_at,
            error=None,
        )

    elif settings.storage_provider == "s3":
        # TODO: Implement S3 signed URL generation
        # This would use boto3 to generate a pre-signed URL
        return SignedUrlResponse(
            success=False,
            upload_url=None,
            asset_id=asset_id,
            public_url=None,
            expires_at=None,
            error="S3 storage not yet implemented",
        )

    return SignedUrlResponse(
        success=False,
        upload_url=None,
        asset_id=asset_id,
        public_url=None,
        expires_at=None,
        error=f"Unknown storage provider: {settings.storage_provider}",
    )


@router.post(
    "/upload/direct/{asset_id}",
    response_model=UploadResponse,
    description="Direct file upload for local or server storage",
)
async def upload_file_direct(
    asset_id: str,
    file: UploadFile = File(...),
    source_type: str = Form(...),
) -> UploadResponse:
    """
    Direct file upload endpoint.

    Used when not using signed URLs (local development) or
    when the client uploads to our server instead of S3.
    """
    try:
        # Validate source type
        try:
            src_type = ImportSourceType(source_type)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid source_type: {source_type}",
            )

        # Determine file extension
        extension = _extension_from_mime(file.content_type or "")
        if not extension and file.filename:
            extension = Path(file.filename).suffix

        # Save file
        file_path = _get_asset_path(asset_id, extension)
        content = await file.read()
        file_path.write_bytes(content)

        # Store metadata (in-memory for now)
        _omr_jobs[f"{asset_id}_meta"] = {
            "asset_id": asset_id,
            "filename": file.filename,
            "mime_type": file.content_type,
            "source_type": src_type.value,
            "size": len(content),
            "path": str(file_path),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
        }

        return UploadResponse(
            success=True,
            asset_id=asset_id,
            url=f"/api/imports/files/{asset_id}",
            stored_size=len(content),
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            error=None,
        )

    except HTTPException:
        raise
    except Exception as e:
        return UploadResponse(
            success=False,
            asset_id=asset_id,
            url=None,
            stored_size=0,
            uploaded_at=datetime.now(timezone.utc).isoformat(),
            error=str(e),
        )


@router.get(
    "/files/{asset_id}",
    description="Retrieve an uploaded file",
)
async def get_file(asset_id: str) -> Any:
    """
    Retrieve an uploaded file.
    """
    # Find the file with any extension
    storage_path = _get_storage_path()
    for file_path in storage_path.glob(f"{asset_id}.*"):
        if file_path.is_file():
            from fastapi.responses import FileResponse

            return FileResponse(
                path=str(file_path),
                filename=file_path.name,
            )

    raise HTTPException(status_code=404, detail=f"File not found: {asset_id}")


# ============================================================================
# OMR Endpoints
# ============================================================================


@router.post(
    "/omr/submit",
    response_model=OmrSubmitResponse,
    description="Submit a file for OMR (optical music recognition) processing",
)
async def submit_omr_job(request: OmrSubmitRequest) -> OmrSubmitResponse:
    """
    Submit a file for OMR processing.

    Creates an async job that processes the uploaded file
    and extracts music notation.
    
    - With Redis: Dispatches to Celery worker for async processing
    - Without Redis: Uses mock provider for immediate results (testing)
    """
    # Verify asset exists
    meta_key = f"{request.asset_id}_meta"
    if meta_key not in _omr_jobs:
        return OmrSubmitResponse(
            success=False,
            job_id=None,
            estimated_duration_ms=None,
            error=f"Asset not found: {request.asset_id}",
        )

    # Get asset metadata
    asset_meta = _omr_jobs[meta_key]
    input_path = asset_meta.get("path")
    
    # Create job
    job_id = _generate_job_id()

    # Estimate processing time based on source type
    duration_estimates = {
        ImportSourceType.PHOTO: 15000,
        ImportSourceType.IMAGE: 10000,
        ImportSourceType.PDF: 20000,
        ImportSourceType.MUSICXML: 1000,
        ImportSourceType.MXL: 2000,
    }
    estimated_ms = duration_estimates.get(request.source_type, 10000)

    # Check if we should use async processing
    job_store = _get_job_store()
    use_async = job_store is not None and settings.omr_provider != "mock"

    if use_async:
        # Production: Use Celery for async processing
        from app.worker.job_store import JobStatus
        from app.worker.tasks import process_omr_job
        
        # Create job in Redis
        job_store.create_job(
            job_id=job_id,
            asset_id=request.asset_id,
            source_type=request.source_type.value,
            options=request.options.model_dump() if request.options else None,
        )
        
        # Dispatch to Celery worker
        process_omr_job.delay(
            job_id=job_id,
            asset_id=request.asset_id,
            input_path=input_path,
            source_type=request.source_type.value,
            options=request.options.model_dump() if request.options else None,
        )
        
        logger.info(f"Dispatched OMR job {job_id} to Celery worker")
        
    else:
        # Fallback: Use in-memory store (for tests or mock provider)
        _omr_jobs[job_id] = {
            "job_id": job_id,
            "asset_id": request.asset_id,
            "source_type": request.source_type.value,
            "options": request.options.model_dump() if request.options else {},
            "status": OmrJobStatus.QUEUED.value,
            "progress": 0,
            "result": None,
            "error": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # For mock provider, immediately complete with mock data
        if settings.omr_provider == "mock":
            _process_mock_omr(job_id, request.asset_id)

    return OmrSubmitResponse(
        success=True,
        job_id=job_id,
        estimated_duration_ms=estimated_ms,
        error=None,
    )


def _process_mock_omr(job_id: str, asset_id: str) -> None:
    """Process OMR job with mock provider (for testing)."""
    job = _omr_jobs.get(job_id)
    if not job:
        return

    # Update to processing
    job["status"] = OmrJobStatus.PROCESSING.value
    job["progress"] = 50

    # Generate mock result - a simple C major scale
    mock_musicxml = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"
    "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work>
    <work-title>Imported Score</work-title>
  </work>
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
  </part>
</score-partwise>'''

    job["status"] = OmrJobStatus.COMPLETED.value
    job["progress"] = 100
    job["result"] = {
        "confidence": 0.85,
        "music_xml": mock_musicxml,
        "measure_confidence": [
            {"measure_number": 1, "part_index": 0, "confidence": 0.85},
            {"measure_number": 2, "part_index": 0, "confidence": 0.83},
        ],
        "uncertain_measures": [],
        "preview_url": None,
        "metadata": {
            "title": "Imported Score",
            "composer": None,
            "key_signature": "C",
            "time_signature": "4/4",
            "tempo": None,
            "measure_count": 2,
            "part_count": 1,
            "page_count": 1,
        },
    }


@router.get(
    "/omr/status/{job_id}",
    response_model=OmrStatusResponse,
    description="Get the status and results of an OMR job",
)
async def get_omr_status(job_id: str) -> OmrStatusResponse:
    """
    Get the status of an OMR job.

    Poll this endpoint to check job progress and retrieve results.
    """
    # Try Redis first, then fallback to in-memory
    job_store = _get_job_store()
    job = None
    
    if job_store is not None:
        stored_job = job_store.get_job(job_id)
        if stored_job:
            job = {
                "job_id": stored_job.job_id,
                "status": stored_job.status,
                "progress": stored_job.progress,
                "result": stored_job.result,
                "error": stored_job.error,
            }
    
    # Fallback to in-memory store
    if job is None:
        job = _omr_jobs.get(job_id)
    
    if not job:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    result = None
    if job.get("result"):
        result = OmrResult(
            confidence=job["result"]["confidence"],
            music_xml=job["result"]["music_xml"],
            measure_confidence=job["result"]["measure_confidence"],
            uncertain_measures=job["result"]["uncertain_measures"],
            preview_url=job["result"].get("preview_url"),
            metadata=ExtractedMetadata(**job["result"]["metadata"])
            if job["result"].get("metadata")
            else None,
        )

    return OmrStatusResponse(
        job_id=job_id,
        status=OmrJobStatus(job["status"]),
        progress=job.get("progress", 0),
        result=result,
        error=job.get("error"),
    )


# ============================================================================
# Score Storage Endpoints
# ============================================================================


@router.post(
    "/scores",
    response_model=SaveScoreResponse,
    description="Save a processed score",
)
async def save_score(request: SaveScoreRequest, db: Session = Depends(get_db)) -> SaveScoreResponse:
    """
    Save a processed score.

    Stores the score data for later retrieval and use in the app.
    """
    try:
        score_id = _generate_score_id()
        now = datetime.now(timezone.utc).isoformat()

        # Store score (in-memory for now)
        _saved_scores[score_id] = {
            "score_id": score_id,
            "source_asset_id": request.source_asset_id,
            "omr_job_id": request.omr_job_id,
            "score_data": request.score_data,
            "metadata": request.metadata_overrides or {},
            "created_at": now,
            "updated_at": now,
        }

        return SaveScoreResponse(
            success=True,
            score_id=score_id,
            saved_at=now,
            error=None,
        )

    except Exception as e:
        return SaveScoreResponse(
            success=False,
            score_id="",
            saved_at=datetime.now(timezone.utc).isoformat(),
            error=str(e),
        )


@router.get(
    "/scores/{score_id}",
    response_model=GetScoreResponse,
    description="Retrieve a saved score",
)
async def get_score(score_id: str, db: Session = Depends(get_db)) -> GetScoreResponse:
    """
    Retrieve a saved score.
    """
    score_data = _saved_scores.get(score_id)
    if not score_data:
        return GetScoreResponse(
            success=False,
            score=None,
            error=f"Score not found: {score_id}",
        )

    return GetScoreResponse(
        success=True,
        score=SavedScore(
            score_id=score_data["score_id"],
            source_asset_id=score_data["source_asset_id"],
            score_data=score_data["score_data"],
            metadata=score_data["metadata"],
            created_at=score_data["created_at"],
            updated_at=score_data["updated_at"],
        ),
        error=None,
    )


@router.delete(
    "/scores/{score_id}",
    description="Delete a saved score",
)
async def delete_score(score_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Delete a saved score.
    """
    if score_id in _saved_scores:
        del _saved_scores[score_id]
        return {"success": True, "message": f"Score {score_id} deleted"}

    raise HTTPException(status_code=404, detail=f"Score not found: {score_id}")


# ============================================================================
# Health Check
# ============================================================================


@router.get(
    "/health",
    description="Health check for import service",
)
async def import_health() -> Dict[str, Any]:
    """
    Health check for import service.
    
    Returns status of storage, OMR provider, and job processing.
    """
    # Check Redis availability
    redis_available = _is_redis_available()
    
    # Get job stats
    active_jobs = 0
    if redis_available:
        try:
            job_store = _get_job_store()
            stats = job_store.get_stats()
            active_jobs = stats.get("queued", 0) + stats.get("processing", 0)
        except Exception:
            pass
    else:
        active_jobs = len([
            j for j in _omr_jobs.values() 
            if isinstance(j, dict) and j.get("status") in ["queued", "processing"]
        ])
    
    # Check OMR provider availability
    omr_available = False
    omr_version = None
    try:
        from app.services.omr import get_omr_provider
        provider = get_omr_provider()
        omr_available = provider.is_available
        if omr_available:
            omr_version = await provider.get_version()
    except Exception:
        pass
    
    return {
        "status": "healthy",
        "storage_provider": settings.storage_provider,
        "omr_provider": settings.omr_provider,
        "omr_available": omr_available,
        "omr_version": omr_version,
        "redis_available": redis_available,
        "active_jobs": active_jobs,
    }
