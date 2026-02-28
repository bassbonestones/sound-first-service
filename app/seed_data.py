# Placeholder data for initial materials and focus cards
from app.models.core import Material, FocusCard
from app.db import SessionLocal

def seed_materials_and_focus_cards():
    db = SessionLocal()
    # Add materials
    materials = [
        Material(
            title="Autumn Leaves",
            allowed_keys="C,F,Bb,Eb",
            required_capability_ids="cap_clef_treble_known,cap_time_signature_4_4_known",
            scaffolding_capability_ids="cap_articulation_staccato_known",
            musicxml_canonical="<musicxml>Autumn Leaves</musicxml>",
            original_key_center="G minor",
            pitch_reference_type="TONAL",
            pitch_ref_json='{"tonic": "G", "mode": "minor"}',
            spelling_policy="from_key"
        ),
        Material(
            title="Clarke Study #2",
            allowed_keys="C,G,F",
            required_capability_ids="cap_clef_treble_known,cap_note_value_quarter_known",
            scaffolding_capability_ids="cap_articulation_tenuto_known",
            musicxml_canonical="<musicxml>Clarke Study #2</musicxml>",
            original_key_center="C major",
            pitch_reference_type="TONAL",
            pitch_ref_json='{"tonic": "C", "mode": "major"}',
            spelling_policy="from_key"
        ),
        Material(
            title="Do-Re-Do",
            allowed_keys="C,F",
            required_capability_ids="cap_clef_treble_known",
            scaffolding_capability_ids="cap_articulation_slur_known",
            musicxml_canonical="<musicxml>Do-Re-Do</musicxml>",
            original_key_center=None,
            pitch_reference_type="ANCHOR_INTERVAL",
            pitch_ref_json='{"pattern_kind": "semitone_offsets", "offsets": [0, 2, 0], "canonical_anchor_midi": 60}',
            spelling_policy="contextual"
        ),
    ]
    for m in materials:
        if not db.query(Material).filter_by(title=m.title).first():
            db.add(m)
    # Add focus cards
    focus_cards = [
        FocusCard(name="Pitch Center"),
        FocusCard(name="Projection Intent"),
        FocusCard(name="Internal Pulse"),
        FocusCard(name="Phrase Direction"),
        FocusCard(name="No Extra Movement"),
    ]
    for fc in focus_cards:
        if not db.query(FocusCard).filter_by(name=fc.name).first():
            db.add(fc)
    db.commit()
    db.close()

if __name__ == "__main__":
    seed_materials_and_focus_cards()
