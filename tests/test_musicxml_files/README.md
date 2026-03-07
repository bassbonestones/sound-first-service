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
| 10_time_sig_3_4.musicxml | 3/4 time signature | `time_signature_3_4`, `rhythm_quarter_notes` |
| 11_time_sig_6_8.musicxml | 6/8 time signature | `time_signature_6_8`, `rhythm_eighth_notes` |
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
