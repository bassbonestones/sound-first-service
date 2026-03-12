"""
Tests for engine data loader utilities.

Tests pure functions that extract and transform data.
"""

import pytest
import json
from unittest.mock import MagicMock

from app.services.engine.data_loaders import extract_hazard_data


class TestExtractHazardData:
    """Test extract_hazard_data function."""
    
    def test_empty_analysis_returns_empty(self):
        """Analysis with no JSON should return empty dicts."""
        analysis = MagicMock()
        analysis.interval_analysis_json = None
        analysis.rhythm_analysis_json = None
        analysis.tonal_analysis_json = None
        analysis.tempo_analysis_json = None
        analysis.range_analysis_json = None
        analysis.throughput_analysis_json = None
        
        hazard_scores, hazard_flags = extract_hazard_data(analysis)
        assert hazard_scores == {}
        assert hazard_flags == []
    
    def test_single_domain_with_hazard_score(self):
        """Single domain should extract hazard score."""
        analysis = MagicMock()
        analysis.interval_analysis_json = json.dumps({
            "scores": {"hazard": 0.3, "primary": 0.5},
            "flags": []
        })
        analysis.rhythm_analysis_json = None
        analysis.tonal_analysis_json = None
        analysis.tempo_analysis_json = None
        analysis.range_analysis_json = None
        analysis.throughput_analysis_json = None
        
        hazard_scores, hazard_flags = extract_hazard_data(analysis)
        assert hazard_scores == {"interval": 0.3}
        assert hazard_flags == []
    
    def test_single_domain_with_flags(self):
        """Single domain should extract flags with prefix."""
        analysis = MagicMock()
        analysis.interval_analysis_json = json.dumps({
            "scores": {"hazard": 0.2},
            "flags": ["chromatic", "wide_leap"]
        })
        analysis.rhythm_analysis_json = None
        analysis.tonal_analysis_json = None
        analysis.tempo_analysis_json = None
        analysis.range_analysis_json = None
        analysis.throughput_analysis_json = None
        
        hazard_scores, hazard_flags = extract_hazard_data(analysis)
        assert "interval:chromatic" in hazard_flags
        assert "interval:wide_leap" in hazard_flags
    
    def test_multiple_domains(self):
        """Multiple domains should all be extracted."""
        analysis = MagicMock()
        analysis.interval_analysis_json = json.dumps({
            "scores": {"hazard": 0.3},
            "flags": ["leap_flag"]
        })
        analysis.rhythm_analysis_json = json.dumps({
            "scores": {"hazard": 0.5},
            "flags": ["syncopation"]
        })
        analysis.tonal_analysis_json = json.dumps({
            "scores": {"hazard": 0.1}
        })
        analysis.tempo_analysis_json = None
        analysis.range_analysis_json = None
        analysis.throughput_analysis_json = None
        
        hazard_scores, hazard_flags = extract_hazard_data(analysis)
        assert hazard_scores["interval"] == 0.3
        assert hazard_scores["rhythm"] == 0.5
        assert hazard_scores["tonal"] == 0.1
        assert "interval:leap_flag" in hazard_flags
        assert "rhythm:syncopation" in hazard_flags
    
    def test_invalid_json_skipped(self):
        """Invalid JSON should be skipped without error."""
        analysis = MagicMock()
        analysis.interval_analysis_json = "not valid json {"
        analysis.rhythm_analysis_json = json.dumps({"scores": {"hazard": 0.5}})
        analysis.tonal_analysis_json = None
        analysis.tempo_analysis_json = None
        analysis.range_analysis_json = None
        analysis.throughput_analysis_json = None
        
        hazard_scores, hazard_flags = extract_hazard_data(analysis)
        assert "interval" not in hazard_scores  # Skipped due to invalid JSON
        assert hazard_scores["rhythm"] == 0.5
    
    def test_missing_scores_key(self):
        """JSON without scores key should not crash."""
        analysis = MagicMock()
        analysis.interval_analysis_json = json.dumps({"other_key": "value"})
        analysis.rhythm_analysis_json = None
        analysis.tonal_analysis_json = None
        analysis.tempo_analysis_json = None
        analysis.range_analysis_json = None
        analysis.throughput_analysis_json = None
        
        hazard_scores, hazard_flags = extract_hazard_data(analysis)
        assert hazard_scores.get("interval") is None
    
    def test_all_six_domains(self):
        """All six domains should be processed."""
        analysis = MagicMock()
        analysis.interval_analysis_json = json.dumps({"scores": {"hazard": 0.1}})
        analysis.rhythm_analysis_json = json.dumps({"scores": {"hazard": 0.2}})
        analysis.tonal_analysis_json = json.dumps({"scores": {"hazard": 0.3}})
        analysis.tempo_analysis_json = json.dumps({"scores": {"hazard": 0.4}})
        analysis.range_analysis_json = json.dumps({"scores": {"hazard": 0.5}})
        analysis.throughput_analysis_json = json.dumps({"scores": {"hazard": 0.6}})
        
        hazard_scores, hazard_flags = extract_hazard_data(analysis)
        assert len(hazard_scores) == 6
        assert hazard_scores["interval"] == 0.1
        assert hazard_scores["rhythm"] == 0.2
        assert hazard_scores["tonal"] == 0.3
        assert hazard_scores["tempo"] == 0.4
        assert hazard_scores["range"] == 0.5
        assert hazard_scores["throughput"] == 0.6
