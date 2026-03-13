"""Tests for app/services/material/service.py"""

import pytest
import json
from unittest.mock import Mock, MagicMock, patch, PropertyMock

from app.services.material.service import MaterialService, get_material_service
from app.services.material.models import UploadResult, ReanalyzeResult, BatchReanalyzeResult


class MockExtractionResult:
    """Mock for extraction result."""
    def __init__(self):
        self.chromatic_complexity_score = 0.5
        self.measure_count = 32
        self.tempo_markings = {'Allegro'}
        self.tempo_bpm = 120
        self.range_analysis = None
        self.to_dict_return = {'chromatic': 0.5}
    
    def to_dict(self):
        return self.to_dict_return


class MockRangeAnalysis:
    """Mock for range analysis."""
    def __init__(self):
        self.lowest_pitch = "C4"
        self.highest_pitch = "G5"
        self.range_semitones = 19


class TestAnalyzeMusicxml:
    """Test analyze_musicxml static method."""
    
    @patch('app.musicxml_analyzer.MusicXMLAnalyzer')
    def test_analyze_musicxml_basic(self, mock_analyzer_class):
        """Test basic MusicXML analysis."""
        mock_analyzer = Mock()
        mock_extraction = MockExtractionResult()
        mock_analyzer.analyze.return_value = mock_extraction
        mock_analyzer.get_capability_names.return_value = {'cap1', 'cap2'}
        mock_analyzer_class.return_value = mock_analyzer
        
        result, caps = MaterialService.analyze_musicxml("<xml>content</xml>")
        
        mock_analyzer.analyze.assert_called_once_with("<xml>content</xml>")
        mock_analyzer.get_capability_names.assert_called_once_with(mock_extraction)
        assert result == mock_extraction
        assert caps == {'cap1', 'cap2'}


class TestDetectAllCapabilities:
    """Test detect_all_capabilities class method."""
    
    @patch('app.capability_registry.DetectionEngine')
    @patch('app.capability_registry.CapabilityRegistry')
    @patch('app.musicxml_analyzer.MusicXMLAnalyzer')
    def test_detect_capabilities_combines_sources(
        self,
        mock_analyzer_class,
        mock_registry_class,
        mock_engine_class
    ):
        """Test that legacy and registry caps are combined."""
        mock_extraction = MockExtractionResult()
        
        # Legacy detection
        mock_analyzer = Mock()
        mock_analyzer.analyze.return_value = mock_extraction
        mock_analyzer.get_capability_names.return_value = {'legacy_cap', 'shared_cap'}
        mock_analyzer_class.return_value = mock_analyzer
        
        # Registry detection
        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry
        mock_engine = Mock()
        mock_engine.detect_all_capabilities.return_value = {'registry_cap', 'shared_cap'}
        mock_engine_class.return_value = mock_engine
        
        result = MaterialService.detect_all_capabilities("<xml>content</xml>")
        
        assert result == {'legacy_cap', 'shared_cap', 'registry_cap'}


class TestComputeAndStoreBitmasks:
    """Test compute_and_store_bitmasks static method."""
    
    @patch('app.musicxml_analyzer.compute_capability_bitmask')
    def test_compute_bitmasks_with_indices(self, mock_compute):
        """Test computing bitmasks with bit indices."""
        mock_material = Mock()
        mock_compute.return_value = 0x1234567890ABCDEF1234567890ABCDEF
        
        MaterialService.compute_and_store_bitmasks(mock_material, [1, 2, 3])
        
        mock_compute.assert_called_once_with([1, 2, 3])
        # Check low and high parts
        assert mock_material.capability_bitmask_low == 0x1234567890ABCDEF
        assert mock_material.capability_bitmask_high == 0x1234567890ABCDEF
    
    def test_compute_bitmasks_empty_indices(self):
        """Test with empty bit indices."""
        mock_material = Mock()
        
        MaterialService.compute_and_store_bitmasks(mock_material, [])
        
        assert mock_material.capability_bitmask_low == 0
        assert mock_material.capability_bitmask_high == 0


class TestCreateMaterialAnalysis:
    """Test create_material_analysis class method."""
    
    @patch('app.services.material.service.update_soft_gates')
    def test_create_analysis_basic(self, mock_update_soft_gates):
        """Test creating basic material analysis."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        mock_extraction = MockExtractionResult()
        
        result = MaterialService.create_material_analysis(
            db=mock_db,
            material=mock_material,
            extraction_result=mock_extraction,
        )
        
        mock_db.add.assert_called_once()
        assert result.material_id == 1
        assert result.chromatic_complexity == 0.5
        assert result.measure_count == 32
        assert result.tempo_marking == 'Allegro'
        assert result.tempo_bpm == 120
    
    @patch('app.services.material.service.update_soft_gates')
    def test_create_analysis_with_range(self, mock_update_soft_gates):
        """Test creating analysis with range analysis."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        mock_extraction = MockExtractionResult()
        mock_extraction.range_analysis = MockRangeAnalysis()
        
        result = MaterialService.create_material_analysis(
            db=mock_db,
            material=mock_material,
            extraction_result=mock_extraction,
        )
        
        assert result.lowest_pitch == "C4"
        assert result.highest_pitch == "G5"
        assert result.range_semitones == 19
    
    @patch('app.services.material.service.update_soft_gates')
    def test_create_analysis_with_soft_gates(self, mock_update_soft_gates):
        """Test creating analysis with soft gates."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        mock_extraction = MockExtractionResult()
        mock_soft_gates = Mock()
        
        MaterialService.create_material_analysis(
            db=mock_db,
            material=mock_material,
            extraction_result=mock_extraction,
            soft_gates=mock_soft_gates
        )
        
        mock_update_soft_gates.assert_called_once()
    
    @patch('app.services.material.service.update_soft_gates')
    def test_create_analysis_empty_tempo_markings(self, mock_update_soft_gates):
        """Test creating analysis with no tempo markings."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        mock_extraction = MockExtractionResult()
        mock_extraction.tempo_markings = set()  # Empty
        
        result = MaterialService.create_material_analysis(
            db=mock_db,
            material=mock_material,
            extraction_result=mock_extraction,
        )
        
        assert result.tempo_marking is None


class TestPersistUnifiedScores:
    """Test persist_unified_scores class method."""
    
    @patch('app.services.material.service.persist_unified_scores')
    def test_persist_unified_scores_delegates(self, mock_persist):
        """Test that method delegates to updaters function."""
        mock_analysis = Mock()
        mock_soft_gates = Mock()
        mock_extraction = Mock()
        mock_persist.return_value = {'scores': 'data'}
        
        result = MaterialService.persist_unified_scores(
            mock_analysis, mock_soft_gates, mock_extraction
        )
        
        mock_persist.assert_called_once_with(
            mock_analysis, mock_soft_gates, mock_extraction
        )
        assert result == {'scores': 'data'}


class TestReanalyzeBatch:
    """Test reanalyze_batch class method."""
    
    @patch.object(MaterialService, 'reanalyze_material')
    def test_batch_reanalyze_success(self, mock_reanalyze):
        """Test successful batch reanalysis."""
        mock_db = Mock()
        
        mat1 = Mock()
        mat1.id = 1
        mat1.musicxml_canonical = "<xml>1</xml>"
        mat2 = Mock()
        mat2.id = 2
        mat2.musicxml_canonical = "<xml>2</xml>"
        
        result = MaterialService.reanalyze_batch(mock_db, [mat1, mat2])
        
        assert result.total_materials == 2
        assert result.materials_updated == 2
        assert result.materials_failed == 0
        assert mock_reanalyze.call_count == 2
    
    @patch.object(MaterialService, 'reanalyze_material')
    def test_batch_reanalyze_with_no_content(self, mock_reanalyze):
        """Test batch with material missing content."""
        mock_db = Mock()
        
        mat1 = Mock()
        mat1.id = 1
        mat1.musicxml_canonical = None  # No content
        
        result = MaterialService.reanalyze_batch(mock_db, [mat1])
        
        assert result.total_materials == 1
        assert result.materials_updated == 0
        assert result.materials_failed == 1
        assert "has no MusicXML content" in result.errors[0]
    
    @patch.object(MaterialService, 'reanalyze_material')
    def test_batch_reanalyze_with_failures(self, mock_reanalyze):
        """Test batch with some failures."""
        mock_db = Mock()
        
        mat1 = Mock()
        mat1.id = 1
        mat1.musicxml_canonical = "<xml>1</xml>"
        mat2 = Mock()
        mat2.id = 2
        mat2.musicxml_canonical = "<xml>2</xml>"
        
        mock_reanalyze.side_effect = [
            Mock(),  # mat1 succeeds
            ValueError("Analysis error")  # mat2 fails
        ]
        
        result = MaterialService.reanalyze_batch(mock_db, [mat1, mat2])
        
        assert result.total_materials == 2
        assert result.materials_updated == 1
        assert result.materials_failed == 1
        assert "Analysis error" in result.errors[0]


class TestBackwardCompatibilityMethods:
    """Test backward compatibility wrapper methods."""
    
    @patch('app.services.material.service.update_soft_gates')
    def test_update_soft_gates_wrapper(self, mock_update):
        """Test update_soft_gates wrapper."""
        mock_analysis = Mock()
        mock_soft_gates = Mock()
        mock_update.return_value = {'result': 'data'}
        
        result = MaterialService.update_soft_gates(mock_analysis, mock_soft_gates)
        
        mock_update.assert_called_once_with(mock_analysis, mock_soft_gates)
        assert result == {'result': 'data'}
    
    @patch('app.services.material.service.update_unified_scores')
    def test_update_unified_scores_wrapper(self, mock_update):
        """Test update_unified_scores wrapper."""
        mock_analysis = Mock()
        mock_soft_gates = Mock()
        mock_update.return_value = {'unified': 'scores'}
        
        result = MaterialService.update_unified_scores(mock_analysis, mock_soft_gates)
        
        mock_update.assert_called_once_with(mock_analysis, mock_soft_gates)
    
    @patch('app.services.material.service.calculate_difficulty_scores')
    def test_calculate_difficulty_scores_wrapper(self, mock_calc):
        """Test calculate_difficulty_scores wrapper."""
        mock_analysis = Mock()
        mock_calc.return_value = {'difficulty': 'scores'}
        
        result = MaterialService.calculate_difficulty_scores(mock_analysis)
        
        mock_calc.assert_called_once_with(mock_analysis)
    
    @patch('app.services.material.service.update_range_analysis')
    def test_update_range_analysis_wrapper(self, mock_update):
        """Test update_range_analysis wrapper."""
        mock_analysis = Mock()
        mock_extraction = Mock()
        mock_update.return_value = {'range': 'data'}
        
        result = MaterialService.update_range_analysis(mock_analysis, mock_extraction)
        
        mock_update.assert_called_once_with(mock_analysis, mock_extraction)


class TestGetMaterialService:
    """Test get_material_service singleton."""
    
    def test_get_material_service_creates_singleton(self):
        """Test that singleton is created."""
        import app.services.material.service as service_module
        service_module._material_service = None
        
        service = get_material_service()
        
        assert service is not None
        assert isinstance(service, MaterialService)
    
    def test_get_material_service_returns_same_instance(self):
        """Test that same instance is returned."""
        import app.services.material.service as service_module
        service_module._material_service = None
        
        service1 = get_material_service()
        service2 = get_material_service()
        
        assert service1 is service2
