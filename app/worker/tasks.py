"""Celery task definitions.

All async tasks are defined here. Tasks are executed by Celery workers
and can be triggered from the FastAPI routes.
"""

import logging
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded

from app.services.omr import get_omr_provider, OmrProviderOptions
from app.services.omr.base import OmrProviderResult
from app.worker.job_store import job_store, JobStatus

logger = logging.getLogger(__name__)


def _run_async(coro):
    """Helper to run async code from sync Celery tasks."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@shared_task(
    bind=True,
    name="app.worker.tasks.process_omr_job",
    max_retries=2,
    default_retry_delay=60,
)
def process_omr_job(
    self,
    job_id: str,
    asset_id: str,
    input_path: str,
    source_type: str,
    options: Optional[dict] = None,
) -> dict:
    """Process an OMR job asynchronously.

    Args:
        job_id: Unique job identifier
        asset_id: Asset ID of the uploaded file
        input_path: Path to the input file
        source_type: Type of source (photo, pdf, etc.)
        options: Processing options dict

    Returns:
        Dict with processing result
    """
    logger.info(f"Starting OMR job {job_id} for asset {asset_id}")

    # Update job status to processing
    job_store.update_job(
        job_id,
        status=JobStatus.PROCESSING,
        progress=10,
        celery_task_id=self.request.id,
    )

    try:
        # Get OMR provider
        provider = get_omr_provider()
        logger.info(f"Using OMR provider: {provider.name}")

        # Check availability
        if not provider.is_available:
            raise RuntimeError(
                f"OMR provider '{provider.name}' is not available. "
                "Check installation and configuration."
            )

        # Build options
        omr_options = OmrProviderOptions()
        if options:
            for key, value in options.items():
                if hasattr(omr_options, key):
                    setattr(omr_options, key, value)

        # Update progress
        job_store.update_job(job_id, progress=20)

        # Run OMR processing
        input_file = Path(input_path)
        result: OmrProviderResult = _run_async(
            provider.process(input_file, omr_options)
        )

        # Update progress
        job_store.update_job(job_id, progress=90)

        if result.success:
            # Store result
            job_store.update_job(
                job_id,
                status=JobStatus.COMPLETED,
                progress=100,
                result={
                    "confidence": result.confidence,
                    "music_xml": result.music_xml,
                    "measure_confidence": [
                        {
                            "measure_number": m.measure_number,
                            "part_index": m.part_index,
                            "confidence": m.confidence,
                        }
                        for m in result.measure_confidence
                    ],
                    "uncertain_measures": [
                        {
                            "measure_number": m.measure_number,
                            "part_index": m.part_index,
                            "confidence": m.confidence,
                            "reason": m.reason,
                            "region_image_url": m.region_image_path,
                        }
                        for m in result.uncertain_measures
                    ],
                    "preview_url": str(result.preview_path) if result.preview_path else None,
                    "metadata": {
                        "title": result.metadata.title if result.metadata else None,
                        "composer": result.metadata.composer if result.metadata else None,
                        "key_signature": result.metadata.key_signature if result.metadata else None,
                        "time_signature": result.metadata.time_signature if result.metadata else None,
                        "tempo": result.metadata.tempo if result.metadata else None,
                        "measure_count": result.metadata.measure_count if result.metadata else 0,
                        "part_count": result.metadata.part_count if result.metadata else 1,
                        "page_count": result.metadata.page_count if result.metadata else 1,
                    } if result.metadata else None,
                },
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

            logger.info(
                f"OMR job {job_id} completed successfully "
                f"(confidence: {result.confidence:.2f}, "
                f"time: {result.processing_time_ms}ms)"
            )

            return {"success": True, "job_id": job_id}

        else:
            # Processing failed
            job_store.update_job(
                job_id,
                status=JobStatus.FAILED,
                error=result.error or "Unknown processing error",
                completed_at=datetime.now(timezone.utc).isoformat(),
            )

            logger.error(f"OMR job {job_id} failed: {result.error}")
            return {"success": False, "job_id": job_id, "error": result.error}

    except SoftTimeLimitExceeded:
        logger.error(f"OMR job {job_id} exceeded time limit")
        job_store.update_job(
            job_id,
            status=JobStatus.FAILED,
            error="Processing exceeded time limit",
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        raise

    except Exception as e:
        logger.exception(f"OMR job {job_id} failed with exception")
        job_store.update_job(
            job_id,
            status=JobStatus.FAILED,
            error=str(e),
            completed_at=datetime.now(timezone.utc).isoformat(),
        )

        # Retry on transient errors
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying OMR job {job_id} (attempt {self.request.retries + 1})")
            raise self.retry(exc=e)

        return {"success": False, "job_id": job_id, "error": str(e)}


@shared_task(name="app.worker.tasks.cleanup_expired_jobs")
def cleanup_expired_jobs(max_age_hours: int = 24) -> dict:
    """Clean up expired jobs from the job store.

    Args:
        max_age_hours: Remove jobs older than this many hours

    Returns:
        Dict with cleanup stats
    """
    count = job_store.cleanup_old_jobs(max_age_hours)
    logger.info(f"Cleaned up {count} expired jobs")
    return {"cleaned_up": count}


@shared_task(name="app.worker.tasks.health_check")
def health_check() -> dict:
    """Health check task for monitoring.

    Returns:
        Dict with worker status
    """
    provider = get_omr_provider()
    return {
        "status": "healthy",
        "omr_provider": provider.name,
        "omr_available": provider.is_available,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
