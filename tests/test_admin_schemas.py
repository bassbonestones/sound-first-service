"""
Tests for admin schemas validators.

Tests validation rules for soft gate and engine configuration schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.admin_schemas import (
    SoftGateRuleUpdate,
    SoftGateRuleCreate,
)


class TestSoftGateRuleValidators:
    """Tests for soft gate rule validation."""

    def test_positive_float_validation_passes(self):
        """Valid positive floats should pass validation."""
        rule = SoftGateRuleUpdate(
            frontier_buffer=0.5,
            promotion_step=0.1,
        )
        assert rule.frontier_buffer == 0.5
        assert rule.promotion_step == 0.1

    def test_positive_float_rejects_zero(self):
        """Zero floats should be rejected."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleUpdate(frontier_buffer=0)
        assert "positive" in str(exc.value).lower()

    def test_positive_float_rejects_negative(self):
        """Negative floats should be rejected."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleUpdate(promotion_step=-0.5)
        assert "positive" in str(exc.value).lower()

    def test_positive_int_validation_passes(self):
        """Valid positive integers should pass validation."""
        rule = SoftGateRuleUpdate(
            min_attempts=3,
            success_required_count=5,
            success_window_count=10,
        )
        assert rule.min_attempts == 3
        assert rule.success_required_count == 5
        assert rule.success_window_count == 10

    def test_positive_int_rejects_zero(self):
        """Zero for min_attempts should be rejected."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleUpdate(min_attempts=0)
        assert "at least 1" in str(exc.value).lower()

    def test_positive_int_rejects_negative(self):
        """Negative integers should be rejected."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleUpdate(success_required_count=-1)
        assert "at least 1" in str(exc.value).lower()

    def test_rating_threshold_in_range(self):
        """Valid threshold (1-5) should pass."""
        rule = SoftGateRuleUpdate(success_rating_threshold=4)
        assert rule.success_rating_threshold == 4

    def test_rating_threshold_rejects_zero(self):
        """Threshold of 0 should be rejected."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleUpdate(success_rating_threshold=0)
        assert "between 1 and 5" in str(exc.value).lower()

    def test_rating_threshold_rejects_above_5(self):
        """Threshold above 5 should be rejected."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleUpdate(success_rating_threshold=6)
        assert "between 1 and 5" in str(exc.value).lower()

    def test_decay_halflife_validation_passes(self):
        """Valid positive halflife should pass."""
        rule = SoftGateRuleUpdate(decay_halflife_days=7.0)
        assert rule.decay_halflife_days == 7.0

    def test_decay_halflife_rejects_zero(self):
        """Zero halflife should be rejected."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleUpdate(decay_halflife_days=0)
        assert "positive" in str(exc.value).lower()

    def test_decay_halflife_rejects_negative(self):
        """Negative halflife should be rejected."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleUpdate(decay_halflife_days=-3.0)
        assert "positive" in str(exc.value).lower()


class TestSoftGateRuleCreate:
    """Tests for SoftGateRuleCreate schema."""

    def test_valid_create_rule(self):
        """Valid create data should pass."""
        rule = SoftGateRuleCreate(
            dimension_name="interval",
            frontier_buffer=0.5,
            promotion_step=0.2,
            min_attempts=3,
            success_required_count=5,
        )
        assert rule.dimension_name == "interval"
        assert rule.frontier_buffer == 0.5

    def test_create_with_defaults(self):
        """Create with optional defaults."""
        rule = SoftGateRuleCreate(
            dimension_name="rhythm",
            frontier_buffer=0.3,
            promotion_step=0.1,
            min_attempts=2,
            success_required_count=3,
        )
        assert rule.success_rating_threshold == 4  # default
        assert rule.success_window_count is None  # default
        assert rule.decay_halflife_days is None  # default

    def test_create_rejects_zero_min_attempts(self):
        """min_attempts must be at least 1."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleCreate(
                dimension_name="test",
                frontier_buffer=0.5,
                promotion_step=0.2,
                min_attempts=0,
                success_required_count=3,
            )
        assert "at least 1" in str(exc.value).lower()

    def test_create_rejects_zero_window_count(self):
        """success_window_count must be at least 1 if provided."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleCreate(
                dimension_name="test",
                frontier_buffer=0.5,
                promotion_step=0.2,
                min_attempts=2,
                success_required_count=3,
                success_window_count=0,
            )
        assert "at least 1" in str(exc.value).lower()

    def test_create_rejects_invalid_rating_threshold(self):
        """success_rating_threshold must be between 1 and 5."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleCreate(
                dimension_name="test",
                frontier_buffer=0.5,
                promotion_step=0.2,
                min_attempts=2,
                success_required_count=3,
                success_rating_threshold=6,
            )
        assert "between 1 and 5" in str(exc.value).lower()

    def test_create_rejects_negative_decay_halflife(self):
        """decay_halflife_days must be positive if provided."""
        with pytest.raises(ValidationError) as exc:
            SoftGateRuleCreate(
                dimension_name="test",
                frontier_buffer=0.5,
                promotion_step=0.2,
                min_attempts=2,
                success_required_count=3,
                decay_halflife_days=-1.0,
            )
        assert "positive" in str(exc.value).lower()
