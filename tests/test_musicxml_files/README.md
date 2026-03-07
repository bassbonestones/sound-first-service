# Test MusicXML Files Index

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
| 01_whole_notes.musicxml | Whole notes in 4/4 | `rhythm_whole_notes`, `time_signature_4_4`, `clef_treble`, `time_signature_basics`, `key_signature_basics` |
| 02_half_notes.musicxml | Half notes in 4/4 | `rhythm_half_notes`, `time_signature_4_4`, `clef_treble` |
| 03_quarter_notes.musicxml | Quarter notes in 4/4 | `rhythm_quarter_notes`, `time_signature_4_4` |
| 04_eighth_notes.musicxml | Eighth notes in 4/4 | `rhythm_eighth_notes`, `time_signature_4_4`, `diatonic_scale_fragment_3` |
| 05_sixteenth_notes.musicxml | Sixteenth notes in 4/4 | `rhythm_sixteenth_notes`, `time_signature_4_4` |
| 06_32nd_notes.musicxml | 32nd notes | `rhythm_32nd_notes`, `time_signature_4_4` |
| 07_dotted_half.musicxml | Dotted half note | `rhythm_dotted_half`, `rhythm_half_notes`, `time_signature_4_4` |
| 08_dotted_quarter.musicxml | Dotted quarter note | `rhythm_dotted_quarter`, `rhythm_quarter_notes`, `rhythm_eighth_notes` |
| 09_dotted_eighth.musicxml | Dotted eighth note | `rhythm_dotted_eighth`, `rhythm_eighth_notes`, `rhythm_sixteenth_notes` |
| 100_expression_agitato.musicxml | Agitato expression marking | `expression_agitato`, `rhythm_quarter_notes` |
| 101_expression_animato.musicxml | Animato expression marking | `expression_animato`, `rhythm_quarter_notes` |
| 102_expression_appassionato.musicxml | Appassionato expression marking | `expression_appassionato`, `rhythm_quarter_notes` |
| 103_expression_brillante.musicxml | Brillante expression marking | `expression_brillante`, `rhythm_quarter_notes` |
| 104_expression_cantabile.musicxml | Cantabile expression marking | `expression_cantabile`, `rhythm_quarter_notes` |
| 105_expression_con_brio.musicxml | Con brio expression marking | `expression_con_brio`, `rhythm_quarter_notes` |
| 106_expression_con_fuoco.musicxml | Con fuoco expression marking | `expression_con_fuoco`, `rhythm_quarter_notes` |
| 107_expression_con_moto.musicxml | Con moto expression marking | `expression_con_moto`, `rhythm_quarter_notes` |
| 108_expression_grazioso.musicxml | Grazioso expression marking | `expression_grazioso`, `rhythm_quarter_notes` |
| 109_expression_leggiero.musicxml | Leggiero expression marking | `expression_leggiero`, `rhythm_quarter_notes` |
| 10_time_sig_3_4.musicxml | 3/4 time signature | `time_signature_3_4`, `rhythm_quarter_notes` |
| 110_expression_maestoso.musicxml | Maestoso expression marking | `expression_maestoso`, `rhythm_quarter_notes` |
| 111_expression_morendo.musicxml | Morendo expression marking | `expression_morendo`, `rhythm_quarter_notes` |
| 112_expression_perdendosi.musicxml | Perdendosi expression marking | `expression_perdendosi`, `rhythm_quarter_notes` |
| 113_expression_pesante.musicxml | Pesante expression marking | `expression_pesante`, `rhythm_quarter_notes` |
| 114_expression_sostenuto.musicxml | Sostenuto expression marking | `expression_sostenuto`, `rhythm_quarter_notes` |
| 115_expression_tranquillo.musicxml | Tranquillo expression marking | `expression_tranquillo`, `rhythm_quarter_notes` |
| 116_form_repeat_sign.musicxml | Repeat sign (barline) | `form_repeat_sign`, `rhythm_quarter_notes` |
| 117_form_first_ending.musicxml | First ending bracket | `form_first_ending`, `form_repeat_sign`, `rhythm_quarter_notes` |
| 118_form_second_ending.musicxml | Second ending bracket | `form_second_ending`, `form_first_ending`, `form_repeat_sign`, `rhythm_quarter_notes` |
| 119_form_dc.musicxml | Da Capo (D.C.) marking | `form_dc`, `rhythm_quarter_notes` |
| 11_time_sig_6_8.musicxml | 6/8 time signature | `time_signature_6_8`, `rhythm_eighth_notes` |
| 120_form_ds.musicxml | Dal Segno (D.S.) marking | `form_ds`, `rhythm_quarter_notes` |
| 121_form_fine.musicxml | Fine marking | `form_fine`, `rhythm_quarter_notes` |
| 122_form_coda.musicxml | Coda marking | `form_coda`, `rhythm_quarter_notes` |
| 123_form_segno.musicxml | Segno sign | `form_segno`, `rhythm_quarter_notes` |
| 12_time_sig_2_4.musicxml | 2/4 time signature | `time_signature_2_4`, `rhythm_quarter_notes` |
| 13_time_sig_2_2.musicxml | 2/2 (cut time) time signature | `time_signature_2_2`, `rhythm_half_notes` |
| 14_time_sig_7_8.musicxml | 7/8 time signature | `time_signature_7_8`, `rhythm_eighth_notes` |
| 15_time_sig_5_4.musicxml | 5/4 time signature | `time_signature_5_4`, `rhythm_quarter_notes` |
| 16_clef_bass.musicxml | Bass clef | `clef_bass`, `rhythm_whole_notes` |
| 17_clef_alto.musicxml | Alto clef (viola) | `clef_alto`, `rhythm_whole_notes` |
| 18_clef_tenor.musicxml | Tenor clef | `clef_tenor`, `rhythm_whole_notes` |
| 19_dynamics_basic.musicxml | Basic dynamics (f, p, mf, mp) | `dynamic_f`, `dynamic_p`, `rhythm_quarter_notes` |
| 20_dynamics_extremes.musicxml | Extreme dynamics (fff, ppp) | `dynamic_fff`, `dynamic_ppp`, `rhythm_half_notes` |
| 21_dynamics_sfz.musicxml | Sforzando dynamics (sf, sfz) | `dynamic_sf`, `dynamic_sfz`, `rhythm_quarter_notes` |
| 22_articulations_staccato.musicxml | Staccato articulation | `articulation_staccato`, `rhythm_quarter_notes` |
| 23_articulations_accent.musicxml | Accent articulation | `articulation_accent`, `rhythm_quarter_notes` |
| 24_articulations_tenuto.musicxml | Tenuto articulation | `articulation_tenuto`, `rhythm_quarter_notes` |
| 25_articulations_marcato.musicxml | Marcato (strong accent) articulation | `articulation_marcato`, `rhythm_quarter_notes` |
| 26_rests_whole.musicxml | Whole rest | `rest_whole`, `time_signature_4_4` |
| 27_rests_half.musicxml | Half rest | `rest_half`, `rhythm_half_notes` |
| 28_rests_quarter.musicxml | Quarter rest | `rest_quarter`, `rhythm_quarter_notes` |
| 29_rests_eighth.musicxml | Eighth rest | `rest_eighth`, `rhythm_eighth_notes` |
| 30_rests_sixteenth.musicxml | Sixteenth rest | `rest_sixteenth`, `rhythm_sixteenth_notes` |
| 31_interval_minor_2.musicxml | Minor 2nd interval (semitone) | `interval_play_minor_2`, `diatonic_scale_fragment_2`, `tonal_chromatic_approach_tones` |
| 32_interval_major_3.musicxml | Major 3rd interval | `interval_play_major_3`, `rhythm_half_notes` |
| 33_interval_perfect_5.musicxml | Perfect 5th interval | `interval_play_perfect_5`, `rhythm_half_notes` |
| 34_interval_octave.musicxml | Octave interval | `interval_play_octave`, `rhythm_half_notes` |
| 35_interval_augmented_4.musicxml | Augmented 4th (tritone) interval | `interval_play_augmented_4`, `rhythm_half_notes` |
| 36_accidental_sharp.musicxml | Sharp accidental | `accidental_sharp_symbol`, `rhythm_half_notes` |
| 37_accidental_flat.musicxml | Flat accidental | `accidental_flat_symbol`, `rhythm_half_notes` |
| 38_ties.musicxml | Tied notes | `notation_ties`, `rhythm_ties_across_beats`, `rhythm_half_notes` |
| 39_ornament_trill.musicxml | Trill ornament | `ornament_trill`, `rhythm_whole_notes` |
| 40_ornament_mordent.musicxml | Mordent ornament | `ornament_mordent`, `rhythm_whole_notes` |
| 41_ornament_turn.musicxml | Turn ornament | `ornament_turn`, `rhythm_whole_notes` |
| 42_fermata.musicxml | Fermata notation | `notation_fermata`, `rhythm_whole_notes` |
| 43_key_sig_g_major.musicxml | G major key signature (1 sharp) | `key_signature_basics`, `rhythm_whole_notes` |
| 44_key_sig_f_major.musicxml | F major key signature (1 flat) | `key_signature_basics`, `rhythm_whole_notes` |
| 45_tempo_allegro.musicxml | Allegro tempo marking | `tempo_term_allegro`, `rhythm_quarter_notes` |
| 46_tempo_andante.musicxml | Andante tempo marking | `tempo_term_andante`, `rhythm_quarter_notes` |
| 47_expression_dolce.musicxml | Dolce expression | `expression_dolce`, `rhythm_half_notes` |
| 48_expression_espressivo.musicxml | Espressivo expression | `expression_espressivo`, `rhythm_half_notes` |
| 49_scale_ascending.musicxml | Ascending scale (tests scale fragments) | `diatonic_scale_fragment_7`, `diatonic_scale_fragment_6`, `diatonic_scale_fragment_5`, `diatonic_scale_fragment_4`, `diatonic_scale_fragment_3` (+2 more) |
| 50_time_sig_9_8.musicxml | 9/8 time signature (compound triple) | `time_signature_9_8`, `rhythm_eighth_notes` |
| 51_time_sig_12_8.musicxml | 12/8 time signature (compound quadruple) | `time_signature_12_8`, `rhythm_eighth_notes` |
| 52_time_sig_3_8.musicxml | 3/8 time signature | `time_signature_3_8`, `rhythm_eighth_notes` |
| 53_time_sig_3_2.musicxml | 3/2 time signature | `time_signature_3_2`, `rhythm_half_notes` |
| 54_time_sig_6_4.musicxml | 6/4 time signature | `time_signature_6_4`, `rhythm_quarter_notes` |
| 55_time_sig_5_8.musicxml | 5/8 time signature (asymmetric) | `time_signature_5_8`, `rhythm_eighth_notes` |
| 56_dynamic_ff.musicxml | Fortissimo (ff) dynamic | `dynamic_ff`, `rhythm_quarter_notes` |
| 57_dynamic_pp.musicxml | Pianissimo (pp) dynamic | `dynamic_pp`, `rhythm_quarter_notes` |
| 58_dynamic_mf.musicxml | Mezzo forte (mf) dynamic | `dynamic_mf`, `rhythm_quarter_notes` |
| 59_dynamic_mp.musicxml | Mezzo piano (mp) dynamic | `dynamic_mp`, `rhythm_quarter_notes` |
| 60_dynamic_fp.musicxml | Forte-piano (fp) dynamic | `dynamic_fp`, `rhythm_quarter_notes` |
| 61_dynamic_rf.musicxml | Rinforzando (rf) dynamic | `dynamic_rf`, `rhythm_quarter_notes` |
| 62_dynamic_rfz.musicxml | Rinforzando (rfz) dynamic | `dynamic_rfz`, `rhythm_quarter_notes` |
| 63_dynamic_sfp.musicxml | Sforzando-piano (sfp) dynamic | `dynamic_sfp`, `rhythm_quarter_notes` |
| 64_dynamic_crescendo.musicxml | Crescendo (hairpin) | `dynamic_crescendo`, `rhythm_quarter_notes` |
| 65_dynamic_decrescendo.musicxml | Decrescendo (hairpin) | `dynamic_decrescendo`, `rhythm_quarter_notes` |
| 66_dynamic_diminuendo.musicxml | Diminuendo text marking | `dynamic_diminuendo`, `rhythm_half_notes` |
| 67_dynamic_subito.musicxml | Subito dynamic change | `dynamic_subito`, `rhythm_quarter_notes` |
| 68_interval_major_2.musicxml | Major 2nd interval (whole step) | `interval_play_major_2`, `rhythm_half_notes` |
| 69_interval_minor_3.musicxml | Minor 3rd interval | `interval_play_minor_3`, `rhythm_half_notes` |
| 70_interval_perfect_4.musicxml | Perfect 4th interval | `interval_play_perfect_4`, `rhythm_half_notes` |
| 71_interval_minor_6.musicxml | Minor 6th interval | `interval_play_minor_6`, `rhythm_half_notes` |
| 72_interval_major_6.musicxml | Major 6th interval | `interval_play_major_6`, `rhythm_half_notes` |
| 73_interval_minor_7.musicxml | Minor 7th interval | `interval_play_minor_7`, `rhythm_half_notes` |
| 74_interval_major_7.musicxml | Major 7th interval | `interval_play_major_7`, `rhythm_half_notes` |
| 75_interval_compound_9.musicxml | Compound interval (9th or greater) | `interval_play_compound_9_plus`, `rhythm_half_notes` |
| 76_range_minor_second.musicxml | Range span of minor 2nd (1 semitone) | `range_span_minor_second`, `rhythm_quarter_notes` |
| 77_range_major_second.musicxml | Range span of major 2nd (2 semitones) | `range_span_major_second`, `rhythm_quarter_notes` |
| 78_range_minor_third.musicxml | Range span of minor 3rd (3 semitones) | `range_span_minor_third`, `rhythm_quarter_notes` |
| 79_range_major_third.musicxml | Range span of major 3rd (4 semitones) | `range_span_major_third`, `rhythm_quarter_notes` |
| 80_range_perfect_fourth.musicxml | Range span of perfect 4th (5 semitones) | `range_span_perfect_fourth`, `rhythm_quarter_notes` |
| 81_range_augmented_fourth.musicxml | Range span of augmented 4th / tritone (6 semitones) | `range_span_augmented_fourth`, `rhythm_quarter_notes` |
| 82_range_perfect_fifth.musicxml | Range span of perfect 5th (7 semitones) | `range_span_perfect_fifth`, `rhythm_quarter_notes` |
| 83_range_minor_sixth.musicxml | Range span of minor 6th (8 semitones) | `range_span_minor_sixth`, `rhythm_quarter_notes` |
| 84_range_major_sixth.musicxml | Range span of major 6th (9 semitones) | `range_span_major_sixth`, `rhythm_quarter_notes` |
| 85_range_minor_seventh.musicxml | Range span of minor 7th (10 semitones) | `range_span_minor_seventh`, `rhythm_quarter_notes` |
| 86_range_major_seventh.musicxml | Range span of major 7th (11 semitones) | `range_span_major_seventh`, `rhythm_quarter_notes` |
| 87_range_octave.musicxml | Range span of octave (12 semitones) | `range_span_octave`, `rhythm_quarter_notes` |
| 88_tempo_adagio.musicxml | Adagio tempo marking | `tempo_term_adagio`, `rhythm_quarter_notes` |
| 89_tempo_allegretto.musicxml | Allegretto tempo marking | `tempo_term_allegretto`, `rhythm_quarter_notes` |
| 90_tempo_largo.musicxml | Largo tempo marking | `tempo_term_largo`, `rhythm_quarter_notes` |
| 91_tempo_moderato.musicxml | Moderato tempo marking | `tempo_term_moderato`, `rhythm_quarter_notes` |
| 92_tempo_prestissimo.musicxml | Prestissimo tempo marking | `tempo_term_prestissimo`, `rhythm_quarter_notes` |
| 93_tempo_presto.musicxml | Presto tempo marking | `tempo_term_presto`, `rhythm_quarter_notes` |
| 94_tempo_vivace.musicxml | Vivace tempo marking | `tempo_term_vivace`, `rhythm_quarter_notes` |
| 95_tempo_a_tempo.musicxml | A tempo marking | `tempo_skill_a_tempo`, `rhythm_quarter_notes` |
| 96_tempo_accelerando.musicxml | Accelerando marking | `tempo_skill_accelerando`, `rhythm_quarter_notes` |
| 97_tempo_rallentando.musicxml | Rallentando marking | `tempo_skill_rallentando`, `rhythm_quarter_notes` |
| 98_tempo_ritardando.musicxml | Ritardando marking | `tempo_skill_ritardando`, `rhythm_quarter_notes` |
| 99_tempo_rubato.musicxml | Rubato marking | `tempo_skill_rubato`, `rhythm_quarter_notes` |

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
