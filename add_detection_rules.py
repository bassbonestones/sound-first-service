#!/usr/bin/env python3
"""
Add music21_detection rules to all capabilities that can be automatically detected.

Categories:
- DETECTABLE: Can be detected from MusicXML via music21
- NOT_DETECTABLE: Theory concepts, user behaviors, or require external context

This script adds detection rules for all detectable capabilities.
"""
import json

# Load capabilities
with open('app/resources/capabilities.json', 'r') as f:
    data = json.load(f)

# Map capability names to detection rules
DETECTION_RULES = {
    # ==========================================================================
    # ACCIDENTALS - Detected from note.pitch.alter
    # ==========================================================================
    "accidental_flat_symbol": {
        "type": "custom",
        "function": "detect_flat_accidentals"
    },
    "accidental_sharp_symbol": {
        "type": "custom",
        "function": "detect_sharp_accidentals"
    },
    "accidental_natural_symbol": {
        "type": "custom",
        "function": "detect_natural_accidentals"
    },
    "double_flat_symbol": {
        "type": "custom",
        "function": "detect_double_flat_accidentals"
    },
    "double_sharp_symbol": {
        "type": "custom",
        "function": "detect_double_sharp_accidentals"
    },
    
    # ==========================================================================
    # ARTICULATIONS
    # ==========================================================================
    "articulation_legato": {
        "type": "element",
        "class": "music21.spanner.Slur"
    },
    "articulation_staccato": {
        "type": "element",
        "class": "music21.articulations.Staccato"
    },
    "articulation_staccatissimo": {
        "type": "element",
        "class": "music21.articulations.Staccatissimo"
    },
    "articulation_accent": {
        "type": "element",
        "class": "music21.articulations.Accent"
    },
    "articulation_marcato": {
        "type": "element",
        "class": "music21.articulations.StrongAccent"
    },
    "articulation_tenuto": {
        "type": "element",
        "class": "music21.articulations.Tenuto"
    },
    "articulation_portato": {
        "type": "element",
        "class": "music21.articulations.DetachedLegato"
    },
    
    # ==========================================================================
    # BASIC NOTE VALUES (RHYTHMS)
    # ==========================================================================
    "rhythm_whole_notes": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "whole"
    },
    "rhythm_half_notes": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "half"
    },
    "rhythm_quarter_notes": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "quarter"
    },
    "rhythm_eighth_notes": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "eighth"
    },
    "rhythm_sixteenth_notes": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "sixteenth"
    },
    "rhythm_32nd_notes": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "32nd"
    },
    "rhythm_64th_notes": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "64th"
    },
    
    # ==========================================================================
    # DOTTED RHYTHMS
    # ==========================================================================
    "rhythm_dotted_half": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "dotted_half"
    },
    "rhythm_dotted_quarter": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "dotted_quarter"
    },
    "rhythm_dotted_eighth": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "dotted_eighth"
    },
    
    # ==========================================================================
    # TIES AND SYNCOPATION
    # ==========================================================================
    "notation_ties": {
        "type": "custom",
        "function": "detect_ties"
    },
    "rhythm_syncopation": {
        "type": "custom",
        "function": "detect_syncopation"
    },
    
    # ==========================================================================
    # CLEFS - Basic clefs
    # ==========================================================================
    "clef_treble": {
        "type": "element",
        "class": "music21.clef.TrebleClef"
    },
    "clef_bass": {
        "type": "element",
        "class": "music21.clef.BassClef"
    },
    "clef_alto": {
        "type": "element",
        "class": "music21.clef.AltoClef"
    },
    "clef_tenor": {
        "type": "element",
        "class": "music21.clef.TenorClef"
    },
    
    # ==========================================================================
    # CLEFS - Octave transposing clefs
    # ==========================================================================
    "clef_bass_8va": {
        "type": "custom",
        "function": "detect_clef_bass_8va"
    },
    "clef_treble_8vb": {
        "type": "custom",
        "function": "detect_clef_treble_8vb"
    },
    # clef_movable_c_f_g is a theory concept, not detectable
    
    # ==========================================================================
    # DYNAMICS - Basic dynamic levels
    # ==========================================================================
    "dynamic_ppp": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "ppp"
    },
    "dynamic_pp": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "pp"
    },
    "dynamic_p": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "p"
    },
    "dynamic_mp": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "mp"
    },
    "dynamic_mf": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "mf"
    },
    "dynamic_f": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "f"
    },
    "dynamic_ff": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "ff"
    },
    "dynamic_fff": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "fff"
    },
    "dynamic_sf": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "sf"
    },
    "dynamic_sfz": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "sfz"
    },
    "dynamic_fp": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "fp"
    },
    
    # ==========================================================================
    # DYNAMICS - Crescendo/Decrescendo via wedges
    # ==========================================================================
    "dynamic_crescendo": {
        "type": "element",
        "class": "music21.dynamics.Crescendo"
    },
    "dynamic_decrescendo": {
        "type": "custom",
        "function": "detect_decrescendo"
    },
    "dynamic_diminuendo": {
        "type": "element",
        "class": "music21.dynamics.Diminuendo"
    },
    "dynamic_rf": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "rf"
    },
    "dynamic_rfz": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "rfz"
    },
    "dynamic_sfp": {
        "type": "value_match",
        "source": "dynamics",
        "field": "value",
        "eq": "sfp"
    },
    "dynamic_subito": {
        "type": "custom",
        "function": "detect_subito"
    },
    
    # ==========================================================================
    # EXPRESSION TERMS - Text matching
    # ==========================================================================
    "expression_agitato": {
        "type": "text_match",
        "source": "expressions",
        "contains": "agitato"
    },
    "expression_animato": {
        "type": "text_match",
        "source": "expressions",
        "contains": "animato"
    },
    "expression_appassionato": {
        "type": "text_match",
        "source": "expressions",
        "contains": "appassionato"
    },
    "expression_brillante": {
        "type": "text_match",
        "source": "expressions",
        "contains": "brillante"
    },
    "expression_con_brio": {
        "type": "text_match",
        "source": "expressions",
        "contains": "con brio"
    },
    "expression_con_fuoco": {
        "type": "text_match",
        "source": "expressions",
        "contains": "con fuoco"
    },
    "expression_con_moto": {
        "type": "text_match",
        "source": "expressions",
        "contains": "con moto"
    },
    "expression_grazioso": {
        "type": "text_match",
        "source": "expressions",
        "contains": "grazioso"
    },
    "expression_leggiero": {
        "type": "text_match",
        "source": "expressions",
        "contains": "leggiero"
    },
    "expression_maestoso": {
        "type": "text_match",
        "source": "expressions",
        "contains": "maestoso"
    },
    "expression_morendo": {
        "type": "text_match",
        "source": "expressions",
        "contains": "morendo"
    },
    "expression_perdendosi": {
        "type": "text_match",
        "source": "expressions",
        "contains": "perdendosi"
    },
    "expression_pesante": {
        "type": "text_match",
        "source": "expressions",
        "contains": "pesante"
    },
    "expression_sostenuto": {
        "type": "text_match",
        "source": "expressions",
        "contains": "sostenuto"
    },
    "expression_tranquillo": {
        "type": "text_match",
        "source": "expressions",
        "contains": "tranquillo"
    },
    "expression_dolce": {
        "type": "text_match",
        "source": "expressions",
        "contains": "dolce"
    },
    "expression_espressivo": {
        "type": "text_match",
        "source": "expressions",
        "contains": "espressivo"
    },
    "expression_cantabile": {
        "type": "text_match",
        "source": "expressions",
        "contains": "cantabile"
    },
    
    # ==========================================================================
    # FORM - Repeats, endings, navigation
    # ==========================================================================
    "form_coda": {
        "type": "custom",
        "function": "detect_coda"
    },
    "form_dc": {
        "type": "custom",
        "function": "detect_da_capo"
    },
    "form_ds": {
        "type": "custom",
        "function": "detect_dal_segno"
    },
    "form_fine": {
        "type": "custom",
        "function": "detect_fine"
    },
    "form_first_ending": {
        "type": "custom",
        "function": "detect_first_ending"
    },
    "form_repeat_sign": {
        "type": "custom",
        "function": "detect_repeat_sign"
    },
    "form_second_ending": {
        "type": "custom",
        "function": "detect_second_ending"
    },
    "form_segno": {
        "type": "custom",
        "function": "detect_segno"
    },
    
    # ==========================================================================
    # INSTRUMENT TECHNIQUE
    # ==========================================================================
    "technique_glissando": {
        "type": "element",
        "class": "music21.spanner.Glissando"
    },
    
    # ==========================================================================
    # INTERVALS - Basic melodic intervals
    # ==========================================================================
    "interval_play_minor_2": {
        "type": "interval",
        "quality": "m2",
        "melodic": True
    },
    "interval_play_major_2": {
        "type": "interval",
        "quality": "M2",
        "melodic": True
    },
    "interval_play_minor_3": {
        "type": "interval",
        "quality": "m3",
        "melodic": True
    },
    "interval_play_major_3": {
        "type": "interval",
        "quality": "M3",
        "melodic": True
    },
    "interval_play_perfect_4": {
        "type": "interval",
        "quality": "P4",
        "melodic": True
    },
    "interval_play_augmented_4": {
        "type": "interval",
        "quality": "A4",
        "melodic": True
    },
    "interval_play_perfect_5": {
        "type": "interval",
        "quality": "P5",
        "melodic": True
    },
    "interval_play_minor_6": {
        "type": "interval",
        "quality": "m6",
        "melodic": True
    },
    "interval_play_major_6": {
        "type": "interval",
        "quality": "M6",
        "melodic": True
    },
    "interval_play_minor_7": {
        "type": "interval",
        "quality": "m7",
        "melodic": True
    },
    "interval_play_major_7": {
        "type": "interval",
        "quality": "M7",
        "melodic": True
    },
    "interval_play_octave": {
        "type": "interval",
        "quality": "P8",
        "melodic": True
    },
    "interval_play_compound_9_plus": {
        "type": "custom",
        "function": "detect_compound_intervals"
    },
    
    # ==========================================================================
    # METER - Time signatures
    # ==========================================================================
    "time_signature_basics": {
        "type": "custom",
        "function": "detect_any_time_signature"
    },
    "time_signature_4_4": {
        "type": "time_signature",
        "numerator": 4,
        "denominator": 4
    },
    "time_signature_3_4": {
        "type": "time_signature",
        "numerator": 3,
        "denominator": 4
    },
    "time_signature_2_4": {
        "type": "time_signature",
        "numerator": 2,
        "denominator": 4
    },
    "time_signature_2_2": {
        "type": "time_signature",
        "numerator": 2,
        "denominator": 2
    },
    "time_signature_6_8": {
        "type": "time_signature",
        "numerator": 6,
        "denominator": 8
    },
    "time_signature_3_8": {
        "type": "time_signature",
        "numerator": 3,
        "denominator": 8
    },
    "time_signature_7_8": {
        "type": "time_signature",
        "numerator": 7,
        "denominator": 8
    },
    "time_signature_9_8": {
        "type": "time_signature",
        "numerator": 9,
        "denominator": 8
    },
    "time_signature_12_8": {
        "type": "time_signature",
        "numerator": 12,
        "denominator": 8
    },
    "time_signature_5_4": {
        "type": "time_signature",
        "numerator": 5,
        "denominator": 4
    },
    "time_signature_5_8": {
        "type": "time_signature",
        "numerator": 5,
        "denominator": 8
    },
    "time_signature_3_2": {
        "type": "time_signature",
        "numerator": 3,
        "denominator": 2
    },
    "time_signature_6_4": {
        "type": "time_signature",
        "numerator": 6,
        "denominator": 4
    },
    "time_signature_3_16": {
        "type": "time_signature",
        "numerator": 3,
        "denominator": 16
    },
    
    # ==========================================================================
    # NOTATION SYMBOLS
    # ==========================================================================
    "notation_breath_mark": {
        "type": "custom",
        "function": "detect_breath_mark"
    },
    "notation_fermata": {
        "type": "element",
        "class": "music21.expressions.Fermata"
    },
    "notation_chord_symbols": {
        "type": "custom",
        "function": "detect_chord_symbols"
    },
    "notation_figured_bass": {
        "type": "custom",
        "function": "detect_figured_bass"
    },
    
    # ==========================================================================
    # KEY SIGNATURES
    # ==========================================================================
    "key_signature_basics": {
        "type": "custom",
        "function": "detect_any_key_signature"
    },
    
    # ==========================================================================
    # ORNAMENTS
    # ==========================================================================
    "ornament_trill": {
        "type": "element",
        "class": "music21.expressions.Trill"
    },
    "ornament_mordent": {
        "type": "element",
        "class": "music21.expressions.Mordent"
    },
    "ornament_inverted_mordent": {
        "type": "element",
        "class": "music21.expressions.InvertedMordent"
    },
    "ornament_turn": {
        "type": "element",
        "class": "music21.expressions.Turn"
    },
    "ornament_grace_note": {
        "type": "custom",
        "function": "detect_grace_note"
    },
    "ornament_tremolo": {
        "type": "element",
        "class": "music21.expressions.Tremolo"
    },
    
    # ==========================================================================
    # RANGE SPAN - Based on range analysis
    # ==========================================================================
    "range_span_minor_second": {
        "type": "range",
        "min_semitones": 1,
        "max_semitones": 1
    },
    "range_span_major_second": {
        "type": "range",
        "min_semitones": 2,
        "max_semitones": 2
    },
    "range_span_minor_third": {
        "type": "range",
        "min_semitones": 3,
        "max_semitones": 3
    },
    "range_span_major_third": {
        "type": "range",
        "min_semitones": 4,
        "max_semitones": 4
    },
    "range_span_perfect_fourth": {
        "type": "range",
        "min_semitones": 5,
        "max_semitones": 5
    },
    "range_span_augmented_fourth": {
        "type": "range",
        "min_semitones": 6,
        "max_semitones": 6
    },
    "range_span_perfect_fifth": {
        "type": "range",
        "min_semitones": 7,
        "max_semitones": 7
    },
    "range_span_minor_sixth": {
        "type": "range",
        "min_semitones": 8,
        "max_semitones": 8
    },
    "range_span_major_sixth": {
        "type": "range",
        "min_semitones": 9,
        "max_semitones": 9
    },
    "range_span_minor_seventh": {
        "type": "range",
        "min_semitones": 10,
        "max_semitones": 10
    },
    "range_span_major_seventh": {
        "type": "range",
        "min_semitones": 11,
        "max_semitones": 11
    },
    "range_span_octave": {
        "type": "range",
        "min_semitones": 12,
        "max_semitones": 12
    },
    
    # ==========================================================================
    # RESTS - Rest types by duration
    # ==========================================================================
    "rest_whole": {
        "type": "value_match",
        "source": "rests",
        "field": "type",
        "eq": "whole"
    },
    "rest_half": {
        "type": "value_match",
        "source": "rests",
        "field": "type",
        "eq": "half"
    },
    "rest_quarter": {
        "type": "value_match",
        "source": "rests",
        "field": "type",
        "eq": "quarter"
    },
    "rest_eighth": {
        "type": "value_match",
        "source": "rests",
        "field": "type",
        "eq": "eighth"
    },
    "rest_triplet_eighth": {
        "type": "custom",
        "function": "detect_triplet_eighth_rest"
    },
    "rest_sixteenth": {
        "type": "value_match",
        "source": "rests",
        "field": "type",
        "eq": "sixteenth"
    },
    "rest_multimeasure": {
        "type": "custom",
        "function": "detect_multimeasure_rest"
    },
    "rest_tuplet_3_quarter": {
        "type": "custom",
        "function": "detect_tuplet_3_quarter_rest"
    },
    "rest_32nd": {
        "type": "value_match",
        "source": "rests",
        "field": "type",
        "eq": "32nd"
    },
    "rest_64th": {
        "type": "value_match",
        "source": "rests",
        "field": "type",
        "eq": "64th"
    },
    
    # ==========================================================================
    # RHYTHM DURATION - Additional
    # ==========================================================================
    "rhythm_ties_across_beats": {
        "type": "custom",
        "function": "detect_ties"  # Reuse existing
    },
    "rhythm_triplets_eighth": {
        "type": "custom",
        "function": "detect_eighth_triplets"
    },
    "rhythm_tuplet_3_quarters": {
        "type": "custom",
        "function": "detect_quarter_triplets"
    },
    "rhythm_dotted_sixteenth": {
        "type": "compound",
        "source": "notes",
        "conditions": [
            {"field": "type", "eq": "sixteenth"},
            {"field": "dots", "gte": 1}
        ]
    },
    "rhythm_double_dotted_half": {
        "type": "compound",
        "source": "notes",
        "conditions": [
            {"field": "type", "eq": "half"},
            {"field": "dots", "gte": 2}
        ]
    },
    "rhythm_dotted_whole": {
        "type": "compound",
        "source": "notes",
        "conditions": [
            {"field": "type", "eq": "whole"},
            {"field": "dots", "gte": 1}
        ]
    },
    "rhythm_64th_notes": {
        "type": "value_match",
        "source": "notes",
        "field": "type",
        "eq": "64th"
    },
    
    # ==========================================================================
    # TEMPO SKILLS - Direction text
    # ==========================================================================
    "tempo_skill_a_tempo": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "a tempo"
    },
    "tempo_skill_accelerando": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "accel"
    },
    "tempo_skill_rallentando": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "rall"
    },
    "tempo_skill_ritardando": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "rit"
    },
    "tempo_skill_rubato": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "rubato"
    },
    
    # ==========================================================================
    # TEMPO TERMS - Tempo text
    # ==========================================================================
    "tempo_term_adagio": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "adagio"
    },
    "tempo_term_allegretto": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "allegretto"
    },
    "tempo_term_allegro": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "allegro"
    },
    "tempo_term_andante": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "andante"
    },
    "tempo_term_largo": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "largo"
    },
    "tempo_term_moderato": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "moderato"
    },
    "tempo_term_prestissimo": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "prestissimo"
    },
    "tempo_term_presto": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "presto"
    },
    "tempo_term_vivace": {
        "type": "text_match",
        "source": "tempo_markings",
        "contains": "vivace"
    },
    
    # ==========================================================================
    # TEXTURE - Voice count detection
    # ==========================================================================
    "texture_two_voices": {
        "type": "custom",
        "function": "detect_two_voices"
    },
    "texture_three_voices": {
        "type": "custom",
        "function": "detect_three_voices"
    },
    "texture_four_voices": {
        "type": "custom",
        "function": "detect_four_voices"
    },
    
    # ==========================================================================
    # TONAL CONTEXT - Scale fragments
    # ==========================================================================
    "diatonic_scale_fragment_2": {
        "type": "custom",
        "function": "detect_scale_fragment_2"
    },
    "diatonic_scale_fragment_3": {
        "type": "custom",
        "function": "detect_scale_fragment_3"
    },
    "diatonic_scale_fragment_4": {
        "type": "custom",
        "function": "detect_scale_fragment_4"
    },
    "diatonic_scale_fragment_5": {
        "type": "custom",
        "function": "detect_scale_fragment_5"
    },
    "diatonic_scale_fragment_6": {
        "type": "custom",
        "function": "detect_scale_fragment_6"
    },
    "diatonic_scale_fragment_7": {
        "type": "custom",
        "function": "detect_scale_fragment_7"
    },
    "tonal_chromatic_approach_tones": {
        "type": "custom",
        "function": "detect_chromatic_approach_tones"
    },
    "tonal_modulation_awareness": {
        "type": "custom",
        "function": "detect_modulation"
    },
    
    # ==========================================================================
    # TUPLETS
    # ==========================================================================
    "tuplet_duplet": {
        "type": "custom",
        "function": "detect_duplet"
    },
    "tuplet_quintuplet": {
        "type": "custom",
        "function": "detect_quintuplet"
    },
    "tuplet_septuplet": {
        "type": "custom",
        "function": "detect_septuplet"
    },
    "tuplet_sextuplet": {
        "type": "custom",
        "function": "detect_sextuplet"
    },
    "tuplet_triplet_general": {
        "type": "custom",
        "function": "detect_triplet_general"
    },
    "tuplet_triplet_quarter": {
        "type": "custom",
        "function": "detect_quarter_triplets"
    },
}

# Capabilities that are NOT detectable via music21 (theory, behavioral, abstract)
NOT_DETECTABLE = {
    # Theory concepts - user must demonstrate understanding, not read from score
    "clef_movable_c_f_g",
    "circle_of_fifths_fourths",
    "half_steps_theory", 
    "whole_steps_theory",
    "interval_theory_minor_2",
    "interval_theory_major_2",
    "interval_theory_minor_3",
    "interval_theory_major_3",
    "interval_theory_perfect_4",
    "interval_theory_perfect_5",
    "interval_theory_augmented_4",
    "interval_theory_minor_6",
    "interval_theory_major_6",
    "interval_theory_minor_7",
    "interval_theory_major_7",
    "interval_theory_octave",
    "interval_theory_compound_9_plus",
    
    # Notation fundamentals - abstract concepts
    "ledger_lines",  # Could detect but not meaningful standalone
    "note_basics",
    "staff_basics",
    
    # Pitch foundation - behavioral/conceptual
    "first_note",
    "accidental_raise_pitch",
    "accidental_lower_pitch",
    "pitch_direction_awareness",
    
    # Rhythm foundation - behavioral/interactive
    "pulse_tracking",
    "pulse_tracking_accent_shifting",
    "pulse_tracking_call_response",
    "pulse_tracking_clapping",
    "pulse_tracking_drum_loop",
    "pulse_tracking_dynamic_rhythm_control",
    "pulse_tracking_guided_improv",
    "pulse_tracking_metronome_fade",
    "pulse_tracking_multi_layer_contrast",
    "pulse_tracking_polyrhythm_intro",
    "pulse_tracking_rest_based",
    "pulse_tracking_rhythm_ear_training",
    "pulse_tracking_subdividing",
    "pulse_tracking_vocal_counting",
    
    # Scales - require pattern analysis, not single element detection
    "scale_major",
    "scale_natural_minor",
    "mode_dorian",
    "mode_locrian",
    "mode_lydian",
    "mode_mixolydian",
    "mode_phrygian",
    "scale_major_pentatonic",
    "scale_minor_pentatonic",
    "scale_chromatic",
    "scale_harmonic_minor",
    "scale_major_minor",
    "scale_melodic_minor",
    "scale_minor_major",
}

# Apply detection rules to capabilities
added_count = 0
for cap in data['capabilities']:
    name = cap['name']
    if name in DETECTION_RULES and 'music21_detection' not in cap:
        cap['music21_detection'] = DETECTION_RULES[name]
        print(f"Added: {name}")
        added_count += 1

# Save updated capabilities
with open('app/resources/capabilities.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f"\n✓ Added {added_count} detection rules")
print(f"✓ Saved to capabilities.json")

# Summary
total = len(data['capabilities'])
with_det = sum(1 for cap in data['capabilities'] if 'music21_detection' in cap)
not_det_count = len(NOT_DETECTABLE)
print(f"\nSUMMARY:")
print(f"  Total capabilities: {total}")
print(f"  With detection rules: {with_det}")
print(f"  Not detectable (theory/behavioral): {not_det_count}")
print(f"  Remaining without rules: {total - with_det - not_det_count}")
