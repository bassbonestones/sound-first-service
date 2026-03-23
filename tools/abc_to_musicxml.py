#!/usr/bin/env python3
"""
ABC to MusicXML Converter for Sound First.

Converts ABC notation files to MusicXML format, optionally transposing to C major
while preserving the original key as metadata.

Usage:
    # Convert a single file
    python -m tools.abc_to_musicxml abc/beginner/hot_cross_buns.abc

    # Convert a single file with explicit output
    python -m tools.abc_to_musicxml input.abc --output output.musicxml

    # Batch convert all files in a directory
    python -m tools.abc_to_musicxml abc/ --batch --output-dir resources/materials/pending/

    # List keys without converting
    python -m tools.abc_to_musicxml abc/beginner/*.abc --dry-run
"""

from __future__ import annotations

import argparse
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    from music21 import converter, key as m21_key, interval, stream, dynamics, expressions, note as m21_note
except ImportError:
    raise ImportError(
        "music21 is required. Install it with: pip install music21"
    )

logger = logging.getLogger(__name__)


# ABC dynamic markers to music21 dynamics
ABC_DYNAMICS_MAP = {
    "pppp": "pppp",
    "ppp": "ppp",
    "pp": "pp",
    "p": "p",
    "mp": "mp",
    "mf": "mf",
    "f": "f",
    "ff": "ff",
    "fff": "fff",
    "ffff": "ffff",
    "sfz": "sfz",
    "sf": "sf",
    "fp": "fp",
    "cresc": "crescendo",
    "decresc": "diminuendo",
    "dim": "diminuendo",
}

# ABC expression markers (not dynamics)
ABC_EXPRESSION_MARKS = {
    "dolce", "espressivo", "cantabile", "legato", "leggiero",
    "maestoso", "soulful", "grazioso", "animato", "sostenuto",
    "marcato", "pesante", "brillante", "con brio", "con fuoco",
}

# ABC articulation markers - maps to music21 articulation class names
ABC_ARTICULATION_MAP = {
    ">": "Accent",
    "accent": "Accent",
    "emphasis": "Accent",
    "marcato": "StrongAccent",
    "tenuto": "Tenuto",
    "-": "Tenuto",
    "staccato": "Staccato",
    "staccatissimo": "Staccatissimo",
    "fermata": "Fermata",
    "upbow": "UpBow",
    "downbow": "DownBow",
    "trill": "Trill",
    "mordent": "Mordent",
    "turn": "Turn",
}


@dataclass
class ABCDynamic:
    """A dynamic marking extracted from ABC."""
    note_index: int  # Which note this applies to (0-based)
    dynamic: str  # The dynamic value (mf, p, etc.)


@dataclass
class ABCExpression:
    """An expression marking extracted from ABC."""
    note_index: int
    text: str


@dataclass
class ABCArticulation:
    """An articulation marking extracted from ABC."""
    note_index: int
    articulation: str  # music21 articulation class name


@dataclass
class ABCWedge:
    """A wedge (hairpin) crescendo/diminuendo marking."""
    start_note_index: int
    end_note_index: int
    wedge_type: str  # "crescendo" or "diminuendo"
    start_offset: float = 0.0  # Offset in quarter notes from start note
    end_offset: float = 0.0  # Offset in quarter notes from end note


@dataclass
class ABCSyllable:
    """A single syllable with syllabic position."""
    text: str
    syllabic: str  # "single", "begin", "middle", or "end"


@dataclass
class ABCLyrics:
    """Lyrics extracted from ABC."""
    syllables: list[ABCSyllable]


@dataclass
class ConversionResult:
    """Result of an ABC to MusicXML conversion."""

    input_file: Path
    output_file: Path
    original_key: str
    transposed: bool
    success: bool
    error: Optional[str] = None


def extract_key_from_abc(abc_content: str) -> Optional[str]:
    """
    Extract the key from ABC notation K: field.

    Args:
        abc_content: Raw ABC notation string

    Returns:
        Key string (e.g., "G", "Bb", "F#m") or None if not found

    Examples:
        >>> extract_key_from_abc("K:G\\nABCD")
        'G'
        >>> extract_key_from_abc("K: Bb major\\nABCD")
        'Bb'
        >>> extract_key_from_abc("K:Am\\nABCD")
        'Am'
    """
    # Match K: field - can have whitespace, mode specifier, etc.
    # K:G, K: Bb, K:Am, K: F# major, K: Dm minor, K:C mix
    # The mode part is captured to detect minor
    # Important: Put longer alternatives before shorter ones (maj before m, mix before m)
    pattern = r"^K:\s*([A-Ga-g][#b]?)\s*(maj(?:or)?|mix(?:olydian)?|min(?:or)?|m|dor(?:ian)?|lyd(?:ian)?|phr(?:ygian)?|loc(?:rian)?)?.*$"
    match = re.search(pattern, abc_content, re.MULTILINE | re.IGNORECASE)

    if match:
        key_str = match.group(1)
        mode_str = match.group(2) or ""
        # Normalize: uppercase letter, proper accidental
        letter = key_str[0].upper()
        accidental = key_str[1:].lower() if len(key_str) > 1 else ""
        # Check if minor key (mode is 'm', 'min', or 'minor' - but not 'maj', 'major', 'mix')
        mode_lower = mode_str.lower()
        is_minor = mode_lower in ("m", "min", "minor")
        mode_suffix = "m" if is_minor else ""
        return f"{letter}{accidental}{mode_suffix}"

    return None


def normalize_key_for_music21(key_str: str) -> str:
    """
    Normalize key string for music21 Key constructor.

    Args:
        key_str: Key like "G", "Bb", "F#m", "Am"

    Returns:
        Normalized key for music21 (e.g., "G", "b-", "a")
        music21.key.Key expects just the pitch name, and infers mode from case
    """
    # Check for minor
    is_minor = key_str.endswith("m") or key_str.endswith("min")
    base_key = re.sub(r"m(in(or)?)?$", "", key_str, flags=re.IGNORECASE)

    # Normalize accidentals for music21
    letter = base_key[0].lower() if is_minor else base_key[0].upper()
    accidental = ""
    if len(base_key) > 1:
        acc = base_key[1:].lower()
        if acc == "#":
            accidental = "#"
        elif acc == "b":
            accidental = "-"

    return f"{letter}{accidental}"


def get_transposition_interval(from_key: str, to_key: str = "C") -> interval.Interval:
    """
    Calculate the interval needed to transpose from one key to another.

    Args:
        from_key: Original key (e.g., "G", "Bb", "F#m")
        to_key: Target key (default "C" for major, "A" for minor)

    Returns:
        music21 Interval object for transposition
    """
    from_key_normalized = normalize_key_for_music21(from_key)
    is_minor = from_key.endswith("m") or from_key.endswith("min")

    # Target key based on mode
    if is_minor:
        to_key_normalized = "a"  # A minor
    else:
        to_key_normalized = "C"  # C major

    from_key_obj = m21_key.Key(from_key_normalized)
    to_key_obj = m21_key.Key(to_key_normalized)

    # Calculate interval from tonic to tonic
    return interval.Interval(from_key_obj.tonic, to_key_obj.tonic)


def extract_abc_dynamics_and_expressions(abc_content: str) -> tuple[list[ABCDynamic], list[ABCExpression], list[ABCArticulation], list[ABCWedge]]:
    """
    Extract dynamic, expression, articulation, and wedge markings from ABC notation.
    
    Parses markers like !mf!, !p!, !dolce!, !accent!, !>!, !<(!, !<)! and tracks
    which note index they apply to.
    
    Wedge markers:
    - !<(! or !crescendo(! - start crescendo hairpin
    - !<)! or !crescendo)! - end crescendo hairpin  
    - !>(! or !diminuendo(! - start diminuendo hairpin
    - !>)! or !diminuendo)! - end diminuendo hairpin
    
    Args:
        abc_content: Raw ABC notation string
        
    Returns:
        Tuple of (dynamics list, expressions list, articulations list, wedges list)
    """
    dynamics_list: list[ABCDynamic] = []
    expressions_list: list[ABCExpression] = []
    articulations_list: list[ABCArticulation] = []
    wedges_list: list[ABCWedge] = []
    
    # Track open wedges (start index, type)
    open_crescendo: Optional[int] = None
    open_diminuendo: Optional[int] = None
    
    # Get only the music lines (after K: field, not header or lyrics)
    lines = abc_content.split('\n')
    music_lines = []
    in_music = False
    for line in lines:
        if line.strip().startswith('K:'):
            in_music = True
            continue
        if in_music and not line.strip().startswith('w:') and line.strip():
            music_lines.append(line)
    
    music_content = ' '.join(music_lines)
    
    # Find all !...! markers and notes
    # Pattern for markers
    marker_pattern = r'!([^!]+)!'
    # Pattern for notes (simplified - letter with optional accidental and octave)
    note_pattern = r"[A-Ga-g][,']*[0-9/]*"
    
    # Track position in music and count notes
    note_count = 0
    current_dynamics: list[str] = []
    current_expressions: list[str] = []
    current_articulations: list[str] = []
    
    # Track pending wedge offsets
    crescendo_start_offset: float = 0.0
    diminuendo_start_offset: float = 0.0
    
    # Process character by character to track markers and notes
    i = 0
    while i < len(music_content):
        char = music_content[i]
        
        # Check for marker start
        if char == '!':
            end = music_content.find('!', i + 1)
            if end != -1:
                marker = music_content[i+1:end].lower()
                
                # Parse offset from marker if present (e.g., ">(@1" or ">)@0.5")
                offset = 0.0
                base_marker = marker
                if '@' in marker:
                    parts = marker.split('@')
                    base_marker = parts[0]
                    try:
                        offset = float(parts[1])
                    except (ValueError, IndexError):
                        offset = 0.0
                
                # Check for wedge markers
                if base_marker in ('<(', 'crescendo('):
                    open_crescendo = note_count
                    crescendo_start_offset = offset
                elif base_marker in ('<)', 'crescendo)'):
                    if open_crescendo is not None:
                        wedges_list.append(ABCWedge(
                            start_note_index=open_crescendo,
                            end_note_index=note_count,
                            wedge_type="crescendo",
                            start_offset=crescendo_start_offset,
                            end_offset=offset
                        ))
                        open_crescendo = None
                        crescendo_start_offset = 0.0
                elif base_marker in ('>(', 'diminuendo(', 'dim('):
                    open_diminuendo = note_count
                    diminuendo_start_offset = offset
                elif base_marker in ('>)', 'diminuendo)', 'dim)'):
                    if open_diminuendo is not None:
                        wedges_list.append(ABCWedge(
                            start_note_index=open_diminuendo,
                            end_note_index=note_count,
                            wedge_type="diminuendo",
                            start_offset=diminuendo_start_offset,
                            end_offset=offset
                        ))
                        open_diminuendo = None
                        diminuendo_start_offset = 0.0
                # Check if it's a dynamic
                elif base_marker in ABC_DYNAMICS_MAP:
                    current_dynamics.append(base_marker)
                # Check if it's an articulation
                elif base_marker in ABC_ARTICULATION_MAP:
                    current_articulations.append(base_marker)
                # Check if it's an expression
                elif base_marker in ABC_EXPRESSION_MARKS:
                    current_expressions.append(base_marker)
                # Fallback: treat any unrecognized text marker as an expression
                # (allows arbitrary Italian terms like "Dolce e legato")
                elif base_marker and not base_marker.startswith(('|', '[', ']', ':', '1', '2')):
                    current_expressions.append(marker)  # Use original marker with case
                i = end + 1
                continue
        
        # Check for note
        if char.upper() in 'ABCDEFG':
            # This is a note - attach any pending dynamics/expressions/articulations
            for dyn in current_dynamics:
                dynamics_list.append(ABCDynamic(note_index=note_count, dynamic=dyn))
            for expr in current_expressions:
                expressions_list.append(ABCExpression(note_index=note_count, text=expr))
            for art in current_articulations:
                articulations_list.append(ABCArticulation(note_index=note_count, articulation=ABC_ARTICULATION_MAP[art]))
            current_dynamics = []
            current_expressions = []
            current_articulations = []
            note_count += 1
        
        i += 1
    
    return dynamics_list, expressions_list, articulations_list, wedges_list


def extract_abc_lyrics(abc_content: str) -> ABCLyrics:
    """
    Extract lyrics from ABC w: lines.
    
    ABC lyrics use:
    - Spaces to separate words/syllables for different notes
    - Hyphens (-) to split syllables within a word across notes
    - Underscores (_) to extend a syllable over multiple notes (melisma)
    - Bars (|) to align with measure bars
    
    Args:
        abc_content: Raw ABC notation string
        
    Returns:
        ABCLyrics with syllables list including syllabic position
    """
    syllables: list[ABCSyllable] = []
    
    # Find all w: lines and combine them
    lyric_text = ""
    for line in abc_content.split('\n'):
        if line.strip().startswith('w:'):
            lyric_text += " " + line[2:].strip()
    
    if not lyric_text.strip():
        return ABCLyrics(syllables=[])
    
    # Remove bar markers, normalize whitespace
    lyric_text = lyric_text.replace('|', ' ').strip()
    
    # Split on whitespace to get words/syllable-groups
    tokens = lyric_text.split()
    
    for token in tokens:
        if token == '_':
            # Melisma extension - add empty placeholder to preserve note index alignment
            syllables.append(ABCSyllable(text="", syllabic="single"))
            continue
        elif token == '-':
            # Standalone hyphen (rare but possible)
            continue
        elif '-' in token:
            # Word split into syllables: "Hel-lo" or "one-a-pen-ny"
            parts = token.split('-')
            for idx, part in enumerate(parts):
                if not part:  # Skip empty parts from trailing hyphens
                    continue
                if len(parts) == 1:
                    syllabic = "single"
                elif idx == 0:
                    syllabic = "begin"
                elif idx == len(parts) - 1:
                    syllabic = "end"
                else:
                    syllabic = "middle"
                syllables.append(ABCSyllable(text=part, syllabic=syllabic))
        else:
            # Single complete word
            syllables.append(ABCSyllable(text=token, syllabic="single"))
    
    return ABCLyrics(syllables=syllables)


def inject_musicality(
    score: stream.Score,
    abc_dynamics: list[ABCDynamic],
    abc_expressions: list[ABCExpression],
    abc_articulations: list[ABCArticulation],
    abc_wedges: list[ABCWedge],
    abc_lyrics: ABCLyrics,
) -> None:
    """
    Inject dynamics, expressions, articulations, wedges, and lyrics into a music21 score.
    
    Modifies the score in place.
    
    Args:
        score: music21 Score object
        abc_dynamics: List of dynamics to add
        abc_expressions: List of expressions to add
        abc_articulations: List of articulations to add
        abc_wedges: List of wedge hairpins to add
        abc_lyrics: Lyrics to add
    """
    from music21 import articulations as m21_articulations
    from music21 import spanner
    
    # Get all notes in order
    notes = list(score.recurse().notes)
    
    # Add dynamics
    for abc_dyn in abc_dynamics:
        if abc_dyn.note_index < len(notes):
            target_note = notes[abc_dyn.note_index]
            dyn_value = ABC_DYNAMICS_MAP.get(abc_dyn.dynamic, abc_dyn.dynamic)
            try:
                dyn = dynamics.Dynamic(dyn_value)
                # Insert dynamic at the note's offset in its parent
                parent = target_note.activeSite
                if parent:
                    parent.insert(target_note.offset, dyn)
            except Exception as e:
                logger.warning(f"Could not add dynamic {dyn_value}: {e}")
    
    # Add expressions (placed above the staff)
    # If expression is on first note, shift to second note to avoid tempo collision
    for abc_expr in abc_expressions:
        note_idx = abc_expr.note_index
        # Shift first-note expressions to second note to avoid tempo mark collision
        if note_idx == 0 and len(notes) > 1:
            note_idx = 1
        if note_idx < len(notes):
            target_note = notes[note_idx]
            expr = expressions.TextExpression(abc_expr.text)
            expr.placement = 'above'
            parent = target_note.activeSite
            if parent:
                parent.insert(target_note.offset, expr)
    
    # Add articulations
    for abc_art in abc_articulations:
        if abc_art.note_index < len(notes):
            target_note = notes[abc_art.note_index]
            try:
                # Get the articulation class from music21
                art_class = getattr(m21_articulations, abc_art.articulation, None)
                if art_class:
                    target_note.articulations.append(art_class())
                else:
                    logger.warning(f"Unknown articulation class: {abc_art.articulation}")
            except Exception as e:
                logger.warning(f"Could not add articulation {abc_art.articulation}: {e}")
    
    # Add wedges (hairpins)
    for wedge in abc_wedges:
        if wedge.start_note_index < len(notes) and wedge.end_note_index < len(notes):
            start_note = notes[wedge.start_note_index]
            end_note = notes[wedge.end_note_index]
            try:
                if wedge.wedge_type == "crescendo":
                    wedge_spanner = dynamics.Crescendo(start_note, end_note)
                else:
                    wedge_spanner = dynamics.Diminuendo(start_note, end_note)
                
                # Apply offsets if specified
                # These shift the visual start/end of the wedge
                if wedge.start_offset > 0 or wedge.end_offset > 0:
                    # Store offset info as spanner properties for MusicXML export
                    wedge_spanner.startOffset = wedge.start_offset
                    wedge_spanner.endOffset = wedge.end_offset
                
                # Add to the score's spanners
                score.insert(0, wedge_spanner)
            except Exception as e:
                logger.warning(f"Could not add wedge {wedge.wedge_type}: {e}")
    
    # Add lyrics with proper syllabic marking
    for i, syl in enumerate(abc_lyrics.syllables):
        if i < len(notes) and syl.text:
            target_note = notes[i]
            if isinstance(target_note, m21_note.Note):
                lyric_obj = m21_note.Lyric(text=syl.text, syllabic=syl.syllabic)
                target_note.lyrics.append(lyric_obj)


def apply_wedge_offsets(musicxml_content: str, wedges: list[ABCWedge], divisions: int = 1) -> str:
    """
    Apply beat offsets to wedges in MusicXML content.
    
    MusicXML uses a <offset> element inside <direction> to shift the position
    of direction elements (including wedges) from their notated position.
    
    Args:
        musicxml_content: Raw MusicXML string
        wedges: List of wedges with offset information
        divisions: Divisions per quarter note (extracted from MusicXML)
        
    Returns:
        MusicXML with wedge offsets applied
    """
    import xml.etree.ElementTree as ET
    
    # Find divisions from MusicXML
    try:
        root = ET.fromstring(musicxml_content)
        # Find divisions element
        div_elem = root.find('.//{http://www.w3.org/2001/XMLSchema-instance}divisions') or root.find('.//divisions')
        if div_elem is not None and div_elem.text:
            divisions = int(div_elem.text)
    except Exception:
        divisions = 1
    
    # For each wedge with offsets, find and modify the MusicXML
    for wedge in wedges:
        if wedge.start_offset > 0 or wedge.end_offset > 0:
            # Calculate offset in divisions (divisions per quarter note)
            start_offset_divs = int(wedge.start_offset * divisions)
            end_offset_divs = int(wedge.end_offset * divisions)
            
            # Find wedge direction elements and add/modify offset
            # This is a simplified approach - for complex scores might need refinement
            wedge_type = "diminuendo" if wedge.wedge_type == "diminuendo" else "crescendo"
            
            # Pattern to find wedge start - add offset after it
            if start_offset_divs > 0:
                import re
                # Find the wedge start direction and add offset
                pattern = rf'(<direction[^>]*>.*?<wedge[^>]*type="{wedge_type}"[^/]*/>.*?)(</direction-type>)'
                replacement = rf'\1\2\n          <offset>{start_offset_divs}</offset>'
                musicxml_content = re.sub(pattern, replacement, musicxml_content, count=1, flags=re.DOTALL)
            
            if end_offset_divs > 0:
                import re
                # Find the wedge stop direction and add offset
                pattern = r'(<direction[^>]*>.*?<wedge[^>]*type="stop"[^/]*/>.*?)(</direction-type>)'
                replacement = rf'\1\2\n          <offset>{end_offset_divs}</offset>'
                # Find the second occurrence (for the stop)
                matches = list(re.finditer(pattern, musicxml_content, flags=re.DOTALL))
                if len(matches) >= 1:
                    # Replace the last match (stop wedge)
                    last_match = matches[-1]
                    musicxml_content = (
                        musicxml_content[:last_match.start()] +
                        re.sub(pattern, replacement, last_match.group(0), flags=re.DOTALL) +
                        musicxml_content[last_match.end():]
                    )
    
    return musicxml_content


def add_original_key_comment(musicxml_content: str, original_key: str) -> str:
    """
    Add an XML comment with the original key to MusicXML content.

    Args:
        musicxml_content: Raw MusicXML string
        original_key: Original key to embed (e.g., "G")

    Returns:
        MusicXML with comment added after XML declaration
    """
    comment = f"<!-- original_key_center: {original_key} -->\n"

    # Insert after XML declaration if present
    if musicxml_content.startswith("<?xml"):
        # Find end of first line
        first_newline = musicxml_content.find("\n")
        if first_newline != -1:
            return (
                musicxml_content[: first_newline + 1]
                + comment
                + musicxml_content[first_newline + 1 :]
            )

    # Otherwise prepend
    return comment + musicxml_content


def convert_abc_to_musicxml(
    abc_content: str,
    transpose_to_c: bool = True,
    title: Optional[str] = None,
) -> tuple[str, str]:
    """
    Convert ABC notation to MusicXML.

    Args:
        abc_content: ABC notation string
        transpose_to_c: Whether to transpose to C major/A minor
        title: Optional title override

    Returns:
        Tuple of (musicxml_content, original_key)

    Raises:
        ValueError: If ABC content is invalid or cannot be parsed
    """
    # Extract original key before parsing
    original_key = extract_key_from_abc(abc_content)
    if not original_key:
        original_key = "C"  # Default if no key specified
        logger.warning("No K: field found in ABC, assuming C major")

    # Extract musicality markers before parsing (music21 doesn't parse these from ABC)
    abc_dynamics, abc_expressions, abc_articulations, abc_wedges = extract_abc_dynamics_and_expressions(abc_content)
    abc_lyrics = extract_abc_lyrics(abc_content)

    try:
        # Parse ABC with music21
        score: stream.Score = converter.parse(abc_content, format="abc")
    except Exception as e:
        raise ValueError(f"Failed to parse ABC notation: {e}") from e

    # Inject musicality markers that music21 didn't parse
    inject_musicality(score, abc_dynamics, abc_expressions, abc_articulations, abc_wedges, abc_lyrics)

    # Set title if provided
    if title and hasattr(score, "metadata"):
        if score.metadata is None:
            from music21 import metadata
            score.metadata = metadata.Metadata()
        score.metadata.title = title

    # Transpose to C if requested and not already in C
    if transpose_to_c and original_key.upper() not in ("C", "AM"):
        try:
            trans_interval = get_transposition_interval(original_key)
            score = score.transpose(trans_interval)
        except Exception as e:
            logger.warning(f"Transposition failed: {e}. Keeping original key.")

    # Convert to MusicXML
    try:
        musicxml_content = score.write("musicxml").read_text(encoding="utf-8")
    except Exception:
        # Fallback for older music21 versions
        import tempfile
        with tempfile.NamedTemporaryFile(suffix=".musicxml", delete=False) as f:
            temp_path = Path(f.name)
        score.write("musicxml", fp=str(temp_path))
        musicxml_content = temp_path.read_text(encoding="utf-8")
        temp_path.unlink()

    # Apply wedge offsets if any wedges have offset information
    wedges_with_offsets = [w for w in abc_wedges if w.start_offset > 0 or w.end_offset > 0]
    if wedges_with_offsets:
        musicxml_content = apply_wedge_offsets(musicxml_content, wedges_with_offsets)

    # Add original key as comment only if not already in C (no meaningful original to preserve)
    if original_key.upper() not in ("C", "AM"):
        musicxml_content = add_original_key_comment(musicxml_content, original_key)

    return musicxml_content, original_key


def convert_file(
    input_path: Path,
    output_path: Optional[Path] = None,
    transpose_to_c: bool = True,
    output_dir: Optional[Path] = None,
) -> ConversionResult:
    """
    Convert a single ABC file to MusicXML.

    Args:
        input_path: Path to ABC file
        output_path: Explicit output path (optional)
        transpose_to_c: Whether to transpose to C
        output_dir: Directory for output (used if output_path not specified)

    Returns:
        ConversionResult with status and details
    """
    if not input_path.exists():
        return ConversionResult(
            input_file=input_path,
            output_file=Path(""),
            original_key="",
            transposed=False,
            success=False,
            error=f"Input file not found: {input_path}",
        )

    # Determine output path
    if output_path is None:
        if output_dir:
            output_path = output_dir / (input_path.stem + ".musicxml")
        else:
            output_path = input_path.with_suffix(".musicxml")

    try:
        abc_content = input_path.read_text(encoding="utf-8")
        title = input_path.stem.replace("_", " ").title()

        musicxml_content, original_key = convert_abc_to_musicxml(
            abc_content,
            transpose_to_c=transpose_to_c,
            title=title,
        )

        # Ensure output directory exists
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Write output
        output_path.write_text(musicxml_content, encoding="utf-8")

        return ConversionResult(
            input_file=input_path,
            output_file=output_path,
            original_key=original_key,
            transposed=transpose_to_c and original_key.upper() not in ("C", "AM"),
            success=True,
        )

    except Exception as e:
        return ConversionResult(
            input_file=input_path,
            output_file=output_path,
            original_key="",
            transposed=False,
            success=False,
            error=str(e),
        )


def batch_convert(
    input_dir: Path,
    output_dir: Path,
    transpose_to_c: bool = True,
    recursive: bool = True,
) -> list[ConversionResult]:
    """
    Convert all ABC files in a directory to MusicXML.

    Args:
        input_dir: Directory containing ABC files
        output_dir: Directory for output MusicXML files
        transpose_to_c: Whether to transpose to C
        recursive: Whether to search subdirectories

    Returns:
        List of ConversionResult for each file
    """
    pattern = "**/*.abc" if recursive else "*.abc"
    abc_files = sorted(input_dir.glob(pattern))

    results = []
    for abc_file in abc_files:
        # Preserve relative directory structure
        rel_path = abc_file.relative_to(input_dir)
        output_path = output_dir / rel_path.with_suffix(".musicxml")

        result = convert_file(
            abc_file,
            output_path=output_path,
            transpose_to_c=transpose_to_c,
        )
        results.append(result)

    return results


def main() -> int:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Convert ABC notation files to MusicXML",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "input",
        type=Path,
        nargs="+",
        help="Input ABC file(s) or directory",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file (single file) or directory (batch mode)",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Output directory for converted files",
    )
    parser.add_argument(
        "--batch",
        action="store_true",
        help="Batch convert all ABC files in input directory",
    )
    parser.add_argument(
        "--no-transpose",
        action="store_true",
        help="Keep original key instead of transposing to C",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be converted without writing files",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output",
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    transpose_to_c = not args.no_transpose
    results: list[ConversionResult] = []

    for input_path in args.input:
        if args.batch or input_path.is_dir():
            # Batch mode
            output_dir = args.output_dir or args.output or Path("resources/materials/pending")
            if args.dry_run:
                abc_files = sorted(input_path.glob("**/*.abc"))
                for abc_file in abc_files:
                    key = extract_key_from_abc(abc_file.read_text(encoding="utf-8"))
                    print(f"  {abc_file.name}: {key or 'C (default)'}")
            else:
                batch_results = batch_convert(
                    input_path,
                    output_dir,
                    transpose_to_c=transpose_to_c,
                )
                results.extend(batch_results)
        else:
            # Single file mode
            if args.dry_run:
                key = extract_key_from_abc(input_path.read_text(encoding="utf-8"))
                print(f"  {input_path.name}: {key or 'C (default)'}")
            else:
                result = convert_file(
                    input_path,
                    output_path=args.output,
                    transpose_to_c=transpose_to_c,
                    output_dir=args.output_dir,
                )
                results.append(result)

    # Print summary
    if not args.dry_run:
        success_count = sum(1 for r in results if r.success)
        fail_count = len(results) - success_count

        print(f"\nConverted {success_count} file(s)")
        if fail_count > 0:
            print(f"Failed: {fail_count} file(s)")

        for result in results:
            status = "✓" if result.success else "✗"
            key_info = f" (from {result.original_key})" if result.transposed else ""
            if result.success:
                print(f"  {status} {result.output_file.name}{key_info}")
            else:
                print(f"  {status} {result.input_file.name}: {result.error}")

        return 0 if fail_count == 0 else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
