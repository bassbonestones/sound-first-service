from __future__ import annotations

"""
Soft Gate Calculator

Main SoftGateCalculator class that parses MusicXML with music21 and
delegates to individual calculator modules.
"""

import logging
from collections import Counter
from typing import Dict, Optional, Any

try:
    from music21 import converter, stream, note, chord, key, meter, tempo
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

from ..models import NoteEvent, IntervalProfile, IntervalLocalDifficulty, SoftGateMetrics
from ..tonal_calculator import calculate_tonal_complexity_stage
from ..interval_calculator import (
    calculate_interval_size_stage,
    calculate_interval_profile,
    calculate_interval_local_difficulty,
    calculate_interval_sustained_stage,
    calculate_interval_hazard_stage,
    calculate_interval_velocity_score,
    calculate_interval_velocity_windowed,
)
from ..rhythm_calculator import (
    calculate_rhythm_complexity_score,
    calculate_rhythm_complexity_windowed,
)
from ..range_calculator import calculate_range_usage_stage
from ..throughput_calculator import (
    calculate_density_metrics,
    calculate_tempo_difficulty_score,
)
from .score_extractor import extract_note_data

logger = logging.getLogger(__name__)


class SoftGateCalculator:
    """
    Main calculator for soft gate metrics from music21 score.
    """
    
    def __init__(self) -> None:
        if not MUSIC21_AVAILABLE:
            raise ImportError("music21 is required for soft gate calculation")
    
    def _extract_note_data(self, score: stream.Score) -> Dict[str, Any]:
        """Extract all note-related data for calculations. Delegates to module function."""
        return extract_note_data(score)
    
    def calculate_from_score(self, score: stream.Score, tempo_bpm: Optional[int] = None) -> SoftGateMetrics:
        """
        Calculate all soft gate metrics from a music21 Score.
        
        Args:
            score: music21 Score object
            tempo_bpm: Override tempo BPM (uses score tempo if None)
            
        Returns:
            SoftGateMetrics dataclass
        """
        # Extract note data
        note_data = extract_note_data(score)
        
        # Get tempo
        if tempo_bpm is None:
            tempo_bpm = self._extract_tempo(score)
        
        # Get measure count
        measure_count = self._count_measures(score)
        
        # Calculate each dimension
        d1_stage, d1_raw = calculate_tonal_complexity_stage(
            note_data["pitch_class_count"],
            note_data["accidental_count"],
            note_data["total_notes"],
        )
        
        # Legacy D2 stage (for backward compatibility)
        d2_stage, d2_raw = calculate_interval_size_stage(
            note_data["interval_semitones"],
        )
        
        # NEW: Interval profile system
        interval_profile = calculate_interval_profile(
            note_data["interval_semitones"],
        )
        
        interval_local_diff = calculate_interval_local_difficulty(
            note_data["interval_semitones"],
            note_data["interval_offsets"],
            note_data["interval_measure_numbers"],
        )
        
        interval_sustained = calculate_interval_sustained_stage(interval_profile)
        interval_hazard = calculate_interval_hazard_stage(interval_profile, interval_local_diff)
        legacy_interval_stage = max(interval_sustained, interval_hazard)
        
        d3_score, d3_raw = calculate_rhythm_complexity_score(
            note_data["durations"],
            note_data["types"],
            note_data["has_dots"],
            note_data["has_tuplets"],
            note_data["has_ties"],
            note_data["pitch_changes"],
            note_data["offsets"],
        )
        
        # Windowed rhythm complexity for longer pieces
        d3_peak, d3_p95, d3_windowed_raw = calculate_rhythm_complexity_windowed(
            note_data["durations"],
            note_data["types"],
            note_data["has_dots"],
            note_data["has_tuplets"],
            note_data["has_ties"],
            note_data["pitch_changes"],
            note_data["offsets"],
        )
        
        d4_stage, d4_raw = calculate_range_usage_stage(
            note_data["note_steps"],
        )
        
        # Estimate duration
        duration_seconds = self._estimate_duration(score, tempo_bpm or 100, measure_count)
        
        # Get time signature for beats per measure
        time_sigs = list(score.recurse().getElementsByClass(meter.TimeSignature))  # type: ignore[attr-defined]
        if time_sigs:
            beats_per_measure = time_sigs[0].beatCount * (4.0 / time_sigs[0].denominator)
        else:
            beats_per_measure = 4.0
        
        # Calculate notes per measure list for density volatility
        notes_per_measure_list = []
        if note_data["note_measure_numbers"]:
            measure_counts = Counter(note_data["note_measure_numbers"])
            # Convert to list ordered by measure number
            max_measure = max(measure_counts.keys()) if measure_counts else 0
            notes_per_measure_list = [measure_counts.get(m, 0) for m in range(1, max_measure + 1)]
        
        d5_nps, d5_npm, d5_peak, d5_vol, d5_raw = calculate_density_metrics(
            note_data["total_notes"],
            duration_seconds,
            notes_per_measure_list=notes_per_measure_list,
            measure_count=measure_count,
            tempo_bpm=tempo_bpm or 120,
            beats_per_measure=beats_per_measure,
        )
        
        # IVS
        ivs, ivs_raw = calculate_interval_velocity_score(
            note_data["note_events"],
        )
        
        # Windowed IVS for longer pieces
        ivs_peak, ivs_p95, ivs_windowed_raw = calculate_interval_velocity_windowed(
            note_data["note_events"],
        )
        
        # Tempo difficulty
        tempo_diff, tempo_raw = calculate_tempo_difficulty_score(
            tempo_bpm,
            d3_score,
            ivs,
        )
        
        # Largest interval
        largest_interval = max(note_data["interval_semitones"]) if note_data["interval_semitones"] else 0
        
        # Tessitura (p10-p90 pitch range = working range)
        tessitura_span = 0
        if note_data["note_events"]:
            pitches = sorted([e.pitch_midi for e in note_data["note_events"]])
            if len(pitches) >= 2:
                p10_idx = max(0, int(len(pitches) * 0.1))
                p90_idx = min(len(pitches) - 1, int(len(pitches) * 0.9))
                tessitura_span = pitches[p90_idx] - pitches[p10_idx]
        
        return SoftGateMetrics(
            tonal_complexity_stage=d1_stage,
            interval_size_stage=d2_stage,  # DEPRECATED
            rhythm_complexity_score=d3_score,
            rhythm_complexity_peak=d3_peak,
            rhythm_complexity_p95=d3_p95,
            range_usage_stage=d4_stage,
            # NEW: Interval profile stages
            interval_sustained_stage=interval_sustained,
            interval_hazard_stage=interval_hazard,
            legacy_interval_size_stage=legacy_interval_stage,
            interval_profile=interval_profile,
            interval_local_difficulty=interval_local_diff,
            # Continuous metrics
            density_notes_per_second=d5_nps,
            note_density_per_measure=d5_npm,
            peak_notes_per_second=d5_peak,
            throughput_volatility=d5_vol,
            tempo_difficulty_score=tempo_diff,
            interval_velocity_score=ivs,
            interval_velocity_peak=ivs_peak,
            interval_velocity_p95=ivs_p95,
            unique_pitch_count=note_data["pitch_class_count"],
            largest_interval_semitones=largest_interval,
            tessitura_span_semitones=tessitura_span,
            raw_metrics={
                "d1": d1_raw,
                "d2": d2_raw,
                "d3": d3_raw,
                "d3_windowed": d3_windowed_raw,
                "d4": d4_raw,
                "d5": d5_raw,
                "ivs": ivs_raw,
                "ivs_windowed": ivs_windowed_raw,
                "tempo": tempo_raw,
                "interval_profile": {
                    "total_intervals": interval_profile.total_intervals,
                    "step_ratio": interval_profile.step_ratio,
                    "skip_ratio": interval_profile.skip_ratio,
                    "leap_ratio": interval_profile.leap_ratio,
                    "large_leap_ratio": interval_profile.large_leap_ratio,
                    "extreme_leap_ratio": interval_profile.extreme_leap_ratio,
                    "p50": interval_profile.interval_p50,
                    "p75": interval_profile.interval_p75,
                    "p90": interval_profile.interval_p90,
                    "max": interval_profile.interval_max,
                } if interval_profile else {},
                "interval_local": {
                    "max_large_in_window": interval_local_diff.max_large_leaps_in_window,
                    "max_extreme_in_window": interval_local_diff.max_extreme_leaps_in_window,
                    "hardest_measures": interval_local_diff.hardest_measure_numbers,
                    "window_count": interval_local_diff.window_count,
                } if interval_local_diff else {},
            },
        )
    
    def calculate_from_musicxml(self, musicxml_content: str, tempo_bpm: Optional[int] = None) -> SoftGateMetrics:
        """
        Calculate metrics from MusicXML string.
        
        Args:
            musicxml_content: MusicXML string
            tempo_bpm: Override tempo BPM
            
        Returns:
            SoftGateMetrics dataclass
        """
        score: Any = converter.parse(musicxml_content)
        return self.calculate_from_score(score, tempo_bpm)
    
    def _extract_tempo(self, score: stream.Score) -> Optional[int]:
        """Extract tempo BPM from score."""
        for mm in score.recurse().getElementsByClass(tempo.MetronomeMark):
            if mm.number:
                return int(mm.number)
        return None
    
    def _count_measures(self, score: stream.Score) -> int:
        """Count measures in score."""
        if score.parts:
            return len(score.parts[0].getElementsByClass('Measure'))
        return 0
    
    def _estimate_duration(self, score: stream.Score, bpm: int, measure_count: int) -> float:
        """Estimate duration in seconds."""
        if measure_count == 0 or bpm == 0:
            return 0
        
        # Get beats per measure from time signature
        time_sigs = list(score.recurse().getElementsByClass('TimeSignature'))
        if time_sigs:
            ts = time_sigs[0]
            beats_per_measure: float = float(ts.beatCount)
            beat_duration: float = float(ts.beatDuration.quarterLength)
        else:
            beats_per_measure = 4.0
            beat_duration = 1.0  # Quarter note
        
        # Total beats
        total_beats = measure_count * beats_per_measure
        
        # Seconds per beat
        seconds_per_beat = 60.0 / bpm
        
        # Total duration
        return total_beats * seconds_per_beat


def calculate_soft_gates(musicxml_content: str, tempo_bpm: Optional[int] = None) -> SoftGateMetrics:
    """
    Convenience function to calculate soft gate metrics from MusicXML.
    
    Args:
        musicxml_content: MusicXML string
        tempo_bpm: Override tempo BPM
        
    Returns:
        SoftGateMetrics dataclass
    """
    calculator = SoftGateCalculator()
    return calculator.calculate_from_musicxml(musicxml_content, tempo_bpm)
