"""
Interval Parser

Extraction of melodic and harmonic intervals from MusicXML scores.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from music21 import stream
    from .extraction_models import ExtractionResult

from .extraction_models import IntervalInfo


def extract_intervals(score: "stream.Score", result: "ExtractionResult"):
    """Extract melodic and harmonic intervals."""
    from music21 import note, chord, interval
    
    for part in score.parts:
        notes_only = [n for n in part.recurse().notes if isinstance(n, note.Note)]
        
        # Melodic intervals (consecutive notes)
        for i in range(len(notes_only) - 1):
            n1 = notes_only[i]
            n2 = notes_only[i + 1]
            
            try:
                intv = interval.Interval(n1, n2)
                info = _get_interval_info(intv, is_melodic=True)
                key_name = f"interval_melodic_{info.name}_{info.direction}"
                
                if key_name in result.melodic_intervals:
                    result.melodic_intervals[key_name].count += 1
                else:
                    result.melodic_intervals[key_name] = info
            except (ValueError, AttributeError, TypeError) as e:
                pass  # Skip problematic intervals
        
        # Harmonic intervals (within chords)
        for c in part.recurse().getElementsByClass(chord.Chord):
            pitches = c.pitches
            for i in range(len(pitches)):
                for j in range(i + 1, len(pitches)):
                    try:
                        intv = interval.Interval(pitches[i], pitches[j])
                        info = _get_interval_info(intv, is_melodic=False)
                        key_name = f"interval_harmonic_{info.name}"
                        
                        if key_name in result.harmonic_intervals:
                            result.harmonic_intervals[key_name].count += 1
                        else:
                            result.harmonic_intervals[key_name] = info
                    except (ValueError, AttributeError, TypeError) as e:
                        pass


def _get_interval_info(intv, is_melodic: bool) -> IntervalInfo:
    """Convert music21 interval to IntervalInfo."""
    from music21 import interval
    
    # Direction
    if intv.semitones > 0:
        direction = "ascending"
    elif intv.semitones < 0:
        direction = "descending"
    else:
        direction = "unison"
    
    # Quality and size
    quality = intv.specifier  # Returns like 'M' for major
    quality_names = {
        interval.Specifier.PERFECT: 'perfect',
        interval.Specifier.MAJOR: 'major',
        interval.Specifier.MINOR: 'minor',
        interval.Specifier.AUGMENTED: 'augmented',
        interval.Specifier.DIMINISHED: 'diminished',
    }
    quality_name = quality_names.get(quality, 'unknown')
    
    # Use simpleName for small intervals, but preserve octaves
    # (simpleName reduces P8 to P1 which loses information)
    abs_semitones = abs(intv.semitones)
    if abs_semitones == 12:
        # Exact octave - use P8
        interval_name = "P8"
    elif abs_semitones > 12:
        # Compound interval - use full name to preserve info
        interval_name = intv.name
    else:
        # Simple interval - use simple name
        interval_name = intv.simpleName
    
    return IntervalInfo(
        name=interval_name,
        direction=direction,
        quality=quality_name,
        semitones=abs_semitones,
        is_melodic=is_melodic,
    )
