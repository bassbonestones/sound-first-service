"""Job store for tracking OMR job status.

Uses Redis for persistence and sharing state between
FastAPI API and Celery workers.
"""

import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from dataclasses import dataclass, asdict

import redis

from app.settings import settings

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """OMR job status."""

    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class OmrJob:
    """OMR job data structure."""

    job_id: str
    asset_id: str
    source_type: str
    status: str = JobStatus.QUEUED.value
    progress: int = 0
    result: Optional[dict] = None
    error: Optional[str] = None
    celery_task_id: Optional[str] = None
    options: Optional[dict] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OmrJob":
        """Create from dictionary."""
        return cls(**data)


class JobStore:
    """Redis-backed job store.

    Manages OMR job state with atomic updates
    and shared access between API and workers.
    """

    KEY_PREFIX = "omr_job:"
    JOB_TTL_SECONDS = 86400  # 24 hours

    def __init__(self, redis_url: Optional[str] = None):
        """Initialize job store.

        Args:
            redis_url: Redis connection URL (uses settings if None)
        """
        self._redis_url = redis_url or settings.redis_url
        self._redis: Optional[redis.Redis] = None

    @property
    def redis(self) -> redis.Redis:
        """Get Redis connection (lazy initialization)."""
        if self._redis is None:
            self._redis = redis.from_url(
                self._redis_url,
                decode_responses=True,
            )
        return self._redis

    def _key(self, job_id: str) -> str:
        """Get Redis key for a job."""
        return f"{self.KEY_PREFIX}{job_id}"

    def create_job(
        self,
        job_id: str,
        asset_id: str,
        source_type: str,
        options: Optional[dict] = None,
    ) -> OmrJob:
        """Create a new job.

        Args:
            job_id: Unique job identifier
            asset_id: Asset ID of the uploaded file
            source_type: Type of source file
            options: Processing options

        Returns:
            The created OmrJob
        """
        now = datetime.now(timezone.utc).isoformat()

        job = OmrJob(
            job_id=job_id,
            asset_id=asset_id,
            source_type=source_type,
            status=JobStatus.QUEUED.value,
            progress=0,
            options=options,
            created_at=now,
            updated_at=now,
        )

        # Store in Redis
        self.redis.setex(
            self._key(job_id),
            self.JOB_TTL_SECONDS,
            json.dumps(job.to_dict()),
        )

        logger.debug(f"Created job {job_id}")
        return job

    def get_job(self, job_id: str) -> Optional[OmrJob]:
        """Get a job by ID.

        Args:
            job_id: Job identifier

        Returns:
            OmrJob if found, None otherwise
        """
        data = self.redis.get(self._key(job_id))
        if data is None:
            return None

        return OmrJob.from_dict(json.loads(data))

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        result: Optional[dict] = None,
        error: Optional[str] = None,
        celery_task_id: Optional[str] = None,
        completed_at: Optional[str] = None,
    ) -> Optional[OmrJob]:
        """Update a job's status.

        Args:
            job_id: Job identifier
            status: New status
            progress: Progress percentage (0-100)
            result: Processing result
            error: Error message
            celery_task_id: Celery task ID
            completed_at: Completion timestamp

        Returns:
            Updated OmrJob if successful, None if job not found
        """
        job = self.get_job(job_id)
        if job is None:
            logger.warning(f"Attempted to update non-existent job {job_id}")
            return None

        # Update fields
        if status is not None:
            job.status = status.value
        if progress is not None:
            job.progress = progress
        if result is not None:
            job.result = result
        if error is not None:
            job.error = error
        if celery_task_id is not None:
            job.celery_task_id = celery_task_id
        if completed_at is not None:
            job.completed_at = completed_at

        job.updated_at = datetime.now(timezone.utc).isoformat()

        # Store back in Redis
        self.redis.setex(
            self._key(job_id),
            self.JOB_TTL_SECONDS,
            json.dumps(job.to_dict()),
        )

        logger.debug(f"Updated job {job_id}: status={job.status}, progress={job.progress}")
        return job

    def delete_job(self, job_id: str) -> bool:
        """Delete a job.

        Args:
            job_id: Job identifier

        Returns:
            True if deleted, False if not found
        """
        result = self.redis.delete(self._key(job_id))
        return result > 0

    def list_jobs(self, limit: int = 100) -> list[OmrJob]:
        """List recent jobs.

        Args:
            limit: Maximum number of jobs to return

        Returns:
            List of OmrJob objects
        """
        keys = self.redis.keys(f"{self.KEY_PREFIX}*")
        jobs = []

        for key in keys[:limit]:
            data = self.redis.get(key)
            if data:
                jobs.append(OmrJob.from_dict(json.loads(data)))

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at or "", reverse=True)
        return jobs

    def cleanup_old_jobs(self, max_age_hours: int = 24) -> int:
        """Remove jobs older than max_age_hours.

        Args:
            max_age_hours: Maximum job age in hours

        Returns:
            Number of jobs cleaned up
        """
        from datetime import timedelta

        cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
        cutoff_iso = cutoff.isoformat()

        keys = self.redis.keys(f"{self.KEY_PREFIX}*")
        cleaned = 0

        for key in keys:
            data = self.redis.get(key)
            if data:
                job_data = json.loads(data)
                created_at = job_data.get("created_at", "")
                if created_at and created_at < cutoff_iso:
                    self.redis.delete(key)
                    cleaned += 1

        return cleaned

    def get_stats(self) -> dict:
        """Get job statistics.

        Returns:
            Dict with job counts by status
        """
        keys = self.redis.keys(f"{self.KEY_PREFIX}*")
        stats = {
            "total": len(keys),
            "queued": 0,
            "processing": 0,
            "completed": 0,
            "failed": 0,
        }

        for key in keys:
            data = self.redis.get(key)
            if data:
                job_data = json.loads(data)
                status = job_data.get("status", "")
                if status in stats:
                    stats[status] += 1

        return stats


# Global job store instance (singleton)
job_store = JobStore()
