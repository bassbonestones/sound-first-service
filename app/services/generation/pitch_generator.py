"""Pitch sequence generator for scales and arpeggios.

This is a pure generator - it produces what is requested without
any capability awareness. Capability filtering is handled by the
orchestration layer that builds GenerationRequest objects.

DESIGN PRINCIPLE: Origin-Based Generation
==========================================
All scales and arpeggios are generated fresh from their interval 
definitions starting from the root of the target key. We NEVER transpose
existing pitch sequences to a new key.

This ensures deterministic enharmonic spelling because:
- Each pitch is generated as (root_midi + interval)
- The KEY_ALTERATION_MAP lookup receives a fresh MIDI value
- There's no accumulation of transposition operations

Example (correct approach - what we do):
    G major scale: root=67, intervals=[2,2,1,2,2,2,1]
    → generates [67, 69, 71, 72, 74, 76, 78, 79]
    → KEY_ALTERATION_MAP spells each pitch in G major context

Avoided anti-pattern (chain transposition):
    C major in memory → transpose +7 → transpose +2 → ...
    This could lead to different spellings depending on the chain.
"""
from typing import List, Optional, Tuple

from app.schemas.generation_schemas import (
    ArpeggioType,
    GenerationRequest,
    GenerationType,
    MusicalKey,
    PitchEvent,
    ScaleType,
)
from .scale_definitions import SCALE_INTERVALS, get_scale_intervals
from .arpeggio_definitions import ARPEGGIO_INTERVALS, get_arpeggio_intervals


# =============================================================================
# Constants
# =============================================================================

# Key transposition offsets (semitones from C)
KEY_OFFSETS: dict[MusicalKey, int] = {
    MusicalKey.C: 0,
    MusicalKey.C_SHARP: 1,
    MusicalKey.D_FLAT: 1,
    MusicalKey.D: 2,
    MusicalKey.D_SHARP: 3,
    MusicalKey.E_FLAT: 3,
    MusicalKey.E: 4,
    MusicalKey.F: 5,
    MusicalKey.F_SHARP: 6,
    MusicalKey.G_FLAT: 6,
    MusicalKey.G: 7,
    MusicalKey.G_SHARP: 8,
    MusicalKey.A_FLAT: 8,
    MusicalKey.A: 9,
    MusicalKey.A_SHARP: 10,
    MusicalKey.B_FLAT: 10,
    MusicalKey.B: 11,
}

# MIDI reference: C4 = 60
DEFAULT_ROOT_MIDI = 60  # Middle C

# Pitch name mapping
PITCH_NAMES_SHARP = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
PITCH_NAMES_FLAT = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"]


# =============================================================================
# Helper Functions
# =============================================================================

def midi_to_pitch_name(midi_note: int, prefer_flats: bool = False) -> str:
    """Convert MIDI note number to pitch name with octave.
    
    Args:
        midi_note: MIDI note number (0-127).
        prefer_flats: If True, use flats (Bb) instead of sharps (A#).
        
    Returns:
        Pitch name with octave (e.g., "C4", "F#5", "Bb3").
    """
    octave = (midi_note // 12) - 1
    pitch_class = midi_note % 12
    names = PITCH_NAMES_FLAT if prefer_flats else PITCH_NAMES_SHARP
    return f"{names[pitch_class]}{octave}"


def get_key_offset(key: MusicalKey) -> int:
    """Get the semitone offset for a key relative to C.
    
    Args:
        key: The target key.
        
    Returns:
        Number of semitones to transpose from C.
    """
    return KEY_OFFSETS[key]


def should_use_flats(key: MusicalKey) -> bool:
    """Determine if a key conventionally uses flats.
    
    Args:
        key: The musical key.
        
    Returns:
        True if the key uses flats in its signature.
    """
    flat_keys = {
        MusicalKey.F, MusicalKey.B_FLAT, MusicalKey.E_FLAT,
        MusicalKey.A_FLAT, MusicalKey.D_FLAT, MusicalKey.G_FLAT,
    }
    return key in flat_keys


# =============================================================================
# Pitch Sequence Generator
# =============================================================================

class PitchSequenceGenerator:
    """Generates pitch sequences for scales and arpeggios.
    
    This is a stateless generator that produces pitch MIDI values
    based on the requested parameters. It handles:
    
    - Scale generation (using interval patterns)
    - Arpeggio generation (using chord tone intervals)
    - Transposition to any key
    - Octave extension
    - Range constraints (optional bounds)
    
    Example:
        generator = PitchSequenceGenerator()
        pitches = generator.generate_scale(
            scale_type=ScaleType.DORIAN,
            octaves=2,
            key=MusicalKey.F,
            range_low_midi=36,
            range_high_midi=84,
        )
    """
    
    def generate_scale(
        self,
        scale_type: ScaleType,
        octaves: int = 1,
        key: MusicalKey = MusicalKey.C,
        range_low_midi: Optional[int] = None,
        range_high_midi: Optional[int] = None,
        ascending: bool = True,
        include_top_note: bool = True,
    ) -> List[int]:
        """Generate a scale as a list of MIDI note numbers.
        
        Args:
            scale_type: The scale type to generate.
            octaves: Number of octaves to generate (1, 2, or 3).
            key: Target key for transposition.
            range_low_midi: Optional lower bound (inclusive).
            range_high_midi: Optional upper bound (inclusive).
            ascending: If True, generate ascending; if False, descending.
            include_top_note: If True, include the octave note at the top.
            
        Returns:
            List of MIDI note numbers.
        """
        intervals = get_scale_intervals(scale_type)
        key_offset = get_key_offset(key)
        
        # Determine starting note
        root_midi = self._calculate_root_midi(
            key_offset, range_low_midi, range_high_midi, intervals, octaves
        )
        
        # Build pitch sequence
        pitches = self._build_scale_pitches(
            root_midi, intervals, octaves, include_top_note
        )
        
        # Constrain to range if specified
        pitches = self._constrain_to_range(pitches, range_low_midi, range_high_midi)
        
        # Reverse if descending
        if not ascending:
            pitches = list(reversed(pitches))
        
        return pitches
    
    def generate_arpeggio(
        self,
        arpeggio_type: ArpeggioType,
        octaves: int = 1,
        key: MusicalKey = MusicalKey.C,
        range_low_midi: Optional[int] = None,
        range_high_midi: Optional[int] = None,
        ascending: bool = True,
    ) -> List[int]:
        """Generate an arpeggio as a list of MIDI note numbers.
        
        Args:
            arpeggio_type: The arpeggio type to generate.
            octaves: Number of octaves to span.
            key: Target key for transposition.
            range_low_midi: Optional lower bound (inclusive).
            range_high_midi: Optional upper bound (inclusive).
            ascending: If True, generate ascending; if False, descending.
            
        Returns:
            List of MIDI note numbers.
        """
        intervals = get_arpeggio_intervals(arpeggio_type)
        key_offset = get_key_offset(key)
        
        # Determine starting note
        root_midi = self._calculate_arpeggio_root(
            key_offset, range_low_midi, range_high_midi, intervals, octaves
        )
        
        # Build pitch sequence
        pitches = self._build_arpeggio_pitches(root_midi, intervals, octaves)
        
        # Constrain to range if specified
        pitches = self._constrain_to_range(pitches, range_low_midi, range_high_midi)
        
        # Reverse if descending
        if not ascending:
            pitches = list(reversed(pitches))
        
        return pitches
    
    def generate_from_request(
        self,
        request: GenerationRequest,
        ascending: bool = True,
    ) -> Tuple[List[int], int]:
        """Generate pitches from a GenerationRequest.
        
        Args:
            request: The generation request with all parameters.
            ascending: If True, generate ascending sequence.
            
        Returns:
            Tuple of (list of MIDI note numbers, effective octaves used).
            
        Raises:
            ValueError: If content_type is LICK (not supported here).
        """
        if request.content_type == GenerationType.LICK:
            raise ValueError(
                "Lick generation is not supported by PitchSequenceGenerator. "
                "Use the lick library instead."
            )
        
        if request.content_type == GenerationType.SCALE:
            scale_type = ScaleType(request.definition)
            pitches = self.generate_scale(
                scale_type=scale_type,
                octaves=request.octaves,
                key=request.key,
                range_low_midi=request.range_low_midi,
                range_high_midi=request.range_high_midi,
                ascending=ascending,
            )
        else:  # ARPEGGIO
            arpeggio_type = ArpeggioType(request.definition)
            pitches = self.generate_arpeggio(
                arpeggio_type=arpeggio_type,
                octaves=request.octaves,
                key=request.key,
                range_low_midi=request.range_low_midi,
                range_high_midi=request.range_high_midi,
                ascending=ascending,
            )
        
        # Calculate effective octaves from actual pitch range
        effective_octaves = self._calculate_effective_octaves(pitches)
        
        return pitches, effective_octaves
    
    def pitches_to_events(
        self,
        pitches: List[int],
        duration_beats: float = 1.0,
        use_flats: bool = False,
    ) -> List[PitchEvent]:
        """Convert MIDI pitches to PitchEvent objects.
        
        Args:
            pitches: List of MIDI note numbers.
            duration_beats: Duration for each note in beats.
            use_flats: If True, use flat names (Bb) instead of sharps (A#).
            
        Returns:
            List of PitchEvent objects with sequential offsets.
        """
        events: List[PitchEvent] = []
        offset = 0.0
        
        for midi_note in pitches:
            events.append(PitchEvent(
                midi_note=midi_note,
                pitch_name=midi_to_pitch_name(midi_note, prefer_flats=use_flats),
                duration_beats=duration_beats,
                offset_beats=offset,
            ))
            offset += duration_beats
        
        return events
    
    # =========================================================================
    # Private Methods
    # =========================================================================
    
    def _calculate_root_midi(
        self,
        key_offset: int,
        range_low: Optional[int],
        range_high: Optional[int],
        intervals: Tuple[int, ...],
        octaves: int,
    ) -> int:
        """Calculate the best starting MIDI note given constraints.
        
        Places the root as low as possible while fitting within range.
        """
        # Default to middle C + key offset
        default_root = DEFAULT_ROOT_MIDI + key_offset
        
        if range_low is None and range_high is None:
            return default_root
        
        # Calculate total span needed
        octave_span = sum(intervals)  # Usually 12
        total_span = octave_span * octaves
        
        if range_low is not None:
            # Find the lowest valid root (must be on the key)
            candidate = range_low
            # Adjust to be on the key
            while (candidate % 12) != (key_offset % 12):
                candidate += 1
            
            # Check if scale fits
            if range_high is None or (candidate + total_span) <= range_high:
                return candidate
        
        if range_high is not None:
            # Work backwards from high bound
            candidate = range_high - total_span
            # Adjust to be on the key
            while (candidate % 12) != (key_offset % 12):
                candidate += 1
            
            if range_low is None or candidate >= range_low:
                return candidate
        
        # Fall back to default, constrained
        return max(range_low or 0, min(default_root, (range_high or 127) - total_span))
    
    def _calculate_arpeggio_root(
        self,
        key_offset: int,
        range_low: Optional[int],
        range_high: Optional[int],
        intervals: Tuple[int, ...],
        octaves: int,
    ) -> int:
        """Calculate the best starting MIDI note for arpeggio."""
        default_root = DEFAULT_ROOT_MIDI + key_offset
        
        if range_low is None and range_high is None:
            return default_root
        
        # For arpeggios, intervals are from root, so max interval + 12*(octaves-1)
        top_interval = intervals[-1] if intervals else 0
        total_span = top_interval + 12 * (octaves - 1)
        
        if range_low is not None:
            candidate = range_low
            while (candidate % 12) != (key_offset % 12):
                candidate += 1
            
            if range_high is None or (candidate + total_span) <= range_high:
                return candidate
        
        if range_high is not None:
            candidate = range_high - total_span
            while (candidate % 12) != (key_offset % 12):
                candidate += 1
            
            if range_low is None or candidate >= range_low:
                return candidate
        
        return max(range_low or 0, min(default_root, (range_high or 127) - total_span))
    
    def _build_scale_pitches(
        self,
        root_midi: int,
        intervals: Tuple[int, ...],
        octaves: int,
        include_top_note: bool,
    ) -> List[int]:
        """Build the pitch sequence for a scale."""
        pitches = [root_midi]
        current = root_midi
        
        for octave_num in range(octaves):
            for interval in intervals:
                current += interval
                # Don't add the final octave note if not requested
                if octave_num == octaves - 1 and not include_top_note:
                    if current == root_midi + 12 * octaves:
                        continue
                pitches.append(current)
        
        # Remove duplicate top note if it was added
        if not include_top_note and len(pitches) > 1:
            if pitches[-1] == root_midi + 12 * octaves:
                pitches.pop()
        
        return pitches
    
    def _build_arpeggio_pitches(
        self,
        root_midi: int,
        intervals: Tuple[int, ...],
        octaves: int,
    ) -> List[int]:
        """Build the pitch sequence for an arpeggio.
        
        Pattern rules:
        - Triads (3 notes): add octave on top (do mi sol do = 4 notes)
        - 7ths (4 notes): just the chord tones, no octave (do mi sol te = 4 notes)
        - Extended (5+ notes): just the chord tones as-is
        """
        pitches = []
        is_triad = len(intervals) == 3
        
        # Build ascending through all octaves
        for octave_num in range(octaves):
            octave_offset = 12 * octave_num
            for interval in intervals:
                pitches.append(root_midi + interval + octave_offset)
        
        # Only add octave completion for triads
        if is_triad:
            final_octave_offset = 12 * octaves
            pitches.append(root_midi + final_octave_offset)
        
        return pitches
    
    def _constrain_to_range(
        self,
        pitches: List[int],
        range_low: Optional[int],
        range_high: Optional[int],
    ) -> List[int]:
        """Filter pitches to be within the specified range."""
        if range_low is None and range_high is None:
            return pitches
        
        result = []
        for p in pitches:
            if range_low is not None and p < range_low:
                continue
            if range_high is not None and p > range_high:
                continue
            result.append(p)
        
        return result
    
    def _calculate_effective_octaves(self, pitches: List[int]) -> int:
        """Calculate how many octaves the pitch list actually spans."""
        if len(pitches) < 2:
            return 1
        
        span = max(pitches) - min(pitches)
        # Round to nearest octave, minimum 1
        return max(1, (span + 6) // 12)
