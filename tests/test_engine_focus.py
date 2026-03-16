"""
Tests for engine/focus.py

Tests for focus targeting functions.
"""

import pytest
from datetime import datetime, timedelta

from app.engine.config import EngineConfig
from app.engine.focus import compute_focus_score, select_focus_targets
from app.engine.models import FocusTarget


class TestComputeFocusScore:
    """Tests for compute_focus_score function."""

    def test_low_ema_high_badness(self):
        """Low EMA should produce high badness component."""
        now = datetime.now()
        score = compute_focus_score(
            pitch_midi=60,
            ema_score=1.0,  # Lowest
            last_attempt_at=now - timedelta(days=1),
            user_range_center=60,
            now=now
        )
        # badness = 1 - 0 = 1.0 (high)
        assert score > 0.8

    def test_high_ema_low_badness(self):
        """High EMA should produce low badness component."""
        now = datetime.now()
        score = compute_focus_score(
            pitch_midi=60,
            ema_score=5.0,  # Highest
            last_attempt_at=now - timedelta(days=1),
            user_range_center=60,
            now=now
        )
        # badness = 1 - 1.0 = 0.0 (low)
        assert score < 0.5

    def test_never_attempted_spacing(self):
        """Never attempted should get max spacing boost."""
        now = datetime.now()
        score_never = compute_focus_score(
            pitch_midi=60,
            ema_score=3.0,
            last_attempt_at=None,  # Never attempted
            user_range_center=60,
            now=now
        )
        score_recent = compute_focus_score(
            pitch_midi=60,
            ema_score=3.0,
            last_attempt_at=now - timedelta(hours=1),  # Recent
            user_range_center=60,
            now=now
        )
        assert score_never > score_recent

    def test_extreme_pitch_penalty(self):
        """Extreme pitch should get penalty."""
        now = datetime.now()
        score_center = compute_focus_score(
            pitch_midi=60,
            ema_score=3.0,
            last_attempt_at=now - timedelta(days=1),
            user_range_center=60,
            now=now
        )
        score_extreme = compute_focus_score(
            pitch_midi=84,  # 24 semitones away
            ema_score=3.0,
            last_attempt_at=now - timedelta(days=1),
            user_range_center=60,
            now=now
        )
        assert score_center > score_extreme

    def test_custom_config_extreme_factor(self):
        """Custom avoid_extremes_factor should affect penalty."""
        now = datetime.now()
        config_low = EngineConfig(avoid_extremes_factor=0.1)
        config_high = EngineConfig(avoid_extremes_factor=0.9)
        
        score_low = compute_focus_score(
            pitch_midi=84,  # Far from center
            ema_score=3.0,
            last_attempt_at=now - timedelta(days=1),
            user_range_center=60,
            now=now,
            config=config_low
        )
        score_high = compute_focus_score(
            pitch_midi=84,
            ema_score=3.0,
            last_attempt_at=now - timedelta(days=1),
            user_range_center=60,
            now=now,
            config=config_high
        )
        # Higher factor = more penalty = lower score
        assert score_low > score_high


class TestSelectFocusTargets:
    """Tests for select_focus_targets function."""

    def test_returns_top_n_targets(self):
        """Should return top N focus targets by score."""
        config = EngineConfig(focus_targets_per_material=2)
        
        pitches = [60, 67, 72]
        focus_ids = [1, 2]
        stats = {}  # All pitches have no history
        
        targets = select_focus_targets(
            material_pitches=pitches,
            focus_card_ids=focus_ids,
            pitch_focus_stats=stats,
            user_range_center=65,
            config=config
        )
        
        assert len(targets) == 2

    def test_all_combinations_scored(self):
        """Should score all pitch/focus combinations."""
        config = EngineConfig(focus_targets_per_material=10)
        
        pitches = [60, 67]
        focus_ids = [1, 2, 3]
        stats = {}
        
        targets = select_focus_targets(
            material_pitches=pitches,
            focus_card_ids=focus_ids,
            pitch_focus_stats=stats,
            user_range_center=63,
            config=config
        )
        
        # 2 pitches * 3 focus = 6 combinations
        assert len(targets) == 6

    def test_uses_pitch_focus_stats(self):
        """Should use existing stats for scoring."""
        config = EngineConfig(focus_targets_per_material=5)
        now = datetime.now()
        
        pitches = [60]
        focus_ids = [1, 2]
        # Focus 1 has low EMA (needs work), Focus 2 has high EMA (good)
        stats = {
            (60, 1): (1.5, now - timedelta(days=5)),
            (60, 2): (4.8, now - timedelta(days=1)),
        }
        
        targets = select_focus_targets(
            material_pitches=pitches,
            focus_card_ids=focus_ids,
            pitch_focus_stats=stats,
            user_range_center=60,
            config=config
        )
        
        # Focus 1 should score higher (lower EMA = more badness)
        focus_1_target = next(t for t in targets if t.focus_card_id == 1)
        focus_2_target = next(t for t in targets if t.focus_card_id == 2)
        assert focus_1_target.score > focus_2_target.score

    def test_returns_focus_target_objects(self):
        """Should return FocusTarget instances."""
        config = EngineConfig(focus_targets_per_material=1)
        
        pitches = [60]
        focus_ids = [5]
        stats = {(60, 5): (3.0, None)}
        
        targets = select_focus_targets(
            material_pitches=pitches,
            focus_card_ids=focus_ids,
            pitch_focus_stats=stats,
            user_range_center=60,
            config=config
        )
        
        assert len(targets) == 1
        assert isinstance(targets[0], FocusTarget)
        assert targets[0].pitch_midi == 60
        assert targets[0].focus_card_id == 5
        assert targets[0].ema_score == 3.0

    def test_empty_pitches_returns_empty(self):
        """Should return empty list for empty pitches."""
        targets = select_focus_targets(
            material_pitches=[],
            focus_card_ids=[1, 2],
            pitch_focus_stats={},
            user_range_center=60
        )
        assert targets == []

    def test_empty_focus_ids_returns_empty(self):
        """Should return empty list for empty focus ids."""
        targets = select_focus_targets(
            material_pitches=[60, 67],
            focus_card_ids=[],
            pitch_focus_stats={},
            user_range_center=60
        )
        assert targets == []
