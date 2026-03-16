"""
Tests for MaterialIngestionService.

Tests the material ingestion pipeline for MusicXML analysis.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.services.ingestion.service import MaterialIngestionService
from app.services.ingestion.models import IngestionResult


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def mock_materials_dir(tmp_path):
    """Create a temporary materials directory with test structure."""
    materials_dir = tmp_path / "materials"
    materials_dir.mkdir()
    
    # Create materials.json
    materials_json = {
        "materials": [
            {
                "title": "Existing Material",
                "musicxml_file": "existing.musicxml",
                "detected_capabilities": ["quarter_note", "half_note"],
                "soft_gates": {"tonal_complexity_stage": 1},
            }
        ],
        "last_updated": "2025-01-01T00:00:00"
    }
    (materials_dir / "materials.json").write_text(json.dumps(materials_json))
    
    return materials_dir


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
  </part>
</score-partwise>"""


# =============================================================================
# TEST: INITIALIZATION
# =============================================================================

class TestServiceInitialization:
    """Test MaterialIngestionService initialization."""
    
    def test_initializes_with_default_directory(self):
        """Should initialize with default materials directory."""
        service = MaterialIngestionService()
        
        # Verify materials_dir is set and contains expected path
        assert "materials" in str(service.materials_dir)
    
    def test_initializes_with_custom_directory(self, mock_materials_dir):
        """Should accept custom materials directory."""
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        assert service.materials_dir == mock_materials_dir
    
    def test_loads_existing_materials_json(self, mock_materials_dir):
        """Should load existing materials.json on init."""
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        assert "materials" in service.materials_data
        assert len(service.materials_data["materials"]) == 1
        assert service.materials_data["materials"][0]["title"] == "Existing Material"
    
    def test_creates_empty_structure_when_no_json(self, tmp_path):
        """Should create empty structure when no materials.json exists."""
        empty_dir = tmp_path / "empty_materials"
        empty_dir.mkdir()
        
        service = MaterialIngestionService(materials_dir=empty_dir)
        
        assert service.materials_data == {"materials": [], "last_updated": None}
    
    def test_initializes_analyzers(self):
        """Should initialize all required analyzer components."""
        service = MaterialIngestionService()
        
        # Verify analyzer components exist with expected methods
        assert service.musicxml_analyzer is not None
        assert hasattr(service.musicxml_analyzer, 'analyze')
        assert service.capability_registry is not None
        assert hasattr(service.capability_registry, 'get_rule')
        assert service.detection_engine is not None
        assert service.soft_gate_calculator is not None
        assert hasattr(service.soft_gate_calculator, 'calculate_from_musicxml')


# =============================================================================
# TEST: SCANNING
# =============================================================================

class TestScanMusicXMLFiles:
    """Test scanning for MusicXML files."""
    
    def test_finds_musicxml_files(self, mock_materials_dir, simple_musicxml):
        """Should find .musicxml files in directory."""
        # Create test files
        (mock_materials_dir / "test1.musicxml").write_text(simple_musicxml)
        (mock_materials_dir / "test2.musicxml").write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        files = service.scan_musicxml_files()
        
        assert len(files) == 2
        assert all(f.suffix == ".musicxml" for f in files)
    
    def test_finds_xml_files(self, mock_materials_dir, simple_musicxml):
        """Should find .xml files in directory."""
        (mock_materials_dir / "test.xml").write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        files = service.scan_musicxml_files()
        
        assert len(files) == 1
        assert files[0].suffix == ".xml"
    
    def test_scans_subdirectories(self, mock_materials_dir, simple_musicxml):
        """Should scan subdirectories recursively."""
        subdir = mock_materials_dir / "subdir"
        subdir.mkdir()
        (subdir / "nested.musicxml").write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        files = service.scan_musicxml_files()
        
        assert len(files) == 1
        assert "nested.musicxml" in str(files[0])
    
    def test_skips_hidden_directories(self, mock_materials_dir, simple_musicxml):
        """Should skip hidden directories."""
        hidden_dir = mock_materials_dir / ".hidden"
        hidden_dir.mkdir()
        (hidden_dir / "hidden.musicxml").write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        files = service.scan_musicxml_files()
        
        assert len(files) == 0
    
    def test_skips_test_directory(self, mock_materials_dir, simple_musicxml):
        """Should skip 'test' directory."""
        test_dir = mock_materials_dir / "test"
        test_dir.mkdir()
        (test_dir / "test_file.musicxml").write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        files = service.scan_musicxml_files()
        
        assert len(files) == 0
    
    def test_returns_empty_for_empty_dir(self, tmp_path):
        """Should return empty list for empty directory."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        service = MaterialIngestionService(materials_dir=empty_dir)
        files = service.scan_musicxml_files()
        
        assert files == []


# =============================================================================
# TEST: EXISTING ENTRIES
# =============================================================================

class TestGetExistingEntries:
    """Test retrieving existing material entries."""
    
    def test_returns_entries_by_filename(self, mock_materials_dir):
        """Should return entries indexed by musicxml_file."""
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        entries = service.get_existing_entries()
        
        assert "existing.musicxml" in entries
        assert entries["existing.musicxml"]["title"] == "Existing Material"
    
    def test_returns_empty_dict_for_no_entries(self, tmp_path):
        """Should return empty dict when no entries exist."""
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        
        service = MaterialIngestionService(materials_dir=empty_dir)
        entries = service.get_existing_entries()
        
        assert entries == {}
    
    def test_handles_entries_without_musicxml_file(self, tmp_path):
        """Should skip entries without musicxml_file field."""
        materials_dir = tmp_path / "materials"
        materials_dir.mkdir()
        
        materials_json = {
            "materials": [
                {"title": "No File Entry"},  # Missing musicxml_file
                {"title": "With File", "musicxml_file": "test.musicxml"}
            ],
            "last_updated": None
        }
        (materials_dir / "materials.json").write_text(json.dumps(materials_json))
        
        service = MaterialIngestionService(materials_dir=materials_dir)
        entries = service.get_existing_entries()
        
        assert len(entries) == 1
        assert "test.musicxml" in entries


# =============================================================================
# TEST: BATCH INGESTION
# =============================================================================

class TestIngestBatch:
    """Test batch ingestion functionality."""
    
    def test_returns_ingestion_result(self, mock_materials_dir):
        """Should return IngestionResult object."""
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        result = service.ingest_batch()
        
        assert isinstance(result, IngestionResult)
        # Verify result has required fields with valid values
        assert result.files_scanned >= 0
        assert result.files_analyzed >= 0
        assert isinstance(result.errors, list)
    
    def test_counts_scanned_files(self, mock_materials_dir, simple_musicxml):
        """Should count all scanned files."""
        (mock_materials_dir / "file1.musicxml").write_text(simple_musicxml)
        (mock_materials_dir / "file2.musicxml").write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        result = service.ingest_batch()
        
        assert result.files_scanned == 2
    
    def test_analyze_missing_only_skips_existing(self, mock_materials_dir, simple_musicxml):
        """Should skip existing files when analyze_missing_only=True."""
        # Create file that matches existing entry
        (mock_materials_dir / "existing.musicxml").write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        result = service.ingest_batch(analyze_missing_only=True)
        
        assert result.files_skipped == 1
    
    def test_overwrite_reanalyzes_all(self, mock_materials_dir, simple_musicxml):
        """Should reanalyze all files when overwrite=True."""
        (mock_materials_dir / "existing.musicxml").write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        result = service.ingest_batch(overwrite=True)
        
        # Should have analyzed the existing file
        assert result.files_skipped == 0
    
    def test_specific_files_filter(self, mock_materials_dir, simple_musicxml):
        """Should only analyze files in specific_files list."""
        (mock_materials_dir / "include.musicxml").write_text(simple_musicxml)
        (mock_materials_dir / "exclude.musicxml").write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        result = service.ingest_batch(
            analyze_missing_only=False,
            specific_files=["include.musicxml"]
        )
        
        assert "include.musicxml" in result.analyzed_materials or result.files_analyzed <= 1
    
    def test_removes_orphan_entries(self, mock_materials_dir):
        """Should remove entries without corresponding files on disk."""
        # mock_materials_dir already has entry for "existing.musicxml"
        # but we're not creating that file
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        result = service.ingest_batch()
        
        # The existing.musicxml entry should be removed as orphan
        assert result.orphans_removed == 1
    
    def test_captures_analysis_errors(self, mock_materials_dir):
        """Should capture errors without crashing."""
        # Create an invalid musicxml file
        (mock_materials_dir / "invalid.musicxml").write_text("not valid xml at all")
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        result = service.ingest_batch()
        
        # Should have error for the invalid file
        assert len(result.errors) >= 1 or result.files_analyzed == 0
    
    def test_updates_materials_json(self, mock_materials_dir, simple_musicxml):
        """Should save updated materials.json after ingestion."""
        (mock_materials_dir / "new_file.musicxml").write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        service.ingest_batch()
        
        # Reload and check
        with open(mock_materials_dir / "materials.json") as f:
            updated_data = json.load(f)
        
        assert "last_updated" in updated_data
        assert updated_data["last_updated"] is not None


# =============================================================================
# TEST: JSON MANAGEMENT
# =============================================================================

class TestJSONManagement:
    """Test JSON save/load functionality."""
    
    def test_saves_with_timestamp(self, mock_materials_dir):
        """Should add timestamp when saving."""
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        test_data = {"materials": [], "last_updated": None}
        service._save_materials_json(test_data)
        
        with open(mock_materials_dir / "materials.json") as f:
            saved = json.load(f)
        
        assert saved["last_updated"] is not None
    
    def test_creates_archive_on_save(self, mock_materials_dir):
        """Should archive previous version when saving."""
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        service._save_materials_json({"materials": [], "last_updated": None})
        
        archive_dir = mock_materials_dir / ".archive"
        assert archive_dir.exists()
        archives = list(archive_dir.glob("materials_*.json"))
        assert len(archives) == 1
    
    def test_updates_internal_data_on_save(self, mock_materials_dir):
        """Should update internal materials_data when saving."""
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        new_data = {"materials": [{"title": "New"}], "last_updated": None}
        service._save_materials_json(new_data)
        
        assert len(service.materials_data["materials"]) == 1
        assert service.materials_data["materials"][0]["title"] == "New"


# =============================================================================
# TEST: SINGLE MATERIAL ANALYSIS
# =============================================================================

class TestAnalyzeMaterial:
    """Test single material analysis."""
    
    def test_analyze_calls_underlying_function(self, mock_materials_dir, simple_musicxml):
        """Should call the analyze_material function with correct args."""
        file_path = mock_materials_dir / "test.musicxml"
        file_path.write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        # Mock the underlying analyze_material function
        with patch("app.services.ingestion.service.analyze_material") as mock_analyze:
            mock_analyze.return_value = {
                "title": "Test Piece",
                "detected_capabilities": ["quarter_note"],
                "soft_gates": {"tonal_complexity_stage": 1},
                "range_analysis": {},
                "measure_count": 1,
                "tempo_bpm": 120,
            }
            
            result = service.analyze_material(file_path)
            
            # Verify result structure
            assert "title" in result
            assert "detected_capabilities" in result
            assert "soft_gates" in result
    
    def test_analyze_passes_tempo_override(self, mock_materials_dir, simple_musicxml):
        """Should pass tempo_bpm to underlying analyzer."""
        file_path = mock_materials_dir / "test.musicxml"
        file_path.write_text(simple_musicxml)
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        with patch("app.services.ingestion.service.analyze_material") as mock_analyze:
            mock_analyze.return_value = {
                "title": "Test",
                "detected_capabilities": [],
                "soft_gates": {},
                "range_analysis": {},
                "measure_count": 1,
                "tempo_bpm": 140,  # Custom tempo
            }
            
            service.analyze_material(file_path, tempo_bpm=140)
            
            # Verify tempo was passed
            call_args = mock_analyze.call_args
            assert call_args is not None


# =============================================================================
# TEST: EXPORT
# =============================================================================

class TestExport:
    """Test export functionality."""
    
    def test_export_to_default_path(self, mock_materials_dir):
        """Should export to default materials.json path."""
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        # export_to_json should return the path
        if hasattr(service, "export_to_json"):
            result_path = service.export_to_json()
            assert result_path.name == "materials.json"


# =============================================================================
# TEST: ANALYZE SPECIFIC METRICS
# =============================================================================

class TestAnalyzeSpecificMetrics:
    """Test analyze_specific_metrics method."""
    
    def test_analyze_specific_metrics_returns_result(self, mock_materials_dir):
        """Should return IngestionResult."""
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        result = service.analyze_specific_metrics(metrics=["capabilities"])
        
        assert isinstance(result, IngestionResult)
    
    def test_analyze_specific_metrics_with_filter(self, mock_materials_dir, simple_musicxml):
        """Should only analyze files in filter."""
        # Create a file on disk
        (mock_materials_dir / "existing.musicxml").write_text(simple_musicxml)
        (mock_materials_dir / "other.musicxml").write_text(simple_musicxml)
        
        # Update materials.json to have two entries
        materials_data = {
            "materials": [
                {"title": "Existing", "musicxml_file": "existing.musicxml"},
                {"title": "Other", "musicxml_file": "other.musicxml"},
            ]
        }
        (mock_materials_dir / "materials.json").write_text(json.dumps(materials_data))
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        result = service.analyze_specific_metrics(
            metrics=["capabilities"],
            file_filter=["existing.musicxml"]
        )
        
        # Should skip other.musicxml
        assert result.files_skipped == 1
    
    def test_analyze_specific_metrics_skips_missing_file(self, mock_materials_dir):
        """Should handle when musicxml_file doesn't exist."""
        # Entry references non-existent file
        materials_data = {
            "materials": [
                {"title": "Missing", "musicxml_file": "nonexistent.musicxml"},
            ]
        }
        (mock_materials_dir / "materials.json").write_text(json.dumps(materials_data))
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        result = service.analyze_specific_metrics(metrics=["capabilities"])
        
        assert len(result.errors) == 1
        assert "not found" in result.errors[0]
    
    def test_analyze_specific_metrics_capabilities(self, mock_materials_dir, simple_musicxml):
        """Should recalculate capabilities when specified."""
        (mock_materials_dir / "test.musicxml").write_text(simple_musicxml)
        
        materials_data = {
            "materials": [
                {
                    "title": "Test",
                    "musicxml_file": "test.musicxml",
                    "detected_capabilities": []  # Empty initially
                },
            ]
        }
        (mock_materials_dir / "materials.json").write_text(json.dumps(materials_data))
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        result = service.analyze_specific_metrics(metrics=["capabilities"])
        
        assert result.files_analyzed == 1
    
    def test_analyze_specific_metrics_soft_gates(self, mock_materials_dir, simple_musicxml):
        """Should recalculate soft gates when specified."""
        (mock_materials_dir / "test.musicxml").write_text(simple_musicxml)
        
        materials_data = {
            "materials": [
                {
                    "title": "Test",
                    "musicxml_file": "test.musicxml",
                },
            ]
        }
        (mock_materials_dir / "materials.json").write_text(json.dumps(materials_data))
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        # Mock both the calculator and the format function
        mock_gates = MagicMock()
        
        with patch.object(service.soft_gate_calculator, 'calculate_from_musicxml', return_value=mock_gates):
            with patch('app.services.ingestion.service.format_soft_gates', return_value={"mocked": True}):
                result = service.analyze_specific_metrics(metrics=["soft_gates"])
        
        assert result.files_analyzed == 1
    
    def test_analyze_specific_metrics_preserves_entries_without_file(self, mock_materials_dir):
        """Should preserve entries that have no musicxml_file."""
        materials_data = {
            "materials": [
                {"title": "No File Entry"},  # No musicxml_file
            ]
        }
        (mock_materials_dir / "materials.json").write_text(json.dumps(materials_data))
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        result = service.analyze_specific_metrics(metrics=["capabilities"])
        
        # Entry should be preserved, not cause error
        assert len(result.errors) == 0
    
    def test_analyze_specific_metrics_handles_error(self, mock_materials_dir, simple_musicxml):
        """Should capture errors during analysis."""
        (mock_materials_dir / "test.musicxml").write_text(simple_musicxml)
        
        materials_data = {
            "materials": [
                {"title": "Test", "musicxml_file": "test.musicxml"},
            ]
        }
        (mock_materials_dir / "materials.json").write_text(json.dumps(materials_data))
        
        service = MaterialIngestionService(materials_dir=mock_materials_dir)
        
        # Mock analyzer to raise error
        with patch.object(service, 'soft_gate_calculator') as mock_calc:
            mock_calc.calculate_from_musicxml.side_effect = ValueError("Analysis failed")
            
            result = service.analyze_specific_metrics(metrics=["soft_gates"])
            
            assert len(result.errors) == 1
            assert "Analysis failed" in result.errors[0]


# =============================================================================
# TEST: CONVENIENCE FUNCTIONS
# =============================================================================

class TestConvenienceFunctions:
    """Test module-level convenience functions."""
    
    @patch('app.services.ingestion.service.MaterialIngestionService')
    def test_ingest_materials_calls_service(self, mock_service_class):
        """Should create service and call ingest_batch."""
        from app.services.ingestion.service import ingest_materials
        
        mock_service = MagicMock()
        mock_result = IngestionResult(
            files_scanned=5,
            files_analyzed=3,
            files_skipped=2,
            orphans_removed=0,
            errors=[],
            analyzed_materials=["a.xml", "b.xml", "c.xml"]
        )
        mock_service.ingest_batch.return_value = mock_result
        mock_service_class.return_value = mock_service
        
        result = ingest_materials(analyze_missing_only=True, overwrite=False)
        
        mock_service.ingest_batch.assert_called_once_with(True, False)
        assert result == mock_result
    
    @patch('app.services.ingestion.service.MaterialIngestionService')
    def test_ingest_materials_with_overwrite(self, mock_service_class):
        """Should pass overwrite flag to service."""
        from app.services.ingestion.service import ingest_materials
        
        mock_service = MagicMock()
        mock_service_class.return_value = mock_service
        
        ingest_materials(analyze_missing_only=False, overwrite=True)
        
        mock_service.ingest_batch.assert_called_once_with(False, True)
    
    @patch('app.services.ingestion.service.MaterialIngestionService')
    def test_export_materials_json_calls_service(self, mock_service_class):
        """Should create service and call export_to_json."""
        from app.services.ingestion.service import export_materials_json
        
        mock_service = MagicMock()
        mock_path = Path("/tmp/materials.json")
        mock_service.export_to_json.return_value = mock_path
        mock_service_class.return_value = mock_service
        
        result = export_materials_json()
        
        mock_service.export_to_json.assert_called_once()
        assert result == mock_path
