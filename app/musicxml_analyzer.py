"""
MusicXML Analyzer for Sound First

Extracts capabilities and analysis data from MusicXML files using music21.

This module identifies all musical elements that require prior learning,
enabling the capability-based material selection system.
"""

import json
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field, asdict
from collections import Counter
from enum import Enum

try:
    from music21 import converter, stream, note, chord, clef, meter, key, dynamics
    from music21 import expressions, articulations, tempo, interval, pitch, repeat
    from music21 import spanner
    MUSIC21_AVAILABLE = True
except ImportError:
    MUSIC21_AVAILABLE = False

# Import tempo analyzer (same package)
from app.tempo_analyzer import (
    TempoProfile, TempoDifficultyMetrics,
    build_tempo_profile, calculate_tempo_difficulty_metrics,
    get_legacy_tempo_bpm,
)


# =============================================================================
# DATA CLASSES FOR EXTRACTION RESULTS
# =============================================================================

def format_pitch_name(pitch_str: str) -> str:
    """Convert music21 pitch notation to standard notation.
    
    music21 uses '-' for flat (e.g., 'E-5' for Eb5).
    Convert to 'b' notation (e.g., 'Eb5').
    """
    return pitch_str.replace('-', 'b')


@dataclass
class IntervalInfo:
    """Information about an interval occurrence."""
    name: str  # e.g., "M3" for major third
    direction: str  # "ascending", "descending", "unison"
    quality: str  # "major", "minor", "perfect", "augmented", "diminished"
    semitones: int
    is_melodic: bool  # True for melodic, False for harmonic
    count: int = 1


@dataclass 
class RangeAnalysis:
    """Pitch range analysis with density information."""
    lowest_pitch: str  # e.g., "E3"
    highest_pitch: str  # e.g., "G5"
    lowest_midi: int
    highest_midi: int
    range_semitones: int
    # Density: what % of notes fall in each third of the range
    density_low: float  # lower 33%
    density_mid: float  # middle 33%
    density_high: float  # upper 33%
    # For trills
    trill_lowest: Optional[str] = None
    trill_highest: Optional[str] = None


@dataclass
class ExtractionResult:
    """Complete extraction result from MusicXML analysis."""
    
    # Basic identification
    title: Optional[str] = None
    composer: Optional[str] = None
    
    # Clefs found
    clefs: Set[str] = field(default_factory=set)  # "treble", "bass", "alto", "tenor"
    
    # Time signatures
    time_signatures: Set[str] = field(default_factory=set)  # "4/4", "3/4", "6/8"
    
    # Key signatures (for reading capability, not ear-playing)
    key_signatures: Set[str] = field(default_factory=set)  # "C major", "G major", "D minor"
    
    # Note values
    note_values: Dict[str, int] = field(default_factory=dict)  # {"quarter": 45, "eighth": 22}
    dotted_notes: Set[str] = field(default_factory=set)  # "dotted_quarter", "dotted_half"
    has_ties: bool = False
    
    # Rests
    rest_values: Dict[str, int] = field(default_factory=dict)
    has_multi_measure_rest: bool = False
    
    # Tuplets
    tuplets: Dict[str, int] = field(default_factory=dict)  # {"triplet": 8, "quintuplet": 2}
    
    # Intervals
    melodic_intervals: Dict[str, IntervalInfo] = field(default_factory=dict)
    harmonic_intervals: Dict[str, IntervalInfo] = field(default_factory=dict)
    
    # Dynamics
    dynamics: Set[str] = field(default_factory=set)  # "p", "f", "mf", "sfz"
    dynamic_changes: Set[str] = field(default_factory=set)  # "crescendo", "diminuendo"
    
    # Articulations
    articulations: Set[str] = field(default_factory=set)  # "staccato", "accent", "tenuto"
    
    # Ornaments
    ornaments: Set[str] = field(default_factory=set)  # "trill", "mordent", "turn", "grace_note"
    
    # Tempo and expression
    tempo_markings: Set[str] = field(default_factory=set)  # "Allegro", "Andante"
    tempo_bpm: Optional[int] = None  # LEGACY: Use tempo_profile.effective_bpm instead
    tempo_profile: Optional[TempoProfile] = None  # Full tempo analysis
    expression_terms: Set[str] = field(default_factory=set)  # "dolce", "cantabile"
    
    # Repeat structures
    repeat_structures: Set[str] = field(default_factory=set)  # "repeat_sign", "coda", "dc"
    
    # Other notation
    fermatas: int = 0
    breath_marks: int = 0
    chord_symbols: Set[str] = field(default_factory=set)
    figured_bass: bool = False
    
    # Multi-voice
    max_voices: int = 1
    
    # Range analysis
    range_analysis: Optional[RangeAnalysis] = None
    
    # Chromatic analysis
    accidentals_outside_key: Dict[str, int] = field(default_factory=dict)  # {"F#": 3, "Bb": 1}
    chromatic_complexity_score: float = 0.0
    
    # Structure
    measure_count: int = 0
    estimated_duration_seconds: Optional[int] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary, handling sets and dataclasses."""
        result = {}
        for k, v in self.__dict__.items():
            if isinstance(v, set):
                result[k] = list(v)
            elif isinstance(v, dict):
                # Handle IntervalInfo objects in dicts
                result[k] = {ik: (asdict(iv) if hasattr(iv, '__dataclass_fields__') else iv) 
                            for ik, iv in v.items()}
            elif hasattr(v, 'to_dict'):
                # Handle TempoProfile and other objects with to_dict
                result[k] = v.to_dict()
            elif hasattr(v, '__dataclass_fields__'):
                result[k] = asdict(v)
            else:
                result[k] = v
        return result


# =============================================================================
# CAPABILITY NAME MAPPINGS
# =============================================================================

# Map music21 clef types to capability names
CLEF_CAPABILITY_MAP = {
    'TrebleClef': 'clef_treble',
    'BassClef': 'clef_bass',
    'AltoClef': 'clef_alto',
    'TenorClef': 'clef_tenor',
    'Treble8vbClef': 'clef_treble_8vb',
    'Bass8vaClef': 'clef_bass_8va',
}

# Map note type names to capability names
NOTE_VALUE_CAPABILITY_MAP = {
    'whole': 'note_whole',
    'half': 'note_half',
    'quarter': 'note_quarter',
    'eighth': 'note_eighth',
    '16th': 'note_sixteenth',
    '32nd': 'note_thirty_second',
    '64th': 'note_sixty_fourth',
}

# Map rest type names to capability names
REST_CAPABILITY_MAP = {
    'whole': 'rest_whole',
    'half': 'rest_half', 
    'quarter': 'rest_quarter',
    'eighth': 'rest_eighth',
    '16th': 'rest_sixteenth',
    '32nd': 'rest_thirty_second',
    '64th': 'rest_sixty_fourth',
}

# Map dynamics to capability names
DYNAMIC_CAPABILITY_MAP = {
    'ppp': 'dynamic_ppp',
    'pp': 'dynamic_pp',
    'p': 'dynamic_p',
    'mp': 'dynamic_mp',
    'mf': 'dynamic_mf',
    'f': 'dynamic_f',
    'ff': 'dynamic_ff',
    'fff': 'dynamic_fff',
    'sf': 'dynamic_sf',
    'sfz': 'dynamic_sfz',
    'sfp': 'dynamic_sfp',
    'fp': 'dynamic_fp',
    'rf': 'dynamic_rf',
    'rfz': 'dynamic_rfz',
}

# Map articulations to capability names
ARTICULATION_CAPABILITY_MAP = {
    'Staccato': 'articulation_staccato',
    'Staccatissimo': 'articulation_staccatissimo',
    'Accent': 'articulation_accent',
    'StrongAccent': 'articulation_marcato',
    'Tenuto': 'articulation_tenuto',
    'DetachedLegato': 'articulation_portato',
}

# Map ornaments to capability names
ORNAMENT_CAPABILITY_MAP = {
    'Trill': 'ornament_trill',
    'Mordent': 'ornament_mordent',
    'InvertedMordent': 'ornament_inverted_mordent',
    'Turn': 'ornament_turn',
    'InvertedTurn': 'ornament_inverted_turn',
    'Tremolo': 'ornament_tremolo',
}

# Common Italian tempo terms
TEMPO_TERMS = {
    'largo', 'lento', 'adagio', 'andante', 'andantino', 'moderato',
    'allegretto', 'allegro', 'vivace', 'presto', 'prestissimo',
    'accelerando', 'ritardando', 'rallentando', 'a tempo', 'rubato',
}

# Common Italian expression terms
EXPRESSION_TERMS = {
    'dolce', 'cantabile', 'espressivo', 'con brio', 'con fuoco',
    'con moto', 'grazioso', 'leggiero', 'maestoso', 'pesante',
    'scherzando', 'sostenuto', 'tranquillo', 'agitato', 'animato',
    'appassionato', 'brillante', 'giocoso', 'legato', 'marcato',
    'perdendosi', 'morendo', 'smorzando', 'sotto voce', 'meno mosso',
    'più mosso', 'sempre', 'molto', 'poco', 'poco a poco',
}


# =============================================================================
# MAIN ANALYZER CLASS
# =============================================================================

class MusicXMLAnalyzer:
    """
    Analyzes MusicXML files to extract capabilities and metrics.
    
    Usage:
        analyzer = MusicXMLAnalyzer()
        result = analyzer.analyze(musicxml_string)
        capabilities = analyzer.get_capability_names(result)
    """
    
    def __init__(self):
        if not MUSIC21_AVAILABLE:
            raise ImportError("music21 is required for MusicXML analysis")
    
    def analyze(self, musicxml_content: str) -> ExtractionResult:
        """
        Analyze MusicXML content and extract all capabilities.
        
        Args:
            musicxml_content: MusicXML string
            
        Returns:
            ExtractionResult with all extracted information
        """
        result = ExtractionResult()
        
        # Parse the MusicXML
        try:
            score = converter.parse(musicxml_content)
        except Exception as e:
            raise ValueError(f"Failed to parse MusicXML: {e}")
        
        # Extract metadata
        self._extract_metadata(score, result)
        
        # Extract clefs
        self._extract_clefs(score, result)
        
        # Extract time signatures
        self._extract_time_signatures(score, result)
        
        # Extract key signatures
        self._extract_key_signatures(score, result)
        
        # Extract notes, rests, and related info
        self._extract_notes_and_rests(score, result)
        
        # Extract intervals
        self._extract_intervals(score, result)
        
        # Extract dynamics
        self._extract_dynamics(score, result)
        
        # Extract articulations
        self._extract_articulations(score, result)
        
        # Extract ornaments
        self._extract_ornaments(score, result)
        
        # Extract tempo and expression
        self._extract_tempo_expression(score, result)
        
        # Extract repeat structures
        self._extract_repeats(score, result)
        
        # Extract other notation elements
        self._extract_other_notation(score, result)
        
        # Analyze range and pitch density
        self._analyze_range(score, result)
        
        # Analyze chromatic complexity
        self._analyze_chromatic_complexity(score, result)
        
        # Count measures
        result.measure_count = len(score.parts[0].getElementsByClass('Measure')) if score.parts else 0
        
        return result
    
    def _extract_metadata(self, score: stream.Score, result: ExtractionResult):
        """Extract title, composer, etc."""
        if score.metadata:
            result.title = score.metadata.title
            result.composer = score.metadata.composer
    
    def _extract_clefs(self, score: stream.Score, result: ExtractionResult):
        """Extract all clefs used in the score."""
        for c in score.recurse().getElementsByClass(clef.Clef):
            clef_type = type(c).__name__
            if clef_type in CLEF_CAPABILITY_MAP:
                result.clefs.add(CLEF_CAPABILITY_MAP[clef_type])
            else:
                # Generic clef handling
                if hasattr(c, 'sign'):
                    result.clefs.add(f"clef_{c.sign.lower()}")
    
    def _extract_time_signatures(self, score: stream.Score, result: ExtractionResult):
        """Extract all time signatures."""
        for ts in score.recurse().getElementsByClass(meter.TimeSignature):
            ts_str = f"{ts.numerator}_{ts.denominator}"
            result.time_signatures.add(f"time_sig_{ts_str}")
    
    def _extract_key_signatures(self, score: stream.Score, result: ExtractionResult):
        """Extract all key signatures."""
        for ks in score.recurse().getElementsByClass(key.KeySignature):
            # Get the key name
            if hasattr(ks, 'asKey'):
                k = ks.asKey()
                mode = 'major' if k.mode == 'major' else 'minor'
                tonic = k.tonic.name.replace('#', '_sharp').replace('-', '_flat')
                result.key_signatures.add(f"key_{tonic}_{mode}")
            else:
                # Just sharps/flats count
                sharps = ks.sharps
                result.key_signatures.add(f"key_sig_{sharps}_sharps" if sharps >= 0 else f"key_sig_{abs(sharps)}_flats")
    
    def _extract_notes_and_rests(self, score: stream.Score, result: ExtractionResult):
        """Extract note values, rests, tuplets, ties."""
        for element in score.recurse().notesAndRests:
            if isinstance(element, note.Note) or isinstance(element, chord.Chord):
                # Note value
                note_type = element.duration.type
                if note_type in NOTE_VALUE_CAPABILITY_MAP:
                    cap_name = NOTE_VALUE_CAPABILITY_MAP[note_type]
                    result.note_values[cap_name] = result.note_values.get(cap_name, 0) + 1
                
                # Dotted notes
                if element.duration.dots > 0:
                    dotted_name = f"dotted_{note_type}"
                    result.dotted_notes.add(dotted_name)
                
                # Double dots
                if element.duration.dots > 1:
                    result.dotted_notes.add(f"double_dotted_{note_type}")
                
                # Ties
                if element.tie is not None:
                    result.has_ties = True
                
                # Tuplets
                if element.duration.tuplets:
                    for t in element.duration.tuplets:
                        tuplet_name = self._get_tuplet_name(t)
                        result.tuplets[tuplet_name] = result.tuplets.get(tuplet_name, 0) + 1
            
            elif isinstance(element, note.Rest):
                # Rest value
                rest_type = element.duration.type
                if rest_type in REST_CAPABILITY_MAP:
                    cap_name = REST_CAPABILITY_MAP[rest_type]
                    result.rest_values[cap_name] = result.rest_values.get(cap_name, 0) + 1
                
                # Multi-measure rest
                if hasattr(element, 'fullMeasure') and element.fullMeasure:
                    result.has_multi_measure_rest = True
        
        # Check for multi-voice
        for part in score.parts:
            for measure in part.getElementsByClass('Measure'):
                voices = measure.voices
                if len(voices) > result.max_voices:
                    result.max_voices = len(voices)
    
    def _get_tuplet_name(self, tuplet) -> str:
        """Convert tuplet to capability name."""
        actual = tuplet.numberNotesActual
        normal = tuplet.numberNotesNormal
        
        if actual == 3 and normal == 2:
            return 'tuplet_triplet'
        elif actual == 5 and normal == 4:
            return 'tuplet_quintuplet'
        elif actual == 6 and normal == 4:
            return 'tuplet_sextuplet'
        elif actual == 7 and normal == 4:
            return 'tuplet_septuplet'
        else:
            return f'tuplet_{actual}_{normal}'
    
    def _extract_intervals(self, score: stream.Score, result: ExtractionResult):
        """Extract melodic and harmonic intervals."""
        for part in score.parts:
            notes_only = [n for n in part.recurse().notes if isinstance(n, note.Note)]
            
            # Melodic intervals (consecutive notes)
            for i in range(len(notes_only) - 1):
                n1 = notes_only[i]
                n2 = notes_only[i + 1]
                
                try:
                    intv = interval.Interval(n1, n2)
                    info = self._get_interval_info(intv, is_melodic=True)
                    key = f"interval_melodic_{info.name}_{info.direction}"
                    
                    if key in result.melodic_intervals:
                        result.melodic_intervals[key].count += 1
                    else:
                        result.melodic_intervals[key] = info
                except:
                    pass  # Skip problematic intervals
            
            # Harmonic intervals (within chords)
            for c in part.recurse().getElementsByClass(chord.Chord):
                pitches = c.pitches
                for i in range(len(pitches)):
                    for j in range(i + 1, len(pitches)):
                        try:
                            intv = interval.Interval(pitches[i], pitches[j])
                            info = self._get_interval_info(intv, is_melodic=False)
                            key = f"interval_harmonic_{info.name}"
                            
                            if key in result.harmonic_intervals:
                                result.harmonic_intervals[key].count += 1
                            else:
                                result.harmonic_intervals[key] = info
                        except:
                            pass
    
    def _get_interval_info(self, intv: interval.Interval, is_melodic: bool) -> IntervalInfo:
        """Convert music21 interval to IntervalInfo."""
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
    
    def _extract_dynamics(self, score: stream.Score, result: ExtractionResult):
        """Extract dynamics and dynamic changes."""
        for d in score.recurse().getElementsByClass(dynamics.Dynamic):
            dyn_val = d.value
            if dyn_val in DYNAMIC_CAPABILITY_MAP:
                result.dynamics.add(DYNAMIC_CAPABILITY_MAP[dyn_val])
            else:
                result.dynamics.add(f"dynamic_{dyn_val}")
        
        # Dynamic wedges (crescendo/diminuendo)
        for s in score.recurse().getElementsByClass(dynamics.DynamicWedge):
            if isinstance(s, dynamics.Crescendo):
                result.dynamic_changes.add('dynamic_change_crescendo')
            elif isinstance(s, dynamics.Diminuendo):
                result.dynamic_changes.add('dynamic_change_diminuendo')
        
        # Also check for text-based cresc/dim
        for tw in score.recurse().getElementsByClass(expressions.TextExpression):
            text = tw.content.lower() if tw.content else ''
            if 'cresc' in text:
                result.dynamic_changes.add('dynamic_change_crescendo')
            if 'dim' in text or 'decresc' in text:
                result.dynamic_changes.add('dynamic_change_diminuendo')
            if 'subito' in text:
                result.dynamic_changes.add('dynamic_change_subito')
    
    def _extract_articulations(self, score: stream.Score, result: ExtractionResult):
        """Extract articulations."""
        for n in score.recurse().notes:
            for art in n.articulations:
                art_type = type(art).__name__
                if art_type in ARTICULATION_CAPABILITY_MAP:
                    result.articulations.add(ARTICULATION_CAPABILITY_MAP[art_type])
                else:
                    result.articulations.add(f"articulation_{art_type.lower()}")
    
    def _extract_ornaments(self, score: stream.Score, result: ExtractionResult):
        """Extract ornaments."""
        for n in score.recurse().notes:
            for expr in n.expressions:
                expr_type = type(expr).__name__
                
                if expr_type in ORNAMENT_CAPABILITY_MAP:
                    result.ornaments.add(ORNAMENT_CAPABILITY_MAP[expr_type])
                elif isinstance(expr, expressions.Fermata):
                    result.fermatas += 1
                elif 'Grace' in expr_type:
                    result.ornaments.add('ornament_grace_note')
                elif 'Appoggiatura' in expr_type:
                    result.ornaments.add('ornament_appoggiatura')
    
    def _extract_tempo_expression(self, score: stream.Score, result: ExtractionResult):
        """Extract tempo markings, expression terms, and build tempo profile."""
        # Build comprehensive tempo profile using tempo_analyzer
        result.tempo_profile = build_tempo_profile(score)
        
        # Set legacy tempo_bpm from effective_bpm (was: last tempo found)
        # LEGACY COMPATIBILITY: This field is deprecated, use tempo_profile instead
        result.tempo_bpm = get_legacy_tempo_bpm(result.tempo_profile)
        
        # Still populate tempo_markings for capability detection
        # This ensures backward compatibility with detection rules
        for t in score.recurse().getElementsByClass(tempo.MetronomeMark):
            if t.text:
                text_lower = t.text.lower()
                for term in TEMPO_TERMS:
                    if term in text_lower:
                        result.tempo_markings.add(f"tempo_{term.replace(' ', '_')}")
        
        for t in score.recurse().getElementsByClass(tempo.TempoText):
            if t.text:
                text_lower = t.text.lower()
                for term in TEMPO_TERMS:
                    if term in text_lower:
                        result.tempo_markings.add(f"tempo_{term.replace(' ', '_')}")
        
        # Expression text (including tempo terms since they can appear as TextExpression)
        for te in score.recurse().getElementsByClass(expressions.TextExpression):
            if te.content:
                text_lower = te.content.lower()
                # Check for tempo terms in TextExpression too
                for term in TEMPO_TERMS:
                    if term in text_lower:
                        result.tempo_markings.add(f"tempo_{term.replace(' ', '_')}")
                # Check for expression terms
                for term in EXPRESSION_TERMS:
                    if term in text_lower:
                        result.expression_terms.add(f"expression_{term.replace(' ', '_')}")
    
    def _extract_repeats(self, score: stream.Score, result: ExtractionResult):
        """Extract repeat structures."""
        # Repeat signs
        for r in score.recurse().getElementsByClass(repeat.RepeatMark):
            result.repeat_structures.add('repeat_sign')
        
        # Barlines with repeats
        for b in score.recurse().getElementsByClass('Barline'):
            if hasattr(b, 'type'):
                if 'repeat' in str(b.type).lower():
                    result.repeat_structures.add('repeat_sign')
        
        # Da Capo, Dal Segno, Coda, etc.
        for te in score.recurse().getElementsByClass(expressions.TextExpression):
            if te.content:
                text = te.content.lower()
                if 'd.c.' in text or 'da capo' in text:
                    result.repeat_structures.add('repeat_dc')
                if 'd.s.' in text or 'dal segno' in text:
                    result.repeat_structures.add('repeat_ds')
                if 'coda' in text:
                    result.repeat_structures.add('repeat_coda')
                if 'segno' in text:
                    result.repeat_structures.add('repeat_segno')
                if 'fine' in text:
                    result.repeat_structures.add('repeat_fine')
        
        # First/second endings
        for s in score.recurse().getElementsByClass(spanner.RepeatBracket):
            result.repeat_structures.add('repeat_first_ending')
            result.repeat_structures.add('repeat_second_ending')
    
    def _extract_other_notation(self, score: stream.Score, result: ExtractionResult):
        """Extract fermatas, breath marks, chord symbols, etc."""
        # Breath marks
        for te in score.recurse().getElementsByClass(expressions.TextExpression):
            if te.content and 'breath' in te.content.lower():
                result.breath_marks += 1
        
        # Also check for BreathMark class
        for n in score.recurse().notes:
            for expr in n.expressions:
                if type(expr).__name__ == 'BreathMark':
                    result.breath_marks += 1
        
        # Chord symbols (jazz)
        for cs in score.recurse().getElementsByClass('ChordSymbol'):
            if hasattr(cs, 'figure'):
                result.chord_symbols.add(str(cs.figure))
        
        # Figured bass
        for fb in score.recurse().getElementsByClass('FiguredBass'):
            result.figured_bass = True
    
    def _analyze_range(self, score: stream.Score, result: ExtractionResult):
        """Analyze pitch range and density."""
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
    
    def _analyze_chromatic_complexity(self, score: stream.Score, result: ExtractionResult):
        """Analyze accidentals outside key signature."""
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
    
    def get_capability_names(self, result: ExtractionResult) -> List[str]:
        """
        Convert extraction result to list of capability names.
        
        Returns:
            List of capability ID names (e.g., ["clef_treble", "time_sig_4_4", ...])
        """
        capabilities = []
        
        # Clefs
        capabilities.extend(result.clefs)
        
        # Time signatures
        capabilities.extend(result.time_signatures)
        
        # Key signatures
        capabilities.extend(result.key_signatures)
        
        # Note values
        capabilities.extend(result.note_values.keys())
        
        # Dotted notes
        for dn in result.dotted_notes:
            capabilities.append(f"note_{dn}")
        
        # Ties
        if result.has_ties:
            capabilities.append("notation_ties")
        
        # Rests
        capabilities.extend(result.rest_values.keys())
        
        # Multi-measure rests
        if result.has_multi_measure_rest:
            capabilities.append("rest_multi_measure")
        
        # Tuplets
        capabilities.extend(result.tuplets.keys())
        
        # Melodic intervals
        for key in result.melodic_intervals.keys():
            capabilities.append(key)
        
        # Harmonic intervals
        for key in result.harmonic_intervals.keys():
            capabilities.append(key)
        
        # Dynamics
        capabilities.extend(result.dynamics)
        
        # Dynamic changes
        capabilities.extend(result.dynamic_changes)
        
        # Articulations
        capabilities.extend(result.articulations)
        
        # Ornaments
        capabilities.extend(result.ornaments)
        
        # Tempo markings
        capabilities.extend(result.tempo_markings)
        
        # Expression terms
        capabilities.extend(result.expression_terms)
        
        # Repeat structures
        capabilities.extend(result.repeat_structures)
        
        # Fermatas
        if result.fermatas > 0:
            capabilities.append("notation_fermata")
        
        # Breath marks
        if result.breath_marks > 0:
            capabilities.append("notation_breath_mark")
        
        # Chord symbols
        if result.chord_symbols:
            capabilities.append("notation_chord_symbols")
        
        # Figured bass
        if result.figured_bass:
            capabilities.append("notation_figured_bass")
        
        # Multi-voice
        if result.max_voices >= 2:
            capabilities.append(f"notation_{result.max_voices}_voices")
        
        return capabilities


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def analyze_musicxml(musicxml_content: str) -> Tuple[ExtractionResult, List[str]]:
    """
    Convenience function to analyze MusicXML and get capabilities.
    
    Returns:
        Tuple of (ExtractionResult, list of capability names)
    """
    analyzer = MusicXMLAnalyzer()
    result = analyzer.analyze(musicxml_content)
    capabilities = analyzer.get_capability_names(result)
    return result, capabilities


def compute_capability_bitmask(capability_ids: List[int]) -> List[int]:
    """
    Compute bitmask values for a list of capability IDs.
    
    Args:
        capability_ids: List of capability IDs (each has a bit_index 0-511)
        
    Returns:
        List of 8 integers representing the 8 mask columns
    """
    masks = [0] * 8
    for cap_id in capability_ids:
        bucket = cap_id // 64
        bit_position = cap_id % 64
        if 0 <= bucket < 8:
            masks[bucket] |= (1 << bit_position)
    return masks


def check_eligibility(user_masks: List[int], material_masks: List[int]) -> bool:
    """
    Check if a user is eligible for a material using bitmasks.
    
    Args:
        user_masks: User's 8 capability mask values
        material_masks: Material's 8 required capability mask values
        
    Returns:
        True if user has all required capabilities
    """
    for i in range(8):
        user_mask = user_masks[i] or 0
        material_mask = material_masks[i] or 0
        # User must have all bits that material requires
        if (material_mask & ~user_mask) != 0:
            return False
    return True
