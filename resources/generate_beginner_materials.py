#!/usr/bin/env python3
"""
Generate beginner MusicXML materials for Sound First curriculum.

All materials generated in C major, bass clef, 4/4 time, range C3-C4.
Engine transposes to user's comfortable range at runtime.

Usage:
    python resources/generate_beginner_materials.py [--output-dir musicxml]
"""

import argparse
from pathlib import Path
from music21 import (
    stream, note, meter, clef, key, tempo,
    articulations, expressions, spanner, metadata
)


def create_base_score(title: str, tempo_bpm: int = 72) -> stream.Score:
    """Create a base score with standard settings."""
    score = stream.Score()
    part = stream.Part()
    
    # Add metadata
    score.insert(0, tempo.MetronomeMark(number=tempo_bpm))
    
    # First measure setup
    m1 = stream.Measure(number=1)
    m1.append(clef.BassClef())
    m1.append(key.Key('C'))
    m1.append(meter.TimeSignature('4/4'))
    part.append(m1)
    
    score.append(part)
    score.metadata = metadata.Metadata()
    score.metadata.title = title
    
    return score


def add_notes_to_score(score: stream.Score, notes_data: list[tuple]) -> None:
    """
    Add notes to the score's first part.
    
    notes_data: list of (pitch, duration, articulation) tuples
                pitch: 'C3', 'D3', etc. or 'rest'
                duration: 'whole', 'half', 'quarter', 'eighth'
                articulation: None, 'staccato', 'legato_start', 'legato_end'
    """
    part = score.parts[0]
    current_measure = part.getElementsByClass(stream.Measure)[-1]
    measure_duration = 4.0  # 4/4 time
    current_duration = sum(n.duration.quarterLength for n in current_measure.notes)
    
    duration_map = {
        'whole': 4.0,
        'half': 2.0,
        'quarter': 1.0,
        'eighth': 0.5,
    }
    
    slur_notes = []
    
    for pitch, dur_name, artic in notes_data:
        dur = duration_map[dur_name]
        
        # Check if we need a new measure
        if current_duration + dur > measure_duration:
            current_measure = stream.Measure(number=current_measure.number + 1)
            part.append(current_measure)
            current_duration = 0
        
        # Create note or rest
        if pitch == 'rest':
            n = note.Rest(quarterLength=dur)
        else:
            n = note.Note(pitch, quarterLength=dur)
            
            # Add articulation
            if artic == 'staccato':
                n.articulations.append(articulations.Staccato())
            elif artic == 'accent':
                n.articulations.append(articulations.Accent())
            elif artic in ('legato_start', 'legato_end'):
                slur_notes.append(n)
                if artic == 'legato_end' and len(slur_notes) >= 2:
                    # Create slur spanning the accumulated notes
                    sl = spanner.Slur(slur_notes)
                    part.insert(0, sl)
                    slur_notes = []
        
        current_measure.append(n)
        current_duration += dur


def generate_long_tone_whole() -> stream.Score:
    """Long tones on whole notes - C3, D3, E3, F3, G3."""
    score = create_base_score("Long Tones - Whole Notes", tempo_bpm=60)
    
    notes = [
        ('C3', 'whole', None),
        ('D3', 'whole', None),
        ('E3', 'whole', None),
        ('F3', 'whole', None),
        ('G3', 'whole', None),
        ('F3', 'whole', None),
        ('E3', 'whole', None),
        ('D3', 'whole', None),
        ('C3', 'whole', None),
    ]
    
    add_notes_to_score(score, notes)
    return score


def generate_long_tone_half() -> stream.Score:
    """Long tones on half notes."""
    score = create_base_score("Long Tones - Half Notes", tempo_bpm=72)
    
    notes = [
        ('C3', 'half', None), ('D3', 'half', None),
        ('E3', 'half', None), ('F3', 'half', None),
        ('G3', 'half', None), ('F3', 'half', None),
        ('E3', 'half', None), ('D3', 'half', None),
        ('C3', 'half', None), ('rest', 'half', None),
    ]
    
    add_notes_to_score(score, notes)
    return score


def generate_quarter_pulse() -> stream.Score:
    """Steady quarter note pulse on C3-E3-G3 pattern."""
    score = create_base_score("Quarter Note Pulse", tempo_bpm=80)
    
    # 4 measures of quarter notes
    notes = []
    pattern = ['C3', 'E3', 'G3', 'E3']
    for _ in range(4):
        for pitch in pattern:
            notes.append((pitch, 'quarter', None))
    
    add_notes_to_score(score, notes)
    return score


def generate_rest_recognition() -> stream.Score:
    """Notes interspersed with various rests."""
    score = create_base_score("Rest Recognition", tempo_bpm=72)
    
    notes = [
        # Measure 1: whole rest
        ('rest', 'whole', None),
        # Measure 2: note then half rest
        ('C3', 'half', None), ('rest', 'half', None),
        # Measure 3: note, quarter rest, note, quarter rest
        ('D3', 'quarter', None), ('rest', 'quarter', None),
        ('E3', 'quarter', None), ('rest', 'quarter', None),
        # Measure 4: alternating quarters
        ('F3', 'quarter', None), ('rest', 'quarter', None),
        ('G3', 'quarter', None), ('rest', 'quarter', None),
        # Measure 5: half note + half rest
        ('G3', 'half', None), ('rest', 'half', None),
        # Measure 6: whole note
        ('C3', 'whole', None),
    ]
    
    add_notes_to_score(score, notes)
    return score


def generate_stepwise_M2_up() -> stream.Score:
    """Do-Re-Do patterns (Major 2nd ascending focus)."""
    score = create_base_score("Stepwise - Major 2nd Up", tempo_bpm=76)
    
    notes = [
        # Pattern 1: C-D-C
        ('C3', 'quarter', None), ('D3', 'quarter', None),
        ('C3', 'half', None),
        # Pattern 2: D-E-D
        ('D3', 'quarter', None), ('E3', 'quarter', None),
        ('D3', 'half', None),
        # Pattern 3: E-F-E (m2 but good prep)
        ('E3', 'quarter', None), ('F3', 'quarter', None),
        ('E3', 'half', None),
        # Pattern 4: F-G-F
        ('F3', 'quarter', None), ('G3', 'quarter', None),
        ('F3', 'half', None),
        # Final long C
        ('C3', 'whole', None),
    ]
    
    add_notes_to_score(score, notes)
    return score


def generate_stepwise_M2_down() -> stream.Score:
    """Re-Do-Re patterns (Major 2nd descending focus)."""
    score = create_base_score("Stepwise - Major 2nd Down", tempo_bpm=76)
    
    notes = [
        # Pattern 1: D-C-D
        ('D3', 'quarter', None), ('C3', 'quarter', None),
        ('D3', 'half', None),
        # Pattern 2: E-D-E
        ('E3', 'quarter', None), ('D3', 'quarter', None),
        ('E3', 'half', None),
        # Pattern 3: G-F-G
        ('G3', 'quarter', None), ('F3', 'quarter', None),
        ('G3', 'half', None),
        # Pattern 4: F-E-F
        ('F3', 'quarter', None), ('E3', 'quarter', None),
        ('F3', 'half', None),
        # Final long C
        ('C3', 'whole', None),
    ]
    
    add_notes_to_score(score, notes)
    return score


def generate_skip_M3_exercise() -> stream.Score:
    """Do-Mi-Do patterns (Major 3rd focus)."""
    score = create_base_score("Skip Exercise - Major 3rd", tempo_bpm=72)
    
    notes = [
        # C-E-C (M3)
        ('C3', 'quarter', None), ('E3', 'quarter', None),
        ('C3', 'half', None),
        # E-C-E (M3 down then up)
        ('E3', 'quarter', None), ('C3', 'quarter', None),
        ('E3', 'half', None),
        # D-F-D (m3 but good contrast)
        ('D3', 'quarter', None), ('F3', 'quarter', None),
        ('D3', 'half', None),
        # E-G-E (m3)
        ('E3', 'quarter', None), ('G3', 'quarter', None),
        ('E3', 'half', None),
        # Final pattern: arpeggiate down
        ('G3', 'quarter', None), ('E3', 'quarter', None),
        ('C3', 'half', None),
    ]
    
    add_notes_to_score(score, notes)
    return score


def generate_five_note_scale() -> stream.Score:
    """C-D-E-F-G pentascale patterns."""
    score = create_base_score("Five Note Scale", tempo_bpm=80)
    
    notes = [
        # Up the scale
        ('C3', 'quarter', None), ('D3', 'quarter', None),
        ('E3', 'quarter', None), ('F3', 'quarter', None),
        # Top + down
        ('G3', 'half', None), ('F3', 'quarter', None), ('E3', 'quarter', None),
        # Continue down
        ('D3', 'quarter', None), ('C3', 'quarter', None),
        ('C3', 'half', None),
        # Up again (half notes)
        ('C3', 'half', None), ('D3', 'half', None),
        ('E3', 'half', None), ('F3', 'half', None),
        ('G3', 'whole', None),
    ]
    
    add_notes_to_score(score, notes)
    return score


def generate_legato_pairs() -> stream.Score:
    """Slurred note pairs for legato practice."""
    score = create_base_score("Legato Pairs", tempo_bpm=72)
    
    notes = [
        # Pair 1: C-D slurred
        ('C3', 'half', 'legato_start'), ('D3', 'half', 'legato_end'),
        # Pair 2: E-F slurred
        ('E3', 'half', 'legato_start'), ('F3', 'half', 'legato_end'),
        # Pair 3: G-F slurred (descending)
        ('G3', 'half', 'legato_start'), ('F3', 'half', 'legato_end'),
        # Pair 4: E-D slurred
        ('E3', 'half', 'legato_start'), ('D3', 'half', 'legato_end'),
        # Final pair: D-C
        ('D3', 'half', 'legato_start'), ('C3', 'half', 'legato_end'),
        # Hold final
        ('C3', 'whole', None),
    ]
    
    add_notes_to_score(score, notes)
    return score


def generate_staccato_intro() -> stream.Score:
    """Detached quarter notes for staccato practice."""
    score = create_base_score("Staccato Introduction", tempo_bpm=84)
    
    notes = [
        # Detached quarters
        ('C3', 'quarter', 'staccato'), ('C3', 'quarter', 'staccato'),
        ('C3', 'quarter', 'staccato'), ('C3', 'quarter', 'staccato'),
        # Move up
        ('D3', 'quarter', 'staccato'), ('D3', 'quarter', 'staccato'),
        ('E3', 'quarter', 'staccato'), ('E3', 'quarter', 'staccato'),
        # Pattern
        ('C3', 'quarter', 'staccato'), ('E3', 'quarter', 'staccato'),
        ('G3', 'quarter', 'staccato'), ('E3', 'quarter', 'staccato'),
        # Down
        ('D3', 'quarter', 'staccato'), ('C3', 'quarter', 'staccato'),
        ('C3', 'half', None),  # Long final note (not staccato)
    ]
    
    add_notes_to_score(score, notes)
    return score


def generate_eighth_note_intro() -> stream.Score:
    """Introduction to eighth notes with quarter note support."""
    score = create_base_score("Eighth Note Introduction", tempo_bpm=72)
    
    notes = [
        # Quarters first (establish pulse)
        ('C3', 'quarter', None), ('C3', 'quarter', None),
        ('C3', 'quarter', None), ('C3', 'quarter', None),
        # Introduce eighths on same note
        ('C3', 'eighth', None), ('C3', 'eighth', None),
        ('C3', 'eighth', None), ('C3', 'eighth', None),
        ('C3', 'quarter', None), ('C3', 'quarter', None),
        # Eighth note scale fragment
        ('C3', 'eighth', None), ('D3', 'eighth', None),
        ('E3', 'eighth', None), ('F3', 'eighth', None),
        ('G3', 'half', None),
        # Mixed rhythm
        ('G3', 'quarter', None),
        ('F3', 'eighth', None), ('E3', 'eighth', None),
        ('D3', 'quarter', None), ('C3', 'quarter', None),
        # Final
        ('C3', 'whole', None),
    ]
    
    add_notes_to_score(score, notes)
    return score


def generate_simple_melody() -> stream.Score:
    """Simple tune combining whole, half, and quarter notes."""
    score = create_base_score("Simple Melody", tempo_bpm=76)
    
    # A simple, singable tune in C
    notes = [
        # Phrase 1
        ('C3', 'quarter', None), ('D3', 'quarter', None),
        ('E3', 'half', None),
        ('E3', 'quarter', None), ('F3', 'quarter', None),
        ('G3', 'half', None),
        # Phrase 2
        ('G3', 'quarter', None), ('F3', 'quarter', None),
        ('E3', 'quarter', None), ('D3', 'quarter', None),
        ('C3', 'whole', None),
        # Phrase 3 (variation)
        ('E3', 'half', None), ('D3', 'half', None),
        ('C3', 'half', None), ('E3', 'half', None),
        # Ending
        ('D3', 'quarter', None), ('E3', 'quarter', None),
        ('D3', 'quarter', None), ('C3', 'quarter', None),
        ('C3', 'whole', None),
    ]
    
    add_notes_to_score(score, notes)
    return score


# Map of filename to generator function
MATERIAL_GENERATORS = {
    'long_tone_whole.musicxml': generate_long_tone_whole,
    'long_tone_half.musicxml': generate_long_tone_half,
    'quarter_pulse.musicxml': generate_quarter_pulse,
    'rest_recognition.musicxml': generate_rest_recognition,
    'stepwise_M2_up.musicxml': generate_stepwise_M2_up,
    'stepwise_M2_down.musicxml': generate_stepwise_M2_down,
    'skip_M3_exercise.musicxml': generate_skip_M3_exercise,
    'five_note_scale.musicxml': generate_five_note_scale,
    'legato_pairs.musicxml': generate_legato_pairs,
    'staccato_intro.musicxml': generate_staccato_intro,
    'eighth_note_intro.musicxml': generate_eighth_note_intro,
    'simple_melody.musicxml': generate_simple_melody,
}


def main():
    parser = argparse.ArgumentParser(description='Generate beginner MusicXML materials')
    parser.add_argument('--output-dir', default='musicxml', 
                        help='Output directory for generated files')
    parser.add_argument('--files', nargs='*', 
                        help='Specific files to generate (default: all)')
    args = parser.parse_args()
    
    # Resolve output directory relative to script location
    script_dir = Path(__file__).parent.parent
    output_dir = script_dir / args.output_dir
    output_dir.mkdir(exist_ok=True)
    
    # Determine which files to generate
    files_to_generate = args.files if args.files else MATERIAL_GENERATORS.keys()
    
    print(f"Generating materials to: {output_dir}")
    print("-" * 50)
    
    for filename in files_to_generate:
        if filename not in MATERIAL_GENERATORS:
            print(f"  [SKIP] Unknown file: {filename}")
            continue
        
        generator = MATERIAL_GENERATORS[filename]
        score = generator()
        
        output_path = output_dir / filename
        score.write('musicxml', fp=str(output_path))
        print(f"  [OK] {filename}")
    
    print("-" * 50)
    print(f"Generated {len(files_to_generate)} files")


if __name__ == '__main__':
    main()
