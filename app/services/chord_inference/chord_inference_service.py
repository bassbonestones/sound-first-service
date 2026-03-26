"""Chord inference service for analyzing melodies and suggesting chord progressions.

This service analyzes melody notes to suggest harmonically appropriate chord
progressions. It uses rule-based inference considering:
- Notes on strong beats (chord tones)
- Key signature context  
- Common harmonic progressions
- Voice leading principles

All chords are inferred in the key of the tune and returned as ChordSymbol objects.
"""
import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# Note name to pitch class mapping (C=0, C#/Db=1, ..., B=11)
NOTE_TO_PITCH_CLASS: Dict[str, int] = {
    "C": 0, "B#": 0,
    "C#": 1, "Db": 1,
    "D": 2,
    "D#": 3, "Eb": 3,
    "E": 4, "Fb": 4,
    "F": 5, "E#": 5,
    "F#": 6, "Gb": 6,
    "G": 7,
    "G#": 8, "Ab": 8,
    "A": 9,
    "A#": 10, "Bb": 10,
    "B": 11, "Cb": 11,
}

# Pitch class to note name (prefer flats for negative key sigs, sharps for positive)
PITCH_CLASS_TO_NOTE_SHARP: Dict[int, str] = {
    0: "C", 1: "C#", 2: "D", 3: "D#", 4: "E", 5: "F",
    6: "F#", 7: "G", 8: "G#", 9: "A", 10: "A#", 11: "B",
}
PITCH_CLASS_TO_NOTE_FLAT: Dict[int, str] = {
    0: "C", 1: "Db", 2: "D", 3: "Eb", 4: "E", 5: "F",
    6: "Gb", 7: "G", 8: "Ab", 9: "A", 10: "Bb", 11: "B",
}

# Circle of fifths for key signatures
# Positive = sharps, negative = flats
KEY_SIG_TO_ROOT: Dict[int, int] = {
    -7: 11,  # Cb
    -6: 6,   # Gb
    -5: 1,   # Db
    -4: 8,   # Ab
    -3: 3,   # Eb
    -2: 10,  # Bb
    -1: 5,   # F
    0: 0,    # C
    1: 7,    # G
    2: 2,    # D
    3: 9,    # A
    4: 4,    # E
    5: 11,   # B
    6: 6,    # F#
    7: 1,    # C#
}

# Chord intervals from root (in semitones) for different chord qualities
CHORD_INTERVALS: Dict[str, Tuple[int, ...]] = {
    # Triads
    "": (0, 4, 7),           # Major
    "m": (0, 3, 7),          # Minor
    "dim": (0, 3, 6),        # Diminished
    "aug": (0, 4, 8),        # Augmented
    
    # Seventh chords
    "maj7": (0, 4, 7, 11),   # Major 7
    "7": (0, 4, 7, 10),      # Dominant 7
    "m7": (0, 3, 7, 10),     # Minor 7
    "dim7": (0, 3, 6, 9),    # Diminished 7
    "m7b5": (0, 3, 6, 10),   # Half-diminished (m7b5)
}

# Scale degree to chord quality mapping for major keys
# Degrees are 0-indexed (0=I, 1=ii, 2=iii, etc.)
MAJOR_SCALE_CHORDS: Dict[int, Tuple[str, str]] = {
    0: ("", "maj7"),      # I - Major, Imaj7
    1: ("m", "m7"),       # ii - minor, ii7
    2: ("m", "m7"),       # iii - minor, iii7
    3: ("", "maj7"),      # IV - Major, IVmaj7
    4: ("", "7"),         # V - Major, V7
    5: ("m", "m7"),       # vi - minor, vi7
    6: ("dim", "m7b5"),   # vii° - diminished, viiø7
}

# Scale degrees (semitones from root) for major scale
MAJOR_SCALE_SEMITONES = (0, 2, 4, 5, 7, 9, 11)


@dataclass
class InferredChord:
    """A chord inferred from melody analysis."""
    
    root: str           # Root note name (e.g., "C", "F#")
    quality: str        # Chord quality (e.g., "", "m", "7", "maj7")
    beat_position: float  # Position within measure
    measure_index: int    # Measure number (0-indexed)
    confidence: float     # 0.0-1.0 confidence score
    
    @property
    def symbol(self) -> str:
        """Full chord symbol string."""
        return f"{self.root}{self.quality}"


class ChordInferenceService:
    """Service for inferring chord progressions from melodies.
    
    Analyzes melody notes to suggest harmonically appropriate chords.
    Uses rule-based inference considering strong beat notes and key context.
    """
    
    def __init__(self) -> None:
        """Initialize the chord inference service."""
        pass
    
    def infer_chords_from_measures(
        self,
        measures_json: str,
        key_signature: int = 0,
        time_signature: Optional[Dict[str, int]] = None,
        use_seventh_chords: bool = True,
        chords_per_measure: int = 1,
    ) -> List[InferredChord]:
        """Infer chord progression from melody measures.
        
        Args:
            measures_json: JSON string of measures array from Tune model.
            key_signature: Key signature (-7 to 7, negative=flats, positive=sharps).
            time_signature: Time signature dict with 'beats' and 'beatUnit'.
            use_seventh_chords: Whether to use 7th chords or just triads.
            chords_per_measure: Number of chords to infer per measure (1 or 2).
            
        Returns:
            List of InferredChord objects representing the progression.
        """
        if time_signature is None:
            time_signature = {"beats": 4, "beatUnit": 4}
            
        measures = json.loads(measures_json)
        if not measures:
            return []
        
        tonic_pitch_class = KEY_SIG_TO_ROOT.get(key_signature, 0)
        use_flats = key_signature < 0
        
        inferred_chords: List[InferredChord] = []
        
        for measure_index, measure in enumerate(measures):
            notes = measure.get("notes", [])
            if not notes:
                continue
            
            # Get chord(s) for this measure
            if chords_per_measure == 2 and time_signature["beats"] >= 4:
                # Split measure into two halves
                half_beat = time_signature["beats"] / 2
                first_half_notes = self._get_notes_in_beat_range(notes, 0, half_beat)
                second_half_notes = self._get_notes_in_beat_range(notes, half_beat, time_signature["beats"])
                
                if first_half_notes:
                    chord = self._infer_chord_from_notes(
                        first_half_notes, tonic_pitch_class, use_flats, use_seventh_chords
                    )
                    if chord:
                        inferred_chords.append(InferredChord(
                            root=chord[0],
                            quality=chord[1],
                            beat_position=0.0,
                            measure_index=measure_index,
                            confidence=chord[2],
                        ))
                
                if second_half_notes:
                    chord = self._infer_chord_from_notes(
                        second_half_notes, tonic_pitch_class, use_flats, use_seventh_chords
                    )
                    if chord:
                        inferred_chords.append(InferredChord(
                            root=chord[0],
                            quality=chord[1],
                            beat_position=half_beat,
                            measure_index=measure_index,
                            confidence=chord[2],
                        ))
            else:
                # One chord for whole measure
                chord = self._infer_chord_from_notes(
                    notes, tonic_pitch_class, use_flats, use_seventh_chords
                )
                if chord:
                    inferred_chords.append(InferredChord(
                        root=chord[0],
                        quality=chord[1],
                        beat_position=0.0,
                        measure_index=measure_index,
                        confidence=chord[2],
                    ))
        
        return inferred_chords
    
    def _get_notes_in_beat_range(
        self,
        notes: List[Dict[str, Any]],
        start_beat: float,
        end_beat: float,
    ) -> List[Dict[str, Any]]:
        """Filter notes that fall within a beat range."""
        result = []
        current_beat = 0.0
        
        for note in notes:
            duration = note.get("duration", 1.0)
            note_start = current_beat
            note_end = current_beat + duration
            
            # Include note if it overlaps with range
            if note_start < end_beat and note_end > start_beat:
                result.append(note)
            
            current_beat = note_end
        
        return result
    
    def _infer_chord_from_notes(
        self,
        notes: List[Dict[str, Any]],
        tonic_pitch_class: int,
        use_flats: bool,
        use_seventh_chords: bool,
    ) -> Optional[Tuple[str, str, float]]:
        """Infer the best chord for a group of notes.
        
        Uses a combination of factors:
        - Beat position (strong beats matter more)
        - Note duration (longer notes are often chord tones)
        - Resolution patterns (4-3, 7-8 suspensions resolve TO chord tones)
        
        Args:
            notes: List of note dicts with 'pitch' or 'isRest'.
            tonic_pitch_class: Pitch class of the key (0=C).
            use_flats: Whether to use flat note names.
            use_seventh_chords: Whether to prefer 7th chords.
            
        Returns:
            Tuple of (root_name, quality, confidence) or None if no chord.
        """
        # Build list of (pitch_class, base_weight, is_resolution_target) tuples
        note_data: List[Tuple[int, float, bool]] = []
        
        current_beat = 0.0
        pitched_notes = []  # (pitch_class, duration, beat_position)
        
        # First pass: collect all pitched notes
        for note in notes:
            if note.get("isRest", False):
                current_beat += note.get("duration", 1.0)
                continue
            
            pitch = note.get("pitch")
            if pitch is not None:
                pc = pitch % 12
                duration = note.get("duration", 1.0)
                pitched_notes.append((pc, duration, current_beat))
            
            current_beat += note.get("duration", 1.0)
        
        if not pitched_notes:
            return None
        
        # Second pass: detect resolution patterns and compute weights
        for i, (pc, duration, beat_pos) in enumerate(pitched_notes):
            # Base weight from beat position
            beat_weight = 1.0
            if beat_pos % 2 == 0:  # Beat 1 or 3
                beat_weight = 1.5
            if beat_pos == 0:  # Beat 1
                beat_weight = 2.0
            
            # Duration weight: longer notes are more likely chord tones
            # Half note = 2.0, quarter = 1.0, eighth = 0.5
            duration_weight = min(duration, 2.0)  # Cap at 2 beats
            
            # Check if this note is a resolution target (came from step above/below)
            is_resolution_target = False
            if i > 0:
                prev_pc, prev_dur, _ = pitched_notes[i - 1]
                interval = abs(pc - prev_pc) % 12
                # Step-wise motion (1 or 2 semitones) from shorter to longer note
                if interval in (1, 2, 10, 11) and duration > prev_dur:
                    is_resolution_target = True
            
            # Check if this note resolves TO the next note (it's a suspension)
            is_suspension = False
            if i < len(pitched_notes) - 1:
                next_pc, next_dur, _ = pitched_notes[i + 1]
                interval = abs(pc - next_pc) % 12
                # Step-wise motion to a longer note = this is likely a suspension
                if interval in (1, 2, 10, 11) and next_dur > duration:
                    is_suspension = True
            
            # Combine weights
            base_weight = beat_weight * duration_weight
            
            # Boost resolution targets significantly (the E in F→E)
            if is_resolution_target:
                base_weight *= 2.0
            
            # Reduce weight of suspensions (the F in F→E)
            if is_suspension:
                base_weight *= 0.3
            
            note_data.append((pc, base_weight, is_resolution_target))
        
        # Extract for scoring
        pitch_classes = [nd[0] for nd in note_data]
        weights = [nd[1] for nd in note_data]
        
        # Try each scale degree as potential root and find best match
        best_match: Optional[Tuple[str, str, float]] = None
        best_score = 0.0
        
        for degree in range(7):
            # Calculate root pitch class from scale degree
            root_pc = (tonic_pitch_class + MAJOR_SCALE_SEMITONES[degree]) % 12
            
            # Get appropriate chord quality for this degree
            triad_quality, seventh_quality = MAJOR_SCALE_CHORDS[degree]
            quality = seventh_quality if use_seventh_chords else triad_quality
            
            # Score how well notes fit this chord
            chord_tones = self._get_chord_tones(root_pc, quality)
            score = self._score_chord_fit(pitch_classes, weights, chord_tones)
            
            if score > best_score:
                best_score = score
                # Get note name
                pitch_lookup = PITCH_CLASS_TO_NOTE_FLAT if use_flats else PITCH_CLASS_TO_NOTE_SHARP
                root_name = pitch_lookup[root_pc]
                best_match = (root_name, quality, score)
        
        # Apply minimum confidence threshold
        if best_match and best_match[2] >= 0.3:
            return best_match
        
        # Fallback to tonic chord if nothing matches well
        pitch_lookup = PITCH_CLASS_TO_NOTE_FLAT if use_flats else PITCH_CLASS_TO_NOTE_SHARP
        root_name = pitch_lookup[tonic_pitch_class]
        quality = "maj7" if use_seventh_chords else ""
        return (root_name, quality, 0.3)
    
    def _get_chord_tones(self, root_pc: int, quality: str) -> Tuple[int, ...]:
        """Get the pitch classes of chord tones for a chord.
        
        Args:
            root_pc: Root pitch class (0-11).
            quality: Chord quality string.
            
        Returns:
            Tuple of pitch classes (0-11) for each chord tone.
        """
        intervals = CHORD_INTERVALS.get(quality, CHORD_INTERVALS[""])
        return tuple((root_pc + interval) % 12 for interval in intervals)
    
    def _score_chord_fit(
        self,
        pitch_classes: List[int],
        weights: List[float],
        chord_tones: Tuple[int, ...],
    ) -> float:
        """Score how well a set of pitch classes fits a chord.
        
        Args:
            pitch_classes: List of pitch classes from melody.
            weights: Corresponding weights for each pitch.
            chord_tones: Pitch classes of the chord.
            
        Returns:
            Score from 0.0 to 1.0 indicating fit quality.
        """
        if not pitch_classes:
            return 0.0
        
        total_weight = sum(weights)
        matching_weight = 0.0
        
        for pc, weight in zip(pitch_classes, weights):
            if pc in chord_tones:
                matching_weight += weight
            else:
                # Check if it's a passing tone (2 semitones from a chord tone)
                is_passing = any(abs((pc - ct) % 12) <= 2 or abs((ct - pc) % 12) <= 2 
                                for ct in chord_tones)
                if is_passing:
                    matching_weight += weight * 0.3  # Partial credit
        
        return matching_weight / total_weight if total_weight > 0 else 0.0
    
    def to_chord_progression_dict(
        self,
        inferred_chords: List[InferredChord],
        name: str = "Auto-Inferred",
    ) -> Dict[str, Any]:
        """Convert inferred chords to a ChordProgression dict.
        
        Args:
            inferred_chords: List of InferredChord objects.
            name: Name for the progression.
            
        Returns:
            Dict matching ChordProgression schema.
        """
        return {
            "id": str(uuid.uuid4()),
            "name": name,
            "isDefault": False,
            "isAutoInferred": True,
            "isSystemDefined": True,
            "chords": [
                {
                    "id": str(uuid.uuid4()),
                    "symbol": chord.symbol,
                    "beatPosition": chord.beat_position,
                    "measureIndex": chord.measure_index,
                }
                for chord in inferred_chords
            ],
        }
