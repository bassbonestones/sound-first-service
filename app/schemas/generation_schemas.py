"""Generation engine Pydantic schemas.

Defines request/response models for the musical content generation engine.
All content is authored in C major/A minor and transposed to target keys.
"""
from enum import Enum
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator, model_validator


# =============================================================================
# Enums - Strict typing for all generation parameters
# =============================================================================


class GenerationType(str, Enum):
    """Type of musical content to generate."""

    SCALE = "scale"
    ARPEGGIO = "arpeggio"
    LICK = "lick"


class ScaleType(str, Enum):
    """Scale types supported by the generation engine.

    Organized by family for clarity.
    """

    # Major scale modes
    IONIAN = "ionian"  # Major scale
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    AEOLIAN = "aeolian"  # Natural minor
    LOCRIAN = "locrian"

    # Harmonic minor modes
    HARMONIC_MINOR = "harmonic_minor"
    LOCRIAN_NAT6 = "locrian_nat6"
    IONIAN_AUG = "ionian_aug"
    DORIAN_SHARP4 = "dorian_sharp4"
    PHRYGIAN_DOMINANT = "phrygian_dominant"
    LYDIAN_SHARP2 = "lydian_sharp2"
    SUPER_LOCRIAN_BB7 = "super_locrian_bb7"

    # Melodic minor modes
    MELODIC_MINOR = "melodic_minor"  # Jazz melodic minor (same both ways)
    MELODIC_MINOR_CLASSICAL = "melodic_minor_classical"  # Classical (natural minor descending)
    DORIAN_FLAT2 = "dorian_flat2"
    LYDIAN_AUGMENTED = "lydian_augmented"
    LYDIAN_DOMINANT = "lydian_dominant"
    MIXOLYDIAN_FLAT6 = "mixolydian_flat6"
    LOCRIAN_NAT2 = "locrian_nat2"
    ALTERED = "altered"  # Super Locrian

    # Harmonic major modes
    HARMONIC_MAJOR = "harmonic_major"  # Ionian b6
    DORIAN_FLAT5 = "dorian_flat5"  # 2nd mode
    PHRYGIAN_FLAT4 = "phrygian_flat4"  # 3rd mode
    LYDIAN_FLAT3 = "lydian_flat3"  # 4th mode (Melodic Minor #4)
    MIXOLYDIAN_FLAT2 = "mixolydian_flat2"  # 5th mode
    LYDIAN_AUG_SHARP2 = "lydian_aug_sharp2"  # 6th mode
    LOCRIAN_DOUBLE_FLAT7 = "locrian_double_flat7"  # 7th mode

    # Pentatonic
    PENTATONIC_MAJOR = "pentatonic_major"
    PENTATONIC_MINOR = "pentatonic_minor"

    # Blues
    BLUES = "blues"
    BLUES_MAJOR = "blues_major"

    # Symmetric
    WHOLE_TONE = "whole_tone"
    DIMINISHED_HW = "diminished_hw"  # Half-whole
    DIMINISHED_WH = "diminished_wh"  # Whole-half
    CHROMATIC = "chromatic"

    # Bebop
    BEBOP_DOMINANT = "bebop_dominant"
    BEBOP_MAJOR = "bebop_major"
    BEBOP_DORIAN = "bebop_dorian"


class ArpeggioType(str, Enum):
    """Arpeggio/chord types supported by the generation engine."""

    # Triads
    MAJOR = "major"
    MINOR = "minor"
    AUGMENTED = "augmented"
    DIMINISHED = "diminished"
    SUS4 = "sus4"
    SUS2 = "sus2"

    # Seventh chords
    MAJOR_7 = "maj7"
    DOMINANT_7 = "dom7"
    MINOR_7 = "min7"
    MINOR_MAJOR_7 = "min_maj7"
    HALF_DIMINISHED = "half_dim7"
    DIMINISHED_7 = "dim7"
    AUGMENTED_MAJOR_7 = "aug_maj7"
    AUGMENTED_7 = "aug7"
    DOMINANT_7_SUS4 = "dom7sus4"

    # Extended chords
    MAJOR_9 = "maj9"
    DOMINANT_9 = "dom9"
    MINOR_9 = "min9"
    MAJOR_11 = "maj11"
    DOMINANT_11 = "dom11"
    MINOR_11 = "min11"
    MAJOR_13 = "maj13"
    DOMINANT_13 = "dom13"

    # Altered dominants
    DOMINANT_7_FLAT9 = "dom7b9"
    DOMINANT_7_SHARP9 = "dom7s9"
    DOMINANT_7_SHARP11 = "dom7s11"
    DOMINANT_7_FLAT13 = "dom7b13"
    ALTERED = "dom7alt"


class ScalePattern(str, Enum):
    """Pattern algorithms for scale practice."""

    # Basic
    STRAIGHT_UP = "straight_up"
    STRAIGHT_DOWN = "straight_down"
    STRAIGHT_UP_DOWN = "straight_up_down"
    STRAIGHT_DOWN_UP = "straight_down_up"

    # Pyramid (cumulative reach)
    PYRAMID_ASCEND = "pyramid_ascend"  # 1-2-1, 1-2-3-2-1, ...
    PYRAMID_DESCEND = "pyramid_descend"  # 7-6-7, 7-6-5-6-7, ...

    # Intervals (diatonic naming - see constraints for chromatic equivalents)
    IN_3RDS = "in_3rds"
    IN_4THS = "in_4ths"
    IN_5THS = "in_5ths"
    IN_6THS = "in_6ths"
    IN_7THS = "in_7ths"
    IN_OCTAVES = "in_octaves"
    
    # Extended intervals (primarily for chromatic scale, but work for all)
    IN_9THS = "in_9ths"    # Chromatic: m6
    IN_10THS = "in_10ths"  # Chromatic: M6
    IN_11THS = "in_11ths"  # Chromatic: m7
    IN_12THS = "in_12ths"  # Chromatic: M7
    IN_13THS = "in_13ths"  # Chromatic: P8 (octave)

    # Sequences/groups
    GROUPS_OF_3 = "groups_of_3"  # 1-2-3, 2-3-4, ...
    GROUPS_OF_4 = "groups_of_4"
    GROUPS_OF_5 = "groups_of_5"
    GROUPS_OF_6 = "groups_of_6"
    GROUPS_OF_7 = "groups_of_7"
    GROUPS_OF_8 = "groups_of_8"   # For diminished (8 notes) and larger
    GROUPS_OF_9 = "groups_of_9"   # For larger scales
    GROUPS_OF_10 = "groups_of_10"
    GROUPS_OF_11 = "groups_of_11"
    GROUPS_OF_12 = "groups_of_12" # For chromatic (12 notes)

    # Weaving
    BROKEN_THIRDS_NEIGHBOR = "broken_thirds_neighbor"  # 1-3-4-2, 3-5-6-4, ...

    # Arpeggio-based
    DIATONIC_TRIADS = "diatonic_triads"
    DIATONIC_7THS = "diatonic_7ths"
    BROKEN_CHORDS = "broken_chords"


class ArpeggioPattern(str, Enum):
    """Pattern algorithms for arpeggio practice."""

    STRAIGHT_UP = "straight_up"
    STRAIGHT_DOWN = "straight_down"
    STRAIGHT_UP_DOWN = "straight_up_down"
    WEAVING_ASCEND = "weaving_ascend"
    WEAVING_DESCEND = "weaving_descend"
    BROKEN_SKIP_1 = "broken_skip_1"
    INVERSION_ROOT = "inversion_root"
    INVERSION_1ST = "inversion_1st"
    INVERSION_2ND = "inversion_2nd"
    INVERSION_3RD = "inversion_3rd"
    ROLLING_ALBERTI = "rolling_alberti"
    SPREAD_VOICINGS = "spread_voicings"
    APPROACH_NOTES = "approach_notes"
    ENCLOSURES = "enclosures"
    DIATONIC_SEQUENCE = "diatonic_sequence"
    CIRCLE_4THS = "circle_4ths"
    CIRCLE_5THS = "circle_5ths"


# =============================================================================
# Pattern Constraints
# =============================================================================
# Patterns can have constraints that limit which scales/octaves they work with.
# These are used by the frontend to filter available options.

from typing import TypedDict


class PatternConstraints(TypedDict, total=False):
    """Constraints for a scale or arpeggio pattern."""
    max_octaves: int  # Maximum octaves this pattern supports
    requires_symmetric: bool  # If True, incompatible with asymmetric scales (melodic minor classical)
    blocked_scale_types: list[str]  # Scale types that cannot use this pattern
    chromatic_display_name: str  # Display name when applied to chromatic scale


# Scale pattern constraints - only patterns with restrictions are listed
# Patterns not listed have no constraints (any octaves, any scale)
SCALE_PATTERN_CONSTRAINTS: dict[str, PatternConstraints] = {
    # Broken thirds neighbor only works for 1 octave and requires symmetric scale
    ScalePattern.BROKEN_THIRDS_NEIGHBOR.value: {
        "max_octaves": 1,
        "requires_symmetric": True,
        "blocked_scale_types": ["chromatic"],
    },
    # Diatonic 7ths have wide leaps, limit to 2 octaves
    # Also doesn't make sense for chromatic (no diatonic structure)
    ScalePattern.DIATONIC_7THS.value: {
        "max_octaves": 2,
        "blocked_scale_types": ["chromatic", "whole_tone"],
    },
    # Diatonic triads don't make sense for chromatic
    ScalePattern.DIATONIC_TRIADS.value: {
        "blocked_scale_types": ["chromatic", "whole_tone"],
    },
    # Broken chords (1-5-3) don't make sense for chromatic
    ScalePattern.BROKEN_CHORDS.value: {
        "blocked_scale_types": ["chromatic", "whole_tone"],
    },
    # Pyramid patterns grow quadratically (~n² notes), limit to 1 octave
    ScalePattern.PYRAMID_ASCEND.value: {
        "max_octaves": 1,
    },
    ScalePattern.PYRAMID_DESCEND.value: {
        "max_octaves": 1,
    },
    # Interval patterns - show chromatic-specific names
    # _in_interval(n) pairs notes at (pos, pos+n-1), so skip = n-1 notes
    # In chromatic (12 notes/octave), skip N = N semitones
    # Diatonic naming: 3rds, 4ths, etc. (based on scale degrees)
    # Chromatic naming: Major 2nds, minor 3rds, etc. (based on semitones)
    ScalePattern.IN_3RDS.value: {
        "chromatic_display_name": "Chromatic Major 2nds",  # skip 2 = 2 semitones
    },
    ScalePattern.IN_4THS.value: {
        "chromatic_display_name": "Chromatic minor 3rds",  # skip 3 = 3 semitones
    },
    ScalePattern.IN_5THS.value: {
        "chromatic_display_name": "Chromatic Major 3rds",  # skip 4 = 4 semitones
    },
    ScalePattern.IN_6THS.value: {
        "chromatic_display_name": "Chromatic Perfect 4ths",  # skip 5 = 5 semitones
    },
    ScalePattern.IN_7THS.value: {
        "chromatic_display_name": "Chromatic Tritones",  # skip 6 = 6 semitones
    },
    ScalePattern.IN_OCTAVES.value: {
        "chromatic_display_name": "Chromatic Perfect 5ths",  # skip 7 = 7 semitones
    },
    # Extended intervals (primarily useful for chromatic scale)
    ScalePattern.IN_9THS.value: {
        "chromatic_display_name": "Chromatic minor 6ths",  # skip 8 = 8 semitones
    },
    ScalePattern.IN_10THS.value: {
        "chromatic_display_name": "Chromatic Major 6ths",  # skip 9 = 9 semitones
    },
    ScalePattern.IN_11THS.value: {
        "chromatic_display_name": "Chromatic minor 7ths",  # skip 10 = 10 semitones
    },
    ScalePattern.IN_12THS.value: {
        "chromatic_display_name": "Chromatic Major 7ths",  # skip 11 = 11 semitones
    },
    ScalePattern.IN_13THS.value: {
        "chromatic_display_name": "Chromatic Octaves",  # skip 12 = 12 semitones
    },
}


class RhythmType(str, Enum):
    """Rhythm/duration templates."""

    # Sustained
    WHOLE_NOTES = "whole_notes"
    HALF_NOTES = "half_notes"

    # Pulse
    QUARTER_NOTES = "quarter_notes"

    # Subdivisions
    EIGHTH_NOTES = "eighth_notes"
    SIXTEENTH_NOTES = "sixteenth_notes"

    # Triplets
    EIGHTH_TRIPLETS = "eighth_triplets"

    # Swing
    SWING_EIGHTHS = "swing_eighths"
    SCOTCH_SNAP = "scotch_snap"

    # Dotted
    DOTTED_QUARTER_EIGHTH = "dotted_quarter_eighth"
    DOTTED_EIGHTH_SIXTEENTH = "dotted_eighth_sixteenth"

    # Compound cells
    SIXTEENTH_EIGHTH_SIXTEENTH = "sixteenth_eighth_sixteenth"
    EIGHTH_SIXTEENTH_SIXTEENTH = "eighth_sixteenth_sixteenth"
    SIXTEENTH_SIXTEENTH_EIGHTH = "sixteenth_sixteenth_eighth"
    SYNCOPATED = "syncopated"


class DynamicType(str, Enum):
    """Dynamic contour options."""

    NONE = "none"
    CRESCENDO = "crescendo"
    DECRESCENDO = "decrescendo"
    TERRACED = "terraced"  # Step changes: p → mf → f
    ACCENTED = "accented"  # Specific beats emphasized
    HAIRPIN = "hairpin"  # Crescendo then decrescendo


class ArticulationType(str, Enum):
    """Articulation options."""

    LEGATO = "legato"
    STACCATO = "staccato"
    TENUTO = "tenuto"
    ACCENT = "accent"
    MARCATO = "marcato"
    MIXED = "mixed"


class MusicalKey(str, Enum):
    """All 12 musical keys for transposition."""

    C = "C"
    C_SHARP = "C#"
    D_FLAT = "Db"
    D = "D"
    D_SHARP = "D#"
    E_FLAT = "Eb"
    E = "E"
    F = "F"
    F_SHARP = "F#"
    G_FLAT = "Gb"
    G = "G"
    G_SHARP = "G#"
    A_FLAT = "Ab"
    A = "A"
    A_SHARP = "A#"
    B_FLAT = "Bb"
    B = "B"


# Canonical key list (12 unique pitches, preferring flats for black keys)
CANONICAL_KEYS: List[MusicalKey] = [
    MusicalKey.C,
    MusicalKey.D_FLAT,
    MusicalKey.D,
    MusicalKey.E_FLAT,
    MusicalKey.E,
    MusicalKey.F,
    MusicalKey.G_FLAT,
    MusicalKey.G,
    MusicalKey.A_FLAT,
    MusicalKey.A,
    MusicalKey.B_FLAT,
    MusicalKey.B,
]


# =============================================================================
# Range Helper Models
# =============================================================================


class RangeSpec(BaseModel):
    """User's playable range specification.

    Used to resolve user range settings (pitch names like "C2", "Bb4")
    into MIDI bounds for the generation engine.

    Example:
        # From user's stored range
        spec = RangeSpec(low_pitch="C2", high_pitch="Bb4")
        request = GenerationRequest(
            ...,
            range_low_midi=spec.low_midi,
            range_high_midi=spec.high_midi,
        )
    """

    low_pitch: str = Field(
        ...,
        description="Lowest playable pitch as string (e.g., 'C2', 'Bb3')",
    )

    high_pitch: str = Field(
        ...,
        description="Highest playable pitch as string (e.g., 'F5', 'C6')",
    )

    @property
    def low_midi(self) -> int:
        """Convert low_pitch to MIDI note number."""
        return _pitch_to_midi(self.low_pitch)

    @property
    def high_midi(self) -> int:
        """Convert high_pitch to MIDI note number."""
        return _pitch_to_midi(self.high_pitch)

    @property
    def span_semitones(self) -> int:
        """Total range span in semitones."""
        return self.high_midi - self.low_midi

    @property
    def span_octaves(self) -> float:
        """Total range span in octaves (may be fractional)."""
        return self.span_semitones / 12.0

    @model_validator(mode="after")
    def validate_range_order(self) -> "RangeSpec":
        """Ensure low_pitch is below high_pitch."""
        if self.low_midi > self.high_midi:
            raise ValueError(
                f"low_pitch ({self.low_pitch}={self.low_midi}) must be below "
                f"high_pitch ({self.high_pitch}={self.high_midi})"
            )
        return self


def _pitch_to_midi(pitch_str: str) -> int:
    """Convert pitch string like 'C4', 'Bb3', 'F#5' to MIDI number.

    This is a schema-local implementation to avoid circular imports.
    """
    import re

    if not pitch_str:
        return 60  # default to middle C

    match = re.match(r"([A-Ga-g])([#b]?)(-?\d+)", pitch_str)
    if not match:
        raise ValueError(f"Invalid pitch format: '{pitch_str}'")

    note, accidental, octave = match.groups()

    note_to_semitone = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}
    midi = note_to_semitone.get(note.upper(), 0)

    if accidental == "#":
        midi += 1
    elif accidental == "b":
        midi -= 1

    return midi + (int(octave) + 1) * 12


def _midi_to_pitch(midi: int) -> str:
    """Convert MIDI number to pitch string.

    Uses sharps for black keys. For enharmonic equivalents, use midi_to_pitch_flat.
    """
    notes = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    octave = (midi // 12) - 1
    note = notes[midi % 12]
    return f"{note}{octave}"


# =============================================================================
# Request Models
# =============================================================================


class GenerationRequest(BaseModel):
    """Request model for generating musical content.

    All content is defined in C major/A minor as the reference key.
    The engine transposes to the target key on output.

    Example:
        GenerationRequest(
            content_type="scale",
            definition="dorian",
            octaves=2,
            pattern="in_3rds",
            rhythm="eighth_notes",
            key="F",
            dynamics="crescendo",
            articulation="staccato"
        )
    """

    # What to generate
    content_type: GenerationType = Field(
        ...,
        description="Type of musical content: scale, arpeggio, or lick",
    )

    definition: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Scale type, arpeggio type, or lick ID",
    )

    # Range - octaves is the desired span, actual output may be constrained by range bounds
    octaves: Literal[1, 2, 3] = Field(
        default=1,
        description="Desired number of octaves (1, 2, or 3). May be reduced to fit within range bounds.",
    )

    # User's playable range bounds (MIDI note numbers)
    # These are typically resolved from User.range_low/range_high before calling the engine
    range_low_midi: Optional[int] = Field(
        default=None,
        ge=0,
        le=127,
        description="Lowest playable MIDI note (e.g., 36 for C2). If None, no lower bound.",
    )

    range_high_midi: Optional[int] = Field(
        default=None,
        ge=0,
        le=127,
        description="Highest playable MIDI note (e.g., 70 for Bb4). If None, no upper bound.",
    )

    # Pattern
    pattern: Optional[str] = Field(
        default=None,
        max_length=50,
        description="Pattern algorithm to apply. If None, uses straight up-down.",
    )

    # Rhythm
    rhythm: RhythmType = Field(
        default=RhythmType.QUARTER_NOTES,
        description="Rhythm/duration template",
    )

    # Transposition
    key: MusicalKey = Field(
        default=MusicalKey.C,
        description="Target key for transposition (content authored in C)",
    )

    # Expression
    dynamics: DynamicType = Field(
        default=DynamicType.NONE,
        description="Dynamic contour to apply",
    )

    articulation: ArticulationType = Field(
        default=ArticulationType.LEGATO,
        description="Articulation style",
    )

    # Tempo bounds (user controls tempo at practice time)
    tempo_min_bpm: Optional[int] = Field(
        default=None,
        ge=20,
        le=400,
        description="Minimum tempo in BPM",
    )

    tempo_max_bpm: Optional[int] = Field(
        default=None,
        ge=20,
        le=400,
        description="Maximum tempo in BPM",
    )

    @field_validator("definition")
    @classmethod
    def validate_definition_format(cls, v: str) -> str:
        """Validate definition is lowercase with underscores only."""
        import re

        if not re.match(r"^[a-z][a-z0-9_]*$", v):
            raise ValueError(
                "definition must be lowercase letters, numbers, and underscores"
            )
        return v

    @model_validator(mode="after")
    def validate_tempo_range(self) -> "GenerationRequest":
        """Ensure tempo_min <= tempo_max if both provided."""
        if (
            self.tempo_min_bpm is not None
            and self.tempo_max_bpm is not None
            and self.tempo_min_bpm > self.tempo_max_bpm
        ):
            raise ValueError("tempo_min_bpm cannot exceed tempo_max_bpm")
        return self

    @model_validator(mode="after")
    def validate_pitch_range(self) -> "GenerationRequest":
        """Ensure range_low_midi <= range_high_midi if both provided."""
        if (
            self.range_low_midi is not None
            and self.range_high_midi is not None
            and self.range_low_midi > self.range_high_midi
        ):
            raise ValueError("range_low_midi cannot exceed range_high_midi")
        return self

    @model_validator(mode="after")
    def validate_definition_for_type(self) -> "GenerationRequest":
        """Validate definition matches content_type."""
        if self.content_type == GenerationType.SCALE:
            try:
                ScaleType(self.definition)
            except ValueError:
                valid_scales = [s.value for s in ScaleType]
                raise ValueError(
                    f"Invalid scale type '{self.definition}'. "
                    f"Valid options: {valid_scales}"
                )
        elif self.content_type == GenerationType.ARPEGGIO:
            try:
                ArpeggioType(self.definition)
            except ValueError:
                valid_arps = [a.value for a in ArpeggioType]
                raise ValueError(
                    f"Invalid arpeggio type '{self.definition}'. "
                    f"Valid options: {valid_arps}"
                )
        # Licks use arbitrary IDs, validated against the lick library elsewhere
        return self

    @model_validator(mode="after")
    def validate_pattern_for_type(self) -> "GenerationRequest":
        """Validate pattern matches content_type if provided."""
        if self.pattern is None:
            return self

        if self.content_type == GenerationType.SCALE:
            try:
                ScalePattern(self.pattern)
            except ValueError:
                valid_patterns = [p.value for p in ScalePattern]
                raise ValueError(
                    f"Invalid scale pattern '{self.pattern}'. "
                    f"Valid options: {valid_patterns}"
                )
        elif self.content_type == GenerationType.ARPEGGIO:
            try:
                ArpeggioPattern(self.pattern)
            except ValueError:
                valid_patterns = [p.value for p in ArpeggioPattern]
                raise ValueError(
                    f"Invalid arpeggio pattern '{self.pattern}'. "
                    f"Valid options: {valid_patterns}"
                )
        # Licks don't use patterns
        return self


# =============================================================================
# Response Models
# =============================================================================


class PitchEvent(BaseModel):
    """A single pitch event in the generated content."""

    midi_note: int = Field(
        ...,
        ge=0,
        le=127,
        description="MIDI note number (0-127)",
    )

    pitch_name: str = Field(
        ...,
        description="Pitch name with octave (e.g., 'C4', 'F#5')",
    )

    duration_beats: float = Field(
        ...,
        gt=0,
        description="Duration in beats (quarter note = 1.0)",
    )

    offset_beats: float = Field(
        ...,
        ge=0,
        description="Offset from start in beats",
    )

    velocity: int = Field(
        default=80,
        ge=1,
        le=127,
        description="MIDI velocity (1-127)",
    )

    articulation: Optional[ArticulationType] = Field(
        default=None,
        description="Articulation marking for this note",
    )


class GenerationResponse(BaseModel):
    """Response model for generated musical content."""

    # Echo request parameters
    content_type: GenerationType
    definition: str
    key: MusicalKey
    octaves: int  # Requested octaves
    pattern: Optional[str]
    rhythm: RhythmType
    dynamics: DynamicType
    articulation: ArticulationType

    # Actual range used (may differ from requested if constrained)
    effective_octaves: int = Field(
        ...,
        ge=1,
        le=3,
        description="Actual octaves generated (may be less than requested due to range constraints)",
    )

    range_used_low_midi: Optional[int] = Field(
        default=None,
        description="Lowest MIDI note in the generated content",
    )

    range_used_high_midi: Optional[int] = Field(
        default=None,
        description="Highest MIDI note in the generated content",
    )

    # Generated content
    events: List[PitchEvent] = Field(
        ...,
        description="List of pitch events in chronological order",
    )

    # Metadata
    total_beats: float = Field(
        ...,
        description="Total duration in beats",
    )

    tempo_range: Optional[tuple[int, int]] = Field(
        default=None,
        description="Suggested tempo range (min_bpm, max_bpm)",
    )

    # For integration with practice system
    capabilities_required: List[str] = Field(
        default_factory=list,
        description="Capability IDs required to perform this content",
    )

    @field_validator("events")
    @classmethod
    def validate_events_not_empty(cls, v: List[PitchEvent]) -> List[PitchEvent]:
        """Ensure at least one event is generated."""
        if not v:
            raise ValueError("events cannot be empty")
        return v


class GenerationPreview(BaseModel):
    """Lightweight preview of what would be generated.

    Used for UI display before full generation.
    """

    content_type: GenerationType
    definition: str
    key: MusicalKey
    display_name: str = Field(
        ...,
        description="Human-readable name (e.g., 'D Dorian Scale, 2 octaves')",
    )

    estimated_notes: int = Field(
        ...,
        ge=1,
        description="Approximate number of notes",
    )

    estimated_beats: float = Field(
        ...,
        gt=0,
        description="Approximate duration in beats",
    )

    difficulty_tier: int = Field(
        default=1,
        ge=1,
        le=5,
        description="Estimated difficulty (1-5)",
    )
