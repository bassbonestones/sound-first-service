"""
Tempo profile building.

Builds complete tempo profile from music21 score.
"""

from typing import Dict

try:
    from music21 import stream
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

from .types import (
    TempoSourceType,
    TempoChangeType,
    TempoProfile,
)
from .parsing import parse_tempo_events
from .regions import build_tempo_regions, calculate_effective_bpm


def build_tempo_profile(score: stream.Score) -> TempoProfile:
    """
    Build complete tempo profile from a music21 score.
    
    Args:
        score: music21 Score object
        
    Returns:
        TempoProfile with all metrics and regions
    """
    # Count measures
    parts = list(score.parts) if score else []
    if parts:
        measures = list(parts[0].getElementsByClass(stream.Measure))
        total_measures = len(measures) if measures else 1
    else:
        total_measures = 1
    
    # Parse events
    events = parse_tempo_events(score)
    
    # Build regions
    regions = build_tempo_regions(events, total_measures)
    
    # Calculate summary metrics
    bpm_values = [r.bpm for r in regions if r.bpm is not None]
    bpm_ranges = []
    for r in regions:
        if r.bpm_min is not None:
            bpm_ranges.append(r.bpm_min)
        if r.bpm_max is not None:
            bpm_ranges.append(r.bpm_max)
        if r.bpm is not None:
            bpm_ranges.append(r.bpm)
    
    base_bpm = bpm_values[0] if bpm_values else None
    min_bpm = min(bpm_ranges) if bpm_ranges else None
    max_bpm = max(bpm_ranges) if bpm_ranges else None
    effective_bpm = calculate_effective_bpm(regions)
    
    # Count meaningful tempo changes (exclude initial)
    change_types = [r.change_type for r in regions]
    tempo_change_count = sum(1 for ct in change_types if ct not in [
        TempoChangeType.INITIAL, TempoChangeType.STABLE
    ])
    
    # Boolean flags
    has_accelerando = TempoChangeType.ACCELERANDO in change_types
    has_ritardando = TempoChangeType.RITARDANDO in change_types
    has_a_tempo = TempoChangeType.A_TEMPO in change_types
    has_rubato = TempoChangeType.RUBATO in change_types
    has_sudden_change = TempoChangeType.SUDDEN_CHANGE in change_types
    has_tempo_marking = len(events) > 0
    
    # Confidence metrics
    is_fully_explicit = all(
        r.source_type == TempoSourceType.METRONOME_MARK 
        for r in regions if r.bpm is not None
    )
    
    # Primary source type
    if events:
        source_counts: Dict[TempoSourceType, int] = {}
        for e in events:
            source_counts[e.source_type] = source_counts.get(e.source_type, 0) + 1
        primary_source_type = max(source_counts, key=source_counts.get)
    else:
        primary_source_type = TempoSourceType.DEFAULT
    
    return TempoProfile(
        base_bpm=base_bpm,
        effective_bpm=effective_bpm,
        min_bpm=min_bpm,
        max_bpm=max_bpm,
        tempo_change_count=tempo_change_count,
        has_accelerando=has_accelerando,
        has_ritardando=has_ritardando,
        has_a_tempo=has_a_tempo,
        has_rubato=has_rubato,
        has_sudden_change=has_sudden_change,
        has_tempo_marking=has_tempo_marking,
        tempo_regions=regions,
        is_fully_explicit=is_fully_explicit,
        primary_source_type=primary_source_type,
    )
