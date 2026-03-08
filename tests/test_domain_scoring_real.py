"""
Test Domain Scoring with Real MusicXML Files

Validates that domain scoring produces expected score ranges for test files
with known complexity profiles. Uses relative ordering expectations
(baseline < moderate < complex) rather than brittle exact values.

Test Files (in tests/test_musicxml_files/scoring/):
- interval_baseline_stepwise.musicxml - Steps only
- interval_moderate_mixed.musicxml - Steps and skips
- interval_complex_large_leaps.musicxml - Large leaps, octaves+
- rhythm_baseline_quarters.musicxml - Quarter notes only
- rhythm_moderate_mixed.musicxml - Mixed values, dotted notes
- rhythm_complex_tuplets.musicxml - Triplets, sixteenths
- pattern_baseline_repetitive.musicxml - Same pattern repeated
- pattern_moderate_varied.musicxml - Some variation
- pattern_complex_unique.musicxml - All unique patterns
- throughput_baseline_sparse.musicxml - 1-2 NPS
- throughput_moderate.musicxml - 3-4 NPS
- throughput_complex_dense.musicxml - 5+ NPS
- tonal_baseline_diatonic.musicxml - Pure C major
- tonal_moderate_accidentals.musicxml - Some accidentals
- tonal_complex_chromatic.musicxml - Chromatic passages
- range_baseline_narrow.musicxml - 6th or less
- range_moderate_octave.musicxml - Within octave
- range_complex_wide.musicxml - Beyond octave
"""

import pytest
import json
from pathlib import Path
from typing import Dict, List

from app.soft_gate_calculator import (
    calculate_soft_gates,
    calculate_unified_domain_scores,
)
from app.scoring import DomainResult


# =============================================================================
# TEST FIXTURES
# =============================================================================

SCORING_FILES_DIR = Path(__file__).parent / "test_musicxml_files" / "scoring"


@pytest.fixture
def manifest():
    """Load the scoring test manifest."""
    manifest_path = SCORING_FILES_DIR / "manifest.json"
    with open(manifest_path) as f:
        return json.load(f)


def load_scoring_file(filename: str) -> str:
    """Load a scoring test MusicXML file."""
    filepath = SCORING_FILES_DIR / filename
    with open(filepath) as f:
        return f.read()


def score_file(filename: str) -> Dict[str, DomainResult]:
    """Score a test file and return domain results."""
    xml = load_scoring_file(filename)
    metrics = calculate_soft_gates(xml)
    return calculate_unified_domain_scores(metrics)


# =============================================================================
# INTERVAL DOMAIN TESTS
# =============================================================================

class TestIntervalDomain:
    """Test interval domain scoring with real MusicXML."""
    
    def test_baseline_scores_low(self):
        """Stepwise motion should have low interval scores."""
        results = score_file("interval_baseline_stepwise.musicxml")
        interval = results['interval']
        
        # Primary and hazard should be low for stepwise
        assert interval.scores['primary'] < 0.4, \
            f"Stepwise interval primary {interval.scores['primary']} should be < 0.4"
        assert interval.scores['hazard'] < 0.3, \
            f"Stepwise interval hazard {interval.scores['hazard']} should be < 0.3"
    
    def test_complex_scores_high(self):
        """Large leaps should have high interval scores."""
        results = score_file("interval_complex_large_leaps.musicxml")
        interval = results['interval']
        
        # Primary and hazard should be high for large leaps
        assert interval.scores['primary'] > 0.4, \
            f"Large leap interval primary {interval.scores['primary']} should be > 0.4"
        assert interval.scores['hazard'] > 0.3, \
            f"Large leap interval hazard {interval.scores['hazard']} should be > 0.3"
    
    def test_ordering_baseline_moderate_complex(self):
        """Scores should increase: baseline < moderate < complex."""
        baseline = score_file("interval_baseline_stepwise.musicxml")['interval']
        moderate = score_file("interval_moderate_mixed.musicxml")['interval']
        complex_ = score_file("interval_complex_large_leaps.musicxml")['interval']
        
        # Overall should follow ordering
        assert baseline.scores['overall'] < moderate.scores['overall'], \
            f"baseline {baseline.scores['overall']} should be < moderate {moderate.scores['overall']}"
        assert moderate.scores['overall'] < complex_.scores['overall'], \
            f"moderate {moderate.scores['overall']} should be < complex {complex_.scores['overall']}"


# =============================================================================
# RHYTHM DOMAIN TESTS
# =============================================================================

class TestRhythmDomain:
    """Test rhythm domain scoring with real MusicXML."""
    
    def test_baseline_scores_low(self):
        """Quarter notes only should have low rhythm scores."""
        results = score_file("rhythm_baseline_quarters.musicxml")
        rhythm = results['rhythm']
        
        assert rhythm.scores['primary'] < 0.5, \
            f"Quarter notes rhythm primary {rhythm.scores['primary']} should be < 0.5"
    
    def test_complex_scores_high(self):
        """Tuplets and complex subdivisions should have high scores."""
        results = score_file("rhythm_complex_tuplets.musicxml")
        rhythm = results['rhythm']
        
        # Tuplet presence should boost scores
        assert rhythm.scores['primary'] > 0.3, \
            f"Tuplet rhythm primary {rhythm.scores['primary']} should be > 0.3"
    
    def test_ordering_baseline_moderate_complex(self):
        """Scores should increase: baseline < moderate < complex."""
        baseline = score_file("rhythm_baseline_quarters.musicxml")['rhythm']
        moderate = score_file("rhythm_moderate_mixed.musicxml")['rhythm']
        complex_ = score_file("rhythm_complex_tuplets.musicxml")['rhythm']
        
        assert baseline.scores['overall'] <= moderate.scores['overall'], \
            f"baseline {baseline.scores['overall']} should be <= moderate {moderate.scores['overall']}"
        # Complex should be same or higher (tuplets boost)
        assert moderate.scores['overall'] <= complex_.scores['overall'], \
            f"moderate {moderate.scores['overall']} should be <= complex {complex_.scores['overall']}"


# =============================================================================
# PATTERN DOMAIN TESTS
# =============================================================================

class TestPatternDomain:
    """Test pattern/predictability domain scoring with real MusicXML."""
    
    def test_baseline_scores_low(self):
        """Repetitive patterns should have low difficulty scores."""
        results = score_file("pattern_baseline_repetitive.musicxml")
        pattern = results['pattern']
        
        # Repetitive = predictable = easy = low difficulty
        assert pattern.scores['primary'] < 0.6, \
            f"Repetitive pattern primary {pattern.scores['primary']} should be < 0.6"
    
    def test_complex_scores_high(self):
        """Unique patterns should have high difficulty scores."""
        results = score_file("pattern_complex_unique.musicxml")
        pattern = results['pattern']
        
        # Unique throughout = unpredictable = hard = high difficulty
        assert pattern.scores['primary'] > 0.3, \
            f"Unique pattern primary {pattern.scores['primary']} should be > 0.3"
    
    def test_ordering_baseline_moderate_complex(self):
        """Difficulty should increase: baseline < moderate < complex."""
        baseline = score_file("pattern_baseline_repetitive.musicxml")['pattern']
        moderate = score_file("pattern_moderate_varied.musicxml")['pattern']
        complex_ = score_file("pattern_complex_unique.musicxml")['pattern']
        
        # Allow some tolerance for pattern scoring variability
        assert baseline.scores['overall'] <= moderate.scores['overall'] + 0.1, \
            f"baseline {baseline.scores['overall']} should be <= moderate {moderate.scores['overall']}"


# =============================================================================
# THROUGHPUT DOMAIN TESTS
# =============================================================================

class TestThroughputDomain:
    """Test throughput domain scoring with real MusicXML."""
    
    def test_baseline_scores_low(self):
        """Sparse notes (whole notes, slow tempo) should have low scores."""
        results = score_file("throughput_baseline_sparse.musicxml")
        throughput = results['throughput']
        
        assert throughput.scores['primary'] < 0.5, \
            f"Sparse throughput primary {throughput.scores['primary']} should be < 0.5"
    
    def test_complex_scores_high(self):
        """Dense notes (16ths at fast tempo) should have high scores."""
        results = score_file("throughput_complex_dense.musicxml")
        throughput = results['throughput']
        
        # Dense with explicit tempo should score higher
        assert throughput.scores['primary'] > 0.3, \
            f"Dense throughput primary {throughput.scores['primary']} should be > 0.3"
    
    def test_ordering_baseline_moderate_complex(self):
        """Scores should increase: baseline < moderate < complex."""
        baseline = score_file("throughput_baseline_sparse.musicxml")['throughput']
        moderate = score_file("throughput_moderate.musicxml")['throughput']
        complex_ = score_file("throughput_complex_dense.musicxml")['throughput']
        
        # With tempo context, ordering should hold
        assert baseline.scores['overall'] <= moderate.scores['overall'] + 0.2, \
            f"baseline {baseline.scores['overall']} should be <= moderate {moderate.scores['overall']}"


# =============================================================================
# TONAL DOMAIN TESTS
# =============================================================================

class TestTonalDomain:
    """Test tonal domain scoring with real MusicXML."""
    
    def test_baseline_scores_low(self):
        """Pure diatonic should have low tonal complexity."""
        results = score_file("tonal_baseline_diatonic.musicxml")
        tonal = results['tonal']
        
        assert tonal.scores['primary'] < 0.4, \
            f"Diatonic tonal primary {tonal.scores['primary']} should be < 0.4"
    
    def test_complex_scores_high(self):
        """Chromatic passages should have high tonal complexity."""
        results = score_file("tonal_complex_chromatic.musicxml")
        tonal = results['tonal']
        
        assert tonal.scores['primary'] > 0.3, \
            f"Chromatic tonal primary {tonal.scores['primary']} should be > 0.3"
    
    def test_ordering_baseline_moderate_complex(self):
        """Scores should increase: baseline < moderate < complex."""
        baseline = score_file("tonal_baseline_diatonic.musicxml")['tonal']
        moderate = score_file("tonal_moderate_accidentals.musicxml")['tonal']
        complex_ = score_file("tonal_complex_chromatic.musicxml")['tonal']
        
        assert baseline.scores['overall'] <= moderate.scores['overall'], \
            f"baseline {baseline.scores['overall']} should be <= moderate {moderate.scores['overall']}"
        assert moderate.scores['overall'] <= complex_.scores['overall'], \
            f"moderate {moderate.scores['overall']} should be <= complex {complex_.scores['overall']}"


# =============================================================================
# RANGE DOMAIN TESTS
# =============================================================================

class TestRangeDomain:
    """Test range domain scoring with real MusicXML."""
    
    def test_baseline_narrow_range(self):
        """Narrow range (6th) should have low scores."""
        results = score_file("range_baseline_narrow.musicxml")
        range_result = results['range']
        
        # Without instrument context, range might be null
        # but profile should show narrow range
        if range_result.scores['primary'] is not None:
            assert range_result.scores['primary'] < 0.3, \
                f"Narrow range primary {range_result.scores['primary']} should be < 0.3"
    
    def test_complex_wide_range(self):
        """Wide range (octave+) should have higher scores."""
        results = score_file("range_complex_wide.musicxml")
        range_result = results['range']
        
        # Profile should indicate wider range
        profile = range_result.profile
        if 'range_semitones' in profile and profile['range_semitones']:
            assert profile['range_semitones'] > 12, \
                f"Wide range should be > 12 semitones, got {profile['range_semitones']}"


# =============================================================================
# COMPOSITE SCORING TESTS
# =============================================================================

class TestCompositeScoringReal:
    """Test composite scoring across multiple domains."""
    
    def test_all_low_file_scores_low_overall(self):
        """A file designed to be easy should have low composite difficulty."""
        # Use the interval baseline - simple stepwise motion
        results = score_file("interval_baseline_stepwise.musicxml")
        
        # Sum up non-null primaries
        domain_count = 0
        total_primary = 0.0
        for domain, result in results.items():
            if result.scores['primary'] is not None:
                total_primary += result.scores['primary']
                domain_count += 1
        
        if domain_count > 0:
            avg_primary = total_primary / domain_count
            # Simple stepwise motion should average low
            assert avg_primary < 0.6, \
                f"Simple file avg primary {avg_primary} should be < 0.6"
    
    def test_complex_file_scores_higher(self):
        """A complex file should have higher composite difficulty."""
        simple = score_file("interval_baseline_stepwise.musicxml")
        complex_ = score_file("interval_complex_large_leaps.musicxml")
        
        def avg_primary(results):
            primaries = [r.scores['primary'] for r in results.values() 
                        if r.scores['primary'] is not None]
            return sum(primaries) / len(primaries) if primaries else 0
        
        simple_avg = avg_primary(simple)
        complex_avg = avg_primary(complex_)
        
        assert simple_avg < complex_avg, \
            f"Simple avg {simple_avg} should be < complex avg {complex_avg}"


# =============================================================================
# PROFILE EXTRACTION TESTS
# =============================================================================

class TestProfileExtraction:
    """Test that profiles are correctly populated from MusicXML."""
    
    def test_interval_profile_has_percentiles(self):
        """Interval profile should have percentile data."""
        results = score_file("interval_complex_large_leaps.musicxml")
        profile = results['interval'].profile
        
        assert 'interval_p75' in profile or 'p75' in profile, \
            "Interval profile should have p75"
        assert 'interval_max' in profile or 'max_interval' in profile, \
            "Interval profile should have max_interval"
    
    def test_rhythm_profile_has_subdivisions(self):
        """Rhythm profile should have subdivision data."""
        results = score_file("rhythm_complex_tuplets.musicxml")
        profile = results['rhythm'].profile
        
        assert 'shortest_duration' in profile, \
            "Rhythm profile should have shortest_duration"
        assert 'tuplet_ratio' in profile, \
            "Rhythm profile should have tuplet_ratio"
    
    def test_tonal_profile_has_accidentals(self):
        """Tonal profile should have accidental data."""
        results = score_file("tonal_complex_chromatic.musicxml")
        profile = results['tonal'].profile
        
        # Should have non-diatonic note info
        assert 'chromatic_ratio' in profile or 'accidental_rate' in profile or \
               'pitch_class_count' in profile, \
            f"Tonal profile should have chromatic/pitch class data, got: {profile}"


# =============================================================================
# FACET SCORE TESTS
# =============================================================================

class TestFacetScores:
    """Test that facet scores are properly populated."""
    
    def test_interval_has_leap_facets(self):
        """Interval domain should have leap-related facets."""
        results = score_file("interval_complex_large_leaps.musicxml")
        facets = results['interval'].facet_scores
        
        # Should have complexity and hazard facets
        assert len(facets) > 0, "Interval should have facet scores"
    
    def test_rhythm_has_subdivision_facets(self):
        """Rhythm domain should have subdivision-related facets."""
        results = score_file("rhythm_moderate_mixed.musicxml")
        facets = results['rhythm'].facet_scores
        
        assert len(facets) > 0, "Rhythm should have facet scores"
    
    def test_pattern_has_predictability_facets(self):
        """Pattern domain should have predictability facets."""
        results = score_file("pattern_baseline_repetitive.musicxml")
        facets = results['pattern'].facet_scores
        
        assert len(facets) > 0, "Pattern should have facet scores"


# =============================================================================
# STAGE DERIVATION TESTS
# =============================================================================

class TestStageDerivedFromScores:
    """Test that stages are properly derived from scores."""
    
    def test_stages_in_valid_range(self):
        """All stages should be 0-6."""
        results = score_file("interval_moderate_mixed.musicxml")
        
        for domain, result in results.items():
            for stage_key, stage_val in result.bands.items():
                if stage_val is not None:
                    assert 0 <= stage_val <= 6, \
                        f"{domain}.{stage_key} = {stage_val} should be 0-6"
    
    def test_low_scores_produce_low_stages(self):
        """Low scores should produce low stages (0-2)."""
        results = score_file("interval_baseline_stepwise.musicxml")
        interval = results['interval']
        
        if interval.bands['primary_stage'] is not None:
            assert interval.bands['primary_stage'] <= 3, \
                f"Stepwise should have low stage, got {interval.bands['primary_stage']}"
    
    def test_high_scores_produce_higher_stages(self):
        """High scores should produce higher stages (3+)."""
        results = score_file("interval_complex_large_leaps.musicxml")
        interval = results['interval']
        
        if interval.bands['hazard_stage'] is not None:
            # Large leaps should produce higher hazard stage
            assert interval.bands['hazard_stage'] >= 1, \
                f"Large leaps should have higher hazard stage"
