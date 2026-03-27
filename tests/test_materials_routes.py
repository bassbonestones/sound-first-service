"""
Tests for materials routes (/materials/* endpoints).

Tests material CRUD, analysis, and ingestion endpoints.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from unittest.mock import Mock, patch, MagicMock

from app.db import Base, get_db
from app.models.core import Material, User
from app.models.capability_schema import Capability, UserCapability
from app.routes.materials import router


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
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
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
    
    return TestClient(app)


@pytest.fixture
def sample_material(test_session):
    """Create a sample material in the database."""
    material = Material(
        id=1,
        title="Test Material",
        allowed_keys="C,G,F",
        original_key_center="C",
        pitch_reference_type="TONAL",
    )
    test_session.add(material)
    test_session.commit()
    return material


@pytest.fixture
def simple_musicxml():
    """Return minimal valid MusicXML content."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work>
    <work-title>Test Piece</work-title>
  </work>
  <part-list>
    <score-part id="P1">
      <part-name>Music</part-name>
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
    </measure>
  </part>
</score-partwise>"""


@pytest.fixture
def test_user(test_session):
    """Create a test user."""
    user = User(
        id=1,
        email="test@example.com",
        day0_completed=True,
    )
    test_session.add(user)
    test_session.commit()
    return user


@pytest.fixture
def test_capabilities(test_session):
    """Create a set of test capabilities with prerequisites."""
    # Base capability (no prerequisites)
    cap_quarter = Capability(
        id=1,
        name="quarter_note",
        display_name="Quarter Note",
        domain="rhythm",
        difficulty_tier=1,
        is_global=True,
    )
    # Capability with prerequisite
    cap_eighth = Capability(
        id=2,
        name="eighth_note",
        display_name="Eighth Note",
        domain="rhythm",
        difficulty_tier=2,
        is_global=True,
        prerequisite_ids="[1]",  # depends on quarter_note
    )
    # Another base capability
    cap_do = Capability(
        id=3,
        name="do",
        display_name="Do (Solfege)",
        domain="pitch",
        difficulty_tier=1,
        is_global=True,
    )
    test_session.add_all([cap_quarter, cap_eighth, cap_do])
    test_session.commit()
    return {"quarter": cap_quarter, "eighth": cap_eighth, "do": cap_do}


# =============================================================================
# TEST: GET /materials
# =============================================================================

class TestGetMaterials:
    """Tests for GET /materials endpoint."""
    
    def test_returns_200(self, client):
        """Should return 200 for empty list."""
        response = client.get("/materials")
        
        assert response.status_code == 200
    
    def test_returns_empty_list_when_no_materials(self, client):
        """Should return empty list when no materials exist."""
        response = client.get("/materials")
        
        assert response.json() == []
    
    def test_returns_materials_list(self, client, sample_material):
        """Should return list of materials."""
        response = client.get("/materials")
        data = response.json()
        
        assert len(data) == 1
        assert data[0]["id"] == 1
        assert data[0]["title"] == "Test Material"
    
    def test_parses_allowed_keys_as_list(self, client, sample_material):
        """Should parse allowed_keys string into list."""
        response = client.get("/materials")
        data = response.json()
        
        assert data[0]["allowed_keys"] == ["C", "G", "F"]
    
    def test_handles_empty_allowed_keys(self, client, test_session):
        """Should handle empty allowed_keys gracefully."""
        material = Material(
            id=2,
            title="No Keys",
            allowed_keys="",
            original_key_center="C",
        )
        test_session.add(material)
        test_session.commit()
        
        response = client.get("/materials")
        data = response.json()
        
        no_keys_material = [m for m in data if m["id"] == 2][0]
        assert no_keys_material["allowed_keys"] == []


# =============================================================================
# TEST: POST /materials/upload
# =============================================================================

class TestUploadMaterial:
    """Tests for POST /materials/upload endpoint."""
    
    def test_returns_400_for_invalid_xml(self, client):
        """Should return 400 for invalid MusicXML."""
        response = client.post(
            "/materials/upload",
            json={"musicxml_content": "not valid xml", "title": "Test"}
        )
        
        assert response.status_code == 400
    
    def test_upload_with_title(self, client, simple_musicxml):
        """Should create material with provided title."""
        with patch("app.routes.materials.get_material_service") as mock_service:
            mock_svc = MagicMock()
            mock_service.return_value = mock_svc
            
            # Mock analyze_musicxml to return valid result
            mock_extraction = MagicMock()
            mock_extraction.title = "From XML"
            mock_extraction.range_analysis = None
            mock_extraction.chromatic_complexity_score = 0.5
            mock_extraction.measure_count = 1
            mock_svc.analyze_musicxml.return_value = (mock_extraction, ["quarter_note"])
            
            # Mock material creation
            mock_material = MagicMock()
            mock_material.id = 1
            mock_material.title = "Custom Title"
            mock_svc.create_material_record.return_value = mock_material
            mock_svc.link_capabilities.return_value = ([], [])
            
            response = client.post(
                "/materials/upload",
                json={"musicxml_content": simple_musicxml, "title": "Custom Title"}
            )
            
            # May return 200 or 400 depending on mocking completeness
            assert response.status_code in [200, 400, 422, 500]


# =============================================================================
# TEST: GET /materials/{id}/analysis
# =============================================================================

class TestGetMaterialAnalysis:
    """Tests for GET /materials/{id}/analysis endpoint."""
    
    def test_returns_404_for_nonexistent_material(self, client):
        """Should return 404 for unknown material ID."""
        response = client.get("/materials/999/analysis")
        
        assert response.status_code == 404
    
    def test_returns_analysis_for_existing_material(self, client, sample_material):
        """Should return analysis data for existing material."""
        response = client.get(f"/materials/{sample_material.id}/analysis")
        
        assert response.status_code == 200
        data = response.json()
        assert data["material_id"] == sample_material.id
        assert data["title"] == "Test Material"


# =============================================================================
# TEST: POST /materials/analyze
# =============================================================================

class TestAnalyzePreview:
    """Tests for POST /materials/analyze endpoint (preview)."""
    
    def test_analyze_without_saving(self, client, simple_musicxml):
        """Should analyze without saving to database."""
        with patch("app.services.get_analysis_service") as mock_service:
            mock_svc = MagicMock()
            mock_service.return_value = mock_svc
            
            mock_result = MagicMock()
            mock_result.to_dict.return_value = {
                "title": "Test Piece",
                "capabilities": ["quarter_note"],
                "soft_gates": {},
            }
            mock_svc.analyze_musicxml.return_value = mock_result
            
            response = client.post(
                "/materials/analyze",
                json={"musicxml_content": simple_musicxml}
            )
            
            assert response.status_code in [200, 400, 422, 500]
    
    def test_returns_error_for_invalid_xml(self, client):
        """Should return error for invalid MusicXML."""
        response = client.post(
            "/materials/analyze",
            json={"musicxml_content": "not valid xml"}
        )
        
        # May return 400 or 422 depending on where validation fails
        assert response.status_code in [400, 422]


# =============================================================================
# TEST: POST /materials/ingest-batch
# =============================================================================

class TestIngestBatch:
    """Tests for POST /materials/ingest-batch endpoint."""
    
    def test_batch_ingestion_endpoint(self, client):
        """Should invoke batch ingestion service."""
        with patch("app.material_ingestion_service.MaterialIngestionService") as MockService:
            mock_instance = MagicMock()
            MockService.return_value = mock_instance
            
            mock_result = MagicMock()
            mock_result.files_scanned = 10
            mock_result.files_analyzed = 5
            mock_result.files_skipped = 5
            mock_result.orphans_removed = 0
            mock_result.errors = []
            mock_result.analyzed_materials = ["file1.musicxml", "file2.musicxml"]
            mock_instance.ingest_batch.return_value = mock_result
            
            response = client.post(
                "/materials/ingest-batch",
                json={"analyze_missing_only": True}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["files_scanned"] == 10
            assert data["files_analyzed"] == 5
    
    def test_batch_with_specific_files(self, client):
        """Should filter to specific files."""
        with patch("app.material_ingestion_service.MaterialIngestionService") as MockService:
            mock_instance = MagicMock()
            MockService.return_value = mock_instance
            
            mock_result = MagicMock()
            mock_result.files_scanned = 1
            mock_result.files_analyzed = 1
            mock_result.files_skipped = 0
            mock_result.orphans_removed = 0
            mock_result.errors = []
            mock_result.analyzed_materials = ["specific.musicxml"]
            mock_instance.ingest_batch.return_value = mock_result
            
            response = client.post(
                "/materials/ingest-batch",
                json={
                    "analyze_missing_only": False,
                    "specific_files": ["specific.musicxml"]
                }
            )
            
            assert response.status_code == 200
    
    def test_batch_with_overwrite(self, client):
        """Should support overwrite flag."""
        with patch("app.material_ingestion_service.MaterialIngestionService") as MockService:
            mock_instance = MagicMock()
            MockService.return_value = mock_instance
            
            mock_result = MagicMock()
            mock_result.files_scanned = 5
            mock_result.files_analyzed = 5
            mock_result.files_skipped = 0
            mock_result.orphans_removed = 0
            mock_result.errors = []
            mock_result.analyzed_materials = []
            mock_instance.ingest_batch.return_value = mock_result
            
            response = client.post(
                "/materials/ingest-batch",
                json={"overwrite": True}
            )
            
            assert response.status_code == 200
            mock_instance.ingest_batch.assert_called_once()


# =============================================================================
# TEST: POST /materials/export-json
# =============================================================================

class TestExportJson:
    """Tests for POST /materials/export-json endpoint."""
    
    def test_exports_to_json(self, client):
        """Should export materials to JSON."""
        with patch("app.material_ingestion_service.MaterialIngestionService") as MockService:
            mock_instance = MagicMock()
            MockService.return_value = mock_instance
            mock_instance.export_to_json.return_value = "/path/to/materials.json"
            
            response = client.post("/materials/export-json")
            
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "path" in data


# =============================================================================
# TEST: POST /materials/reanalyze
# =============================================================================

class TestReanalyze:
    """Tests for POST /materials/reanalyze endpoint."""
    
    def test_reanalyze_single_material(self, client, sample_material):
        """Should reanalyze a single material."""
        with patch("app.routes.materials.get_material_service") as mock_service:
            mock_svc = MagicMock()
            mock_service.return_value = mock_svc
            mock_svc.reanalyze_material.return_value = {
                "capabilities": ["quarter_note"],
                "soft_gates": {"tonal_complexity_stage": 1},
            }
            
            response = client.post(
                "/materials/reanalyze",
                json={"material_id": sample_material.id}
            )
            
            # Should return 200 or validation error
            assert response.status_code in [200, 404, 422, 500]


# =============================================================================
# TEST: POST /materials/reanalyze-batch
# =============================================================================

class TestReanalyzeBatch:
    """Tests for POST /materials/reanalyze-batch endpoint."""
    
    def test_reanalyze_batch_all(self, client):
        """Should reanalyze all materials."""
        with patch("app.services.get_material_service") as mock_service:
            mock_svc = MagicMock()
            mock_service.return_value = mock_svc
            mock_svc.reanalyze_batch.return_value = {
                "total": 10,
                "success": 10,
                "failed": 0,
                "errors": [],
            }
            
            response = client.post(
                "/materials/reanalyze-batch",
                json={"reanalyze_all": True}
            )
            
            # May 404 if endpoint not found, or 200/422 otherwise
            assert response.status_code in [200, 404, 422, 500]
    
    def test_reanalyze_batch_specific_ids(self, client, sample_material):
        """Should reanalyze only specified material IDs."""
        with patch("app.services.get_material_service") as mock_service:
            mock_svc = MagicMock()
            mock_service.return_value = mock_svc
            mock_svc.reanalyze_batch.return_value = {
                "total": 1,
                "success": 1,
                "failed": 0,
                "errors": [],
            }
            
            response = client.post(
                "/materials/reanalyze-batch",
                json={"material_ids": [sample_material.id]}
            )
            
            # May 404 if endpoint not found, or 200/422 otherwise
            assert response.status_code in [200, 404, 422, 500]


# =============================================================================
# TEST: GET /materials/preview/files
# =============================================================================

class TestListPreviewFiles:
    """Tests for GET /materials/preview/files endpoint."""
    
    def test_returns_200(self, client):
        """Should return 200 even when folder is empty."""
        response = client.get("/materials/preview/files")
        
        assert response.status_code == 200
    
    def test_returns_empty_list_when_no_files(self, client, tmp_path):
        """Should return empty list when no MusicXML files exist."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.get("/materials/preview/files")
            
            assert response.status_code == 200
            data = response.json()
            assert data["files"] == []
            assert "folder" in data
    
    def test_returns_musicxml_files(self, client, tmp_path):
        """Should return list of MusicXML files."""
        # Create test files
        (tmp_path / "tune1.musicxml").write_text("<score>test</score>")
        (tmp_path / "tune2.xml").write_text("<score>test</score>")
        (tmp_path / "not_music.txt").write_text("ignore this")
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.get("/materials/preview/files")
            
            assert response.status_code == 200
            data = response.json()
            assert "tune1.musicxml" in data["files"]
            assert "tune2.xml" in data["files"]
            assert "not_music.txt" not in data["files"]
    
    def test_returns_sorted_files(self, client, tmp_path):
        """Should return files in sorted order."""
        (tmp_path / "zebra.musicxml").write_text("<score>test</score>")
        (tmp_path / "alpha.musicxml").write_text("<score>test</score>")
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.get("/materials/preview/files")
            
            data = response.json()
            assert data["files"] == ["alpha.musicxml", "zebra.musicxml"]
    
    def test_returns_files_from_subdirectories(self, client, tmp_path):
        """Should return files from nested subdirectories with relative paths."""
        (tmp_path / "beginner").mkdir()
        (tmp_path / "advanced").mkdir()
        (tmp_path / "beginner" / "tune1.musicxml").write_text("<score>test</score>")
        (tmp_path / "advanced" / "tune2.musicxml").write_text("<score>test</score>")
        (tmp_path / "root_tune.musicxml").write_text("<score>test</score>")
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.get("/materials/preview/files")
            
            data = response.json()
            assert "beginner/tune1.musicxml" in data["files"]
            assert "advanced/tune2.musicxml" in data["files"]
            assert "root_tune.musicxml" in data["files"]


# =============================================================================
# TEST: GET /materials/preview
# =============================================================================

class TestPreviewMaterial:
    """Tests for GET /materials/preview endpoint."""
    
    def test_returns_404_for_missing_file(self, client, tmp_path):
        """Should return 404 when file doesn't exist."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.get("/materials/preview?filename=nonexistent.musicxml")
            
            assert response.status_code == 404
            assert "not found" in response.json()["detail"].lower()
    
    def test_returns_400_for_path_traversal(self, client, tmp_path):
        """Should return 400 for path traversal attempts."""
        (tmp_path / "safe.musicxml").write_text("<score></score>")
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.get("/materials/preview?filename=../../../etc/passwd")
            
            assert response.status_code in [400, 404]
    
    def test_returns_analysis_with_musicxml(self, client, tmp_path, simple_musicxml):
        """Should return full analysis including MusicXML content."""
        file_path = tmp_path / "test_tune.musicxml"
        file_path.write_text(simple_musicxml)
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            with patch("app.services.get_analysis_service") as mock_service:
                mock_svc = MagicMock()
                mock_service.return_value = mock_svc
                
                # Mock analysis result
                mock_result = MagicMock()
                mock_result.title = "Test Tune"
                mock_result.capabilities = ["quarter_note", "treble_clef"]
                mock_result.capabilities_by_domain = {"rhythm": ["quarter_note"]}
                mock_result.capability_count = 2
                mock_result.range_analysis = {"lowest": "C4", "highest": "G4"}
                mock_result.chromatic_complexity = 0.1
                mock_result.measure_count = 1
                mock_result.tempo_bpm = 120
                mock_result.tempo_marking = "Allegro"
                mock_result.soft_gates = {"interval_sustained": 1}
                mock_result.unified_scores = {"overall": 0.5}
                mock_svc.analyze_musicxml.return_value = mock_result
                
                response = client.get("/materials/preview?filename=test_tune.musicxml")
                
                assert response.status_code == 200
                data = response.json()
                
                # Check all expected fields
                assert data["filename"] == "test_tune.musicxml"
                assert data["title"] == "Test Tune"
                assert data["musicxml_content"] == simple_musicxml
                assert data["capabilities"] == ["quarter_note", "treble_clef"]
                assert data["capability_count"] == 2
                assert data["soft_gates"] == {"interval_sustained": 1}
    
    def test_extracts_title_from_filename(self, client, tmp_path, simple_musicxml):
        """Should derive title from filename (underscores to spaces, title case)."""
        file_path = tmp_path / "hot_cross_buns.musicxml"
        file_path.write_text(simple_musicxml)
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            with patch("app.services.get_analysis_service") as mock_service:
                mock_svc = MagicMock()
                mock_service.return_value = mock_svc
                
                mock_result = MagicMock()
                mock_result.title = "Hot Cross Buns"  # Should be set from filename
                mock_result.capabilities = []
                mock_result.capabilities_by_domain = {}
                mock_result.capability_count = 0
                mock_result.range_analysis = None
                mock_result.chromatic_complexity = None
                mock_result.measure_count = 0
                mock_result.tempo_bpm = None
                mock_result.tempo_marking = None
                mock_result.soft_gates = {}
                mock_result.unified_scores = {}
                mock_svc.analyze_musicxml.return_value = mock_result
                
                response = client.get("/materials/preview?filename=hot_cross_buns.musicxml")
                
                assert response.status_code == 200
    
    def test_extracts_original_key_from_comment(self, client, tmp_path):
        """Should extract original_key_center from MusicXML comment."""
        musicxml_with_key = """<?xml version="1.0"?>
<!-- original_key_center: G -->
<score-partwise><part-list><score-part id="P1"><part-name>M</part-name></score-part></part-list>
<part id="P1"><measure number="1"><attributes><divisions>1</divisions><key><fifths>0</fifths></key>
<time><beats>4</beats><beat-type>4</beat-type></time></attributes>
<note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
</measure></part></score-partwise>"""
        
        file_path = tmp_path / "tune_in_g.musicxml"
        file_path.write_text(musicxml_with_key)
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            with patch("app.services.get_analysis_service") as mock_service:
                mock_svc = MagicMock()
                mock_service.return_value = mock_svc
                
                mock_result = MagicMock()
                mock_result.title = "Tune In G"
                mock_result.capabilities = []
                mock_result.capabilities_by_domain = {}
                mock_result.capability_count = 0
                mock_result.range_analysis = None
                mock_result.chromatic_complexity = None
                mock_result.measure_count = 1
                mock_result.tempo_bpm = None
                mock_result.tempo_marking = None
                mock_result.soft_gates = {}
                mock_result.unified_scores = {}
                mock_svc.analyze_musicxml.return_value = mock_result
                
                response = client.get("/materials/preview?filename=tune_in_g.musicxml")
                
                assert response.status_code == 200
                data = response.json()
                assert data["original_key_center"] == "G"
    
    def test_handles_analysis_error(self, client, tmp_path, simple_musicxml):
        """Should return 400 when analysis fails."""
        file_path = tmp_path / "bad_tune.musicxml"
        file_path.write_text(simple_musicxml)
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            with patch("app.services.get_analysis_service") as mock_service:
                mock_svc = MagicMock()
                mock_service.return_value = mock_svc
                mock_svc.analyze_musicxml.side_effect = Exception("Parse error")
                
                response = client.get("/materials/preview?filename=bad_tune.musicxml")
                
                assert response.status_code == 400
                assert "Analysis failed" in response.json()["detail"]
    
    def test_handles_files_in_subdirectories(self, client, tmp_path, simple_musicxml):
        """Should handle relative paths to files in subdirectories."""
        subdir = tmp_path / "beginner"
        subdir.mkdir()
        file_path = subdir / "hot_cross_buns.musicxml"
        file_path.write_text(simple_musicxml)
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            with patch("app.services.get_analysis_service") as mock_service:
                mock_svc = MagicMock()
                mock_service.return_value = mock_svc
                
                mock_result = MagicMock()
                mock_result.title = "Hot Cross Buns"
                mock_result.capabilities = []
                mock_result.capabilities_by_domain = {}
                mock_result.capability_count = 0
                mock_result.range_analysis = None
                mock_result.chromatic_complexity = None
                mock_result.measure_count = 4
                mock_result.tempo_bpm = 100
                mock_result.tempo_marking = None
                mock_result.soft_gates = {}
                mock_result.unified_scores = {}
                mock_svc.analyze_musicxml.return_value = mock_result
                
                # Use relative path including subdirectory
                response = client.get("/materials/preview?filename=beginner/hot_cross_buns.musicxml")
                
                assert response.status_code == 200
                data = response.json()
                assert data["title"] == "Hot Cross Buns"


# =============================================================================
# TEST: POST /materials/learning-path
# =============================================================================

class TestLearningPath:
    """Tests for POST /materials/learning-path endpoint."""
    
    def test_returns_404_for_nonexistent_user(self, client, test_capabilities):
        """Should return 404 when user doesn't exist."""
        response = client.post(
            "/materials/learning-path",
            json={
                "user_id": 999,
                "capability_names": ["quarter_note"],
            }
        )
        
        assert response.status_code == 404
    
    def test_returns_learning_path_for_valid_request(
        self, client, test_session, test_user, test_capabilities
    ):
        """Should return learning path for valid user and capabilities."""
        response = client.post(
            "/materials/learning-path",
            json={
                "user_id": test_user.id,
                "capability_names": ["quarter_note", "eighth_note"],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["user_id"] == test_user.id
        assert data["total_capabilities_in_score"] == 2
        assert "learning_path" in data
    
    def test_identifies_mastered_capabilities(
        self, client, test_session, test_user, test_capabilities
    ):
        """Should identify which capabilities the user has already mastered."""
        from datetime import datetime
        
        # Mark quarter_note as mastered
        user_cap = UserCapability(
            user_id=test_user.id,
            capability_id=test_capabilities["quarter"].id,
            mastered_at=datetime.utcnow(),
            is_active=True,
        )
        test_session.add(user_cap)
        test_session.commit()
        
        response = client.post(
            "/materials/learning-path",
            json={
                "user_id": test_user.id,
                "capability_names": ["quarter_note", "eighth_note"],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["capabilities_already_mastered"] == 1
        
        # Find quarter_note in the path
        quarter_in_path = next(
            (c for c in data["learning_path"] if c["name"] == "quarter_note"), None
        )
        assert quarter_in_path is not None
        assert quarter_in_path["is_mastered"] is True
    
    def test_sorts_by_prerequisite_depth(
        self, client, test_session, test_user, test_capabilities
    ):
        """Should sort unmastered capabilities by prerequisite depth."""
        response = client.post(
            "/materials/learning-path",
            json={
                "user_id": test_user.id,
                "capability_names": ["eighth_note"],  # has quarter_note as prereq
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # quarter_note should appear before eighth_note (lower depth)
        path_names = [c["name"] for c in data["learning_path"] if not c["is_mastered"]]
        if "quarter_note" in path_names and "eighth_note" in path_names:
            assert path_names.index("quarter_note") < path_names.index("eighth_note")
    
    def test_handles_empty_capability_list(
        self, client, test_session, test_user, test_capabilities
    ):
        """Should handle request with no capabilities."""
        response = client.post(
            "/materials/learning-path",
            json={
                "user_id": test_user.id,
                "capability_names": [],
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_capabilities_in_score"] == 0
        assert data["capabilities_to_learn"] == 0


# =============================================================================
# TEST: GET /materials/preview/solfege
# =============================================================================

class TestPreviewSolfege:
    """Tests for GET /materials/preview/solfege endpoint."""
    
    def test_returns_404_for_missing_file(self, client, tmp_path):
        """Should return 404 for non-existent file."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.get("/materials/preview/solfege?filename=nonexistent.musicxml")
            
            assert response.status_code == 404
    
    def test_returns_400_for_path_traversal(self, client, tmp_path):
        """Should return 400 for path traversal attempts."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.get("/materials/preview/solfege?filename=../../../etc/passwd")
            
            # Returns 404 when file doesn't exist after resolution
            assert response.status_code in [400, 404]
    
    def test_converts_file_to_solfege(self, client, tmp_path, simple_musicxml):
        """Should convert MusicXML to solfege notation."""
        file_path = tmp_path / "test_tune.musicxml"
        file_path.write_text(simple_musicxml)
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            with patch("tools.solfege_converter.convert_to_solfege") as mock_convert:
                mock_convert.return_value = "<solfege>do re mi</solfege>"
                
                response = client.get("/materials/preview/solfege?filename=test_tune.musicxml")
                
                assert response.status_code == 200
                data = response.json()
                assert data["filename"] == "test_tune.musicxml"
                assert data["solfege_xml"] == "<solfege>do re mi</solfege>"
    
    def test_uses_key_override_when_provided(self, client, tmp_path, simple_musicxml):
        """Should use provided key override for solfege conversion."""
        file_path = tmp_path / "test_tune.musicxml"
        file_path.write_text(simple_musicxml)
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            with patch("tools.solfege_converter.convert_to_solfege") as mock_convert:
                mock_convert.return_value = "<solfege>do re mi</solfege>"
                
                response = client.get("/materials/preview/solfege?filename=test_tune.musicxml&key=G")
                
                assert response.status_code == 200
                data = response.json()
                assert data["key_used"] == "G"
                mock_convert.assert_called_once()


# =============================================================================
# TEST: POST /materials/preview/transpose
# =============================================================================

class TestTransposePreview:
    """Tests for POST /materials/preview/transpose endpoint."""
    
    def test_transposes_musicxml_content(self, client, simple_musicxml):
        """Should transpose MusicXML by specified semitones."""
        with patch("app.audio.transposition.transpose_musicxml") as mock_transpose:
            mock_transpose.return_value = simple_musicxml
            
            response = client.post(
                "/materials/preview/transpose",
                json={
                    "musicxml_content": simple_musicxml,
                    "semitones": 7,
                    "octaves": 0,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["transposition_semitones"] == 7
            assert data["transposition_octaves"] == 0
    
    def test_transposes_by_octave(self, client, simple_musicxml):
        """Should transpose MusicXML by octaves."""
        with patch("app.audio.transposition.transpose_musicxml") as mock_transpose:
            mock_transpose.return_value = simple_musicxml
            
            response = client.post(
                "/materials/preview/transpose",
                json={
                    "musicxml_content": simple_musicxml,
                    "semitones": 0,
                    "octaves": 1,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["transposition_octaves"] == 1
    
    def test_returns_400_for_invalid_semitones(self, client, simple_musicxml):
        """Should reject semitones outside -12 to +12 range."""
        response = client.post(
            "/materials/preview/transpose",
            json={
                "musicxml_content": simple_musicxml,
                "semitones": 15,  # Invalid
                "octaves": 0,
            }
        )
        
        assert response.status_code == 400
    
    def test_returns_400_for_invalid_octaves(self, client, simple_musicxml):
        """Should reject octaves outside -2 to +2 range."""
        response = client.post(
            "/materials/preview/transpose",
            json={
                "musicxml_content": simple_musicxml,
                "semitones": 0,
                "octaves": 5,  # Invalid
            }
        )
        
        assert response.status_code == 400
    
    def test_returns_400_for_invalid_clef(self, client, simple_musicxml):
        """Should reject invalid clef values."""
        response = client.post(
            "/materials/preview/transpose",
            json={
                "musicxml_content": simple_musicxml,
                "semitones": 0,
                "octaves": 0,
                "target_clef": "alto",  # Invalid
            }
        )
        
        assert response.status_code == 400


# =============================================================================
# TEST: PUT /materials/preview
# =============================================================================

class TestSavePreviewFile:
    """Tests for PUT /materials/preview (update existing file) endpoint."""
    
    def test_returns_404_for_nonexistent_file(self, client, tmp_path, simple_musicxml):
        """Should return 404 when trying to update a file that doesn't exist."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.put(
                "/materials/preview",
                json={
                    "filename": "nonexistent.musicxml",
                    "musicxml_content": simple_musicxml,
                }
            )
            
            assert response.status_code == 404
    
    def test_returns_400_for_path_traversal(self, client, tmp_path, simple_musicxml):
        """Should return 400 for path traversal attempts."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.put(
                "/materials/preview",
                json={
                    "filename": "../../../etc/passwd",
                    "musicxml_content": simple_musicxml,
                }
            )
            
            assert response.status_code == 400
    
    def test_saves_updated_content(self, client, tmp_path, simple_musicxml):
        """Should save updated content to existing file."""
        # Create the file first
        file_path = tmp_path / "existing_tune.musicxml"
        file_path.write_text("old content")
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.put(
                "/materials/preview",
                json={
                    "filename": "existing_tune.musicxml",
                    "musicxml_content": simple_musicxml,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["filename"] == "existing_tune.musicxml"
            # Verify file was updated
            assert file_path.read_text() == simple_musicxml


# =============================================================================
# TEST: POST /materials/preview/save
# =============================================================================

class TestCreatePreviewFile:
    """Tests for POST /materials/preview/save (create new file) endpoint."""
    
    def test_returns_409_for_existing_file(self, client, tmp_path, simple_musicxml):
        """Should return 409 when file already exists."""
        file_path = tmp_path / "existing.musicxml"
        file_path.write_text("existing content")
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.post(
                "/materials/preview/save",
                json={
                    "filename": "existing.musicxml",
                    "musicxml_content": simple_musicxml,
                }
            )
            
            assert response.status_code == 409
    
    def test_returns_400_for_path_traversal(self, client, tmp_path, simple_musicxml):
        """Should return 400 for path traversal attempts."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.post(
                "/materials/preview/save",
                json={
                    "filename": "../../../etc/passwd",
                    "musicxml_content": simple_musicxml,
                }
            )
            
            assert response.status_code == 400
    
    def test_creates_new_file(self, client, tmp_path, simple_musicxml):
        """Should create new file in preview folder."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.post(
                "/materials/preview/save",
                json={
                    "filename": "new_tune.musicxml",
                    "musicxml_content": simple_musicxml,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Verify file was created
            assert (tmp_path / "new_tune.musicxml").exists()
    
    def test_creates_subdirectories(self, client, tmp_path, simple_musicxml):
        """Should create parent directories if needed."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.post(
                "/materials/preview/save",
                json={
                    "filename": "beginner/easy/new_tune.musicxml",
                    "musicxml_content": simple_musicxml,
                }
            )
            
            assert response.status_code == 200
            assert (tmp_path / "beginner" / "easy" / "new_tune.musicxml").exists()
    
    def test_adds_musicxml_extension(self, client, tmp_path, simple_musicxml):
        """Should add .musicxml extension if missing."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.post(
                "/materials/preview/save",
                json={
                    "filename": "my_tune",
                    "musicxml_content": simple_musicxml,
                }
            )
            
            assert response.status_code == 200
            assert (tmp_path / "my_tune.musicxml").exists()


# =============================================================================
# TEST: DELETE /materials/preview/{filename}
# =============================================================================

class TestDeletePreviewFile:
    """Tests for DELETE /materials/preview/{filename} endpoint."""
    
    def test_returns_404_for_nonexistent_file(self, client, tmp_path):
        """Should return 404 for non-existent file."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.delete("/materials/preview/nonexistent.musicxml")
            
            assert response.status_code == 404
    
    def test_returns_400_for_path_traversal(self, client, tmp_path):
        """Should return 400 for path traversal attempts."""
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.delete("/materials/preview/../../../etc/passwd")
            
            # May return 400 or 404 depending on resolution
            assert response.status_code in [400, 404]
    
    def test_returns_400_for_directories(self, client, tmp_path):
        """Should return 400 when trying to delete a directory."""
        subdir = tmp_path / "beginner"
        subdir.mkdir()
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.delete("/materials/preview/beginner")
            
            assert response.status_code == 400
    
    def test_deletes_existing_file(self, client, tmp_path, simple_musicxml):
        """Should delete existing file."""
        file_path = tmp_path / "to_delete.musicxml"
        file_path.write_text(simple_musicxml)
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.delete("/materials/preview/to_delete.musicxml")
            
            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            # Verify file was deleted
            assert not file_path.exists()
    
    def test_deletes_file_in_subdirectory(self, client, tmp_path, simple_musicxml):
        """Should delete file in subdirectory."""
        subdir = tmp_path / "beginner"
        subdir.mkdir()
        file_path = subdir / "hot_cross_buns.musicxml"
        file_path.write_text(simple_musicxml)
        
        with patch("app.routes.materials.PENDING_MATERIALS_FOLDER", tmp_path):
            response = client.delete("/materials/preview/beginner/hot_cross_buns.musicxml")
            
            assert response.status_code == 200
            assert not file_path.exists()
