"""
Tempo region building functions.

Converts tempo events into contiguous regions and calculates effective BPM.
"""

from typing import List, Optional

from .types import (
    TempoSourceType,
    TempoChangeType,
    TempoEvent,
    TempoRegion,
)


def build_tempo_regions(events: List[TempoEvent], total_measures: int) -> List[TempoRegion]:
    """
    Convert tempo events into contiguous regions.
    
    Args:
        events: Parsed tempo events in order
        total_measures: Total measure count in the piece
        
    Returns:
        List of TempoRegion objects covering the piece
    """
    if not events:
        # No tempo info - return single default region
        return [TempoRegion(
            start_measure=1,
            end_measure=total_measures,
            bpm=None,
            bpm_min=None,
            bpm_max=None,
            source_type=TempoSourceType.DEFAULT,
            change_type=TempoChangeType.INITIAL,
            text=None,
            is_approximate=True,
        )]
    
    regions: List[TempoRegion] = []
    base_bpm = None  # Track base tempo for a_tempo returns
    
    for i, event in enumerate(events):
        # Handle first event  
        if event.change_type == TempoChangeType.INITIAL or not regions:
            if event.bpm:
                base_bpm = event.bpm
        
        # Determine end measure (next event's start - 1, or end of piece)
        if i < len(events) - 1:
            end_meas = events[i + 1].measure_number - 1
            if end_meas < event.measure_number:
                end_meas = event.measure_number
        else:
            end_meas = total_measures
        
        # Handle a_tempo - restore base_bpm
        effective_bpm = event.bpm
        if event.change_type == TempoChangeType.A_TEMPO and base_bpm:
            effective_bpm = base_bpm
        
        # Handle gradual changes (accel/rit) - they span to next event
        bpm_min = effective_bpm
        bpm_max = effective_bpm
        if event.change_type == TempoChangeType.ACCELERANDO and i < len(events) - 1:
            next_bpm = events[i + 1].bpm
            if next_bpm and effective_bpm:
                bpm_min = min(effective_bpm, next_bpm)
                bpm_max = max(effective_bpm, next_bpm)
        elif event.change_type == TempoChangeType.RITARDANDO and i < len(events) - 1:
            next_bpm = events[i + 1].bpm
            if next_bpm and effective_bpm:
                bpm_min = min(effective_bpm, next_bpm)
                bpm_max = max(effective_bpm, next_bpm)
        
        region = TempoRegion(
            start_measure=event.measure_number,
            end_measure=end_meas,
            bpm=effective_bpm,
            bpm_min=bpm_min,
            bpm_max=bpm_max,
            source_type=event.source_type,
            change_type=event.change_type,
            text=event.text,
            is_approximate=event.is_approximate,
        )
        regions.append(region)
    
    # Merge adjacent stable regions with same tempo
    merged: List[TempoRegion] = []
    for region in regions:
        if merged and (
            merged[-1].bpm == region.bpm and
            merged[-1].change_type == TempoChangeType.STABLE and
            region.change_type == TempoChangeType.STABLE
        ):
            merged[-1].end_measure = region.end_measure
        else:
            merged.append(region)
    
    return merged


def calculate_effective_bpm(regions: List[TempoRegion]) -> Optional[int]:
    """
    Calculate weighted effective BPM based on region measure spans.
    
    Longer regions contribute more to the effective tempo.
    
    Args:
        regions: List of tempo regions
        
    Returns:
        Weighted average BPM, or None if no BPM info
    """
    total_weighted = 0.0
    total_measures = 0
    
    for region in regions:
        if region.bpm is None:
            continue
        
        span = region.end_measure - region.start_measure + 1
        
        # For tempo-changing regions (accel/rit), use midpoint
        if region.bpm_min and region.bpm_max and region.bpm_min != region.bpm_max:
            region_bpm = (region.bpm_min + region.bpm_max) / 2
        else:
            region_bpm = region.bpm
        
        total_weighted += region_bpm * span
        total_measures += span
    
    if total_measures == 0:
        return None
    
    return round(total_weighted / total_measures)
