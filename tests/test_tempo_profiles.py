"""
Tests for tempo/profile.py

Tests for tempo profile building functions.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch

from app.tempo.profile import build_tempo_profile
from app.tempo.types import (
    TempoSourceType,
    TempoChangeType,
    TempoEvent,
    TempoRegion,
    TempoProfile,
)


class TestBuildTempoProfile:
    """Tests for build_tempo_profile function."""

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_empty_score(self, mock_effective, mock_regions, mock_parse):
        """Empty score should return profile with defaults."""
        # Setup mocks
        mock_score = Mock()
        mock_score.parts = []
        
        mock_parse.return_value = []
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=1,
                bpm=None,
                bpm_min=None,
                bpm_max=None,
                source_type=TempoSourceType.DEFAULT,
                change_type=TempoChangeType.INITIAL,
                text=None,
                is_approximate=True,
            )
        ]
        mock_effective.return_value = None
        
        result = build_tempo_profile(mock_score)
        
        assert isinstance(result, TempoProfile)
        assert result.base_bpm is None
        assert result.has_tempo_marking is False
        assert result.tempo_change_count == 0

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_single_tempo_event(self, mock_effective, mock_regions, mock_parse):
        """Score with single tempo event."""
        # Setup mocks
        mock_score = Mock()
        mock_part = Mock()
        mock_measure = Mock()
        mock_part.getElementsByClass.return_value = [mock_measure] * 10
        mock_score.parts = [mock_part]
        
        mock_parse.return_value = [
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
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=10,
                bpm=120,
                bpm_min=120,
                bpm_max=120,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                text="Allegro",
                is_approximate=False,
            )
        ]
        mock_effective.return_value = 120
        
        result = build_tempo_profile(mock_score)
        
        assert result.base_bpm == 120
        assert result.effective_bpm == 120
        assert result.min_bpm == 120
        assert result.max_bpm == 120
        assert result.has_tempo_marking is True
        assert result.tempo_change_count == 0
        assert result.is_fully_explicit is True

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_accelerando_detection(self, mock_effective, mock_regions, mock_parse):
        """Should detect accelerando in profile."""
        mock_score = Mock()
        mock_part = Mock()
        mock_part.getElementsByClass.return_value = [Mock()] * 20
        mock_score.parts = [mock_part]
        
        mock_parse.return_value = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0.0,
                bpm=100,
                text="Andante",
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                is_approximate=False,
            ),
            TempoEvent(
                measure_number=10,
                offset_in_measure=36.0,
                bpm=None,
                text="accel.",
                source_type=TempoSourceType.TEXT_TERM,
                change_type=TempoChangeType.ACCELERANDO,
                is_approximate=True,
            ),
        ]
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=9,
                bpm=100,
                bpm_min=100,
                bpm_max=100,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                text="Andante",
                is_approximate=False,
            ),
            TempoRegion(
                start_measure=10,
                end_measure=20,
                bpm=110,
                bpm_min=100,
                bpm_max=120,
                source_type=TempoSourceType.TEXT_TERM,
                change_type=TempoChangeType.ACCELERANDO,
                text="accel.",
                is_approximate=True,
            ),
        ]
        mock_effective.return_value = 105
        
        result = build_tempo_profile(mock_score)
        
        assert result.has_accelerando is True
        assert result.tempo_change_count >= 1

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_ritardando_detection(self, mock_effective, mock_regions, mock_parse):
        """Should detect ritardando in profile."""
        mock_score = Mock()
        mock_part = Mock()
        mock_part.getElementsByClass.return_value = [Mock()] * 16
        mock_score.parts = [mock_part]
        
        mock_parse.return_value = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0.0,
                bpm=120,
                text="Allegro",
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                is_approximate=False,
            ),
        ]
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=8,
                bpm=120,
                bpm_min=120,
                bpm_max=120,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                text="Allegro",
                is_approximate=False,
            ),
            TempoRegion(
                start_measure=9,
                end_measure=16,
                bpm=100,
                bpm_min=80,
                bpm_max=120,
                source_type=TempoSourceType.TEXT_TERM,
                change_type=TempoChangeType.RITARDANDO,
                text="rit.",
                is_approximate=True,
            ),
        ]
        mock_effective.return_value = 110
        
        result = build_tempo_profile(mock_score)
        
        assert result.has_ritardando is True

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_rubato_detection(self, mock_effective, mock_regions, mock_parse):
        """Should detect rubato in profile."""
        mock_score = Mock()
        mock_score.parts = []
        
        mock_parse.return_value = []
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=10,
                bpm=80,
                bpm_min=70,
                bpm_max=90,
                source_type=TempoSourceType.TEXT_TERM,
                change_type=TempoChangeType.RUBATO,
                text="rubato",
                is_approximate=True,
            )
        ]
        mock_effective.return_value = 80
        
        result = build_tempo_profile(mock_score)
        
        assert result.has_rubato is True

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_a_tempo_detection(self, mock_effective, mock_regions, mock_parse):
        """Should detect a tempo in profile."""
        mock_score = Mock()
        mock_score.parts = []
        
        mock_parse.return_value = []
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=8,
                bpm=100,
                bpm_min=100,
                bpm_max=100,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                text=None,
                is_approximate=False,
            ),
            TempoRegion(
                start_measure=9,
                end_measure=16,
                bpm=100,
                bpm_min=100,
                bpm_max=100,
                source_type=TempoSourceType.TEXT_TERM,
                change_type=TempoChangeType.A_TEMPO,
                text="a tempo",
                is_approximate=False,
            ),
        ]
        mock_effective.return_value = 100
        
        result = build_tempo_profile(mock_score)
        
        assert result.has_a_tempo is True

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_sudden_change_detection(self, mock_effective, mock_regions, mock_parse):
        """Should detect sudden tempo change."""
        mock_score = Mock()
        mock_score.parts = []
        
        mock_parse.return_value = []
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=10,
                bpm=60,
                bpm_min=60,
                bpm_max=60,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                text=None,
                is_approximate=False,
            ),
            TempoRegion(
                start_measure=11,
                end_measure=20,
                bpm=120,
                bpm_min=120,
                bpm_max=120,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.SUDDEN_CHANGE,
                text="Presto",
                is_approximate=False,
            ),
        ]
        mock_effective.return_value = 90
        
        result = build_tempo_profile(mock_score)
        
        assert result.has_sudden_change is True

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_min_max_bpm(self, mock_effective, mock_regions, mock_parse):
        """Should calculate min and max BPM across regions."""
        mock_score = Mock()
        mock_score.parts = []
        
        mock_parse.return_value = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0.0,
                bpm=100,
                text=None,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                is_approximate=False,
            ),
        ]
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=8,
                bpm=100,
                bpm_min=80,  # Range during accel/rit
                bpm_max=120,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                text=None,
                is_approximate=False,
            ),
        ]
        mock_effective.return_value = 100
        
        result = build_tempo_profile(mock_score)
        
        assert result.min_bpm == 80
        assert result.max_bpm == 120

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_primary_source_type(self, mock_effective, mock_regions, mock_parse):
        """Should determine primary source type from events."""
        mock_score = Mock()
        mock_score.parts = []
        
        mock_parse.return_value = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0.0,
                bpm=120,
                text="q=120",
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
            TempoEvent(
                measure_number=20,
                offset_in_measure=72.0,
                bpm=100,
                text="Moderato",
                source_type=TempoSourceType.TEXT_TERM,
                change_type=TempoChangeType.SUDDEN_CHANGE,
                is_approximate=True,
            ),
        ]
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=30,
                bpm=100,
                bpm_min=80,
                bpm_max=120,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                text=None,
                is_approximate=False,
            )
        ]
        mock_effective.return_value = 100
        
        result = build_tempo_profile(mock_score)
        
        # TEXT_TERM appears twice, so should be primary
        assert result.primary_source_type == TempoSourceType.TEXT_TERM

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_is_fully_explicit(self, mock_effective, mock_regions, mock_parse):
        """Should identify fully explicit tempo profiles."""
        mock_score = Mock()
        mock_score.parts = []
        
        mock_parse.return_value = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0.0,
                bpm=120,
                text="q=120",
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                is_approximate=False,
            ),
        ]
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=10,
                bpm=120,
                bpm_min=120,
                bpm_max=120,
                source_type=TempoSourceType.METRONOME_MARK,
                change_type=TempoChangeType.INITIAL,
                text="q=120",
                is_approximate=False,
            )
        ]
        mock_effective.return_value = 120
        
        result = build_tempo_profile(mock_score)
        
        assert result.is_fully_explicit is True

    @patch('app.tempo.profile.parse_tempo_events')
    @patch('app.tempo.profile.build_tempo_regions')
    @patch('app.tempo.profile.calculate_effective_bpm')
    def test_not_fully_explicit(self, mock_effective, mock_regions, mock_parse):
        """Should identify non-explicit tempo profiles."""
        mock_score = Mock()
        mock_score.parts = []
        
        mock_parse.return_value = [
            TempoEvent(
                measure_number=1,
                offset_in_measure=0.0,
                bpm=100,
                text="Andante",
                source_type=TempoSourceType.TEXT_TERM,
                change_type=TempoChangeType.INITIAL,
                is_approximate=True,
            ),
        ]
        mock_regions.return_value = [
            TempoRegion(
                start_measure=1,
                end_measure=10,
                bpm=100,
                bpm_min=90,
                bpm_max=110,
                source_type=TempoSourceType.TEXT_TERM,
                change_type=TempoChangeType.INITIAL,
                text="Andante",
                is_approximate=True,
            )
        ]
        mock_effective.return_value = 100
        
        result = build_tempo_profile(mock_score)
        
        assert result.is_fully_explicit is False
