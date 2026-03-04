"""
Tests for Practice Engine Algorithms

Tests cover:
- EMA calculations
- Mastery checks
- Eligibility functions
- Maturity calculations
- Bucket weights
- Target capability selection
- Candidate generation and filtering
- Ranking within buckets
- Focus targeting
- Attempt processing
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
    FocusTarget,
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
    sample_bucket,
    select_target_capabilities,
    build_candidate_pool,
    filter_candidates_by_bucket,
    compute_fatigue_penalty,
    compute_progress_value,
    compute_maintenance_value,
    compute_novelty_value,
    score_candidate,
    rank_candidates,
    compute_focus_score,
    select_focus_targets,
    process_attempt,
    update_pitch_focus_stats,
    get_user_capability_masks,
    set_capability_bit,
    has_capability_bit,
)


# =============================================================================
# EMA TESTS
# =============================================================================

class TestComputeEMA:
    """Tests for EMA calculation."""
    
    def test_first_score(self):
        """First score with no history should weight heavily."""
        result = compute_ema(5.0, 0.0, alpha=0.35)
        assert result == pytest.approx(1.75)  # 0.35 * 5.0 + 0.65 * 0.0
    
    def test_consistent_scores(self):
        """Consistent high scores should converge to that value."""
        ema = 0.0
        for _ in range(20):
            ema = compute_ema(5.0, ema, alpha=0.35)
        assert ema > 4.9  # Should be very close to 5.0
    
    def test_score_drop(self):
        """A drop in score should reduce EMA."""
        ema = 4.5
        new_ema = compute_ema(2.0, ema, alpha=0.35)
        assert new_ema < ema
        assert new_ema == pytest.approx(3.625)  # 0.35 * 2.0 + 0.65 * 4.5
    
    def test_custom_alpha(self):
        """Custom alpha should be applied."""
        result = compute_ema(5.0, 3.0, alpha=0.5)
        assert result == pytest.approx(4.0)  # 0.5 * 5.0 + 0.5 * 3.0
    
    def test_config_alpha(self):
        """Config alpha should be used when provided."""
        config = EngineConfig(ema_alpha=0.5)
        result = compute_ema(5.0, 3.0, config=config)
        assert result == pytest.approx(4.0)


# =============================================================================
# MASTERY TESTS
# =============================================================================

class TestMaterialMastery:
    """Tests for material mastery check."""
    
    def test_not_mastered_low_attempts(self):
        """Should not be mastered with too few attempts."""
        assert not check_material_mastery(5.0, 3)  # High EMA but only 3 attempts
    
    def test_not_mastered_low_ema(self):
        """Should not be mastered with low EMA."""
        assert not check_material_mastery(3.0, 10)  # Many attempts but low EMA
    
    def test_mastered(self):
        """Should be mastered with high EMA and enough attempts."""
        assert check_material_mastery(4.0, 5)
        assert check_material_mastery(4.5, 10)
    
    def test_exactly_at_threshold(self):
        """Should be mastered at exactly the threshold."""
        assert check_material_mastery(4.0, 5)  # Exactly at both thresholds
    
    def test_custom_config(self):
        """Should use custom config values."""
        config = EngineConfig(min_attempts_for_mastery=3, mastery_threshold=3.5)
        assert check_material_mastery(3.5, 3, config=config)
        assert not check_material_mastery(3.4, 3, config=config)


class TestCapabilityMastery:
    """Tests for capability mastery check."""
    
    def test_simple_count(self):
        """Simple count-based mastery."""
        assert check_capability_mastery(evidence_count=3, required_count=3)
        assert not check_capability_mastery(evidence_count=2, required_count=3)
    
    def test_distinct_materials_required(self):
        """Distinct materials requirement."""
        # Has 5 evidence events but only 2 distinct materials
        assert not check_capability_mastery(
            evidence_count=5,
            required_count=3,
            distinct_materials_required=True,
            distinct_material_count=2
        )
        # Has 3+ distinct materials
        assert check_capability_mastery(
            evidence_count=5,
            required_count=3,
            distinct_materials_required=True,
            distinct_material_count=3
        )


# =============================================================================
# ELIGIBILITY TESTS
# =============================================================================

class TestBitmaskEligibility:
    """Tests for bitmask eligibility checking."""
    
    def test_all_required_present(self):
        """User has all required capabilities."""
        user_masks = [0b11111111, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0b00001111, 0, 0, 0, 0, 0, 0, 0]
        assert check_bitmask_eligibility(user_masks, material_masks)
    
    def test_missing_capability(self):
        """User missing required capability."""
        user_masks = [0b00001111, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0b00011111, 0, 0, 0, 0, 0, 0, 0]  # Requires bit 4
        assert not check_bitmask_eligibility(user_masks, material_masks)
    
    def test_no_requirements(self):
        """Material has no requirements."""
        user_masks = [0, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0, 0, 0, 0, 0, 0, 0, 0]
        assert check_bitmask_eligibility(user_masks, material_masks)
    
    def test_multi_mask_eligibility(self):
        """Check across multiple masks."""
        user_masks = [0b11111111, 0b11111111, 0, 0, 0, 0, 0, 0]
        material_masks = [0b00001111, 0b00000011, 0, 0, 0, 0, 0, 0]
        assert check_bitmask_eligibility(user_masks, material_masks)


class TestContentDimensionEligibility:
    """Tests for content dimension eligibility."""
    
    def test_within_caps(self):
        """Material within user's content caps."""
        material_stages = {'rhythm_complexity_stage': 2, 'range_usage_stage': 3}
        user_max_stages = {'rhythm_complexity_stage': 4, 'range_usage_stage': 5}
        assert check_content_dimension_eligibility(material_stages, user_max_stages)
    
    def test_exceeds_caps(self):
        """Material exceeds user's content caps."""
        material_stages = {'rhythm_complexity_stage': 5}
        user_max_stages = {'rhythm_complexity_stage': 3}
        assert not check_content_dimension_eligibility(material_stages, user_max_stages)
    
    def test_none_values_ignored(self):
        """None values should be ignored."""
        material_stages = {'rhythm_complexity_stage': None, 'range_usage_stage': 2}
        user_max_stages = {'rhythm_complexity_stage': 1, 'range_usage_stage': 5}
        assert check_content_dimension_eligibility(material_stages, user_max_stages)


class TestIsMaterialEligible:
    """Tests for combined eligibility check."""
    
    def test_fully_eligible(self):
        """Material passes all checks."""
        assert is_material_eligible(
            user_masks=[0b11111111, 0, 0, 0, 0, 0, 0, 0],
            material_masks=[0b00001111, 0, 0, 0, 0, 0, 0, 0],
            material_stages={'rhythm_complexity_stage': 2},
            user_max_stages={'rhythm_complexity_stage': 5},
            has_license=True
        )
    
    def test_no_license(self):
        """Fails without license."""
        assert not is_material_eligible(
            user_masks=[0b11111111, 0, 0, 0, 0, 0, 0, 0],
            material_masks=[0, 0, 0, 0, 0, 0, 0, 0],
            has_license=False
        )
    
    def test_fails_capability_check(self):
        """Fails capability check."""
        assert not is_material_eligible(
            user_masks=[0, 0, 0, 0, 0, 0, 0, 0],
            material_masks=[0b00000001, 0, 0, 0, 0, 0, 0, 0],
            has_license=True
        )


# =============================================================================
# MATURITY TESTS
# =============================================================================

class TestMaturityCalculations:
    """Tests for maturity calculations."""
    
    def test_material_maturity_zero(self):
        """Zero mastered materials."""
        assert compute_material_maturity(0.0, 10.0) == 0.0
    
    def test_material_maturity_full(self):
        """All materials mastered."""
        assert compute_material_maturity(10.0, 10.0) == 1.0
    
    def test_material_maturity_partial(self):
        """Partial mastery."""
        assert compute_material_maturity(5.0, 10.0) == 0.5
    
    def test_capability_maturity_zero(self):
        """Zero mastered capabilities."""
        assert compute_capability_maturity(0.0, 10.0) == 0.0
    
    def test_capability_maturity_full(self):
        """All capabilities mastered."""
        assert compute_capability_maturity(10.0, 10.0) == 1.0
    
    def test_combined_maturity(self):
        """Combined maturity calculation."""
        result = compute_combined_maturity(cap_maturity=0.5, mat_maturity=0.5)
        assert result == pytest.approx(0.5)  # 0.6*0.5 + 0.4*0.5
        
        result = compute_combined_maturity(cap_maturity=1.0, mat_maturity=0.0)
        assert result == pytest.approx(0.6)  # 0.6*1.0 + 0.4*0.0
    
    def test_combined_maturity_clamped(self):
        """Combined maturity should be clamped to [0, 1]."""
        result = compute_combined_maturity(cap_maturity=1.5, mat_maturity=1.0)
        assert result <= 1.0


# =============================================================================
# BUCKET WEIGHT TESTS
# =============================================================================

class TestBucketWeights:
    """Tests for bucket weight calculations."""
    
    def test_early_learner_weights(self):
        """Early learner should favor in_progress."""
        weights = compute_bucket_weights(maturity=0.0)
        assert weights[Bucket.IN_PROGRESS] > weights[Bucket.NEW]
        assert weights[Bucket.IN_PROGRESS] > weights[Bucket.MAINTENANCE]
    
    def test_advanced_learner_weights(self):
        """Advanced learner should favor maintenance."""
        weights = compute_bucket_weights(maturity=1.0)
        assert weights[Bucket.MAINTENANCE] > weights[Bucket.NEW]
    
    def test_weights_sum_to_one(self):
        """Weights should sum to 1."""
        for maturity in [0.0, 0.25, 0.5, 0.75, 1.0]:
            weights = compute_bucket_weights(maturity)
            total = sum(weights.values())
            assert total == pytest.approx(1.0)
    
    def test_minimum_weights_respected(self):
        """Minimum weights should be respected."""
        config = EngineConfig(min_bucket_new=0.15, min_bucket_in_progress=0.20, min_bucket_maintenance=0.10)
        weights = compute_bucket_weights(maturity=1.0, config=config)
        assert weights[Bucket.NEW] >= 0.15
        assert weights[Bucket.IN_PROGRESS] >= 0.20
        assert weights[Bucket.MAINTENANCE] >= 0.10


class TestSampleBucket:
    """Tests for bucket sampling."""
    
    def test_returns_valid_bucket(self):
        """Should always return a valid bucket."""
        weights = {Bucket.NEW: 0.3, Bucket.IN_PROGRESS: 0.5, Bucket.MAINTENANCE: 0.2}
        for _ in range(100):
            bucket = sample_bucket(weights)
            assert bucket in [Bucket.NEW, Bucket.IN_PROGRESS, Bucket.MAINTENANCE]
    
    def test_respects_weights_distribution(self):
        """Should roughly follow weight distribution over many samples."""
        weights = {Bucket.NEW: 0.1, Bucket.IN_PROGRESS: 0.7, Bucket.MAINTENANCE: 0.2}
        counts = {Bucket.NEW: 0, Bucket.IN_PROGRESS: 0, Bucket.MAINTENANCE: 0}
        
        for _ in range(1000):
            bucket = sample_bucket(weights)
            counts[bucket] += 1
        
        # IN_PROGRESS should be most common
        assert counts[Bucket.IN_PROGRESS] > counts[Bucket.NEW]
        assert counts[Bucket.IN_PROGRESS] > counts[Bucket.MAINTENANCE]


# =============================================================================
# TARGET CAPABILITY SELECTION TESTS
# =============================================================================

class TestTargetCapabilitySelection:
    """Tests for target capability selection."""
    
    def test_selects_near_unlock(self):
        """Should prioritize capabilities near unlock."""
        progress = [
            CapabilityProgress(capability_id=1, evidence_count=2, required_count=3),  # 0.67
            CapabilityProgress(capability_id=2, evidence_count=1, required_count=10),  # 0.1
            CapabilityProgress(capability_id=3, evidence_count=4, required_count=5),  # 0.8
        ]
        targets = select_target_capabilities(progress, EngineConfig(target_capability_count=2))
        target_ids = [t.capability_id for t in targets]
        assert 3 in target_ids  # Highest progress ratio
        assert 1 in target_ids  # Second highest
    
    def test_excludes_mastered(self):
        """Should not select mastered capabilities."""
        progress = [
            CapabilityProgress(capability_id=1, evidence_count=3, required_count=3, is_mastered=True),
            CapabilityProgress(capability_id=2, evidence_count=2, required_count=3, is_mastered=False),
        ]
        targets = select_target_capabilities(progress)
        target_ids = [t.capability_id for t in targets]
        assert 1 not in target_ids
        assert 2 in target_ids
    
    def test_respects_count_limit(self):
        """Should respect target_capability_count."""
        progress = [
            CapabilityProgress(capability_id=i, evidence_count=i, required_count=10)
            for i in range(1, 20)
        ]
        targets = select_target_capabilities(progress, EngineConfig(target_capability_count=5))
        assert len(targets) == 5


# =============================================================================
# CANDIDATE FILTERING TESTS
# =============================================================================

class TestFilterCandidatesByBucket:
    """Tests for filtering candidates by bucket."""
    
    def test_filter_new(self):
        """Should filter to unexplored materials."""
        candidates = [
            MaterialCandidate(material_id=1, status=MaterialStatus.UNEXPLORED, attempt_count=0),
            MaterialCandidate(material_id=2, status=MaterialStatus.IN_PROGRESS, attempt_count=3),
            MaterialCandidate(material_id=3, status=MaterialStatus.MASTERED),
        ]
        result = filter_candidates_by_bucket(candidates, Bucket.NEW)
        assert len(result) == 1
        assert result[0].material_id == 1
    
    def test_filter_in_progress(self):
        """Should filter to in-progress materials."""
        candidates = [
            MaterialCandidate(material_id=1, status=MaterialStatus.UNEXPLORED),
            MaterialCandidate(material_id=2, status=MaterialStatus.IN_PROGRESS),
            MaterialCandidate(material_id=3, status=MaterialStatus.MASTERED),
        ]
        result = filter_candidates_by_bucket(candidates, Bucket.IN_PROGRESS)
        assert len(result) == 1
        assert result[0].material_id == 2
    
    def test_filter_maintenance(self):
        """Should filter to mastered+maintenance materials."""
        candidates = [
            MaterialCandidate(material_id=1, status=MaterialStatus.MASTERED, shelf=MaterialShelf.MAINTENANCE),
            MaterialCandidate(material_id=2, status=MaterialStatus.MASTERED, shelf=MaterialShelf.ARCHIVE),
            MaterialCandidate(material_id=3, status=MaterialStatus.MASTERED, shelf=MaterialShelf.DEFAULT),
        ]
        result = filter_candidates_by_bucket(candidates, Bucket.MAINTENANCE)
        assert len(result) == 1
        assert result[0].material_id == 1


# =============================================================================
# RANKING COMPONENT TESTS
# =============================================================================

class TestFatiguePenalty:
    """Tests for fatigue penalty calculation."""
    
    def test_never_attempted(self):
        """No penalty for never-attempted materials."""
        assert compute_fatigue_penalty(None) == 0.0
    
    def test_recent_attempt_high_penalty(self):
        """Recent attempt should have high penalty."""
        now = datetime.now()
        yesterday = now - timedelta(days=1)
        penalty = compute_fatigue_penalty(yesterday, now)
        assert penalty > 0.5  # Recent = high penalty
    
    def test_old_attempt_low_penalty(self):
        """Old attempt should have low penalty."""
        now = datetime.now()
        long_ago = now - timedelta(days=14)
        penalty = compute_fatigue_penalty(long_ago, now)
        assert penalty < 0.1  # Old = low penalty


class TestProgressValue:
    """Tests for progress value calculation."""
    
    def test_no_teaches_caps(self):
        """Should return 0 if material teaches nothing."""
        candidate = MaterialCandidate(material_id=1, teaches_capabilities=[])
        assert compute_progress_value(candidate, {}) == 0.0
    
    def test_max_progress_ratio(self):
        """Should return max progress ratio among taught capabilities."""
        candidate = MaterialCandidate(material_id=1, teaches_capabilities=[1, 2, 3])
        cap_progress = {
            1: CapabilityProgress(capability_id=1, evidence_count=1, required_count=10),  # 0.1
            2: CapabilityProgress(capability_id=2, evidence_count=8, required_count=10),  # 0.8
            3: CapabilityProgress(capability_id=3, evidence_count=5, required_count=10),  # 0.5
        }
        result = compute_progress_value(candidate, cap_progress)
        assert result == pytest.approx(0.8)
    
    def test_excludes_mastered(self):
        """Should exclude mastered capabilities from progress value."""
        candidate = MaterialCandidate(material_id=1, teaches_capabilities=[1, 2])
        cap_progress = {
            1: CapabilityProgress(capability_id=1, evidence_count=10, required_count=10, is_mastered=True),
            2: CapabilityProgress(capability_id=2, evidence_count=5, required_count=10, is_mastered=False),
        }
        result = compute_progress_value(candidate, cap_progress)
        assert result == pytest.approx(0.5)  # Only counts non-mastered


class TestMaintenanceValue:
    """Tests for maintenance value calculation."""
    
    def test_low_ema_high_value(self):
        """Low EMA should give high maintenance value."""
        candidate = MaterialCandidate(material_id=1, ema_score=1.0)
        assert compute_maintenance_value(candidate) == 1.0  # 1 - 0
    
    def test_high_ema_low_value(self):
        """High EMA should give low maintenance value."""
        candidate = MaterialCandidate(material_id=1, ema_score=5.0)
        assert compute_maintenance_value(candidate) == 0.0  # 1 - 1
    
    def test_mid_ema(self):
        """Mid EMA should give mid value."""
        candidate = MaterialCandidate(material_id=1, ema_score=3.0)
        # Normalized: (3-1)/4 = 0.5, maintenance = 1 - 0.5 = 0.5
        assert compute_maintenance_value(candidate) == pytest.approx(0.5)


class TestNoveltyValue:
    """Tests for novelty value calculation."""
    
    def test_unexplored_has_novelty(self):
        """Unexplored materials should have novelty value 1."""
        candidate = MaterialCandidate(material_id=1, status=MaterialStatus.UNEXPLORED)
        assert compute_novelty_value(candidate) == 1.0
    
    def test_in_progress_no_novelty(self):
        """In-progress materials should have novelty value 0."""
        candidate = MaterialCandidate(material_id=1, status=MaterialStatus.IN_PROGRESS)
        assert compute_novelty_value(candidate) == 0.0
    
    def test_mastered_no_novelty(self):
        """Mastered materials should have novelty value 0."""
        candidate = MaterialCandidate(material_id=1, status=MaterialStatus.MASTERED)
        assert compute_novelty_value(candidate) == 0.0


# =============================================================================
# FOCUS TARGETING TESTS
# =============================================================================

class TestFocusScore:
    """Tests for focus targeting score calculation."""
    
    def test_low_ema_high_score(self):
        """Low EMA should result in higher focus score (needs attention)."""
        score_low = compute_focus_score(
            pitch_midi=60, ema_score=1.0, last_attempt_at=datetime.now(),
            user_range_center=60
        )
        score_high = compute_focus_score(
            pitch_midi=60, ema_score=5.0, last_attempt_at=datetime.now(),
            user_range_center=60
        )
        assert score_low > score_high
    
    def test_extreme_pitch_penalty(self):
        """Pitches far from center should be penalized."""
        center = 60
        score_center = compute_focus_score(
            pitch_midi=center, ema_score=2.0, last_attempt_at=None,
            user_range_center=center
        )
        score_extreme = compute_focus_score(
            pitch_midi=center + 24, ema_score=2.0, last_attempt_at=None,
            user_range_center=center
        )
        assert score_center > score_extreme


class TestSelectFocusTargets:
    """Tests for focus target selection."""
    
    def test_selects_weakest_combos(self):
        """Should select weakest pitch/focus combinations."""
        pitches = [60, 62, 64]
        focus_ids = [1, 2]
        stats = {
            (60, 1): (2.0, None),  # Low EMA - should be selected
            (60, 2): (4.5, None),
            (62, 1): (4.0, None),
            (62, 2): (4.0, None),
            (64, 1): (4.5, None),
            (64, 2): (1.5, None),  # Low EMA - should be selected
        }
        targets = select_focus_targets(
            pitches, focus_ids, stats, user_range_center=62,
            config=EngineConfig(focus_targets_per_material=2)
        )
        assert len(targets) == 2
        # Should select the two lowest EMA combos
        target_keys = [(t.pitch_midi, t.focus_card_id) for t in targets]
        assert (64, 2) in target_keys or (60, 1) in target_keys
    
    def test_respects_count_limit(self):
        """Should respect focus_targets_per_material."""
        targets = select_focus_targets(
            [60, 62, 64, 66], [1, 2, 3], {}, 62,
            config=EngineConfig(focus_targets_per_material=3)
        )
        assert len(targets) == 3


# =============================================================================
# ATTEMPT PROCESSING TESTS
# =============================================================================

class TestProcessAttempt:
    """Tests for attempt processing."""
    
    def test_updates_ema(self):
        """Should update EMA correctly."""
        material = MaterialCandidate(material_id=1, ema_score=3.0, attempt_count=5)
        result = process_attempt(
            rating=5,
            material_state=material,
            teaches_capability_ids=[],
            capability_progress={},
            config=EngineConfig(ema_alpha=0.35)
        )
        expected_ema = 0.35 * 5.0 + 0.65 * 3.0
        assert result.new_ema == pytest.approx(expected_ema)
    
    def test_increments_attempt_count(self):
        """Should increment attempt count."""
        material = MaterialCandidate(material_id=1, ema_score=0.0, attempt_count=5)
        result = process_attempt(
            rating=4, material_state=material,
            teaches_capability_ids=[], capability_progress={}
        )
        assert result.new_attempt_count == 6
    
    def test_transitions_to_in_progress(self):
        """Should transition from UNEXPLORED to IN_PROGRESS."""
        material = MaterialCandidate(
            material_id=1, ema_score=0.0, attempt_count=0,
            status=MaterialStatus.UNEXPLORED
        )
        result = process_attempt(
            rating=3, material_state=material,
            teaches_capability_ids=[], capability_progress={}
        )
        assert result.new_status == MaterialStatus.IN_PROGRESS
    
    def test_transitions_to_mastered(self):
        """Should transition to MASTERED when criteria met."""
        material = MaterialCandidate(
            material_id=1, ema_score=4.2, attempt_count=4,  # One more attempt will hit threshold
            status=MaterialStatus.IN_PROGRESS
        )
        result = process_attempt(
            rating=5, material_state=material,
            teaches_capability_ids=[], capability_progress={},
            config=EngineConfig(min_attempts_for_mastery=5, mastery_threshold=4.0)
        )
        assert result.new_status == MaterialStatus.MASTERED
    
    def test_adds_capability_evidence(self):
        """Should add evidence for taught capabilities."""
        material = MaterialCandidate(material_id=1, ema_score=0.0, attempt_count=0)
        cap_progress = {
            1: CapabilityProgress(capability_id=1, evidence_count=2, required_count=5),
        }
        result = process_attempt(
            rating=4,  # Meets threshold
            material_state=material,
            teaches_capability_ids=[1],
            capability_progress=cap_progress,
            is_off_course=False
        )
        assert 1 in result.capability_evidence_added
    
    def test_no_evidence_for_off_course(self):
        """Should not add evidence for off-course attempts."""
        material = MaterialCandidate(material_id=1, ema_score=0.0, attempt_count=0)
        cap_progress = {
            1: CapabilityProgress(capability_id=1, evidence_count=2, required_count=5),
        }
        result = process_attempt(
            rating=5,
            material_state=material,
            teaches_capability_ids=[1],
            capability_progress=cap_progress,
            is_off_course=True  # Off-course!
        )
        assert 1 not in result.capability_evidence_added
    
    def test_detects_capability_mastery(self):
        """Should detect when capability is mastered."""
        material = MaterialCandidate(material_id=1, ema_score=0.0, attempt_count=0)
        cap_progress = {
            1: CapabilityProgress(capability_id=1, evidence_count=4, required_count=5),  # One away
        }
        result = process_attempt(
            rating=4,
            material_state=material,
            teaches_capability_ids=[1],
            capability_progress=cap_progress
        )
        assert 1 in result.capabilities_mastered


# =============================================================================
# BITMASK HELPER TESTS
# =============================================================================

class TestBitmaskHelpers:
    """Tests for bitmask manipulation helpers."""
    
    def test_set_capability_bit(self):
        """Should set correct bit."""
        masks = [0, 0, 0, 0, 0, 0, 0, 0]
        masks = set_capability_bit(masks, 0)
        assert masks[0] == 1
        
        masks = set_capability_bit(masks, 63)
        assert masks[0] == (1 | (1 << 63))
        
        masks = set_capability_bit(masks, 64)
        assert masks[1] == 1
    
    def test_has_capability_bit(self):
        """Should correctly check bit presence."""
        masks = [0b00001111, 0b00000001, 0, 0, 0, 0, 0, 0]
        assert has_capability_bit(masks, 0)
        assert has_capability_bit(masks, 3)
        assert not has_capability_bit(masks, 4)
        assert has_capability_bit(masks, 64)
        assert not has_capability_bit(masks, 65)
    
    def test_invalid_bit_index(self):
        """Should handle invalid bit indices gracefully."""
        masks = [0, 0, 0, 0, 0, 0, 0, 0]
        masks = set_capability_bit(masks, -1)
        assert masks == [0, 0, 0, 0, 0, 0, 0, 0]
        
        masks = set_capability_bit(masks, 512)
        assert masks == [0, 0, 0, 0, 0, 0, 0, 0]
        
        assert not has_capability_bit(masks, -1)
        assert not has_capability_bit(masks, 512)


# =============================================================================
# PITCH FOCUS STATS UPDATE TESTS
# =============================================================================

class TestUpdatePitchFocusStats:
    """Tests for pitch focus stats update."""
    
    def test_updates_ema_and_count(self):
        """Should update both EMA and attempt count."""
        new_ema, new_count = update_pitch_focus_stats(
            pitch_midi=60, focus_card_id=1, rating=4,
            current_ema=3.0, current_attempts=5,
            config=EngineConfig(ema_alpha=0.35)
        )
        expected_ema = 0.35 * 4.0 + 0.65 * 3.0
        assert new_ema == pytest.approx(expected_ema)
        assert new_count == 6
