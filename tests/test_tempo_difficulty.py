"""
Tests for tempo/difficulty.py

Tests for tempo difficulty metric calculations.
"""

import pytest

from app.tempo.types import TempoProfile, TempoSourceType
from app.tempo.difficulty import (
    calculate_tempo_speed_difficulty,
    calculate_tempo_control_difficulty,
    calculate_tempo_difficulty_metrics,
)


def make_profile(**kwargs) -> TempoProfile:
    """Helper to create TempoProfile with sensible defaults."""
    defaults = {
        'base_bpm': None,
        'effective_bpm': None,
        'min_bpm': None,
        'max_bpm': None,
        'tempo_change_count': 0,
        'has_accelerando': False,
        'has_ritardando': False,
        'has_a_tempo': False,
        'has_rubato': False,
        'has_sudden_change': False,
        'has_tempo_marking': True,
    }
    defaults.update(kwargs)
    return TempoProfile(**defaults)


class TestCalculateTempoSpeedDifficulty:
    """Tests for calculate_tempo_speed_difficulty function."""

    def test_no_bpm_returns_none(self):
        """Should return None if no effective BPM."""
        profile = make_profile(effective_bpm=None)
        result = calculate_tempo_speed_difficulty(profile)
        assert result is None

    def test_minimum_bpm_zero_difficulty(self):
        """40 BPM should be approximately 0 difficulty."""
        profile = make_profile(effective_bpm=40)
        result = calculate_tempo_speed_difficulty(profile)
        assert result == pytest.approx(0.0, abs=0.05)

    def test_maximum_bpm_full_difficulty(self):
        """200 BPM should be approximately 1.0 difficulty."""
        profile = make_profile(effective_bpm=200, max_bpm=200)
        result = calculate_tempo_speed_difficulty(profile)
        assert result > 0.8

    def test_moderate_tempo(self):
        """120 BPM (moderate) should be mid-range difficulty."""
        profile = make_profile(effective_bpm=120)
        result = calculate_tempo_speed_difficulty(profile)
        # (120-40)/(200-40) ≈ 0.5
        assert 0.3 < result < 0.7

    def test_max_bpm_boost(self):
        """Higher max BPM should boost difficulty."""
        profile_no_max = make_profile(effective_bpm=100, max_bpm=100)
        profile_high_max = make_profile(effective_bpm=100, max_bpm=150)
        
        result_no_max = calculate_tempo_speed_difficulty(profile_no_max)
        result_high_max = calculate_tempo_speed_difficulty(profile_high_max)
        
        assert result_high_max > result_no_max

    def test_clamped_to_0_1(self):
        """Result should be clamped to [0, 1]."""
        profile_low = make_profile(effective_bpm=20)
        profile_high = make_profile(effective_bpm=300, max_bpm=300)
        
        assert calculate_tempo_speed_difficulty(profile_low) >= 0.0
        assert calculate_tempo_speed_difficulty(profile_high) <= 1.0

    def test_result_rounded(self):
        """Result should be rounded to 3 decimal places."""
        profile = make_profile(effective_bpm=123)
        result = calculate_tempo_speed_difficulty(profile)
        
        # Check it's rounded (3 decimal places)
        assert result == round(result, 3)


class TestCalculateTempoControlDifficulty:
    """Tests for calculate_tempo_control_difficulty function."""

    def test_no_marking_returns_none(self):
        """Should return None if no tempo marking."""
        profile = make_profile(has_tempo_marking=False)
        result = calculate_tempo_control_difficulty(profile)
        assert result is None

    def test_no_changes_zero_difficulty(self):
        """No tempo changes should be low difficulty."""
        profile = make_profile(tempo_change_count=0)
        result = calculate_tempo_control_difficulty(profile)
        assert result == 0.0

    def test_changes_increase_difficulty(self):
        """More tempo changes should increase difficulty."""
        profile_few = make_profile(tempo_change_count=1)
        profile_many = make_profile(tempo_change_count=5)
        
        result_few = calculate_tempo_control_difficulty(profile_few)
        result_many = calculate_tempo_control_difficulty(profile_many)
        
        assert result_many > result_few

    def test_accelerando_adds_difficulty(self):
        """Accelerando should add to difficulty."""
        profile_no = make_profile(has_accelerando=False)
        profile_yes = make_profile(has_accelerando=True)
        
        assert calculate_tempo_control_difficulty(profile_yes) > \
               calculate_tempo_control_difficulty(profile_no)

    def test_ritardando_adds_difficulty(self):
        """Ritardando should add to difficulty."""
        profile_no = make_profile(has_ritardando=False)
        profile_yes = make_profile(has_ritardando=True)
        
        assert calculate_tempo_control_difficulty(profile_yes) > \
               calculate_tempo_control_difficulty(profile_no)

    def test_rubato_adds_difficulty(self):
        """Rubato should add significant difficulty."""
        profile_no = make_profile(has_rubato=False)
        profile_yes = make_profile(has_rubato=True)
        
        diff_yes = calculate_tempo_control_difficulty(profile_yes)
        diff_no = calculate_tempo_control_difficulty(profile_no)
        
        assert diff_yes > diff_no
        assert diff_yes - diff_no >= 0.1  # Rubato adds at least 0.2

    def test_a_tempo_adds_difficulty(self):
        """A tempo returns should add difficulty."""
        profile_no = make_profile(has_a_tempo=False)
        profile_yes = make_profile(has_a_tempo=True)
        
        assert calculate_tempo_control_difficulty(profile_yes) > \
               calculate_tempo_control_difficulty(profile_no)

    def test_sudden_change_adds_difficulty(self):
        """Sudden tempo changes should add difficulty."""
        profile_no = make_profile(has_sudden_change=False)
        profile_yes = make_profile(has_sudden_change=True)
        
        assert calculate_tempo_control_difficulty(profile_yes) > \
               calculate_tempo_control_difficulty(profile_no)

    def test_clamped_to_0_1(self):
        """Result should be clamped to [0, 1]."""
        profile = make_profile(
            tempo_change_count=10,
            has_accelerando=True,
            has_ritardando=True,
            has_a_tempo=True,
            has_rubato=True,
            has_sudden_change=True
        )
        result = calculate_tempo_control_difficulty(profile)
        assert result <= 1.0


class TestCalculateTempoDifficultyMetrics:
    """Tests for calculate_tempo_difficulty_metrics function."""

    def test_returns_metrics_object(self):
        """Should return TempoDifficultyMetrics object."""
        profile = make_profile(effective_bpm=100)
        from app.tempo.types import TempoDifficultyMetrics
        
        result = calculate_tempo_difficulty_metrics(profile)
        
        assert isinstance(result, TempoDifficultyMetrics)

    def test_includes_both_scores(self):
        """Should include both speed and control difficulty."""
        profile = make_profile(effective_bpm=120, tempo_change_count=2)
        
        result = calculate_tempo_difficulty_metrics(profile)
        
        assert result.tempo_speed_difficulty is not None
        assert result.tempo_control_difficulty is not None

    def test_includes_raw_metrics(self):
        """Should include raw metrics for debugging."""
        profile = make_profile(
            base_bpm=100,
            effective_bpm=120,
            min_bpm=80,
            max_bpm=140,
            tempo_change_count=3,
            has_accelerando=True,
            has_ritardando=False,
            has_rubato=True
        )
        
        result = calculate_tempo_difficulty_metrics(profile)
        
        assert result.raw_metrics['base_bpm'] == 100
        assert result.raw_metrics['effective_bpm'] == 120
        assert result.raw_metrics['tempo_change_count'] == 3
        assert result.raw_metrics['has_accelerando'] is True
        assert result.raw_metrics['has_rubato'] is True

    def test_handles_missing_bpm(self):
        """Should handle profile with no BPM."""
        profile = make_profile(effective_bpm=None)
        
        result = calculate_tempo_difficulty_metrics(profile)
        
        assert result.tempo_speed_difficulty is None
