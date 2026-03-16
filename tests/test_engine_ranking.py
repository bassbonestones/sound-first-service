"""
Tests for engine/ranking.py

Tests for candidate scoring and ranking functions.
"""

import pytest
from datetime import datetime, timedelta

from app.engine.config import EngineConfig
from app.engine.models import (
    Bucket,
    CapabilityProgress,
    MaterialCandidate,
    MaterialStatus,
)
from app.engine.ranking import (
    compute_fatigue_penalty,
    compute_progress_value,
    compute_maintenance_value,
    compute_novelty_value,
    compute_difficulty_match_value,
    score_candidate,
)


class TestComputeFatiguePenalty:
    """Tests for compute_fatigue_penalty function."""

    def test_never_attempted(self):
        """Should return 0 for never attempted."""
        penalty = compute_fatigue_penalty(None)
        assert penalty == 0.0

    def test_just_attempted_high_penalty(self):
        """Just attempted should have high fatigue penalty."""
        now = datetime.now()
        penalty = compute_fatigue_penalty(now, now=now)
        # exp(-0/3) = 1.0
        assert penalty == pytest.approx(1.0)

    def test_old_attempt_low_penalty(self):
        """Old attempt should have low fatigue penalty."""
        now = datetime.now()
        last = now - timedelta(days=10)
        penalty = compute_fatigue_penalty(last, now=now)
        
        # exp(-10/3) ≈ 0.036
        assert penalty < 0.1

    def test_custom_tau_days(self):
        """Custom tau should affect decay rate."""
        now = datetime.now()
        last = now - timedelta(days=3)
        config_fast = EngineConfig(fatigue_tau_days=1.0)
        config_slow = EngineConfig(fatigue_tau_days=10.0)
        
        penalty_fast = compute_fatigue_penalty(last, now, config_fast)
        penalty_slow = compute_fatigue_penalty(last, now, config_slow)
        
        # Fast decay = lower penalty after same time
        assert penalty_fast < penalty_slow


class TestComputeProgressValue:
    """Tests for compute_progress_value function."""

    def test_no_capabilities(self):
        """Should return 0 for material with no capabilities."""
        candidate = MaterialCandidate(material_id=1, teaches_capabilities=[])
        progress_dict = {}
        
        result = compute_progress_value(candidate, progress_dict)
        
        assert result == 0.0

    def test_max_progress_ratio(self):
        """Should return max progress ratio from capabilities."""
        candidate = MaterialCandidate(material_id=1, teaches_capabilities=[1, 2, 3])
        progress_dict = {
            1: CapabilityProgress(capability_id=1, evidence_count=1, required_count=4),  # 0.25
            2: CapabilityProgress(capability_id=2, evidence_count=3, required_count=4),  # 0.75
            3: CapabilityProgress(capability_id=3, evidence_count=2, required_count=4),  # 0.5
        }
        
        result = compute_progress_value(candidate, progress_dict)
        
        assert result == 0.75

    def test_ignores_mastered_capabilities(self):
        """Should ignore mastered capabilities."""
        candidate = MaterialCandidate(material_id=1, teaches_capabilities=[1, 2])
        progress_dict = {
            1: CapabilityProgress(
                capability_id=1,
                evidence_count=5,
                required_count=3,
                is_mastered=True
            ),
            2: CapabilityProgress(
                capability_id=2,
                evidence_count=1,
                required_count=4
            ),
        }
        
        result = compute_progress_value(candidate, progress_dict)
        
        # Should be 0.25 from cap 2, not 1.0+ from mastered cap 1
        assert result == 0.25


class TestComputeMaintenanceValue:
    """Tests for compute_maintenance_value function."""

    def test_low_ema_high_maintenance(self):
        """Low EMA should produce high maintenance value."""
        candidate = MaterialCandidate(material_id=1, ema_score=1.0)
        
        result = compute_maintenance_value(candidate)
        
        # 1 - 0 = 1.0
        assert result == 1.0

    def test_high_ema_low_maintenance(self):
        """High EMA should produce low maintenance value."""
        candidate = MaterialCandidate(material_id=1, ema_score=5.0)
        
        result = compute_maintenance_value(candidate)
        
        # 1 - 1 = 0.0
        assert result == 0.0

    def test_middle_ema_middle_maintenance(self):
        """Middle EMA should produce middle maintenance value."""
        candidate = MaterialCandidate(material_id=1, ema_score=3.0)
        
        result = compute_maintenance_value(candidate)
        
        # 1 - 0.5 = 0.5
        assert result == 0.5


class TestComputeNoveltyValue:
    """Tests for compute_novelty_value function."""

    def test_unexplored_is_novel(self):
        """Unexplored material should be novel."""
        candidate = MaterialCandidate(
            material_id=1,
            status=MaterialStatus.UNEXPLORED
        )
        
        assert compute_novelty_value(candidate) == 1.0

    def test_in_progress_not_novel(self):
        """In progress material should not be novel."""
        candidate = MaterialCandidate(
            material_id=1,
            status=MaterialStatus.IN_PROGRESS
        )
        
        assert compute_novelty_value(candidate) == 0.0

    def test_mastered_not_novel(self):
        """Mastered material should not be novel."""
        candidate = MaterialCandidate(
            material_id=1,
            status=MaterialStatus.MASTERED
        )
        
        assert compute_novelty_value(candidate) == 0.0


class TestComputeDifficultyMatchValue:
    """Tests for compute_difficulty_match_value function."""

    def test_perfect_match(self):
        """Should return 1.0 for perfect difficulty match."""
        candidate = MaterialCandidate(material_id=1, overall_score=0.5)
        
        result = compute_difficulty_match_value(candidate, user_maturity=0.5)
        
        assert result == 1.0

    def test_no_match(self):
        """Should return 0.0 for complete mismatch."""
        candidate = MaterialCandidate(material_id=1, overall_score=1.0)
        
        result = compute_difficulty_match_value(candidate, user_maturity=0.0)
        
        assert result == 0.0

    def test_partial_match(self):
        """Should return partial value for partial match."""
        candidate = MaterialCandidate(material_id=1, overall_score=0.7)
        
        result = compute_difficulty_match_value(candidate, user_maturity=0.5)
        
        # Gap = 0.2, match = 1 - 0.2 = 0.8
        assert result == pytest.approx(0.8)

    def test_fallback_to_difficulty_index(self):
        """Should use difficulty_index if overall_score is None."""
        candidate = MaterialCandidate(
            material_id=1,
            difficulty_index=0.6,
            overall_score=None
        )
        
        result = compute_difficulty_match_value(candidate, user_maturity=0.6)
        
        assert result == 1.0


class TestScoreCandidate:
    """Tests for score_candidate function."""

    def test_new_bucket_scoring(self):
        """NEW bucket should weight progress and novelty."""
        candidate = MaterialCandidate(
            material_id=1,
            status=MaterialStatus.UNEXPLORED,
            teaches_capabilities=[1]
        )
        progress_dict = {
            1: CapabilityProgress(capability_id=1, evidence_count=2, required_count=4)
        }
        
        score = score_candidate(
            candidate,
            bucket=Bucket.NEW,
            capability_progress=progress_dict
        )
        
        # progressValue=0.5, noveltyValue=1.0, no fatigue
        # 1.0*0.5 + 0.5*1.0 = 1.0 + unified bonus
        assert score >= 0.9

    def test_in_progress_bucket_scoring(self):
        """IN_PROGRESS bucket should weight progress and maintenance."""
        candidate = MaterialCandidate(
            material_id=1,
            status=MaterialStatus.IN_PROGRESS,
            ema_score=2.0,  # Low EMA = high maintenance value
            teaches_capabilities=[1]
        )
        progress_dict = {
            1: CapabilityProgress(capability_id=1, evidence_count=3, required_count=4)
        }
        
        score = score_candidate(
            candidate,
            bucket=Bucket.IN_PROGRESS,
            capability_progress=progress_dict
        )
        
        # progressValue=0.75, maintenanceValue≈0.75
        # 1.0*0.75 + 0.8*0.75 = 1.35 + unified bonus
        assert score > 1.0

    def test_maintenance_bucket_scoring(self):
        """MAINTENANCE bucket should weight maintenance over progress."""
        candidate = MaterialCandidate(
            material_id=1,
            status=MaterialStatus.MASTERED,
            ema_score=4.0,  # High EMA = low maintenance value
        )
        progress_dict = {}
        
        score = score_candidate(
            candidate,
            bucket=Bucket.MAINTENANCE,
            capability_progress=progress_dict
        )
        
        # maintenanceValue≈0.25, progressValue=0
        # 0.6*0.25 + 0.3*0 = 0.15 + unified bonus
        assert score < 0.5

    def test_fatigue_penalty_applied(self):
        """Should apply fatigue penalty for recent attempts."""
        now = datetime.now()
        candidate_recent = MaterialCandidate(
            material_id=1,
            status=MaterialStatus.IN_PROGRESS,
            teaches_capabilities=[1],
            last_attempt_at=now  # Just attempted
        )
        candidate_old = MaterialCandidate(
            material_id=2,
            status=MaterialStatus.IN_PROGRESS,
            teaches_capabilities=[1],
            last_attempt_at=now - timedelta(days=10)  # Old attempt
        )
        progress_dict = {
            1: CapabilityProgress(capability_id=1, evidence_count=2, required_count=4)
        }
        
        score_recent = score_candidate(
            candidate_recent,
            bucket=Bucket.IN_PROGRESS,
            capability_progress=progress_dict,
            now=now
        )
        score_old = score_candidate(
            candidate_old,
            bucket=Bucket.IN_PROGRESS,
            capability_progress=progress_dict,
            now=now
        )
        
        # Old attempt should score higher (less fatigue)
        assert score_old > score_recent

    def test_unified_scoring_bonus(self):
        """Should add bonus for difficulty match and interaction."""
        candidate = MaterialCandidate(
            material_id=1,
            status=MaterialStatus.UNEXPLORED,
            overall_score=0.5,
            interaction_bonus=0.5
        )
        config = EngineConfig(
            ranking_overall_score_weight=0.3,
            ranking_interaction_bonus_weight=0.2
        )
        
        score = score_candidate(
            candidate,
            bucket=Bucket.NEW,
            capability_progress={},
            config=config,
            user_maturity=0.5  # Perfect match
        )
        
        # Base: 0*1 + 1*0.5 = 0.5
        # Unified: 0.3*1.0 + 0.2*0.5 = 0.4
        # Total ≈ 0.9
        assert score > 0.8
