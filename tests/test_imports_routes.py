"""
Tests for import routes (/imports/* endpoints).

Tests file upload, OMR processing, and score storage endpoints.
"""

import pytest
import io
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import patch

from app.db import Base, get_db
from app.routes.imports import router, _omr_jobs, _saved_scores


# =============================================================================
# DATABASE FIXTURES
# =============================================================================


@pytest.fixture(scope="function")
def test_engine():
    """Create an in-memory SQLite database for testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture(scope="function")
def test_session(test_engine):
    """Create a database session for testing."""
    TestingSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=test_engine
    )
    return TestingSessionLocal()


@pytest.fixture(scope="function")
def client(test_engine, test_session):
    """Create a test client with dependency overrides."""
    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        try:
            yield test_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Clear in-memory stores before each test
    _omr_jobs.clear()
    _saved_scores.clear()

    return TestClient(app)


@pytest.fixture
def sample_musicxml():
    """Return minimal valid MusicXML content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"
    "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
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
        <duration>4</duration>
        <type>whole</type>
      </note>
    </measure>
  </part>
</score-partwise>"""


# =============================================================================
# SIGNED URL TESTS
# =============================================================================


class TestSignedUrl:
    """Tests for signed URL endpoint."""

    def test_get_signed_url_success(self, client):
        """Test getting a signed URL for upload."""
        response = client.post(
            "/imports/upload/signed-url",
            json={
                "file_name": "test.jpg",
                "mime_type": "image/jpeg",
                "file_size": 1024,
                "source_type": "photo",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["asset_id"].startswith("asset_")
        assert data["upload_url"] is not None
        assert data["error"] is None

    def test_get_signed_url_all_source_types(self, client):
        """Test signed URL generation for all source types."""
        source_types = ["photo", "image", "pdf", "musicxml", "mxl"]

        for source_type in source_types:
            response = client.post(
                "/imports/upload/signed-url",
                json={
                    "file_name": f"test.{source_type}",
                    "mime_type": "application/octet-stream",
                    "source_type": source_type,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["asset_id"].startswith("asset_")

    def test_get_signed_url_empty_filename(self, client):
        """Test signed URL with empty filename."""
        response = client.post(
            "/imports/upload/signed-url",
            json={
                "file_name": "",
                "mime_type": "image/jpeg",
                "source_type": "photo",
            },
        )

        assert response.status_code == 422  # Validation error

    def test_get_signed_url_invalid_mime_type(self, client):
        """Test signed URL with invalid MIME type."""
        response = client.post(
            "/imports/upload/signed-url",
            json={
                "file_name": "test.jpg",
                "mime_type": "invalid",  # No slash
                "source_type": "photo",
            },
        )

        assert response.status_code == 422  # Validation error


# =============================================================================
# DIRECT UPLOAD TESTS
# =============================================================================


class TestDirectUpload:
    """Tests for direct file upload endpoint."""

    def test_upload_image_file(self, client, tmp_path):
        """Test uploading an image file."""
        # Create a fake image file
        file_content = b"fake image content"
        file = io.BytesIO(file_content)

        response = client.post(
            "/imports/upload/direct/asset_test123",
            files={"file": ("test.jpg", file, "image/jpeg")},
            data={"source_type": "photo"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["asset_id"] == "asset_test123"
        assert data["stored_size"] == len(file_content)

    def test_upload_musicxml_file(self, client, sample_musicxml):
        """Test uploading a MusicXML file."""
        file = io.BytesIO(sample_musicxml.encode("utf-8"))

        response = client.post(
            "/imports/upload/direct/asset_musicxml",
            files={"file": ("score.musicxml", file, "application/xml")},
            data={"source_type": "musicxml"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["asset_id"] == "asset_musicxml"

    def test_upload_invalid_source_type(self, client):
        """Test uploading with invalid source type."""
        file = io.BytesIO(b"content")

        response = client.post(
            "/imports/upload/direct/asset_test",
            files={"file": ("test.jpg", file, "image/jpeg")},
            data={"source_type": "invalid_type"},
        )

        assert response.status_code == 400


# =============================================================================
# FILE RETRIEVAL TESTS
# =============================================================================


class TestFileRetrieval:
    """Tests for file retrieval endpoint."""

    def test_get_uploaded_file(self, client):
        """Test retrieving an uploaded file."""
        # First upload a file
        file_content = b"test content"
        file = io.BytesIO(file_content)

        upload_response = client.post(
            "/imports/upload/direct/asset_retrieve",
            files={"file": ("test.txt", file, "text/plain")},
            data={"source_type": "musicxml"},
        )
        assert upload_response.status_code == 200

        # Now retrieve it
        get_response = client.get("/imports/files/asset_retrieve")
        assert get_response.status_code == 200
        assert get_response.content == file_content

    def test_get_nonexistent_file(self, client):
        """Test retrieving a file that doesn't exist."""
        response = client.get("/imports/files/nonexistent_asset")
        assert response.status_code == 404


# =============================================================================
# OMR SUBMISSION TESTS
# =============================================================================


class TestOmrSubmission:
    """Tests for OMR job submission endpoint."""

    def test_submit_omr_job(self, client):
        """Test submitting an OMR job."""
        # First upload a file
        file = io.BytesIO(b"image content")
        upload_response = client.post(
            "/imports/upload/direct/asset_omr",
            files={"file": ("score.jpg", file, "image/jpeg")},
            data={"source_type": "photo"},
        )
        assert upload_response.status_code == 200

        # Submit OMR job
        response = client.post(
            "/imports/omr/submit",
            json={
                "asset_id": "asset_omr",
                "source_type": "photo",
                "options": {
                    "language": "en",
                    "enhance_image": True,
                    "detect_parts": True,
                    "generate_preview": True,
                },
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["job_id"].startswith("omr_")
        assert data["estimated_duration_ms"] is not None

    def test_submit_omr_job_nonexistent_asset(self, client):
        """Test submitting OMR for nonexistent asset."""
        response = client.post(
            "/imports/omr/submit",
            json={
                "asset_id": "nonexistent_asset",
                "source_type": "photo",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    def test_submit_omr_job_different_source_types(self, client):
        """Test OMR job submission for different source types."""
        source_types = ["photo", "image", "pdf"]

        for source_type in source_types:
            # Upload file
            file = io.BytesIO(b"content")
            asset_id = f"asset_{source_type}"
            client.post(
                f"/imports/upload/direct/{asset_id}",
                files={"file": (f"test.{source_type}", file, "image/jpeg")},
                data={"source_type": source_type},
            )

            # Submit OMR
            response = client.post(
                "/imports/omr/submit",
                json={
                    "asset_id": asset_id,
                    "source_type": source_type,
                },
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


# =============================================================================
# OMR STATUS TESTS
# =============================================================================


class TestOmrStatus:
    """Tests for OMR job status endpoint."""

    def test_get_omr_status(self, client):
        """Test getting OMR job status."""
        # Upload and submit job
        file = io.BytesIO(b"image content")
        client.post(
            "/imports/upload/direct/asset_status",
            files={"file": ("score.jpg", file, "image/jpeg")},
            data={"source_type": "photo"},
        )

        submit_response = client.post(
            "/imports/omr/submit",
            json={"asset_id": "asset_status", "source_type": "photo"},
        )
        job_id = submit_response.json()["job_id"]

        # Check status
        response = client.get(f"/imports/omr/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] in ["queued", "processing", "completed", "failed"]

    def test_get_omr_status_completed_has_result(self, client):
        """Test that completed jobs have results (with mock provider)."""
        # Upload and submit job
        file = io.BytesIO(b"image content")
        client.post(
            "/imports/upload/direct/asset_complete",
            files={"file": ("score.jpg", file, "image/jpeg")},
            data={"source_type": "photo"},
        )

        submit_response = client.post(
            "/imports/omr/submit",
            json={"asset_id": "asset_complete", "source_type": "photo"},
        )
        job_id = submit_response.json()["job_id"]

        # With mock provider, job should be completed
        response = client.get(f"/imports/omr/status/{job_id}")

        data = response.json()
        # Mock provider completes immediately
        assert data["status"] == "completed"
        assert data["result"] is not None
        assert data["result"]["confidence"] > 0
        assert data["result"]["music_xml"] is not None

    def test_get_omr_status_nonexistent_job(self, client):
        """Test getting status of nonexistent job."""
        response = client.get("/imports/omr/status/nonexistent_job")
        assert response.status_code == 404


# =============================================================================
# SCORE STORAGE TESTS
# =============================================================================


class TestScoreStorage:
    """Tests for score storage endpoints."""

    def test_save_score(self, client):
        """Test saving a score."""
        response = client.post(
            "/imports/scores",
            json={
                "source_asset_id": "asset_123",
                "omr_job_id": "omr_456",
                "score_data": '{"title": "Test Score"}',
                "metadata_overrides": {"title": "My Score"},
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["score_id"].startswith("score_")
        assert data["saved_at"] is not None

    def test_save_score_minimal(self, client):
        """Test saving a score with minimal data."""
        response = client.post(
            "/imports/scores",
            json={
                "source_asset_id": "asset_789",
                "omr_job_id": None,
                "score_data": "{}",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_score(self, client):
        """Test retrieving a saved score."""
        # First save a score
        save_response = client.post(
            "/imports/scores",
            json={
                "source_asset_id": "asset_get",
                "score_data": '{"title": "Retrievable Score"}',
            },
        )
        score_id = save_response.json()["score_id"]

        # Retrieve it
        response = client.get(f"/imports/scores/{score_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["score"]["score_id"] == score_id
        assert data["score"]["source_asset_id"] == "asset_get"

    def test_get_nonexistent_score(self, client):
        """Test retrieving a nonexistent score."""
        response = client.get("/imports/scores/nonexistent_score")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is False
        assert "not found" in data["error"].lower()

    def test_delete_score(self, client):
        """Test deleting a saved score."""
        # First save a score
        save_response = client.post(
            "/imports/scores",
            json={
                "source_asset_id": "asset_delete",
                "score_data": "{}",
            },
        )
        score_id = save_response.json()["score_id"]

        # Delete it
        response = client.delete(f"/imports/scores/{score_id}")
        assert response.status_code == 200

        # Verify it's gone
        get_response = client.get(f"/imports/scores/{score_id}")
        assert get_response.json()["success"] is False

    def test_delete_nonexistent_score(self, client):
        """Test deleting a nonexistent score."""
        response = client.delete("/imports/scores/nonexistent_score")
        assert response.status_code == 404


# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================


class TestHealthCheck:
    """Tests for health check endpoint."""

    def test_health_check(self, client):
        """Test health check returns expected data."""
        response = client.get("/imports/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "storage_provider" in data
        assert "omr_provider" in data
        assert "active_jobs" in data


# =============================================================================
# SCHEMA VALIDATION TESTS
# =============================================================================


class TestSchemaValidation:
    """Tests for request schema validation."""

    def test_signed_url_request_validates_source_type(self, client):
        """Test that invalid source types are rejected."""
        response = client.post(
            "/imports/upload/signed-url",
            json={
                "file_name": "test.jpg",
                "mime_type": "image/jpeg",
                "source_type": "invalid_type",
            },
        )

        assert response.status_code == 422

    def test_omr_submit_validates_asset_id(self, client):
        """Test that empty asset ID is rejected."""
        response = client.post(
            "/imports/omr/submit",
            json={
                "asset_id": "",
                "source_type": "photo",
            },
        )

        assert response.status_code == 422

    def test_save_score_validates_source_asset_id(self, client):
        """Test that empty source asset ID is rejected."""
        response = client.post(
            "/imports/scores",
            json={
                "source_asset_id": "",
                "score_data": "{}",
            },
        )

        assert response.status_code == 422


# =============================================================================
# END-TO-END WORKFLOW TESTS
# =============================================================================


class TestEndToEndWorkflow:
    """Tests for complete import workflows."""

    def test_photo_to_score_workflow(self, client):
        """Test complete workflow: photo upload -> OMR -> save score."""
        # 1. Get signed URL
        url_response = client.post(
            "/imports/upload/signed-url",
            json={
                "file_name": "sheet_music.jpg",
                "mime_type": "image/jpeg",
                "source_type": "photo",
            },
        )
        assert url_response.status_code == 200
        asset_id = url_response.json()["asset_id"]

        # 2. Upload file
        file = io.BytesIO(b"photo content")
        upload_response = client.post(
            f"/imports/upload/direct/{asset_id}",
            files={"file": ("sheet_music.jpg", file, "image/jpeg")},
            data={"source_type": "photo"},
        )
        assert upload_response.status_code == 200

        # 3. Submit OMR job
        omr_response = client.post(
            "/imports/omr/submit",
            json={"asset_id": asset_id, "source_type": "photo"},
        )
        assert omr_response.status_code == 200
        job_id = omr_response.json()["job_id"]

        # 4. Check status (mock completes immediately)
        status_response = client.get(f"/imports/omr/status/{job_id}")
        assert status_response.status_code == 200
        result = status_response.json()["result"]
        assert result is not None

        # 5. Save score
        save_response = client.post(
            "/imports/scores",
            json={
                "source_asset_id": asset_id,
                "omr_job_id": job_id,
                "score_data": result["music_xml"],
            },
        )
        assert save_response.status_code == 200
        score_id = save_response.json()["score_id"]

        # 6. Retrieve score
        get_response = client.get(f"/imports/scores/{score_id}")
        assert get_response.status_code == 200
        assert get_response.json()["success"] is True

    def test_musicxml_direct_import_workflow(self, client, sample_musicxml):
        """Test workflow for direct MusicXML import (no OMR needed)."""
        # 1. Get signed URL
        url_response = client.post(
            "/imports/upload/signed-url",
            json={
                "file_name": "score.musicxml",
                "mime_type": "application/xml",
                "source_type": "musicxml",
            },
        )
        asset_id = url_response.json()["asset_id"]

        # 2. Upload MusicXML
        file = io.BytesIO(sample_musicxml.encode("utf-8"))
        upload_response = client.post(
            f"/imports/upload/direct/{asset_id}",
            files={"file": ("score.musicxml", file, "application/xml")},
            data={"source_type": "musicxml"},
        )
        assert upload_response.status_code == 200

        # 3. Save directly (no OMR needed for MusicXML)
        save_response = client.post(
            "/imports/scores",
            json={
                "source_asset_id": asset_id,
                "omr_job_id": None,
                "score_data": sample_musicxml,
            },
        )
        assert save_response.status_code == 200
        assert save_response.json()["success"] is True
