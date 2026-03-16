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


class TestCreateMaterialRecord:
    """Test create_material_record class method."""
    
    @patch('app.services.material.service.Material')
    def test_create_material_record_basic(self, mock_material_class):
        """Test creating a basic material record."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material_class.return_value = mock_material
        
        result = MaterialService.create_material_record(
            db=mock_db,
            title="Test Song",
            musicxml_content="<xml>content</xml>",
        )
        
        mock_material_class.assert_called_once_with(
            title="Test Song",
            musicxml_canonical="<xml>content</xml>",
            tempo_bpm=None,
            composer=None,
            source=None,
        )
        mock_db.add.assert_called_once_with(mock_material)
        mock_db.flush.assert_called_once()
        assert result == mock_material
    
    @patch('app.services.material.service.Material')
    def test_create_material_record_with_all_fields(self, mock_material_class):
        """Test creating material with all optional fields."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material_class.return_value = mock_material
        
        result = MaterialService.create_material_record(
            db=mock_db,
            title="Full Material",
            musicxml_content="<xml>full</xml>",
            tempo_bpm=120,
            composer="Bach",
            source="test-source",
        )
        
        mock_material_class.assert_called_once_with(
            title="Full Material",
            musicxml_canonical="<xml>full</xml>",
            tempo_bpm=120,
            composer="Bach",
            source="test-source",
        )
        mock_db.add.assert_called_once()
        assert result == mock_material
    
    @patch('app.services.material.service.Material')  
    def test_create_material_record_flushes_for_id(self, mock_material_class):
        """Test that flush is called to get the material ID."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 42
        mock_material_class.return_value = mock_material
        
        result = MaterialService.create_material_record(
            db=mock_db,
            title="Flush Test",
            musicxml_content="<xml/>",
        )
        
        mock_db.flush.assert_called_once()
        assert result.id == 42


class TestLinkCapabilities:
    """Test link_capabilities class method."""
    
    @patch.object(MaterialService, 'compute_and_store_bitmasks')
    def test_link_capabilities_with_existing_caps(self, mock_compute_bitmasks):
        """Test linking capabilities that exist in database."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        
        # Mock capability lookups
        mock_cap1 = Mock()
        mock_cap1.id = 10
        mock_cap1.bit_index = 5
        mock_cap2 = Mock()
        mock_cap2.id = 20
        mock_cap2.bit_index = 7
        
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            mock_cap1, mock_cap2
        ]
        
        result = MaterialService.link_capabilities(
            db=mock_db,
            material=mock_material,
            capability_names=['cap1', 'cap2']
        )
        
        assert mock_db.add.call_count == 2
        mock_compute_bitmasks.assert_called_once_with(mock_material, [5, 7])
        assert result == [5, 7]
    
    @patch.object(MaterialService, 'compute_and_store_bitmasks')
    def test_link_capabilities_nonexistent_cap(self, mock_compute_bitmasks):
        """Test linking capabilities where some don't exist."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        
        # First cap exists, second doesn't
        mock_cap = Mock()
        mock_cap.id = 10
        mock_cap.bit_index = 3
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            mock_cap, None
        ]
        
        result = MaterialService.link_capabilities(
            db=mock_db,
            material=mock_material,
            capability_names=['cap1', 'nonexistent']
        )
        
        # Only one MaterialCapability added
        assert mock_db.add.call_count == 1
        assert result == [3]
    
    @patch.object(MaterialService, 'compute_and_store_bitmasks')
    def test_link_capabilities_with_null_bit_index(self, mock_compute_bitmasks):
        """Test linking capability with null bit_index."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        
        mock_cap = Mock()
        mock_cap.id = 10
        mock_cap.bit_index = None  # No bit index
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_cap
        
        result = MaterialService.link_capabilities(
            db=mock_db,
            material=mock_material,
            capability_names=['cap_no_bit']
        )
        
        mock_db.add.assert_called_once()
        # Bit indices list should be empty
        mock_compute_bitmasks.assert_called_once_with(mock_material, [])
        assert result == []
    
    @patch.object(MaterialService, 'compute_and_store_bitmasks')
    def test_link_capabilities_empty_list(self, mock_compute_bitmasks):
        """Test linking empty capability list."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        
        result = MaterialService.link_capabilities(
            db=mock_db,
            material=mock_material,
            capability_names=[]
        )
        
        mock_db.add.assert_not_called()
        mock_compute_bitmasks.assert_called_once_with(mock_material, [])
        assert result == []


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


class TestRelinkCapabilities:
    """Test relink_capabilities class method."""
    
    @patch.object(MaterialService, 'compute_and_store_bitmasks')
    @patch('app.musicxml_analyzer.compute_capability_bitmask')
    def test_relink_capabilities_clears_and_rebuilds(self, mock_compute, mock_bitmasks):
        """Test that existing links are cleared before relinking."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        
        # Mock capability lookup
        mock_cap = Mock()
        mock_cap.id = 10
        mock_cap.bit_index = 5
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_cap
        mock_db.query.return_value.filter_by.return_value.delete.return_value = 3  # 3 deleted
        
        result = MaterialService.relink_capabilities(
            db=mock_db,
            material=mock_material,
            capability_names=['cap1']
        )
        
        # Verify delete was called for existing links
        assert mock_db.query.return_value.filter_by.return_value.delete.called
        # Verify new links were created
        mock_db.add.assert_called_once()
        assert result == 1  # Returns count of capabilities linked
    
    @patch.object(MaterialService, 'compute_and_store_bitmasks')
    @patch('app.musicxml_analyzer.compute_capability_bitmask')
    def test_relink_capabilities_multiple_caps(self, mock_compute, mock_bitmasks):
        """Test relinking multiple capabilities."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        
        mock_cap1 = Mock()
        mock_cap1.id = 10
        mock_cap1.bit_index = 5
        mock_cap2 = Mock()
        mock_cap2.id = 20
        mock_cap2.bit_index = 8
        
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            mock_cap1, mock_cap2
        ]
        
        result = MaterialService.relink_capabilities(
            db=mock_db,
            material=mock_material,
            capability_names=['cap1', 'cap2']
        )
        
        assert mock_db.add.call_count == 2
        assert result == 2
    
    @patch.object(MaterialService, 'compute_and_store_bitmasks')
    @patch('app.musicxml_analyzer.compute_capability_bitmask')
    def test_relink_capabilities_skips_missing(self, mock_compute, mock_bitmasks):
        """Test that missing capabilities are skipped."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        
        # First exists, second doesn't
        mock_cap = Mock()
        mock_cap.id = 10
        mock_cap.bit_index = 5
        mock_db.query.return_value.filter_by.return_value.first.side_effect = [
            mock_cap, None
        ]
        
        result = MaterialService.relink_capabilities(
            db=mock_db,
            material=mock_material,
            capability_names=['exists', 'missing']
        )
        
        assert mock_db.add.call_count == 1
        assert result == 2  # Returns count of capability_names, not found caps


class TestReanalyzeMaterial:
    """Test reanalyze_material class method."""
    
    @patch('app.services.material.service.update_range_analysis')
    @patch('app.services.material.service.update_soft_gates')
    @patch.object(MaterialService, 'persist_unified_scores')
    @patch.object(MaterialService, 'relink_capabilities')
    @patch.object(MaterialService, 'detect_all_capabilities')
    @patch.object(MaterialService, 'analyze_musicxml')
    @patch('app.soft_gate_calculator.SoftGateCalculator')
    def test_reanalyze_material_all_metrics(
        self, 
        mock_calculator_class,
        mock_analyze,
        mock_detect,
        mock_relink,
        mock_persist_unified,
        mock_update_soft_gates,
        mock_update_range
    ):
        """Test reanalyzing material with all metrics."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        mock_material.title = "Test Material"
        mock_material.musicxml_canonical = "<xml>content</xml>"
        
        mock_extraction = MockExtractionResult()
        mock_analyze.return_value = (mock_extraction, {'legacy_cap'})
        mock_detect.return_value = {'cap1', 'cap2'}
        mock_relink.return_value = 2
        mock_update_soft_gates.return_value = {'soft_gate': 'data'}
        mock_update_range.return_value = {'range': 'data'}
        
        # Mock existing analysis
        mock_analysis = Mock()
        mock_db.query.return_value.filter_by.return_value.first.return_value = mock_analysis
        
        mock_calculator = Mock()
        mock_calculator.calculate_from_musicxml.return_value = {'gates': 'data'}
        mock_calculator_class.return_value = mock_calculator
        
        result = MaterialService.reanalyze_material(
            db=mock_db,
            material=mock_material,
            metrics=None  # All metrics
        )
        
        assert result.material_id == 1
        assert result.title == "Test Material"
        assert 'capabilities' in result.metrics_updated
        assert result.capabilities_count == 2
    
    @patch('app.services.material.service.update_range_analysis')
    @patch('app.services.material.service.update_soft_gates')
    @patch.object(MaterialService, 'persist_unified_scores')
    @patch.object(MaterialService, 'relink_capabilities')
    @patch.object(MaterialService, 'detect_all_capabilities')
    @patch.object(MaterialService, 'analyze_musicxml')
    def test_reanalyze_material_capabilities_only(
        self,
        mock_analyze,
        mock_detect,
        mock_relink,
        mock_persist_unified,
        mock_update_soft_gates,
        mock_update_range
    ):
        """Test reanalyzing with only capabilities metric."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        mock_material.title = "Test"
        mock_material.musicxml_canonical = "<xml/>"
        
        mock_extraction = MockExtractionResult()
        mock_analyze.return_value = (mock_extraction, set())
        mock_detect.return_value = {'cap1'}
        mock_relink.return_value = 1
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = Mock()
        
        result = MaterialService.reanalyze_material(
            db=mock_db,
            material=mock_material,
            metrics=['capabilities']
        )
        
        assert 'capabilities' in result.metrics_updated
        mock_update_soft_gates.assert_not_called()
        mock_update_range.assert_not_called()
    
    @patch('app.services.material.service.update_range_analysis')
    @patch('app.services.material.service.update_soft_gates')
    @patch.object(MaterialService, 'persist_unified_scores')
    @patch.object(MaterialService, 'analyze_musicxml')
    @patch('app.soft_gate_calculator.SoftGateCalculator')
    def test_reanalyze_material_soft_gates_only(
        self,
        mock_calculator_class,
        mock_analyze,
        mock_persist_unified,
        mock_update_soft_gates,
        mock_update_range
    ):
        """Test reanalyzing with only soft_gates metric."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        mock_material.title = "Test"
        mock_material.musicxml_canonical = "<xml/>"
        
        mock_extraction = MockExtractionResult()
        mock_analyze.return_value = (mock_extraction, set())
        mock_update_soft_gates.return_value = {'updated': True}
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = Mock()
        
        mock_calculator = Mock()
        mock_calculator.calculate_from_musicxml.return_value = {}
        mock_calculator_class.return_value = mock_calculator
        
        result = MaterialService.reanalyze_material(
            db=mock_db,
            material=mock_material,
            metrics=['soft_gates']
        )
        
        assert 'soft_gates' in result.metrics_updated
        mock_update_soft_gates.assert_called_once()
    
    @patch('app.services.material.service.update_range_analysis')
    @patch('app.services.material.service.update_soft_gates')
    @patch.object(MaterialService, 'persist_unified_scores')
    @patch.object(MaterialService, 'analyze_musicxml')
    def test_reanalyze_material_range_only(
        self,
        mock_analyze,
        mock_persist_unified,
        mock_update_soft_gates,
        mock_update_range
    ):
        """Test reanalyzing with only range metric."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        mock_material.title = "Test"
        mock_material.musicxml_canonical = "<xml/>"
        
        mock_extraction = MockExtractionResult()
        mock_analyze.return_value = (mock_extraction, set())
        mock_update_range.return_value = {'range': 'updated'}
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = Mock()
        
        result = MaterialService.reanalyze_material(
            db=mock_db,
            material=mock_material,
            metrics=['range']
        )
        
        assert 'range' in result.metrics_updated
        mock_update_range.assert_called_once()
    
    @patch('app.services.material.service.update_range_analysis')
    @patch('app.services.material.service.update_soft_gates')
    @patch.object(MaterialService, 'persist_unified_scores')
    @patch.object(MaterialService, 'analyze_musicxml')
    def test_reanalyze_material_creates_analysis_if_missing(
        self,
        mock_analyze,
        mock_persist_unified,
        mock_update_soft_gates,
        mock_update_range
    ):
        """Test that MaterialAnalysis is created if it doesn't exist."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        mock_material.title = "Test"
        mock_material.musicxml_canonical = "<xml/>"
        
        mock_extraction = MockExtractionResult()
        mock_analyze.return_value = (mock_extraction, set())
        
        # No existing analysis
        mock_db.query.return_value.filter_by.return_value.first.return_value = None
        
        result = MaterialService.reanalyze_material(
            db=mock_db,
            material=mock_material,
            metrics=['range']
        )
        
        # Verify new analysis was added
        assert mock_db.add.called
    
    @patch('app.services.material.service.update_range_analysis')
    @patch('app.services.material.service.update_soft_gates')
    @patch.object(MaterialService, 'persist_unified_scores')
    @patch.object(MaterialService, 'analyze_musicxml')
    @patch('app.soft_gate_calculator.SoftGateCalculator')
    def test_reanalyze_material_handles_unified_scores_error(
        self,
        mock_calculator_class,
        mock_analyze,
        mock_persist_unified,
        mock_update_soft_gates,
        mock_update_range
    ):
        """Test that unified_scores errors are captured."""
        mock_db = Mock()
        mock_material = Mock()
        mock_material.id = 1
        mock_material.title = "Test"
        mock_material.musicxml_canonical = "<xml/>"
        
        mock_extraction = MockExtractionResult()
        mock_analyze.return_value = (mock_extraction, set())
        mock_persist_unified.side_effect = ValueError("Score calculation failed")
        
        mock_db.query.return_value.filter_by.return_value.first.return_value = Mock()
        
        mock_calculator = Mock()
        mock_calculator.calculate_from_musicxml.return_value = {}
        mock_calculator_class.return_value = mock_calculator
        
        result = MaterialService.reanalyze_material(
            db=mock_db,
            material=mock_material,
            metrics=['unified_scores']
        )
        
        assert result.unified_scores_error == "Score calculation failed"


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
        
        # Verify service is initialized with analysis capability
        assert service is not None
        assert hasattr(service, 'analyze_musicxml')
    
    def test_get_material_service_returns_same_instance(self):
        """Test that same instance is returned."""
        import app.services.material.service as service_module
        service_module._material_service = None
        
        service1 = get_material_service()
        service2 = get_material_service()
        
        assert service1 is service2
