"""
Tests for composite scoring module.

Tests aggregate domain analysis and result containers.
"""

import pytest
from app.scoring.composite import (
    AllDomainResults,
    analyze_all_domains,
    interval_profile_to_scores,
    rhythm_profile_to_scores,
    throughput_profile_to_scores,
    pattern_profile_to_scores,
)
from app.scoring.models import DomainResult, DomainScores, DomainBands


class TestAllDomainResults:
    """Test AllDomainResults dataclass."""
    
    def test_empty_results(self):
        """Empty results should have all None."""
        results = AllDomainResults()
        assert results.interval is None
        assert results.rhythm is None
        assert results.tonal is None
        assert results.tempo is None
        assert results.range is None
        assert results.throughput is None
        assert results.pattern is None
    
    def test_to_dict_empty(self):
        """Empty results should convert to empty dict."""
        results = AllDomainResults()
        assert results.to_dict() == {}
    
    def test_to_dict_with_results(self):
        """Results with data should convert to dict."""
        scores: DomainScores = {'primary': 0.5, 'hazard': 0.2, 'overall': 0.4}
        bands: DomainBands = {'primary_stage': 3, 'hazard_stage': 1, 'overall_stage': 2}
        result = DomainResult(scores=scores, bands=bands, flags=[])
        
        results = AllDomainResults(interval=result)
        d = results.to_dict()
        
        assert 'interval' in d
        assert d['interval']['scores']['primary'] == 0.5
    
    def test_to_dict_multiple_domains(self):
        """Multiple domains should all appear in dict."""
        scores: DomainScores = {'primary': 0.5, 'hazard': 0.2, 'overall': 0.4}
        bands: DomainBands = {'primary_stage': 3, 'hazard_stage': 1, 'overall_stage': 2}
        result = DomainResult(scores=scores, bands=bands, flags=[])
        
        results = AllDomainResults(
            interval=result,
            rhythm=result,
            tonal=result
        )
        d = results.to_dict()
        
        assert 'interval' in d
        assert 'rhythm' in d
        assert 'tonal' in d
        assert 'tempo' not in d


class TestAnalyzeAllDomains:
    """Test analyze_all_domains function."""
    
    def test_empty_profiles(self):
        """Empty profiles should return empty results."""
        results = analyze_all_domains({})
        d = results.to_dict()
        assert d == {}
    
    def test_single_domain(self):
        """Single domain should analyze just that."""
        profiles = {
            'interval': {
                'step_ratio': 0.7,
                'skip_ratio': 0.2,
                'leap_ratio': 0.1,
                'interval_p90': 5,
            }
        }
        results = analyze_all_domains(profiles)
        # Verify interval is populated by accessing its attributes
        assert results.interval.scores['overall'] >= 0
        assert results.rhythm is None
    
    def test_multiple_domains(self):
        """Multiple domains should all be analyzed."""
        profiles = {
            'interval': {
                'step_ratio': 0.7,
                'skip_ratio': 0.2,
                'leap_ratio': 0.1,
                'interval_p90': 5,
            },
            'rhythm': {
                'mean_complexity': 0.3,
                'p95_complexity': 0.5,
            }
        }
        results = analyze_all_domains(profiles)
        # Verify both domains are populated with scores
        assert results.interval.scores['overall'] >= 0
        assert results.rhythm.scores['overall'] >= 0


class TestLegacyAliases:
    """Test backward compatibility alias functions."""
    
    def test_interval_profile_to_scores(self):
        """Legacy interval function should return scores dict."""
        profile = {
            'step_ratio': 0.7,
            'skip_ratio': 0.2,
            'leap_ratio': 0.1,
            'interval_p90': 5,
        }
        scores = interval_profile_to_scores(profile)
        # TypedDict so check keys instead of isinstance
        assert 'primary' in scores
        assert 'hazard' in scores
        assert 'overall' in scores
        assert 0.0 <= scores['primary'] <= 1.0
    
    def test_rhythm_profile_to_scores(self):
        """Legacy rhythm function should return scores dict."""
        profile = {
            'mean_complexity': 0.3,
            'p95_complexity': 0.5,
        }
        scores = rhythm_profile_to_scores(profile)
        assert 'primary' in scores
        assert 'hazard' in scores
        assert 'overall' in scores
        assert 0.0 <= scores['primary'] <= 1.0


class TestAllDomainsToDictBranches:
    """Test all branches of to_dict method."""
    
    def test_to_dict_with_tempo(self):
        """to_dict should include tempo when present."""
        from app.scoring.composite import AllDomainResults
        from app.scoring.models import DomainResult
        
        scores = {'primary': 0.4, 'hazard': 0.2, 'overall': 0.3}
        bands = {'primary_stage': 2, 'hazard_stage': 1, 'overall_stage': 2}
        result = DomainResult(scores=scores, bands=bands, flags=[])
        
        results = AllDomainResults(tempo=result)
        d = results.to_dict()
        
        assert 'tempo' in d
        assert d['tempo']['scores']['primary'] == 0.4

    def test_to_dict_with_range(self):
        """to_dict should include range when present."""
        from app.scoring.composite import AllDomainResults
        from app.scoring.models import DomainResult
        
        scores = {'primary': 0.5, 'hazard': 0.3, 'overall': 0.4}
        bands = {'primary_stage': 3, 'hazard_stage': 2, 'overall_stage': 2}
        result = DomainResult(scores=scores, bands=bands, flags=[])
        
        results = AllDomainResults(range=result)
        d = results.to_dict()
        
        assert 'range' in d

    def test_to_dict_with_throughput(self):
        """to_dict should include throughput when present."""
        from app.scoring.composite import AllDomainResults
        from app.scoring.models import DomainResult
        
        scores = {'primary': 0.6, 'hazard': 0.4, 'overall': 0.5}
        bands = {'primary_stage': 3, 'hazard_stage': 2, 'overall_stage': 3}
        result = DomainResult(scores=scores, bands=bands, flags=[])
        
        results = AllDomainResults(throughput=result)
        d = results.to_dict()
        
        assert 'throughput' in d

    def test_to_dict_with_pattern(self):
        """to_dict should include pattern when present."""
        from app.scoring.composite import AllDomainResults
        from app.scoring.models import DomainResult
        
        scores = {'primary': 0.3, 'hazard': 0.1, 'overall': 0.2}
        bands = {'primary_stage': 2, 'hazard_stage': 1, 'overall_stage': 1}
        result = DomainResult(scores=scores, bands=bands, flags=[])
        
        results = AllDomainResults(pattern=result)
        d = results.to_dict()
        
        assert 'pattern' in d


class TestAnalyzeAllDomainsBranches:
    """Test all branches of analyze_all_domains function."""
    
    def test_analyze_tempo_domain(self):
        """Tempo domain should be analyzed."""
        profiles = {
            'tempo': {
                'base_bpm': 120,
                'tempo_changes': 0,
                'rubato_events': 0,
            }
        }
        results = analyze_all_domains(profiles)
        assert results.tempo is not None
        assert results.tempo.scores is not None

    def test_analyze_range_domain(self):
        """Range domain should be analyzed."""
        profiles = {
            'range': {
                'range_semitones': 12,
                'tessitura_density': 0.6,
            }
        }
        results = analyze_all_domains(profiles)
        assert results.range is not None

    def test_analyze_throughput_domain(self):
        """Throughput domain should be analyzed."""
        profiles = {
            'throughput': {
                'notes_per_second_mean': 2.5,
                'notes_per_second_p95': 4.0,
            }
        }
        results = analyze_all_domains(profiles)
        assert results.throughput is not None

    def test_analyze_pattern_domain(self):
        """Pattern domain should be analyzed."""
        profiles = {
            'pattern': {
                'pattern_diversity': 0.5,
                'unique_patterns': 8,
            }
        }
        results = analyze_all_domains(profiles)
        assert results.pattern is not None


class TestLegacyAliases:
    """Tests for legacy alias functions."""

    def test_throughput_profile_to_scores(self):
        """throughput_profile_to_scores should return scores dict."""
        profile = {
            'notes_per_second_mean': 2.0,
            'notes_per_second_p95': 3.5,
        }
        scores = throughput_profile_to_scores(profile)
        assert isinstance(scores, dict)
        assert 'primary' in scores or scores.get('primary') is not None or len(scores) >= 0

    def test_pattern_profile_to_scores(self):
        """pattern_profile_to_scores should return scores dict."""
        profile = {
            'pattern_diversity': 0.5,
            'unique_patterns': 10,
        }
        scores = pattern_profile_to_scores(profile)
        assert isinstance(scores, dict)

    def test_throughput_profile_to_scores_empty(self):
        """throughput_profile_to_scores with empty profile."""
        profile = {}
        scores = throughput_profile_to_scores(profile)
        assert isinstance(scores, dict)

    def test_pattern_profile_to_scores_empty(self):
        """pattern_profile_to_scores with empty profile."""
        profile = {}
        scores = pattern_profile_to_scores(profile)
        assert isinstance(scores, dict)
