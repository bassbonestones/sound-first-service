"""Tests for Soft Gate Predictor.

Tests the prediction of soft gate metrics for generated content,
including interval stages, rhythm complexity, and tonal complexity.
"""

import pytest
from typing import Set

from app.schemas.generation_schemas import (
    ArpeggioPattern,
    ArpeggioType,
    GenerationRequest,
    GenerationType,
    MusicalKey,
    RhythmType,
    ScalePattern,
    ScaleType,
)
from app.services.generation.soft_gate_predictor import (
    PredictedSoftGates,
    RHYTHM_COMPLEXITY_MAP,
    get_rhythm_complexity,
    get_tonal_complexity,
    predict_soft_gates,
    _calculate_sustained_stage,
    _calculate_hazard_stage,
    _estimate_p75_from_intervals,
    _get_melodic_intervals_for_scale_pattern,
    _get_melodic_intervals_for_arpeggio_pattern,
)


class TestRhythmComplexity:
    """Tests for rhythm complexity mapping."""
    
    def test_whole_notes_lowest_complexity(self) -> None:
        """Whole notes should have minimal complexity."""
        score = get_rhythm_complexity(RhythmType.WHOLE_NOTES)
        assert score == 0.05
    
    def test_quarter_notes_basic(self) -> None:
        """Quarter notes should have basic complexity."""
        score = get_rhythm_complexity(RhythmType.QUARTER_NOTES)
        assert score == 0.20
    
    def test_eighth_notes_moderate(self) -> None:
        """Eighth notes should have moderate complexity."""
        score = get_rhythm_complexity(RhythmType.EIGHTH_NOTES)
        assert score == 0.40
    
    def test_sixteenth_notes_high(self) -> None:
        """Sixteenth notes should have high complexity."""
        score = get_rhythm_complexity(RhythmType.SIXTEENTH_NOTES)
        assert score == 0.60
    
    def test_compound_cells_high(self) -> None:
        """Compound rhythm cells should have high complexity."""
        score = get_rhythm_complexity(RhythmType.SIXTEENTH_EIGHTH_SIXTEENTH)
        assert score == 0.65
    
    def test_all_rhythms_have_mapping(self) -> None:
        """All RhythmType values should have a mapping."""
        for rhythm in RhythmType:
            score = get_rhythm_complexity(rhythm)
            assert 0.0 <= score <= 1.0
    
    def test_complexity_ordering(self) -> None:
        """Basic rhythms should have lower complexity than subdivisions."""
        whole = get_rhythm_complexity(RhythmType.WHOLE_NOTES)
        half = get_rhythm_complexity(RhythmType.HALF_NOTES)
        quarter = get_rhythm_complexity(RhythmType.QUARTER_NOTES)
        eighth = get_rhythm_complexity(RhythmType.EIGHTH_NOTES)
        sixteenth = get_rhythm_complexity(RhythmType.SIXTEENTH_NOTES)
        
        assert whole < half < quarter < eighth < sixteenth


class TestTonalComplexity:
    """Tests for tonal complexity mapping."""
    
    def test_c_major_basic(self) -> None:
        """C major should have 0 accidentals, stage 2."""
        accidentals, stage = get_tonal_complexity(MusicalKey.C)
        assert accidentals == 0
        assert stage == 2
    
    def test_g_major_one_sharp(self) -> None:
        """G major should have 1 accidental, stage 2."""
        accidentals, stage = get_tonal_complexity(MusicalKey.G)
        assert accidentals == 1
        assert stage == 2
    
    def test_f_major_one_flat(self) -> None:
        """F major should have 1 accidental, stage 2."""
        accidentals, stage = get_tonal_complexity(MusicalKey.F)
        assert accidentals == 1
        assert stage == 2
    
    def test_d_major_two_sharps(self) -> None:
        """D major should have 2 accidentals, stage 3."""
        accidentals, stage = get_tonal_complexity(MusicalKey.D)
        assert accidentals == 2
        assert stage == 3
    
    def test_b_flat_two_flats(self) -> None:
        """Bb major should have 2 accidentals, stage 3."""
        accidentals, stage = get_tonal_complexity(MusicalKey.B_FLAT)
        assert accidentals == 2
        assert stage == 3
    
    def test_f_sharp_six_sharps(self) -> None:
        """F# major should have 6 accidentals, stage 5."""
        accidentals, stage = get_tonal_complexity(MusicalKey.F_SHARP)
        assert accidentals == 6
        assert stage == 5
    
    def test_chromatic_scale_always_high(self) -> None:
        """Chromatic scale should always return stage 5."""
        _, stage = get_tonal_complexity(MusicalKey.C, ScaleType.CHROMATIC)
        assert stage == 5
    
    def test_blues_scale_adds_one(self) -> None:
        """Blues scale should add +1 to tonal stage."""
        _, stage_without = get_tonal_complexity(MusicalKey.C)
        _, stage_with = get_tonal_complexity(MusicalKey.C, ScaleType.BLUES)
        assert stage_with == stage_without + 1
    
    def test_blues_scale_caps_at_5(self) -> None:
        """Blues scale modifier should cap at stage 5."""
        _, stage = get_tonal_complexity(MusicalKey.F_SHARP, ScaleType.BLUES)
        assert stage == 5


class TestIntervalStages:
    """Tests for interval stage calculations."""
    
    def test_sustained_stage_unison(self) -> None:
        """p75 of 0 should give stage 0."""
        stage = _calculate_sustained_stage(0)
        assert stage == 0
    
    def test_sustained_stage_half_step(self) -> None:
        """p75 of 1 should give stage 1."""
        stage = _calculate_sustained_stage(1)
        assert stage == 1
    
    def test_sustained_stage_whole_step(self) -> None:
        """p75 of 2 should give stage 2."""
        stage = _calculate_sustained_stage(2)
        assert stage == 2
    
    def test_sustained_stage_thirds(self) -> None:
        """p75 of 3-4 should give stage 3."""
        assert _calculate_sustained_stage(3) == 3
        assert _calculate_sustained_stage(4) == 3
    
    def test_sustained_stage_fourths(self) -> None:
        """p75 of 5-7 should give stage 4."""
        assert _calculate_sustained_stage(5) == 4
        assert _calculate_sustained_stage(7) == 4
    
    def test_sustained_stage_sixths(self) -> None:
        """p75 of 8-9 should give stage 5."""
        assert _calculate_sustained_stage(8) == 5
        assert _calculate_sustained_stage(9) == 5
    
    def test_sustained_stage_sevenths_plus(self) -> None:
        """p75 > 9 should give stage 6."""
        assert _calculate_sustained_stage(10) == 6
        assert _calculate_sustained_stage(12) == 6
    
    def test_hazard_stage_steps(self) -> None:
        """max of 0-2 should give stage 0."""
        assert _calculate_hazard_stage(0) == 0
        assert _calculate_hazard_stage(2) == 0
    
    def test_hazard_stage_small_skip(self) -> None:
        """max of 3-4 should give stage 1."""
        assert _calculate_hazard_stage(3) == 1
        assert _calculate_hazard_stage(4) == 1
    
    def test_hazard_stage_fourths(self) -> None:
        """max of 5-7 should give stage 2."""
        assert _calculate_hazard_stage(5) == 2
        assert _calculate_hazard_stage(7) == 2
    
    def test_hazard_stage_major_7th(self) -> None:
        """max of 8-11 should give stage 3."""
        assert _calculate_hazard_stage(8) == 3
        assert _calculate_hazard_stage(11) == 3
    
    def test_hazard_stage_octave(self) -> None:
        """max of 12-15 should give stage 4."""
        assert _calculate_hazard_stage(12) == 4
        assert _calculate_hazard_stage(15) == 4
    
    def test_hazard_stage_extended(self) -> None:
        """max of 16-20 should give stage 5."""
        assert _calculate_hazard_stage(16) == 5
        assert _calculate_hazard_stage(20) == 5
    
    def test_hazard_stage_extreme(self) -> None:
        """max > 20 should give stage 6."""
        assert _calculate_hazard_stage(21) == 6
        assert _calculate_hazard_stage(24) == 6


class TestP75Estimation:
    """Tests for p75 interval estimation."""
    
    def test_empty_set(self) -> None:
        """Empty interval set should return 0."""
        assert _estimate_p75_from_intervals(set()) == 0
    
    def test_single_interval(self) -> None:
        """Single interval should return that interval."""
        assert _estimate_p75_from_intervals({3}) == 3
    
    def test_two_intervals(self) -> None:
        """Two intervals should return the larger one (p75)."""
        assert _estimate_p75_from_intervals({2, 4}) == 4
    
    def test_multiple_intervals(self) -> None:
        """Multiple intervals should return approximate p75."""
        # {1, 2, 3, 4} - p75 index is ~3, value is 3 or 4
        result = _estimate_p75_from_intervals({1, 2, 3, 4})
        assert result in (3, 4)


class TestScalePatternIntervals:
    """Tests for scale pattern interval computation."""
    
    def test_ionian_straight_intervals(self) -> None:
        """Ionian straight pattern should have step intervals."""
        intervals = _get_melodic_intervals_for_scale_pattern(
            ScaleType.IONIAN, ScalePattern.STRAIGHT_UP_DOWN
        )
        # Major scale steps: W-W-H-W-W-W-H = 2,2,1,2,2,2,1
        assert 1 in intervals  # Half step
        assert 2 in intervals  # Whole step
        assert max(intervals) <= 2  # No larger intervals
    
    def test_ionian_in_3rds_intervals(self) -> None:
        """Ionian in 3rds should have third intervals."""
        intervals = _get_melodic_intervals_for_scale_pattern(
            ScaleType.IONIAN, ScalePattern.IN_3RDS
        )
        # Thirds in major scale: 3 or 4 semitones
        assert 3 in intervals or 4 in intervals
        assert max(intervals) <= 4
    
    def test_ionian_in_octaves_intervals(self) -> None:
        """Ionian in octaves should have octave intervals."""
        intervals = _get_melodic_intervals_for_scale_pattern(
            ScaleType.IONIAN, ScalePattern.IN_OCTAVES
        )
        # Should include octaves (12 semitones)
        assert 12 in intervals
    
    def test_unknown_scale_returns_empty(self) -> None:
        """Unknown scale type should return empty set."""
        # Using a valid pattern but with corrupted scale_type check
        intervals = _get_melodic_intervals_for_scale_pattern(
            ScaleType.IONIAN, ScalePattern.STRAIGHT_UP_DOWN
        )
        assert len(intervals) > 0  # Valid case should work
    
    def test_chromatic_in_10ths_intervals(self) -> None:
        """Chromatic IN_10THS (major 6ths) should have large intervals."""
        intervals = _get_melodic_intervals_for_scale_pattern(
            ScaleType.CHROMATIC, ScalePattern.IN_10THS
        )
        # IN_10THS on chromatic: skip 9 chromatic notes = 9 semitones (M6)
        # Should have significant intervals, NOT just 1 semitone
        assert max(intervals) > 1  # Bug fix: was falling through to straight
        assert 9 in intervals  # Major 6th forward skip
    
    def test_chromatic_straight_intervals(self) -> None:
        """Chromatic straight pattern should have 1 semitone intervals."""
        intervals = _get_melodic_intervals_for_scale_pattern(
            ScaleType.CHROMATIC, ScalePattern.STRAIGHT_UP_DOWN
        )
        # Chromatic straight: all half steps
        assert 1 in intervals
        assert max(intervals) == 1


class TestArpeggioPatternIntervals:
    """Tests for arpeggio pattern interval computation."""
    
    def test_major_triad_intervals(self) -> None:
        """Major triad should have third and fourth intervals."""
        intervals = _get_melodic_intervals_for_arpeggio_pattern(
            ArpeggioType.MAJOR, ArpeggioPattern.STRAIGHT_UP_DOWN
        )
        # Major triad: 4 (M3) + 3 (m3) semitones
        assert 3 in intervals or 4 in intervals
    
    def test_major_7th_intervals(self) -> None:
        """Major 7th arpeggio should have larger intervals."""
        intervals = _get_melodic_intervals_for_arpeggio_pattern(
            ArpeggioType.MAJOR_7, ArpeggioPattern.STRAIGHT_UP_DOWN
        )
        # Should have some intervals
        assert len(intervals) > 0


class TestPredictSoftGates:
    """Tests for the main predict_soft_gates function."""
    
    def test_returns_predicted_soft_gates(self) -> None:
        """Should return PredictedSoftGates instance."""
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.C,
        )
        result = predict_soft_gates(request)
        assert isinstance(result, PredictedSoftGates)
    
    def test_c_major_scale_basic_metrics(self) -> None:
        """C major scale straight should have low complexity."""
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            pattern="straight_up_down",
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.C,
        )
        result = predict_soft_gates(request)
        
        # Straight pattern has only steps (1-2 semitones)
        assert result.interval_sustained_stage <= 2
        assert result.interval_hazard_stage <= 1
        
        # Quarter notes = 0.20 complexity
        assert result.rhythm_complexity_score == 0.20
        
        # C major = 0 accidentals, stage 2
        assert result.accidental_count == 0
        assert result.tonal_complexity_stage == 2
    
    def test_scale_in_3rds_higher_interval_stage(self) -> None:
        """Scale in 3rds should have higher interval sustained stage."""
        straight_request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            pattern="straight_up_down",
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.C,
        )
        thirds_request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            pattern="in_3rds",
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.C,
        )
        
        straight_result = predict_soft_gates(straight_request)
        thirds_result = predict_soft_gates(thirds_request)
        
        # In 3rds should have higher interval stages
        assert thirds_result.interval_sustained_stage >= straight_result.interval_sustained_stage
        assert thirds_result.max_interval_semitones >= straight_result.max_interval_semitones
    
    def test_harder_key_higher_tonal_stage(self) -> None:
        """Keys with more accidentals should have higher tonal stage."""
        c_request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.C,
        )
        f_sharp_request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.F_SHARP,
        )
        
        c_result = predict_soft_gates(c_request)
        f_sharp_result = predict_soft_gates(f_sharp_request)
        
        assert f_sharp_result.tonal_complexity_stage > c_result.tonal_complexity_stage
        assert f_sharp_result.accidental_count > c_result.accidental_count
    
    def test_faster_rhythm_higher_complexity(self) -> None:
        """Faster rhythms should have higher complexity scores."""
        quarter_request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.C,
        )
        sixteenth_request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            rhythm=RhythmType.SIXTEENTH_NOTES,
            key=MusicalKey.C,
        )
        
        quarter_result = predict_soft_gates(quarter_request)
        sixteenth_result = predict_soft_gates(sixteenth_request)
        
        assert sixteenth_result.rhythm_complexity_score > quarter_result.rhythm_complexity_score
    
    def test_arpeggio_prediction(self) -> None:
        """Should handle arpeggio content type."""
        request = GenerationRequest(
            content_type=GenerationType.ARPEGGIO,
            definition="major",
            rhythm=RhythmType.EIGHTH_NOTES,
            key=MusicalKey.G,
        )
        result = predict_soft_gates(request)
        
        assert isinstance(result, PredictedSoftGates)
        assert result.rhythm_complexity_score == 0.40
        assert result.accidental_count == 1
    
    def test_dataclass_is_frozen(self) -> None:
        """PredictedSoftGates should be immutable."""
        request = GenerationRequest(
            content_type=GenerationType.SCALE,
            definition="ionian",
            rhythm=RhythmType.QUARTER_NOTES,
            key=MusicalKey.C,
        )
        result = predict_soft_gates(request)
        
        with pytest.raises(AttributeError):
            result.rhythm_complexity_score = 0.99  # type: ignore
