"""
Tests for tonal_calculator.py

D1 — Tonal Complexity Stage (0-5) based on chromatic vs diatonic content.
"""

import pytest

from app.calculators.tonal_calculator import calculate_tonal_complexity_stage


class TestTonalComplexityStage:
    """Tests for calculate_tonal_complexity_stage function."""

    def test_returns_tuple(self):
        """Should return (stage, raw_dict) tuple."""
        result = calculate_tonal_complexity_stage(
            pitch_class_count=5,
            accidental_count=0,
            total_note_count=20,
        )
        assert isinstance(result, tuple)
        assert len(result) == 2
        stage, raw = result
        assert isinstance(stage, int)
        assert isinstance(raw, dict)

    def test_stage_in_valid_range(self):
        """Stage should be 0-5."""
        test_cases = [
            (1, 0, 10),   # Unison
            (2, 0, 10),   # Two-note
            (5, 0, 20),   # Small diatonic
            (7, 0, 30),   # Diatonic full
            (9, 5, 20),   # Light chromatic
            (12, 20, 40), # Full chromatic
        ]
        for pitch_count, acc_count, total in test_cases:
            stage, _ = calculate_tonal_complexity_stage(
                pitch_class_count=pitch_count,
                accidental_count=acc_count,
                total_note_count=total,
            )
            assert 0 <= stage <= 5

    def test_zero_notes_returns_stage_0(self):
        """Empty content should return stage 0."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=0,
            accidental_count=0,
            total_note_count=0,
        )
        assert stage == 0
        assert raw["accidental_rate"] == 0
        assert raw["pitch_class_count"] == 0

    def test_raw_metrics_included(self):
        """Raw dict should contain all metrics."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=5,
            accidental_count=3,
            total_note_count=20,
        )
        assert "pitch_class_count" in raw
        assert "accidental_count" in raw
        assert "total_note_count" in raw
        assert "accidental_rate" in raw
        assert raw["pitch_class_count"] == 5
        assert raw["accidental_count"] == 3
        assert raw["total_note_count"] == 20
        assert raw["accidental_rate"] == 3 / 20


class TestTonalStageClassification:
    """Tests for specific stage classifications."""

    def test_stage_0_unison(self):
        """Single pitch class = stage 0 (unison)."""
        stage, _ = calculate_tonal_complexity_stage(
            pitch_class_count=1,
            accidental_count=0,
            total_note_count=10,
        )
        assert stage == 0

    def test_stage_1_two_note_neighbor(self):
        """2 pitch classes, low accidentals = stage 1."""
        stage, _ = calculate_tonal_complexity_stage(
            pitch_class_count=2,
            accidental_count=0,
            total_note_count=20,
        )
        assert stage == 1

    def test_stage_2_small_diatonic_set(self):
        """3-5 pitch classes, low accidentals = stage 2."""
        for pitch_count in [3, 4, 5]:
            stage, _ = calculate_tonal_complexity_stage(
                pitch_class_count=pitch_count,
                accidental_count=0,
                total_note_count=20,
            )
            assert stage == 2, f"pitch_count={pitch_count} should be stage 2"

    def test_stage_3_diatonic_broader(self):
        """6-7 pitch classes, low accidentals = stage 3."""
        for pitch_count in [6, 7]:
            stage, _ = calculate_tonal_complexity_stage(
                pitch_class_count=pitch_count,
                accidental_count=0,
                total_note_count=50,
            )
            assert stage == 3, f"pitch_count={pitch_count} should be stage 3"

    def test_stage_4_light_chromatic(self):
        """Higher accidental rate (≤30%) = stage 4."""
        # 20% accidentals
        stage, _ = calculate_tonal_complexity_stage(
            pitch_class_count=9,
            accidental_count=6,
            total_note_count=30,
        )
        assert stage == 4

    def test_stage_5_chromatic(self):
        """High accidental rate (>30%) = stage 5."""
        # 50% accidentals
        stage, _ = calculate_tonal_complexity_stage(
            pitch_class_count=12,
            accidental_count=25,
            total_note_count=50,
        )
        assert stage == 5


class TestAccidentalRateThresholds:
    """Tests for accidental rate boundary conditions."""

    def test_exactly_10_percent_accidentals(self):
        """10% accidentals is boundary for stages 1-3."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=5,
            accidental_count=2,
            total_note_count=20,
        )
        assert raw["accidental_rate"] == 0.10
        assert stage == 2  # 5 pitch classes, exactly 10%

    def test_just_over_10_percent_accidentals(self):
        """>10% accidentals pushes to higher stage."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=5,
            accidental_count=3,
            total_note_count=20,
        )
        assert raw["accidental_rate"] == 0.15
        assert stage == 4  # Light chromatic

    def test_exactly_30_percent_accidentals(self):
        """30% accidentals is boundary for stage 4."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=8,
            accidental_count=9,
            total_note_count=30,
        )
        assert raw["accidental_rate"] == 0.30
        assert stage == 4  # Still stage 4

    def test_just_over_30_percent_accidentals(self):
        """>30% accidentals pushes to stage 5."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=8,
            accidental_count=10,
            total_note_count=30,
        )
        assert raw["accidental_rate"] > 0.30
        assert stage == 5  # Chromatic


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_max_pitch_classes(self):
        """12 pitch classes (all chromatic notes)."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=12,
            accidental_count=0,
            total_note_count=50,
        )
        # 12 > 7, but accidentals are 0, so stage 4
        assert stage == 4
        assert raw["pitch_class_count"] == 12

    def test_all_notes_are_accidentals(self):
        """100% accidental rate."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=5,
            accidental_count=20,
            total_note_count=20,
        )
        assert raw["accidental_rate"] == 1.0
        assert stage == 5

    def test_single_note_piece(self):
        """Piece with just one note."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=1,
            accidental_count=0,
            total_note_count=1,
        )
        assert stage == 0
        assert raw["accidental_rate"] == 0

    def test_single_accidental_note(self):
        """Single note that's an accidental."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=1,
            accidental_count=1,
            total_note_count=1,
        )
        # 1 pitch class = stage 0 (unison) regardless of accidentals
        assert stage == 0
        assert raw["accidental_rate"] == 1.0

    def test_very_large_piece(self):
        """Large piece with many notes."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=7,
            accidental_count=10,
            total_note_count=1000,
        )
        assert raw["accidental_rate"] == 0.01
        assert stage == 3  # 7 pitch classes, low accidentals
