"""Tests for app/services/material_analysis_service.py"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from typing import Dict, Any

from app.services.material_analysis_service import (
    AnalysisResult,
    MaterialAnalysisService,
    get_analysis_service
)


class MockExtractionResult:
    """Mock ExtractionResult."""
    def __init__(self):
        self.title = "Test Title"
        self.range_analysis = None
        self.chromatic_complexity_score = 0.5
        self.measure_count = 32
        self.tempo_bpm = 120
        self.tempo_markings = {"Allegro"}
        self.tempo_profile = None
        self.note_values = {"quarter": 50, "eighth": 30}
        self.tuplets = {}
        self.dotted_notes = []
        self.has_ties = False
        self.rhythm_pattern_analysis = None
    
    def to_dict(self):
        return {"title": self.title}


class MockRangeAnalysis:
    """Mock range analysis."""
    def __init__(self):
        self.lowest_pitch = "C4"
        self.highest_pitch = "G5"
        self.range_semitones = 19


class MockIntervalProfile:
    """Mock interval profile."""
    total_intervals = 100
    step_ratio = 0.6
    skip_ratio = 0.25
    leap_ratio = 0.1
    large_leap_ratio = 0.04
    extreme_leap_ratio = 0.01
    interval_p50 = 2
    interval_p75 = 4
    interval_p90 = 7
    interval_max = 12


class MockIntervalLocalDifficulty:
    """Mock interval local difficulty."""
    max_large_leaps_in_window = 3
    max_extreme_leaps_in_window = 1
    hardest_measure_numbers = [5, 12]
    window_count = 20


class MockSoftGateMetrics:
    """Mock soft gate metrics."""
    def __init__(self):
        self.tonal_complexity_stage = 2
        self.interval_size_stage = 3
        self.interval_sustained_stage = 2
        self.interval_hazard_stage = 1
        self.legacy_interval_size_stage = 3
        self.interval_profile = MockIntervalProfile()
        self.interval_local_difficulty = MockIntervalLocalDifficulty()
        self.rhythm_complexity_score = 0.45
        self.rhythm_complexity_peak = 0.8
        self.rhythm_complexity_p95 = 0.65
        self.range_usage_stage = 3
        self.density_notes_per_second = 2.5
        self.note_density_per_measure = 8.0
        self.interval_velocity_score = 0.35
        self.interval_velocity_peak = 0.7
        self.interval_velocity_p95 = 0.55
        self.tempo_difficulty_score = 0.4


class MockDomainResult:
    """Mock domain result."""
    def __init__(self, primary_score):
        self.primary_score = primary_score
        self.scores = {"score1": 0.5}
    
    def to_dict(self):
        return {"primary_score": self.primary_score}


class TestAnalysisResult:
    """Test AnalysisResult dataclass."""
    
    def test_to_dict(self):
        """Test to_dict returns all fields."""
        result = AnalysisResult(
            title="Test",
            capabilities=["cap1"],
            capabilities_by_domain={"domain1": ["cap1"]},
            capability_count=1,
            range_analysis=None,
            chromatic_complexity=0.5,
            measure_count=32,
            tempo_bpm=120,
            tempo_marking="Allegro",
            tempo_profile=None,
            soft_gates={},
            unified_scores={},
            detailed_extraction={}
        )
        
        d = result.to_dict()
        
        assert d["title"] == "Test"
        assert d["capabilities"] == ["cap1"]
        assert d["capability_count"] == 1


class TestMaterialAnalysisServiceInit:
    """Test service initialization."""
    
    def test_init_creates_analyzers(self):
        """Test initialization creates analyzer and calculator."""
        service = MaterialAnalysisService()
        
        # Verify analyzers are initialized and have expected methods
        assert service.analyzer is not None
        assert hasattr(service.analyzer, 'analyze')
        assert service.soft_gate_calculator is not None
        assert hasattr(service.soft_gate_calculator, 'calculate_from_musicxml')
        assert service.registry is None  # Lazy loaded


class TestEnsureRegistryLoaded:
    """Test _ensure_registry_loaded method."""
    
    @patch('app.services.material_analysis_service.DetectionEngine')
    @patch('app.services.material_analysis_service.CapabilityRegistry')
    def test_loads_registry_on_first_call(self, mock_registry_class, mock_engine_class):
        """Test registry is loaded on first call."""
        mock_registry = Mock()
        mock_registry_class.return_value = mock_registry
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        service = MaterialAnalysisService()
        service._ensure_registry_loaded()
        
        mock_registry.load.assert_called_once()
        mock_engine_class.assert_called_once_with(mock_registry)
        assert service.registry == mock_registry
        assert service.engine == mock_engine
    
    @patch('app.services.material_analysis_service.CapabilityRegistry')
    def test_does_not_reload_registry(self, mock_registry_class):
        """Test registry is not reloaded on subsequent calls."""
        service = MaterialAnalysisService()
        service.registry = Mock()  # Already loaded
        service.engine = Mock()
        
        service._ensure_registry_loaded()
        
        mock_registry_class.assert_not_called()


class TestComputeSoftGates:
    """Test _compute_soft_gates method."""
    
    def test_compute_soft_gates_success(self):
        """Test successful soft gate computation."""
        service = MaterialAnalysisService()
        service.soft_gate_calculator = Mock()
        service.soft_gate_calculator.calculate_from_musicxml.return_value = MockSoftGateMetrics()
        
        result = service._compute_soft_gates("<xml>content</xml>")
        
        assert "tonal_complexity_stage" in result
        assert result["tonal_complexity_stage"] == 2
        assert result["interval_size_stage"] == 3
        assert result["rhythm_complexity_score"] == 0.45
    
    def test_compute_soft_gates_error(self):
        """Test soft gate computation error handling."""
        service = MaterialAnalysisService()
        service.soft_gate_calculator = Mock()
        service.soft_gate_calculator.calculate_from_musicxml.side_effect = ValueError("Parse error")
        
        result = service._compute_soft_gates("<xml>bad</xml>")
        
        assert "error" in result
        assert "Parse error" in result["error"]


class TestFormatIntervalProfile:
    """Test _format_interval_profile method."""
    
    def test_format_interval_profile_with_data(self):
        """Test formatting interval profile."""
        service = MaterialAnalysisService()
        metrics = MockSoftGateMetrics()
        
        result = service._format_interval_profile(metrics)
        
        assert result["total_intervals"] == 100
        assert result["step_ratio"] == 0.6
        assert result["p50"] == 2
    
    def test_format_interval_profile_none(self):
        """Test returns None when no profile."""
        service = MaterialAnalysisService()
        metrics = MockSoftGateMetrics()
        metrics.interval_profile = None
        
        result = service._format_interval_profile(metrics)
        
        assert result is None


class TestFormatIntervalLocalDifficulty:
    """Test _format_interval_local_difficulty method."""
    
    def test_format_local_difficulty_with_data(self):
        """Test formatting local difficulty."""
        service = MaterialAnalysisService()
        metrics = MockSoftGateMetrics()
        
        result = service._format_interval_local_difficulty(metrics)
        
        assert result["max_large_in_window"] == 3
        assert result["hardest_measures"] == [5, 12]
    
    def test_format_local_difficulty_none(self):
        """Test returns None when no data."""
        service = MaterialAnalysisService()
        metrics = MockSoftGateMetrics()
        metrics.interval_local_difficulty = None
        
        result = service._format_interval_local_difficulty(metrics)
        
        assert result is None


class TestDetectCapabilities:
    """Test _detect_capabilities method."""
    
    @patch('app.services.material_analysis_service.DetectionEngine')
    @patch('app.services.material_analysis_service.CapabilityRegistry')
    def test_detect_capabilities_success(self, mock_registry_class, mock_engine_class):
        """Test successful capability detection."""
        mock_registry = Mock()
        mock_registry.capabilities_by_domain = {
            "pitch": ["cap1", "cap2"],
            "rhythm": ["cap3"]
        }
        mock_registry.capability_bit_index = {"cap1": 1, "cap2": 2, "cap3": 3}
        mock_registry_class.return_value = mock_registry
        
        mock_engine = Mock()
        mock_engine.detect_capabilities.return_value = ["cap1", "cap3"]
        mock_engine_class.return_value = mock_engine
        
        service = MaterialAnalysisService()
        result = MockExtractionResult()
        
        caps, by_domain = service._detect_capabilities(result, ["fallback"])
        
        assert "cap1" in caps
        assert "cap3" in caps
        assert by_domain["pitch"] == ["cap1"]
        assert by_domain["rhythm"] == ["cap3"]
    
    def test_detect_capabilities_fallback_on_error(self):
        """Test falls back on error."""
        service = MaterialAnalysisService()
        service.registry = Mock()
        service.registry.load.side_effect = ValueError("Registry error")
        
        result = MockExtractionResult()
        
        caps, by_domain = service._detect_capabilities(result, ["fallback_cap"])
        
        assert caps == ["fallback_cap"]
        assert by_domain == {"unknown": ["fallback_cap"]}


class TestComputeUnifiedScores:
    """Test _compute_unified_scores method."""
    
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    def test_compute_unified_scores_success(self, mock_domain_scores, mock_composite):
        """Test successful unified score computation."""
        mock_domain_scores.return_value = {
            "interval": MockDomainResult(0.5),
            "rhythm": MockDomainResult(0.6)
        }
        mock_composite.return_value = {"combined": 0.55}
        
        service = MaterialAnalysisService()
        result = MockExtractionResult()
        metrics = MockSoftGateMetrics()
        
        scores = service._compute_unified_scores(result, metrics)
        
        assert "interval" in scores
        assert "composite" in scores
        assert scores["composite"] == {"combined": 0.55}
    
    def test_compute_unified_scores_no_metrics(self):
        """Test returns error when no metrics."""
        service = MaterialAnalysisService()
        result = MockExtractionResult()
        
        scores = service._compute_unified_scores(result, None)
        
        assert scores == {"error": "No metrics available"}
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    def test_compute_unified_scores_error(self, mock_domain_scores):
        """Test error handling in unified scores."""
        mock_domain_scores.side_effect = ValueError("Calculation error")
        
        service = MaterialAnalysisService()
        result = MockExtractionResult()
        metrics = MockSoftGateMetrics()
        
        scores = service._compute_unified_scores(result, metrics)
        
        assert "error" in scores
        assert "Calculation error" in scores["error"]


class TestAnalyzeMusicxml:
    """Test analyze_musicxml method."""
    
    def test_analyze_musicxml_basic(self):
        """Test basic MusicXML analysis."""
        service = MaterialAnalysisService()
        service.analyzer = Mock()
        service.soft_gate_calculator = Mock()
        
        mock_result = MockExtractionResult()
        service.analyzer.analyze.return_value = mock_result
        service.analyzer.get_capability_names.return_value = ["cap1"]
        
        with patch.object(service, '_compute_soft_gates', return_value={"tonal": 2}):
            with patch.object(service, '_detect_capabilities', return_value=(["cap1"], {"pitch": ["cap1"]})):
                with patch.object(service, '_compute_unified_scores', return_value={"score": 0.5}):
                    result = service.analyze_musicxml("<xml>content</xml>", title="My Title")
        
        assert result.title == "My Title"
        assert result.capabilities == ["cap1"]
        assert result.measure_count == 32
    
    def test_analyze_musicxml_uses_extraction_title(self):
        """Test uses title from extraction when not provided."""
        service = MaterialAnalysisService()
        service.analyzer = Mock()
        service.soft_gate_calculator = Mock()
        
        mock_result = MockExtractionResult()
        mock_result.title = "Extraction Title"
        service.analyzer.analyze.return_value = mock_result
        service.analyzer.get_capability_names.return_value = []
        
        with patch.object(service, '_compute_soft_gates', return_value={}):
            with patch.object(service, '_detect_capabilities', return_value=([], {})):
                with patch.object(service, '_compute_unified_scores', return_value={}):
                    result = service.analyze_musicxml("<xml>content</xml>")
        
        assert result.title == "Extraction Title"


class TestGetAnalysisService:
    """Test get_analysis_service singleton."""
    
    def test_creates_singleton(self):
        """Test singleton creation."""
        import app.services.material_analysis_service as module
        module._analysis_service = None
        
        service = get_analysis_service()
        
        # Verify service has expected interface
        assert service is not None
        assert hasattr(service, 'analyze_musicxml')
        assert isinstance(service, MaterialAnalysisService)
    
    def test_returns_same_instance(self):
        """Test returns same instance."""
        import app.services.material_analysis_service as module
        module._analysis_service = None
        
        s1 = get_analysis_service()
        s2 = get_analysis_service()
        
        assert s1 is s2
