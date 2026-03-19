from __future__ import annotations

"""
Pattern Analyzer

Rhythm and melodic pattern analysis for sight-reading difficulty prediction.
"""

from collections import Counter
from typing import List, TYPE_CHECKING

if TYPE_CHECKING:
    from music21 import stream
    from .extraction_models import ExtractionResult

from .extraction_models import RhythmPatternAnalysis, MelodicPatternAnalysis


def analyze_rhythm_patterns(score: "stream.Score", result: "ExtractionResult") -> None:
    """Analyze rhythm pattern uniqueness across measures.
    
    This is a key predictor of sight-reading difficulty:
    - Low uniqueness ratio = many repeated patterns = easier to read
    - High uniqueness ratio = every measure different = harder to read
    
    Creates a canonical rhythm signature per measure based on note/rest
    durations only (ignores pitch), then counts unique vs total patterns.
    """
    from music21 import note
    
    pattern_counts: Counter[str] = Counter()
    
    for part in score.parts:
        measures = part.getElementsByClass('Measure')
        
        for measure in measures:
            # Build canonical rhythm signature for this measure
            # Format: sequence of duration quarterLengths, e.g., "1.0|0.5|0.5|1.0"
            elements = []
            
            # Get all notes and rests in the measure, sorted by offset
            for elem in measure.notesAndRests:
                elements.append((elem.offset, elem.duration.quarterLength, 
                               'r' if isinstance(elem, note.Rest) else 'n'))
            
            # Also check voices within the measure
            for voice in measure.voices:
                for elem in voice.notesAndRests:
                    elements.append((elem.offset, elem.duration.quarterLength,
                                   'r' if isinstance(elem, note.Rest) else 'n'))
            
            # Sort by offset, then build signature
            elements.sort(key=lambda x: x[0])
            
            if elements:
                # Include both duration and note/rest type in signature
                # This distinguishes "quarter rest + quarter note" from "quarter note + quarter rest"
                signature = "|".join(f"{e[2]}{e[1]}" for e in elements)
                pattern_counts[signature] += 1
    
    total_measures = sum(pattern_counts.values())
    unique_patterns = len(pattern_counts)
    
    if total_measures == 0:
        result.rhythm_pattern_analysis = RhythmPatternAnalysis(
            total_measures=0,
            unique_rhythm_patterns=0,
            rhythm_measure_uniqueness_ratio=0.0,
            rhythm_measure_repetition_ratio=1.0,
            pattern_counts={},
        )
        return
    
    uniqueness_ratio = unique_patterns / total_measures
    repetition_ratio = 1.0 - uniqueness_ratio
    
    # Find most common pattern
    most_common = pattern_counts.most_common(1)
    most_common_pattern = most_common[0][0] if most_common else None
    most_common_count = most_common[0][1] if most_common else 0
    
    result.rhythm_pattern_analysis = RhythmPatternAnalysis(
        total_measures=total_measures,
        unique_rhythm_patterns=unique_patterns,
        rhythm_measure_uniqueness_ratio=round(uniqueness_ratio, 4),
        rhythm_measure_repetition_ratio=round(repetition_ratio, 4),
        pattern_counts=dict(pattern_counts),
        most_common_pattern=most_common_pattern,
        most_common_count=most_common_count,
    )


def analyze_melodic_patterns(score: "stream.Score", result: "ExtractionResult") -> None:
    """
    Analyze melodic patterns/motifs for predictability scoring (Phase 8).
    
    Detects:
    1. Short motifs (3-4 note interval sequences)
    2. Longer sequences (repeated phrases of 4+ notes)
    
    Higher repetition = more predictable = easier sight-reading.
    """
    from music21 import note
    
    # Collect all melodic intervals in sequence
    all_intervals: List[int] = []  # List of interval semitones
    all_pitches: List[int] = []  # For sequence detection
    
    for part in score.parts:
        prev_note = None
        
        for elem in part.flatten().notesAndRests:
            if isinstance(elem, note.Note):
                all_pitches.append(elem.pitch.midi)
                
                if prev_note is not None:
                    interval_semitones = elem.pitch.midi - prev_note.pitch.midi
                    all_intervals.append(interval_semitones)
                
                prev_note = elem
            elif isinstance(elem, note.Rest):
                # Rest breaks the melodic line
                prev_note = None
    
    if len(all_intervals) < 2:
        result.melodic_pattern_analysis = MelodicPatternAnalysis(
            total_motifs=0,
            unique_motifs=0,
            motif_uniqueness_ratio=0.0,
            motif_repetition_ratio=1.0,
        )
        return
    
    # Detect 3-note motifs (2 intervals)
    motif_counts_2: Counter[str] = Counter()  # 2-interval motifs
    for i in range(len(all_intervals) - 1):
        motif = f"{all_intervals[i]}_{all_intervals[i+1]}"
        motif_counts_2[motif] += 1
    
    # Detect 4-note motifs (3 intervals)
    motif_counts_3: Counter[str] = Counter()
    for i in range(len(all_intervals) - 2):
        motif = f"{all_intervals[i]}_{all_intervals[i+1]}_{all_intervals[i+2]}"
        motif_counts_3[motif] += 1
    
    # Combine motif counts (weight 3-interval motifs more)
    combined_counts: Counter[str] = Counter()
    for motif, count in motif_counts_2.items():
        combined_counts[motif] = count
    for motif, count in motif_counts_3.items():
        combined_counts[motif] += count * 2  # Weight longer patterns more
    
    total_motifs = sum(combined_counts.values())
    unique_motifs = len(combined_counts)
    
    if total_motifs == 0:
        result.melodic_pattern_analysis = MelodicPatternAnalysis(
            total_motifs=0,
            unique_motifs=0,
            motif_uniqueness_ratio=0.0,
            motif_repetition_ratio=1.0,
        )
        return
    
    uniqueness_ratio = unique_motifs / total_motifs if total_motifs > 0 else 0.0
    repetition_ratio = 1.0 - uniqueness_ratio
    
    # Detect longer sequences (4+ consecutive matching pitches)
    sequence_count = 0
    sequence_notes = 0
    
    if len(all_pitches) >= 8:
        # Look for repeated 4-note phrases
        phrase_length = 4
        seen_phrases = {}
        
        for i in range(len(all_pitches) - phrase_length + 1):
            phrase = tuple(all_pitches[i:i + phrase_length])
            # Normalize to relative intervals for comparison
            normalized = tuple(phrase[j+1] - phrase[j] for j in range(len(phrase) - 1))
            
            if normalized in seen_phrases:
                sequence_count += 1
                sequence_notes += phrase_length
            else:
                seen_phrases[normalized] = i
    
    sequence_coverage = sequence_notes / len(all_pitches) if all_pitches else 0.0
    
    # Find most common motif
    most_common = combined_counts.most_common(1)
    most_common_motif = most_common[0][0] if most_common else None
    most_common_count = most_common[0][1] if most_common else 0
    
    result.melodic_pattern_analysis = MelodicPatternAnalysis(
        total_motifs=total_motifs,
        unique_motifs=unique_motifs,
        motif_uniqueness_ratio=round(uniqueness_ratio, 4),
        motif_repetition_ratio=round(repetition_ratio, 4),
        sequence_count=sequence_count,
        sequence_total_notes=sequence_notes,
        sequence_coverage_ratio=round(sequence_coverage, 4),
        most_common_motif=most_common_motif,
        most_common_count=most_common_count,
    )
