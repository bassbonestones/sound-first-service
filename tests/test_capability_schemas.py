"""
Tests for capability schemas validators.

Tests validation rules for capability creation and update schemas.
"""

import pytest
from pydantic import ValidationError

from app.schemas.capability_schemas import CapabilityCreateRequest


class TestCapabilityCreateValidators:
    """Tests for CapabilityCreateRequest validation."""

    def test_valid_capability_create(self):
        """Valid capability data should pass validation."""
        cap = CapabilityCreateRequest(
            name="test_capability",
            domain="interval",
            requirement_type="required",
            mastery_type="single",
            difficulty_tier=1,
            evidence_acceptance_threshold=4,
            difficulty_weight=1.0,
            evidence_required_count=3,
        )
        assert cap.name == "test_capability"

    def test_name_must_be_snake_case(self):
        """Name must be snake_case."""
        with pytest.raises(ValidationError) as exc:
            CapabilityCreateRequest(
                name="TestCapability",  # CamelCase
                domain="interval",
                requirement_type="required",
                mastery_type="single",
                difficulty_tier=1,
                evidence_acceptance_threshold=4,
                difficulty_weight=1.0,
                evidence_required_count=3,
            )
        assert "snake_case" in str(exc.value).lower()

    def test_name_cannot_start_with_number(self):
        """Name cannot start with a number."""
        with pytest.raises(ValidationError) as exc:
            CapabilityCreateRequest(
                name="123_capability",
                domain="interval",
                requirement_type="required",
                mastery_type="single",
                difficulty_tier=1,
                evidence_acceptance_threshold=4,
                difficulty_weight=1.0,
                evidence_required_count=3,
            )
        assert "snake_case" in str(exc.value).lower()

    def test_requirement_type_must_be_valid(self):
        """Requirement type must be one of the allowed values."""
        with pytest.raises(ValidationError) as exc:
            CapabilityCreateRequest(
                name="test_capability",
                domain="interval",
                requirement_type="invalid_type",
                mastery_type="single",
                difficulty_tier=1,
                evidence_acceptance_threshold=4,
                difficulty_weight=1.0,
                evidence_required_count=3,
            )
        assert "requirement_type must be one of" in str(exc.value).lower()

    def test_mastery_type_must_be_valid(self):
        """Mastery type must be one of the allowed values."""
        with pytest.raises(ValidationError) as exc:
            CapabilityCreateRequest(
                name="test_capability",
                domain="interval",
                requirement_type="required",
                mastery_type="invalid_type",
                difficulty_tier=1,
                evidence_acceptance_threshold=4,
                difficulty_weight=1.0,
                evidence_required_count=3,
            )
        assert "mastery_type must be one of" in str(exc.value).lower()

    def test_difficulty_tier_must_be_positive(self):
        """Difficulty tier must be at least 1."""
        with pytest.raises(ValidationError) as exc:
            CapabilityCreateRequest(
                name="test_capability",
                domain="interval",
                requirement_type="required",
                mastery_type="single",
                difficulty_tier=0,  # Invalid
                evidence_acceptance_threshold=4,
                difficulty_weight=1.0,
                evidence_required_count=3,
            )
        assert "at least 1" in str(exc.value).lower()

    def test_evidence_threshold_too_low(self):
        """Evidence threshold must be at least 1."""
        with pytest.raises(ValidationError) as exc:
            CapabilityCreateRequest(
                name="test_capability",
                domain="interval",
                requirement_type="required",
                mastery_type="single",
                difficulty_tier=1,
                evidence_acceptance_threshold=0,  # Too low
                difficulty_weight=1.0,
                evidence_required_count=3,
            )
        assert "between" in str(exc.value).lower()

    def test_evidence_threshold_too_high(self):
        """Evidence threshold must be at most 5."""
        with pytest.raises(ValidationError) as exc:
            CapabilityCreateRequest(
                name="test_capability",
                domain="interval",
                requirement_type="required",
                mastery_type="single",
                difficulty_tier=1,
                evidence_acceptance_threshold=6,  # Too high
                difficulty_weight=1.0,
                evidence_required_count=3,
            )
        assert "between" in str(exc.value).lower()

    def test_difficulty_weight_too_low(self):
        """Difficulty weight must be within bounds."""
        with pytest.raises(ValidationError) as exc:
            CapabilityCreateRequest(
                name="test_capability",
                domain="interval",
                requirement_type="required",
                mastery_type="single",
                difficulty_tier=1,
                evidence_acceptance_threshold=4,
                difficulty_weight=0.05,  # Below minimum (0.1)
                evidence_required_count=3,
            )
        assert "difficulty_weight must be between" in str(exc.value).lower()

    def test_difficulty_weight_too_high(self):
        """Difficulty weight must not exceed maximum."""
        with pytest.raises(ValidationError) as exc:
            CapabilityCreateRequest(
                name="test_capability",
                domain="interval",
                requirement_type="required",
                mastery_type="single",
                difficulty_tier=1,
                evidence_acceptance_threshold=4,
                difficulty_weight=15.0,  # Above maximum (10.0)
                evidence_required_count=3,
            )
        assert "difficulty_weight must be between" in str(exc.value).lower()
