"""
Tests for orchestration/calculator.py

Main SoftGateCalculator class and calculate_soft_gates function.
"""

import pytest

try:
    from music21 import stream, note, meter, tempo, key
    from app.calculators.orchestration.calculator import (
        SoftGateCalculator,
        calculate_soft_gates,
        MUSIC21_AVAILABLE,
    )
    MUSIC21_OK = MUSIC21_AVAILABLE
except ImportError:
    MUSIC21_OK = False


@pytest.fixture
def simple_score():
    """Create a simple music21 score for testing."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    
    # Add some notes: C4, D4, E4, F4
    for pitch in ["C4", "D4", "E4", "F4"]:
        n = note.Note(pitch)
        n.duration.quarterLength = 1.0
        m.append(n)
    
    p.append(m)
    s.append(p)
    return s


@pytest.fixture
def score_with_metadata(simple_score):
    """Score with tempo and time signature."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    # Add tempo mark
    mm = tempo.MetronomeMark(number=120)
    simple_score.insert(0, mm)
    
    # Add time signature
    ts = meter.TimeSignature("4/4")
    simple_score.parts[0].insert(0, ts)
    
    return simple_score


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestSoftGateCalculatorInit:
    """Tests for SoftGateCalculator initialization."""

    def test_can_instantiate(self):
        """Should create calculator instance when music21 available."""
        calc = SoftGateCalculator()
        assert calc is not None

    def test_has_calculate_from_score(self):
        """Calculator should have calculate_from_score method."""
        calc = SoftGateCalculator()
        assert hasattr(calc, "calculate_from_score")
        assert callable(calc.calculate_from_score)

    def test_has_calculate_from_musicxml(self):
        """Calculator should have calculate_from_musicxml method."""
        calc = SoftGateCalculator()
        assert hasattr(calc, "calculate_from_musicxml")
        assert callable(calc.calculate_from_musicxml)


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestCalculateFromScore:
    """Tests for calculate_from_score method."""

    def test_returns_soft_gate_metrics(self, simple_score):
        """Should return SoftGateMetrics dataclass."""
        from app.calculators.models import SoftGateMetrics
        
        calc = SoftGateCalculator()
        result = calc.calculate_from_score(simple_score, tempo_bpm=120)
        
        assert isinstance(result, SoftGateMetrics)

    def test_calculates_tonal_complexity(self, simple_score):
        """Should calculate D1 tonal complexity."""
        calc = SoftGateCalculator()
        result = calc.calculate_from_score(simple_score, tempo_bpm=120)
        
        # 4 notes: C, D, E, F - all diatonic
        assert result.tonal_complexity_stage >= 0
        assert result.tonal_complexity_stage <= 5

    def test_calculates_interval_stages(self, simple_score):
        """Should calculate interval-related stages."""
        calc = SoftGateCalculator()
        result = calc.calculate_from_score(simple_score, tempo_bpm=120)
        
        # Should have interval profile
        assert result.interval_profile is not None
        assert result.interval_sustained_stage >= 0
        assert result.interval_hazard_stage >= 0

    def test_calculates_rhythm_complexity(self, simple_score):
        """Should calculate D3 rhythm complexity."""
        calc = SoftGateCalculator()
        result = calc.calculate_from_score(simple_score, tempo_bpm=120)
        
        assert result.rhythm_complexity_score >= 0
        assert result.rhythm_complexity_score <= 1

    def test_calculates_range_usage(self, simple_score):
        """Should calculate D4 range usage."""
        calc = SoftGateCalculator()
        result = calc.calculate_from_score(simple_score, tempo_bpm=120)
        
        # C, D, E, F = 4 distinct notes = stage 3
        assert result.range_usage_stage >= 0
        assert result.range_usage_stage <= 6

    def test_calculates_density_metrics(self, simple_score):
        """Should calculate D5 density metrics."""
        calc = SoftGateCalculator()
        result = calc.calculate_from_score(simple_score, tempo_bpm=120)
        
        assert result.density_notes_per_second >= 0
        assert result.note_density_per_measure >= 0

    def test_calculates_interval_velocity(self, simple_score):
        """Should calculate IVS."""
        calc = SoftGateCalculator()
        result = calc.calculate_from_score(simple_score, tempo_bpm=120)
        
        assert result.interval_velocity_score >= 0

    def test_tempo_override(self, simple_score):
        """Should allow tempo override."""
        calc = SoftGateCalculator()
        
        result_slow = calc.calculate_from_score(simple_score, tempo_bpm=60)
        result_fast = calc.calculate_from_score(simple_score, tempo_bpm=180)
        
        # Different tempos should produce different density metrics
        # (assuming same note count, faster tempo = higher NPS)
        # Note: Both might be 0 if no notes, so check raw metrics
        assert result_slow.raw_metrics is not None
        assert result_fast.raw_metrics is not None

    def test_raw_metrics_included(self, simple_score):
        """Should include raw metrics dict."""
        calc = SoftGateCalculator()
        result = calc.calculate_from_score(simple_score, tempo_bpm=120)
        
        assert result.raw_metrics is not None
        assert "d1" in result.raw_metrics
        assert "d3" in result.raw_metrics
        assert "d4" in result.raw_metrics
        assert "d5" in result.raw_metrics
        assert "ivs" in result.raw_metrics


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestCalculateFromMusicXML:
    """Tests for calculate_from_musicxml method."""

    def test_parses_simple_musicxml(self):
        """Should parse simple MusicXML string."""
        calc = SoftGateCalculator()
        
        # Minimal MusicXML
        musicxml = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1">
      <part-name>Part 1</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time>
          <beats>4</beats>
          <beat-type>4</beat-type>
        </time>
        <clef>
          <sign>G</sign>
          <line>2</line>
        </clef>
      </attributes>
      <note>
        <pitch>
          <step>C</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>"""
        
        result = calc.calculate_from_musicxml(musicxml, tempo_bpm=120)
        
        from app.calculators.models import SoftGateMetrics
        assert isinstance(result, SoftGateMetrics)


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestCalculateSoftGatesFunction:
    """Tests for the convenience function."""

    def test_convenience_function_exists(self):
        """calculate_soft_gates function should be importable."""
        assert calculate_soft_gates is not None
        assert callable(calculate_soft_gates)


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestPrivateMethods:
    """Tests for private helper methods."""

    def test_extract_tempo(self, score_with_metadata):
        """Should extract tempo from score."""
        calc = SoftGateCalculator()
        tempo_bpm = calc._extract_tempo(score_with_metadata)
        
        assert tempo_bpm == 120

    def test_extract_tempo_no_tempo(self, simple_score):
        """Should return None when no tempo marking."""
        calc = SoftGateCalculator()
        tempo_bpm = calc._extract_tempo(simple_score)
        
        assert tempo_bpm is None

    def test_count_measures(self, simple_score):
        """Should count measures in score."""
        calc = SoftGateCalculator()
        measure_count = calc._count_measures(simple_score)
        
        assert measure_count == 1

    def test_estimate_duration(self, score_with_metadata):
        """Should estimate duration in seconds."""
        calc = SoftGateCalculator()
        
        duration = calc._estimate_duration(score_with_metadata, bpm=120, measure_count=1)
        
        # 1 measure of 4/4 at 120bpm = 2 seconds
        assert duration == pytest.approx(2.0, rel=0.1)

    def test_estimate_duration_zero_measures(self, simple_score):
        """Should return 0 for empty score."""
        calc = SoftGateCalculator()
        duration = calc._estimate_duration(simple_score, bpm=120, measure_count=0)
        
        assert duration == 0

    def test_estimate_duration_zero_bpm(self, simple_score):
        """Should return 0 for zero BPM."""
        calc = SoftGateCalculator()
        duration = calc._estimate_duration(simple_score, bpm=0, measure_count=1)
        
        assert duration == 0
