"""
Capability name mappings for MusicXML analysis.

Maps music21 element types to Sound First capability names.
"""

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
    'BreathMark': 'notation_breath_mark',
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
