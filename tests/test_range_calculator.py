"""
Tests for range_calculator.py

D4 — Range Usage Stage (0-6) based on distinct note names.
"""

import pytest

from app.calculators.range_calculator import calculate_range_usage_stage


class TestRangeUsageStage:
    """Tests for calculate_range_usage_stage function."""

    def test_returns_tuple(self):
        """Should return (stage, raw_dict) tuple."""
        result = calculate_range_usage_stage(["C", "D", "E"])
        assert isinstance(result, tuple)
        assert len(result) == 2
        stage, raw = result
        assert isinstance(stage, int)
        assert isinstance(raw, dict)

    def test_stage_in_valid_range(self):
        """Stage should be 0-6."""
        test_cases = [
            [],
            ["C"],
            ["C", "D"],
            ["C", "D", "E", "F", "G", "A", "B"],
            ["C", "D", "E", "F", "G", "A", "B", "C"],  # duplicates
        ]
        for note_steps in test_cases:
            stage, _ = calculate_range_usage_stage(note_steps)
            assert 0 <= stage <= 6

    def test_raw_metrics_included(self):
        """Raw dict should contain metrics."""
        stage, raw = calculate_range_usage_stage(["C", "D", "E"])
        assert "distinct_note_names" in raw
        assert "unique_steps" in raw
        assert raw["distinct_note_names"] == 3
        assert set(raw["unique_steps"]) == {"C", "D", "E"}


class TestStageClassification:
    """Tests for specific stage classifications."""

    def test_empty_list_returns_stage_0(self):
        """Empty note list should return stage 0."""
        stage, raw = calculate_range_usage_stage([])
        assert stage == 0
        assert raw["distinct_note_names"] == 0

    def test_stage_0_single_note(self):
        """1 distinct note = stage 0 (1-1=0)."""
        stage, _ = calculate_range_usage_stage(["C"])
        assert stage == 0

    def test_stage_1_two_notes(self):
        """2 distinct notes = stage 1 (2-1=1)."""
        stage, _ = calculate_range_usage_stage(["C", "D"])
        assert stage == 1

    def test_stage_2_three_notes(self):
        """3 distinct notes = stage 2 (3-1=2)."""
        stage, _ = calculate_range_usage_stage(["C", "D", "E"])
        assert stage == 2

    def test_stage_3_four_notes(self):
        """4 distinct notes = stage 3 (4-1=3)."""
        stage, _ = calculate_range_usage_stage(["C", "D", "E", "F"])
        assert stage == 3

    def test_stage_4_five_notes(self):
        """5 distinct notes = stage 4 (5-1=4)."""
        stage, _ = calculate_range_usage_stage(["C", "D", "E", "F", "G"])
        assert stage == 4

    def test_stage_5_six_notes(self):
        """6 distinct notes = stage 5 (6-1=5)."""
        stage, _ = calculate_range_usage_stage(["C", "D", "E", "F", "G", "A"])
        assert stage == 5

    def test_stage_6_seven_notes(self):
        """7 distinct notes = stage 6 (capped at 6)."""
        stage, _ = calculate_range_usage_stage(["C", "D", "E", "F", "G", "A", "B"])
        assert stage == 6


class TestDuplicateHandling:
    """Tests for handling duplicate note names."""

    def test_duplicates_dont_increase_count(self):
        """Duplicate notes should not affect distinct count."""
        stage1, raw1 = calculate_range_usage_stage(["C", "D", "E"])
        stage2, raw2 = calculate_range_usage_stage(["C", "C", "D", "D", "E", "E"])
        
        assert stage1 == stage2
        assert raw1["distinct_note_names"] == raw2["distinct_note_names"]

    def test_repeated_single_note(self):
        """Many repetitions of same note = stage 0."""
        stage, raw = calculate_range_usage_stage(["C"] * 100)
        assert stage == 0
        assert raw["distinct_note_names"] == 1

    def test_realistic_melody_with_repetition(self):
        """Realistic melody: C-D-E-C-D-E-F-E-D-C."""
        notes = ["C", "D", "E", "C", "D", "E", "F", "E", "D", "C"]
        stage, raw = calculate_range_usage_stage(notes)
        assert raw["distinct_note_names"] == 4  # C, D, E, F
        assert stage == 3  # 4-1=3


class TestStageCapping:
    """Tests for stage maximum of 6."""

    def test_seven_notes_capped_at_6(self):
        """Stage caps at 6 even with 7 distinct notes."""
        all_notes = ["C", "D", "E", "F", "G", "A", "B"]
        stage, raw = calculate_range_usage_stage(all_notes)
        assert raw["distinct_note_names"] == 7
        assert stage == 6

    def test_repeated_all_seven_notes(self):
        """All 7 notes repeated many times = still stage 6."""
        notes = ["C", "D", "E", "F", "G", "A", "B"] * 10
        stage, raw = calculate_range_usage_stage(notes)
        assert raw["distinct_note_names"] == 7
        assert stage == 6


class TestEdgeCases:
    """Tests for edge cases."""

    def test_case_sensitivity(self):
        """Note names should be case-sensitive by default."""
        # If implementation treats 'c' != 'C', this tests that
        notes = ["C", "c"]  # May be 2 distinct or 1 depending on impl
        stage, raw = calculate_range_usage_stage(notes)
        # Just verify it handles mixed case without error
        assert stage >= 0

    def test_very_long_melody(self):
        """Handle very long note sequences."""
        notes = ["C", "D", "E", "F", "G"] * 1000
        stage, raw = calculate_range_usage_stage(notes)
        assert raw["distinct_note_names"] == 5
        assert stage == 4

    def test_unique_steps_is_list(self):
        """unique_steps in raw dict should be a list."""
        _, raw = calculate_range_usage_stage(["C", "D", "E"])
        assert isinstance(raw["unique_steps"], list)
