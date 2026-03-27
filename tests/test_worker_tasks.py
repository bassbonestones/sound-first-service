"""
Tests for app/worker/tasks.py module.

Tests Celery task definitions with mocked dependencies.
"""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from datetime import datetime, timezone


class TestRunAsync:
    """Tests for _run_async helper function."""
    
    def test_runs_coroutine_to_completion(self):
        """Should run async function and return result."""
        from app.worker.tasks import _run_async
        
        async def async_func():
            return "test_result"
        
        result = _run_async(async_func())
        
        assert result == "test_result"
    
    def test_handles_async_exceptions(self):
        """Should propagate exceptions from async functions."""
        from app.worker.tasks import _run_async
        
        async def failing_async():
            raise ValueError("async error")
        
        with pytest.raises(ValueError) as exc_info:
            _run_async(failing_async())
        
        assert "async error" in str(exc_info.value)


class TestProcessOmrJob:
    """Tests for process_omr_job Celery task."""
    
    @pytest.fixture
    def mock_job_store(self):
        """Mock job store."""
        with patch("app.worker.tasks.job_store") as mock:
            yield mock
    
    @pytest.fixture
    def mock_omr_provider(self):
        """Mock OMR provider."""
        with patch("app.worker.tasks.get_omr_provider") as mock:
            provider = MagicMock()
            provider.name = "mock_provider"
            provider.is_available = True
            mock.return_value = provider
            yield provider
    
    def test_updates_job_status_to_processing(
        self, mock_job_store, mock_omr_provider
    ):
        """Should update job status to PROCESSING at start."""
        from app.worker.tasks import process_omr_job, JobStatus
        
        # Mock successful result
        result = MagicMock()
        result.success = True
        result.confidence = 0.95
        result.music_xml = "<score></score>"
        result.measure_confidence = []
        result.uncertain_measures = []
        result.preview_path = None
        result.metadata = None
        result.processing_time_ms = 1000
        
        with patch("app.worker.tasks._run_async", return_value=result):
            # Call the underlying function directly, bypassing Celery decorator
            process_omr_job.run(
                job_id="job-123",
                asset_id="asset-456",
                input_path="/tmp/test.jpg",
                source_type="photo",
            )
        
        # Check PROCESSING status was set
        calls = mock_job_store.update_job.call_args_list
        first_call = calls[0]
        assert first_call[0][0] == "job-123"
        assert first_call[1]["status"] == JobStatus.PROCESSING
    
    def test_raises_when_provider_unavailable(
        self, mock_job_store, mock_omr_provider
    ):
        """Should fail when OMR provider is not available."""
        from app.worker.tasks import process_omr_job
        
        mock_omr_provider.is_available = False
        
        with pytest.raises(RuntimeError) as exc_info:
            process_omr_job.run(
                job_id="job-123",
                asset_id="asset-456",
                input_path="/tmp/test.jpg",
                source_type="photo",
            )
        
        assert "not available" in str(exc_info.value)
    
    def test_handles_successful_processing(
        self, mock_job_store, mock_omr_provider
    ):
        """Should update job with results on success."""
        from app.worker.tasks import process_omr_job, JobStatus
        
        # Mock metadata
        mock_metadata = MagicMock()
        mock_metadata.title = "Test Song"
        mock_metadata.composer = "Test Composer"
        mock_metadata.key_signature = "C major"
        mock_metadata.time_signature = "4/4"
        mock_metadata.tempo = 120
        mock_metadata.measure_count = 16
        mock_metadata.part_count = 1
        mock_metadata.page_count = 1
        
        # Mock successful result
        result = MagicMock()
        result.success = True
        result.confidence = 0.92
        result.music_xml = "<score-partwise></score-partwise>"
        result.measure_confidence = []
        result.uncertain_measures = []
        result.preview_path = "/tmp/preview.png"
        result.metadata = mock_metadata
        result.processing_time_ms = 2500
        
        with patch("app.worker.tasks._run_async", return_value=result):
            output = process_omr_job.run(
                job_id="job-123",
                asset_id="asset-456",
                input_path="/tmp/test.jpg",
                source_type="photo",
            )
        
        assert output["success"] is True
        assert output["job_id"] == "job-123"
        
        # Verify COMPLETED status was set
        final_call = mock_job_store.update_job.call_args_list[-1]
        assert final_call[1]["status"] == JobStatus.COMPLETED
        assert final_call[1]["progress"] == 100
    
    def test_handles_failed_processing(
        self, mock_job_store, mock_omr_provider
    ):
        """Should update job with error on failure."""
        from app.worker.tasks import process_omr_job, JobStatus
        
        # Mock failed result
        result = MagicMock()
        result.success = False
        result.error = "Could not parse sheet music"
        
        with patch("app.worker.tasks._run_async", return_value=result):
            output = process_omr_job.run(
                job_id="job-123",
                asset_id="asset-456",
                input_path="/tmp/test.jpg",
                source_type="photo",
            )
        
        assert output["success"] is False
        assert output["error"] == "Could not parse sheet music"
        
        # Verify FAILED status was set
        final_call = mock_job_store.update_job.call_args_list[-1]
        assert final_call[1]["status"] == JobStatus.FAILED
    
    def test_handles_exception_during_processing(
        self, mock_job_store, mock_omr_provider
    ):
        """Should catch exceptions and retry."""
        from app.worker.tasks import process_omr_job, JobStatus
        from celery.exceptions import Retry
        
        with patch("app.worker.tasks._run_async", side_effect=Exception("Unexpected error")):
            # The function retries on exception
            with pytest.raises((Exception, Retry)):
                process_omr_job.run(
                    job_id="job-123",
                    asset_id="asset-456",
                    input_path="/tmp/test.jpg",
                    source_type="photo",
                )
        
        # Verify FAILED status was set with error before retry
        failed_calls = [c for c in mock_job_store.update_job.call_args_list 
                       if c[1].get("status") == JobStatus.FAILED]
        assert len(failed_calls) > 0
    
    def test_handles_timeout(
        self, mock_job_store, mock_omr_provider
    ):
        """Should handle SoftTimeLimitExceeded."""
        from app.worker.tasks import process_omr_job, JobStatus
        from celery.exceptions import SoftTimeLimitExceeded
        
        with patch("app.worker.tasks._run_async", side_effect=SoftTimeLimitExceeded()):
            with pytest.raises(SoftTimeLimitExceeded):
                process_omr_job.run(
                    job_id="job-123",
                    asset_id="asset-456",
                    input_path="/tmp/test.jpg",
                    source_type="photo",
                )
        
        # Verify FAILED status was set
        final_call = mock_job_store.update_job.call_args_list[-1]
        assert final_call[1]["status"] == JobStatus.FAILED
        assert "time limit" in final_call[1]["error"]
    
    def test_applies_custom_options(
        self, mock_job_store, mock_omr_provider
    ):
        """Should apply custom options from request."""
        from app.worker.tasks import process_omr_job, OmrProviderOptions
        
        result = MagicMock()
        result.success = True
        result.confidence = 0.9
        result.music_xml = "<score></score>"
        result.measure_confidence = []
        result.uncertain_measures = []
        result.preview_path = None
        result.metadata = None
        result.processing_time_ms = 1000
        
        with patch("app.worker.tasks._run_async", return_value=result):
            process_omr_job.run(
                job_id="job-123",
                asset_id="asset-456",
                input_path="/tmp/test.jpg",
                source_type="photo",
                options={"output_format": "musicxml"},
            )
        
        # Task should complete without error
        assert mock_job_store.update_job.called
