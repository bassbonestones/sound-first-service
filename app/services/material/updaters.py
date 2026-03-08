"""
Material Analysis Updaters

Methods for updating MaterialAnalysis records with computed metrics.
"""

import json
from typing import Dict, Optional

from app.models.capability_schema import MaterialAnalysis


def update_soft_gates(analysis: MaterialAnalysis, soft_gates) -> Dict:
    """Update MaterialAnalysis with soft gate metrics."""
    analysis.tonal_complexity_stage = soft_gates.tonal_complexity_stage
    analysis.interval_size_stage = soft_gates.interval_size_stage
    analysis.interval_sustained_stage = soft_gates.interval_sustained_stage
    analysis.interval_hazard_stage = soft_gates.interval_hazard_stage
    analysis.legacy_interval_size_stage = soft_gates.legacy_interval_size_stage
    
    if soft_gates.interval_profile:
        analysis.interval_step_ratio = soft_gates.interval_profile.step_ratio
        analysis.interval_skip_ratio = soft_gates.interval_profile.skip_ratio
        analysis.interval_leap_ratio = soft_gates.interval_profile.leap_ratio
        analysis.interval_large_leap_ratio = soft_gates.interval_profile.large_leap_ratio
        analysis.interval_extreme_leap_ratio = soft_gates.interval_profile.extreme_leap_ratio
        analysis.interval_p50 = soft_gates.interval_profile.interval_p50
        analysis.interval_p75 = soft_gates.interval_profile.interval_p75
        analysis.interval_p90 = soft_gates.interval_profile.interval_p90
    
    if soft_gates.interval_local_difficulty:
        analysis.interval_max_large_in_window = soft_gates.interval_local_difficulty.max_large_leaps_in_window
        analysis.interval_max_extreme_in_window = soft_gates.interval_local_difficulty.max_extreme_leaps_in_window
        analysis.interval_hardest_measures = json.dumps(soft_gates.interval_local_difficulty.hardest_measure_numbers)
    
    analysis.rhythm_complexity_stage = soft_gates.rhythm_complexity_score
    analysis.rhythm_complexity_peak = soft_gates.rhythm_complexity_peak
    analysis.rhythm_complexity_p95 = soft_gates.rhythm_complexity_p95
    analysis.range_usage_stage = soft_gates.range_usage_stage
    analysis.density_notes_per_second = soft_gates.density_notes_per_second
    analysis.note_density_per_measure = soft_gates.note_density_per_measure
    analysis.tempo_difficulty_score = soft_gates.tempo_difficulty_score
    analysis.interval_velocity_score = soft_gates.interval_velocity_score
    analysis.interval_velocity_peak = soft_gates.interval_velocity_peak
    analysis.interval_velocity_p95 = soft_gates.interval_velocity_p95
    analysis.unique_pitch_count = soft_gates.unique_pitch_count
    analysis.largest_interval_semitones = soft_gates.largest_interval_semitones
    
    return {
        "tonal_complexity_stage": soft_gates.tonal_complexity_stage,
        "interval_size_stage": soft_gates.interval_size_stage,
        "interval_sustained_stage": soft_gates.interval_sustained_stage,
        "interval_hazard_stage": soft_gates.interval_hazard_stage,
        "legacy_interval_size_stage": soft_gates.legacy_interval_size_stage,
        "rhythm_complexity_score": round(soft_gates.rhythm_complexity_score, 3),
        "rhythm_complexity_peak": round(soft_gates.rhythm_complexity_peak, 3) if soft_gates.rhythm_complexity_peak else None,
        "rhythm_complexity_p95": round(soft_gates.rhythm_complexity_p95, 3) if soft_gates.rhythm_complexity_p95 else None,
        "range_usage_stage": soft_gates.range_usage_stage,
        "density_notes_per_second": round(soft_gates.density_notes_per_second, 3),
        "tempo_difficulty_score": round(soft_gates.tempo_difficulty_score, 3) if soft_gates.tempo_difficulty_score else None,
        "interval_velocity_score": round(soft_gates.interval_velocity_score, 3),
    }


def update_unified_scores(analysis: MaterialAnalysis, soft_gates) -> Dict:
    """Calculate and store unified domain scores."""
    from app.soft_gate_calculator import calculate_unified_domain_scores
    
    scores = calculate_unified_domain_scores(soft_gates)
    analysis.rhythm_domain_score = scores.rhythm_score
    analysis.interval_domain_score = scores.interval_score
    analysis.range_domain_score = scores.range_score
    analysis.throughput_domain_score = scores.throughput_score
    analysis.tonality_domain_score = scores.tonality_score
    
    return {
        "rhythm_domain_score": round(scores.rhythm_score, 2),
        "interval_domain_score": round(scores.interval_score, 2),
        "range_domain_score": round(scores.range_score, 2),
        "throughput_domain_score": round(scores.throughput_score, 2),
        "tonality_domain_score": round(scores.tonality_score, 2),
    }


def calculate_difficulty_scores(analysis: MaterialAnalysis) -> Dict:
    """Calculate and store composite difficulty scores."""
    from app.difficulty_interactions import calculate_composite_difficulty
    
    diff = calculate_composite_difficulty(analysis)
    analysis.physical_difficulty = diff.physical_difficulty
    analysis.cognitive_difficulty = diff.cognitive_difficulty
    analysis.combined_difficulty = diff.combined_difficulty
    
    return {
        "physical_difficulty": round(diff.physical_difficulty, 2),
        "cognitive_difficulty": round(diff.cognitive_difficulty, 2),
        "combined_difficulty": round(diff.combined_difficulty, 2),
    }


def update_range_analysis(analysis: MaterialAnalysis, extraction_result) -> Dict:
    """Update range analysis fields from extraction result."""
    range_data = extraction_result.range_analysis
    if not range_data:
        return {}
    
    analysis.lowest_pitch = range_data.lowest_pitch
    analysis.highest_pitch = range_data.highest_pitch
    analysis.range_semitones = range_data.range_semitones
    analysis.pitch_density_low = range_data.density_low
    analysis.pitch_density_mid = range_data.density_mid
    analysis.pitch_density_high = range_data.density_high
    analysis.trill_lowest = range_data.trill_lowest
    analysis.trill_highest = range_data.trill_highest
    
    return {
        "lowest_pitch": range_data.lowest_pitch,
        "highest_pitch": range_data.highest_pitch,
        "range_semitones": range_data.range_semitones,
    }


def persist_unified_scores(
    analysis: MaterialAnalysis,
    soft_gates,
    extraction_result
) -> Optional[Dict]:
    """
    Calculate and persist unified domain scores with composite difficulty.
    
    Returns the composite difficulty dict or None if failed.
    """
    from app.soft_gate_calculator import calculate_unified_domain_scores
    from app.difficulty_interactions import calculate_composite_difficulty
    
    try:
        # Build extraction dict for unified scoring
        extraction_dict = {
            'note_values': dict(extraction_result.note_values) if extraction_result.note_values else {},
            'tuplets': dict(extraction_result.tuplets) if extraction_result.tuplets else {},
            'dotted_notes': list(extraction_result.dotted_notes) if extraction_result.dotted_notes else [],
            'has_ties': extraction_result.has_ties,
        }
        if extraction_result.rhythm_pattern_analysis:
            extraction_dict['rhythm_measure_uniqueness_ratio'] = extraction_result.rhythm_pattern_analysis.rhythm_measure_uniqueness_ratio
            extraction_dict['rhythm_measure_repetition_ratio'] = extraction_result.rhythm_pattern_analysis.rhythm_measure_repetition_ratio
        
        tempo_profile_dict = extraction_result.tempo_profile.to_dict() if extraction_result.tempo_profile else None
        range_analysis_dict = extraction_result.range_analysis.__dict__ if extraction_result.range_analysis else None
        
        # Calculate unified domain scores
        domain_results = calculate_unified_domain_scores(
            metrics=soft_gates,
            tempo_profile=tempo_profile_dict,
            range_analysis=range_analysis_dict,
            extraction=extraction_dict,
        )
        
        # Persist JSON columns
        analysis.analysis_schema_version = 1
        analysis.interval_analysis_json = json.dumps(domain_results['interval'].to_dict()) if 'interval' in domain_results else None
        analysis.rhythm_analysis_json = json.dumps(domain_results['rhythm'].to_dict()) if 'rhythm' in domain_results else None
        analysis.tonal_analysis_json = json.dumps(domain_results['tonal'].to_dict()) if 'tonal' in domain_results else None
        analysis.tempo_analysis_json = json.dumps(domain_results['tempo'].to_dict()) if 'tempo' in domain_results else None
        analysis.range_analysis_json = json.dumps(domain_results['range'].to_dict()) if 'range' in domain_results else None
        analysis.throughput_analysis_json = json.dumps(domain_results['throughput'].to_dict()) if 'throughput' in domain_results else None
        
        # Persist indexed primary scores
        for domain in ['interval', 'rhythm', 'tonal', 'tempo', 'range', 'throughput']:
            if domain in domain_results and domain_results[domain].scores:
                setattr(analysis, f'{domain}_primary_score', domain_results[domain].scores.get('primary'))
        
        # Compute and persist composite scores
        all_scores = {name: dr.scores for name, dr in domain_results.items()}
        composite = calculate_composite_difficulty(all_scores)
        analysis.overall_score = composite.get('overall')
        analysis.interaction_bonus = composite.get('interaction_bonus')
        
        return composite
    except Exception as e:
        raise e
