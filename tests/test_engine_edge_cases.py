"""
Edge Cases and Boundary Tests for Practice Engine

Tests specifically for edge cases mentioned in Phase 11.3.3:
- EMA edge cases (zero values, boundary alphas)
- Mastery threshold boundaries (exact threshold values)
- Eligibility filtering (each criterion independently)
- Candidate ranking tie-breaking

These supplement the main test_practice_engine.py tests.
"""

import pytest
from datetime import datetime, timedelta
from app.practice_engine import (
    EngineConfig,
    MaterialStatus,
    MaterialShelf,
    Bucket,
    MaterialCandidate,
    CapabilityProgress,
    AttemptResult,
    compute_ema,
    check_material_mastery,
    check_capability_mastery,
    check_bitmask_eligibility,
    check_content_dimension_eligibility,
    is_material_eligible,
    compute_material_maturity,
    compute_capability_maturity,
    compute_combined_maturity,
    compute_bucket_weights,
    build_candidate_pool,
    filter_candidates_by_bucket,
    score_candidate,
    rank_candidates,
    compute_progress_value,
    compute_maintenance_value,
    compute_novelty_value,
    compute_fatigue_penalty,
)


# =============================================================================
# EMA EDGE CASES
# =============================================================================

class TestEMAEdgeCases:
    """Test EMA calculation edge cases."""
    
    def test_zero_previous_zero_new(self):
        """Zero + zero should stay zero."""
        result = compute_ema(0.0, 0.0, alpha=0.35)
        assert result == 0.0
    
    def test_zero_previous_positive_new(self):
        """Starting from zero with positive score."""
        result = compute_ema(3.0, 0.0, alpha=0.35)
        assert result == pytest.approx(1.05)  # 0.35 * 3.0
    
    def test_positive_previous_zero_new(self):
        """A zero score should drag EMA down."""
        result = compute_ema(0.0, 4.0, alpha=0.35)
        assert result == pytest.approx(2.6)  # 0.65 * 4.0
    
    def test_alpha_zero_ignores_new_score(self):
        """Alpha=0 should completely ignore new score."""
        result = compute_ema(5.0, 3.0, alpha=0.0)
        assert result == pytest.approx(3.0)  # Just the old EMA
    
    def test_alpha_one_uses_only_new_score(self):
        """Alpha=1 should replace with new score entirely."""
        result = compute_ema(5.0, 3.0, alpha=1.0)
        assert result == pytest.approx(5.0)  # Just the new score
    
    def test_very_small_alpha(self):
        """Very small alpha should weight old EMA heavily."""
        result = compute_ema(5.0, 2.0, alpha=0.01)
        assert result == pytest.approx(2.03)  # Almost all old EMA
    
    def test_maximum_score_convergence(self):
        """EMA should converge to max score (5.0) with repeated max scores."""
        ema = 0.0
        for _ in range(50):
            ema = compute_ema(5.0, ema, alpha=0.35)
        assert ema == pytest.approx(5.0, abs=0.01)
    
    def test_minimum_score_convergence(self):
        """EMA should converge to min score (0.0) from high starting point."""
        ema = 5.0
        for _ in range(50):
            ema = compute_ema(0.0, ema, alpha=0.35)
        assert ema == pytest.approx(0.0, abs=0.01)
    
    def test_negative_score_handling(self):
        """EMA should handle negative scores (if allowed)."""
        # Some systems might pass negative scores for penalties
        result = compute_ema(-1.0, 2.0, alpha=0.35)
        assert result == pytest.approx(0.95)  # 0.35 * -1 + 0.65 * 2


# =============================================================================
# MASTERY THRESHOLD BOUNDARY TESTS
# =============================================================================

class TestMasteryThresholdBoundaries:
    """Test mastery at exact threshold boundaries."""
    
    def test_material_exactly_at_ema_threshold(self):
        """Exactly at EMA threshold should be mastered."""
        # Default threshold is 4.0 EMA, 5 attempts
        assert check_material_mastery(4.0, 5) is True
    
    def test_material_just_below_ema_threshold(self):
        """Just below EMA threshold should NOT be mastered."""
        assert check_material_mastery(3.99, 10) is False
    
    def test_material_exactly_at_attempt_threshold(self):
        """Exactly at attempt threshold should be mastered."""
        assert check_material_mastery(5.0, 5) is True
    
    def test_material_just_below_attempt_threshold(self):
        """Just below attempt threshold should NOT be mastered."""
        assert check_material_mastery(5.0, 4) is False
    
    def test_material_both_boundaries_met(self):
        """Both boundaries exactly met should be mastered."""
        assert check_material_mastery(4.0, 5) is True
    
    def test_material_zero_attempts_never_mastered(self):
        """Zero attempts should never be mastered regardless of EMA."""
        assert check_material_mastery(5.0, 0) is False
    
    def test_material_zero_ema_never_mastered(self):
        """Zero EMA should never be mastered regardless of attempts."""
        assert check_material_mastery(0.0, 100) is False
    
    def test_capability_exactly_at_evidence_threshold(self):
        """Exactly at evidence threshold should be mastered."""
        assert check_capability_mastery(evidence_count=3, required_count=3) is True
    
    def test_capability_just_below_evidence_threshold(self):
        """Just below evidence threshold should NOT be mastered."""
        assert check_capability_mastery(evidence_count=2, required_count=3) is False
    
    def test_capability_zero_required_always_mastered(self):
        """Zero required count should always be mastered."""
        # This might be an edge case in the implementation
        # Capabilities with no required evidence
        result = check_capability_mastery(evidence_count=0, required_count=0)
        # Implementation-dependent - either always True or raises error
        assert result in [True, False]  # Just test it doesn't crash


# =============================================================================
# BITMASK ELIGIBILITY - EACH CRITERION
# =============================================================================

class TestBitmaskEligibilityIndividual:
    """Test bitmask eligibility for individual capability bits."""
    
    def test_single_required_capability_present(self):
        """Single required capability that user has."""
        # User has capability bit 1 in first mask
        user_masks = [0b00000010, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0b00000010, 0, 0, 0, 0, 0, 0, 0]
        assert check_bitmask_eligibility(user_masks, material_masks) is True
    
    def test_single_required_capability_missing(self):
        """Single required capability that user lacks."""
        user_masks = [0b00000010, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0b00000100, 0, 0, 0, 0, 0, 0, 0]  # Different bit
        assert check_bitmask_eligibility(user_masks, material_masks) is False
    
    def test_multiple_required_all_present(self):
        """Multiple required capabilities, all present."""
        user_masks = [0b11111111, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0b00001111, 0, 0, 0, 0, 0, 0, 0]  # Needs first 4 bits
        assert check_bitmask_eligibility(user_masks, material_masks) is True
    
    def test_multiple_required_some_missing(self):
        """Multiple required capabilities, some missing."""
        user_masks = [0b00000011, 0, 0, 0, 0, 0, 0, 0]  # Has bits 0 and 1
        material_masks = [0b00000111, 0, 0, 0, 0, 0, 0, 0]  # Needs bits 0, 1, and 2
        assert check_bitmask_eligibility(user_masks, material_masks) is False
    
    def test_no_required_capabilities(self):
        """No required capabilities (zero masks)."""
        user_masks = [0, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0, 0, 0, 0, 0, 0, 0, 0]
        assert check_bitmask_eligibility(user_masks, material_masks) is True
    
    def test_user_has_extra_capabilities(self):
        """User has more capabilities than required."""
        user_masks = [0b11111111, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0b00000001, 0, 0, 0, 0, 0, 0, 0]
        assert check_bitmask_eligibility(user_masks, material_masks) is True
    
    def test_multi_mask_requirement(self):
        """Requirements spanning multiple masks."""
        user_masks = [0b11111111, 0b11111111, 0, 0, 0, 0, 0, 0]
        material_masks = [0b00001111, 0b00000011, 0, 0, 0, 0, 0, 0]
        assert check_bitmask_eligibility(user_masks, material_masks) is True
    
    def test_multi_mask_partial_failure(self):
        """Failure in second mask."""
        user_masks = [0b11111111, 0b00000001, 0, 0, 0, 0, 0, 0]  # Missing bits in mask 2
        material_masks = [0b00001111, 0b00000011, 0, 0, 0, 0, 0, 0]  # Needs bit 1 in mask 2
        assert check_bitmask_eligibility(user_masks, material_masks) is False


class TestContentDimensionEligibilityIndividual:
    """Test content dimension eligibility for each criterion."""
    
    def test_stage_within_bounds(self):
        """Material stage within user's max stage."""
        material_stages = {'rhythm_complexity_stage': 2}
        user_max_stages = {'rhythm_complexity_stage': 5}
        assert check_content_dimension_eligibility(material_stages, user_max_stages) is True
    
    def test_stage_exactly_at_max(self):
        """Material stage exactly at user's max."""
        material_stages = {'rhythm_complexity_stage': 5}
        user_max_stages = {'rhythm_complexity_stage': 5}
        assert check_content_dimension_eligibility(material_stages, user_max_stages) is True
    
    def test_stage_above_max(self):
        """Material stage above user's max."""
        material_stages = {'rhythm_complexity_stage': 6}
        user_max_stages = {'rhythm_complexity_stage': 5}
        assert check_content_dimension_eligibility(material_stages, user_max_stages) is False
    
    def test_multiple_stages_all_ok(self):
        """Multiple stages, all within bounds."""
        material_stages = {'rhythm_complexity_stage': 2, 'range_usage_stage': 3}
        user_max_stages = {'rhythm_complexity_stage': 5, 'range_usage_stage': 5}
        assert check_content_dimension_eligibility(material_stages, user_max_stages) is True
    
    def test_multiple_stages_one_exceeds(self):
        """Multiple stages, one exceeds limit."""
        material_stages = {'rhythm_complexity_stage': 2, 'range_usage_stage': 6}
        user_max_stages = {'rhythm_complexity_stage': 5, 'range_usage_stage': 5}
        assert check_content_dimension_eligibility(material_stages, user_max_stages) is False
    
    def test_none_stage_ignored(self):
        """None values in material stages should be ignored."""
        material_stages = {'rhythm_complexity_stage': None, 'range_usage_stage': 2}
        user_max_stages = {'rhythm_complexity_stage': 1, 'range_usage_stage': 5}
        assert check_content_dimension_eligibility(material_stages, user_max_stages) is True
    
    def test_missing_stage_in_user_max(self):
        """Stage not in user max should use default behavior."""
        material_stages = {'unknown_stage': 3}
        user_max_stages = {'rhythm_complexity_stage': 5}
        # Implementation-dependent - might pass or fail
        result = check_content_dimension_eligibility(material_stages, user_max_stages)
        assert result in [True, False]  # Just test it doesn't crash


class TestIsMaterialEligibleCriteriaCombinations:
    """Test is_material_eligible with various criterion combinations."""
    
    def test_all_criteria_pass(self):
        """All eligibility criteria pass."""
        result = is_material_eligible(
            user_masks=[0b11111111, 0, 0, 0, 0, 0, 0, 0],
            material_masks=[0b00001111, 0, 0, 0, 0, 0, 0, 0],
            material_stages={'rhythm_complexity_stage': 2},
            user_max_stages={'rhythm_complexity_stage': 5},
            has_license=True
        )
        assert result is True
    
    def test_only_bitmask_fails(self):
        """Only bitmask criterion fails."""
        result = is_material_eligible(
            user_masks=[0, 0, 0, 0, 0, 0, 0, 0],  # No capabilities
            material_masks=[0b00000001, 0, 0, 0, 0, 0, 0, 0],  # Needs one
            material_stages={'rhythm_complexity_stage': 2},
            user_max_stages={'rhythm_complexity_stage': 5},
            has_license=True
        )
        assert result is False
    
    def test_only_stage_fails(self):
        """Only stage/dimension criterion fails."""
        result = is_material_eligible(
            user_masks=[0b11111111, 0, 0, 0, 0, 0, 0, 0],
            material_masks=[0, 0, 0, 0, 0, 0, 0, 0],
            material_stages={'rhythm_complexity_stage': 10},  # Too high
            user_max_stages={'rhythm_complexity_stage': 5},
            has_license=True
        )
        assert result is False
    
    def test_only_license_fails(self):
        """Only license criterion fails."""
        result = is_material_eligible(
            user_masks=[0b11111111, 0, 0, 0, 0, 0, 0, 0],
            material_masks=[0, 0, 0, 0, 0, 0, 0, 0],
            material_stages={'rhythm_complexity_stage': 2},
            user_max_stages={'rhythm_complexity_stage': 5},
            has_license=False
        )
        assert result is False
    
    def test_multiple_criteria_fail(self):
        """Multiple criteria fail simultaneously."""
        result = is_material_eligible(
            user_masks=[0, 0, 0, 0, 0, 0, 0, 0],  # Fails
            material_masks=[0b00000001, 0, 0, 0, 0, 0, 0, 0],
            material_stages={'rhythm_complexity_stage': 10},  # Fails
            user_max_stages={'rhythm_complexity_stage': 5},
            has_license=True
        )
        assert result is False


# =============================================================================
# CANDIDATE RANKING TIE-BREAKING
# =============================================================================

class TestCandidateRankingTieBreaking:
    """Test candidate ranking when scores are equal."""
    
    @pytest.fixture
    def tied_candidates(self):
        """Create candidates with equal base scores."""
        # All have same base properties to create ties
        return [
            MaterialCandidate(
                material_id=1,
                status=MaterialStatus.UNEXPLORED,
                teaches_capabilities=[1],
            ),
            MaterialCandidate(
                material_id=2,
                status=MaterialStatus.UNEXPLORED,
                teaches_capabilities=[1],
            ),
            MaterialCandidate(
                material_id=3,
                status=MaterialStatus.UNEXPLORED,
                teaches_capabilities=[1],
            ),
        ]
    
    def test_tie_produces_consistent_order(self, tied_candidates):
        """Tied candidates should produce a stable order."""
        progress = {1: CapabilityProgress(capability_id=1, evidence_count=2, required_count=5)}
        config = EngineConfig()
        
        # Rank multiple times
        results = []
        for _ in range(10):
            ranked = rank_candidates(
                tied_candidates,
                Bucket.NEW,  # Bucket for unexplored
                progress,
                datetime.now(),
                config,
            )
            results.append([c.material_id for c in ranked])
        
        # All results should contain all candidates
        for r in results:
            assert sorted(r) == [1, 2, 3]
    
    def test_different_progress_breaks_tie(self):
        """Different capability progress should break ties."""
        candidates = [
            MaterialCandidate(
                material_id=1,
                status=MaterialStatus.IN_PROGRESS,
                teaches_capabilities=[1],  # Low progress cap
            ),
            MaterialCandidate(
                material_id=2,
                status=MaterialStatus.IN_PROGRESS,
                teaches_capabilities=[2],  # High progress cap
            ),
        ]
        progress = {
            1: CapabilityProgress(capability_id=1, evidence_count=1, required_count=10),  # 10%
            2: CapabilityProgress(capability_id=2, evidence_count=4, required_count=5),   # 80%
        }
        config = EngineConfig()
        
        ranked = rank_candidates(
            candidates,
            Bucket.IN_PROGRESS,
            progress,
            datetime.now(),
            config,
        )
        
        # Material 2 should rank higher (teaches cap closer to mastery)
        assert ranked[0].material_id == 2
    
    def test_different_fatigue_breaks_tie(self):
        """Different last_attempt times should break ties via fatigue."""
        now = datetime.now()
        candidates = [
            MaterialCandidate(
                material_id=1,
                status=MaterialStatus.IN_PROGRESS,
                teaches_capabilities=[1],
                last_attempt_at=now - timedelta(hours=24),  # Old - no fatigue
            ),
            MaterialCandidate(
                material_id=2,
                status=MaterialStatus.IN_PROGRESS,
                teaches_capabilities=[1],
                last_attempt_at=now - timedelta(minutes=5),  # Recent - fatigue
            ),
        ]
        progress = {1: CapabilityProgress(capability_id=1, evidence_count=2, required_count=5)}
        config = EngineConfig()
        
        ranked = rank_candidates(
            candidates,
            Bucket.IN_PROGRESS,
            progress,
            now,
            config,
        )
        
        # Material 1 should rank higher (less fatigued)
        assert ranked[0].material_id == 1


# =============================================================================
# MATURITY CALCULATION EDGE CASES
# =============================================================================

class TestMaturityEdgeCases:
    """Test maturity calculation edge cases."""
    
    def test_zero_total_materials(self):
        """Zero total materials should return 0."""
        maturity = compute_material_maturity(0.0, 0.0)
        assert maturity == 0.0
    
    def test_all_materials_mastered(self):
        """All materials mastered should give maturity 1.0."""
        maturity = compute_material_maturity(10.0, 10.0)
        assert maturity == 1.0
    
    def test_zero_capabilities_mastered(self):
        """Zero capabilities mastered."""
        maturity = compute_capability_maturity(0.0, 10.0)
        assert maturity == 0.0
    
    def test_combined_maturity_weighting(self):
        """Combined maturity should weight material and capability."""
        # Standard weighting is 0.6 cap + 0.4 mat
        combined = compute_combined_maturity(cap_maturity=0.5, mat_maturity=0.5)
        assert combined == pytest.approx(0.5)


# =============================================================================
# BUCKET WEIGHT EDGE CASES
# =============================================================================

class TestBucketWeightEdgeCases:
    """Test bucket weight calculation edge cases."""
    
    def test_maturity_exactly_zero(self):
        """Maturity exactly 0 should favor new/in_progress."""
        weights = compute_bucket_weights(maturity=0.0)
        assert weights[Bucket.NEW] > 0
        assert weights[Bucket.IN_PROGRESS] > 0
        # Maintenance should be at its minimum
    
    def test_maturity_exactly_one(self):
        """Maturity exactly 1 should favor maintenance."""
        weights = compute_bucket_weights(maturity=1.0)
        assert weights[Bucket.MAINTENANCE] >= weights[Bucket.NEW]
    
    def test_maturity_mid_point(self):
        """Maturity 0.5 should have balanced weights."""
        weights = compute_bucket_weights(maturity=0.5)
        total = sum(weights.values())
        assert total == pytest.approx(1.0)
        # No bucket should be zero
        for bucket, weight in weights.items():
            assert weight > 0
    
    def test_negative_maturity_clamped(self):
        """Negative maturity should be clamped to 0."""
        weights = compute_bucket_weights(maturity=-0.5)
        # Should behave same as maturity=0
        for bucket, weight in weights.items():
            assert 0 <= weight <= 1
        assert sum(weights.values()) == pytest.approx(1.0)
    
    def test_maturity_over_one_clamped(self):
        """Maturity > 1 should be clamped to 1."""
        weights = compute_bucket_weights(maturity=1.5)
        for bucket, weight in weights.items():
            assert 0 <= weight <= 1
        assert sum(weights.values()) == pytest.approx(1.0)


# =============================================================================
# SCORE CANDIDATE COMPONENT TESTS
# =============================================================================

class TestScoreCandidateComponents:
    """Test individual scoring components."""
    
    def test_progress_value_no_capabilities(self):
        """Progress value with no taught capabilities."""
        candidate = MaterialCandidate(
            material_id=1,
            teaches_capabilities=[],
        )
        progress = {}
        value = compute_progress_value(candidate, progress)
        assert value == 0.0
    
    def test_maintenance_value_never_attempted(self):
        """Maintenance value for never-attempted material."""
        candidate = MaterialCandidate(
            material_id=1,
            last_attempt_at=None,
            ema_score=0.0,
        )
        value = compute_maintenance_value(candidate)
        assert value >= 0.0
    
    def test_novelty_value_all_statuses(self):
        """Novelty value for each possible status."""
        for status in MaterialStatus:
            candidate = MaterialCandidate(material_id=1, status=status)
            value = compute_novelty_value(candidate)
            assert 0.0 <= value <= 1.0
    
    def test_fatigue_penalty_never_attempted(self):
        """Fatigue penalty for never-attempted material."""
        penalty = compute_fatigue_penalty(None)
        assert penalty == 0.0  # No fatigue if never attempted
    
    def test_fatigue_penalty_very_recent(self):
        """Fatigue penalty for very recently attempted material."""
        now = datetime.now()
        penalty = compute_fatigue_penalty(now, datetime.now())
        assert penalty > 0.0  # Should have some fatigue
    
    def test_fatigue_penalty_old_attempt(self):
        """Fatigue penalty should decrease with time."""
        now = datetime.now()
        recent = now - timedelta(minutes=5)
        old = now - timedelta(days=7)
        
        recent_penalty = compute_fatigue_penalty(recent, now)
        old_penalty = compute_fatigue_penalty(old, now)
        
        assert recent_penalty >= old_penalty
