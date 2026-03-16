"""
Tests for scoring/models.py

Tests for scoring model dataclasses and type definitions.
"""

import pytest

from app.scoring.models import DomainScores, DomainBands, DomainResult


class TestDomainScores:
    """Tests for DomainScores TypedDict."""

    def test_create_domain_scores(self):
        """Should create domain scores."""
        scores: DomainScores = {
            'primary': 0.5,
            'hazard': 0.3,
            'overall': 0.45
        }
        
        assert scores['primary'] == 0.5
        assert scores['hazard'] == 0.3
        assert scores['overall'] == 0.45

    def test_domain_scores_as_dict(self):
        """Should be usable as dict."""
        scores: DomainScores = {
            'primary': 0.6,
            'hazard': 0.2,
            'overall': 0.5
        }
        
        assert 'primary' in scores
        assert 'hazard' in scores
        assert 'overall' in scores


class TestDomainBands:
    """Tests for DomainBands TypedDict."""

    def test_create_domain_bands(self):
        """Should create domain bands."""
        bands: DomainBands = {
            'primary_stage': 3,
            'hazard_stage': 2,
            'overall_stage': 3
        }
        
        assert bands['primary_stage'] == 3
        assert bands['hazard_stage'] == 2
        assert bands['overall_stage'] == 3


class TestDomainResult:
    """Tests for DomainResult dataclass."""

    def test_default_values(self):
        """Should have sensible defaults."""
        result = DomainResult()
        
        assert result.profile == {}
        assert result.facet_scores == {}
        assert result.scores['primary'] == 0.0
        assert result.scores['hazard'] == 0.0
        assert result.scores['overall'] == 0.0
        assert result.bands['primary_stage'] == 0
        assert result.flags == []
        assert result.confidence == 1.0

    def test_create_with_values(self):
        """Should create with custom values."""
        result = DomainResult(
            profile={'total_intervals': 50, 'step_ratio': 0.6},
            facet_scores={'texture': 0.3, 'size': 0.4},
            scores={'primary': 0.45, 'hazard': 0.2, 'overall': 0.4},
            bands={'primary_stage': 3, 'hazard_stage': 1, 'overall_stage': 2},
            flags=['complex_intervals'],
            confidence=0.95
        )
        
        assert result.profile['total_intervals'] == 50
        assert result.facet_scores['texture'] == 0.3
        assert result.scores['primary'] == 0.45
        assert result.bands['primary_stage'] == 3
        assert 'complex_intervals' in result.flags
        assert result.confidence == 0.95

    def test_to_dict(self):
        """Should convert to dictionary."""
        result = DomainResult(
            profile={'test': 'value'},
            facet_scores={'facet1': 0.5},
            scores={'primary': 0.3, 'hazard': 0.1, 'overall': 0.25},
            bands={'primary_stage': 2, 'hazard_stage': 0, 'overall_stage': 1},
            flags=['flag1'],
            confidence=0.85
        )
        
        d = result.to_dict()
        
        assert d['profile'] == {'test': 'value'}
        assert d['facet_scores'] == {'facet1': 0.5}
        assert d['scores']['primary'] == 0.3
        assert d['bands']['primary_stage'] == 2
        assert d['flags'] == ['flag1']
        assert d['confidence'] == 0.85

    def test_to_dict_serializable(self):
        """to_dict output should be JSON serializable."""
        import json
        
        result = DomainResult(
            profile={'nested': {'data': [1, 2, 3]}},
            scores={'primary': 0.5, 'hazard': 0.3, 'overall': 0.4},
            bands={'primary_stage': 3, 'hazard_stage': 2, 'overall_stage': 2}
        )
        
        # Should not raise
        json_str = json.dumps(result.to_dict())
        parsed = json.loads(json_str)
        
        assert parsed['profile']['nested']['data'] == [1, 2, 3]
