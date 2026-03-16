"""
Tests for tempo/regions.py

Tests for tempo region building functions.
"""

import pytest

from app.tempo.regions import (
    build_tempo_regions,
    calculate_effective_bpm,
)
from app.tempo.types import (
    TempoSourceType,
    TempoChangeType,
    TempoEvent,
    TempoRegion,
)


class TestBuildTempoRegions:
    """Tests for build_tempo_regions function."""

    def test_empty_events_returns_default(self):
        """Empty events should return single default region."""
        regions = build_tempo_regions([], total_measures=10)
        
        assert len(regions) == 1
        assert regions[0].start_measure == 1
        assert regions[0].end_measure == 10
        assert regions[0].source_type == TempoSourceType.DEFAULT
        assert regions[0].change_type == TempoChangeType.INITIAL

    def test_single_event_covers_piece(self):
        """Single event should create region covering entire piece."""
        events = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0.0,
                bpm=120,
                text="Allegro",
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                is_approximate=False,
            )
        ]
        
        regions = build_tempo_regions(events, total_measures=20)
        
        assert len(regions) >= 1
        assert regions[0].bpm == 120
        assert regions[0].end_measure == 20

    def test_multiple_events_create_regions(self):
        """Multiple events should create multiple regions."""
        events = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0.0,
                bpm=120,
                text="Allegro",
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                is_approximate=False,
            ),
            TempoEvent(
                measure_number=10,
                offset_in_measure=36.0,
                bpm=80,
                text="Andante",
                source_type=TempoSourceType.TEXT_TERM,
                change_type=TempoChangeType.SUDDEN_CHANGE,
                is_approximate=True,
            ),
        ]
        
        regions = build_tempo_regions(events, total_measures=20)
        
        assert len(regions) >= 2

    def test_region_boundaries(self):
        """Region boundaries should be correct."""
        events = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0.0,
                bpm=100,
                text=None,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                is_approximate=False,
            ),
            TempoEvent(
                measure_number=5,
                offset_in_measure=16.0,
                bpm=120,
                text=None,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.SUDDEN_CHANGE,
                is_approximate=False,
            ),
        ]
        
        regions = build_tempo_regions(events, total_measures=10)
        
        # First region should end at measure 4
        assert regions[0].start_measure == 1
        assert regions[0].end_measure == 4
        
        # Second region should start at measure 5
        assert regions[1].start_measure == 5
        assert regions[1].end_measure == 10


class TestCalculateEffectiveBpm:
    """Tests for calculate_effective_bpm function."""

    def test_empty_regions_returns_none(self):
        """Empty regions should return None."""
        result = calculate_effective_bpm([])
        assert result is None

    def test_single_region(self):
        """Single region should return its BPM."""
        regions = [
            TempoRegion(
                start_measure=1,
                end_measure=10,
                bpm=100,
                bpm_min=100,
                bpm_max=100,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                text=None,
                is_approximate=False,
            )
        ]
        
        result = calculate_effective_bpm(regions)
        
        assert result == 100

    def test_weighted_average(self):
        """Should calculate weighted average by measure count."""
        regions = [
            TempoRegion(
                start_measure=1,
                end_measure=5,
                bpm=100,
                bpm_min=100,
                bpm_max=100,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                text=None,
                is_approximate=False,
            ),
            TempoRegion(
                start_measure=6,
                end_measure=10,
                bpm=120,
                bpm_min=120,
                bpm_max=120,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.SUDDEN_CHANGE,
                text=None,
                is_approximate=False,
            ),
        ]
        
        result = calculate_effective_bpm(regions)
        
        # Equal weight: (100*5 + 120*5) / 10 = 110
        assert result == 110

    def test_ignores_none_bpm(self):
        """Should ignore regions with None BPM."""
        regions = [
            TempoRegion(
                start_measure=1,
                end_measure=5,
                bpm=None,  # No BPM
                bpm_min=None,
                bpm_max=None,
                source_type=TempoSourceType.DEFAULT,
                change_type=TempoChangeType.INITIAL,
                text=None,
                is_approximate=True,
            ),
            TempoRegion(
                start_measure=6,
                end_measure=10,
                bpm=100,
                bpm_min=100,
                bpm_max=100,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.SUDDEN_CHANGE,
                text=None,
                is_approximate=False,
            ),
        ]
        
        result = calculate_effective_bpm(regions)
        
        # Should use only the region with actual BPM
        assert result == 100

    def test_all_none_returns_none(self):
        """All None BPMs should return None."""
        regions = [
            TempoRegion(
                start_measure=1,
                end_measure=10,
                bpm=None,
                bpm_min=None,
                bpm_max=None,
                source_type=TempoSourceType.DEFAULT,
                change_type=TempoChangeType.INITIAL,
                text=None,
                is_approximate=True,
            ),
        ]
        
        result = calculate_effective_bpm(regions)
        
        assert result is None


# =============================================================================
# TEMPO CHANGE HANDLING TESTS
# =============================================================================

class TestBuildTempoRegionsChanges:
    """Test build_tempo_regions with tempo changes."""
    
    def test_accelerando_sets_bpm_range(self):
        """Accelerando should set bpm_min and bpm_max based on next event."""
        events = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0,
                bpm=100,
                text="Moderato",
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.ACCELERANDO,
                is_approximate=False,
            ),
            TempoEvent(
                measure_number=5,
                offset_in_measure=0,
                bpm=132,
                text="Allegro",
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.STABLE,
                is_approximate=False,
            ),
        ]
        
        result = build_tempo_regions(events, total_measures=8)
        
        # First region should have bpm_min and bpm_max spanning the accel
        assert len(result) >= 1
        # The accelerando region should span from 100 to 132
        accel_region = result[0]
        assert accel_region.bpm_min == 100
        assert accel_region.bpm_max == 132
    
    def test_ritardando_sets_bpm_range(self):
        """Ritardando should set bpm_min and bpm_max based on next event."""
        events = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0,
                bpm=132,
                text="Allegro",
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.RITARDANDO,
                is_approximate=False,
            ),
            TempoEvent(
                measure_number=5,
                offset_in_measure=0,
                bpm=80,
                text="Andante",
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.STABLE,
                is_approximate=False,
            ),
        ]
        
        result = build_tempo_regions(events, total_measures=8)
        
        # First region should have bpm range spanning the rit
        assert len(result) >= 1
        rit_region = result[0]
        assert rit_region.bpm_min == 80
        assert rit_region.bpm_max == 132
    
    def test_a_tempo_restores_base(self):
        """A tempo event should restore to base BPM."""
        events = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0,
                bpm=120,
                text="Moderato",
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                is_approximate=False,
            ),
            TempoEvent(
                measure_number=5,
                offset_in_measure=0,
                bpm=None,  # A tempo doesn't specify BPM
                text="a tempo",
                source_type=TempoSourceType.TEXT_TERM,
                change_type=TempoChangeType.A_TEMPO,
                is_approximate=True,
            ),
        ]
        
        result = build_tempo_regions(events, total_measures=8)
        
        # Should have 2 regions, second should restore to base 120
        assert len(result) == 2
        a_tempo_region = result[1]
        assert a_tempo_region.bpm == 120  # Restored to base
    
    def test_merges_adjacent_stable_regions(self):
        """Adjacent stable regions with same BPM should be merged."""
        events = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0,
                bpm=120,
                text=None,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.STABLE,
                is_approximate=False,
            ),
            TempoEvent(
                measure_number=5,
                offset_in_measure=0,
                bpm=120,  # Same BPM
                text=None,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.STABLE,
                is_approximate=False,
            ),
        ]
        
        result = build_tempo_regions(events, total_measures=8)
        
        # Should merge into one region since both are stable at same tempo
        assert len(result) == 1
        assert result[0].start_measure == 1
        assert result[0].end_measure == 8


class TestCalculateEffectiveBpmWithRanges:
    """Test effective BPM calculation with BPM ranges."""
    
    def test_uses_midpoint_for_changing_tempo(self):
        """Should use midpoint BPM for regions with different min/max."""
        regions = [
            TempoRegion(
                start_measure=1,
                end_measure=4,
                bpm=100,
                bpm_min=80,
                bpm_max=120,  # Range spans 80-120
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.ACCELERANDO,
                text=None,
                is_approximate=False,
            ),
        ]
        
        result = calculate_effective_bpm(regions)
        
        # Should use midpoint: (80 + 120) / 2 = 100
        assert result == 100
