"""
Tests for stage_derivation module.

Tests score-to-stage conversion, stage labels, and domain staging.
"""

import pytest
from app.stage_derivation import (
    DEFAULT_STAGE_THRESHOLDS,
    STAGE_LABELS,
    STAGE_LABELS_SHORT,
    score_to_stage,
    stage_to_score_range,
    get_stage_label,
    derive_domain_stages,
    DomainStages,
    AllDomainStages,
    derive_all_stages,
    analyze_score_distribution,
    suggest_thresholds_from_distribution,
)


# =============================================================================
# CONSTANT VALIDATION
# =============================================================================

class TestConstants:
    """Test stage derivation constants."""
    
    def test_default_thresholds_has_6_values(self):
        """Should have 6 thresholds for 7 stages."""
        assert len(DEFAULT_STAGE_THRESHOLDS) == 6
    
    def test_thresholds_are_ascending(self):
        """Thresholds should be in ascending order."""
        for i in range(len(DEFAULT_STAGE_THRESHOLDS) - 1):
            assert DEFAULT_STAGE_THRESHOLDS[i] < DEFAULT_STAGE_THRESHOLDS[i + 1]
    
    def test_thresholds_in_valid_range(self):
        """All thresholds should be between 0 and 1."""
        for t in DEFAULT_STAGE_THRESHOLDS:
            assert 0.0 < t < 1.0
    
    def test_stage_labels_has_7_entries(self):
        """Should have labels for stages 0-6."""
        assert len(STAGE_LABELS) == 7
        for i in range(7):
            assert i in STAGE_LABELS
    
    def test_stage_labels_short_has_7_entries(self):
        """Should have short labels for stages 0-6."""
        assert len(STAGE_LABELS_SHORT) == 7
        for i in range(7):
            assert i in STAGE_LABELS_SHORT


# =============================================================================
# SCORE TO STAGE CONVERSION
# =============================================================================

class TestScoreToStage:
    """Test score_to_stage function."""
    
    def test_zero_score_is_stage_0(self):
        assert score_to_stage(0.0) == 0
    
    def test_score_just_below_first_threshold(self):
        assert score_to_stage(0.14) == 0
    
    def test_score_at_first_threshold(self):
        assert score_to_stage(0.15) == 1
    
    def test_score_in_middle_range(self):
        assert score_to_stage(0.50) == 3
    
    def test_score_at_stage_5_threshold(self):
        assert score_to_stage(0.75) == 5
    
    def test_score_just_below_max_threshold(self):
        assert score_to_stage(0.89) == 5
    
    def test_score_at_max_threshold(self):
        assert score_to_stage(0.90) == 6
    
    def test_perfect_score_is_stage_6(self):
        assert score_to_stage(1.0) == 6
    
    def test_negative_score_clamped_to_stage_0(self):
        assert score_to_stage(-0.5) == 0
    
    def test_score_above_1_clamped_to_stage_6(self):
        assert score_to_stage(1.5) == 6
    
    def test_boundary_cases(self):
        """Test all threshold boundaries."""
        assert score_to_stage(0.00) == 0
        assert score_to_stage(0.149) == 0
        assert score_to_stage(0.15) == 1
        assert score_to_stage(0.299) == 1
        assert score_to_stage(0.30) == 2
        assert score_to_stage(0.449) == 2
        assert score_to_stage(0.45) == 3
        assert score_to_stage(0.599) == 3
        assert score_to_stage(0.60) == 4
        assert score_to_stage(0.749) == 4
        assert score_to_stage(0.75) == 5
        assert score_to_stage(0.899) == 5
        assert score_to_stage(0.90) == 6
        assert score_to_stage(1.0) == 6


class TestScoreToStageCustomThresholds:
    """Test score_to_stage with custom thresholds."""
    
    def test_uniform_thresholds(self):
        """Custom even thresholds."""
        thresholds = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6]
        assert score_to_stage(0.05, thresholds) == 0
        assert score_to_stage(0.15, thresholds) == 1
        assert score_to_stage(0.55, thresholds) == 5
        assert score_to_stage(0.65, thresholds) == 6
    
    def test_tight_thresholds(self):
        """Very close together thresholds."""
        thresholds = [0.1, 0.11, 0.12, 0.13, 0.14, 0.15]
        assert score_to_stage(0.09, thresholds) == 0
        assert score_to_stage(0.135, thresholds) == 4


# =============================================================================
# STAGE TO SCORE RANGE
# =============================================================================

class TestStageToScoreRange:
    """Test stage_to_score_range function."""
    
    def test_stage_0_range(self):
        low, high = stage_to_score_range(0)
        assert low == 0.0
        assert high == 0.15
    
    def test_stage_1_range(self):
        low, high = stage_to_score_range(1)
        assert low == 0.15
        assert high == 0.30
    
    def test_stage_3_range(self):
        low, high = stage_to_score_range(3)
        assert low == 0.45
        assert high == 0.60
    
    def test_stage_6_range(self):
        low, high = stage_to_score_range(6)
        assert low == 0.90
        assert high == 1.0
    
    def test_negative_stage_clamped(self):
        low, high = stage_to_score_range(-1)
        assert low == 0.0
        assert high == 0.15  # Stage 0 range
    
    def test_stage_above_6_clamped(self):
        low, high = stage_to_score_range(10)
        assert low == 0.90
        assert high == 1.0  # Stage 6 range
    
    def test_ranges_are_contiguous(self):
        """All ranges should be contiguous (no gaps)."""
        prev_high = 0.0
        for stage in range(7):
            low, high = stage_to_score_range(stage)
            assert low == prev_high, f"Gap between stage {stage-1} and {stage}"
            prev_high = high
        assert prev_high == 1.0


# =============================================================================
# STAGE LABELS
# =============================================================================

class TestGetStageLabel:
    """Test get_stage_label function."""
    
    def test_stage_0_label(self):
        assert get_stage_label(0) == "Trivial"
    
    def test_stage_1_label(self):
        assert get_stage_label(1) == "Beginner"
    
    def test_stage_3_label(self):
        assert get_stage_label(3) == "Intermediate"
    
    def test_stage_6_label(self):
        assert get_stage_label(6) == "Expert"
    
    def test_stage_0_short_label(self):
        assert get_stage_label(0, short=True) == "I"
    
    def test_stage_6_short_label(self):
        assert get_stage_label(6, short=True) == "VII"
    
    def test_negative_stage_clamped(self):
        assert get_stage_label(-1) == "Trivial"
    
    def test_stage_above_6_clamped(self):
        assert get_stage_label(10) == "Expert"


# =============================================================================
# DOMAIN STAGES
# =============================================================================

class TestDeriveDomainStages:
    """Test derive_domain_stages function."""
    
    def test_returns_domain_stages_object(self):
        scores = {"primary": 0.5, "hazard": 0.3, "overall": 0.4}
        result = derive_domain_stages(scores)
        assert isinstance(result, DomainStages)
    
    def test_all_zeroes(self):
        scores = {"primary": 0.0, "hazard": 0.0, "overall": 0.0}
        result = derive_domain_stages(scores)
        assert result.primary_stage == 0
        assert result.hazard_stage == 0
        assert result.overall_stage == 0
    
    def test_all_ones(self):
        scores = {"primary": 1.0, "hazard": 1.0, "overall": 1.0}
        result = derive_domain_stages(scores)
        assert result.primary_stage == 6
        assert result.hazard_stage == 6
        assert result.overall_stage == 6
    
    def test_mixed_scores(self):
        scores = {"primary": 0.5, "hazard": 0.2, "overall": 0.8}
        result = derive_domain_stages(scores)
        assert result.primary_stage == 3  # 0.45-0.60 is stage 3
        assert result.hazard_stage == 1   # 0.15-0.30 is stage 1
        assert result.overall_stage == 5  # 0.75-0.90 is stage 5
    
    def test_missing_keys_default_to_zero(self):
        scores = {"primary": 0.5}  # Missing hazard and overall
        result = derive_domain_stages(scores)
        assert result.primary_stage == 3
        assert result.hazard_stage == 0  # Default 0.0 → stage 0
        assert result.overall_stage == 0
    
    def test_empty_dict(self):
        result = derive_domain_stages({})
        assert result.primary_stage == 0
        assert result.hazard_stage == 0
        assert result.overall_stage == 0


class TestDomainStagesDataclass:
    """Test DomainStages dataclass."""
    
    def test_create_instance(self):
        stages = DomainStages(primary_stage=2, hazard_stage=1, overall_stage=3)
        assert stages.primary_stage == 2
        assert stages.hazard_stage == 1
        assert stages.overall_stage == 3
    
    def test_equality(self):
        stages1 = DomainStages(primary_stage=2, hazard_stage=1, overall_stage=3)
        stages2 = DomainStages(primary_stage=2, hazard_stage=1, overall_stage=3)
        assert stages1 == stages2
    
    def test_inequality(self):
        stages1 = DomainStages(primary_stage=2, hazard_stage=1, overall_stage=3)
        stages2 = DomainStages(primary_stage=3, hazard_stage=1, overall_stage=3)
        assert stages1 != stages2


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestScoreStageRoundTrip:
    """Test that score-to-stage and stage-to-range are consistent."""
    
    def test_midpoint_of_range_maps_back(self):
        """Midpoint of a stage range should convert back to that stage."""
        for stage in range(7):
            low, high = stage_to_score_range(stage)
            midpoint = (low + high) / 2
            assert score_to_stage(midpoint) == stage
    
    def test_low_bound_maps_to_stage(self):
        """Low bound of range should map to the stage."""
        for stage in range(7):
            low, _ = stage_to_score_range(stage)
            if stage > 0:  # Skip stage 0 since low=0 is edge case
                assert score_to_stage(low) == stage
    
    def test_just_below_high_bound_maps_to_stage(self):
        """Just below high bound should map to the stage."""
        for stage in range(7):
            _, high = stage_to_score_range(stage)
            if stage < 6:  # Skip stage 6 since high=1.0 is edge case
                assert score_to_stage(high - 0.001) == stage


class TestStageProgression:
    """Test stage progression scenarios."""
    
    def test_increasing_scores_give_increasing_stages(self):
        """Monotonically increasing scores should give non-decreasing stages."""
        scores = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
        stages = [score_to_stage(s) for s in scores]
        for i in range(len(stages) - 1):
            assert stages[i] <= stages[i + 1]
    
    def test_all_labels_are_unique(self):
        """Each stage should have a unique label."""
        labels = [get_stage_label(s) for s in range(7)]
        assert len(labels) == len(set(labels))
    
    def test_short_labels_are_roman_numerals(self):
        """Short labels should be Roman numerals I-VII."""
        expected = ["I", "II", "III", "IV", "V", "VI", "VII"]
        for stage in range(7):
            assert get_stage_label(stage, short=True) == expected[stage]


# =============================================================================
# ALL DOMAIN STAGES
# =============================================================================

class TestAllDomainStages:
    """Test AllDomainStages dataclass."""
    
    def test_create_empty(self):
        """Should create with all None by default."""
        stages = AllDomainStages()
        assert stages.interval is None
        assert stages.rhythm is None
        assert stages.tonal is None
        assert stages.tempo is None
        assert stages.range is None
        assert stages.throughput is None
    
    def test_create_with_values(self):
        """Should create with provided domain stages."""
        interval_stages = DomainStages(primary_stage=2, hazard_stage=1, overall_stage=2)
        stages = AllDomainStages(interval=interval_stages)
        assert stages.interval == interval_stages
        assert stages.rhythm is None


class TestDeriveAllStages:
    """Test derive_all_stages function."""
    
    def test_empty_scores(self):
        """Empty dict should return all None."""
        result = derive_all_stages({})
        assert result.interval is None
        assert result.rhythm is None
    
    def test_single_domain(self):
        """Single domain should populate only that field."""
        scores = {"interval": {"primary": 0.5, "hazard": 0.3, "overall": 0.4}}
        result = derive_all_stages(scores)
        assert result.interval is not None
        assert result.interval.primary_stage == 3
        assert result.rhythm is None
    
    def test_multiple_domains(self):
        """Multiple domains should all be populated."""
        scores = {
            "interval": {"primary": 0.5, "hazard": 0.3, "overall": 0.4},
            "rhythm": {"primary": 0.8, "hazard": 0.1, "overall": 0.7},
            "tonal": {"primary": 0.2, "hazard": 0.2, "overall": 0.2},
        }
        result = derive_all_stages(scores)
        assert result.interval.primary_stage == 3
        assert result.rhythm.primary_stage == 5
        assert result.tonal.primary_stage == 1
        assert result.tempo is None
    
    def test_all_domains(self):
        """All 6 domains should be populated."""
        scores = {
            "interval": {"primary": 0.5, "hazard": 0.3, "overall": 0.4},
            "rhythm": {"primary": 0.5, "hazard": 0.3, "overall": 0.4},
            "tonal": {"primary": 0.5, "hazard": 0.3, "overall": 0.4},
            "tempo": {"primary": 0.5, "hazard": 0.3, "overall": 0.4},
            "range": {"primary": 0.5, "hazard": 0.3, "overall": 0.4},
            "throughput": {"primary": 0.5, "hazard": 0.3, "overall": 0.4},
        }
        result = derive_all_stages(scores)
        assert result.interval is not None
        assert result.rhythm is not None
        assert result.tonal is not None
        assert result.tempo is not None
        assert result.range is not None
        assert result.throughput is not None


# =============================================================================
# CALIBRATION UTILITIES
# =============================================================================

class TestAnalyzeScoreDistribution:
    """Test analyze_score_distribution function."""
    
    def test_empty_list(self):
        """Empty list should return zero count."""
        result = analyze_score_distribution([])
        assert result['count'] == 0
        assert result['min'] is None
        assert result['max'] is None
    
    def test_single_score(self):
        """Single score should have same min/max/mean/median."""
        result = analyze_score_distribution([0.5])
        assert result['count'] == 1
        assert result['min'] == 0.5
        assert result['max'] == 0.5
        assert result['mean'] == 0.5
        assert result['median'] == 0.5
    
    def test_multiple_scores(self):
        """Multiple scores should calculate stats correctly."""
        scores = [0.1, 0.3, 0.5, 0.7, 0.9]
        result = analyze_score_distribution(scores)
        assert result['count'] == 5
        assert result['min'] == 0.1
        assert result['max'] == 0.9
        assert result['mean'] == 0.5
        assert result['median'] == 0.5
    
    def test_percentiles_exist(self):
        """Should calculate standard percentiles."""
        scores = [i * 0.01 for i in range(101)]  # 0.0 to 1.0
        result = analyze_score_distribution(scores)
        assert 'p10' in result['percentiles']
        assert 'p25' in result['percentiles']
        assert 'p50' in result['percentiles']
        assert 'p75' in result['percentiles']
        assert 'p90' in result['percentiles']
        assert 'p95' in result['percentiles']
    
    def test_stage_distribution(self):
        """Should count scores per stage."""
        scores = [0.0, 0.1, 0.2, 0.3, 0.5, 0.7, 0.95]
        result = analyze_score_distribution(scores)
        assert 'stage_distribution' in result
        # Check that all 7 stages are represented
        for stage in range(7):
            assert stage in result['stage_distribution']


class TestSuggestThresholdsFromDistribution:
    """Test suggest_thresholds_from_distribution function."""
    
    def test_empty_list_returns_defaults(self):
        """Empty list should return default thresholds."""
        result = suggest_thresholds_from_distribution([])
        assert result == DEFAULT_STAGE_THRESHOLDS
    
    def test_returns_six_thresholds(self):
        """Should always return exactly 6 thresholds."""
        scores = [i * 0.1 for i in range(11)]
        result = suggest_thresholds_from_distribution(scores)
        assert len(result) == 6
    
    def test_thresholds_are_ascending(self):
        """Thresholds should be in ascending order."""
        scores = [i * 0.01 for i in range(101)]
        result = suggest_thresholds_from_distribution(scores)
        for i in range(len(result) - 1):
            assert result[i] <= result[i + 1]
    
    def test_custom_distribution(self):
        """Custom target distribution should affect thresholds."""
        scores = [i * 0.01 for i in range(101)]
        # Heavy toward low stages
        target = {0: 0.30, 1: 0.30, 2: 0.20, 3: 0.10, 4: 0.05, 5: 0.03, 6: 0.02}
        result = suggest_thresholds_from_distribution(scores, target)
        assert len(result) == 6
        # First threshold should be higher since more items in stage 0
        assert result[0] > DEFAULT_STAGE_THRESHOLDS[0]
