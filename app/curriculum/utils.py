"""
Utility functions for note/MIDI conversions and key transposition.
"""

import re


# MIDI note mapping for range calculations
NOTE_TO_MIDI = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11
}

# Pitch content for each key when transposing - estimates the range shift
# Positive = higher, Negative = lower (relative to C)
KEY_TRANSPOSITION_OFFSET = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}


def note_to_midi(note_str: str) -> int:
    """Convert note string like 'C4', 'Bb3', 'F#5' to MIDI number."""
    if not note_str:
        return 60  # default to middle C
    
    match = re.match(r'([A-Ga-g])([#b]?)(\d+)', note_str)
    if not match:
        return 60
    
    note, accidental, octave = match.groups()
    midi = NOTE_TO_MIDI.get(note.upper(), 0)
    
    if accidental == '#':
        midi += 1
    elif accidental == 'b':
        midi -= 1
    
    return midi + (int(octave) + 1) * 12


def midi_to_note(midi: int) -> str:
    """Convert MIDI number to note string."""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi // 12) - 1
    note = notes[midi % 12]
    return f"{note}{octave}"
