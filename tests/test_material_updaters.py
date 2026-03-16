"""
Tests for material analysis updaters.

Comprehensive tests for functions that update MaterialAnalysis records.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from dataclasses import dataclass
from typing import Optional, Dict, Any


# Mock classes for testing without database
class MockMaterialAnalysis:
    """Mock MaterialAnalysis for testing."""
    def __init__(self):
        # Range analysis
        self.lowest_pitch = None
        self.highest_pitch = None
        self.range_semitones = None
        self.pitch_density_low = None
        self.pitch_density_mid = None
        self.pitch_density_high = None
        self.trill_lowest = None
        self.trill_highest = None
        
        # Soft gate metrics
        self.tonal_complexity_stage = None
        self.interval_size_stage = None
        self.interval_sustained_stage = None
        self.interval_hazard_stage = None
        self.legacy_interval_size_stage = None
        
        # Interval profile
        self.interval_step_ratio = None
        self.interval_skip_ratio = None
        self.interval_leap_ratio = None
        self.interval_large_leap_ratio = None
        self.interval_extreme_leap_ratio = None
        self.interval_p50 = None
        self.interval_p75 = None
        self.interval_p90 = None
        
        # Interval local difficulty
        self.interval_max_large_in_window = None
        self.interval_max_extreme_in_window = None
        self.interval_hardest_measures = None
        
        # Rhythm and other stages
        self.rhythm_complexity_stage = None
        self.rhythm_complexity_peak = None
        self.rhythm_complexity_p95 = None
        self.range_usage_stage = None
        self.density_notes_per_second = None
        self.note_density_per_measure = None
        self.tempo_difficulty_score = None
        self.interval_velocity_score = None
        self.interval_velocity_peak = None
        self.interval_velocity_p95 = None
        self.unique_pitch_count = None
        self.largest_interval_semitones = None
        
        # Domain scores
        self.rhythm_domain_score = None
        self.interval_domain_score = None
        self.range_domain_score = None
        self.throughput_domain_score = None
        self.tonality_domain_score = None
        
        # Difficulty scores
        self.physical_difficulty = None
        self.cognitive_difficulty = None
        self.combined_difficulty = None
        
        # Unified scores
        self.analysis_schema_version = None
        self.interval_analysis_json = None
        self.rhythm_analysis_json = None
        self.tonal_analysis_json = None
        self.tempo_analysis_json = None
        self.range_analysis_json = None
        self.throughput_analysis_json = None
        self.interval_primary_score = None
        self.rhythm_primary_score = None
        self.tonal_primary_score = None
        self.tempo_primary_score = None
        self.range_primary_score = None
        self.throughput_primary_score = None
        self.overall_score = None
        self.interaction_bonus = None


@dataclass
class MockIntervalProfile:
    """Mock interval profile data."""
    step_ratio: float = 0.5
    skip_ratio: float = 0.3
    leap_ratio: float = 0.15
    large_leap_ratio: float = 0.04
    extreme_leap_ratio: float = 0.01
    interval_p50: int = 2
    interval_p75: int = 4
    interval_p90: int = 7


@dataclass
class MockIntervalLocalDifficulty:
    """Mock interval local difficulty data."""
    max_large_leaps_in_window: int = 2
    max_extreme_leaps_in_window: int = 0
    hardest_measure_numbers: list = None
    
    def __post_init__(self):
        if self.hardest_measure_numbers is None:
            self.hardest_measure_numbers = [5, 12, 18]


@dataclass
class MockSoftGates:
    """Mock soft gates data."""
    tonal_complexity_stage: int = 2
    interval_size_stage: int = 3
    interval_sustained_stage: int = 2
    interval_hazard_stage: int = 3
    legacy_interval_size_stage: int = 3
    interval_profile: MockIntervalProfile = None
    interval_local_difficulty: MockIntervalLocalDifficulty = None
    rhythm_complexity_score: float = 0.45
    rhythm_complexity_peak: float = 0.65
    rhythm_complexity_p95: float = 0.58
    range_usage_stage: int = 2
    density_notes_per_second: float = 2.5
    note_density_per_measure: float = 8.0
    tempo_difficulty_score: float = 0.35
    interval_velocity_score: float = 0.42
    interval_velocity_peak: float = 0.68
    interval_velocity_p95: float = 0.55
    unique_pitch_count: int = 7
    largest_interval_semitones: int = 12
    
    def __post_init__(self):
        if self.interval_profile is None:
            self.interval_profile = MockIntervalProfile()
        if self.interval_local_difficulty is None:
            self.interval_local_difficulty = MockIntervalLocalDifficulty()


@dataclass
class MockRangeAnalysis:
    """Mock range analysis data."""
    lowest_pitch: str = "C4"
    highest_pitch: str = "G5"
    range_semitones: int = 19
    density_low: float = 0.25
    density_mid: float = 0.50
    density_high: float = 0.25
    trill_lowest: str = "D4"
    trill_highest: str = "F5"


@dataclass
class MockRhythmPatternAnalysis:
    """Mock rhythm pattern analysis."""
    rhythm_measure_uniqueness_ratio: float = 0.75
    rhythm_measure_repetition_ratio: float = 0.25


@dataclass
class MockTempoProfile:
    """Mock tempo profile."""
    def to_dict(self) -> Dict[str, Any]:
        return {
            "base_bpm": 120,
            "tempo_marking": "Allegro",
            "stability": 0.95
        }


@dataclass
class MockExtractionResult:
    """Mock extraction result."""
    range_analysis: MockRangeAnalysis = None
    tempo_profile: MockTempoProfile = None
    rhythm_pattern_analysis: MockRhythmPatternAnalysis = None
    note_values: Dict[str, int] = None
    tuplets: Dict[str, int] = None
    dotted_notes: list = None
    has_ties: bool = False
    
    def __post_init__(self):
        if self.range_analysis is None:
            self.range_analysis = MockRangeAnalysis()
        if self.tempo_profile is None:
            self.tempo_profile = MockTempoProfile()
        if self.rhythm_pattern_analysis is None:
            self.rhythm_pattern_analysis = MockRhythmPatternAnalysis()
        if self.note_values is None:
            self.note_values = {"quarter": 16, "eighth": 8, "half": 4}
        if self.tuplets is None:
            self.tuplets = {"triplet": 2}
        if self.dotted_notes is None:
            self.dotted_notes = ["dotted_quarter"]


# Import the functions under test
from app.services.material.updaters import (
    update_soft_gates,
    update_unified_scores,
    calculate_difficulty_scores,
    update_range_analysis,
    persist_unified_scores
)


# =============================================================================
# UPDATE SOFT GATES
# =============================================================================

class TestUpdateSoftGates:
    """Test update_soft_gates function."""
    
    def test_updates_tonal_complexity_stage(self):
        """Should update tonal_complexity_stage."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_soft_gates(analysis, soft_gates)
        
        assert analysis.tonal_complexity_stage == 2
    
    def test_updates_interval_stages(self):
        """Should update all interval stage fields."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_soft_gates(analysis, soft_gates)
        
        assert analysis.interval_size_stage == 3
        assert analysis.interval_sustained_stage == 2
        assert analysis.interval_hazard_stage == 3
        assert analysis.legacy_interval_size_stage == 3
    
    def test_updates_interval_profile_ratios(self):
        """Should update interval profile ratio fields."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_soft_gates(analysis, soft_gates)
        
        assert analysis.interval_step_ratio == 0.5
        assert analysis.interval_skip_ratio == 0.3
        assert analysis.interval_leap_ratio == 0.15
        assert analysis.interval_large_leap_ratio == 0.04
        assert analysis.interval_extreme_leap_ratio == 0.01
    
    def test_updates_interval_percentiles(self):
        """Should update interval percentile fields."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_soft_gates(analysis, soft_gates)
        
        assert analysis.interval_p50 == 2
        assert analysis.interval_p75 == 4
        assert analysis.interval_p90 == 7
    
    def test_updates_local_difficulty(self):
        """Should update interval local difficulty fields."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_soft_gates(analysis, soft_gates)
        
        assert analysis.interval_max_large_in_window == 2
        assert analysis.interval_max_extreme_in_window == 0
        assert analysis.interval_hardest_measures == '[5, 12, 18]'
    
    def test_updates_rhythm_fields(self):
        """Should update rhythm complexity fields."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_soft_gates(analysis, soft_gates)
        
        assert analysis.rhythm_complexity_stage == 0.45
        assert analysis.rhythm_complexity_peak == 0.65
        assert analysis.rhythm_complexity_p95 == 0.58
    
    def test_updates_density_fields(self):
        """Should update density and throughput fields."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_soft_gates(analysis, soft_gates)
        
        assert analysis.density_notes_per_second == 2.5
        assert analysis.note_density_per_measure == 8.0
        assert analysis.tempo_difficulty_score == 0.35
    
    def test_updates_interval_velocity(self):
        """Should update interval velocity fields."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_soft_gates(analysis, soft_gates)
        
        assert analysis.interval_velocity_score == 0.42
        assert analysis.interval_velocity_peak == 0.68
        assert analysis.interval_velocity_p95 == 0.55
    
    def test_updates_pitch_count(self):
        """Should update unique pitch count and largest interval."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_soft_gates(analysis, soft_gates)
        
        assert analysis.unique_pitch_count == 7
        assert analysis.largest_interval_semitones == 12
    
    def test_returns_summary_dict(self):
        """Should return summary dictionary with key metrics."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        result = update_soft_gates(analysis, soft_gates)
        
        # Verify dict has expected keys
        assert result["tonal_complexity_stage"] == 2
        assert result["interval_size_stage"] == 3
        assert result["rhythm_complexity_score"] == pytest.approx(0.45, rel=0.01)
        assert result["range_usage_stage"] == 2
    
    def test_handles_none_interval_profile(self):
        """Should handle None interval_profile gracefully."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        soft_gates.interval_profile = None
        
        update_soft_gates(analysis, soft_gates)
        
        # Profile fields should remain None
        assert analysis.interval_step_ratio is None
        assert analysis.interval_p50 is None
    
    def test_handles_none_local_difficulty(self):
        """Should handle None interval_local_difficulty gracefully."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        soft_gates.interval_local_difficulty = None
        
        update_soft_gates(analysis, soft_gates)
        
        # Local difficulty fields should remain None
        assert analysis.interval_max_large_in_window is None
        assert analysis.interval_hardest_measures is None
    
    def test_handles_none_rhythm_complexity_peak(self):
        """Should handle None values in optional fields."""
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        soft_gates.rhythm_complexity_peak = None
        soft_gates.rhythm_complexity_p95 = None
        
        result = update_soft_gates(analysis, soft_gates)
        
        assert result["rhythm_complexity_peak"] is None
        assert result["rhythm_complexity_p95"] is None


# =============================================================================
# UPDATE UNIFIED SCORES
# =============================================================================

class TestUpdateUnifiedScores:
    """Test update_unified_scores function."""
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    def test_calls_calculate_unified_domain_scores(self, mock_calc):
        """Should call calculate_unified_domain_scores with soft_gates."""
        mock_result = MagicMock()
        mock_result.rhythm_score = 0.5
        mock_result.interval_score = 0.4
        mock_result.range_score = 0.3
        mock_result.throughput_score = 0.6
        mock_result.tonality_score = 0.25
        mock_calc.return_value = mock_result
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_unified_scores(analysis, soft_gates)
        
        mock_calc.assert_called_once_with(soft_gates)
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    def test_updates_domain_scores(self, mock_calc):
        """Should update all domain score fields."""
        mock_result = MagicMock()
        mock_result.rhythm_score = 0.5
        mock_result.interval_score = 0.4
        mock_result.range_score = 0.3
        mock_result.throughput_score = 0.6
        mock_result.tonality_score = 0.25
        mock_calc.return_value = mock_result
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        update_unified_scores(analysis, soft_gates)
        
        assert analysis.rhythm_domain_score == 0.5
        assert analysis.interval_domain_score == 0.4
        assert analysis.range_domain_score == 0.3
        assert analysis.throughput_domain_score == 0.6
        assert analysis.tonality_domain_score == 0.25
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    def test_returns_rounded_scores(self, mock_calc):
        """Should return scores rounded to 2 decimal places."""
        mock_result = MagicMock()
        mock_result.rhythm_score = 0.5555
        mock_result.interval_score = 0.4444
        mock_result.range_score = 0.3333
        mock_result.throughput_score = 0.6666
        mock_result.tonality_score = 0.2222
        mock_calc.return_value = mock_result
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        
        result = update_unified_scores(analysis, soft_gates)
        
        assert result["rhythm_domain_score"] == 0.56
        assert result["interval_domain_score"] == 0.44
        assert result["range_domain_score"] == 0.33
        assert result["throughput_domain_score"] == 0.67
        assert result["tonality_domain_score"] == 0.22


# =============================================================================
# CALCULATE DIFFICULTY SCORES
# =============================================================================

class TestCalculateDifficultyScores:
    """Test calculate_difficulty_scores function."""
    
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_calls_calculate_composite_difficulty(self, mock_calc):
        """Should call calculate_composite_difficulty with analysis."""
        mock_result = MagicMock()
        mock_result.physical_difficulty = 0.5
        mock_result.cognitive_difficulty = 0.6
        mock_result.combined_difficulty = 0.55
        mock_calc.return_value = mock_result
        
        analysis = MockMaterialAnalysis()
        
        calculate_difficulty_scores(analysis)
        
        mock_calc.assert_called_once_with(analysis)
    
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_updates_difficulty_fields(self, mock_calc):
        """Should update all difficulty score fields."""
        mock_result = MagicMock()
        mock_result.physical_difficulty = 0.5
        mock_result.cognitive_difficulty = 0.6
        mock_result.combined_difficulty = 0.55
        mock_calc.return_value = mock_result
        
        analysis = MockMaterialAnalysis()
        
        calculate_difficulty_scores(analysis)
        
        assert analysis.physical_difficulty == 0.5
        assert analysis.cognitive_difficulty == 0.6
        assert analysis.combined_difficulty == 0.55
    
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_returns_rounded_scores(self, mock_calc):
        """Should return scores rounded to 2 decimal places."""
        mock_result = MagicMock()
        mock_result.physical_difficulty = 0.5555
        mock_result.cognitive_difficulty = 0.6666
        mock_result.combined_difficulty = 0.5555
        mock_calc.return_value = mock_result
        
        analysis = MockMaterialAnalysis()
        
        result = calculate_difficulty_scores(analysis)
        
        assert result["physical_difficulty"] == 0.56
        assert result["cognitive_difficulty"] == 0.67
        assert result["combined_difficulty"] == 0.56


# =============================================================================
# UPDATE RANGE ANALYSIS
# =============================================================================

class TestUpdateRangeAnalysis:
    """Test update_range_analysis function."""
    
    def test_updates_pitch_range(self):
        """Should update lowest and highest pitch."""
        analysis = MockMaterialAnalysis()
        extraction = MockExtractionResult()
        
        update_range_analysis(analysis, extraction)
        
        assert analysis.lowest_pitch == "C4"
        assert analysis.highest_pitch == "G5"
        assert analysis.range_semitones == 19
    
    def test_updates_pitch_density(self):
        """Should update pitch density fields."""
        analysis = MockMaterialAnalysis()
        extraction = MockExtractionResult()
        
        update_range_analysis(analysis, extraction)
        
        assert analysis.pitch_density_low == 0.25
        assert analysis.pitch_density_mid == 0.50
        assert analysis.pitch_density_high == 0.25
    
    def test_updates_trill_range(self):
        """Should update trill range fields."""
        analysis = MockMaterialAnalysis()
        extraction = MockExtractionResult()
        
        update_range_analysis(analysis, extraction)
        
        assert analysis.trill_lowest == "D4"
        assert analysis.trill_highest == "F5"
    
    def test_returns_summary_dict(self):
        """Should return summary with key range metrics."""
        analysis = MockMaterialAnalysis()
        extraction = MockExtractionResult()
        
        result = update_range_analysis(analysis, extraction)
        
        assert result["lowest_pitch"] == "C4"
        assert result["highest_pitch"] == "G5"
        assert result["range_semitones"] == 19
    
    def test_handles_none_range_analysis(self):
        """Should handle None range_analysis gracefully."""
        analysis = MockMaterialAnalysis()
        extraction = MockExtractionResult()
        extraction.range_analysis = None
        
        result = update_range_analysis(analysis, extraction)
        
        assert result == {}
        assert analysis.lowest_pitch is None


# =============================================================================
# PERSIST UNIFIED SCORES
# =============================================================================

class TestPersistUnifiedScores:
    """Test persist_unified_scores function."""
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_sets_schema_version(self, mock_composite, mock_unified):
        """Should set analysis_schema_version to 1."""
        mock_unified.return_value = {
            'interval': MagicMock(to_dict=lambda: {}, scores={'primary': 0.5}),
            'rhythm': MagicMock(to_dict=lambda: {}, scores={'primary': 0.4}),
        }
        mock_composite.return_value = {'overall': 0.45, 'interaction_bonus': 0.02}
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        extraction = MockExtractionResult()
        
        persist_unified_scores(analysis, soft_gates, extraction)
        
        assert analysis.analysis_schema_version == 1
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_persists_domain_json(self, mock_composite, mock_unified):
        """Should persist domain analysis as JSON."""
        interval_dict = {'score': 0.5, 'band': 'medium'}
        rhythm_dict = {'score': 0.4, 'band': 'easy'}
        
        mock_unified.return_value = {
            'interval': MagicMock(to_dict=lambda: interval_dict, scores={'primary': 0.5}),
            'rhythm': MagicMock(to_dict=lambda: rhythm_dict, scores={'primary': 0.4}),
        }
        mock_composite.return_value = {'overall': 0.45, 'interaction_bonus': 0.02}
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        extraction = MockExtractionResult()
        
        persist_unified_scores(analysis, soft_gates, extraction)
        
        assert analysis.interval_analysis_json == json.dumps(interval_dict)
        assert analysis.rhythm_analysis_json == json.dumps(rhythm_dict)
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_persists_primary_scores(self, mock_composite, mock_unified):
        """Should persist indexed primary scores."""
        mock_unified.return_value = {
            'interval': MagicMock(to_dict=lambda: {}, scores={'primary': 0.55}),
            'rhythm': MagicMock(to_dict=lambda: {}, scores={'primary': 0.42}),
            'tonal': MagicMock(to_dict=lambda: {}, scores={'primary': 0.30}),
            'tempo': MagicMock(to_dict=lambda: {}, scores={'primary': 0.65}),
            'range': MagicMock(to_dict=lambda: {}, scores={'primary': 0.48}),
            'throughput': MagicMock(to_dict=lambda: {}, scores={'primary': 0.72}),
        }
        mock_composite.return_value = {'overall': 0.52, 'interaction_bonus': 0.05}
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        extraction = MockExtractionResult()
        
        persist_unified_scores(analysis, soft_gates, extraction)
        
        assert analysis.interval_primary_score == 0.55
        assert analysis.rhythm_primary_score == 0.42
        assert analysis.tonal_primary_score == 0.30
        assert analysis.tempo_primary_score == 0.65
        assert analysis.range_primary_score == 0.48
        assert analysis.throughput_primary_score == 0.72
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_persists_composite_scores(self, mock_composite, mock_unified):
        """Should persist overall and interaction bonus."""
        mock_unified.return_value = {}
        mock_composite.return_value = {'overall': 0.58, 'interaction_bonus': 0.08}
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        extraction = MockExtractionResult()
        
        persist_unified_scores(analysis, soft_gates, extraction)
        
        assert analysis.overall_score == 0.58
        assert analysis.interaction_bonus == 0.08
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_returns_composite_dict(self, mock_composite, mock_unified):
        """Should return composite difficulty dictionary."""
        mock_unified.return_value = {}
        expected = {'overall': 0.58, 'interaction_bonus': 0.08}
        mock_composite.return_value = expected
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        extraction = MockExtractionResult()
        
        result = persist_unified_scores(analysis, soft_gates, extraction)
        
        assert result == expected
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    def test_reraises_exceptions(self, mock_unified):
        """Should reraise any exceptions."""
        mock_unified.side_effect = ValueError("Test error")
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        extraction = MockExtractionResult()
        
        with pytest.raises(ValueError, match="Test error"):
            persist_unified_scores(analysis, soft_gates, extraction)
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_builds_extraction_dict_with_rhythm_pattern(self, mock_composite, mock_unified):
        """Should include rhythm pattern analysis in extraction dict."""
        mock_unified.return_value = {}
        mock_composite.return_value = {'overall': 0.5}
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        extraction = MockExtractionResult()
        
        persist_unified_scores(analysis, soft_gates, extraction)
        
        # Verify calculate_unified_domain_scores was called with proper args
        call_kwargs = mock_unified.call_args[1]
        assert 'metrics' in call_kwargs
        assert 'extraction' in call_kwargs
        extraction_dict = call_kwargs['extraction']
        assert extraction_dict['rhythm_measure_uniqueness_ratio'] == 0.75
        assert extraction_dict['rhythm_measure_repetition_ratio'] == 0.25
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_handles_none_rhythm_pattern_analysis(self, mock_composite, mock_unified):
        """Should handle None rhythm_pattern_analysis."""
        mock_unified.return_value = {}
        mock_composite.return_value = {'overall': 0.5}
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        extraction = MockExtractionResult()
        extraction.rhythm_pattern_analysis = None
        
        # Should not raise and should return result
        result = persist_unified_scores(analysis, soft_gates, extraction)
        
        # Verify function completed without raising an exception
        # Result can be None or a value, but should not be an exception
        assert not isinstance(result, Exception), f"Function raised: {result}"
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_handles_none_tempo_profile(self, mock_composite, mock_unified):
        """Should handle None tempo_profile."""
        mock_unified.return_value = {}
        mock_composite.return_value = {'overall': 0.5}
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        extraction = MockExtractionResult()
        extraction.tempo_profile = None
        
        persist_unified_scores(analysis, soft_gates, extraction)
        
        call_kwargs = mock_unified.call_args[1]
        assert call_kwargs['tempo_profile'] is None
    
    @patch('app.soft_gate_calculator.calculate_unified_domain_scores')
    @patch('app.difficulty_interactions.calculate_composite_difficulty')
    def test_handles_none_range_analysis(self, mock_composite, mock_unified):
        """Should handle None range_analysis in extraction."""
        mock_unified.return_value = {}
        mock_composite.return_value = {'overall': 0.5}
        
        analysis = MockMaterialAnalysis()
        soft_gates = MockSoftGates()
        extraction = MockExtractionResult()
        extraction.range_analysis = None
        
        persist_unified_scores(analysis, soft_gates, extraction)
        
        call_kwargs = mock_unified.call_args[1]
        assert call_kwargs['range_analysis'] is None
