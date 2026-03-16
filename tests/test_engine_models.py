"""
Tests for engine/models.py

Tests for engine enums and dataclasses.
"""

import pytest
from datetime import datetime

from app.engine.models import (
    MaterialStatus,
    MaterialShelf,
    Bucket,
    MaterialCandidate,
    CapabilityProgress,
    FocusTarget,
    SessionMaterial,
    AttemptResult,
)


class TestMaterialStatus:
    """Tests for MaterialStatus enum."""

    def test_unexplored_value(self):
        """Should have UNEXPLORED status."""
        assert MaterialStatus.UNEXPLORED.value == "unexplored"

    def test_in_progress_value(self):
        """Should have IN_PROGRESS status."""
        assert MaterialStatus.IN_PROGRESS.value == "in_progress"

    def test_mastered_value(self):
        """Should have MASTERED status."""
        assert MaterialStatus.MASTERED.value == "mastered"


class TestMaterialShelf:
    """Tests for MaterialShelf enum."""

    def test_default_shelf(self):
        """Should have DEFAULT shelf."""
        assert MaterialShelf.DEFAULT.value == "default"

    def test_maintenance_shelf(self):
        """Should have MAINTENANCE shelf."""
        assert MaterialShelf.MAINTENANCE.value == "maintenance"

    def test_archive_shelf(self):
        """Should have ARCHIVE shelf."""
        assert MaterialShelf.ARCHIVE.value == "archive"


class TestBucket:
    """Tests for Bucket enum."""

    def test_new_bucket(self):
        """Should have NEW bucket."""
        assert Bucket.NEW.value == "new"

    def test_in_progress_bucket(self):
        """Should have IN_PROGRESS bucket."""
        assert Bucket.IN_PROGRESS.value == "in_progress"

    def test_maintenance_bucket(self):
        """Should have MAINTENANCE bucket."""
        assert Bucket.MAINTENANCE.value == "maintenance"


class TestMaterialCandidate:
    """Tests for MaterialCandidate dataclass."""

    def test_create_minimal_candidate(self):
        """Should create candidate with just material_id."""
        candidate = MaterialCandidate(material_id=42)
        
        assert candidate.material_id == 42
        assert candidate.teaches_capabilities == []
        assert candidate.difficulty_index == 0.0
        assert candidate.ema_score == 3.0  # Default middle of scale
        assert candidate.attempt_count == 0
        assert candidate.status == MaterialStatus.UNEXPLORED
        assert candidate.shelf == MaterialShelf.DEFAULT

    def test_create_full_candidate(self):
        """Should create candidate with all fields."""
        now = datetime.now()
        candidate = MaterialCandidate(
            material_id=100,
            teaches_capabilities=[1, 5, 10],
            difficulty_index=0.7,
            ema_score=4.5,
            attempt_count=8,
            status=MaterialStatus.MASTERED,
            shelf=MaterialShelf.MAINTENANCE,
            last_attempt_at=now,
            overall_score=0.65,
            primary_scores={"rhythm": 0.5, "interval": 0.7},
            hazard_scores={"tempo": 0.3},
            hazard_flags=["complex_rhythm"],
            interaction_bonus=0.1
        )
        
        assert candidate.teaches_capabilities == [1, 5, 10]
        assert candidate.difficulty_index == 0.7
        assert candidate.overall_score == 0.65
        assert candidate.hazard_flags == ["complex_rhythm"]
        assert candidate.interaction_bonus == 0.1


class TestCapabilityProgress:
    """Tests for CapabilityProgress dataclass."""

    def test_create_progress(self):
        """Should create capability progress."""
        progress = CapabilityProgress(
            capability_id=5,
            evidence_count=2,
            required_count=5
        )
        
        assert progress.capability_id == 5
        assert progress.evidence_count == 2
        assert progress.is_mastered is False

    def test_progress_ratio_partial(self):
        """Should compute partial progress ratio."""
        progress = CapabilityProgress(
            capability_id=1,
            evidence_count=2,
            required_count=4
        )
        assert progress.progress_ratio == 0.5

    def test_progress_ratio_complete(self):
        """Should return 1.0 when evidence >= required."""
        progress = CapabilityProgress(
            capability_id=1,
            evidence_count=5,
            required_count=3
        )
        # Capped at 1.0
        assert progress.progress_ratio == 1.0

    def test_progress_ratio_zero_required(self):
        """Should handle zero required count."""
        progress = CapabilityProgress(
            capability_id=1,
            evidence_count=0,
            required_count=0
        )
        assert progress.progress_ratio == 1.0


class TestFocusTarget:
    """Tests for FocusTarget dataclass."""

    def test_create_focus_target(self):
        """Should create focus target."""
        target = FocusTarget(
            pitch_midi=60,
            focus_card_id=3,
            ema_score=3.5,
            score=0.75
        )
        
        assert target.pitch_midi == 60
        assert target.focus_card_id == 3
        assert target.ema_score == 3.5
        assert target.score == 0.75

    def test_defaults(self):
        """Should have default scores."""
        target = FocusTarget(pitch_midi=72, focus_card_id=1)
        assert target.ema_score == 0.0
        assert target.score == 0.0


class TestSessionMaterial:
    """Tests for SessionMaterial dataclass."""

    def test_create_session_material(self):
        """Should create session material."""
        material = SessionMaterial(
            material_id=42,
            bucket=Bucket.IN_PROGRESS
        )
        
        assert material.material_id == 42
        assert material.bucket == Bucket.IN_PROGRESS
        assert material.focus_targets == []
        assert material.hazard_warnings == []

    def test_with_focus_targets(self):
        """Should include focus targets."""
        target = FocusTarget(pitch_midi=60, focus_card_id=1)
        material = SessionMaterial(
            material_id=42,
            bucket=Bucket.NEW,
            focus_targets=[target],
            hazard_warnings=["complex_rhythm"]
        )
        
        assert len(material.focus_targets) == 1
        assert material.hazard_warnings == ["complex_rhythm"]


class TestAttemptResult:
    """Tests for AttemptResult dataclass."""

    def test_create_attempt_result(self):
        """Should create attempt result."""
        result = AttemptResult(
            new_ema=4.2,
            new_attempt_count=6,
            new_status=MaterialStatus.IN_PROGRESS
        )
        
        assert result.new_ema == 4.2
        assert result.new_attempt_count == 6
        assert result.new_status == MaterialStatus.IN_PROGRESS
        assert result.capability_evidence_added == []
        assert result.capabilities_mastered == []

    def test_with_capability_changes(self):
        """Should include capability changes."""
        result = AttemptResult(
            new_ema=4.5,
            new_attempt_count=8,
            new_status=MaterialStatus.MASTERED,
            capability_evidence_added=[1, 2, 3],
            capabilities_mastered=[1]
        )
        
        assert result.capability_evidence_added == [1, 2, 3]
        assert result.capabilities_mastered == [1]
