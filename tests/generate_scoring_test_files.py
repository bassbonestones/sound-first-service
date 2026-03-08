#!/usr/bin/env python3
"""
Generate MusicXML test files for scoring domain validation.

Creates files with known complexity profiles for:
- Interval: stepwise → mixed → large leaps
- Rhythm: quarter notes → mixed → tuplets/complex
- Pattern: repetitive → varied → unique
- Throughput: sparse (1-2 NPS) → moderate → dense (5+ NPS)
- Tonal: diatonic → some accidentals → chromatic
- Range: 6th or less → within octave → octave+

Each file is designed to produce predictable domain scores for validation.
"""

import os

OUTPUT_DIR = "tests/test_musicxml_files/scoring"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def wrap_musicxml_multi(measures: list, title: str = "Test", divisions: int = 4,
                        time_beats: int = 4, time_type: int = 4,
                        key_fifths: int = 0, clef_sign: str = "G", clef_line: int = 2,
                        tempo: int = 100) -> str:
    """Wrap multiple measures in a MusicXML document."""
    measures_xml = ""
    for i, measure_content in enumerate(measures, 1):
        if i == 1:
            measures_xml += f"""    <measure number="{i}">
      <attributes>
        <divisions>{divisions}</divisions>
        <key><fifths>{key_fifths}</fifths></key>
        <time><beats>{time_beats}</beats><beat-type>{time_type}</beat-type></time>
        <clef><sign>{clef_sign}</sign><line>{clef_line}</line></clef>
      </attributes>
      <direction>
        <direction-type>
          <metronome>
            <beat-unit>quarter</beat-unit>
            <per-minute>{tempo}</per-minute>
          </metronome>
        </direction-type>
        <sound tempo="{tempo}"/>
      </direction>
{measure_content}
    </measure>
"""
        else:
            measures_xml += f"""    <measure number="{i}">
{measure_content}
    </measure>
"""
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>{title}</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test</part-name></score-part>
  </part-list>
  <part id="P1">
{measures_xml}  </part>
</score-partwise>'''


def note(step: str, octave: int, duration: int, note_type: str,
         alter: int = None, dot: bool = False, tied_start: bool = False,
         tied_stop: bool = False) -> str:
    """Generate a note element."""
    alter_xml = f"<alter>{alter}</alter>" if alter else ""
    dot_xml = "<dot/>" if dot else ""
    tie_xml = ""
    if tied_start:
        tie_xml += '<tie type="start"/>'
    if tied_stop:
        tie_xml += '<tie type="stop"/>'
    notations = ""
    if tied_start or tied_stop:
        tied_notations = ""
        if tied_start:
            tied_notations += '<tied type="start"/>'
        if tied_stop:
            tied_notations += '<tied type="stop"/>'
        notations = f"<notations>{tied_notations}</notations>"
    
    return f"""      <note>
        <pitch><step>{step}</step>{alter_xml}<octave>{octave}</octave></pitch>
        <duration>{duration}</duration>
        <type>{note_type}</type>{dot_xml}{tie_xml}
        {notations}
      </note>"""


def rest(duration: int, rest_type: str) -> str:
    """Generate a rest element."""
    return f"""      <rest/>
      <duration>{duration}</duration>
      <type>{rest_type}</type>"""


def tuplet_notes(notes_content: str, actual: int = 3, normal: int = 2) -> str:
    """Wrap notes in tuplet notation."""
    return f"""      <note>
        <time-modification>
          <actual-notes>{actual}</actual-notes>
          <normal-notes>{normal}</normal-notes>
        </time-modification>
{notes_content}
      </note>"""


# =============================================================================
# INTERVAL DOMAIN TEST FILES
# =============================================================================

INTERVAL_BASELINE = {
    "filename": "interval_baseline_stepwise.musicxml",
    "description": "Stepwise motion only (seconds)",
    "expected_score_range": {"primary": [0.0, 0.2], "hazard": [0.0, 0.1]},
    "measures": [
        # C4-D4-E4-F4 (all steps)
        note("C", 4, 4, "quarter") + note("D", 4, 4, "quarter") + 
        note("E", 4, 4, "quarter") + note("F", 4, 4, "quarter"),
        # G4-A4-B4-C5 (all steps)
        note("G", 4, 4, "quarter") + note("A", 4, 4, "quarter") + 
        note("B", 4, 4, "quarter") + note("C", 5, 4, "quarter"),
        # C5-B4-A4-G4 (descending steps)
        note("C", 5, 4, "quarter") + note("B", 4, 4, "quarter") + 
        note("A", 4, 4, "quarter") + note("G", 4, 4, "quarter"),
        # F4-E4-D4-C4 (descending steps)
        note("F", 4, 4, "quarter") + note("E", 4, 4, "quarter") + 
        note("D", 4, 4, "quarter") + note("C", 4, 4, "quarter"),
    ]
}

INTERVAL_MODERATE = {
    "filename": "interval_moderate_mixed.musicxml",
    "description": "Mixed steps, skips, and small leaps",
    "expected_score_range": {"primary": [0.3, 0.5], "hazard": [0.1, 0.3]},
    "measures": [
        # C4-E4-D4-F4 (skip, step, skip)
        note("C", 4, 4, "quarter") + note("E", 4, 4, "quarter") + 
        note("D", 4, 4, "quarter") + note("F", 4, 4, "quarter"),
        # A4-C5-E4-G4 (minor 3rd, major 6th down, minor 3rd)
        note("A", 4, 4, "quarter") + note("C", 5, 4, "quarter") + 
        note("E", 4, 4, "quarter") + note("G", 4, 4, "quarter"),
        # E4-B4-G4-D5 (P5, M3 down, P5)
        note("E", 4, 4, "quarter") + note("B", 4, 4, "quarter") + 
        note("G", 4, 4, "quarter") + note("D", 5, 4, "quarter"),
        # C5-A4-F4-D4 (M3 down, M3 down, M3 down)
        note("C", 5, 4, "quarter") + note("A", 4, 4, "quarter") + 
        note("F", 4, 4, "quarter") + note("D", 4, 4, "quarter"),
    ]
}

INTERVAL_COMPLEX = {
    "filename": "interval_complex_large_leaps.musicxml",
    "description": "Large leaps including octaves and beyond",
    "expected_score_range": {"primary": [0.6, 0.9], "hazard": [0.4, 0.8]},
    "measures": [
        # C4-C5-C4-G4 (octave, octave down, P5)
        note("C", 4, 4, "quarter") + note("C", 5, 4, "quarter") + 
        note("C", 4, 4, "quarter") + note("G", 4, 4, "quarter"),
        # E4-E5-B4-G5 (octave, P4 down, M6)
        note("E", 4, 4, "quarter") + note("E", 5, 4, "quarter") + 
        note("B", 4, 4, "quarter") + note("G", 5, 4, "quarter"),
        # G3-G5-D5-D3 (2 octaves!, P4 down, 2 octaves down)
        note("G", 3, 4, "quarter") + note("G", 5, 4, "quarter") + 
        note("D", 5, 4, "quarter") + note("D", 3, 4, "quarter"),
        # C3-A5-F5-C6 (M13!, M3 down, P5)
        note("C", 3, 4, "quarter") + note("A", 5, 4, "quarter") + 
        note("F", 5, 4, "quarter") + note("C", 6, 4, "quarter"),
    ]
}


# =============================================================================
# RHYTHM DOMAIN TEST FILES
# =============================================================================

RHYTHM_BASELINE = {
    "filename": "rhythm_baseline_quarters.musicxml",
    "description": "Quarter notes only at moderate tempo",
    "expected_score_range": {"primary": [0.0, 0.2], "hazard": [0.0, 0.1]},
    "tempo": 100,
    "measures": [
        note("C", 4, 4, "quarter") + note("E", 4, 4, "quarter") + 
        note("G", 4, 4, "quarter") + note("C", 5, 4, "quarter"),
        note("D", 4, 4, "quarter") + note("F", 4, 4, "quarter") + 
        note("A", 4, 4, "quarter") + note("D", 5, 4, "quarter"),
        note("E", 4, 4, "quarter") + note("G", 4, 4, "quarter") + 
        note("B", 4, 4, "quarter") + note("E", 5, 4, "quarter"),
        note("C", 5, 4, "quarter") + note("G", 4, 4, "quarter") + 
        note("E", 4, 4, "quarter") + note("C", 4, 4, "quarter"),
    ]
}

RHYTHM_MODERATE = {
    "filename": "rhythm_moderate_mixed.musicxml",
    "description": "Mixed note values: quarters, eighths, dotted",
    "expected_score_range": {"primary": [0.3, 0.5], "hazard": [0.1, 0.3]},
    "tempo": 100,
    "divisions": 4,
    "measures": [
        # Quarter, 2 eighths, dotted quarter + eighth
        note("C", 4, 4, "quarter") + note("D", 4, 2, "eighth") + note("E", 4, 2, "eighth") + 
        note("F", 4, 6, "quarter", dot=True) + note("G", 4, 2, "eighth"),
        # Half, 2 eighths
        note("A", 4, 8, "half") + note("G", 4, 2, "eighth") + note("F", 4, 2, "eighth") +
        note("E", 4, 4, "quarter"),
        # Syncopated: eighth, quarter, eighth, half
        note("D", 4, 2, "eighth") + note("E", 4, 4, "quarter") + note("D", 4, 2, "eighth") +
        note("C", 4, 8, "half"),
        # Dotted half + quarter
        note("G", 4, 12, "half", dot=True) + note("E", 4, 4, "quarter"),
    ]
}

RHYTHM_COMPLEX = {
    "filename": "rhythm_complex_tuplets.musicxml",
    "description": "Tuplets, sixteenths, complex subdivisions",
    "expected_score_range": {"primary": [0.6, 0.9], "hazard": [0.4, 0.8]},
    "tempo": 120,
    "divisions": 12,  # Divisible by 3 for triplets
    "measures": [
        # Triplet eighths (each 2 div = 8 total for quarter), then regular quarter
        """      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>eighth</type>
        <time-modification>
          <actual-notes>3</actual-notes>
          <normal-notes>2</normal-notes>
        </time-modification>
        <notations><tuplet type="start"/></notations>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>eighth</type>
        <time-modification>
          <actual-notes>3</actual-notes>
          <normal-notes>2</normal-notes>
        </time-modification>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>eighth</type>
        <time-modification>
          <actual-notes>3</actual-notes>
          <normal-notes>2</normal-notes>
        </time-modification>
        <notations><tuplet type="stop"/></notations>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>3</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>3</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>3</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>3</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>24</duration>
        <type>half</type>
      </note>""",
        # More triplets and varied values
        """      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>eighth</type>
        <time-modification>
          <actual-notes>3</actual-notes>
          <normal-notes>2</normal-notes>
        </time-modification>
        <notations><tuplet type="start"/></notations>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>eighth</type>
        <time-modification>
          <actual-notes>3</actual-notes>
          <normal-notes>2</normal-notes>
        </time-modification>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>eighth</type>
        <time-modification>
          <actual-notes>3</actual-notes>
          <normal-notes>2</normal-notes>
        </time-modification>
        <notations><tuplet type="stop"/></notations>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>6</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>18</duration>
        <type>quarter</type>
        <dot/>
      </note>
      <note>
        <pitch><step>B</step><octave>3</octave></pitch>
        <duration>12</duration>
        <type>quarter</type>
      </note>""",
    ]
}


# =============================================================================
# PATTERN DOMAIN TEST FILES
# =============================================================================

PATTERN_BASELINE = {
    "filename": "pattern_baseline_repetitive.musicxml",
    "description": "Highly repetitive melodic/rhythmic pattern",
    "expected_score_range": {"primary": [0.0, 0.2], "hazard": [0.0, 0.2]},
    "measures": [
        # Same 4-note pattern repeated
        note("C", 4, 4, "quarter") + note("D", 4, 4, "quarter") + 
        note("E", 4, 4, "quarter") + note("D", 4, 4, "quarter"),
        note("C", 4, 4, "quarter") + note("D", 4, 4, "quarter") + 
        note("E", 4, 4, "quarter") + note("D", 4, 4, "quarter"),
        note("C", 4, 4, "quarter") + note("D", 4, 4, "quarter") + 
        note("E", 4, 4, "quarter") + note("D", 4, 4, "quarter"),
        note("C", 4, 4, "quarter") + note("D", 4, 4, "quarter") + 
        note("E", 4, 4, "quarter") + note("C", 4, 4, "quarter"),
    ]
}

PATTERN_MODERATE = {
    "filename": "pattern_moderate_varied.musicxml",
    "description": "Some repetition with variations",
    "expected_score_range": {"primary": [0.3, 0.5], "hazard": [0.2, 0.4]},
    "measures": [
        # Pattern A
        note("C", 4, 4, "quarter") + note("E", 4, 4, "quarter") + 
        note("G", 4, 4, "quarter") + note("E", 4, 4, "quarter"),
        # Pattern B
        note("D", 4, 4, "quarter") + note("F", 4, 4, "quarter") + 
        note("A", 4, 4, "quarter") + note("F", 4, 4, "quarter"),
        # Pattern A again
        note("C", 4, 4, "quarter") + note("E", 4, 4, "quarter") + 
        note("G", 4, 4, "quarter") + note("E", 4, 4, "quarter"),
        # Pattern C (new)
        note("G", 4, 4, "quarter") + note("B", 4, 4, "quarter") + 
        note("D", 5, 4, "quarter") + note("B", 4, 4, "quarter"),
    ]
}

PATTERN_COMPLEX = {
    "filename": "pattern_complex_unique.musicxml",
    "description": "No repetition, unique throughout",
    "expected_score_range": {"primary": [0.6, 0.9], "hazard": [0.5, 0.8]},
    "measures": [
        # All unique melodic shapes
        note("C", 4, 4, "quarter") + note("G", 4, 4, "quarter") + 
        note("D", 4, 4, "quarter") + note("A", 4, 4, "quarter"),
        note("E", 4, 4, "quarter") + note("B", 4, 4, "quarter") + 
        note("F", 4, 4, "quarter") + note("C", 5, 4, "quarter"),
        note("A", 4, 4, "quarter") + note("D", 4, 4, "quarter") + 
        note("G", 4, 4, "quarter") + note("B", 4, 4, "quarter"),
        note("F", 4, 4, "quarter") + note("E", 4, 4, "quarter") +
        note("D", 5, 4, "quarter") + note("C", 4, 4, "quarter"),
    ]
}


# =============================================================================
# THROUGHPUT DOMAIN TEST FILES
# =============================================================================

THROUGHPUT_BASELINE = {
    "filename": "throughput_baseline_sparse.musicxml",
    "description": "Sparse: ~1-2 notes per second (whole and half notes)",
    "expected_score_range": {"primary": [0.0, 0.2], "hazard": [0.0, 0.1]},
    "tempo": 60,  # Slow tempo
    "measures": [
        note("C", 4, 16, "whole"),
        note("E", 4, 16, "whole"),
        note("G", 4, 8, "half") + note("A", 4, 8, "half"),
        note("C", 5, 16, "whole"),
    ]
}

THROUGHPUT_MODERATE = {
    "filename": "throughput_moderate.musicxml",
    "description": "Moderate: ~3-4 notes per second",
    "expected_score_range": {"primary": [0.3, 0.5], "hazard": [0.1, 0.3]},
    "tempo": 100,
    "measures": [
        note("C", 4, 4, "quarter") + note("D", 4, 4, "quarter") +
        note("E", 4, 4, "quarter") + note("F", 4, 4, "quarter"),
        note("G", 4, 2, "eighth") + note("A", 4, 2, "eighth") +
        note("B", 4, 2, "eighth") + note("C", 5, 2, "eighth") +
        note("D", 5, 4, "quarter") + note("C", 5, 4, "quarter"),
        note("B", 4, 4, "quarter") + note("A", 4, 4, "quarter") +
        note("G", 4, 4, "quarter") + note("F", 4, 4, "quarter"),
        note("E", 4, 8, "half") + note("C", 4, 8, "half"),
    ]
}

THROUGHPUT_COMPLEX = {
    "filename": "throughput_complex_dense.musicxml",
    "description": "Dense: 5+ notes per second",
    "expected_score_range": {"primary": [0.6, 0.9], "hazard": [0.4, 0.8]},
    "tempo": 140,  # Fast tempo
    "divisions": 4,
    "measures": [
        # 16th notes at 140 BPM = ~9 NPS
        note("C", 4, 1, "16th") + note("D", 4, 1, "16th") +
        note("E", 4, 1, "16th") + note("F", 4, 1, "16th") +
        note("G", 4, 1, "16th") + note("A", 4, 1, "16th") +
        note("B", 4, 1, "16th") + note("C", 5, 1, "16th") +
        note("D", 5, 1, "16th") + note("E", 5, 1, "16th") +
        note("F", 5, 1, "16th") + note("G", 5, 1, "16th") +
        note("A", 5, 4, "quarter"),
        note("G", 5, 1, "16th") + note("F", 5, 1, "16th") +
        note("E", 5, 1, "16th") + note("D", 5, 1, "16th") +
        note("C", 5, 1, "16th") + note("B", 4, 1, "16th") +
        note("A", 4, 1, "16th") + note("G", 4, 1, "16th") +
        note("F", 4, 1, "16th") + note("E", 4, 1, "16th") +
        note("D", 4, 1, "16th") + note("C", 4, 1, "16th") +
        note("B", 3, 4, "quarter"),
    ]
}


# =============================================================================
# TONAL DOMAIN TEST FILES
# =============================================================================

TONAL_BASELINE = {
    "filename": "tonal_baseline_diatonic.musicxml",
    "description": "Pure diatonic (C major, no accidentals)",
    "expected_score_range": {"primary": [0.0, 0.2], "hazard": [0.0, 0.1]},
    "measures": [
        note("C", 4, 4, "quarter") + note("D", 4, 4, "quarter") +
        note("E", 4, 4, "quarter") + note("F", 4, 4, "quarter"),
        note("G", 4, 4, "quarter") + note("A", 4, 4, "quarter") +
        note("B", 4, 4, "quarter") + note("C", 5, 4, "quarter"),
        note("D", 5, 4, "quarter") + note("C", 5, 4, "quarter") +
        note("B", 4, 4, "quarter") + note("A", 4, 4, "quarter"),
        note("G", 4, 4, "quarter") + note("F", 4, 4, "quarter") +
        note("E", 4, 4, "quarter") + note("C", 4, 4, "quarter"),
    ]
}

TONAL_MODERATE = {
    "filename": "tonal_moderate_accidentals.musicxml",
    "description": "Some accidentals (secondary dominants, passing tones)",
    "expected_score_range": {"primary": [0.3, 0.5], "hazard": [0.1, 0.4]},
    "measures": [
        # F# as leading to G, Bb passing
        note("C", 4, 4, "quarter") + note("D", 4, 4, "quarter") +
        note("E", 4, 4, "quarter") + note("F", 4, 4, "quarter", alter=1),  # F#
        note("G", 4, 4, "quarter") + note("A", 4, 4, "quarter") +
        note("B", 4, 4, "quarter", alter=-1) + note("C", 5, 4, "quarter"),  # Bb
        note("D", 5, 4, "quarter") + note("C", 5, 4, "quarter", alter=1) +  # C#
        note("D", 5, 4, "quarter") + note("E", 5, 4, "quarter"),
        note("D", 5, 4, "quarter") + note("C", 5, 4, "quarter") +
        note("B", 4, 4, "quarter") + note("C", 5, 4, "quarter"),
    ]
}

TONAL_COMPLEX = {
    "filename": "tonal_complex_chromatic.musicxml",
    "description": "Chromatic scale passages",
    "expected_score_range": {"primary": [0.6, 0.9], "hazard": [0.5, 0.9]},
    "divisions": 4,
    "measures": [
        # Chromatic scale ascending
        note("C", 4, 2, "eighth") + note("C", 4, 2, "eighth", alter=1) +
        note("D", 4, 2, "eighth") + note("D", 4, 2, "eighth", alter=1) +
        note("E", 4, 2, "eighth") + note("F", 4, 2, "eighth") +
        note("F", 4, 2, "eighth", alter=1) + note("G", 4, 2, "eighth"),
        # Continue chromatic
        note("G", 4, 2, "eighth", alter=1) + note("A", 4, 2, "eighth") +
        note("A", 4, 2, "eighth", alter=1) + note("B", 4, 2, "eighth") +
        note("C", 5, 4, "quarter") + note("B", 4, 4, "quarter"),
        # Chromatic descending
        note("B", 4, 2, "eighth", alter=-1) + note("A", 4, 2, "eighth") +
        note("A", 4, 2, "eighth", alter=-1) + note("G", 4, 2, "eighth") +
        note("G", 4, 2, "eighth", alter=-1) + note("F", 4, 2, "eighth") +
        note("E", 4, 2, "eighth") + note("E", 4, 2, "eighth", alter=-1),
        # Resolve
        note("D", 4, 4, "quarter") + note("D", 4, 4, "quarter", alter=-1) +
        note("C", 4, 8, "half"),
    ]
}


# =============================================================================
# RANGE DOMAIN TEST FILES
# =============================================================================

RANGE_BASELINE = {
    "filename": "range_baseline_narrow.musicxml",
    "description": "Narrow range: 6th or less",
    "expected_score_range": {"primary": [0.0, 0.2]},  # Range doesn't have hazard
    "measures": [
        # C4 to A4 (M6)
        note("C", 4, 4, "quarter") + note("D", 4, 4, "quarter") +
        note("E", 4, 4, "quarter") + note("F", 4, 4, "quarter"),
        note("G", 4, 4, "quarter") + note("A", 4, 4, "quarter") +
        note("G", 4, 4, "quarter") + note("F", 4, 4, "quarter"),
        note("E", 4, 4, "quarter") + note("F", 4, 4, "quarter") +
        note("G", 4, 4, "quarter") + note("E", 4, 4, "quarter"),
        note("D", 4, 4, "quarter") + note("E", 4, 4, "quarter") +
        note("D", 4, 4, "quarter") + note("C", 4, 4, "quarter"),
    ]
}

RANGE_MODERATE = {
    "filename": "range_moderate_octave.musicxml",
    "description": "Moderate range: within octave",
    "expected_score_range": {"primary": [0.3, 0.5]},
    "measures": [
        # C4 to C5 (octave)
        note("C", 4, 4, "quarter") + note("E", 4, 4, "quarter") +
        note("G", 4, 4, "quarter") + note("C", 5, 4, "quarter"),
        note("B", 4, 4, "quarter") + note("A", 4, 4, "quarter") +
        note("G", 4, 4, "quarter") + note("F", 4, 4, "quarter"),
        note("E", 4, 4, "quarter") + note("D", 4, 4, "quarter") +
        note("C", 4, 4, "quarter") + note("G", 4, 4, "quarter"),
        note("C", 5, 4, "quarter") + note("G", 4, 4, "quarter") +
        note("E", 4, 4, "quarter") + note("C", 4, 4, "quarter"),
    ]
}

RANGE_COMPLEX = {
    "filename": "range_complex_wide.musicxml",
    "description": "Wide range: beyond octave (C4 to G5 = P12)",
    "expected_score_range": {"primary": [0.6, 0.9]},
    "measures": [
        # C4 to G5 (perfect 12th)
        note("C", 4, 4, "quarter") + note("G", 4, 4, "quarter") +
        note("C", 5, 4, "quarter") + note("G", 5, 4, "quarter"),
        note("E", 5, 4, "quarter") + note("C", 5, 4, "quarter") +
        note("G", 4, 4, "quarter") + note("E", 4, 4, "quarter"),
        note("C", 4, 4, "quarter") + note("F", 4, 4, "quarter") +
        note("D", 5, 4, "quarter") + note("G", 5, 4, "quarter"),
        note("F", 5, 4, "quarter") + note("D", 5, 4, "quarter") +
        note("B", 4, 4, "quarter") + note("C", 4, 4, "quarter"),
    ]
}


# =============================================================================
# FILE GENERATION
# =============================================================================

def generate_file(spec: dict, domain: str):
    """Generate a MusicXML file from a specification."""
    filename = spec["filename"]
    measures = spec["measures"]
    tempo = spec.get("tempo", 100)
    divisions = spec.get("divisions", 4)
    
    xml = wrap_musicxml_multi(
        measures=measures,
        title=spec.get("description", filename),
        tempo=tempo,
        divisions=divisions,
    )
    
    filepath = os.path.join(OUTPUT_DIR, filename)
    with open(filepath, "w") as f:
        f.write(xml)
    print(f"  Generated: {filename}")
    
    return {
        "filename": filename,
        "domain": domain,
        "level": spec["filename"].split("_")[1],  # baseline/moderate/complex
        "description": spec["description"],
        "expected_score_range": spec.get("expected_score_range", {}),
    }


def main():
    """Generate all scoring test MusicXML files."""
    print("Generating scoring domain test MusicXML files...")
    print(f"Output directory: {OUTPUT_DIR}")
    print()
    
    manifest = []
    
    # Interval domain
    print("Interval domain:")
    manifest.append(generate_file(INTERVAL_BASELINE, "interval"))
    manifest.append(generate_file(INTERVAL_MODERATE, "interval"))
    manifest.append(generate_file(INTERVAL_COMPLEX, "interval"))
    print()
    
    # Rhythm domain
    print("Rhythm domain:")
    manifest.append(generate_file(RHYTHM_BASELINE, "rhythm"))
    manifest.append(generate_file(RHYTHM_MODERATE, "rhythm"))
    manifest.append(generate_file(RHYTHM_COMPLEX, "rhythm"))
    print()
    
    # Pattern domain
    print("Pattern domain:")
    manifest.append(generate_file(PATTERN_BASELINE, "pattern"))
    manifest.append(generate_file(PATTERN_MODERATE, "pattern"))
    manifest.append(generate_file(PATTERN_COMPLEX, "pattern"))
    print()
    
    # Throughput domain
    print("Throughput domain:")
    manifest.append(generate_file(THROUGHPUT_BASELINE, "throughput"))
    manifest.append(generate_file(THROUGHPUT_MODERATE, "throughput"))
    manifest.append(generate_file(THROUGHPUT_COMPLEX, "throughput"))
    print()
    
    # Tonal domain
    print("Tonal domain:")
    manifest.append(generate_file(TONAL_BASELINE, "tonal"))
    manifest.append(generate_file(TONAL_MODERATE, "tonal"))
    manifest.append(generate_file(TONAL_COMPLEX, "tonal"))
    print()
    
    # Range domain
    print("Range domain:")
    manifest.append(generate_file(RANGE_BASELINE, "range"))
    manifest.append(generate_file(RANGE_MODERATE, "range"))
    manifest.append(generate_file(RANGE_COMPLEX, "range"))
    print()
    
    # Write manifest
    import json
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w") as f:
        json.dump({
            "description": "Scoring domain test files with expected score ranges",
            "domains": ["interval", "rhythm", "pattern", "throughput", "tonal", "range"],
            "levels": ["baseline", "moderate", "complex"],
            "files": manifest,
        }, f, indent=2)
    print(f"Wrote manifest to: {manifest_path}")
    
    print(f"\nGenerated {len(manifest)} scoring test files.")


if __name__ == "__main__":
    main()
