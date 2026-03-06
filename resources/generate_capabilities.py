import json
from typing import Dict, List, Any, Tuple


def cap(
 name: str,
 display_name: str,
 domain: str,
 *,
 subdomain: str = None,
 prerequisite_names: List[str] = None,
 requirement_type: str = "required",
 difficulty_tier: int = 1,
 sequence_order: int = None,
 evidence_required_count: int = 1,
 evidence_distinct_materials: bool = False,
 evidence_acceptance_threshold: int = 4,
 evidence_qualifier_json: Dict[str, Any] = None,
 difficulty_weight: float = 1.0,
) -> Dict[str, Any]:
 return {
  "name": name,
  "display_name": display_name,
  "domain": domain,
  "subdomain": subdomain,
  "requirement_type": requirement_type,
  "prerequisite_names": prerequisite_names or [],
  "sequence_order": sequence_order,  # may be overwritten later
  "difficulty_tier": difficulty_tier,
  "mastery_type": "single",
  "mastery_count": 1,
  "evidence_required_count": evidence_required_count,
  "evidence_distinct_materials": evidence_distinct_materials,
  "evidence_acceptance_threshold": evidence_acceptance_threshold,
  "evidence_qualifier_json": evidence_qualifier_json or {},
  "difficulty_weight": difficulty_weight,
 }


def ordered_caps(domain: str, items: List[Tuple[str, str]], prereq_chain: bool = True, prereq_base: List[str] = None) -> List[Dict[str, Any]]:
 """
 items: [(name, display_name), ...] in unlock order
 prereq_chain: each requires previous
 prereq_base: additional prerequisites for all
 """
 out: List[Dict[str, Any]] = []
 prev = None
 for (n, d) in items:
  prereqs = list(prereq_base or [])
  if prereq_chain and prev:
   prereqs.append(prev)
  out.append(cap(n, d, domain, prerequisite_names=prereqs))
  prev = n
 return out


def main() -> None:
 caps: List[Dict[str, Any]] = []

 # -----------------------------
 # Fundamentals (Notation Primitives)
 # -----------------------------
 caps += [
  cap("staff_basics", "Staff Basics", "notation_fundamentals"),
  cap("ledger_lines", "Ledger Lines", "notation_fundamentals", prerequisite_names=["staff_basics"]),
  cap("note_basics", "Note Basics", "notation_fundamentals", prerequisite_names=["staff_basics"]),
  cap("first_note", "First Note", "pitch_foundation", prerequisite_names=["note_basics"]),
 ]

 # -----------------------------
 # Accidentals (Accidental System)
 # -----------------------------
 caps += [
  cap("accidental_sharp_symbol", "Sharp Symbol (♯)", "accidental_system", prerequisite_names=["note_basics"]),
  cap("accidental_flat_symbol", "Flat Symbol (♭)", "accidental_system", prerequisite_names=["note_basics"]),
  cap("accidental_natural_symbol", "Natural Symbol (♮)", "accidental_system", prerequisite_names=["note_basics"]),
 ]

 # -----------------------------
 # Clefs
 # Note: instrument main clef is handled as instrument-specific at runtime,
 # but we still represent it as a capability so you can gate or teach it.
 # -----------------------------
 caps += [
  cap("clef_instrument_main", "Instrument Main Clef", "clef_system", prerequisite_names=["staff_basics"]),
  cap("clef_bass", "Bass Clef", "clef_system", prerequisite_names=["staff_basics"]),
  cap("clef_treble", "Treble Clef", "clef_system", prerequisite_names=["staff_basics"]),
  cap("clef_tenor", "Tenor Clef", "clef_system", prerequisite_names=["clef_bass"]),
  cap("clef_alto", "Alto Clef", "clef_system", prerequisite_names=["clef_treble"]),
  cap("clef_treble_8vb", "Treble Clef (8vb)", "clef_system", prerequisite_names=["clef_treble"]),
  cap("clef_bass_8va", "Bass Clef (8va)", "clef_system", prerequisite_names=["clef_bass"]),
  cap("clef_movable_c_f_g", "Movable C, F, and G Clefs", "clef_system", prerequisite_names=["clef_alto", "clef_tenor"]),
 ]

 # -----------------------------
 # Meter / Time Signatures
 # Your rule: Time Signature Basics introduced before Half Notes
 # We model "time_signature_basics" + specific signatures.
 # -----------------------------
 caps += [
  cap("time_signature_basics", "Time Signature Basics", "meter", prerequisite_names=["staff_basics"]),
 ]

 time_sigs = [
  ("time_signature_4_4", "Time Signature: 4/4"),
  ("time_signature_3_4", "Time Signature: 3/4"),
  ("time_signature_2_4", "Time Signature: 2/4"),
  ("time_signature_6_8", "Time Signature: 6/8 (Compound Meter)",),
  ("time_signature_2_2", "Time Signature: 2/2 (Cut Time)"),
  ("time_signature_9_8", "Time Signature: 9/8"),
  ("time_signature_12_8", "Time Signature: 12/8"),
  ("time_signature_3_8", "Time Signature: 3/8"),
  ("time_signature_5_4", "Time Signature: 5/4"),
  ("time_signature_7_8", "Time Signature: 7/8"),
  ("time_signature_5_8", "Time Signature: 5/8"),
  ("time_signature_3_2", "Time Signature: 3/2"),
  ("time_signature_6_4", "Time Signature: 6/4"),
  ("time_signature_3_16", "Time Signature: 3/16"),
 ]
 # keep 4/4 earliest, then the rest
 for (n, d) in time_sigs:
  prereqs = ["time_signature_basics"]
  if n != "time_signature_4_4":
   prereqs.append("time_signature_4_4")
  caps.append(cap(n, d, "meter", prerequisite_names=prereqs))

 # -----------------------------
 # Rhythm: Pulse Tracking (a cluster) + duration ladder
 # -----------------------------
 caps += [
  cap("pulse_tracking", "Pulse Tracking", "rhythm_foundation", prerequisite_names=["time_signature_basics"]),
  cap("pulse_tracking_clapping", "Pulse Tracking: Clapping", "rhythm_foundation", prerequisite_names=["pulse_tracking"]),
  cap("pulse_tracking_metronome_fade", "Pulse Tracking: Metronome Fade Out / In", "rhythm_foundation", prerequisite_names=["pulse_tracking"]),
  cap("pulse_tracking_vocal_counting", "Pulse Tracking: Vocal Counting", "rhythm_foundation", prerequisite_names=["pulse_tracking"]),
  cap("pulse_tracking_subdividing", "Pulse Tracking: Subdividing Beats", "rhythm_foundation", prerequisite_names=["pulse_tracking"]),
  cap("pulse_tracking_drum_loop", "Pulse Tracking: Drum Loop", "rhythm_foundation", prerequisite_names=["pulse_tracking"]),
  cap("pulse_tracking_call_response", "Pulse Tracking: Call and Response", "rhythm_foundation", prerequisite_names=["pulse_tracking"]),
  cap("pulse_tracking_guided_improv", "Pulse Tracking: Guided Improvisation", "rhythm_foundation", prerequisite_names=["pulse_tracking"]),
  cap("pulse_tracking_polyrhythm_intro", "Pulse Tracking: Polyrhythm Introduction", "rhythm_foundation", prerequisite_names=["pulse_tracking_subdividing"], difficulty_tier=2),
  cap("pulse_tracking_accent_shifting", "Pulse Tracking: Accent Shifting", "rhythm_foundation", prerequisite_names=["pulse_tracking_drum_loop"], difficulty_tier=2),
  cap("pulse_tracking_rhythm_ear_training", "Pulse Tracking: Rhythm Ear Training", "rhythm_foundation", prerequisite_names=["pulse_tracking_call_response"]),
  cap("pulse_tracking_dynamic_rhythm_control", "Pulse Tracking: Dynamic Rhythm Control", "rhythm_foundation", prerequisite_names=["pulse_tracking"]),
  cap("pulse_tracking_rest_based", "Pulse Tracking: Rest-Based Rhythms", "rhythm_foundation", prerequisite_names=["pulse_tracking"]),
  cap("pulse_tracking_multi_layer_contrast", "Pulse Tracking: Multi-Layer Contrast", "rhythm_foundation", prerequisite_names=["pulse_tracking_polyrhythm_intro"], difficulty_tier=3),
 ]

 # Duration ladder (your order; each requires the previous)
 caps += ordered_caps(
  "rhythm_duration",
  [
   ("rhythm_whole_notes", "Whole Notes"),
   ("rhythm_half_notes", "Half Notes"),
   ("rhythm_quarter_notes", "Quarter Notes"),
   ("rhythm_eighth_notes", "Eighth Notes"),
   ("rhythm_dotted_half", "Dotted Half Note"),
   ("rhythm_dotted_quarter", "Dotted Quarter Note"),
   ("rhythm_ties_across_beats", "Ties Across Beats"),
   ("rhythm_triplets_eighth", "Triplet (Eighth-Note Triplet)"),
   ("rhythm_sixteenth_notes", "Sixteenth Notes"),
   ("rhythm_syncopation", "Syncopation"),
   ("rhythm_dotted_eighth", "Dotted Eighth Note"),
   ("rhythm_tuplet_3_quarters", "Tuplet: 3 Quarter Notes"),
   ("rhythm_32nd_notes", "Thirty-Second Notes"),
   ("rhythm_dotted_sixteenth", "Dotted Sixteenth Note"),
   ("rhythm_double_dotted_half", "Double-Dotted Half Note"),
   ("rhythm_dotted_whole", "Dotted Whole Note"),
   ("rhythm_64th_notes", "Sixty-Fourth Notes and Beyond"),
  ],
  prereq_chain=True,
  prereq_base=["pulse_tracking", "time_signature_4_4"]
 )

 # A couple special prerequisites you asked for
 # (We keep them here as additional AND requirements)
 # Dotted whole often needs 3/2 or 6/4 awareness
 for c in caps:
  if c["name"] == "rhythm_dotted_whole":
   c["prerequisite_names"] += ["time_signature_3_2", "time_signature_6_4"]

 # -----------------------------
 # Rests ladder (mirrors rhythm ladder)
 # -----------------------------
 caps += [
  cap("rest_whole", "Whole Rest", "rests", prerequisite_names=["rhythm_whole_notes"]),
  cap("rest_half", "Half Rest", "rests", prerequisite_names=["rest_whole", "rhythm_half_notes"]),
  cap("rest_quarter", "Quarter Rest", "rests", prerequisite_names=["rest_half", "rhythm_quarter_notes"]),
  cap("rest_eighth", "Eighth Rest", "rests", prerequisite_names=["rest_quarter", "rhythm_eighth_notes"]),
  cap("rest_triplet_eighth", "Triplet Eighth Rest", "rests", prerequisite_names=["rest_eighth", "rhythm_triplets_eighth"]),
  cap("rest_sixteenth", "Sixteenth Rest", "rests", prerequisite_names=["rest_triplet_eighth", "rhythm_sixteenth_notes"]),
  cap("rest_multimeasure", "Multi-Measure Rest", "rests", prerequisite_names=["rest_sixteenth"]),
  cap("rest_tuplet_3_quarter", "Tuplet: 3 Quarter Rests", "rests", prerequisite_names=["rest_multimeasure", "rhythm_tuplet_3_quarters"]),
  cap("rest_32nd", "Thirty-Second Rest", "rests", prerequisite_names=["rest_tuplet_3_quarter", "rhythm_32nd_notes"]),
  cap("rest_64th", "Sixty-Fourth Rest and Beyond", "rests", prerequisite_names=["rest_32nd", "rhythm_64th_notes"]),
 ]

 # -----------------------------
 # Intervals (your unlock chain; taught both directions)
 # We store generic interval classes as capabilities; direction is a material property or subdomain later.
 # -----------------------------
 interval_chain = [
  ("interval_m2", "Minor Second (m2)"),
  ("interval_M2", "Major Second (M2)"),
  ("interval_m3", "Minor Third (m3)"),
  ("interval_M3", "Major Third (M3)"),
  ("interval_P4", "Perfect Fourth (P4)"),
  ("interval_P5", "Perfect Fifth (P5)"),
  ("interval_A4", "Augmented Fourth (A4)"),
  ("interval_m6", "Minor Sixth (m6)"),
  ("interval_M6", "Major Sixth (M6)"),
  ("interval_m7", "Minor Seventh (m7)"),
  ("interval_M7", "Major Seventh (M7)"),
  ("interval_octave", "Octave (P8)"),
  ("interval_compound_9_plus", "Compound Intervals (9+)"),
 ]
 caps += ordered_caps("intervals", interval_chain, prereq_chain=True, prereq_base=["first_note"])

 # Your additional requirements:
 # - A4 after P5 already satisfied by chain
 # - M6 requires pentachord awareness + P5 mastered
 # - M7 requires scale fragment
 # - Octave requires scale fragment
 # We'll define tonal context later and patch prerequisites after.
 # For now add placeholder prerequisite names that will exist.
 for c in caps:
  if c["name"] == "interval_M6":
   c["prerequisite_names"] += ["tonal_pentachord_awareness", "interval_P5"]
  if c["name"] == "interval_M7":
   c["prerequisite_names"] += ["tonal_diatonic_scale_fragment"]
  if c["name"] == "interval_octave":
   c["prerequisite_names"] += ["tonal_diatonic_scale_fragment"]

 # -----------------------------
 # Tonal Context ladder (ear-first)
 # -----------------------------
 caps += [
  cap("tonal_single_pitch_center", "Single Pitch Center", "tonal_context", prerequisite_names=["first_note"]),
  cap("tonal_diatonic_neighbor_motion", "Diatonic Neighbor Motion", "tonal_context",
   prerequisite_names=["tonal_single_pitch_center", "interval_M2"]),
  cap("tonal_diatonic_scale_fragment", "Diatonic Scale Fragment", "tonal_context",
   prerequisite_names=["tonal_diatonic_neighbor_motion", "interval_M2", "interval_m2"]),
  cap("tonal_pentachord_awareness", "Pentachord Awareness (Do–Re–Mi–Fa–Sol)", "tonal_context",
   prerequisite_names=["tonal_diatonic_scale_fragment"]),
  cap("tonal_chromatic_approach_tones", "Chromatic Approach Tones", "tonal_context",
   prerequisite_names=["tonal_pentachord_awareness"]),
  cap("tonal_modulation_awareness", "Modulation Awareness", "tonal_context",
   prerequisite_names=["tonal_chromatic_approach_tones"], difficulty_tier=3),
 ]

 # -----------------------------
 # Key system
 # You want Key Signature after Pentachord Awareness
 # -----------------------------
 caps += [
  cap("key_signature_basics", "Key Signature Basics", "key_system", prerequisite_names=["tonal_pentachord_awareness"]),
  cap("circle_of_fifths_fourths", "Circle of Fifths / Fourths", "key_system", prerequisite_names=["key_signature_basics"], difficulty_tier=2),
  cap("whole_steps_theory", "Whole Steps Theory", "key_system", prerequisite_names=["key_signature_basics"]),
  cap("half_steps_theory", "Half Steps Theory", "key_system", prerequisite_names=["key_signature_basics"]),
 ]

 # -----------------------------
 # Dynamics (order can be tuned; this is a reasonable ear-first progression)
 # -----------------------------
 dynamics_chain = [
  ("dynamic_mf", "Mezzo-Forte (mf)"),
  ("dynamic_f", "Forte (f)"),
  ("dynamic_p", "Piano (p)"),
  ("dynamic_mp", "Mezzo-Piano (mp)"),
  ("dynamic_ff", "Fortissimo (ff)"),
  ("dynamic_pp", "Pianissimo (pp)"),
  ("dynamic_crescendo", "Crescendo (cresc.)"),
  ("dynamic_diminuendo", "Diminuendo"),
  ("dynamic_decrescendo", "Decrescendo (decresc.)"),
  ("dynamic_subito", "Subito (Sudden Dynamic Change)"),
  ("dynamic_sf", "Sforzando (sf)"),
  ("dynamic_sfz", "Sforzato (sfz)"),
  ("dynamic_sfp", "Sforzando-Piano (sfp)"),
  ("dynamic_fp", "Forte-Piano (fp)"),
  ("dynamic_rf", "Rinforzando (rf)"),
  ("dynamic_rfz", "Rinforzato (rfz)"),
  ("dynamic_fff", "Fortississimo (fff)"),
  ("dynamic_ppp", "Pianississimo (ppp)"),
 ]
 caps += ordered_caps("dynamics", dynamics_chain, prereq_chain=True, prereq_base=["pulse_tracking"])

 # -----------------------------
 # Articulations (sustained → connected → shortened → accented)
 # -----------------------------
 articulations_chain = [
  ("articulation_legato", "Legato"),
  ("articulation_tenuto", "Tenuto (-)"),
  ("articulation_portato", "Portato"),
  ("articulation_staccato", "Staccato"),
  ("articulation_staccatissimo", "Staccatissimo"),
  ("articulation_accent", "Accent (>)"),
  ("articulation_marcato", "Marcato (^)"),
 ]
 caps += ordered_caps("articulations", articulations_chain, prereq_chain=True, prereq_base=["first_note"])

 # -----------------------------
 # Technique
 # -----------------------------
 caps += [
  cap("technique_glissando", "Glissando", "instrument_technique", prerequisite_names=["first_note"]),
 ]

 # -----------------------------
 # Ornaments
 # You wanted Grace Note after Sixteenth Notes; Trill after Interval Velocity Score soft gate (not a capability),
 # so we just prerequisite it on interval competence + rhythmic competence.
 # -----------------------------
 caps += [
  cap("ornament_grace_note", "Grace Note", "ornaments", prerequisite_names=["rhythm_sixteenth_notes"]),
  cap("ornament_trill", "Trill", "ornaments", prerequisite_names=["interval_M2", "rhythm_eighth_notes"], difficulty_tier=2),
  cap("ornament_mordent", "Mordent", "ornaments", prerequisite_names=["ornament_trill"], difficulty_tier=2),
  cap("ornament_inverted_mordent", "Inverted Mordent", "ornaments", prerequisite_names=["ornament_mordent"], difficulty_tier=2),
  cap("ornament_turn", "Turn", "ornaments", prerequisite_names=["ornament_inverted_mordent"], difficulty_tier=2),
  cap("ornament_tremolo", "Tremolo", "ornaments", prerequisite_names=["rhythm_32nd_notes", "ornament_turn"], difficulty_tier=3),
 ]

 # -----------------------------
 # Tuplets
 # You want Triplets first, then Triplet Quarters, then other tuplets later.
 # We model triplet eighth under rhythm ladder already; add triplet-quarter as separate tuplet concept.
 # -----------------------------
 caps += [
  cap("tuplet_triplet_general", "Triplet (General Concept)", "tuplets", prerequisite_names=["rhythm_triplets_eighth"]),
  cap("tuplet_triplet_quarter", "Triplet Quarter Notes", "tuplets", prerequisite_names=["tuplet_triplet_general", "rhythm_quarter_notes"]),
  cap("tuplet_duplet", "Duplet", "tuplets", prerequisite_names=["tuplet_triplet_general"], difficulty_tier=2),
  cap("tuplet_quintuplet", "Quintuplet", "tuplets", prerequisite_names=["tuplet_triplet_general"], difficulty_tier=3),
  cap("tuplet_sextuplet", "Sextuplet", "tuplets", prerequisite_names=["tuplet_quintuplet"], difficulty_tier=3),
  cap("tuplet_septuplet", "Septuplet", "tuplets", prerequisite_names=["tuplet_sextuplet"], difficulty_tier=3),
 ]

 # -----------------------------
 # Repeat structures / form
 # -----------------------------
 caps += [
  cap("form_repeat_sign", "Repeat Sign", "form", prerequisite_names=["staff_basics"]),
  cap("form_first_ending", "First Ending", "form", prerequisite_names=["form_repeat_sign"]),
  cap("form_second_ending", "Second Ending", "form", prerequisite_names=["form_first_ending"]),
  cap("form_dc", "Da Capo (D.C.)", "form", prerequisite_names=["form_repeat_sign"], difficulty_tier=2),
  cap("form_ds", "Dal Segno (D.S.)", "form", prerequisite_names=["form_repeat_sign"], difficulty_tier=2),
  cap("form_coda", "Coda", "form", prerequisite_names=["form_ds"], difficulty_tier=2),
  cap("form_segno", "Segno", "form", prerequisite_names=["form_ds"], difficulty_tier=2),
  cap("form_fine", "Fine", "form", prerequisite_names=["form_dc"], difficulty_tier=2),
 ]

 # -----------------------------
 # Other notations
 # -----------------------------
 caps += [
  cap("notation_fermata", "Fermata", "notation_symbols", prerequisite_names=["staff_basics"]),
  cap("notation_breath_mark", "Breath Mark", "notation_symbols", prerequisite_names=["staff_basics"]),
  cap("notation_chord_symbols", "Chord Symbols", "notation_symbols", prerequisite_names=["key_signature_basics"], difficulty_tier=3),
  cap("notation_figured_bass", "Figured Bass", "notation_symbols", prerequisite_names=["notation_chord_symbols"], difficulty_tier=3),
  cap("texture_two_voices", "Two Voices", "texture", prerequisite_names=["staff_basics"], difficulty_tier=2),
  cap("texture_three_voices", "Three Voices", "texture", prerequisite_names=["texture_two_voices"], difficulty_tier=3),
  cap("texture_four_voices", "Four Voices", "texture", prerequisite_names=["texture_three_voices"], difficulty_tier=3),
 ]

 # -----------------------------
 # Tempo terms (vocabulary) + tempo modification skills
 # You wanted: vocab first (steady tempo zones), then elastic time.
 # We'll model both:
 # - tempo_term_* as vocabulary
 # - tempo_skill_* as control drills
 # -----------------------------
 tempo_terms = [
  ("tempo_term_largo", "Largo (Broad, Spacious)"),
  ("tempo_term_adagio", "Adagio (Slow, Expressive)"),
  ("tempo_term_andante", "Andante (Walking Pace)"),
  ("tempo_term_moderato", "Moderato (Moderate, Controlled)"),
  ("tempo_term_allegretto", "Allegretto (Lightly Fast)"),
  ("tempo_term_allegro", "Allegro (Bright, Fast)"),
  ("tempo_term_vivace", "Vivace (Lively)"),
  ("tempo_term_presto", "Presto (Very Fast)"),
  ("tempo_term_prestissimo", "Prestissimo (Extremely Fast)"),
 ]
 caps += ordered_caps("tempo_terms", tempo_terms, prereq_chain=True, prereq_base=["pulse_tracking"])

 # Elastic control (after a steady-tempo mental model)
 caps += [
  cap("tempo_skill_ritardando", "Ritardando (rit.)", "tempo_skills", prerequisite_names=["tempo_term_allegro"]),
  cap("tempo_skill_rallentando", "Rallentando (rall.)", "tempo_skills", prerequisite_names=["tempo_skill_ritardando"]),
  cap("tempo_skill_a_tempo", "A Tempo", "tempo_skills", prerequisite_names=["tempo_skill_ritardando"]),
  cap("tempo_skill_accelerando", "Accelerando", "tempo_skills", prerequisite_names=["tempo_skill_a_tempo"]),
  cap("tempo_skill_rubato", "Rubato (Elastic Time)", "tempo_skills", prerequisite_names=["tempo_skill_accelerando"], difficulty_tier=2),
 ]

 # -----------------------------
 # Expressive terms (vocabulary; not hard/soft gates)
 # We chain lightly, but you can randomize teaching in engine.
 # -----------------------------
 expressive_terms = [
  ("expression_dolce", "Dolce"),
  ("expression_cantabile", "Cantabile"),
  ("expression_espressivo", "Espressivo"),
  ("expression_con_brio", "Con brio"),
  ("expression_con_fuoco", "Con fuoco"),
  ("expression_con_moto", "Con moto"),
  ("expression_grazioso", "Grazioso"),
  ("expression_leggiero", "Leggiero"),
  ("expression_maestoso", "Maestoso"),
  ("expression_pesante", "Pesante"),
  ("expression_sostenuto", "Sostenuto (expressive term)"),
  ("expression_tranquillo", "Tranquillo"),
  ("expression_agitato", "Agitato"),
  ("expression_animato", "Animato"),
  ("expression_appassionato", "Appassionato"),
  ("expression_brillante", "Brillante"),
  ("expression_morendo", "Morendo"),
  ("expression_perdendosi", "Perdendosi"),
 ]
 # Make them all depend on staff basics (but not a strict chain)
 for (n, d) in expressive_terms:
  caps.append(cap(n, d, "expression_terms", prerequisite_names=["staff_basics"], requirement_type="learnable_in_context"))

 # -----------------------------
 # Scales (after octave in comfort zone conceptually; in v1 we gate by tonal + interval skills)
 # -----------------------------
 caps += [
  cap("scale_major", "Major Scale (Ionian Mode)", "scales_diatonic", prerequisite_names=["interval_octave", "whole_steps_theory", "half_steps_theory"], difficulty_tier=2),
  cap("scale_natural_minor", "Natural Minor Scale (Aeolian Mode)", "scales_diatonic", prerequisite_names=["scale_major"], difficulty_tier=2),
  cap("scale_major_pentatonic", "Major Pentatonic Scale", "scales_pentatonic", prerequisite_names=["scale_major"], difficulty_tier=2),
  cap("scale_minor_pentatonic", "Minor Pentatonic Scale", "scales_pentatonic", prerequisite_names=["scale_natural_minor"], difficulty_tier=2),
  cap("scale_chromatic", "Chromatic Scale", "scales_symmetric", prerequisite_names=["scale_minor_pentatonic"], difficulty_tier=3),
 ]

 # Modes (requires bigger range in real life; capability graph just assumes later)
 caps += [
  cap("mode_dorian", "Dorian Mode", "scales_modes", prerequisite_names=["scale_chromatic"], difficulty_tier=3),
  cap("mode_phrygian", "Phrygian Mode", "scales_modes", prerequisite_names=["mode_dorian"], difficulty_tier=3),
  cap("mode_lydian", "Lydian Mode", "scales_modes", prerequisite_names=["mode_phrygian"], difficulty_tier=3),
  cap("mode_mixolydian", "Mixolydian Mode", "scales_modes", prerequisite_names=["mode_lydian"], difficulty_tier=3),
  cap("mode_locrian", "Locrian Mode", "scales_modes", prerequisite_names=["mode_mixolydian"], difficulty_tier=3),
  cap("scale_harmonic_minor", "Harmonic Minor Scale", "scales_variations", prerequisite_names=["scale_natural_minor"], difficulty_tier=3),
  cap("scale_melodic_minor", "Melodic Minor Scale", "scales_variations", prerequisite_names=["scale_harmonic_minor"], difficulty_tier=3),
  cap("scale_minor_major", "Minor-Major Scale (Variant)", "scales_variations", prerequisite_names=["scale_melodic_minor"], difficulty_tier=3),
  cap("scale_major_minor", "Major-Minor Scale (Variant)", "scales_variations", prerequisite_names=["scale_minor_major"], difficulty_tier=3),
 ]

 # -----------------------------
 # Assign sequence_order and bit_index deterministically
 # sequence_order = index in final list
 # bit_index = index in final list (you can later re-map if you want reserved blocks)
 # -----------------------------
 # Ensure stable ordering by (domain, then insertion order) to avoid churn when you add later.
 # If you want exact "teaching order" sorting, change this sorting strategy.
 caps_sorted = sorted(caps, key=lambda x: (x["domain"], x["name"]))

 for i, c in enumerate(caps_sorted):
  c["sequence_order"] = i + 1
  c["bit_index"] = i

 payload = {
  "version": "capabilities_full_graph",
  "count": len(caps_sorted),
  "capabilities": caps_sorted
 }

 with open("capabilities.json", "w") as f:
  json.dump(payload, f, indent=1)

 print(f"Wrote capabilities.json with {len(caps_sorted)} capabilities.")


if __name__ == "__main__":
 main()