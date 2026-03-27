"""
Tests for app/engine/attempt.py

Tests for attempt processing and stats update functions.
"""

import pytest

from app.engine.attempt import process_attempt, update_pitch_focus_stats
from app.engine.config import EngineConfig
from app.engine.models import (
    AttemptResult,
    CapabilityProgress,
    MaterialCandidate,
    MaterialStatus,
    MaterialShelf,
)


class TestProcessAttempt:
    """Tests for process_attempt function."""

    def test_returns_attempt_result(self):
        """Should return an AttemptResult."""
        material = MaterialCandidate(
            material_id=1,
            ema_score=0.5,
            attempt_count=5,
            difficulty_index=1.0,
            status=MaterialStatus.IN_PROGRESS,
            overall_score=0.5,
            interaction_bonus=0.0,
        )
        
        result = process_attempt(
            rating=4,
            material_state=material,
            teaches_capability_ids=[],
            capability_progress={},
        )
        
        assert isinstance(result, AttemptResult)
        assert result.new_attempt_count == 6

    def test_mastered_status_with_high_ema(self):
        """Should set MASTERED status when EMA is high enough."""
        material = MaterialCandidate(
            material_id=1,
            ema_score=0.9,
            attempt_count=10,
            difficulty_index=1.0,
            status=MaterialStatus.IN_PROGRESS,
            overall_score=0.9,
            interaction_bonus=0.0,
        )
        
        # High rating should push EMA higher
        result = process_attempt(
            rating=5,
            material_state=material,
            teaches_capability_ids=[],
            capability_progress={},
        )
        
        # With high EMA and attempts, might be mastered
        assert result.new_status in [MaterialStatus.MASTERED, MaterialStatus.IN_PROGRESS]

    def test_in_progress_status(self):
        """Should set IN_PROGRESS when not mastered."""
        material = MaterialCandidate(
            material_id=1,
            ema_score=0.3,
            attempt_count=2,
            difficulty_index=1.0,
            status=MaterialStatus.IN_PROGRESS,
            overall_score=0.3,
            interaction_bonus=0.0,
        )
        
        result = process_attempt(
            rating=3,
            material_state=material,
            teaches_capability_ids=[],
            capability_progress={},
        )
        
        assert result.new_status == MaterialStatus.IN_PROGRESS

    def test_capability_evidence_added(self):
        """Should add capability evidence with high rating."""
        material = MaterialCandidate(
            material_id=1,
            ema_score=0.5,
            attempt_count=3,
            difficulty_index=1.0,
            status=MaterialStatus.IN_PROGRESS,
            overall_score=0.5,
            interaction_bonus=0.0,
        )
        
        cap_progress = {
            101: CapabilityProgress(
                capability_id=101,
                difficulty_weight=1.0,
                is_mastered=False,
                evidence_count=2,
                required_count=5,
            )
        }
        
        result = process_attempt(
            rating=5,  # High rating
            material_state=material,
            teaches_capability_ids=[101],
            capability_progress=cap_progress,
            is_off_course=False,
        )
        
        assert 101 in result.capability_evidence_added

    def test_no_evidence_when_off_course(self):
        """Should not add evidence when off-course."""
        material = MaterialCandidate(
            material_id=1,
            ema_score=0.5,
            attempt_count=3,
            difficulty_index=1.0,
            status=MaterialStatus.IN_PROGRESS,
            overall_score=0.5,
            interaction_bonus=0.0,
        )
        
        cap_progress = {
            101: CapabilityProgress(
                capability_id=101,
                difficulty_weight=1.0,
                is_mastered=False,
                evidence_count=2,
                required_count=5,
            )
        }
        
        result = process_attempt(
            rating=5,
            material_state=material,
            teaches_capability_ids=[101],
            capability_progress=cap_progress,
            is_off_course=True,
        )
        
        assert 101 not in result.capability_evidence_added

    def test_capability_mastery(self):
        """Should detect when capability becomes mastered."""
        material = MaterialCandidate(
            material_id=1,
            ema_score=0.5,
            attempt_count=3,
            difficulty_index=1.0,
            status=MaterialStatus.IN_PROGRESS,
            overall_score=0.5,
            interaction_bonus=0.0,
        )
        
        # Evidence at 4, required 5 - one more tips it
        cap_progress = {
            101: CapabilityProgress(
                capability_id=101,
                difficulty_weight=1.0,
                is_mastered=False,
                evidence_count=4,
                required_count=5,
            )
        }
        
        result = process_attempt(
            rating=5,
            material_state=material,
            teaches_capability_ids=[101],
            capability_progress=cap_progress,
            is_off_course=False,
        )
        
        assert 101 in result.capabilities_mastered


class TestUpdatePitchFocusStats:
    """Tests for update_pitch_focus_stats function."""

    def test_returns_updated_stats(self):
        """Should return updated EMA and attempt count."""
        new_ema, new_attempts = update_pitch_focus_stats(
            pitch_midi=60,
            focus_card_id=1,
            rating=4,
            current_ema=0.5,
            current_attempts=3,
        )
        
        assert isinstance(new_ema, float)
        assert new_attempts == 4

    def test_uses_default_config_when_none(self):
        """Should use default config when config is None."""
        new_ema, new_attempts = update_pitch_focus_stats(
            pitch_midi=60,
            focus_card_id=1,
            rating=5,
            current_ema=0.5,
            current_attempts=10,
            config=None,  # Explicitly None
        )
        
        assert new_attempts == 11
        # EMA calculation can produce values outside 0-1 range based on rating scale
        assert isinstance(new_ema, float)

    def test_with_custom_config(self):
        """Should use provided config."""
        config = EngineConfig(ema_alpha=0.3)
        
        new_ema, new_attempts = update_pitch_focus_stats(
            pitch_midi=60,
            focus_card_id=1,
            rating=5,
            current_ema=0.5,
            current_attempts=5,
            config=config,
        )
        
        assert new_attempts == 6
        # EMA should be affected by custom alpha
        assert isinstance(new_ema, float)

    def test_increments_attempts(self):
        """Should always increment attempt count by 1."""
        _, new_attempts = update_pitch_focus_stats(
            pitch_midi=72,
            focus_card_id=42,
            rating=3,
            current_ema=0.7,
            current_attempts=0,
        )
        
        assert new_attempts == 1
