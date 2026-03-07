"""
Integration Tests for Unified Scoring Pipeline

Tests the full flow: MusicXML → SoftGateMetrics → UnifiedDomainScores

These tests verify:
1. End-to-end pipeline produces valid domain results
2. Profile data flows correctly through the pipeline
3. Null handling works for missing tempo/range context
4. Stage derivation matches threshold spec
5. Composite scoring aggregates correctly
"""

import pytest
import os
from pathlib import Path
from typing import Dict, Any

from app.soft_gate_calculator import (
    SoftGateCalculator,
    calculate_soft_gates,
    calculate_unified_domain_scores,
)
from app.scoring_functions import DomainResult, score_to_stage, STAGE_THRESHOLDS
from app.difficulty_interactions import calculate_composite_difficulty


# =============================================================================
# TEST FIXTURES
# =============================================================================

@pytest.fixture
def test_files_dir():
    """Path to test MusicXML files."""
    return Path(__file__).parent.parent / "resources" / "materials" / "test"


@pytest.fixture
def simple_musicxml():
    """Simple MusicXML with basic quarter notes in C major."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Test</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
    <measure number="2">
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>1</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>"""


@pytest.fixture
def complex_musicxml_with_tempo():
    """MusicXML with explicit tempo marking."""
    return """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Test</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>2</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction placement="above">
        <direction-type>
          <metronome>
            <beat-unit>quarter</beat-unit>
            <per-minute>120</per-minute>
          </metronome>
        </direction-type>
        <sound tempo="120"/>
      </direction>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>eighth</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>eighth</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>1</duration><type>eighth</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>1</duration><type>eighth</type></note>
      <note><pitch><step>E</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type></note>
      <note><pitch><step>C</step><octave>5</octave></pitch><duration>2</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>"""


# =============================================================================
# SOFT GATE METRICS TESTS
# =============================================================================

class TestSoftGateCalculation:
    """Test SoftGateMetrics calculation from MusicXML."""
    
    def test_calculate_from_simple_musicxml(self, simple_musicxml):
        """Verify basic metrics extraction works."""
        metrics = calculate_soft_gates(simple_musicxml)
        
        assert metrics is not None
        assert metrics.unique_pitch_count > 0
        assert metrics.density_notes_per_second > 0
        assert metrics.rhythm_complexity_score >= 0
        assert metrics.rhythm_complexity_score <= 1
    
    def test_interval_profile_populated(self, simple_musicxml):
        """Verify interval profile is populated."""
        metrics = calculate_soft_gates(simple_musicxml)
        
        assert metrics.interval_profile is not None
        assert metrics.interval_profile.total_intervals > 0
        # Simple stepwise motion should have high step_ratio
        assert metrics.interval_profile.step_ratio > 0.5
    
    def test_tempo_not_extracted_when_missing(self, simple_musicxml):
        """Verify tempo is None when not specified in score."""
        calc = SoftGateCalculator()
        score = calc._extract_note_data  # Access internal method indirectly
        
        metrics = calculate_soft_gates(simple_musicxml)
        # tempo_difficulty_score should be None when no tempo marking
        assert metrics.tempo_difficulty_score is None


# =============================================================================
# UNIFIED DOMAIN SCORING TESTS
# =============================================================================

class TestUnifiedDomainScoring:
    """Test unified domain score calculation."""
    
    def test_all_domains_produced(self, simple_musicxml):
        """Verify all 7 domains are produced."""
        metrics = calculate_soft_gates(simple_musicxml)
        results = calculate_unified_domain_scores(metrics)
        
        expected_domains = ['interval', 'rhythm', 'tonal', 'tempo', 'range', 'throughput', 'pattern']
        for domain in expected_domains:
            assert domain in results, f"Missing domain: {domain}"
            assert isinstance(results[domain], DomainResult)
    
    def test_domain_result_structure(self, simple_musicxml):
        """Verify each domain result has required fields."""
        metrics = calculate_soft_gates(simple_musicxml)
        results = calculate_unified_domain_scores(metrics)
        
        for domain, result in results.items():
            # Check profile
            assert isinstance(result.profile, dict), f"{domain} missing profile"
            
            # Check facet_scores
            assert isinstance(result.facet_scores, dict), f"{domain} missing facet_scores"
            
            # Check scores (dict with primary/hazard/overall keys)
            assert 'primary' in result.scores, f"{domain} scores missing primary"
            assert 'hazard' in result.scores, f"{domain} scores missing hazard"
            assert 'overall' in result.scores, f"{domain} scores missing overall"
            
            # Check bands (dict with stage keys)
            assert 'primary_stage' in result.bands, f"{domain} bands missing primary_stage"
            assert 'hazard_stage' in result.bands, f"{domain} bands missing hazard_stage"
            assert 'overall_stage' in result.bands, f"{domain} bands missing overall_stage"
            
            # Check flags and confidence
            assert isinstance(result.flags, list)
            assert isinstance(result.confidence, float)
    
    def test_tempo_returns_null_scores_without_marking(self, simple_musicxml):
        """Tempo domain should return null scores when no tempo marking."""
        metrics = calculate_soft_gates(simple_musicxml)
        results = calculate_unified_domain_scores(metrics)
        
        tempo = results['tempo']
        assert tempo.scores['primary'] is None
        assert tempo.scores['hazard'] is None
        assert tempo.scores['overall'] is None
        assert tempo.confidence == 0.0
        assert 'no_tempo_marking' in tempo.flags
    
    def test_range_returns_null_scores_no_instrument(self, simple_musicxml):
        """Range domain should return null scores without instrument context."""
        metrics = calculate_soft_gates(simple_musicxml)
        results = calculate_unified_domain_scores(metrics)
        
        range_result = results['range']
        assert range_result.scores['primary'] is None
        assert range_result.scores['hazard'] is None
        assert range_result.scores['overall'] is None
        assert range_result.confidence == 0.0
        assert 'requires_instrument_context' in range_result.flags
    
    def test_interval_produces_valid_scores(self, simple_musicxml):
        """Interval domain should produce valid scores."""
        metrics = calculate_soft_gates(simple_musicxml)
        results = calculate_unified_domain_scores(metrics)
        
        interval = results['interval']
        # Scores should be between 0 and 1
        assert 0 <= interval.scores['primary'] <= 1
        assert 0 <= interval.scores['hazard'] <= 1
        assert 0 <= interval.scores['overall'] <= 1
        # Stages should be 0-6
        assert 0 <= interval.bands['primary_stage'] <= 6
        assert 0 <= interval.bands['hazard_stage'] <= 6
        assert 0 <= interval.bands['overall_stage'] <= 6


# =============================================================================
# STAGE DERIVATION TESTS
# =============================================================================

class TestStageDerivation:
    """Test that stage derivation matches spec thresholds."""
    
    @pytest.mark.parametrize("score,expected_stage", [
        (0.00, 0),
        (0.10, 0),
        (0.14, 0),
        (0.15, 1),
        (0.20, 1),
        (0.29, 1),
        (0.30, 2),
        (0.44, 2),
        (0.45, 3),
        (0.59, 3),
        (0.60, 4),
        (0.74, 4),
        (0.75, 5),
        (0.89, 5),
        (0.90, 6),
        (1.00, 6),
    ])
    def test_stage_thresholds(self, score, expected_stage):
        """Verify stage derivation matches threshold table."""
        assert score_to_stage(score) == expected_stage
    
    def test_stage_thresholds_match_spec(self):
        """Verify STAGE_THRESHOLDS matches documented spec."""
        expected = [0.15, 0.30, 0.45, 0.60, 0.75, 0.90]
        assert STAGE_THRESHOLDS == expected


# =============================================================================
# COMPOSITE SCORING TESTS
# =============================================================================

class TestCompositeScoring:
    """Test composite difficulty calculation."""
    
    def test_composite_handles_null_scores(self, simple_musicxml):
        """Composite should skip domains with null scores."""
        metrics = calculate_soft_gates(simple_musicxml)
        results = calculate_unified_domain_scores(metrics)
        
        all_scores = {name: dr.scores for name, dr in results.items()}
        composite = calculate_composite_difficulty(all_scores)
        
        # Should not error and should produce valid result
        assert 'overall' in composite
        assert 'weighted_sum' in composite
        assert 0 <= composite['overall'] <= 1
    
    def test_composite_produces_interaction_flags(self):
        """Composite should produce interaction flags when thresholds met."""
        # Create mock scores that trigger interactions
        high_scores = {
            'interval': {'primary': 0.7, 'hazard': 0.5, 'overall': 0.6},
            'rhythm': {'primary': 0.7, 'hazard': 0.5, 'overall': 0.6},
            'tonal': {'primary': 0.3, 'hazard': 0.2, 'overall': 0.25},
            'tempo': {'primary': None, 'hazard': None, 'overall': None},
            'range': {'primary': None, 'hazard': None, 'overall': None},
            'throughput': {'primary': 0.4, 'hazard': 0.3, 'overall': 0.35},
        }
        
        composite = calculate_composite_difficulty(high_scores)
        
        # High interval + high rhythm should trigger interaction
        assert composite['interaction_bonus'] > 0 or len(composite.get('interaction_flags', [])) > 0


# =============================================================================
# END-TO-END PIPELINE TESTS
# =============================================================================

class TestEndToEndPipeline:
    """Test complete pipeline from MusicXML file to scores."""
    
    def test_pipeline_with_test_file(self, test_files_dir):
        """Test pipeline with actual test file if it exists."""
        test_file = test_files_dir / "test_06_complex.musicxml"
        
        if not test_file.exists():
            pytest.skip(f"Test file not found: {test_file}")
        
        with open(test_file) as f:
            content = f.read()
        
        # Full pipeline
        metrics = calculate_soft_gates(content)
        results = calculate_unified_domain_scores(metrics)
        all_scores = {name: dr.scores for name, dr in results.items()}
        composite = calculate_composite_difficulty(all_scores)
        
        # Verify structure (7 domains: interval, rhythm, tonal, tempo, range, throughput, pattern)
        assert len(results) == 7
        assert 'overall' in composite
        
        # Verify interval is scored (test file has intervals)
        assert results['interval'].scores['overall'] is not None
        
        # Verify rhythm is scored
        assert results['rhythm'].scores['overall'] is not None
    
    def test_pipeline_to_dict_serialization(self, simple_musicxml):
        """Test that results serialize correctly for API response."""
        metrics = calculate_soft_gates(simple_musicxml)
        results = calculate_unified_domain_scores(metrics)
        
        # Convert to dict for JSON serialization
        serialized = {name: dr.to_dict() for name, dr in results.items()}
        
        for domain, data in serialized.items():
            assert isinstance(data, dict)
            assert 'profile' in data
            assert 'facet_scores' in data
            assert 'scores' in data
            assert 'bands' in data
            assert 'flags' in data
            assert 'confidence' in data


# =============================================================================
# REGRESSION TESTS
# =============================================================================

class TestRegressions:
    """Regression tests for previously fixed issues."""
    
    def test_subdivision_complexity_detects_sixteenth_notes(self):
        """Verify subdivision_complexity > 0 when 16th notes present."""
        musicxml_with_sixteenths = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Test</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>D</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>E</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>F</step><octave>4</octave></pitch><duration>1</duration><type>16th</type></note>
      <note><pitch><step>G</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>A</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
      <note><pitch><step>B</step><octave>4</octave></pitch><duration>4</duration><type>quarter</type></note>
    </measure>
  </part>
</score-partwise>"""
        
        metrics = calculate_soft_gates(musicxml_with_sixteenths)
        results = calculate_unified_domain_scores(
            metrics, 
            extraction={'note_values': {'note_sixteenth': 4, 'note_quarter': 3}}
        )
        
        rhythm = results['rhythm']
        # subdivision_complexity should be > 0 (not stuck at 0)
        assert rhythm.facet_scores['subdivision_complexity'] > 0
    
    def test_null_scores_do_not_crash_composite(self):
        """Verify null scores don't cause TypeError in composite calculation."""
        # This was a regression where None * float caused TypeError
        mock_scores = {
            'interval': {'primary': 0.5, 'hazard': 0.3, 'overall': 0.4},
            'rhythm': {'primary': 0.4, 'hazard': 0.3, 'overall': 0.35},
            'tonal': {'primary': 0.2, 'hazard': 0.1, 'overall': 0.15},
            'tempo': {'primary': None, 'hazard': None, 'overall': None},
            'range': {'primary': None, 'hazard': None, 'overall': None},
            'throughput': {'primary': 0.3, 'hazard': 0.2, 'overall': 0.25},
        }
        
        # Should not raise TypeError
        composite = calculate_composite_difficulty(mock_scores)
        assert composite['overall'] is not None
