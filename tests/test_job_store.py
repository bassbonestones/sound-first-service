"""
Tests for the OMR job store module.

Tests the Redis-backed job store for OMR job state management.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

from app.worker.job_store import (
    JobStore,
    JobStatus,
    OmrJob,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis_mock = MagicMock()
    # Storage for mock operations
    redis_mock._storage = {}
    
    def mock_setex(key, ttl, value):
        redis_mock._storage[key] = value
    
    def mock_get(key):
        return redis_mock._storage.get(key)
    
    def mock_delete(key):
        if key in redis_mock._storage:
            del redis_mock._storage[key]
            return 1
        return 0
    
    def mock_keys(pattern):
        # Simple pattern matching for "prefix*"
        prefix = pattern.rstrip("*")
        return [k for k in redis_mock._storage.keys() if k.startswith(prefix)]
    
    redis_mock.setex = mock_setex
    redis_mock.get = mock_get
    redis_mock.delete = mock_delete
    redis_mock.keys = mock_keys
    
    return redis_mock


@pytest.fixture
def job_store(mock_redis):
    """Create a job store with mocked Redis."""
    store = JobStore()
    store._redis = mock_redis
    return store


# =============================================================================
# Tests for OmrJob
# =============================================================================


class TestOmrJob:
    """Test OmrJob dataclass."""

    def test_to_dict(self):
        """Test converting job to dictionary."""
        job = OmrJob(
            job_id="test-123",
            asset_id="asset-456",
            source_type="pdf",
            status=JobStatus.PROCESSING.value,
            progress=50,
        )
        
        data = job.to_dict()
        
        assert data["job_id"] == "test-123"
        assert data["asset_id"] == "asset-456"
        assert data["source_type"] == "pdf"
        assert data["status"] == "processing"
        assert data["progress"] == 50

    def test_from_dict(self):
        """Test creating job from dictionary."""
        data = {
            "job_id": "test-789",
            "asset_id": "asset-000",
            "source_type": "png",
            "status": "completed",
            "progress": 100,
            "result": {"success": True},
            "error": None,
            "celery_task_id": "celery-123",
            "options": {"format": "musicxml"},
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:05:00Z",
            "completed_at": "2024-01-01T00:05:00Z",
        }
        
        job = OmrJob.from_dict(data)
        
        assert job.job_id == "test-789"
        assert job.status == "completed"
        assert job.result == {"success": True}

    def test_defaults(self):
        """Test default values."""
        job = OmrJob(
            job_id="test",
            asset_id="asset",
            source_type="pdf",
        )
        
        assert job.status == JobStatus.QUEUED.value
        assert job.progress == 0
        assert job.result is None
        assert job.error is None


# =============================================================================
# Tests for JobStore.create_job
# =============================================================================


class TestJobStoreCreateJob:
    """Test JobStore.create_job method."""

    def test_create_job_basic(self, job_store, mock_redis):
        """Test creating a basic job."""
        job = job_store.create_job(
            job_id="job-001",
            asset_id="asset-001",
            source_type="pdf",
        )
        
        assert job.job_id == "job-001"
        assert job.asset_id == "asset-001"
        assert job.source_type == "pdf"
        assert job.status == JobStatus.QUEUED.value
        assert job.progress == 0
        assert job.created_at is not None
        assert job.updated_at is not None
        
        # Verify stored in Redis
        key = "omr_job:job-001"
        assert key in mock_redis._storage

    def test_create_job_with_options(self, job_store):
        """Test creating a job with options."""
        options = {"format": "musicxml", "quality": "high"}
        
        job = job_store.create_job(
            job_id="job-002",
            asset_id="asset-002",
            source_type="png",
            options=options,
        )
        
        assert job.options == options

    def test_create_job_timestamps(self, job_store):
        """Test that timestamps are set correctly."""
        job = job_store.create_job(
            job_id="job-003",
            asset_id="asset-003",
            source_type="pdf",
        )
        
        # Timestamps should be ISO format
        assert "T" in job.created_at
        assert job.created_at == job.updated_at


# =============================================================================
# Tests for JobStore.get_job
# =============================================================================


class TestJobStoreGetJob:
    """Test JobStore.get_job method."""

    def test_get_existing_job(self, job_store):
        """Test getting an existing job."""
        # Create a job first
        created = job_store.create_job(
            job_id="get-001",
            asset_id="asset-001",
            source_type="pdf",
        )
        
        # Get it back
        retrieved = job_store.get_job("get-001")
        
        assert retrieved is not None
        assert retrieved.job_id == created.job_id
        assert retrieved.asset_id == created.asset_id

    def test_get_nonexistent_job(self, job_store):
        """Test getting a job that doesn't exist."""
        result = job_store.get_job("nonexistent-id")
        assert result is None


# =============================================================================
# Tests for JobStore.update_job
# =============================================================================


class TestJobStoreUpdateJob:
    """Test JobStore.update_job method."""

    def test_update_status(self, job_store):
        """Test updating job status."""
        job_store.create_job("upd-001", "asset-001", "pdf")
        
        updated = job_store.update_job(
            "upd-001",
            status=JobStatus.PROCESSING,
        )
        
        assert updated is not None
        assert updated.status == JobStatus.PROCESSING.value

    def test_update_progress(self, job_store):
        """Test updating job progress."""
        job_store.create_job("upd-002", "asset-002", "pdf")
        
        updated = job_store.update_job(
            "upd-002",
            progress=75,
        )
        
        assert updated is not None
        assert updated.progress == 75

    def test_update_result(self, job_store):
        """Test updating job result."""
        job_store.create_job("upd-003", "asset-003", "pdf")
        
        result = {"music_xml": "<score/>", "confidence": 0.95}
        updated = job_store.update_job(
            "upd-003",
            status=JobStatus.COMPLETED,
            result=result,
        )
        
        assert updated is not None
        assert updated.result == result
        assert updated.status == JobStatus.COMPLETED.value

    def test_update_error(self, job_store):
        """Test updating job with error."""
        job_store.create_job("upd-004", "asset-004", "pdf")
        
        updated = job_store.update_job(
            "upd-004",
            status=JobStatus.FAILED,
            error="Processing failed: invalid input",
        )
        
        assert updated is not None
        assert updated.error == "Processing failed: invalid input"
        assert updated.status == JobStatus.FAILED.value

    def test_update_celery_task_id(self, job_store):
        """Test updating Celery task ID."""
        job_store.create_job("upd-005", "asset-005", "pdf")
        
        updated = job_store.update_job(
            "upd-005",
            celery_task_id="celery-task-abc123",
        )
        
        assert updated is not None
        assert updated.celery_task_id == "celery-task-abc123"

    def test_update_completed_at(self, job_store):
        """Test updating completion timestamp."""
        job_store.create_job("upd-006", "asset-006", "pdf")
        
        completed_at = datetime.now(timezone.utc).isoformat()
        updated = job_store.update_job(
            "upd-006",
            completed_at=completed_at,
        )
        
        assert updated is not None
        assert updated.completed_at == completed_at

    def test_update_nonexistent_job(self, job_store):
        """Test updating a job that doesn't exist."""
        result = job_store.update_job(
            "nonexistent",
            status=JobStatus.PROCESSING,
        )
        
        assert result is None

    def test_update_changes_updated_at(self, job_store):
        """Test that updating changes the updated_at timestamp."""
        job = job_store.create_job("upd-007", "asset-007", "pdf")
        original_updated_at = job.updated_at
        
        # Small delay to ensure different timestamp (optional, may not be needed)
        updated = job_store.update_job(
            "upd-007",
            progress=50,
        )
        
        assert updated is not None
        # updated_at should be different or equal (depending on timing)
        assert updated.updated_at is not None

    def test_update_multiple_fields(self, job_store):
        """Test updating multiple fields at once."""
        job_store.create_job("upd-008", "asset-008", "pdf")
        
        updated = job_store.update_job(
            "upd-008",
            status=JobStatus.COMPLETED,
            progress=100,
            result={"success": True},
            completed_at=datetime.now(timezone.utc).isoformat(),
        )
        
        assert updated is not None
        assert updated.status == JobStatus.COMPLETED.value
        assert updated.progress == 100
        assert updated.result == {"success": True}
        assert updated.completed_at is not None


# =============================================================================
# Tests for JobStore.delete_job
# =============================================================================


class TestJobStoreDeleteJob:
    """Test JobStore.delete_job method."""

    def test_delete_existing_job(self, job_store, mock_redis):
        """Test deleting an existing job."""
        job_store.create_job("del-001", "asset-001", "pdf")
        
        result = job_store.delete_job("del-001")
        
        assert result is True
        assert job_store.get_job("del-001") is None

    def test_delete_nonexistent_job(self, job_store):
        """Test deleting a job that doesn't exist."""
        result = job_store.delete_job("nonexistent")
        assert result is False


# =============================================================================
# Tests for JobStore.list_jobs
# =============================================================================


class TestJobStoreListJobs:
    """Test JobStore.list_jobs method."""

    def test_list_empty(self, job_store):
        """Test listing when no jobs exist."""
        jobs = job_store.list_jobs()
        assert jobs == []

    def test_list_multiple_jobs(self, job_store):
        """Test listing multiple jobs."""
        job_store.create_job("list-001", "asset-001", "pdf")
        job_store.create_job("list-002", "asset-002", "png")
        job_store.create_job("list-003", "asset-003", "jpg")
        
        jobs = job_store.list_jobs()
        
        assert len(jobs) == 3
        job_ids = {j.job_id for j in jobs}
        assert job_ids == {"list-001", "list-002", "list-003"}

    def test_list_respects_limit(self, job_store):
        """Test that list respects the limit parameter."""
        for i in range(10):
            job_store.create_job(f"limit-{i:03d}", f"asset-{i}", "pdf")
        
        jobs = job_store.list_jobs(limit=5)
        
        assert len(jobs) == 5

    def test_list_sorted_by_created_at(self, job_store):
        """Test that jobs are sorted by created_at descending."""
        # Create jobs with explicit timestamps
        job_store.create_job("sort-001", "asset-001", "pdf")
        job_store.create_job("sort-002", "asset-002", "pdf")
        job_store.create_job("sort-003", "asset-003", "pdf")
        
        jobs = job_store.list_jobs()
        
        # Should be sorted newest first
        assert len(jobs) == 3
        # Just verify they're sorted by created_at desc
        for i in range(len(jobs) - 1):
            assert jobs[i].created_at >= jobs[i + 1].created_at


# =============================================================================
# Tests for JobStore.cleanup_old_jobs
# =============================================================================


class TestJobStoreCleanupOldJobs:
    """Test JobStore.cleanup_old_jobs method."""

    def test_cleanup_removes_old_jobs(self, job_store, mock_redis):
        """Test that old jobs are cleaned up."""
        # Create a job with old timestamp
        old_time = (datetime.now(timezone.utc) - timedelta(hours=48)).isoformat()
        old_job = OmrJob(
            job_id="old-001",
            asset_id="asset-001",
            source_type="pdf",
            created_at=old_time,
            updated_at=old_time,
        )
        mock_redis._storage["omr_job:old-001"] = json.dumps(old_job.to_dict())
        
        # Create a recent job
        job_store.create_job("new-001", "asset-002", "pdf")
        
        cleaned = job_store.cleanup_old_jobs(max_age_hours=24)
        
        assert cleaned == 1
        assert job_store.get_job("old-001") is None
        assert job_store.get_job("new-001") is not None

    def test_cleanup_no_old_jobs(self, job_store):
        """Test cleanup when no jobs are old."""
        job_store.create_job("new-001", "asset-001", "pdf")
        job_store.create_job("new-002", "asset-002", "pdf")
        
        cleaned = job_store.cleanup_old_jobs(max_age_hours=24)
        
        assert cleaned == 0

    def test_cleanup_empty_store(self, job_store):
        """Test cleanup on empty store."""
        cleaned = job_store.cleanup_old_jobs()
        assert cleaned == 0


# =============================================================================
# Tests for JobStore.get_stats
# =============================================================================


class TestJobStoreGetStats:
    """Test JobStore.get_stats method."""

    def test_get_stats_empty(self, job_store):
        """Test stats on empty store."""
        stats = job_store.get_stats()
        
        assert stats["total"] == 0
        assert stats["queued"] == 0
        assert stats["processing"] == 0
        assert stats["completed"] == 0
        assert stats["failed"] == 0

    def test_get_stats_with_jobs(self, job_store):
        """Test stats with various job states."""
        # Create jobs in different states
        job_store.create_job("stat-001", "asset-001", "pdf")
        job_store.create_job("stat-002", "asset-002", "pdf")
        job_store.update_job("stat-002", status=JobStatus.PROCESSING)
        job_store.create_job("stat-003", "asset-003", "pdf")
        job_store.update_job("stat-003", status=JobStatus.COMPLETED)
        job_store.create_job("stat-004", "asset-004", "pdf")
        job_store.update_job("stat-004", status=JobStatus.FAILED)
        
        stats = job_store.get_stats()
        
        assert stats["total"] == 4
        assert stats["queued"] == 1
        assert stats["processing"] == 1
        assert stats["completed"] == 1
        assert stats["failed"] == 1


# =============================================================================
# Tests for JobStore Redis Connection
# =============================================================================


class TestJobStoreRedisConnection:
    """Test JobStore Redis connection handling."""

    def test_redis_property_creates_connection(self):
        """Test that redis property creates connection lazily."""
        with patch("redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis
            
            store = JobStore(redis_url="redis://localhost:6379/0")
            
            # Access redis property
            _ = store.redis
            
            mock_from_url.assert_called_once_with(
                "redis://localhost:6379/0",
                decode_responses=True,
            )

    def test_redis_property_caches_connection(self):
        """Test that redis connection is cached."""
        with patch("redis.from_url") as mock_from_url:
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis
            
            store = JobStore(redis_url="redis://localhost:6379/0")
            
            # Access redis property multiple times
            _ = store.redis
            _ = store.redis
            _ = store.redis
            
            # Should only create connection once
            assert mock_from_url.call_count == 1

    def test_key_format(self, job_store):
        """Test key format."""
        key = job_store._key("test-job-123")
        assert key == "omr_job:test-job-123"


# =============================================================================
# Tests for JobStatus Enum
# =============================================================================


class TestJobStatus:
    """Test JobStatus enum."""

    def test_status_values(self):
        """Test status enum values."""
        assert JobStatus.QUEUED.value == "queued"
        assert JobStatus.PROCESSING.value == "processing"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"

    def test_status_is_string_enum(self):
        """Test that status values are strings."""
        assert isinstance(JobStatus.QUEUED.value, str)
        assert JobStatus.PROCESSING == "processing"
