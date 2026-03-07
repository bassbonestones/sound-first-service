# Capability Test Coverage Plan

This document tracks the implementation of test files for all 108 capabilities that have `music21_detection` rules but are not yet tested.

**Current Status:** 124 tests covering 117+ capabilities  
**Target:** 108 additional capabilities to test  
**Total after completion:** ~160+ test files

---

## Stage 1: Time Signatures & Dynamics (18 capabilities) ✅ COMPLETE

**Priority:** High - Core musical elements with straightforward detection

### Time Signatures (6 tests) ✅

| #   | Capability            | Detection Type | Status |
| --- | --------------------- | -------------- | ------ |
| 50  | `time_signature_9_8`  | time_signature | ✅     |
| 51  | `time_signature_12_8` | time_signature | ✅     |
| 52  | `time_signature_3_8`  | time_signature | ✅     |
| 53  | `time_signature_3_2`  | time_signature | ✅     |
| 54  | `time_signature_6_4`  | time_signature | ✅     |
| 55  | `time_signature_5_8`  | time_signature | ✅     |

### Dynamics - Value Match (8 tests) ✅

| #   | Capability    | Detection Type | Status |
| --- | ------------- | -------------- | ------ |
| 56  | `dynamic_ff`  | value_match    | ✅     |
| 57  | `dynamic_pp`  | value_match    | ✅     |
| 58  | `dynamic_mf`  | value_match    | ✅     |
| 59  | `dynamic_mp`  | value_match    | ✅     |
| 60  | `dynamic_fp`  | value_match    | ✅     |
| 61  | `dynamic_rf`  | value_match    | ✅     |
| 62  | `dynamic_rfz` | value_match    | ✅     |
| 63  | `dynamic_sfp` | value_match    | ✅     |

### Dynamics - Element/Text (4 tests) ✅

| #   | Capability            | Detection Type | Status |
| --- | --------------------- | -------------- | ------ |
| 64  | `dynamic_crescendo`   | element        | ✅     |
| 65  | `dynamic_decrescendo` | custom         | ✅     |
| 66  | `dynamic_diminuendo`  | element        | ✅     |
| 67  | `dynamic_subito`      | custom         | ✅     |

---

## Stage 2: Intervals & Range Spans (20 capabilities) ✅ COMPLETE

**Priority:** High - Important for melodic analysis

### Intervals (8 tests) ✅

| #   | Capability                      | Detection Type | Status |
| --- | ------------------------------- | -------------- | ------ |
| 68  | `interval_play_major_2`         | interval       | ✅     |
| 69  | `interval_play_minor_3`         | interval       | ✅     |
| 70  | `interval_play_perfect_4`       | interval       | ✅     |
| 71  | `interval_play_minor_6`         | interval       | ✅     |
| 72  | `interval_play_major_6`         | interval       | ✅     |
| 73  | `interval_play_minor_7`         | interval       | ✅     |
| 74  | `interval_play_major_7`         | interval       | ✅     |
| 75  | `interval_play_compound_9_plus` | custom         | ✅     |

### Range Spans (12 tests) ✅

| #   | Capability                    | Detection Type | Status |
| --- | ----------------------------- | -------------- | ------ |
| 76  | `range_span_minor_second`     | range          | ✅     |
| 77  | `range_span_major_second`     | range          | ✅     |
| 78  | `range_span_minor_third`      | range          | ✅     |
| 79  | `range_span_major_third`      | range          | ✅     |
| 80  | `range_span_perfect_fourth`   | range          | ✅     |
| 81  | `range_span_augmented_fourth` | range          | ✅     |
| 82  | `range_span_perfect_fifth`    | range          | ✅     |
| 83  | `range_span_minor_sixth`      | range          | ✅     |
| 84  | `range_span_major_sixth`      | range          | ✅     |
| 85  | `range_span_minor_seventh`    | range          | ✅     |
| 86  | `range_span_major_seventh`    | range          | ✅     |
| 87  | `range_span_octave`           | range          | ✅     |

---

## Stage 3: Tempo & Expression Terms (28 capabilities) ✅ COMPLETE

**Priority:** High - All text_match, batch-efficient

### Tempo Terms (7 tests) ✅

| #   | Capability               | Detection Type | Status |
| --- | ------------------------ | -------------- | ------ |
| 88  | `tempo_term_adagio`      | text_match     | ✅     |
| 89  | `tempo_term_allegretto`  | text_match     | ✅     |
| 90  | `tempo_term_largo`       | text_match     | ✅     |
| 91  | `tempo_term_moderato`    | text_match     | ✅     |
| 92  | `tempo_term_prestissimo` | text_match     | ✅     |
| 93  | `tempo_term_presto`      | text_match     | ✅     |
| 94  | `tempo_term_vivace`      | text_match     | ✅     |

### Tempo Skills (5 tests) ✅

| #   | Capability                | Detection Type | Status |
| --- | ------------------------- | -------------- | ------ |
| 95  | `tempo_skill_a_tempo`     | text_match     | ✅     |
| 96  | `tempo_skill_accelerando` | text_match     | ✅     |
| 97  | `tempo_skill_rallentando` | text_match     | ✅     |
| 98  | `tempo_skill_ritardando`  | text_match     | ✅     |
| 99  | `tempo_skill_rubato`      | text_match     | ✅     |

### Expression Terms (16 tests) ✅

| #   | Capability                | Detection Type | Status |
| --- | ------------------------- | -------------- | ------ |
| 100 | `expression_agitato`      | text_match     | ✅     |
| 101 | `expression_animato`      | text_match     | ✅     |
| 102 | `expression_appassionato` | text_match     | ✅     |
| 103 | `expression_brillante`    | text_match     | ✅     |
| 104 | `expression_cantabile`    | text_match     | ✅     |
| 105 | `expression_con_brio`     | text_match     | ✅     |
| 106 | `expression_con_fuoco`    | text_match     | ✅     |
| 107 | `expression_con_moto`     | text_match     | ✅     |
| 108 | `expression_grazioso`     | text_match     | ✅     |
| 109 | `expression_leggiero`     | text_match     | ✅     |
| 110 | `expression_maestoso`     | text_match     | ✅     |
| 111 | `expression_morendo`      | text_match     | ✅     |
| 112 | `expression_perdendosi`   | text_match     | ✅     |
| 113 | `expression_pesante`      | text_match     | ✅     |
| 114 | `expression_sostenuto`    | text_match     | ✅     |
| 115 | `expression_tranquillo`   | text_match     | ✅     |

---

## Stage 4: Form Structure (8 capabilities) ✅ COMPLETE

**Priority:** Medium - All custom detectors

| #   | Capability           | Detection Type | Status |
| --- | -------------------- | -------------- | ------ |
| 116 | `form_repeat_sign`   | custom         | ✅     |
| 117 | `form_first_ending`  | custom         | ✅     |
| 118 | `form_second_ending` | custom         | ✅     |
| 119 | `form_dc`            | custom         | ✅     |
| 120 | `form_ds`            | custom         | ✅     |
| 121 | `form_fine`          | custom         | ✅     |
| 122 | `form_coda`          | custom         | ✅     |
| 123 | `form_segno`         | custom         | ✅     |

---

## Stage 5: Tuplets & Rhythm (12 capabilities) ✅ COMPLETE

**Priority:** Medium - Custom detectors for complex rhythms

### Tuplets (6 tests)

| #   | Capability               | Detection Type | Status |
| --- | ------------------------ | -------------- | ------ |
| 124 | `tuplet_duplet`          | custom         | ✅     |
| 125 | `tuplet_triplet_general` | custom         | ✅     |
| 126 | `tuplet_triplet_quarter` | custom         | ✅     |
| 127 | `tuplet_quintuplet`      | custom         | ✅     |
| 128 | `tuplet_sextuplet`       | custom         | ✅     |
| 129 | `tuplet_septuplet`       | custom         | ✅     |

### Advanced Rhythm (6 tests)

| #   | Capability                  | Detection Type | Status |
| --- | --------------------------- | -------------- | ------ |
| 130 | `rhythm_64th_notes`         | value_match    | ✅     |
| 131 | `rhythm_dotted_whole`       | compound       | ✅     |
| 132 | `rhythm_dotted_sixteenth`   | compound       | ✅     |
| 133 | `rhythm_double_dotted_half` | compound       | ✅     |
| 134 | `rhythm_syncopation`        | custom         | ✅     |
| 135 | `rhythm_tuplet_3_quarters`  | custom         | ✅     |

---

## Stage 6: Rests & Articulations (11 capabilities) ✅ COMPLETE

**Priority:** Medium

### Rests (5 tests)

| #   | Capability              | Detection Type | Status |
| --- | ----------------------- | -------------- | ------ |
| 136 | `rest_32nd`             | value_match    | ✅     |
| 137 | `rest_64th`             | value_match    | ✅     |
| 138 | `rest_multimeasure`     | custom         | ✅     |
| 139 | `rest_triplet_eighth`   | custom         | ✅     |
| 140 | `rest_tuplet_3_quarter` | custom         | ✅     |

### Articulations (3 tests)

| #   | Capability                   | Detection Type | Status |
| --- | ---------------------------- | -------------- | ------ |
| 141 | `articulation_legato`        | element        | ✅     |
| 142 | `articulation_portato`       | element        | ✅     |
| 143 | `articulation_staccatissimo` | element        | ✅     |

### Accidentals (3 tests)

| #   | Capability                  | Detection Type | Status |
| --- | --------------------------- | -------------- | ------ |
| 144 | `accidental_natural_symbol` | custom         | ✅     |
| 145 | `double_flat_symbol`        | custom         | ✅     |
| 146 | `double_sharp_symbol`       | custom         | ✅     |

---

## Stage 7: Ornaments, Notation & Misc (13 capabilities) ✅ COMPLETE

**Priority:** Low - Specialized elements

### Ornaments (3 tests)

| #   | Capability                  | Detection Type | Status |
| --- | --------------------------- | -------------- | ------ |
| 147 | `ornament_grace_note`       | custom         | ✅     |
| 148 | `ornament_inverted_mordent` | element        | ✅     |
| 149 | `ornament_tremolo`          | element        | ✅     |

### Notation (3 tests)

| #   | Capability               | Detection Type | Status |
| --- | ------------------------ | -------------- | ------ |
| 150 | `notation_breath_mark`   | custom         | ✅     |
| 151 | `notation_chord_symbols` | custom         | ✅     |
| 152 | `notation_figured_bass`  | custom         | ✅     |

### Clefs (2 tests)

| #   | Capability        | Detection Type | Status |
| --- | ----------------- | -------------- | ------ |
| 153 | `clef_bass_8va`   | custom         | ✅     |
| 154 | `clef_treble_8vb` | custom         | ✅     |

### Texture (3 tests)

| #   | Capability             | Detection Type | Status |
| --- | ---------------------- | -------------- | ------ |
| 155 | `texture_two_voices`   | custom         | ✅     |
| 156 | `texture_three_voices` | custom         | ✅     |
| 157 | `texture_four_voices`  | custom         | ✅     |

### Technique (1 test)

| #   | Capability            | Detection Type | Status |
| --- | --------------------- | -------------- | ------ |
| 158 | `technique_glissando` | element        | ✅     |

### Tonal (1 test)

| #   | Capability                   | Detection Type | Status |
| --- | ---------------------------- | -------------- | ------ |
| 159 | `tonal_modulation_awareness` | custom         | ✅     |

---

## Progress Summary

| Stage     | Description                | Count   | Status             |
| --------- | -------------------------- | ------- | ------------------ |
| 1         | Time Signatures & Dynamics | 18      | ✅ Complete        |
| 2         | Intervals & Range Spans    | 20      | ✅ Complete        |
| 3         | Tempo & Expression Terms   | 28      | ✅ Complete        |
| 4         | Form Structure             | 8       | ✅ Complete        |
| 5         | Tuplets & Rhythm           | 12      | ✅ Complete        |
| 6         | Rests & Articulations      | 11      | ✅ Complete        |
| 7         | Ornaments, Notation & Misc | 13      | ✅ Complete        |
| **Total** |                            | **110** | **110/110 (100%)** |

---

## Implementation Notes

### For each stage:

1. Add test file definitions to `tests/generate_test_files.py`
2. Run `python tests/generate_test_files.py` to regenerate files
3. Add test cases to `tests/test_comprehensive_detection.py`
4. Run `pytest tests/test_comprehensive_detection.py -v` to verify
5. Update this document with ✅ for completed items

### Detection Type Reference:

- **value_match**: Simple property comparison (e.g., dynamic == 'ff')
- **element**: Check for presence of music21 element type
- **text_match**: Search for text in expressions/directions
- **time_signature**: Match beats/beat-type
- **interval**: Check melodic intervals between notes
- **range**: Check overall pitch range of the piece
- **compound**: Multiple conditions combined (AND logic)
- **custom**: Custom detector function in capability_registry.py

---

## Changelog

- **2026-03-07**: Stage 1 complete - 18 tests added (time signatures: 6, dynamics: 12). Fixed detection rules for `dynamic_decrescendo` and `dynamic_subito` to use custom detectors. All 68 tests passing.
- **2026-03-07**: Initial plan created with 108 untested capabilities across 7 stages
