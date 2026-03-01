"""
Comprehensive Capability Seed Data for Sound First

This file seeds the capabilities_v2 table with all known musical capabilities.
Run after applying the capability_v2 migration.

Usage:
    cd sound-first-service
    py -m app.seed_capabilities_v2
"""

from app.db import get_db, engine
from app.models import Base
from app.models.capability_schema import CapabilityV2
from sqlalchemy.orm import Session

# =============================================================================
# CAPABILITY DEFINITIONS
# =============================================================================
# Format: (name, display_name, domain, subdomain, requirement_type, difficulty_tier, sequence_order, explanation)
# OR extended: (name, display_name, domain, subdomain, requirement_type, difficulty_tier, sequence_order, explanation, mastery_type, mastery_count)
#
# mastery_type values (defaults applied in seed_capabilities if not specified):
#   - 'single': One material/exercise is enough (e.g., learning fermata symbol)
#   - 'any_of_pool': Demonstrate success on any one from a pool (random pick)
#   - 'multiple': Must succeed on N materials (e.g., sixteenth notes in multiple contexts)
#
# NOTE: Melodic intervals use max_melodic_interval on User, not individual capabilities for filtering.
# Interval capabilities here are for teaching content/reference only.

CAPABILITIES = [
    # =========================================================================
    # CLEFS (bit_index 0-9)
    # =========================================================================
    ("clef_treble", "Treble Clef (G Clef)", "clef", None, "required", 1, 1,
     "The treble clef indicates that the second line from the bottom is G above middle C. Most common clef for higher-pitched instruments and the right hand of piano."),
    ("clef_bass", "Bass Clef (F Clef)", "clef", None, "required", 1, 2,
     "The bass clef indicates that the fourth line from the bottom is F below middle C. Used for lower-pitched instruments and the left hand of piano."),
    ("clef_alto", "Alto Clef (C Clef)", "clef", None, "required", 2, 50,
     "The alto clef places middle C on the third line. Primarily used by viola."),
    ("clef_tenor", "Tenor Clef (C Clef)", "clef", None, "required", 2, 51,
     "The tenor clef places middle C on the fourth line. Used by cello, trombone, and bassoon in higher registers."),
    ("clef_treble_8vb", "Treble Clef 8vb", "clef", None, "required", 2, 52,
     "Treble clef sounding an octave lower than written. Common for tenor voice and guitar."),
    ("clef_bass_8va", "Bass Clef 8va", "clef", None, "required", 3, 53,
     "Bass clef sounding an octave higher than written. Rare."),
    
    # =========================================================================
    # TIME SIGNATURES (bit_index 10-39)
    # =========================================================================
    ("time_sig_4_4", "4/4 Time (Common Time)", "time_signature", "simple", "required", 1, 5,
     "Four quarter-note beats per measure. The most common time signature in Western music."),
    ("time_sig_3_4", "3/4 Time (Waltz Time)", "time_signature", "simple", "required", 1, 6,
     "Three quarter-note beats per measure. Associated with waltzes and minuets."),
    ("time_sig_2_4", "2/4 Time", "time_signature", "simple", "required", 1, 7,
     "Two quarter-note beats per measure. Common in marches and polkas."),
    ("time_sig_2_2", "2/2 Time (Cut Time)", "time_signature", "simple", "required", 1, 20,
     "Two half-note beats per measure. Feels faster than 4/4 at the same tempo marking."),
    ("time_sig_6_8", "6/8 Time", "time_signature", "compound", "required", 2, 30,
     "Six eighth-note beats grouped in two, giving a lilting duple feel."),
    ("time_sig_9_8", "9/8 Time", "time_signature", "compound", "required", 2, 31,
     "Nine eighth-note beats grouped in three."),
    ("time_sig_12_8", "12/8 Time", "time_signature", "compound", "required", 2, 32,
     "Twelve eighth-note beats grouped in four. Common in blues and ballads."),
    ("time_sig_3_8", "3/8 Time", "time_signature", "simple", "required", 2, 33,
     "Three eighth-note beats per measure."),
    ("time_sig_5_4", "5/4 Time", "time_signature", "irregular", "required", 3, 60,
     "Five quarter-note beats per measure. Requires thinking in 3+2 or 2+3."),
    ("time_sig_7_8", "7/8 Time", "time_signature", "irregular", "required", 3, 61,
     "Seven eighth-note beats per measure. Common groupings: 2+2+3, 3+2+2."),
    ("time_sig_5_8", "5/8 Time", "time_signature", "irregular", "required", 3, 62,
     "Five eighth-note beats per measure."),
    
    # =========================================================================
    # KEY SIGNATURES - MAJOR (bit_index 40-55)
    # =========================================================================
    ("key_c_major", "C Major / A minor", "key_signature", "major", "required", 1, 3,
     "No sharps or flats. The 'white key' scale on piano."),
    ("key_g_major", "G Major / E minor", "key_signature", "major", "required", 1, 4,
     "One sharp (F#). Very common key for violin and guitar."),
    ("key_d_major", "D Major / B minor", "key_signature", "major", "required", 1, 8,
     "Two sharps (F#, C#). Bright, cheerful key."),
    ("key_f_major", "F Major / D minor", "key_signature", "major", "required", 1, 9,
     "One flat (Bb). Common for wind instruments."),
    ("key_bb_major", "Bb Major / G minor", "key_signature", "major", "required", 1, 10,
     "Two flats (Bb, Eb). Standard key for many brass instruments."),
    ("key_eb_major", "Eb Major / C minor", "key_signature", "major", "required", 2, 25,
     "Three flats (Bb, Eb, Ab). Common in jazz and brass band music."),
    ("key_a_major", "A Major / F# minor", "key_signature", "major", "required", 2, 26,
     "Three sharps (F#, C#, G#). Bright key, favored for violin."),
    ("key_ab_major", "Ab Major / F minor", "key_signature", "major", "required", 2, 35,
     "Four flats. Rich, warm sound."),
    ("key_e_major", "E Major / C# minor", "key_signature", "major", "required", 2, 36,
     "Four sharps. Popular for guitar."),
    ("key_db_major", "Db Major / Bb minor", "key_signature", "major", "required", 3, 70,
     "Five flats. Warm, dark quality."),
    ("key_b_major", "B Major / G# minor", "key_signature", "major", "required", 3, 71,
     "Five sharps. Brilliant but challenging."),
    ("key_gb_major", "Gb Major / Eb minor", "key_signature", "major", "required", 3, 72,
     "Six flats."),
    ("key_f_sharp_major", "F# Major / D# minor", "key_signature", "major", "required", 3, 73,
     "Six sharps."),
    
    # =========================================================================
    # NOTE VALUES (bit_index 56-79)
    # =========================================================================
    ("note_whole", "Whole Note", "note_value", None, "required", 1, 10,
     "A note lasting four beats in 4/4 time. An open oval with no stem."),
    ("note_half", "Half Note", "note_value", None, "required", 1, 11,
     "A note lasting two beats in 4/4 time. An open oval with a stem."),
    ("note_quarter", "Quarter Note", "note_value", None, "required", 1, 12,
     "A note lasting one beat in 4/4 time. A filled oval with a stem."),
    ("note_eighth", "Eighth Note", "note_value", None, "required", 1, 13,
     "A note lasting half a beat. Has one flag or beam."),
    ("note_sixteenth", "Sixteenth Note", "note_value", None, "required", 2, 40,
     "A note lasting a quarter of a beat. Has two flags or beams."),
    ("note_thirty_second", "Thirty-Second Note", "note_value", None, "required", 3, 80,
     "A note lasting an eighth of a beat. Has three flags or beams."),
    ("note_sixty_fourth", "Sixty-Fourth Note", "note_value", None, "required", 3, 81,
     "A note lasting a sixteenth of a beat. Has four flags. Very rare."),
    ("note_dotted_whole", "Dotted Whole Note", "note_value", "dotted", "required", 1, 15,
     "A whole note extended by half its value (6 beats in 4/4)."),
    ("note_dotted_half", "Dotted Half Note", "note_value", "dotted", "required", 1, 16,
     "A half note extended by half its value (3 beats in 4/4)."),
    ("note_dotted_quarter", "Dotted Quarter Note", "note_value", "dotted", "required", 1, 17,
     "A quarter note extended by half its value (1.5 beats)."),
    ("note_dotted_eighth", "Dotted Eighth Note", "note_value", "dotted", "required", 2, 41,
     "An eighth note extended by half its value (0.75 beats)."),
    ("note_dotted_sixteenth", "Dotted Sixteenth Note", "note_value", "dotted", "required", 2, 42,
     "A sixteenth note extended by half its value."),
    ("note_double_dotted_half", "Double-Dotted Half Note", "note_value", "double_dotted", "required", 3, 82,
     "A half note extended by 3/4 its value (3.5 beats)."),
    ("notation_ties", "Tied Notes", "note_value", "tie", "required", 1, 18,
     "Two or more notes connected by a curved line, combining their durations."),
    
    # =========================================================================
    # RESTS (bit_index 80-95)
    # =========================================================================
    ("rest_whole", "Whole Rest", "rest", None, "required", 1, 10,
     "A rest lasting four beats. Hangs from the fourth line."),
    ("rest_half", "Half Rest", "rest", None, "required", 1, 11,
     "A rest lasting two beats. Sits on the third line."),
    ("rest_quarter", "Quarter Rest", "rest", None, "required", 1, 12,
     "A rest lasting one beat. Squiggly vertical symbol."),
    ("rest_eighth", "Eighth Rest", "rest", None, "required", 1, 13,
     "A rest lasting half a beat."),
    ("rest_sixteenth", "Sixteenth Rest", "rest", None, "required", 2, 40,
     "A rest lasting a quarter of a beat."),
    ("rest_thirty_second", "Thirty-Second Rest", "rest", None, "required", 3, 80,
     "A rest lasting an eighth of a beat."),
    ("rest_multi_measure", "Multi-Measure Rest", "rest", "multi", "required", 2, 45,
     "A rest spanning multiple measures, with a number indicating how many."),
    
    # =========================================================================
    # TUPLETS (bit_index 96-111)
    # =========================================================================
    ("tuplet_triplet", "Triplet", "tuplet", None, "required", 1, 35,
     "Three notes in the space of two. Creates a 'swing' or lilting feel."),
    ("tuplet_quintuplet", "Quintuplet", "tuplet", None, "required", 3, 85,
     "Five notes in the space of four. Requires precise subdivision."),
    ("tuplet_sextuplet", "Sextuplet", "tuplet", None, "required", 2, 55,
     "Six notes in the space of four. Can feel like two triplets."),
    ("tuplet_septuplet", "Septuplet", "tuplet", None, "required", 3, 86,
     "Seven notes in the space of four or six."),
    ("tuplet_duplet", "Duplet", "tuplet", None, "required", 2, 56,
     "Two notes in the space of three (in compound meter)."),
    
    # =========================================================================
    # MELODIC INTERVALS - ASCENDING (bit_index 112-159)
    # =========================================================================
    ("interval_melodic_m2_ascending", "Minor 2nd Up", "interval_melodic", "ascending", "required", 1, 100,
     "Half step up. Think 'Jaws' theme."),
    ("interval_melodic_M2_ascending", "Major 2nd Up", "interval_melodic", "ascending", "required", 1, 101,
     "Whole step up. 'Do-Re'. Very common."),
    ("interval_melodic_m3_ascending", "Minor 3rd Up", "interval_melodic", "ascending", "required", 1, 102,
     "Three half steps up. 'Greensleeves' opening."),
    ("interval_melodic_M3_ascending", "Major 3rd Up", "interval_melodic", "ascending", "required", 1, 103,
     "Four half steps up. 'Oh When the Saints' opening."),
    ("interval_melodic_P4_ascending", "Perfect 4th Up", "interval_melodic", "ascending", "required", 1, 104,
     "Five half steps up. 'Here Comes the Bride'."),
    ("interval_melodic_A4_ascending", "Tritone Up", "interval_melodic", "ascending", "required", 2, 140,
     "Six half steps up. 'The Simpsons' theme."),
    ("interval_melodic_P5_ascending", "Perfect 5th Up", "interval_melodic", "ascending", "required", 1, 105,
     "Seven half steps up. 'Star Wars' opening."),
    ("interval_melodic_m6_ascending", "Minor 6th Up", "interval_melodic", "ascending", "required", 2, 141,
     "Eight half steps up. 'The Entertainer' opening."),
    ("interval_melodic_M6_ascending", "Major 6th Up", "interval_melodic", "ascending", "required", 2, 142,
     "Nine half steps up. 'NBC' chimes."),
    ("interval_melodic_m7_ascending", "Minor 7th Up", "interval_melodic", "ascending", "required", 2, 143,
     "Ten half steps up. 'Star Trek' theme."),
    ("interval_melodic_M7_ascending", "Major 7th Up", "interval_melodic", "ascending", "required", 3, 180,
     "Eleven half steps up. 'Take On Me' chorus."),
    ("interval_melodic_P8_ascending", "Octave Up", "interval_melodic", "ascending", "required", 1, 106,
     "Twelve half steps up. 'Somewhere Over the Rainbow'."),
    
    # =========================================================================
    # MELODIC INTERVALS - DESCENDING (bit_index 160-207)
    # =========================================================================
    ("interval_melodic_m2_descending", "Minor 2nd Down", "interval_melodic", "descending", "required", 1, 110,
     "Half step down. 'Joy to the World' continues."),
    ("interval_melodic_M2_descending", "Major 2nd Down", "interval_melodic", "descending", "required", 1, 111,
     "Whole step down. 'Re-Do'. Very common."),
    ("interval_melodic_m3_descending", "Minor 3rd Down", "interval_melodic", "descending", "required", 1, 112,
     "Three half steps down. 'Hey Jude' ('Jude')."),
    ("interval_melodic_M3_descending", "Major 3rd Down", "interval_melodic", "descending", "required", 1, 113,
     "Four half steps down. 'Swing Low, Sweet Chariot'."),
    ("interval_melodic_P4_descending", "Perfect 4th Down", "interval_melodic", "descending", "required", 1, 114,
     "Five half steps down. 'Born Free'."),
    ("interval_melodic_A4_descending", "Tritone Down", "interval_melodic", "descending", "required", 2, 150,
     "Six half steps down."),
    ("interval_melodic_P5_descending", "Perfect 5th Down", "interval_melodic", "descending", "required", 1, 115,
     "Seven half steps down. 'Flintstones' theme."),
    ("interval_melodic_m6_descending", "Minor 6th Down", "interval_melodic", "descending", "required", 2, 151,
     "Eight half steps down."),
    ("interval_melodic_M6_descending", "Major 6th Down", "interval_melodic", "descending", "required", 2, 152,
     "Nine half steps down. 'Nobody Knows the Trouble'."),
    ("interval_melodic_m7_descending", "Minor 7th Down", "interval_melodic", "descending", "required", 2, 153,
     "Ten half steps down."),
    ("interval_melodic_M7_descending", "Major 7th Down", "interval_melodic", "descending", "required", 3, 181,
     "Eleven half steps down."),
    ("interval_melodic_P8_descending", "Octave Down", "interval_melodic", "descending", "required", 1, 116,
     "Twelve half steps down."),
    
    # =========================================================================
    # HARMONIC INTERVALS (bit_index 208-223)
    # =========================================================================
    ("interval_harmonic_m2", "Harmonic Minor 2nd", "interval_harmonic", None, "required", 2, 160,
     "Two notes a half step apart played simultaneously. Dissonant."),
    ("interval_harmonic_M2", "Harmonic Major 2nd", "interval_harmonic", None, "required", 2, 161,
     "Two notes a whole step apart played simultaneously."),
    ("interval_harmonic_m3", "Harmonic Minor 3rd", "interval_harmonic", None, "required", 1, 120,
     "Minor third harmony. Sad or dark quality."),
    ("interval_harmonic_M3", "Harmonic Major 3rd", "interval_harmonic", None, "required", 1, 121,
     "Major third harmony. Bright, happy quality."),
    ("interval_harmonic_P4", "Harmonic Perfect 4th", "interval_harmonic", None, "required", 1, 122,
     "Fourth harmony. Open, suspended sound."),
    ("interval_harmonic_P5", "Harmonic Perfect 5th", "interval_harmonic", None, "required", 1, 123,
     "Fifth harmony. Very open, resonant sound."),
    ("interval_harmonic_m6", "Harmonic Minor 6th", "interval_harmonic", None, "required", 2, 162,
     "Minor sixth harmony."),
    ("interval_harmonic_M6", "Harmonic Major 6th", "interval_harmonic", None, "required", 2, 163,
     "Major sixth harmony."),
    ("interval_harmonic_P8", "Harmonic Octave", "interval_harmonic", None, "required", 1, 124,
     "Octave played as harmony. Reinforcing, 'same' sound."),
    
    # =========================================================================
    # DYNAMICS (bit_index 224-255)
    # =========================================================================
    ("dynamic_pp", "Pianissimo (pp)", "dynamic", "level", "learnable_in_context", 1, 200,
     "Very soft. Play as quietly as possible while maintaining tone quality."),
    ("dynamic_p", "Piano (p)", "dynamic", "level", "learnable_in_context", 1, 201,
     "Soft. Gentle, quiet playing."),
    ("dynamic_mp", "Mezzo-piano (mp)", "dynamic", "level", "learnable_in_context", 1, 202,
     "Moderately soft. Between piano and mezzo-forte."),
    ("dynamic_mf", "Mezzo-forte (mf)", "dynamic", "level", "learnable_in_context", 1, 203,
     "Moderately loud. The 'default' volume for most music."),
    ("dynamic_f", "Forte (f)", "dynamic", "level", "learnable_in_context", 1, 204,
     "Loud. Strong, full sound."),
    ("dynamic_ff", "Fortissimo (ff)", "dynamic", "level", "learnable_in_context", 1, 205,
     "Very loud. As loud as possible while maintaining control."),
    ("dynamic_ppp", "Pianississimo (ppp)", "dynamic", "level", "learnable_in_context", 2, 250,
     "Extremely soft. Barely audible."),
    ("dynamic_fff", "Fortississimo (fff)", "dynamic", "level", "learnable_in_context", 2, 251,
     "Extremely loud. Maximum volume."),
    ("dynamic_sf", "Sforzando (sf)", "dynamic", "accent", "learnable_in_context", 2, 252,
     "Sudden strong accent."),
    ("dynamic_sfz", "Sforzato (sfz)", "dynamic", "accent", "learnable_in_context", 2, 253,
     "Sudden loud accent, more emphatic than sf."),
    ("dynamic_sfp", "Sforzando-piano (sfp)", "dynamic", "accent", "learnable_in_context", 2, 254,
     "Strong accent immediately followed by soft."),
    ("dynamic_fp", "Forte-piano (fp)", "dynamic", "accent", "learnable_in_context", 2, 255,
     "Start loud, immediately become soft."),
    ("dynamic_rf", "Rinforzando (rf)", "dynamic", "accent", "learnable_in_context", 2, 256,
     "Reinforced, sudden emphasis."),
    ("dynamic_rfz", "Rinforzato (rfz)", "dynamic", "accent", "learnable_in_context", 2, 257,
     "More emphatic reinforcement."),
    
    # =========================================================================
    # DYNAMIC CHANGES (bit_index 256-271)
    # =========================================================================
    ("dynamic_change_crescendo", "Crescendo", "dynamic_change", None, "learnable_in_context", 1, 210,
     "Gradually getting louder. Often shown as a 'hairpin' opening to the right."),
    ("dynamic_change_diminuendo", "Diminuendo / Decrescendo", "dynamic_change", None, "learnable_in_context", 1, 211,
     "Gradually getting softer. Hairpin closing to the right."),
    ("dynamic_change_subito", "Subito (sudden)", "dynamic_change", None, "learnable_in_context", 2, 260,
     "Sudden dynamic change, without gradual transition."),
    
    # =========================================================================
    # ARTICULATIONS (bit_index 272-303)
    # =========================================================================
    ("articulation_staccato", "Staccato", "articulation", "shortening", "required", 1, 220,
     "Short, detached notes. Play for about half the written value."),
    ("articulation_staccatissimo", "Staccatissimo", "articulation", "shortening", "required", 2, 270,
     "Very short, extremely detached notes."),
    ("articulation_legato", "Legato", "articulation", "connecting", "required", 1, 221,
     "Smooth, connected notes with no space between them."),
    ("articulation_accent", "Accent (>)", "articulation", "emphasis", "required", 1, 222,
     "Emphasized note, played louder than surrounding notes."),
    ("articulation_marcato", "Marcato (^)", "articulation", "emphasis", "required", 2, 271,
     "Strongly accented, more emphatic than regular accent."),
    ("articulation_tenuto", "Tenuto (-)", "articulation", "sustaining", "required", 1, 223,
     "Held for full value, slight emphasis. 'Leaning' on the note."),
    ("articulation_portato", "Portato", "articulation", "connecting", "required", 2, 272,
     "Between legato and staccato. Slightly detached but smooth."),
    
    # =========================================================================
    # ORNAMENTS (bit_index 304-335)
    # =========================================================================
    ("ornament_trill", "Trill", "ornament", None, "required", 2, 280,
     "Rapid alternation between the written note and the note above."),
    ("ornament_mordent", "Mordent", "ornament", None, "required", 2, 281,
     "Quick alternation: main note → lower note → main note."),
    ("ornament_inverted_mordent", "Inverted Mordent (Prall)", "ornament", None, "required", 2, 282,
     "Quick alternation: main note → upper note → main note."),
    ("ornament_turn", "Turn", "ornament", None, "required", 2, 283,
     "Four-note figure: upper → main → lower → main."),
    ("ornament_inverted_turn", "Inverted Turn", "ornament", None, "required", 3, 320,
     "Four-note figure starting from below."),
    ("ornament_grace_note", "Grace Note (Appoggiatura/Acciaccatura)", "ornament", None, "required", 2, 284,
     "Small note played quickly before the main note."),
    ("ornament_tremolo", "Tremolo", "ornament", None, "required", 2, 285,
     "Rapid repetition of a single note or alternation between two notes."),
    ("ornament_glissando", "Glissando", "ornament", None, "required", 2, 286,
     "Sliding between notes through all pitches in between."),
    
    # =========================================================================
    # TEMPO TERMS (bit_index 336-383)
    # =========================================================================
    ("tempo_largo", "Largo", "tempo_term", "slow", "learnable_in_context", 1, 290,
     "Very slow and broad. 40-60 BPM."),
    ("tempo_lento", "Lento", "tempo_term", "slow", "learnable_in_context", 1, 291,
     "Slow. 45-60 BPM."),
    ("tempo_adagio", "Adagio", "tempo_term", "slow", "learnable_in_context", 1, 292,
     "Slowly, with great expression. 66-76 BPM."),
    ("tempo_andante", "Andante", "tempo_term", "moderate", "learnable_in_context", 1, 293,
     "Walking pace. 76-108 BPM."),
    ("tempo_andantino", "Andantino", "tempo_term", "moderate", "learnable_in_context", 1, 294,
     "Slightly faster than andante."),
    ("tempo_moderato", "Moderato", "tempo_term", "moderate", "learnable_in_context", 1, 295,
     "Moderate speed. 108-120 BPM."),
    ("tempo_allegretto", "Allegretto", "tempo_term", "fast", "learnable_in_context", 1, 296,
     "Moderately fast, but lighter than allegro. 112-120 BPM."),
    ("tempo_allegro", "Allegro", "tempo_term", "fast", "learnable_in_context", 1, 297,
     "Fast, bright, lively. 120-156 BPM."),
    ("tempo_vivace", "Vivace", "tempo_term", "fast", "learnable_in_context", 2, 330,
     "Lively and fast. 156-176 BPM."),
    ("tempo_presto", "Presto", "tempo_term", "very_fast", "learnable_in_context", 2, 331,
     "Very fast. 168-200 BPM."),
    ("tempo_prestissimo", "Prestissimo", "tempo_term", "very_fast", "learnable_in_context", 3, 380,
     "Extremely fast, as fast as possible."),
    ("tempo_accelerando", "Accelerando", "tempo_term", "change", "learnable_in_context", 2, 332,
     "Gradually getting faster."),
    ("tempo_ritardando", "Ritardando (rit.)", "tempo_term", "change", "learnable_in_context", 2, 333,
     "Gradually slowing down."),
    ("tempo_rallentando", "Rallentando (rall.)", "tempo_term", "change", "learnable_in_context", 2, 334,
     "Slowing down, similar to ritardando."),
    ("tempo_a_tempo", "A tempo", "tempo_term", "change", "learnable_in_context", 1, 298,
     "Return to the original tempo."),
    ("tempo_rubato", "Rubato", "tempo_term", "change", "learnable_in_context", 2, 335,
     "Flexible tempo, 'robbing' time from one beat to give to another."),
    
    # =========================================================================
    # EXPRESSION TERMS (bit_index 384-447)
    # =========================================================================
    ("expression_dolce", "Dolce", "expression_term", None, "learnable_in_context", 1, 300,
     "Sweetly, gently."),
    ("expression_cantabile", "Cantabile", "expression_term", None, "learnable_in_context", 1, 301,
     "In a singing style."),
    ("expression_espressivo", "Espressivo", "expression_term", None, "learnable_in_context", 1, 302,
     "Expressively, with feeling."),
    ("expression_con_brio", "Con brio", "expression_term", None, "learnable_in_context", 2, 340,
     "With spirit, vigorously."),
    ("expression_con_fuoco", "Con fuoco", "expression_term", None, "learnable_in_context", 2, 341,
     "With fire, passionately."),
    ("expression_con_moto", "Con moto", "expression_term", None, "learnable_in_context", 2, 342,
     "With movement."),
    ("expression_grazioso", "Grazioso", "expression_term", None, "learnable_in_context", 1, 303,
     "Gracefully."),
    ("expression_leggiero", "Leggiero", "expression_term", None, "learnable_in_context", 2, 343,
     "Lightly, delicately."),
    ("expression_maestoso", "Maestoso", "expression_term", None, "learnable_in_context", 2, 344,
     "Majestically, stately."),
    ("expression_pesante", "Pesante", "expression_term", None, "learnable_in_context", 2, 345,
     "Heavy, weighty."),
    ("expression_sostenuto", "Sostenuto", "expression_term", None, "learnable_in_context", 2, 346,
     "Sustained."),
    ("expression_tranquillo", "Tranquillo", "expression_term", None, "learnable_in_context", 1, 304,
     "Tranquil, calm."),
    ("expression_agitato", "Agitato", "expression_term", None, "learnable_in_context", 2, 347,
     "Agitated, restless."),
    ("expression_animato", "Animato", "expression_term", None, "learnable_in_context", 2, 348,
     "Animated, lively."),
    ("expression_appassionato", "Appassionato", "expression_term", None, "learnable_in_context", 2, 349,
     "Passionately."),
    ("expression_brillante", "Brillante", "expression_term", None, "learnable_in_context", 2, 350,
     "Brilliantly, sparkling."),
    ("expression_morendo", "Morendo", "expression_term", None, "learnable_in_context", 2, 351,
     "Dying away."),
    ("expression_perdendosi", "Perdendosi", "expression_term", None, "learnable_in_context", 2, 352,
     "Fading away, losing itself."),
    
    # =========================================================================
    # REPEAT STRUCTURES (bit_index 448-479)
    # =========================================================================
    ("repeat_sign", "Repeat Sign", "repeat_structure", None, "required", 1, 230,
     "Indicates a section should be played again. Dots before or after double bar."),
    ("repeat_first_ending", "First Ending", "repeat_structure", None, "required", 1, 231,
     "Bracket marked '1.' - play first time through, skip on repeat."),
    ("repeat_second_ending", "Second Ending", "repeat_structure", None, "required", 1, 232,
     "Bracket marked '2.' - skip first time, play on repeat."),
    ("repeat_dc", "D.C. (Da Capo)", "repeat_structure", None, "required", 2, 360,
     "Return to the beginning."),
    ("repeat_ds", "D.S. (Dal Segno)", "repeat_structure", None, "required", 2, 361,
     "Return to the sign (𝄋)."),
    ("repeat_coda", "Coda", "repeat_structure", None, "required", 2, 362,
     "The ending section, jumped to from D.C. or D.S."),
    ("repeat_segno", "Segno", "repeat_structure", None, "required", 2, 363,
     "The sign (𝄋) marking where to return to."),
    ("repeat_fine", "Fine", "repeat_structure", None, "required", 2, 364,
     "The end. Stop here after D.C. or D.S."),
    
    # =========================================================================
    # OTHER NOTATION (bit_index 480-511)
    # =========================================================================
    ("notation_fermata", "Fermata", "notation_symbol", None, "learnable_in_context", 1, 240,
     "Hold the note longer than its written value. 'Bird's eye' symbol."),
    ("notation_breath_mark", "Breath Mark", "notation_symbol", None, "learnable_in_context", 1, 241,
     "Indicates where to breathe. Brief pause."),
    ("notation_chord_symbols", "Chord Symbols", "notation_symbol", "jazz", "required", 2, 370,
     "Letter names with chord quality (Cmaj7, Dm, G7) above the staff."),
    ("notation_figured_bass", "Figured Bass", "notation_symbol", "baroque", "required", 3, 390,
     "Numbers below bass notes indicating harmonies. Baroque practice."),
    ("notation_2_voices", "Two Voices", "notation_symbol", "polyphony", "required", 2, 371,
     "Two independent melodic lines on one staff."),
    ("notation_3_voices", "Three Voices", "notation_symbol", "polyphony", "required", 3, 391,
     "Three independent melodic lines."),
    ("notation_4_voices", "Four Voices", "notation_symbol", "polyphony", "required", 3, 392,
     "Four-part harmony or counterpoint."),
]


def seed_capabilities():
    """Seed all capabilities into the database."""
    db = next(get_db())
    
    try:
        # Clear existing capabilities_v2 (careful in production!)
        db.query(CapabilityV2).delete()
        db.commit()
        
        bit_index = 0
        for cap_tuple in CAPABILITIES:
            # Support both old 8-tuple and new 10-tuple format
            if len(cap_tuple) == 8:
                name, display_name, domain, subdomain, req_type, diff_tier, seq_order, explanation = cap_tuple
                mastery_type = 'single'
                mastery_count = 1
            elif len(cap_tuple) == 10:
                name, display_name, domain, subdomain, req_type, diff_tier, seq_order, explanation, mastery_type, mastery_count = cap_tuple
            else:
                raise ValueError(f"Invalid capability tuple length: {len(cap_tuple)} for {cap_tuple[0]}")
            
            # Default mastery settings by domain if not specified
            if mastery_type == 'single' and domain in ('note_value', 'tuplet', 'articulation', 'ornament'):
                # These require practicing in multiple contexts
                mastery_type = 'multiple'
                mastery_count = 3
            elif mastery_type == 'single' and domain in ('time_signature', 'key_signature'):
                # These can be mastered by playing any piece in that signature
                mastery_type = 'any_of_pool'
            
            cap = CapabilityV2(
                name=name,
                display_name=display_name,
                domain=domain,
                subdomain=subdomain,
                requirement_type=req_type,
                difficulty_tier=diff_tier,
                sequence_order=seq_order,
                explanation=explanation,
                bit_index=bit_index if bit_index < 512 else None,
                mastery_type=mastery_type,
                mastery_count=mastery_count,
            )
            db.add(cap)
            bit_index += 1
        
        db.commit()
        print(f"Seeded {len(CAPABILITIES)} capabilities (bit indices 0-{bit_index-1})")
        
        # Print domain summary
        domains = {}
        for cap_tuple in CAPABILITIES:
            domain = cap_tuple[2]
            domains[domain] = domains.get(domain, 0) + 1
        
        print("\nCapabilities by domain:")
        for domain, count in sorted(domains.items(), key=lambda x: -x[1]):
            print(f"  {domain}: {count}")
            
    except Exception as e:
        db.rollback()
        print(f"Error seeding capabilities: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_capabilities()
