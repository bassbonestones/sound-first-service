"""
Range Analyzer

Pitch range and chromatic complexity analysis.
"""

from collections import Counter
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music21 import stream
    from .extraction_models import ExtractionResult

from .extraction_models import RangeAnalysis, format_pitch_name


def analyze_range(score: "stream.Score", result: "ExtractionResult"):
    """Analyze pitch range and density."""
    from music21 import note, chord, pitch
    
    pitches_midi = []
    trill_pitches = []
    
    for n in score.recurse().notes:
        if isinstance(n, note.Note):
            pitches_midi.append(n.pitch.midi)
            
            # Check for trills
            for expr in n.expressions:
                if type(expr).__name__ == 'Trill':
                    trill_pitches.append(n.pitch.midi)
        elif isinstance(n, chord.Chord):
            for p in n.pitches:
                pitches_midi.append(p.midi)
    
    if not pitches_midi:
        return
    
    lowest_midi = min(pitches_midi)
    highest_midi = max(pitches_midi)
    range_semitones = highest_midi - lowest_midi
    
    # Calculate density
    if range_semitones > 0:
        low_threshold = lowest_midi + range_semitones / 3
        high_threshold = highest_midi - range_semitones / 3
        
        low_count = sum(1 for p in pitches_midi if p < low_threshold)
        high_count = sum(1 for p in pitches_midi if p > high_threshold)
        mid_count = len(pitches_midi) - low_count - high_count
        
        total = len(pitches_midi)
        density_low = low_count / total * 100
        density_mid = mid_count / total * 100
        density_high = high_count / total * 100
    else:
        density_low = density_mid = density_high = 33.33
    
    result.range_analysis = RangeAnalysis(
        lowest_pitch=format_pitch_name(pitch.Pitch(midi=lowest_midi).nameWithOctave),
        highest_pitch=format_pitch_name(pitch.Pitch(midi=highest_midi).nameWithOctave),
        lowest_midi=lowest_midi,
        highest_midi=highest_midi,
        range_semitones=range_semitones,
        density_low=round(density_low, 1),
        density_mid=round(density_mid, 1),
        density_high=round(density_high, 1),
        trill_lowest=format_pitch_name(pitch.Pitch(midi=min(trill_pitches)).nameWithOctave) if trill_pitches else None,
        trill_highest=format_pitch_name(pitch.Pitch(midi=max(trill_pitches)).nameWithOctave) if trill_pitches else None,
    )


def analyze_chromatic_complexity(score: "stream.Score", result: "ExtractionResult"):
    """Analyze accidentals outside key signature."""
    from music21 import note, chord, key
    
    # Get the key signature
    key_sigs = list(score.recurse().getElementsByClass(key.KeySignature))
    current_key = key_sigs[0] if key_sigs else key.KeySignature(0)
    
    # Get pitches that are "in key"
    if hasattr(current_key, 'asKey'):
        k = current_key.asKey()
        in_key_pitches = set(p.name for p in k.pitches)
    else:
        in_key_pitches = set(['C', 'D', 'E', 'F', 'G', 'A', 'B'])
    
    # Count accidentals outside key
    accidentals = Counter()
    total_notes = 0
    
    for n in score.recurse().notes:
        if isinstance(n, note.Note):
            total_notes += 1
            if n.pitch.name not in in_key_pitches:
                accidentals[n.pitch.name] += 1
        elif isinstance(n, chord.Chord):
            for p in n.pitches:
                total_notes += 1
                if p.name not in in_key_pitches:
                    accidentals[p.name] += 1
    
    result.accidentals_outside_key = dict(accidentals)
    
    # Chromatic complexity score (0-10)
    if total_notes > 0:
        chromatic_ratio = sum(accidentals.values()) / total_notes
        unique_alterations = len(accidentals)
        
        # Score based on ratio and variety of alterations
        result.chromatic_complexity_score = min(10.0, 
            chromatic_ratio * 20 + unique_alterations * 0.5)
