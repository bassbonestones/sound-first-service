"""
Tests for analyzers/pattern_analyzer.py

Tests for rhythm and melodic pattern analysis.
"""

import pytest

try:
    from music21 import stream, note
    from app.analyzers.pattern_analyzer import (
        analyze_rhythm_patterns,
        analyze_melodic_patterns,
    )
    from app.analyzers.extraction_models import (
        ExtractionResult,
        RhythmPatternAnalysis,
        MelodicPatternAnalysis,
    )
    MUSIC21_OK = True
except ImportError:
    MUSIC21_OK = False


@pytest.fixture
def repetitive_score():
    """Score with repeated rhythm pattern across measures."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    
    # 4 identical measures: quarter, quarter, quarter, quarter
    for i in range(4):
        m = stream.Measure(number=i + 1)
        for pitch in ["C4", "D4", "E4", "F4"]:
            n = note.Note(pitch)
            n.duration.quarterLength = 1.0
            m.append(n)
        p.append(m)
    
    s.append(p)
    return s


@pytest.fixture
def varied_score():
    """Score with varied rhythm patterns."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    
    # Measure 1: quarters
    m1 = stream.Measure(number=1)
    for pitch in ["C4", "D4", "E4", "F4"]:
        n = note.Note(pitch)
        n.duration.quarterLength = 1.0
        m1.append(n)
    p.append(m1)
    
    # Measure 2: eighths
    m2 = stream.Measure(number=2)
    for pitch in ["C4", "D4", "E4", "F4", "G4", "A4", "B4", "C5"]:
        n = note.Note(pitch)
        n.duration.quarterLength = 0.5
        m2.append(n)
    p.append(m2)
    
    # Measure 3: half notes
    m3 = stream.Measure(number=3)
    for pitch in ["C4", "E4"]:
        n = note.Note(pitch)
        n.duration.quarterLength = 2.0
        m3.append(n)
    p.append(m3)
    
    s.append(p)
    return s


@pytest.fixture
def melodic_pattern_score():
    """Score with repeated melodic patterns."""
    if not MUSIC21_OK:
        pytest.skip("music21 not available")
    
    s = stream.Score()
    p = stream.Part()
    m = stream.Measure(number=1)
    
    # Repeated pattern: C-D-E, C-D-E, C-D-E
    for _ in range(3):
        for pitch in ["C4", "D4", "E4"]:
            n = note.Note(pitch)
            n.duration.quarterLength = 0.5
            m.append(n)
    
    p.append(m)
    s.append(p)
    return s


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestAnalyzeRhythmPatterns:
    """Tests for analyze_rhythm_patterns function."""

    def test_creates_analysis(self, repetitive_score):
        """Should create RhythmPatternAnalysis."""
        result = ExtractionResult()
        analyze_rhythm_patterns(repetitive_score, result)
        
        assert result.rhythm_pattern_analysis is not None
        assert isinstance(result.rhythm_pattern_analysis, RhythmPatternAnalysis)

    def test_counts_measures(self, repetitive_score):
        """Should count total measures."""
        result = ExtractionResult()
        analyze_rhythm_patterns(repetitive_score, result)
        
        assert result.rhythm_pattern_analysis.total_measures == 4

    def test_repetitive_pattern_ratio(self, repetitive_score):
        """Identical measures should have high repetition ratio."""
        result = ExtractionResult()
        analyze_rhythm_patterns(repetitive_score, result)
        
        # 4 identical measures = 1 unique pattern / 4 total = 0.25 uniqueness
        assert result.rhythm_pattern_analysis.rhythm_measure_uniqueness_ratio <= 0.5
        assert result.rhythm_pattern_analysis.rhythm_measure_repetition_ratio >= 0.5

    def test_varied_pattern_ratio(self, varied_score):
        """Different measures should have higher uniqueness ratio."""
        result = ExtractionResult()
        analyze_rhythm_patterns(varied_score, result)
        
        # Each measure is different
        assert result.rhythm_pattern_analysis.unique_rhythm_patterns >= 2

    def test_tracks_pattern_counts(self, repetitive_score):
        """Should track individual pattern counts."""
        result = ExtractionResult()
        analyze_rhythm_patterns(repetitive_score, result)
        
        assert len(result.rhythm_pattern_analysis.pattern_counts) > 0

    def test_most_common_pattern(self, repetitive_score):
        """Should identify most common pattern."""
        result = ExtractionResult()
        analyze_rhythm_patterns(repetitive_score, result)
        
        assert result.rhythm_pattern_analysis.most_common_pattern is not None
        assert result.rhythm_pattern_analysis.most_common_count >= 1


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestAnalyzeMelodicPatterns:
    """Tests for analyze_melodic_patterns function."""

    def test_creates_analysis(self, melodic_pattern_score):
        """Should create MelodicPatternAnalysis."""
        result = ExtractionResult()
        analyze_melodic_patterns(melodic_pattern_score, result)
        
        assert result.melodic_pattern_analysis is not None
        assert isinstance(result.melodic_pattern_analysis, MelodicPatternAnalysis)

    def test_counts_motifs(self, melodic_pattern_score):
        """Should count total motifs analyzed."""
        result = ExtractionResult()
        analyze_melodic_patterns(melodic_pattern_score, result)
        
        assert result.melodic_pattern_analysis.total_motifs > 0

    def test_counts_unique_motifs(self, melodic_pattern_score):
        """Should count unique motif patterns."""
        result = ExtractionResult()
        analyze_melodic_patterns(melodic_pattern_score, result)
        
        assert result.melodic_pattern_analysis.unique_motifs >= 1

    def test_repeated_pattern_high_repetition(self, melodic_pattern_score):
        """Repeated melodic pattern should have high repetition."""
        result = ExtractionResult()
        analyze_melodic_patterns(melodic_pattern_score, result)
        
        # The same C-D-E pattern repeated should have high repetition
        assert result.melodic_pattern_analysis.motif_repetition_ratio >= 0.5

    def test_most_common_motif(self, melodic_pattern_score):
        """Should identify most common motif."""
        result = ExtractionResult()
        analyze_melodic_patterns(melodic_pattern_score, result)
        
        assert result.melodic_pattern_analysis.most_common_motif is not None


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestEdgeCases:
    """Tests for edge cases in pattern analysis."""

    def test_empty_score(self):
        """Empty score should not crash."""
        s = stream.Score()
        p = stream.Part()
        m = stream.Measure(number=1)
        p.append(m)
        s.append(p)
        
        result = ExtractionResult()
        analyze_rhythm_patterns(s, result)
        analyze_melodic_patterns(s, result)
        
        assert result.rhythm_pattern_analysis is not None
        assert result.melodic_pattern_analysis is not None

    def test_single_note(self):
        """Single note should not crash."""
        s = stream.Score()
        p = stream.Part()
        m = stream.Measure(number=1)
        
        n = note.Note("C4")
        m.append(n)
        p.append(m)
        s.append(p)
        
        result = ExtractionResult()
        analyze_rhythm_patterns(s, result)
        analyze_melodic_patterns(s, result)
        
        assert result.rhythm_pattern_analysis.total_measures >= 1

    def test_two_notes_melodic(self):
        """Two notes should handle interval analysis."""
        s = stream.Score()
        p = stream.Part()
        m = stream.Measure(number=1)
        
        n1 = note.Note("C4")
        n2 = note.Note("E4")
        m.append(n1)
        m.append(n2)
        p.append(m)
        s.append(p)
        
        result = ExtractionResult()
        analyze_melodic_patterns(s, result)
        
        # Only one interval = not enough for motif analysis
        assert result.melodic_pattern_analysis is not None

    def test_score_with_rests(self):
        """Rests should be handled in pattern analysis."""
        s = stream.Score()
        p = stream.Part()
        m = stream.Measure(number=1)
        
        n1 = note.Note("C4")
        r = note.Rest()
        n2 = note.Note("E4")
        m.append(n1)
        m.append(r)
        m.append(n2)
        p.append(m)
        s.append(p)
        
        result = ExtractionResult()
        analyze_rhythm_patterns(s, result)
        analyze_melodic_patterns(s, result)
        
        # Both analyses should complete
        assert result.rhythm_pattern_analysis is not None
        assert result.melodic_pattern_analysis is not None
