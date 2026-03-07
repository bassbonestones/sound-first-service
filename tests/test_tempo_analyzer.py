"""
Tests for tempo_analyzer module.

Covers:
- Single stable tempo
- Multiple tempo markings
- Accelerando sections
- Ritardando followed by a tempo
- Text-only tempo terms
- Sparse/ambiguous tempo information
- Effective BPM weighting
"""

import pytest
from typing import Optional
from app.tempo_analyzer import (
    TempoProfile, TempoRegion, TempoEvent,
    TempoSourceType, TempoChangeType,
    estimate_bpm_from_term, classify_tempo_term,
    parse_tempo_events, build_tempo_regions,
    calculate_effective_bpm, build_tempo_profile,
    calculate_tempo_speed_difficulty, calculate_tempo_control_difficulty,
    calculate_tempo_difficulty_metrics, get_legacy_tempo_bpm,
    TEMPO_TERM_BPM,
)

try:
    from music21 import converter, stream, tempo, note, meter
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def simple_score_no_tempo():
    """Create a simple score with no tempo markings."""
    if not MUSIC21_AVAILABLE:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    m.append(meter.TimeSignature('4/4'))
    m.append(note.Note('C4', quarterLength=4))
    p.append(m)
    s.append(p)
    return s


@pytest.fixture
def score_with_single_tempo():
    """Create a score with one tempo marking (Allegro = 132)."""
    if not MUSIC21_AVAILABLE:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    
    m1 = stream.Measure(number=1)
    m1.append(meter.TimeSignature('4/4'))
    # Add metronome mark
    mm = tempo.MetronomeMark(number=132, text="Allegro")
    m1.append(mm)
    m1.append(note.Note('C4', quarterLength=4))
    p.append(m1)
    
    m2 = stream.Measure(number=2)
    m2.append(note.Note('D4', quarterLength=4))
    p.append(m2)
    
    s.append(p)
    return s


@pytest.fixture
def score_with_multiple_tempos():
    """
    Create a score where the last tempo is NOT representative.
    Measures 1-10: Allegro (132)
    Measures 11-12: Presto (184) - only 2 measures
    """
    if not MUSIC21_AVAILABLE:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    
    # First 10 measures - Allegro
    m1 = stream.Measure(number=1)
    m1.append(meter.TimeSignature('4/4'))
    mm1 = tempo.MetronomeMark(number=132, text="Allegro")
    m1.append(mm1)
    m1.append(note.Note('C4', quarterLength=4))
    p.append(m1)
    
    for i in range(2, 11):
        m = stream.Measure(number=i)
        m.append(note.Note('D4', quarterLength=4))
        p.append(m)
    
    # Last 2 measures - Presto
    m11 = stream.Measure(number=11)
    mm2 = tempo.MetronomeMark(number=184, text="Presto")
    m11.append(mm2)
    m11.append(note.Note('E4', quarterLength=4))
    p.append(m11)
    
    m12 = stream.Measure(number=12)
    m12.append(note.Note('F4', quarterLength=4))
    p.append(m12)
    
    s.append(p)
    return s


@pytest.fixture
def score_with_rit_a_tempo():
    """
    Create score with ritardando followed by a tempo.
    Measures 1-4: Allegro (120)
    Measures 5-6: rit.
    Measures 7-8: a tempo
    """
    if not MUSIC21_AVAILABLE:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    
    # Allegro start
    m1 = stream.Measure(number=1)
    m1.append(meter.TimeSignature('4/4'))
    mm1 = tempo.MetronomeMark(number=120, text="Allegro")
    m1.append(mm1)
    m1.append(note.Note('C4', quarterLength=4))
    p.append(m1)
    
    for i in range(2, 5):
        m = stream.Measure(number=i)
        m.append(note.Note('D4', quarterLength=4))
        p.append(m)
    
    # Ritardando
    m5 = stream.Measure(number=5)
    tt = tempo.TempoText("rit.")
    m5.insert(0, tt)
    m5.append(note.Note('E4', quarterLength=4))
    p.append(m5)
    
    m6 = stream.Measure(number=6)
    m6.append(note.Note('F4', quarterLength=4))
    p.append(m6)
    
    # A tempo
    m7 = stream.Measure(number=7)
    at = tempo.TempoText("a tempo")
    m7.insert(0, at)
    m7.append(note.Note('G4', quarterLength=4))
    p.append(m7)
    
    m8 = stream.Measure(number=8)
    m8.append(note.Note('A4', quarterLength=4))
    p.append(m8)
    
    s.append(p)
    return s


@pytest.fixture
def score_with_accelerando():
    """
    Create score with accelerando section.
    Measures 1-2: Andante (88)
    Measures 3-4: accel.
    Measures 5-6: Allegro (138)
    """
    if not MUSIC21_AVAILABLE:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    
    # Andante
    m1 = stream.Measure(number=1)
    m1.append(meter.TimeSignature('4/4'))
    mm1 = tempo.MetronomeMark(number=88, text="Andante")
    m1.append(mm1)
    m1.append(note.Note('C4', quarterLength=4))
    p.append(m1)
    
    m2 = stream.Measure(number=2)
    m2.append(note.Note('D4', quarterLength=4))
    p.append(m2)
    
    # Accelerando
    m3 = stream.Measure(number=3)
    tt = tempo.TempoText("accelerando")
    m3.insert(0, tt)
    m3.append(note.Note('E4', quarterLength=4))
    p.append(m3)
    
    m4 = stream.Measure(number=4)
    m4.append(note.Note('F4', quarterLength=4))
    p.append(m4)
    
    # Allegro
    m5 = stream.Measure(number=5)
    mm2 = tempo.MetronomeMark(number=138, text="Allegro")
    m5.append(mm2)
    m5.append(note.Note('G4', quarterLength=4))
    p.append(m5)
    
    m6 = stream.Measure(number=6)
    m6.append(note.Note('A4', quarterLength=4))
    p.append(m6)
    
    s.append(p)
    return s


@pytest.fixture
def score_text_only_tempo():
    """
    Create score with only text tempo terms (no explicit BPM).
    """
    if not MUSIC21_AVAILABLE:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    
    m1 = stream.Measure(number=1)
    m1.append(meter.TimeSignature('4/4'))
    # TempoText without BPM
    tt = tempo.TempoText("Moderato")
    m1.insert(0, tt)
    m1.append(note.Note('C4', quarterLength=4))
    p.append(m1)
    
    for i in range(2, 5):
        m = stream.Measure(number=i)
        m.append(note.Note('D4', quarterLength=4))
        p.append(m)
    
    s.append(p)
    return s


# =============================================================================
# UNIT TESTS: HELPER FUNCTIONS
# =============================================================================

class TestEstimateBPMFromTerm:
    """Tests for estimate_bpm_from_term function."""
    
    def test_exact_term_match(self):
        """Should recognize exact tempo terms."""
        bpm, is_approx = estimate_bpm_from_term("allegro")
        assert bpm == 138  # from TEMPO_TERM_BPM
        assert is_approx is True
    
    def test_case_insensitive(self):
        """Should be case insensitive."""
        bpm1, _ = estimate_bpm_from_term("ALLEGRO")
        bpm2, _ = estimate_bpm_from_term("Allegro")
        bpm3, _ = estimate_bpm_from_term("allegro")
        assert bpm1 == bpm2 == bpm3
    
    def test_partial_match(self):
        """Should match terms embedded in longer text."""
        bpm, _ = estimate_bpm_from_term("Allegro ma non troppo")
        assert bpm == 138  # allegro found
    
    def test_unknown_term_returns_none(self):
        """Unknown terms should return None."""
        bpm, is_approx = estimate_bpm_from_term("gibberish")
        assert bpm is None
        assert is_approx is False
    
    def test_all_standard_terms_mapped(self):
        """All standard tempo terms should have mappings."""
        for term in ["largo", "lento", "adagio", "andante", "moderato", 
                     "allegretto", "allegro", "vivace", "presto", "prestissimo"]:
            bpm, _ = estimate_bpm_from_term(term)
            assert bpm is not None, f"Term '{term}' should have BPM mapping"


class TestClassifyTempoTerm:
    """Tests for classify_tempo_term function."""
    
    def test_accelerando_variations(self):
        """Should recognize accelerando variations."""
        for text in ["accelerando", "accel.", "accel", "stringendo"]:
            ct = classify_tempo_term(text)
            assert ct == TempoChangeType.ACCELERANDO, f"'{text}' should be accelerando"
    
    def test_ritardando_variations(self):
        """Should recognize ritardando variations."""
        for text in ["ritardando", "rit.", "rit", "rallentando", "rall."]:
            ct = classify_tempo_term(text)
            assert ct == TempoChangeType.RITARDANDO, f"'{text}' should be ritardando"
    
    def test_a_tempo_variations(self):
        """Should recognize a tempo variations."""
        for text in ["a tempo", "tempo primo", "tempo I"]:
            ct = classify_tempo_term(text)
            assert ct == TempoChangeType.A_TEMPO, f"'{text}' should be a_tempo"
    
    def test_rubato(self):
        """Should recognize rubato."""
        ct = classify_tempo_term("tempo rubato")
        assert ct == TempoChangeType.RUBATO
    
    def test_non_modifier_returns_none(self):
        """Non-modifier terms should return None."""
        ct = classify_tempo_term("Allegro")
        assert ct is None


# =============================================================================
# UNIT TESTS: REGION BUILDING
# =============================================================================

class TestBuildTempoRegions:
    """Tests for build_tempo_regions function."""
    
    def test_empty_events_creates_default_region(self):
        """No events should create one default region."""
        regions = build_tempo_regions([], total_measures=10)
        assert len(regions) == 1
        assert regions[0].source_type == TempoSourceType.DEFAULT
        assert regions[0].start_measure == 1
        assert regions[0].end_measure == 10
        assert regions[0].bpm is None
    
    def test_single_event_spans_whole_piece(self):
        """Single tempo event should span the whole piece."""
        event = TempoEvent(
            measure_number=1,
            offset_in_measure=0,
            bpm=120,
            text="Allegro",
            source_type=TempoSourceType.METRONOME_MARK,
            change_type=TempoChangeType.INITIAL,
        )
        regions = build_tempo_regions([event], total_measures=8)
        assert len(regions) == 1
        assert regions[0].start_measure == 1
        assert regions[0].end_measure == 8
        assert regions[0].bpm == 120
    
    def test_multiple_events_create_multiple_regions(self):
        """Multiple events should create multiple regions."""
        events = [
            TempoEvent(1, 0, 100, "Andante", TempoSourceType.METRONOME_MARK, TempoChangeType.INITIAL),
            TempoEvent(5, 0, 140, "Allegro", TempoSourceType.METRONOME_MARK, TempoChangeType.SUDDEN_CHANGE),
        ]
        regions = build_tempo_regions(events, total_measures=8)
        assert len(regions) == 2
        assert regions[0].end_measure == 4
        assert regions[1].start_measure == 5
        assert regions[1].end_measure == 8


class TestCalculateEffectiveBPM:
    """Tests for calculate_effective_bpm function."""
    
    def test_single_region_returns_that_bpm(self):
        """Single region should return its BPM."""
        regions = [TempoRegion(1, 10, 120, 120, 120, TempoSourceType.METRONOME_MARK, TempoChangeType.INITIAL)]
        assert calculate_effective_bpm(regions) == 120
    
    def test_weighted_by_measure_span(self):
        """Longer regions should contribute more to effective BPM."""
        regions = [
            TempoRegion(1, 10, 100, 100, 100, TempoSourceType.METRONOME_MARK, TempoChangeType.INITIAL),  # 10 measures
            TempoRegion(11, 12, 200, 200, 200, TempoSourceType.METRONOME_MARK, TempoChangeType.SUDDEN_CHANGE),  # 2 measures
        ]
        effective = calculate_effective_bpm(regions)
        # (100*10 + 200*2) / 12 = 1400/12 = 116.67 ≈ 117
        assert effective == 117
        # NOT a simple average of (100+200)/2 = 150
        assert effective != 150
    
    def test_no_bpm_regions_returns_none(self):
        """All null BPM regions should return None."""
        regions = [TempoRegion(1, 10, None, None, None, TempoSourceType.DEFAULT, TempoChangeType.INITIAL)]
        assert calculate_effective_bpm(regions) is None


# =============================================================================
# INTEGRATION TESTS: FULL PROFILE BUILDING
# =============================================================================

class TestBuildTempoProfile:
    """Integration tests for build_tempo_profile."""
    
    def test_no_tempo_info(self, simple_score_no_tempo):
        """Score with no tempo should have null BPM values."""
        profile = build_tempo_profile(simple_score_no_tempo)
        
        assert profile.base_bpm is None
        assert profile.effective_bpm is None
        assert profile.min_bpm is None
        assert profile.max_bpm is None
        assert profile.has_tempo_marking is False
        assert len(profile.tempo_regions) == 1
        assert profile.tempo_regions[0].source_type == TempoSourceType.DEFAULT
    
    def test_single_stable_tempo(self, score_with_single_tempo):
        """Score with single tempo should have consistent values."""
        profile = build_tempo_profile(score_with_single_tempo)
        
        assert profile.base_bpm == 132
        assert profile.effective_bpm == 132
        assert profile.min_bpm == 132
        assert profile.max_bpm == 132
        assert profile.tempo_change_count == 0
        assert profile.has_tempo_marking is True
        assert profile.has_accelerando is False
        assert profile.has_ritardando is False
    
    def test_multiple_tempos_weighted_correctly(self, score_with_multiple_tempos):
        """Effective BPM should weight by measure span."""
        profile = build_tempo_profile(score_with_multiple_tempos)
        
        assert profile.base_bpm == 132  # First tempo
        assert profile.max_bpm == 184  # Presto at end
        assert profile.min_bpm == 132
        
        # Effective should be weighted (10 measures Allegro, 2 measures Presto)
        # NOT simply 184 (last tempo) or (132+184)/2=158 (simple average)
        assert profile.effective_bpm is not None
        assert profile.effective_bpm < 150  # Should be closer to 132
        assert profile.effective_bpm > 132  # But slightly higher due to Presto
        
        assert profile.tempo_change_count >= 1  # At least one change
    
    def test_rit_a_tempo_detection(self, score_with_rit_a_tempo):
        """Should detect ritardando and a tempo patterns."""
        profile = build_tempo_profile(score_with_rit_a_tempo)
        
        assert profile.has_ritardando is True
        assert profile.has_a_tempo is True
        assert profile.base_bpm == 120
    
    def test_accelerando_detection(self, score_with_accelerando):
        """Should detect accelerando."""
        profile = build_tempo_profile(score_with_accelerando)
        
        assert profile.has_accelerando is True
        assert profile.min_bpm == 88  # Andante
        assert profile.max_bpm == 138  # Allegro
    
    def test_text_only_tempo_estimation(self, score_text_only_tempo):
        """Text-only tempo should estimate BPM."""
        profile = build_tempo_profile(score_text_only_tempo)
        
        assert profile.has_tempo_marking is True
        assert profile.base_bpm is not None  # Should have estimated
        # Moderato is ~112 BPM
        assert 100 <= profile.base_bpm <= 120
        
        # Should be marked approximate
        assert any(r.is_approximate for r in profile.tempo_regions)


# =============================================================================
# TESTS: DIFFICULTY METRICS
# =============================================================================

class TestTempoDifficultyMetrics:
    """Tests for tempo difficulty calculations."""
    
    def test_speed_difficulty_increases_with_bpm(self):
        """Higher BPM should increase speed difficulty."""
        slow_profile = TempoProfile(
            base_bpm=60, effective_bpm=60, min_bpm=60, max_bpm=60,
            tempo_change_count=0, has_accelerando=False, has_ritardando=False,
            has_a_tempo=False, has_rubato=False, has_sudden_change=False,
            has_tempo_marking=True, tempo_regions=[],
        )
        fast_profile = TempoProfile(
            base_bpm=180, effective_bpm=180, min_bpm=180, max_bpm=180,
            tempo_change_count=0, has_accelerando=False, has_ritardando=False,
            has_a_tempo=False, has_rubato=False, has_sudden_change=False,
            has_tempo_marking=True, tempo_regions=[],
        )
        
        slow_diff = calculate_tempo_speed_difficulty(slow_profile)
        fast_diff = calculate_tempo_speed_difficulty(fast_profile)
        
        assert fast_diff > slow_diff
    
    def test_control_difficulty_increases_with_changes(self):
        """More tempo changes should increase control difficulty."""
        stable_profile = TempoProfile(
            base_bpm=120, effective_bpm=120, min_bpm=120, max_bpm=120,
            tempo_change_count=0, has_accelerando=False, has_ritardando=False,
            has_a_tempo=False, has_rubato=False, has_sudden_change=False,
            has_tempo_marking=True, tempo_regions=[],
        )
        complex_profile = TempoProfile(
            base_bpm=120, effective_bpm=120, min_bpm=80, max_bpm=160,
            tempo_change_count=5, has_accelerando=True, has_ritardando=True,
            has_a_tempo=True, has_rubato=True, has_sudden_change=True,
            has_tempo_marking=True, tempo_regions=[],
        )
        
        stable_diff = calculate_tempo_control_difficulty(stable_profile)
        complex_diff = calculate_tempo_control_difficulty(complex_profile)
        
        assert complex_diff > stable_diff
    
    def test_no_tempo_returns_none(self):
        """No tempo info should return None difficulty."""
        profile = TempoProfile(
            base_bpm=None, effective_bpm=None, min_bpm=None, max_bpm=None,
            tempo_change_count=0, has_accelerando=False, has_ritardando=False,
            has_a_tempo=False, has_rubato=False, has_sudden_change=False,
            has_tempo_marking=False, tempo_regions=[],
        )
        
        speed = calculate_tempo_speed_difficulty(profile)
        control = calculate_tempo_control_difficulty(profile)
        
        assert speed is None
        assert control is None


# =============================================================================
# TESTS: LEGACY COMPATIBILITY
# =============================================================================

class TestLegacyCompatibility:
    """Tests for backward compatibility functions."""
    
    def test_get_legacy_tempo_bpm_prefers_effective(self):
        """Should prefer effective_bpm over base_bpm."""
        profile = TempoProfile(
            base_bpm=100, effective_bpm=120, min_bpm=100, max_bpm=140,
            tempo_change_count=2, has_accelerando=False, has_ritardando=False,
            has_a_tempo=False, has_rubato=False, has_sudden_change=False,
            has_tempo_marking=True, tempo_regions=[],
        )
        
        legacy = get_legacy_tempo_bpm(profile)
        assert legacy == 120  # effective_bpm
    
    def test_get_legacy_tempo_bpm_fallback_to_base(self):
        """Should fall back to base_bpm if effective is None."""
        profile = TempoProfile(
            base_bpm=100, effective_bpm=None, min_bpm=100, max_bpm=100,
            tempo_change_count=0, has_accelerando=False, has_ritardando=False,
            has_a_tempo=False, has_rubato=False, has_sudden_change=False,
            has_tempo_marking=True, tempo_regions=[],
        )
        
        legacy = get_legacy_tempo_bpm(profile)
        assert legacy == 100  # base_bpm
    
    def test_get_legacy_tempo_bpm_returns_none(self):
        """Should return None if both are None."""
        profile = TempoProfile(
            base_bpm=None, effective_bpm=None, min_bpm=None, max_bpm=None,
            tempo_change_count=0, has_accelerando=False, has_ritardando=False,
            has_a_tempo=False, has_rubato=False, has_sudden_change=False,
            has_tempo_marking=False, tempo_regions=[],
        )
        
        legacy = get_legacy_tempo_bpm(profile)
        assert legacy is None


# =============================================================================
# TESTS: SERIALIZATION
# =============================================================================

class TestSerialization:
    """Tests for tempo profile serialization."""
    
    def test_profile_to_dict(self, score_with_single_tempo):
        """TempoProfile should serialize to dict."""
        profile = build_tempo_profile(score_with_single_tempo)
        result = profile.to_dict()
        
        assert isinstance(result, dict)
        assert "base_bpm" in result
        assert "effective_bpm" in result
        assert "tempo_regions" in result
        assert isinstance(result["tempo_regions"], list)
    
    def test_region_serialization(self, score_with_single_tempo):
        """Tempo regions should serialize to dict."""
        profile = build_tempo_profile(score_with_single_tempo)
        result = profile.to_dict()
        
        for region in result["tempo_regions"]:
            assert "start_measure" in region
            assert "end_measure" in region
            assert "bpm" in region
            assert "source_type" in region
            assert "change_type" in region
            # Enums should be strings
            assert isinstance(region["source_type"], str)
            assert isinstance(region["change_type"], str)
