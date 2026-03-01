"""
Tests for MusicXML Analyzer module.

Tests the extraction of musical elements from MusicXML files and
capability mapping for the material selection system.
"""

import pytest
from app.musicxml_analyzer import (
    MusicXMLAnalyzer,
    ExtractionResult,
    IntervalInfo,
    RangeAnalysis,
    analyze_musicxml,
    compute_capability_bitmask,
    check_eligibility,
    MUSIC21_AVAILABLE,
)


# Skip all tests if music21 is not available
pytestmark = pytest.mark.skipif(
    not MUSIC21_AVAILABLE, reason="music21 not installed"
)


# =============================================================================
# TEST DATA
# =============================================================================

@pytest.fixture
def simple_musicxml():
    """Simple MusicXML with C4 whole note in 4/4 time."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Test Piece</work-title></work>
  <identification>
    <creator type="composer">Test Composer</creator>
  </identification>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>whole</type>
      </note>
    </measure>
  </part>
</score-partwise>'''


@pytest.fixture
def complex_musicxml():
    """MusicXML with multiple note values, dynamics, and intervals."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Test</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>2</divisions>
        <key><fifths>1</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>F</sign><line>4</line></clef>
      </attributes>
      <direction>
        <direction-type><dynamics><f/></dynamics></direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>3</octave></pitch>
        <duration>2</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>3</octave></pitch>
        <duration>2</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>3</octave></pitch>
        <duration>4</duration>
        <type>half</type>
      </note>
    </measure>
  </part>
</score-partwise>'''


@pytest.fixture
def bass_clef_musicxml():
    """MusicXML in bass clef."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Bass</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>F</sign><line>4</line></clef>
      </attributes>
      <note>
        <pitch><step>F</step><octave>2</octave></pitch>
        <duration>4</duration>
        <type>whole</type>
      </note>
    </measure>
  </part>
</score-partwise>'''


@pytest.fixture
def time_sig_6_8_musicxml():
    """MusicXML in 6/8 time."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>6</beats><beat-type>8</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>eighth</type>
      </note>
    </measure>
  </part>
</score-partwise>'''


# =============================================================================
# DATA CLASS TESTS
# =============================================================================

class TestExtractionResult:
    """Tests for ExtractionResult dataclass."""
    
    def test_default_values(self):
        """Verify default values are set correctly."""
        result = ExtractionResult()
        assert result.title is None
        assert result.composer is None
        assert result.clefs == set()
        assert result.time_signatures == set()
        assert result.key_signatures == set()
        assert result.note_values == {}
        assert result.has_ties is False
        assert result.measure_count == 0
    
    def test_to_dict_converts_sets(self):
        """Verify to_dict converts sets to lists."""
        result = ExtractionResult()
        result.clefs.add("clef_treble")
        result.time_signatures.add("time_sig_4_4")
        
        d = result.to_dict()
        assert isinstance(d["clefs"], list)
        assert "clef_treble" in d["clefs"]
        assert isinstance(d["time_signatures"], list)
    
    def test_to_dict_preserves_values(self):
        """Verify to_dict preserves all values."""
        result = ExtractionResult()
        result.title = "Test Title"
        result.composer = "Test Composer"
        result.measure_count = 16
        result.has_ties = True
        
        d = result.to_dict()
        assert d["title"] == "Test Title"
        assert d["composer"] == "Test Composer"
        assert d["measure_count"] == 16
        assert d["has_ties"] is True


class TestIntervalInfo:
    """Tests for IntervalInfo dataclass."""
    
    def test_creation(self):
        """Test creating IntervalInfo."""
        interval = IntervalInfo(
            name="M3",
            direction="ascending",
            quality="major",
            semitones=4,
            is_melodic=True,
            count=5
        )
        assert interval.name == "M3"
        assert interval.direction == "ascending"
        assert interval.quality == "major"
        assert interval.semitones == 4
        assert interval.is_melodic is True
        assert interval.count == 5


class TestRangeAnalysis:
    """Tests for RangeAnalysis dataclass."""
    
    def test_creation(self):
        """Test creating RangeAnalysis."""
        range_info = RangeAnalysis(
            lowest_pitch="C4",
            highest_pitch="C5",
            lowest_midi=60,
            highest_midi=72,
            range_semitones=12,
            density_low=33.3,
            density_mid=33.3,
            density_high=33.3
        )
        assert range_info.lowest_pitch == "C4"
        assert range_info.highest_pitch == "C5"
        assert range_info.range_semitones == 12


# =============================================================================
# ANALYZER TESTS
# =============================================================================

class TestMusicXMLAnalyzer:
    """Tests for MusicXMLAnalyzer class."""
    
    def test_analyzer_creation(self):
        """Test analyzer can be created."""
        analyzer = MusicXMLAnalyzer()
        assert analyzer is not None
    
    def test_simple_analysis(self, simple_musicxml):
        """Test analyzing simple MusicXML."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(simple_musicxml)
        
        assert result is not None
        assert result.measure_count >= 1
    
    def test_extracts_title(self, simple_musicxml):
        """Test title extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(simple_musicxml)
        
        assert result.title == "Test Piece"
    
    def test_extracts_composer(self, simple_musicxml):
        """Test composer extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(simple_musicxml)
        
        assert result.composer == "Test Composer"
    
    def test_extracts_treble_clef(self, simple_musicxml):
        """Test treble clef extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(simple_musicxml)
        
        assert "clef_treble" in result.clefs
    
    def test_extracts_bass_clef(self, bass_clef_musicxml):
        """Test bass clef extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(bass_clef_musicxml)
        
        assert "clef_bass" in result.clefs
    
    def test_extracts_4_4_time_sig(self, simple_musicxml):
        """Test 4/4 time signature extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(simple_musicxml)
        
        assert "time_sig_4_4" in result.time_signatures
    
    def test_extracts_6_8_time_sig(self, time_sig_6_8_musicxml):
        """Test 6/8 time signature extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(time_sig_6_8_musicxml)
        
        assert "time_sig_6_8" in result.time_signatures
    
    def test_extracts_whole_note(self, simple_musicxml):
        """Test whole note extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(simple_musicxml)
        
        assert "note_whole" in result.note_values
        assert result.note_values["note_whole"] >= 1
    
    def test_extracts_quarter_note(self, complex_musicxml):
        """Test quarter note extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(complex_musicxml)
        
        assert "note_quarter" in result.note_values
    
    def test_extracts_eighth_notes(self, time_sig_6_8_musicxml):
        """Test eighth note extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(time_sig_6_8_musicxml)
        
        assert "note_eighth" in result.note_values
        assert result.note_values["note_eighth"] >= 6
    
    def test_extracts_half_note(self, complex_musicxml):
        """Test half note extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(complex_musicxml)
        
        assert "note_half" in result.note_values
    
    def test_extracts_range_analysis(self, simple_musicxml):
        """Test range analysis extraction."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(simple_musicxml)
        
        assert result.range_analysis is not None
        assert result.range_analysis.lowest_midi == 60  # C4
        assert result.range_analysis.highest_midi == 60  # Same note
    
    def test_extracts_range_with_multiple_notes(self, time_sig_6_8_musicxml):
        """Test range analysis with multiple notes."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(time_sig_6_8_musicxml)
        
        assert result.range_analysis is not None
        assert result.range_analysis.lowest_pitch == "C4"
        assert result.range_analysis.highest_pitch == "A4"
        assert result.range_analysis.range_semitones == 9  # C4 to A4
    
    def test_invalid_musicxml_raises(self):
        """Test invalid MusicXML raises ValueError."""
        analyzer = MusicXMLAnalyzer()
        
        with pytest.raises(ValueError, match="Failed to parse"):
            analyzer.analyze("not valid xml at all")
    
    def test_empty_musicxml_raises(self):
        """Test empty content raises ValueError."""
        analyzer = MusicXMLAnalyzer()
        
        with pytest.raises(ValueError):
            analyzer.analyze("")


class TestCapabilityExtraction:
    """Tests for capability name extraction."""
    
    def test_get_capability_names_includes_clef(self, simple_musicxml):
        """Test capability names include clef."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(simple_musicxml)
        capabilities = analyzer.get_capability_names(result)
        
        assert "clef_treble" in capabilities
    
    def test_get_capability_names_includes_time_sig(self, simple_musicxml):
        """Test capability names include time signature."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(simple_musicxml)
        capabilities = analyzer.get_capability_names(result)
        
        assert "time_sig_4_4" in capabilities
    
    def test_get_capability_names_includes_note_values(self, simple_musicxml):
        """Test capability names include note values."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(simple_musicxml)
        capabilities = analyzer.get_capability_names(result)
        
        assert "note_whole" in capabilities
    
    def test_get_capability_names_multiple_notes(self, complex_musicxml):
        """Test capability names include all note values."""
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(complex_musicxml)
        capabilities = analyzer.get_capability_names(result)
        
        assert "note_quarter" in capabilities
        assert "note_half" in capabilities


# =============================================================================
# UTILITY FUNCTION TESTS
# =============================================================================

class TestAnalyzeMusicXMLFunction:
    """Tests for the analyze_musicxml convenience function."""
    
    def test_returns_tuple(self, simple_musicxml):
        """Test returns tuple of result and capabilities."""
        result, capabilities = analyze_musicxml(simple_musicxml)
        
        assert isinstance(result, ExtractionResult)
        assert isinstance(capabilities, list)
    
    def test_capabilities_not_empty(self, simple_musicxml):
        """Test capabilities list is not empty."""
        result, capabilities = analyze_musicxml(simple_musicxml)
        
        assert len(capabilities) > 0


class TestComputeCapabilityBitmask:
    """Tests for compute_capability_bitmask function."""
    
    def test_empty_list_returns_zeros(self):
        """Test empty capability list returns all zeros."""
        masks = compute_capability_bitmask([])
        
        assert masks == [0, 0, 0, 0, 0, 0, 0, 0]
    
    def test_single_capability_in_first_bucket(self):
        """Test capability in first bucket (0-63)."""
        masks = compute_capability_bitmask([0])
        
        assert masks[0] == 1  # Bit 0 set
        assert masks[1] == 0
    
    def test_capability_in_second_bucket(self):
        """Test capability in second bucket (64-127)."""
        masks = compute_capability_bitmask([64])
        
        assert masks[0] == 0
        assert masks[1] == 1  # Bit 0 of bucket 1
    
    def test_multiple_capabilities_same_bucket(self):
        """Test multiple capabilities in same bucket."""
        masks = compute_capability_bitmask([0, 1, 2])
        
        assert masks[0] == 7  # Bits 0, 1, 2 set (1 + 2 + 4)
    
    def test_capabilities_across_buckets(self):
        """Test capabilities spanning multiple buckets."""
        masks = compute_capability_bitmask([0, 64, 128])
        
        assert masks[0] == 1
        assert masks[1] == 1
        assert masks[2] == 1


class TestCheckEligibility:
    """Tests for check_eligibility function."""
    
    def test_empty_requirements_always_eligible(self):
        """Test user is eligible when no requirements."""
        user_masks = [0, 0, 0, 0, 0, 0, 0, 0]
        material_masks = [0, 0, 0, 0, 0, 0, 0, 0]
        
        assert check_eligibility(user_masks, material_masks) is True
    
    def test_user_has_required_capability(self):
        """Test user is eligible when they have required capability."""
        user_masks = [1, 0, 0, 0, 0, 0, 0, 0]  # Has capability 0
        material_masks = [1, 0, 0, 0, 0, 0, 0, 0]  # Requires capability 0
        
        assert check_eligibility(user_masks, material_masks) is True
    
    def test_user_missing_required_capability(self):
        """Test user is not eligible when missing required capability."""
        user_masks = [0, 0, 0, 0, 0, 0, 0, 0]  # No capabilities
        material_masks = [1, 0, 0, 0, 0, 0, 0, 0]  # Requires capability 0
        
        assert check_eligibility(user_masks, material_masks) is False
    
    def test_user_has_extra_capabilities(self):
        """Test user is eligible when they have more than required."""
        user_masks = [7, 0, 0, 0, 0, 0, 0, 0]  # Has caps 0, 1, 2
        material_masks = [1, 0, 0, 0, 0, 0, 0, 0]  # Requires only cap 0
        
        assert check_eligibility(user_masks, material_masks) is True
    
    def test_user_missing_one_of_multiple(self):
        """Test user not eligible when missing one of multiple requirements."""
        user_masks = [1, 0, 0, 0, 0, 0, 0, 0]  # Has cap 0 only
        material_masks = [3, 0, 0, 0, 0, 0, 0, 0]  # Requires caps 0 and 1
        
        assert check_eligibility(user_masks, material_masks) is False
    
    def test_handles_none_values(self):
        """Test handles None values gracefully."""
        user_masks = [1, None, 0, 0, 0, 0, 0, 0]
        material_masks = [1, 0, 0, 0, 0, 0, 0, 0]
        
        # Should not raise, should treat None as 0
        result = check_eligibility(user_masks, material_masks)
        assert result is True


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""
    
    def test_musicxml_with_only_rests(self):
        """Test MusicXML with only rests."""
        musicxml = '''<?xml version="1.0" encoding="UTF-8"?>
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <rest/>
        <duration>4</duration>
        <type>whole</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
        
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(musicxml)
        
        # Should have rest but no notes
        assert "rest_whole" in result.rest_values
        assert result.range_analysis is None  # No pitched notes
    
    def test_musicxml_minimal(self):
        """Test minimal valid MusicXML."""
        musicxml = '''<?xml version="1.0"?>
<score-partwise>
  <part-list>
    <score-part id="P1"><part-name>P</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
        
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(musicxml)
        
        assert result is not None
        assert "note_quarter" in result.note_values
