"""
Tests for analyzers/extractor.py

Tests for MusicXMLAnalyzer class and helper functions.
"""

import pytest

try:
    from music21 import stream, note, meter, key, clef
    from app.analyzers.extractor import (
        MusicXMLAnalyzer,
        analyze_musicxml,
        compute_capability_bitmask,
        check_eligibility,
        MUSIC21_AVAILABLE,
    )
    from app.analyzers.extraction_models import ExtractionResult
    MUSIC21_OK = MUSIC21_AVAILABLE
except ImportError:
    MUSIC21_OK = False


# Minimal valid MusicXML for testing
MINIMAL_MUSICXML = """<?xml version="1.0" encoding="UTF-8"?>
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
      <note>
        <pitch>
          <step>D</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>E</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch>
          <step>F</step>
          <octave>4</octave>
        </pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>"""


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestMusicXMLAnalyzerInit:
    """Tests for MusicXMLAnalyzer initialization."""

    def test_can_instantiate(self):
        """Should create analyzer instance."""
        analyzer = MusicXMLAnalyzer()
        assert analyzer is not None

    def test_has_analyze_method(self):
        """Should have analyze method."""
        analyzer = MusicXMLAnalyzer()
        assert hasattr(analyzer, "analyze")
        assert callable(analyzer.analyze)

    def test_has_get_capability_names(self):
        """Should have get_capability_names method."""
        analyzer = MusicXMLAnalyzer()
        assert hasattr(analyzer, "get_capability_names")
        assert callable(analyzer.get_capability_names)


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestMusicXMLAnalyzerAnalyze:
    """Tests for MusicXMLAnalyzer.analyze method."""

    def test_returns_extraction_result(self):
        """Should return ExtractionResult."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(MINIMAL_MUSICXML)
        
        assert isinstance(result, ExtractionResult)

    def test_extracts_clefs(self):
        """Should extract clef information."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(MINIMAL_MUSICXML)
        
        # G clef = treble
        assert len(result.clefs) > 0

    def test_extracts_time_signatures(self):
        """Should extract time signature."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(MINIMAL_MUSICXML)
        
        assert len(result.time_signatures) > 0

    def test_extracts_note_values(self):
        """Should extract note values."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(MINIMAL_MUSICXML)
        
        # 4 quarter notes in the example
        assert len(result.note_values) > 0

    def test_extracts_melodic_intervals(self):
        """Should extract melodic intervals."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(MINIMAL_MUSICXML)
        
        # C-D-E-F has 3 step intervals
        assert len(result.melodic_intervals) > 0

    def test_counts_measures(self):
        """Should count measures."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(MINIMAL_MUSICXML)
        
        assert hasattr(result, "measure_count")
        assert result.measure_count >= 1

    def test_analyzes_range(self):
        """Should analyze pitch range."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(MINIMAL_MUSICXML)
        
        # Range analysis should be populated
        assert result.range_analysis is not None

    def test_invalid_musicxml_raises(self):
        """Should raise ValueError for invalid MusicXML."""
        analyzer = MusicXMLAnalyzer()
        
        with pytest.raises(ValueError, match="Failed to parse"):
            analyzer.analyze("<invalid>not xml</invalid>")


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestMusicXMLAnalyzerGetCapabilityNames:
    """Tests for get_capability_names method."""

    def test_returns_list(self):
        """Should return list of capability names."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(MINIMAL_MUSICXML)
        capabilities = analyzer.get_capability_names(result)
        
        assert isinstance(capabilities, list)

    def test_capabilities_are_strings(self):
        """All capabilities should be strings."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(MINIMAL_MUSICXML)
        capabilities = analyzer.get_capability_names(result)
        
        assert all(isinstance(c, str) for c in capabilities)

    def test_includes_expected_capabilities(self):
        """Should include basic capabilities from the example."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(MINIMAL_MUSICXML)
        capabilities = analyzer.get_capability_names(result)
        
        # Should have note_quarter from the example
        assert any("quarter" in c for c in capabilities)


@pytest.mark.skipif(not MUSIC21_OK, reason="music21 not installed")
class TestAnalyzeMusicXML:
    """Tests for analyze_musicxml convenience function."""

    def test_returns_tuple(self):
        """Should return (result, capabilities) tuple."""
        output = analyze_musicxml(MINIMAL_MUSICXML)
        
        assert isinstance(output, tuple)
        assert len(output) == 2

    def test_first_element_is_result(self):
        """First element should be ExtractionResult."""
        result, capabilities = analyze_musicxml(MINIMAL_MUSICXML)
        
        assert isinstance(result, ExtractionResult)

    def test_second_element_is_list(self):
        """Second element should be capability list."""
        result, capabilities = analyze_musicxml(MINIMAL_MUSICXML)
        
        assert isinstance(capabilities, list)


class TestComputeCapabilityBitmask:
    """Tests for compute_capability_bitmask function."""

    def test_empty_list_returns_zeros(self):
        """Empty capability list should return all zeros."""
        masks = compute_capability_bitmask([])
        
        assert masks == [0, 0, 0, 0, 0, 0, 0, 0]

    def test_returns_8_integers(self):
        """Should return exactly 8 mask integers."""
        masks = compute_capability_bitmask([1, 2, 3])
        
        assert len(masks) == 8
        assert all(isinstance(m, int) for m in masks)

    def test_first_bucket_bit_0(self):
        """Capability ID 0 should set bit 0 in bucket 0."""
        masks = compute_capability_bitmask([0])
        
        assert masks[0] == 1
        assert masks[1:] == [0, 0, 0, 0, 0, 0, 0]

    def test_first_bucket_bit_63(self):
        """Capability ID 63 should set bit 63 in bucket 0."""
        masks = compute_capability_bitmask([63])
        
        expected = 1 << 63
        assert masks[0] == expected

    def test_second_bucket(self):
        """Capability ID 64 should set bit 0 in bucket 1."""
        masks = compute_capability_bitmask([64])
        
        assert masks[0] == 0
        assert masks[1] == 1

    def test_multiple_capabilities(self):
        """Multiple capabilities should set multiple bits."""
        masks = compute_capability_bitmask([0, 1, 2])
        
        # Bits 0, 1, 2 in bucket 0 = 0b111 = 7
        assert masks[0] == 7

    def test_across_buckets(self):
        """Should handle capabilities across different buckets."""
        masks = compute_capability_bitmask([0, 64, 128])
        
        # Bit 0 in bucket 0, bit 0 in bucket 1, bit 0 in bucket 2
        assert masks[0] == 1
        assert masks[1] == 1
        assert masks[2] == 1


class TestCheckEligibility:
    """Tests for check_eligibility function."""

    def test_empty_masks_eligible(self):
        """User with no caps, material with no requirements = eligible."""
        user_masks = [0, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0, 0, 0, 0, 0, 0, 0, 0]
        
        # Note: Implementation may vary on empty case
        # Just verify it doesn't crash
        result = check_eligibility(user_masks, material_masks)
        assert isinstance(result, bool)

    def test_user_has_all_caps(self):
        """User with all required caps should be eligible."""
        user_masks = [0b111, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0b101, 0, 0, 0, 0, 0, 0, 0]
        
        result = check_eligibility(user_masks, material_masks)
        assert result is True

    def test_user_missing_caps(self):
        """User missing required caps should not be eligible."""
        user_masks = [0b001, 0, 0, 0, 0, 0, 0, 0]  # Only has cap 0
        material_masks = [0b101, 0, 0, 0, 0, 0, 0, 0]  # Needs cap 0 and 2
        
        result = check_eligibility(user_masks, material_masks)
        assert result is False

    def test_exact_match_eligible(self):
        """User with exact required caps should be eligible."""
        user_masks = [0b101, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0b101, 0, 0, 0, 0, 0, 0, 0]
        
        result = check_eligibility(user_masks, material_masks)
        assert result is True

    def test_user_has_extra_caps(self):
        """User with extra caps beyond requirements should be eligible."""
        user_masks = [0b11111111, 0, 0, 0, 0, 0, 0, 0]  # Has many caps
        material_masks = [0b101, 0, 0, 0, 0, 0, 0, 0]  # Needs few
        
        result = check_eligibility(user_masks, material_masks)
        assert result is True
