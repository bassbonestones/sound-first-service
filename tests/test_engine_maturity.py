"""
Tests for engine/maturity.py

Tests for maturity calculation and bucket weight functions.
"""

import pytest
import random

from app.engine.config import EngineConfig
from app.engine.maturity import (
    compute_material_maturity,
    compute_capability_maturity,
    compute_combined_maturity,
    compute_bucket_weights,
    sample_bucket,
)
from app.engine.models import Bucket


class TestComputeMaterialMaturity:
    """Tests for compute_material_maturity function."""

    def test_no_difficulty_sum(self):
        """Should return 0 when total difficulty is 0."""
        result = compute_material_maturity(5.0, 0.0)
        assert result == 0.0

    def test_all_mastered(self):
        """Should return 1.0 when all mastered."""
        result = compute_material_maturity(10.0, 10.0)
        assert result == 1.0

    def test_half_mastered(self):
        """Should return ratio for partial mastery."""
        result = compute_material_maturity(5.0, 10.0)
        assert result == 0.5

    def test_small_fraction_mastered(self):
        """Should compute small fractions correctly."""
        result = compute_material_maturity(1.0, 100.0)
        assert result == 0.01


class TestComputeCapabilityMaturity:
    """Tests for compute_capability_maturity function."""

    def test_no_weight_sum(self):
        """Should return 0 when total weight is 0."""
        result = compute_capability_maturity(5.0, 0.0)
        assert result == 0.0

    def test_all_mastered(self):
        """Should return 1.0 when all mastered."""
        result = compute_capability_maturity(20.0, 20.0)
        assert result == 1.0

    def test_partial_mastery(self):
        """Should return ratio for partial mastery."""
        result = compute_capability_maturity(3.0, 12.0)
        assert result == 0.25


class TestComputeCombinedMaturity:
    """Tests for compute_combined_maturity function."""

    def test_default_weights(self):
        """Should use default weights 0.6 cap + 0.4 mat."""
        result = compute_combined_maturity(1.0, 0.5)
        # 0.6 * 1.0 + 0.4 * 0.5 = 0.6 + 0.2 = 0.8
        assert result == pytest.approx(0.8)

    def test_custom_weights(self):
        """Should use custom weights from config."""
        config = EngineConfig(maturity_cap_weight=0.5, maturity_mat_weight=0.5)
        result = compute_combined_maturity(1.0, 0.0, config=config)
        # 0.5 * 1.0 + 0.5 * 0.0 = 0.5
        assert result == pytest.approx(0.5)

    def test_clamped_to_zero(self):
        """Should not go below 0."""
        # Note: Normal inputs won't go below 0, but just in case
        result = compute_combined_maturity(0.0, 0.0)
        assert result >= 0.0

    def test_clamped_to_one(self):
        """Should not exceed 1."""
        result = compute_combined_maturity(1.0, 1.0)
        assert result <= 1.0


class TestComputeBucketWeights:
    """Tests for compute_bucket_weights function."""

    def test_early_learner_more_in_progress(self):
        """Early learner (low maturity) should have high IN_PROGRESS weight."""
        weights = compute_bucket_weights(0.0)
        
        assert weights[Bucket.IN_PROGRESS] > weights[Bucket.MAINTENANCE]

    def test_advanced_learner_more_maintenance(self):
        """Advanced learner (high maturity) should have higher MAINTENANCE."""
        weights = compute_bucket_weights(1.0)
        
        assert weights[Bucket.MAINTENANCE] > 0.3

    def test_weights_sum_to_one(self):
        """Bucket weights should always sum to 1.0."""
        for maturity in [0.0, 0.25, 0.5, 0.75, 1.0]:
            weights = compute_bucket_weights(maturity)
            total = sum(weights.values())
            assert total == pytest.approx(1.0)

    def test_minimum_weights_applied(self):
        """Should enforce minimum bucket weights."""
        config = EngineConfig(
            min_bucket_new=0.15,
            min_bucket_in_progress=0.25,
            min_bucket_maintenance=0.10
        )
        
        weights = compute_bucket_weights(1.0, config=config)
        
        assert weights[Bucket.NEW] >= 0.15
        assert weights[Bucket.IN_PROGRESS] >= 0.25
        assert weights[Bucket.MAINTENANCE] >= 0.10

    def test_all_buckets_have_weights(self):
        """Should return weights for all three buckets."""
        weights = compute_bucket_weights(0.5)
        
        assert Bucket.NEW in weights
        assert Bucket.IN_PROGRESS in weights
        assert Bucket.MAINTENANCE in weights


class TestSampleBucket:
    """Tests for sample_bucket function."""

    def test_deterministic_when_weight_is_one(self):
        """Should always return bucket with weight 1.0."""
        weights = {
            Bucket.NEW: 0.0,
            Bucket.IN_PROGRESS: 1.0,
            Bucket.MAINTENANCE: 0.0,
        }
        
        # Sample multiple times
        for _ in range(10):
            result = sample_bucket(weights)
            assert result == Bucket.IN_PROGRESS

    def test_respects_weights_statistically(self):
        """Should sample according to weights (statistical test)."""
        random.seed(42)
        weights = {
            Bucket.NEW: 0.2,
            Bucket.IN_PROGRESS: 0.5,
            Bucket.MAINTENANCE: 0.3,
        }
        
        counts = {Bucket.NEW: 0, Bucket.IN_PROGRESS: 0, Bucket.MAINTENANCE: 0}
        samples = 1000
        
        for _ in range(samples):
            bucket = sample_bucket(weights)
            counts[bucket] = counts.get(bucket, 0) + 1
        
        # Check ratios are approximately correct (within 10%)
        assert counts[Bucket.IN_PROGRESS] / samples > 0.4
        assert counts[Bucket.IN_PROGRESS] / samples < 0.6
    
    def test_fallback_when_weights_less_than_one(self):
        """Should return IN_PROGRESS fallback when random exceeds total weights."""
        from unittest.mock import patch
        
        # Weights that sum to less than 1 (0.9 total)
        weights = {
            Bucket.NEW: 0.3,
            Bucket.IN_PROGRESS: 0.3,
            Bucket.MAINTENANCE: 0.3,
        }
        
        # Mock random to return 0.95 (greater than 0.9 total)
        with patch('random.random', return_value=0.95):
            result = sample_bucket(weights)
            assert result == Bucket.IN_PROGRESS  # Fallback
