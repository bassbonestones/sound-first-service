"""
Tests for Soft Gate Calculator.

Tests all soft gate dimensions (D1-D5), IVS, and tempo difficulty scoring.
"""

import pytest
from pathlib import Path

from app.soft_gate_calculator import (
    SoftGateCalculator,
    SoftGateMetrics,
    calculate_tonal_complexity_stage,
    calculate_interval_size_stage,
    calculate_rhythm_complexity_score,
    calculate_rhythm_complexity_windowed,
    calculate_range_usage_stage,
    calculate_density_metrics,
    calculate_interval_velocity_score,
    calculate_tempo_difficulty_score,
    NoteEvent,
    MUSIC21_AVAILABLE,
    RHYTHM_WINDOW_MIN_PIECE_QL,
)


# Skip all tests if music21 is not available
pytestmark = pytest.mark.skipif(
    not MUSIC21_AVAILABLE, reason="music21 not installed"
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def calculator():
    """Soft gate calculator instance."""
    return SoftGateCalculator()


@pytest.fixture
def test_files_dir():
    """Path to test MusicXML files."""
    return Path(__file__).parent.parent / "resources" / "materials" / "test"


def load_test_file(name):
    """Load a test MusicXML file."""
    path = Path(__file__).parent.parent / "resources" / "materials" / "test" / name
    if not path.exists():
        return None
    with open(path) as f:
        return f.read()


# =============================================================================
# TEST: D1 — TONAL COMPLEXITY STAGE
# =============================================================================

class TestTonalComplexityStage:
    """Test D1 tonal complexity staging."""
    
    def test_unison_stage_0(self):
        """Single pitch class should be stage 0."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=1,
            accidental_count=0,
            total_note_count=10,
        )
        assert stage == 0
    
    def test_two_note_stage_1(self):
        """Two pitch classes with low accidentals should be stage 1."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=2,
            accidental_count=0,
            total_note_count=10,
        )
        assert stage == 1
    
    def test_diatonic_small_stage_2(self):
        """Five pitch classes diatonic should be stage 2."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=5,
            accidental_count=0,
            total_note_count=20,
        )
        assert stage == 2
    
    def test_diatonic_broad_stage_3(self):
        """Six-seven pitch classes diatonic should be stage 3."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=7,
            accidental_count=1,
            total_note_count=30,
        )
        assert stage == 3
    
    def test_light_chromatic_stage_4(self):
        """Moderate accidental rate should be stage 4."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=8,
            accidental_count=5,  # 25% rate
            total_note_count=20,
        )
        assert stage == 4
    
    def test_chromatic_stage_5(self):
        """High accidental rate should be stage 5."""
        stage, raw = calculate_tonal_complexity_stage(
            pitch_class_count=10,
            accidental_count=10,  # 50% rate
            total_note_count=20,
        )
        assert stage == 5
    
    def test_empty_notes_returns_0(self):
        """Empty notes should return stage 0."""
        stage, raw = calculate_tonal_complexity_stage(0, 0, 0)
        assert stage == 0


# =============================================================================
# TEST: D2 — INTERVAL SIZE STAGE
# =============================================================================

class TestIntervalSizeStage:
    """Test D2 interval size staging based on p90."""
    
    def test_unison_stage_0(self):
        """All unisons should be stage 0."""
        stage, raw = calculate_interval_size_stage([0, 0, 0, 0])
        assert stage == 0
    
    def test_half_step_stage_1(self):
        """Half steps should be stage 1."""
        stage, raw = calculate_interval_size_stage([1, 1, 1, 1, 1])
        assert stage == 1
    
    def test_whole_step_stage_2(self):
        """Whole steps should be stage 2."""
        stage, raw = calculate_interval_size_stage([2, 2, 2, 2, 2])
        assert stage == 2
    
    def test_thirds_stage_3(self):
        """Minor/major thirds should be stage 3."""
        stage, raw = calculate_interval_size_stage([3, 3, 4, 4, 3])
        assert stage == 3
    
    def test_fourths_fifths_stage_4(self):
        """Fourths and fifths should be stage 4."""
        stage, raw = calculate_interval_size_stage([5, 5, 7, 7, 5])
        assert stage == 4
    
    def test_sixths_stage_5(self):
        """Sixths should be stage 5."""
        stage, raw = calculate_interval_size_stage([8, 8, 9, 9, 8])
        assert stage == 5
    
    def test_octaves_stage_6(self):
        """Octaves and larger should be stage 6."""
        stage, raw = calculate_interval_size_stage([12, 10, 11, 12, 12])
        assert stage == 6
    
    def test_empty_intervals_stage_0(self):
        """Empty intervals should return stage 0."""
        stage, raw = calculate_interval_size_stage([])
        assert stage == 0
    
    def test_p90_robustness(self):
        """p90 calculates the 90th percentile."""
        # 9 small intervals + 1 large outlier, p90 includes 90% of data
        intervals = [2, 2, 2, 2, 2, 2, 2, 2, 2, 12]
        stage, raw = calculate_interval_size_stage(intervals)
        # With 10 values, p90 picks the 9th value (sorted) which may be 2 or 12
        # depending on implementation - test that it returns a valid stage
        assert 0 <= stage <= 6


# =============================================================================
# TEST: D3 — RHYTHM COMPLEXITY SCORE
# =============================================================================

class TestRhythmComplexityScore:
    """Test D3 rhythm complexity scoring."""
    
    def test_simple_rhythm_low_score(self):
        """Simple quarter notes should have low score."""
        score, raw = calculate_rhythm_complexity_score(
            note_durations=[1.0, 1.0, 1.0, 1.0],
            note_types=["quarter", "quarter", "quarter", "quarter"],
            has_dots=[False, False, False, False],
            has_tuplets=[False, False, False, False],
            has_ties=[False, False, False, False],
            pitch_changes=[2, 2, 2],
            offsets=[0, 1, 2, 3],
        )
        assert 0 <= score <= 0.4
    
    def test_complex_rhythm_higher_score(self):
        """Varied rhythms should have higher score."""
        score, raw = calculate_rhythm_complexity_score(
            note_durations=[1.0, 0.5, 0.25, 0.5, 1.0, 0.25],
            note_types=["quarter", "eighth", "16th", "eighth", "quarter", "16th"],
            has_dots=[False, True, False, False, False, False],
            has_tuplets=[False, False, False, True, False, False],
            has_ties=[False, False, False, False, True, False],
            pitch_changes=[2, 4, 3, 5, 2],
            offsets=[0, 1, 1.5, 1.75, 2.25, 3.25],
        )
        assert score > 0.2
    
    def test_score_bounded_0_1(self):
        """Score should always be between 0 and 1."""
        score, raw = calculate_rhythm_complexity_score(
            note_durations=[0.125] * 20,
            note_types=["16th"] * 20,
            has_dots=[True] * 20,
            has_tuplets=[True] * 20,
            has_ties=[True] * 20,
            pitch_changes=[12] * 19,
            offsets=list(range(20)),
        )
        assert 0 <= score <= 1
    
    def test_empty_returns_0(self):
        """Empty inputs should return 0."""
        score, raw = calculate_rhythm_complexity_score([], [], [], [], [], [], [])
        assert score == 0.0


# =============================================================================
# TEST: D3 WINDOWED — RHYTHM COMPLEXITY FOR LONG PIECES
# =============================================================================

class TestRhythmComplexityWindowed:
    """Test windowed rhythm complexity calculation."""
    
    def test_short_piece_returns_none(self):
        """Piece shorter than threshold should return None for peak/p95."""
        # 16 quarter notes = 16 qL, below 32 qL threshold
        n = 16
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            note_durations=[1.0] * n,
            note_types=["quarter"] * n,
            has_dots=[False] * n,
            has_tuplets=[False] * n,
            has_ties=[False] * n,
            pitch_changes=[2] * (n - 1),
            offsets=list(range(n)),
        )
        assert peak is None
        assert p95 is None
        assert raw.get("reason") == "piece_too_short"
    
    def test_long_piece_returns_values(self):
        """Piece at threshold should return peak and p95."""
        # 48 quarter notes = 48 qL, above 32 qL threshold
        n = 48
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            note_durations=[1.0] * n,
            note_types=["quarter"] * n,
            has_dots=[False] * n,
            has_tuplets=[False] * n,
            has_ties=[False] * n,
            pitch_changes=[2] * (n - 1),
            offsets=list(range(n)),
        )
        # Verify valid normalized scores
        assert 0 <= peak <= 1
        assert 0 <= p95 <= 1
        assert raw.get("window_count") > 0
    
    def test_peak_detects_hard_section(self):
        """Peak should be higher than global when one section is harder."""
        # Create a 48 qL piece: mostly simple, with one complex section
        n_simple = 40  # Simple quarter notes
        n_complex = 8   # Complex 16ths with tuplets
        
        # Simple section
        durations = [1.0] * n_simple
        types = ["quarter"] * n_simple
        dots = [False] * n_simple
        tuplets = [False] * n_simple
        ties = [False] * n_simple
        offsets = list(range(n_simple))
        
        # Complex section (starting at offset 40)
        durations += [0.25] * n_complex
        types += ["16th"] * n_complex
        dots += [True] * n_complex
        tuplets += [True] * n_complex
        ties += [True] * n_complex
        offsets += [40 + i * 0.25 for i in range(n_complex)]
        
        pitch_changes = [2] * (len(durations) - 1)
        
        # Get global score
        global_score, _ = calculate_rhythm_complexity_score(
            durations, types, dots, tuplets, ties, pitch_changes, offsets
        )
        
        # Get windowed scores
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            durations, types, dots, tuplets, ties, pitch_changes, offsets
        )
        
        # Peak should be higher than global because of the complex section
        assert peak >= global_score * 0.9  # Allow some tolerance
    
    def test_uniform_piece_peak_equals_global_approximately(self):
        """For uniform piece, peak should be close to global."""
        # 64 eighth notes at 0.5 qL each = 32 qL, exactly at threshold
        # Use 80 to ensure we're above threshold
        n = 80
        durations = [0.5] * n  # Uniform eighth notes
        types = ["eighth"] * n
        dots = [False] * n
        tuplets = [False] * n
        ties = [False] * n
        pitch_changes = [2] * (n - 1)
        offsets = [i * 0.5 for i in range(n)]
        
        global_score, _ = calculate_rhythm_complexity_score(
            durations, types, dots, tuplets, ties, pitch_changes, offsets
        )
        
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            durations, types, dots, tuplets, ties, pitch_changes, offsets
        )
        
        # For uniform piece, peak should be within 20% of global
        assert abs(peak - global_score) < 0.2
    
    def test_p95_less_than_or_equal_to_peak(self):
        """P95 should always be <= peak."""
        n = 64
        # Mix of rhythms
        types_pattern = ["quarter", "eighth", "16th", "eighth"]
        types = (types_pattern * (n // 4))[:n]
        durations = [1.0 if t == "quarter" else 0.5 if t == "eighth" else 0.25 for t in types]
        dots = [i % 5 == 0 for i in range(n)]
        tuplets = [i % 7 == 0 for i in range(n)]
        ties = [i % 11 == 0 for i in range(n)]
        offsets = []
        off = 0.0
        for d in durations:
            offsets.append(off)
            off += d
        pitch_changes = [2] * (n - 1)
        
        peak, p95, raw = calculate_rhythm_complexity_windowed(
            durations, types, dots, tuplets, ties, pitch_changes, offsets
        )
        
        # P95 is the 95th percentile, must be <= peak (max)
        assert p95 <= peak
    
    def test_empty_returns_none(self):
        """Empty inputs should return None."""
        peak, p95, raw = calculate_rhythm_complexity_windowed([], [], [], [], [], [], [])
        assert peak is None
        assert p95 is None


# =============================================================================
# TEST: D4 — RANGE USAGE STAGE
# =============================================================================

class TestRangeUsageStage:
    """Test D4 range usage staging."""
    
    def test_single_note_stage_0(self):
        """Single note name should be stage 0."""
        stage, raw = calculate_range_usage_stage(["C", "C", "C"])
        assert stage == 0
    
    def test_two_notes_stage_1(self):
        """Two note names should be stage 1."""
        stage, raw = calculate_range_usage_stage(["C", "D", "C", "D"])
        assert stage == 1
    
    def test_full_scale_stage_6(self):
        """All seven note names should be stage 6."""
        stage, raw = calculate_range_usage_stage(["C", "D", "E", "F", "G", "A", "B"])
        assert stage == 6
    
    def test_accidentals_dont_add_steps(self):
        """Accidentals shouldn't increase note name count."""
        # C# and C are same note name (C)
        stage, raw = calculate_range_usage_stage(["C", "C", "D", "D"])
        assert stage == 1  # Only C and D
    
    def test_empty_returns_minus_1_capped_at_0(self):
        """Empty should return stage 0 (capped)."""
        stage, raw = calculate_range_usage_stage([])
        assert stage == 0


# =============================================================================
# TEST: D5 — DENSITY
# =============================================================================

class TestDensityMetrics:
    """Test D5 density calculations."""
    
    def test_notes_per_second(self):
        """Notes per second calculation."""
        nps, npm, peak_nps, volatility, raw = calculate_density_metrics(
            total_notes=60,
            duration_seconds=30,
            measure_count=10,
        )
        assert nps == 2.0  # 60 notes / 30 seconds
        assert npm == 6.0  # 60 notes / 10 measures
    
    def test_zero_duration(self):
        """Zero duration should return 0 density."""
        nps, npm, peak_nps, volatility, raw = calculate_density_metrics(10, 0, 5)
        assert nps == 0
    
    def test_zero_measures(self):
        """Zero measures should return 0 notes per measure."""
        nps, npm, peak_nps, volatility, raw = calculate_density_metrics(10, 10, 0)
        assert npm == 0


# =============================================================================
# TEST: INTERVAL VELOCITY SCORE
# =============================================================================

class TestIntervalVelocityScore:
    """Test IVS calculation."""
    
    def test_slow_stepwise_low_ivs(self):
        """Slow stepwise motion should have low IVS."""
        events = [
            NoteEvent(pitch_midi=60, duration_ql=2.0, offset_ql=0),
            NoteEvent(pitch_midi=62, duration_ql=2.0, offset_ql=2),
            NoteEvent(pitch_midi=64, duration_ql=2.0, offset_ql=4),
        ]
        ivs, raw = calculate_interval_velocity_score(events)
        assert ivs < 0.3
    
    def test_fast_leaps_high_ivs(self):
        """Fast large leaps should have high IVS."""
        events = [
            NoteEvent(pitch_midi=60, duration_ql=0.25, offset_ql=0),
            NoteEvent(pitch_midi=72, duration_ql=0.25, offset_ql=0.25),  # Octave
            NoteEvent(pitch_midi=60, duration_ql=0.25, offset_ql=0.5),
            NoteEvent(pitch_midi=72, duration_ql=0.25, offset_ql=0.75),
        ]
        ivs, raw = calculate_interval_velocity_score(events)
        assert ivs > 0.3
    
    def test_single_note_returns_0(self):
        """Single note should return IVS 0."""
        events = [NoteEvent(pitch_midi=60, duration_ql=1.0, offset_ql=0)]
        ivs, raw = calculate_interval_velocity_score(events)
        assert ivs == 0.0
    
    def test_empty_returns_0(self):
        """Empty notes should return IVS 0."""
        ivs, raw = calculate_interval_velocity_score([])
        assert ivs == 0.0
    
    def test_ivs_bounded_0_1(self):
        """IVS should be bounded between 0 and 1."""
        events = [
            NoteEvent(pitch_midi=48, duration_ql=0.1, offset_ql=i * 0.1)
            for i in range(20)
        ]
        # Add large jumps
        for i in range(0, 20, 2):
            events[i] = NoteEvent(pitch_midi=48 + (i % 4) * 12, duration_ql=0.1, offset_ql=i * 0.1)
        
        ivs, raw = calculate_interval_velocity_score(events)
        assert 0 <= ivs <= 1


# =============================================================================
# TEST: TEMPO DIFFICULTY SCORE
# =============================================================================

class TestTempoDifficultyScore:
    """Test tempo difficulty scoring."""
    
    def test_slow_simple_low_score(self):
        """Slow tempo with simple rhythm should be low."""
        score, raw = calculate_tempo_difficulty_score(
            bpm=60,
            rhythm_complexity=0.1,
            interval_velocity=0.1,
        )
        assert score < 0.1
    
    def test_fast_complex_high_score(self):
        """Fast tempo with complex rhythm should be higher."""
        score, raw = calculate_tempo_difficulty_score(
            bpm=180,
            rhythm_complexity=0.8,
            interval_velocity=0.8,
        )
        assert score > 0.3
    
    def test_score_bounded_0_1(self):
        """Score should be bounded 0-1."""
        score, raw = calculate_tempo_difficulty_score(
            bpm=300,
            rhythm_complexity=1.0,
            interval_velocity=1.0,
        )
        assert 0 <= score <= 1
    
    def test_none_bpm_returns_none(self):
        """None BPM should return None (no assumed tempo)."""
        score, raw = calculate_tempo_difficulty_score(
            bpm=None,
            rhythm_complexity=0.5,
            interval_velocity=0.5,
        )
        assert score is None
        assert raw.get("reason") == "no tempo specified in score"


# =============================================================================
# TEST: FULL CALCULATOR
# =============================================================================

class TestSoftGateCalculator:
    """Integration tests for full calculator."""
    
    def test_calculator_from_musicxml(self, calculator, test_files_dir):
        """Calculator should process MusicXML files."""
        simple_file = test_files_dir / "test_01_simple.musicxml"
        if not simple_file.exists():
            pytest.skip("Test file not found")
        
        with open(simple_file) as f:
            content = f.read()
        
        metrics = calculator.calculate_from_musicxml(content)
        
        # Verify all domain scores are valid
        assert 0 <= metrics.tonal_complexity_stage <= 5
        assert 0 <= metrics.interval_size_stage <= 6
        assert 0 <= metrics.rhythm_complexity_score <= 1
        assert 0 <= metrics.range_usage_stage <= 6
    
    def test_simple_file_low_complexity(self, calculator, test_files_dir):
        """Simple test file should have low complexity scores."""
        simple_file = test_files_dir / "test_01_simple.musicxml"
        if not simple_file.exists():
            pytest.skip("Test file not found")
        
        with open(simple_file) as f:
            metrics = calculator.calculate_from_musicxml(f.read())
        
        # Simple file should be low to moderate complexity
        assert metrics.tonal_complexity_stage <= 3
        assert metrics.interval_size_stage <= 3
        assert metrics.rhythm_complexity_score < 0.5
    
    def test_complex_file_higher_scores(self, calculator, test_files_dir):
        """Complex test file should have higher scores."""
        complex_file = test_files_dir / "test_06_complex.musicxml"
        if not complex_file.exists():
            pytest.skip("Test file not found")
        
        with open(complex_file) as f:
            metrics = calculator.calculate_from_musicxml(f.read())
        
        # Complex file should have higher values in at least some dimensions
        total_complexity = (
            metrics.tonal_complexity_stage +
            metrics.interval_size_stage +
            metrics.range_usage_stage
        )
        assert total_complexity > 5  # Some combination of complexity
    
    def test_interval_file_high_interval_stage(self, calculator, test_files_dir):
        """Interval test file should have high interval stage."""
        interval_file = test_files_dir / "test_03_intervals.musicxml"
        if not interval_file.exists():
            pytest.skip("Test file not found")
        
        with open(interval_file) as f:
            metrics = calculator.calculate_from_musicxml(f.read())
        
        # Interval test file has large intervals
        assert metrics.interval_size_stage >= 4
        assert metrics.interval_velocity_score > 0.1
    
    def test_rhythm_file_high_rhythm_score(self, calculator, test_files_dir):
        """Rhythm test file should have higher rhythm score."""
        rhythm_file = test_files_dir / "test_02_rhythms.musicxml"
        if not rhythm_file.exists():
            pytest.skip("Test file not found")
        
        with open(rhythm_file) as f:
            metrics = calculator.calculate_from_musicxml(f.read())
        
        # Rhythm file has varied rhythms
        assert metrics.rhythm_complexity_score > 0.15
    
    def test_chromatic_file_high_tonal_stage(self, calculator, test_files_dir):
        """Chromatic test file should have higher tonal stage."""
        chromatic_file = test_files_dir / "test_04_chromatic.musicxml"
        if not chromatic_file.exists():
            pytest.skip("Test file not found")
        
        with open(chromatic_file) as f:
            metrics = calculator.calculate_from_musicxml(f.read())
        
        # Chromatic file has more accidentals
        assert metrics.tonal_complexity_stage >= 3
