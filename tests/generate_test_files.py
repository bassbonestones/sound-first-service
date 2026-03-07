#!/usr/bin/env python3
"""
Generate comprehensive test MusicXML files for capability detection testing.

Each file tests specific capabilities and includes metadata about expected detections.
"""
import os
import json

OUTPUT_DIR = "tests/test_musicxml_files"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# =============================================================================
# MusicXML Templates
# =============================================================================

def wrap_musicxml(content: str, title: str = "Test", divisions: int = 4, 
                  time_beats: int = 4, time_type: int = 4, 
                  key_fifths: int = 0, clef_sign: str = "G", clef_line: int = 2,
                  tempo: int = None) -> str:
    """Wrap content in a complete MusicXML document."""
    tempo_direction = ""
    if tempo:
        tempo_direction = f"""
      <direction>
        <direction-type>
          <metronome>
            <beat-unit>quarter</beat-unit>
            <per-minute>{tempo}</per-minute>
          </metronome>
        </direction-type>
        <sound tempo="{tempo}"/>
      </direction>"""
    
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>{title}</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>{divisions}</divisions>
        <key><fifths>{key_fifths}</fifths></key>
        <time><beats>{time_beats}</beats><beat-type>{time_type}</beat-type></time>
        <clef><sign>{clef_sign}</sign><line>{clef_line}</line></clef>
      </attributes>{tempo_direction}
{content}
    </measure>
  </part>
</score-partwise>'''


# =============================================================================
# Test File Definitions
# =============================================================================

TEST_FILES = {
    # =========================================================================
    # BASIC RHYTHM/NOTE VALUES
    # =========================================================================
    "01_whole_notes.musicxml": {
        "description": "Whole notes in 4/4",
        "expected": ["rhythm_whole_notes", "time_signature_4_4", "clef_treble", "time_signature_basics", "key_signature_basics"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>16</duration>
        <type>whole</type>
      </note>''', tempo=100)
    },
    
    "02_half_notes.musicxml": {
        "description": "Half notes in 4/4",
        "expected": ["rhythm_half_notes", "time_signature_4_4", "clef_treble"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "03_quarter_notes.musicxml": {
        "description": "Quarter notes in 4/4",
        "expected": ["rhythm_quarter_notes", "time_signature_4_4"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "04_eighth_notes.musicxml": {
        "description": "Eighth notes in 4/4",
        "expected": ["rhythm_eighth_notes", "time_signature_4_4", "diatonic_scale_fragment_3"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>''', tempo=100)
    },
    
    "05_sixteenth_notes.musicxml": {
        "description": "Sixteenth notes in 4/4",
        "expected": ["rhythm_sixteenth_notes", "time_signature_4_4"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "06_32nd_notes.musicxml": {
        "description": "32nd notes",
        "expected": ["rhythm_32nd_notes", "time_signature_4_4"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>32nd</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>32nd</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>32nd</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>32nd</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>12</duration>
        <type>half</type>
        <dot/>
      </note>''', divisions=4, tempo=100)
    },
    
    # =========================================================================
    # DOTTED RHYTHMS
    # =========================================================================
    "07_dotted_half.musicxml": {
        "description": "Dotted half note",
        "expected": ["rhythm_dotted_half", "rhythm_half_notes", "time_signature_4_4"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>12</duration>
        <type>half</type>
        <dot/>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "08_dotted_quarter.musicxml": {
        "description": "Dotted quarter note",
        "expected": ["rhythm_dotted_quarter", "rhythm_quarter_notes", "rhythm_eighth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>6</duration>
        <type>quarter</type>
        <dot/>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "09_dotted_eighth.musicxml": {
        "description": "Dotted eighth note",
        "expected": ["rhythm_dotted_eighth", "rhythm_eighth_notes", "rhythm_sixteenth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>3</duration>
        <type>eighth</type>
        <dot/>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>3</duration>
        <type>eighth</type>
        <dot/>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # TIME SIGNATURES
    # =========================================================================
    "10_time_sig_3_4.musicxml": {
        "description": "3/4 time signature",
        "expected": ["time_signature_3_4", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', time_beats=3, time_type=4, tempo=100)
    },
    
    "11_time_sig_6_8.musicxml": {
        "description": "6/8 time signature",
        "expected": ["time_signature_6_8", "rhythm_eighth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>''', time_beats=6, time_type=8, tempo=100)
    },
    
    "12_time_sig_2_4.musicxml": {
        "description": "2/4 time signature",
        "expected": ["time_signature_2_4", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', time_beats=2, time_type=4, tempo=100)
    },
    
    "13_time_sig_2_2.musicxml": {
        "description": "2/2 (cut time) time signature",
        "expected": ["time_signature_2_2", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', time_beats=2, time_type=2, tempo=100)
    },
    
    "14_time_sig_7_8.musicxml": {
        "description": "7/8 time signature",
        "expected": ["time_signature_7_8", "rhythm_eighth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>''', time_beats=7, time_type=8, tempo=100)
    },
    
    "15_time_sig_5_4.musicxml": {
        "description": "5/4 time signature",
        "expected": ["time_signature_5_4", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', time_beats=5, time_type=4, tempo=100)
    },
    
    # =========================================================================
    # CLEFS
    # =========================================================================
    "16_clef_bass.musicxml": {
        "description": "Bass clef",
        "expected": ["clef_bass", "rhythm_whole_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>3</octave></pitch>
        <duration>16</duration>
        <type>whole</type>
      </note>''', clef_sign="F", clef_line=4, tempo=100)
    },
    
    "17_clef_alto.musicxml": {
        "description": "Alto clef (viola)",
        "expected": ["clef_alto", "rhythm_whole_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>16</duration>
        <type>whole</type>
      </note>''', clef_sign="C", clef_line=3, tempo=100)
    },
    
    "18_clef_tenor.musicxml": {
        "description": "Tenor clef",
        "expected": ["clef_tenor", "rhythm_whole_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>16</duration>
        <type>whole</type>
      </note>''', clef_sign="C", clef_line=4, tempo=100)
    },
    
    # =========================================================================
    # DYNAMICS
    # =========================================================================
    "19_dynamics_basic.musicxml": {
        "description": "Basic dynamics (f, p, mf, mp)",
        "expected": ["dynamic_f", "dynamic_p", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type><dynamics><f/></dynamics></direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <direction>
        <direction-type><dynamics><p/></dynamics></direction-type>
      </direction>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "20_dynamics_extremes.musicxml": {
        "description": "Extreme dynamics (fff, ppp)",
        "expected": ["dynamic_fff", "dynamic_ppp", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type><dynamics><fff/></dynamics></direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <direction>
        <direction-type><dynamics><ppp/></dynamics></direction-type>
      </direction>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "21_dynamics_sfz.musicxml": {
        "description": "Sforzando dynamics (sf, sfz)",
        "expected": ["dynamic_sf", "dynamic_sfz", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type><dynamics><sf/></dynamics></direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <direction>
        <direction-type><dynamics><sfz/></dynamics></direction-type>
      </direction>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # ARTICULATIONS
    # =========================================================================
    "22_articulations_staccato.musicxml": {
        "description": "Staccato articulation",
        "expected": ["articulation_staccato", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
        <notations>
          <articulations><staccato/></articulations>
        </notations>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
        <notations>
          <articulations><staccato/></articulations>
        </notations>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "23_articulations_accent.musicxml": {
        "description": "Accent articulation",
        "expected": ["articulation_accent", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
        <notations>
          <articulations><accent/></articulations>
        </notations>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "24_articulations_tenuto.musicxml": {
        "description": "Tenuto articulation",
        "expected": ["articulation_tenuto", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
        <notations>
          <articulations><tenuto/></articulations>
        </notations>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
        <notations>
          <articulations><tenuto/></articulations>
        </notations>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "25_articulations_marcato.musicxml": {
        "description": "Marcato (strong accent) articulation",
        "expected": ["articulation_marcato", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
        <notations>
          <articulations><strong-accent/></articulations>
        </notations>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # RESTS
    # =========================================================================
    "26_rests_whole.musicxml": {
        "description": "Whole rest",
        "expected": ["rest_whole", "time_signature_4_4"],
        "content": wrap_musicxml('''
      <note>
        <rest/>
        <duration>16</duration>
        <type>whole</type>
      </note>''', tempo=100)
    },
    
    "27_rests_half.musicxml": {
        "description": "Half rest",
        "expected": ["rest_half", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <rest/>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "28_rests_quarter.musicxml": {
        "description": "Quarter rest",
        "expected": ["rest_quarter", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <rest/>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <rest/>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "29_rests_eighth.musicxml": {
        "description": "Eighth rest",
        "expected": ["rest_eighth", "rhythm_eighth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <rest/>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <rest/>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "30_rests_sixteenth.musicxml": {
        "description": "Sixteenth rest",
        "expected": ["rest_sixteenth", "rhythm_sixteenth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <rest/>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <rest/>
        <duration>1</duration>
        <type>16th</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>12</duration>
        <type>half</type>
        <dot/>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # INTERVALS
    # =========================================================================
    "31_interval_minor_2.musicxml": {
        "description": "Minor 2nd interval (semitone)",
        "expected": ["interval_play_minor_2", "diatonic_scale_fragment_2", "tonal_chromatic_approach_tones"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>D</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "32_interval_major_3.musicxml": {
        "description": "Major 3rd interval",
        "expected": ["interval_play_major_3", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "33_interval_perfect_5.musicxml": {
        "description": "Perfect 5th interval",
        "expected": ["interval_play_perfect_5", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "34_interval_octave.musicxml": {
        "description": "Octave interval",
        "expected": ["interval_play_octave", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "35_interval_augmented_4.musicxml": {
        "description": "Augmented 4th (tritone) interval",
        "expected": ["interval_play_augmented_4", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>F</step><alter>1</alter><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # ACCIDENTALS
    # =========================================================================
    "36_accidental_sharp.musicxml": {
        "description": "Sharp accidental",
        "expected": ["accidental_sharp_symbol", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>F</step><alter>1</alter><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
        <accidental>sharp</accidental>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "37_accidental_flat.musicxml": {
        "description": "Flat accidental",
        "expected": ["accidental_flat_symbol", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
        <accidental>flat</accidental>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # TIES
    # =========================================================================
    "38_ties.musicxml": {
        "description": "Tied notes",
        "expected": ["notation_ties", "rhythm_ties_across_beats", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
        <tie type="start"/>
        <notations>
          <tied type="start"/>
        </notations>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
        <tie type="stop"/>
        <notations>
          <tied type="stop"/>
        </notations>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # ORNAMENTS
    # =========================================================================
    "39_ornament_trill.musicxml": {
        "description": "Trill ornament",
        "expected": ["ornament_trill", "rhythm_whole_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>16</duration>
        <type>whole</type>
        <notations>
          <ornaments><trill-mark/></ornaments>
        </notations>
      </note>''', tempo=100)
    },
    
    "40_ornament_mordent.musicxml": {
        "description": "Mordent ornament",
        "expected": ["ornament_mordent", "rhythm_whole_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>16</duration>
        <type>whole</type>
        <notations>
          <ornaments><mordent/></ornaments>
        </notations>
      </note>''', tempo=100)
    },
    
    "41_ornament_turn.musicxml": {
        "description": "Turn ornament",
        "expected": ["ornament_turn", "rhythm_whole_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>16</duration>
        <type>whole</type>
        <notations>
          <ornaments><turn/></ornaments>
        </notations>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # FERMATA
    # =========================================================================
    "42_fermata.musicxml": {
        "description": "Fermata notation",
        "expected": ["notation_fermata", "rhythm_whole_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>16</duration>
        <type>whole</type>
        <notations>
          <fermata type="upright"/>
        </notations>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # KEY SIGNATURES
    # =========================================================================
    "43_key_sig_g_major.musicxml": {
        "description": "G major key signature (1 sharp)",
        "expected": ["key_signature_basics", "rhythm_whole_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>16</duration>
        <type>whole</type>
      </note>''', key_fifths=1, tempo=100)
    },
    
    "44_key_sig_f_major.musicxml": {
        "description": "F major key signature (1 flat)",
        "expected": ["key_signature_basics", "rhythm_whole_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>16</duration>
        <type>whole</type>
      </note>''', key_fifths=-1, tempo=100)
    },
    
    # =========================================================================
    # TEMPO MARKINGS
    # =========================================================================
    "45_tempo_allegro.musicxml": {
        "description": "Allegro tempo marking",
        "expected": ["tempo_term_allegro", "rhythm_quarter_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Test</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction>
        <direction-type>
          <words>Allegro</words>
        </direction-type>
        <sound tempo="120"/>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "46_tempo_andante.musicxml": {
        "description": "Andante tempo marking",
        "expected": ["tempo_term_andante", "rhythm_quarter_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Test</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction>
        <direction-type>
          <words>Andante</words>
        </direction-type>
        <sound tempo="76"/>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    # =========================================================================
    # EXPRESSION TERMS
    # =========================================================================
    "47_expression_dolce.musicxml": {
        "description": "Dolce expression",
        "expected": ["expression_dolce", "rhythm_half_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Test</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction>
        <direction-type>
          <words>dolce</words>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "48_expression_espressivo.musicxml": {
        "description": "Espressivo expression",
        "expected": ["expression_espressivo", "rhythm_half_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1"><part-name>Test</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction>
        <direction-type>
          <words>espressivo</words>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    # =========================================================================
    # SCALE FRAGMENTS
    # =========================================================================
    "49_scale_ascending.musicxml": {
        "description": "Ascending scale (tests scale fragments)",
        "expected": ["diatonic_scale_fragment_7", "diatonic_scale_fragment_6", "diatonic_scale_fragment_5", 
                     "diatonic_scale_fragment_4", "diatonic_scale_fragment_3", "diatonic_scale_fragment_2",
                     "rhythm_eighth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # STAGE 1: TIME SIGNATURES (Additional)
    # =========================================================================
    "50_time_sig_9_8.musicxml": {
        "description": "9/8 time signature (compound triple)",
        "expected": ["time_signature_9_8", "rhythm_eighth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>5</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>''', time_beats=9, time_type=8, tempo=100)
    },
    
    "51_time_sig_12_8.musicxml": {
        "description": "12/8 time signature (compound quadruple)",
        "expected": ["time_signature_12_8", "rhythm_eighth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>5</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>5</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>F</step><octave>5</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>5</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>''', time_beats=12, time_type=8, tempo=100)
    },
    
    "52_time_sig_3_8.musicxml": {
        "description": "3/8 time signature",
        "expected": ["time_signature_3_8", "rhythm_eighth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>''', time_beats=3, time_type=8, tempo=100)
    },
    
    "53_time_sig_3_2.musicxml": {
        "description": "3/2 time signature",
        "expected": ["time_signature_3_2", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', time_beats=3, time_type=2, tempo=100)
    },
    
    "54_time_sig_6_4.musicxml": {
        "description": "6/4 time signature",
        "expected": ["time_signature_6_4", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', time_beats=6, time_type=4, tempo=100)
    },
    
    "55_time_sig_5_8.musicxml": {
        "description": "5/8 time signature (asymmetric)",
        "expected": ["time_signature_5_8", "rhythm_eighth_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>2</duration>
        <type>eighth</type>
      </note>''', time_beats=5, time_type=8, tempo=100)
    },
    
    # =========================================================================
    # STAGE 1: DYNAMICS (Value Match)
    # =========================================================================
    "56_dynamic_ff.musicxml": {
        "description": "Fortissimo (ff) dynamic",
        "expected": ["dynamic_ff", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type>
          <dynamics><ff/></dynamics>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "57_dynamic_pp.musicxml": {
        "description": "Pianissimo (pp) dynamic",
        "expected": ["dynamic_pp", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type>
          <dynamics><pp/></dynamics>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "58_dynamic_mf.musicxml": {
        "description": "Mezzo forte (mf) dynamic",
        "expected": ["dynamic_mf", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type>
          <dynamics><mf/></dynamics>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "59_dynamic_mp.musicxml": {
        "description": "Mezzo piano (mp) dynamic",
        "expected": ["dynamic_mp", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type>
          <dynamics><mp/></dynamics>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "60_dynamic_fp.musicxml": {
        "description": "Forte-piano (fp) dynamic",
        "expected": ["dynamic_fp", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type>
          <dynamics><fp/></dynamics>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "61_dynamic_rf.musicxml": {
        "description": "Rinforzando (rf) dynamic",
        "expected": ["dynamic_rf", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type>
          <dynamics><rf/></dynamics>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "62_dynamic_rfz.musicxml": {
        "description": "Rinforzando (rfz) dynamic",
        "expected": ["dynamic_rfz", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type>
          <dynamics><rfz/></dynamics>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "63_dynamic_sfp.musicxml": {
        "description": "Sforzando-piano (sfp) dynamic",
        "expected": ["dynamic_sfp", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <direction>
        <direction-type>
          <dynamics><sfp/></dynamics>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # STAGE 1: DYNAMICS (Element - Crescendo/Decrescendo)
    # =========================================================================
    "64_dynamic_crescendo.musicxml": {
        "description": "Crescendo (hairpin)",
        "expected": ["dynamic_crescendo", "rhythm_quarter_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Crescendo Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction>
        <direction-type>
          <wedge type="crescendo"/>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <direction>
        <direction-type>
          <wedge type="stop"/>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "65_dynamic_decrescendo.musicxml": {
        "description": "Decrescendo (hairpin)",
        "expected": ["dynamic_decrescendo", "rhythm_quarter_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Decrescendo Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction>
        <direction-type>
          <wedge type="diminuendo"/>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <direction>
        <direction-type>
          <wedge type="stop"/>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "66_dynamic_diminuendo.musicxml": {
        "description": "Diminuendo text marking",
        "expected": ["dynamic_diminuendo", "rhythm_half_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Diminuendo Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction>
        <direction-type>
          <wedge type="diminuendo"/>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <direction>
        <direction-type>
          <wedge type="stop"/>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "67_dynamic_subito.musicxml": {
        "description": "Subito dynamic change",
        "expected": ["dynamic_subito", "rhythm_quarter_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Subito Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <direction>
        <direction-type>
          <words>subito piano</words>
        </direction-type>
      </direction>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    # =========================================================================
    # STAGE 2: INTERVALS (Additional)
    # =========================================================================
    "68_interval_major_2.musicxml": {
        "description": "Major 2nd interval (whole step)",
        "expected": ["interval_play_major_2", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "69_interval_minor_3.musicxml": {
        "description": "Minor 3rd interval",
        "expected": ["interval_play_minor_3", "rhythm_half_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Minor 3rd Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>E</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "70_interval_perfect_4.musicxml": {
        "description": "Perfect 4th interval",
        "expected": ["interval_play_perfect_4", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "71_interval_minor_6.musicxml": {
        "description": "Minor 6th interval",
        "expected": ["interval_play_minor_6", "rhythm_half_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Minor 6th Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>A</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "72_interval_major_6.musicxml": {
        "description": "Major 6th interval",
        "expected": ["interval_play_major_6", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "73_interval_minor_7.musicxml": {
        "description": "Minor 7th interval",
        "expected": ["interval_play_minor_7", "rhythm_half_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Minor 7th Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "74_interval_major_7.musicxml": {
        "description": "Major 7th interval",
        "expected": ["interval_play_major_7", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    "75_interval_compound_9.musicxml": {
        "description": "Compound interval (9th or greater)",
        "expected": ["interval_play_compound_9_plus", "rhythm_half_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>
      <note>
        <pitch><step>D</step><octave>5</octave></pitch>
        <duration>8</duration>
        <type>half</type>
      </note>''', tempo=100)
    },
    
    # =========================================================================
    # STAGE 2: RANGE SPANS
    # =========================================================================
    "76_range_minor_second.musicxml": {
        "description": "Range span of minor 2nd (1 semitone)",
        "expected": ["range_span_minor_second", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>D</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "77_range_major_second.musicxml": {
        "description": "Range span of major 2nd (2 semitones)",
        "expected": ["range_span_major_second", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "78_range_minor_third.musicxml": {
        "description": "Range span of minor 3rd (3 semitones)",
        "expected": ["range_span_minor_third", "rhythm_quarter_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Range Minor 3rd Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "79_range_major_third.musicxml": {
        "description": "Range span of major 3rd (4 semitones)",
        "expected": ["range_span_major_third", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>D</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "80_range_perfect_fourth.musicxml": {
        "description": "Range span of perfect 4th (5 semitones)",
        "expected": ["range_span_perfect_fourth", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>F</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "81_range_augmented_fourth.musicxml": {
        "description": "Range span of augmented 4th / tritone (6 semitones)",
        "expected": ["range_span_augmented_fourth", "rhythm_quarter_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Range Tritone Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>F</step><alter>1</alter><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "82_range_perfect_fifth.musicxml": {
        "description": "Range span of perfect 5th (7 semitones)",
        "expected": ["range_span_perfect_fifth", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "83_range_minor_sixth.musicxml": {
        "description": "Range span of minor 6th (8 semitones)",
        "expected": ["range_span_minor_sixth", "rhythm_quarter_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Range Minor 6th Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>A</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "84_range_major_sixth.musicxml": {
        "description": "Range span of major 6th (9 semitones)",
        "expected": ["range_span_major_sixth", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>A</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "85_range_minor_seventh.musicxml": {
        "description": "Range span of minor 7th (10 semitones)",
        "expected": ["range_span_minor_seventh", "rhythm_quarter_notes"],
        "content": '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <work><work-title>Range Minor 7th Test</work-title></work>
  <part-list>
    <score-part id="P1"><part-name>Test Part</part-name></score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>4</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>B</step><alter>-1</alter><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
    </measure>
  </part>
</score-partwise>'''
    },
    
    "86_range_major_seventh.musicxml": {
        "description": "Range span of major 7th (11 semitones)",
        "expected": ["range_span_major_seventh", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>B</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>E</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
    
    "87_range_octave.musicxml": {
        "description": "Range span of octave (12 semitones)",
        "expected": ["range_span_octave", "rhythm_quarter_notes"],
        "content": wrap_musicxml('''
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>5</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>G</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>quarter</type>
      </note>''', tempo=100)
    },
}

# =============================================================================
# Generate Files
# =============================================================================

def main():
    print(f"Generating {len(TEST_FILES)} test MusicXML files...")
    
    manifest = {}
    
    for filename, info in TEST_FILES.items():
        filepath = os.path.join(OUTPUT_DIR, filename)
        with open(filepath, 'w') as f:
            f.write(info['content'])
        
        manifest[filename] = {
            "description": info['description'],
            "expected_capabilities": info['expected']
        }
        
        print(f"  ✓ {filename}: {info['description']}")
    
    # Save manifest
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n✓ Generated {len(TEST_FILES)} files")
    print(f"✓ Saved manifest to {manifest_path}")
    
    # Generate markdown index
    generate_index_markdown()


def generate_index_markdown():
    """Generate the index markdown file."""
    md_content = """# Test MusicXML Files Index

This directory contains test MusicXML files for comprehensive capability detection testing.
Each file is designed to test specific musical capabilities that can be detected via music21.

## File Organization

Files are numbered and organized by category:
- 01-09: Basic note values (whole, half, quarter, eighth, sixteenth, 32nd)
- 07-09: Dotted rhythms
- 10-15: Time signatures
- 16-18: Clefs
- 19-21: Dynamics
- 22-25: Articulations
- 26-30: Rests
- 31-35: Intervals
- 36-37: Accidentals
- 38: Ties
- 39-41: Ornaments
- 42: Fermata
- 43-44: Key signatures
- 45-46: Tempo markings
- 47-48: Expression terms
- 49: Scale fragments

## Test Files

| File | Description | Expected Capabilities |
|------|-------------|----------------------|
"""
    
    for filename, info in sorted(TEST_FILES.items()):
        caps = ", ".join(f"`{c}`" for c in info['expected'][:5])
        if len(info['expected']) > 5:
            caps += f" (+{len(info['expected'])-5} more)"
        md_content += f"| {filename} | {info['description']} | {caps} |\n"
    
    md_content += """
## Running Tests

```bash
cd sound-first-service
python -m pytest tests/test_comprehensive_detection.py -v
```

## Adding New Test Files

1. Add a new entry to `generate_test_files.py` in the `TEST_FILES` dict
2. Run `python generate_test_files.py` to regenerate files
3. The manifest.json will be updated automatically

## Manifest

The `manifest.json` file contains machine-readable metadata about each test file,
including descriptions and expected capability detections. This is used by the
test suite to verify detection accuracy.
"""
    
    index_path = os.path.join(OUTPUT_DIR, "README.md")
    with open(index_path, 'w') as f:
        f.write(md_content)
    
    print(f"✓ Generated index at {index_path}")


if __name__ == "__main__":
    main()
