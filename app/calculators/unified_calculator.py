"""
Unified Domain Score Calculator

Bridges SoftGateMetrics to the facet-aware scoring schema,
calling domain analyzers from scoring_functions.py.
"""

from typing import Dict, Optional, Any

from .models import SoftGateMetrics

# Import unified scoring functions
from app.scoring_functions import (
    analyze_interval_domain,
    analyze_rhythm_domain,
    analyze_tonal_domain,
    analyze_tempo_domain,
    analyze_range_domain,
    analyze_throughput_domain,
    analyze_pattern_domain,
    DomainResult,
)


def calculate_unified_domain_scores(
    metrics: SoftGateMetrics,
    tempo_profile: Optional[Dict[str, Any]] = None,
    range_analysis: Optional[Dict[str, Any]] = None,
    extraction: Optional[Dict[str, Any]] = None,
) -> Dict[str, DomainResult]:
    """
    Calculate unified domain scores from SoftGateMetrics.
    
    This is the bridge from raw metrics extraction to the facet-aware
    scoring schema. Builds profiles for each domain and calls the
    domain analyzers from scoring_functions.py.
    
    Args:
        metrics: SoftGateMetrics from calculate_soft_gates()
        tempo_profile: Optional tempo profile dict (from TempoAnalyzer)
        range_analysis: Optional range analysis dict (from MusicXMLAnalyzer)
        extraction: Optional detailed extraction dict (for additional profile data)
        
    Returns:
        Dict mapping domain name to DomainResult
    """
    results = {}
    
    # -------------------------------------------------------------------------
    # INTERVAL DOMAIN
    # -------------------------------------------------------------------------
    interval_profile_data = metrics.interval_profile
    interval_local = metrics.interval_local_difficulty
    
    interval_profile = {
        'interval_p50': interval_profile_data.interval_p50 if interval_profile_data else 0,
        'interval_p75': interval_profile_data.interval_p75 if interval_profile_data else 0,
        'interval_p90': interval_profile_data.interval_p90 if interval_profile_data else 0,
        'interval_max': interval_profile_data.interval_max if interval_profile_data else 0,
        'step_ratio': interval_profile_data.step_ratio if interval_profile_data else 1.0,
        'skip_ratio': interval_profile_data.skip_ratio if interval_profile_data else 0.0,
        'leap_ratio': interval_profile_data.leap_ratio if interval_profile_data else 0.0,
        'large_leap_ratio': interval_profile_data.large_leap_ratio if interval_profile_data else 0.0,
        'extreme_leap_ratio': interval_profile_data.extreme_leap_ratio if interval_profile_data else 0.0,
        'total_intervals': interval_profile_data.total_intervals if interval_profile_data else 0,
        'max_large_leaps_in_window': interval_local.max_large_leaps_in_window if interval_local else 0,
        'max_extreme_leaps_in_window': interval_local.max_extreme_leaps_in_window if interval_local else 0,
    }
    results['interval'] = analyze_interval_domain(interval_profile)
    
    # -------------------------------------------------------------------------
    # RHYTHM DOMAIN
    # -------------------------------------------------------------------------
    # Build subdivision_complexity from note_values in extraction
    shortest_duration = 1.0  # Default to quarter note
    tuplet_ratio = 0.0
    dot_ratio = 0.0
    tie_ratio = 0.0
    rhythm_uniqueness = 0.0
    rhythm_repetition = 1.0
    
    if extraction:
        # Note value durations
        duration_map = {
            'note_64th': 0.0625, 'note_32nd': 0.125, 'note_sixteenth': 0.25,
            'note_eighth': 0.5, 'note_quarter': 1.0, 'note_half': 2.0, 'note_whole': 4.0,
            '64th': 0.0625, '32nd': 0.125, '16th': 0.25,
            'eighth': 0.5, 'quarter': 1.0, 'half': 2.0, 'whole': 4.0,
        }
        note_values = extraction.get('note_values', {})
        for nv in note_values.keys():
            if nv in duration_map:
                shortest_duration = min(shortest_duration, duration_map[nv])
        
        # Compute ratios from extraction
        total_notes = sum(note_values.values()) if note_values else 1
        tuplets = extraction.get('tuplets', {})
        if tuplets:
            tuplet_ratio = sum(tuplets.values()) / max(total_notes, 1)
        dotted = extraction.get('dotted_notes', [])
        if dotted:
            dot_ratio = len(dotted) / max(total_notes, 1)
        if extraction.get('has_ties'):
            tie_ratio = 0.1  # Estimate
        
        # Rhythm pattern analysis
        rhythm_uniqueness = extraction.get('rhythm_measure_uniqueness_ratio', 0.0)
        rhythm_repetition = extraction.get('rhythm_measure_repetition_ratio', 1.0 - rhythm_uniqueness)
    
    # Fall back to raw metrics if extraction not available
    if not extraction and metrics.raw_metrics:
        d3_raw = metrics.raw_metrics.get('d3', {})
        rhythm_uniqueness = d3_raw.get('f2', 0)
        rhythm_repetition = 1.0 - rhythm_uniqueness
        # Estimate from f4 (irregular features composite)
        f4 = d3_raw.get('f4', 0)
        tuplet_ratio = f4 * 0.4
        dot_ratio = f4 * 0.3
        tie_ratio = f4 * 0.3
    
    rhythm_profile = {
        'rhythm_complexity_score': metrics.rhythm_complexity_score,
        'rhythm_complexity_peak': metrics.rhythm_complexity_peak,
        'rhythm_measure_uniqueness_ratio': rhythm_uniqueness,
        'rhythm_measure_repetition_ratio': rhythm_repetition,
        'tuplet_ratio': tuplet_ratio,
        'dot_ratio': dot_ratio,
        'tie_ratio': tie_ratio,
        'shortest_duration': shortest_duration,
    }
    results['rhythm'] = analyze_rhythm_domain(rhythm_profile)
    
    # -------------------------------------------------------------------------
    # TONAL DOMAIN
    # -------------------------------------------------------------------------
    d1_raw = metrics.raw_metrics.get('d1', {}) if metrics.raw_metrics else {}
    tonal_profile = {
        'pitch_class_count': d1_raw.get('pitch_class_count', metrics.unique_pitch_count),
        'accidental_rate': d1_raw.get('accidental_rate', 0),
        'chromatic_ratio': d1_raw.get('accidental_rate', 0),  # Approximate
        'unique_pitches': metrics.unique_pitch_count,
    }
    results['tonal'] = analyze_tonal_domain(tonal_profile)
    
    # -------------------------------------------------------------------------
    # TEMPO DOMAIN
    # -------------------------------------------------------------------------
    tempo_is_explicit = False
    if tempo_profile:
        tempo_is_explicit = tempo_profile.get('primary_source_type', 'default') != 'default'
    
    tempo_domain_profile = {
        'base_bpm': tempo_profile.get('base_bpm') if tempo_profile else None,
        'effective_bpm': tempo_profile.get('effective_bpm') if tempo_profile else None,
        'tempo_is_explicit': tempo_is_explicit,
    }
    results['tempo'] = analyze_tempo_domain(tempo_domain_profile)
    
    # -------------------------------------------------------------------------
    # RANGE DOMAIN
    # -------------------------------------------------------------------------
    range_profile = {
        'span_semitones': range_analysis.get('range_semitones') if range_analysis else None,
        'tessitura_span': metrics.tessitura_span_semitones,
        'lowest_pitch': range_analysis.get('lowest_pitch') if range_analysis else None,
        'highest_pitch': range_analysis.get('highest_pitch') if range_analysis else None,
    }
    results['range'] = analyze_range_domain(range_profile)
    
    # -------------------------------------------------------------------------
    # THROUGHPUT DOMAIN
    # -------------------------------------------------------------------------
    throughput_profile = {
        'notes_per_second': metrics.density_notes_per_second,
        'peak_notes_per_second': metrics.peak_notes_per_second,
        'throughput_volatility': metrics.throughput_volatility,
        'notes_per_measure': metrics.note_density_per_measure,
    }
    results['throughput'] = analyze_throughput_domain(throughput_profile)
    
    # -------------------------------------------------------------------------
    # PATTERN / PREDICTABILITY DOMAIN
    # -------------------------------------------------------------------------
    # Get melodic pattern analysis from extraction if available
    melodic_pattern = extraction.get('melodic_pattern_analysis', {}) if extraction else {}
    
    pattern_profile = {
        'total_melodic_motifs': melodic_pattern.get('total_motifs', 0),
        'unique_melodic_motifs': melodic_pattern.get('unique_motifs', 0),
        'melodic_motif_uniqueness_ratio': melodic_pattern.get('motif_uniqueness_ratio'),
        'melodic_motif_repetition_ratio': melodic_pattern.get('motif_repetition_ratio'),
        'sequence_count': melodic_pattern.get('sequence_count', 0),
        'sequence_coverage_ratio': melodic_pattern.get('sequence_coverage_ratio', 0.0),
        # Include rhythm pattern metrics
        'rhythm_uniqueness_ratio': rhythm_uniqueness,
        'rhythm_repetition_ratio': rhythm_repetition,
    }
    results['pattern'] = analyze_pattern_domain(pattern_profile)
    
    return results
