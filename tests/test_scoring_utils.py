"""
Tests for scoring/utils.py

Tests for normalization and stage derivation utilities.
"""

import pytest

from app.scoring.utils import (
    clamp,
    normalize_linear,
    normalize_sigmoid,
    score_to_stage,
    derive_bands,
    STAGE_THRESHOLDS,
)
from app.scoring.models import DomainScores


class TestClamp:
    """Tests for clamp function."""

    def test_value_in_range(self):
        """Should return value if in range."""
        assert clamp(0.5) == 0.5

    def test_value_below_min(self):
        """Should clamp to min if below."""
        assert clamp(-0.5) == 0.0

    def test_value_above_max(self):
        """Should clamp to max if above."""
        assert clamp(1.5) == 1.0

    def test_at_boundaries(self):
        """Should work at exact boundaries."""
        assert clamp(0.0) == 0.0
        assert clamp(1.0) == 1.0

    def test_custom_range(self):
        """Should support custom min/max."""
        assert clamp(5.0, min_val=0.0, max_val=10.0) == 5.0
        assert clamp(-5.0, min_val=0.0, max_val=10.0) == 0.0
        assert clamp(15.0, min_val=0.0, max_val=10.0) == 10.0


class TestNormalizeLinear:
    """Tests for normalize_linear function."""

    def test_at_low_boundary(self):
        """Should return 0 at low boundary."""
        result = normalize_linear(0.0, low=0.0, high=10.0)
        assert result == 0.0

    def test_at_high_boundary(self):
        """Should return 1 at high boundary."""
        result = normalize_linear(10.0, low=0.0, high=10.0)
        assert result == 1.0

    def test_midpoint(self):
        """Should return 0.5 at midpoint."""
        result = normalize_linear(5.0, low=0.0, high=10.0)
        assert result == 0.5

    def test_below_low(self):
        """Should clamp to 0 below low."""
        result = normalize_linear(-5.0, low=0.0, high=10.0)
        assert result == 0.0

    def test_above_high(self):
        """Should clamp to 1 above high."""
        result = normalize_linear(15.0, low=0.0, high=10.0)
        assert result == 1.0

    def test_negative_range(self):
        """Should work with negative range."""
        result = normalize_linear(0.0, low=-10.0, high=10.0)
        assert result == 0.5

    def test_invalid_range(self):
        """Should return 0 when high <= low."""
        assert normalize_linear(5.0, low=10.0, high=10.0) == 0.0
        assert normalize_linear(5.0, low=10.0, high=5.0) == 0.0


class TestNormalizeSigmoid:
    """Tests for normalize_sigmoid function."""

    def test_at_midpoint(self):
        """Should return 0.5 at midpoint."""
        result = normalize_sigmoid(5.0, midpoint=5.0)
        assert result == pytest.approx(0.5)

    def test_below_midpoint(self):
        """Should return < 0.5 below midpoint."""
        result = normalize_sigmoid(3.0, midpoint=5.0)
        assert result < 0.5

    def test_above_midpoint(self):
        """Should return > 0.5 above midpoint."""
        result = normalize_sigmoid(7.0, midpoint=5.0)
        assert result > 0.5

    def test_steepness_affects_slope(self):
        """Higher steepness should increase slope."""
        low_steep = normalize_sigmoid(6.0, midpoint=5.0, steepness=0.5)
        high_steep = normalize_sigmoid(6.0, midpoint=5.0, steepness=2.0)
        
        # Both above 0.5, but high steepness more extreme
        assert low_steep > 0.5
        assert high_steep > low_steep

    def test_sigmoid_bounds(self):
        """Sigmoid should approach 0 and 1 at extremes."""
        low = normalize_sigmoid(-10.0, midpoint=0.0)
        high = normalize_sigmoid(10.0, midpoint=0.0)
        
        assert low < 0.01
        assert high > 0.99


class TestScoreToStage:
    """Tests for score_to_stage function."""

    def test_stage_0(self):
        """Score < 0.15 should be stage 0."""
        assert score_to_stage(0.0) == 0
        assert score_to_stage(0.10) == 0
        assert score_to_stage(0.14) == 0

    def test_stage_1(self):
        """Score 0.15-0.29 should be stage 1."""
        assert score_to_stage(0.15) == 1
        assert score_to_stage(0.20) == 1
        assert score_to_stage(0.29) == 1

    def test_stage_2(self):
        """Score 0.30-0.44 should be stage 2."""
        assert score_to_stage(0.30) == 2
        assert score_to_stage(0.35) == 2
        assert score_to_stage(0.44) == 2

    def test_stage_3(self):
        """Score 0.45-0.59 should be stage 3."""
        assert score_to_stage(0.45) == 3
        assert score_to_stage(0.50) == 3
        assert score_to_stage(0.59) == 3

    def test_stage_4(self):
        """Score 0.60-0.74 should be stage 4."""
        assert score_to_stage(0.60) == 4
        assert score_to_stage(0.70) == 4
        assert score_to_stage(0.74) == 4

    def test_stage_5(self):
        """Score 0.75-0.89 should be stage 5."""
        assert score_to_stage(0.75) == 5
        assert score_to_stage(0.80) == 5
        assert score_to_stage(0.89) == 5

    def test_stage_6(self):
        """Score >= 0.90 should be stage 6."""
        assert score_to_stage(0.90) == 6
        assert score_to_stage(0.95) == 6
        assert score_to_stage(1.0) == 6

    def test_clamped_input(self):
        """Should clamp scores outside 0-1."""
        assert score_to_stage(-0.5) == 0
        assert score_to_stage(1.5) == 6

    def test_thresholds_count(self):
        """Should have 6 thresholds for 7 stages."""
        assert len(STAGE_THRESHOLDS) == 6


class TestDeriveBands:
    """Tests for derive_bands function."""

    def test_all_zero_scores(self):
        """Should return stage 0 for all zero scores."""
        scores: DomainScores = {'primary': 0.0, 'hazard': 0.0, 'overall': 0.0}
        bands = derive_bands(scores)
        
        assert bands['primary_stage'] == 0
        assert bands['hazard_stage'] == 0
        assert bands['overall_stage'] == 0

    def test_mixed_scores(self):
        """Should derive correct stages for mixed scores."""
        scores: DomainScores = {'primary': 0.50, 'hazard': 0.25, 'overall': 0.70}
        bands = derive_bands(scores)
        
        assert bands['primary_stage'] == 3  # 0.45-0.59
        assert bands['hazard_stage'] == 1   # 0.15-0.29
        assert bands['overall_stage'] == 4  # 0.60-0.74

    def test_max_scores(self):
        """Should return stage 6 for max scores."""
        scores: DomainScores = {'primary': 1.0, 'hazard': 1.0, 'overall': 1.0}
        bands = derive_bands(scores)
        
        assert bands['primary_stage'] == 6
        assert bands['hazard_stage'] == 6
        assert bands['overall_stage'] == 6
