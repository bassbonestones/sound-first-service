# Seed data for Sound First music practice app
import json
from app.models.core import Material, FocusCard
from app.db import SessionLocal


# === FOCUS CARDS (All 28 from spec) ===
FOCUS_CARDS = [
    # --- Ear & Pitch (3 cards) ---
    {
        "name": "Pitch Center",
        "category": "Ear & Pitch",
        "description": "Focus on locking your ear onto the exact center of each pitch before and during playing.",
        "attention_cue": "Lock your ear onto the center of the pitch before you play.",
        "micro_cues": ["Hear the center.", "Sing the center.", "Play the center."],
        "prompts": {
            "listen": "Listen for the exact center of the pitch. Not sharp, not flat—right in the middle.",
            "sing": "Sing the pitch and feel where it sits in the center.",
            "imagine_instrument": "Imagine your instrument producing that centered pitch."
        }
    },
    {
        "name": "Pitch + Tone Together",
        "category": "Ear & Pitch",
        "description": "Combine pitch accuracy with tone quality as a unified target.",
        "attention_cue": "Hear both the pitch center and the tone quality you want before playing.",
        "micro_cues": ["Hear pitch.", "Hear tone.", "Play both."],
        "prompts": {
            "listen": "Notice how the tone color and pitch are intertwined in the model.",
            "sing": "Vocalize with both pitch accuracy and the tone character you want.",
            "imagine_instrument": "Imagine your instrument with that exact pitch and tone together."
        }
    },
    {
        "name": "Pitch Snap",
        "category": "Ear & Pitch",
        "description": "Focus on instantaneous pitch arrival—no scooping or searching.",
        "attention_cue": "Snap to the pitch immediately. No searching.",
        "micro_cues": ["Hear it.", "Snap to it.", "Lock in."],
        "prompts": {
            "listen": "Notice how the pitch arrives instantly without any sliding or searching.",
            "sing": "Sing each pitch with immediate arrival—no scooping up or down.",
            "imagine_instrument": "Imagine your first note snapping perfectly into place."
        }
    },
    
    # --- Resonance & Tone (6 cards) ---
    {
        "name": "Projection Intent",
        "category": "Resonance & Tone",
        "description": "Focus on directing sound outward to a specific point in space.",
        "attention_cue": "Aim your sound at a point beyond the room.",
        "micro_cues": ["Pick a target.", "Direct the sound.", "Fill the space."],
        "prompts": {
            "listen": "Notice how the sound seems to travel and fill space.",
            "sing": "Sing as if sending your voice to the back wall.",
            "imagine_instrument": "Imagine your sound traveling to a specific point in the distance."
        }
    },
    {
        "name": "Resonant Ring",
        "category": "Resonance & Tone",
        "description": "Focus on the natural overtones and ring in your sound.",
        "attention_cue": "Listen for the ring in your sound—the overtones that bloom after the attack.",
        "micro_cues": ["Start the note.", "Let it ring.", "Hear the bloom."],
        "prompts": {
            "listen": "Notice the overtones that continue after the initial attack.",
            "sing": "Let your voice resonate and bloom after each onset.",
            "imagine_instrument": "Imagine your tone ringing with rich overtones."
        }
    },
    {
        "name": "Core Sound",
        "category": "Resonance & Tone",
        "description": "Focus on the fundamental, centered tone at the heart of your sound.",
        "attention_cue": "Find the core—the centered, fundamental tone.",
        "micro_cues": ["Hear the fundamental.", "Center the tone.", "Maintain the core."],
        "prompts": {
            "listen": "Notice the centered, fundamental tone quality.",
            "sing": "Produce a tone with a strong, clear center.",
            "imagine_instrument": "Imagine a solid core to every note you play."
        }
    },
    {
        "name": "Soft with Carry",
        "category": "Resonance & Tone",
        "description": "Play softly while maintaining projection and presence.",
        "attention_cue": "Play soft but let the sound still travel.",
        "micro_cues": ["Reduce volume.", "Keep projection.", "Let it carry."],
        "prompts": {
            "listen": "Notice how soft playing can still have presence and carry.",
            "sing": "Sing quietly but with forward placement.",
            "imagine_instrument": "Imagine a soft sound that still reaches the back of the hall."
        }
    },
    {
        "name": "Projected without Push",
        "category": "Resonance & Tone",
        "description": "Project sound using resonance rather than force.",
        "attention_cue": "Project through resonance, not through pushing.",
        "micro_cues": ["Open the sound.", "Let it resonate.", "No forcing."],
        "prompts": {
            "listen": "Notice projection that comes from resonance rather than force.",
            "sing": "Project your voice without tension or pushing.",
            "imagine_instrument": "Imagine full projection with completely relaxed effort."
        }
    },
    {
        "name": "Stable Center Through Change",
        "category": "Resonance & Tone",
        "description": "Maintain consistent tone quality across register and dynamic changes.",
        "attention_cue": "Keep your core tone stable even as other things change.",
        "micro_cues": ["Establish the center.", "Change register/dynamic.", "Maintain the core."],
        "prompts": {
            "listen": "Notice how the core tone stays consistent through changes.",
            "sing": "Maintain your tone quality while changing pitch or volume.",
            "imagine_instrument": "Imagine the same fundamental tone through every note."
        }
    },
    
    # --- Rhythm & Time (5 cards) ---
    {
        "name": "Subdivision",
        "category": "Rhythm & Time",
        "description": "Feel the smallest rhythmic unit underlying the music.",
        "attention_cue": "Feel the subdivision—the smallest pulse within the beat.",
        "micro_cues": ["Find the beat.", "Divide it.", "Feel the smallest unit."],
        "prompts": {
            "listen": "Notice the underlying subdivision that holds everything together.",
            "sing": "Tap or vocalize the subdivision while singing the melody.",
            "imagine_instrument": "Imagine each note placed precisely within the subdivision grid."
        }
    },
    {
        "name": "Internal Pulse",
        "category": "Rhythm & Time",
        "description": "Maintain a steady internal sense of time independent of external sounds.",
        "attention_cue": "Feel the pulse inside you—steady and independent.",
        "micro_cues": ["Find your pulse.", "Lock in.", "Trust your time."],
        "prompts": {
            "listen": "Internalize the tempo so completely it feels like your heartbeat.",
            "sing": "Maintain rock-solid time from within.",
            "imagine_instrument": "Imagine playing with perfect internal time, no metronome needed."
        }
    },
    {
        "name": "Rhythm Locks Pitch",
        "category": "Rhythm & Time",
        "description": "Use rhythmic precision to support pitch accuracy.",
        "attention_cue": "Let perfect rhythm create perfect pitch placement.",
        "micro_cues": ["Set the rhythm.", "Lock the pitch.", "They're connected."],
        "prompts": {
            "listen": "Notice how rhythmic precision supports pitch accuracy.",
            "sing": "Use exact rhythm to place each pitch precisely.",
            "imagine_instrument": "Imagine rhythm and pitch as one unified target."
        }
    },
    {
        "name": "Speech-Like Time",
        "category": "Rhythm & Time",
        "description": "Play with the natural rhythmic ebb and flow of speech.",
        "attention_cue": "Let the rhythm breathe like natural speech.",
        "micro_cues": ["Hear the phrase.", "Speak the rhythm.", "Natural timing."],
        "prompts": {
            "listen": "Notice how the rhythm rises and falls like speech.",
            "sing": "Let your phrasing have the natural timing of speaking.",
            "imagine_instrument": "Imagine playing as if telling a story."
        }
    },
    {
        "name": "Time First",
        "category": "Rhythm & Time",
        "description": "Establish time before adding any other musical elements.",
        "attention_cue": "Set the time before you play a note.",
        "micro_cues": ["Feel the tempo.", "Count in.", "Then play."],
        "prompts": {
            "listen": "Notice how strong time sense underlies everything.",
            "sing": "Establish the pulse before adding the melody.",
            "imagine_instrument": "Imagine the time already moving before you enter."
        }
    },
    
    # --- Articulation & Communication (6 cards) ---
    {
        "name": "Clean Front",
        "category": "Articulation & Communication",
        "description": "Focus on clear, precise note beginnings.",
        "attention_cue": "Every note starts with a clean, clear attack.",
        "micro_cues": ["Prepare the start.", "Clean attack.", "Clear beginning."],
        "prompts": {
            "listen": "Notice how each note begins with clarity.",
            "sing": "Start each note with a precise, clean onset.",
            "imagine_instrument": "Imagine every attack perfectly clear."
        }
    },
    {
        "name": "Rhythmic Communication",
        "category": "Articulation & Communication",
        "description": "Use articulation to communicate rhythmic intention.",
        "attention_cue": "Your articulation tells the rhythm story.",
        "micro_cues": ["Feel the rhythm.", "Shape the attack.", "Communicate."],
        "prompts": {
            "listen": "Notice how articulation choices communicate rhythmic character.",
            "sing": "Use your consonants and vowels to express rhythm.",
            "imagine_instrument": "Imagine your articulation speaking the rhythm."
        }
    },
    {
        "name": "Instant Switch Connection",
        "category": "Articulation & Communication",
        "description": "Connect different articulations seamlessly without hesitation.",
        "attention_cue": "Switch articulation styles instantly without breaking flow.",
        "micro_cues": ["One style.", "Switch!", "No gap."],
        "prompts": {
            "listen": "Notice smooth transitions between articulation types.",
            "sing": "Practice switching from legato to staccato instantly.",
            "imagine_instrument": "Imagine flowing between articulations effortlessly."
        }
    },
    {
        "name": "Attack Matches Style",
        "category": "Articulation & Communication",
        "description": "Choose attack styles that match the musical context.",
        "attention_cue": "Match your attack to the musical character.",
        "micro_cues": ["Hear the style.", "Shape the attack.", "Match."],
        "prompts": {
            "listen": "Notice how attack style reflects musical character.",
            "sing": "Vary your attack to match the mood of each phrase.",
            "imagine_instrument": "Imagine the perfect attack for each musical moment."
        }
    },
    {
        "name": "Clean Ends",
        "category": "Articulation & Communication",
        "description": "Focus on precise, intentional note endings.",
        "attention_cue": "End every note with intention and clarity.",
        "micro_cues": ["Shape the note.", "Plan the end.", "Clean release."],
        "prompts": {
            "listen": "Notice how notes end—tapered? Cut off? Sustained?",
            "sing": "Give each note a deliberate ending.",
            "imagine_instrument": "Imagine controlling exactly when and how each note ends."
        }
    },
    {
        "name": "Rhythmic Edges",
        "category": "Articulation & Communication",
        "description": "Create clear rhythmic definition through precise note boundaries.",
        "attention_cue": "Define the rhythm with clear edges on every note.",
        "micro_cues": ["Start edge.", "End edge.", "Clear boundaries."],
        "prompts": {
            "listen": "Notice how clear note boundaries create rhythmic clarity.",
            "sing": "Give each note precise boundaries.",
            "imagine_instrument": "Imagine each note with perfectly defined edges."
        }
    },
    
    # --- Ease & Efficiency (4 cards) ---
    {
        "name": "No Extra Movement",
        "category": "Ease & Efficiency",
        "description": "Eliminate unnecessary physical tension and movement.",
        "attention_cue": "Use only the movement you need. Nothing extra.",
        "micro_cues": ["Scan for tension.", "Release extra.", "Essential only."],
        "prompts": {
            "listen": "Imagine the sound being produced with minimal effort.",
            "sing": "Sing with only the effort needed—nothing more.",
            "imagine_instrument": "Imagine playing with perfect efficiency."
        }
    },
    {
        "name": "Free Air",
        "category": "Ease & Efficiency",
        "description": "Allow breath to flow freely without restriction.",
        "attention_cue": "Let the air flow freely—no holding, no forcing.",
        "micro_cues": ["Open the throat.", "Release.", "Let it flow."],
        "prompts": {
            "listen": "Notice sound produced with free, unrestricted air.",
            "sing": "Sing with completely free airflow.",
            "imagine_instrument": "Imagine air moving through your instrument without any obstruction."
        }
    },
    {
        "name": "Even Changes",
        "category": "Ease & Efficiency",
        "description": "Make musical changes (register, dynamic, etc.) smoothly and evenly.",
        "attention_cue": "Every change is smooth and even—no bumps or jolts.",
        "micro_cues": ["Prepare the change.", "Smooth transition.", "Even motion."],
        "prompts": {
            "listen": "Notice how changes happen smoothly without disruption.",
            "sing": "Make every change gradual and controlled.",
            "imagine_instrument": "Imagine all transitions perfectly smooth."
        }
    },
    {
        "name": "Minimum Pressure",
        "category": "Ease & Efficiency",
        "description": "Use the minimum physical pressure needed to produce the sound.",
        "attention_cue": "Only as much pressure as you need—not a gram more.",
        "micro_cues": ["Find the minimum.", "Reduce.", "Just enough."],
        "prompts": {
            "listen": "Imagine sound produced with the lightest possible touch.",
            "sing": "Produce tone with minimal effort.",
            "imagine_instrument": "Imagine playing with the lightest pressure that still works."
        }
    },
    
    # --- Musical Shape (6 cards) ---
    {
        "name": "Phrase Direction",
        "category": "Musical Shape",
        "description": "Every phrase has direction—moving toward or away from a point.",
        "attention_cue": "Know where the phrase is going. Every phrase has direction.",
        "micro_cues": ["Find the goal.", "Move toward it.", "Shape the line."],
        "prompts": {
            "listen": "Notice the forward motion and goal of each phrase.",
            "sing": "Give each phrase a clear sense of direction.",
            "imagine_instrument": "Imagine your phrase as an arrow with a target."
        }
    },
    {
        "name": "Forward Rest",
        "category": "Musical Shape",
        "description": "Rests have forward momentum—they don't stop the music.",
        "attention_cue": "Rests keep moving forward. They're active, not passive.",
        "micro_cues": ["Active silence.", "Keep the momentum.", "Forward through rest."],
        "prompts": {
            "listen": "Notice how rests maintain musical momentum.",
            "sing": "Feel the rest as active anticipation.",
            "imagine_instrument": "Imagine rests as springboards to the next phrase."
        }
    },
    {
        "name": "Continuous Tension",
        "category": "Musical Shape",
        "description": "Maintain musical tension and engagement throughout a passage.",
        "attention_cue": "Keep the musical tension alive from start to finish.",
        "micro_cues": ["Engage.", "Maintain.", "Sustain the line."],
        "prompts": {
            "listen": "Notice how musical tension is sustained throughout.",
            "sing": "Keep every moment engaged with musical intention.",
            "imagine_instrument": "Imagine an unbroken thread of musical energy."
        }
    },
    {
        "name": "Line Over Notes",
        "category": "Musical Shape",
        "description": "Think horizontally—the line matters more than individual notes.",
        "attention_cue": "Hear the line, not just the notes. Connect everything.",
        "micro_cues": ["Think horizontal.", "Connect.", "One line."],
        "prompts": {
            "listen": "Notice the overarching line rather than individual notes.",
            "sing": "Sing the phrase as one continuous line.",
            "imagine_instrument": "Imagine drawing a single unbroken line through the music."
        }
    },
    {
        "name": "Confident Silence",
        "category": "Musical Shape",
        "description": "Use silence with intention and confidence.",
        "attention_cue": "Own the silence. It's part of the music.",
        "micro_cues": ["Stop with intention.", "Hold the silence.", "Stay confident."],
        "prompts": {
            "listen": "Notice how silence is used as a musical element.",
            "sing": "Use silence as deliberately as sound.",
            "imagine_instrument": "Imagine silence as a powerful musical statement."
        }
    },
    {
        "name": "Phrase Targets",
        "category": "Musical Shape",
        "description": "Identify and move toward the peak or goal of each phrase.",
        "attention_cue": "Find the target of each phrase and shape toward it.",
        "micro_cues": ["Find the peak.", "Build toward it.", "Arrive."],
        "prompts": {
            "listen": "Notice where each phrase reaches its peak or goal.",
            "sing": "Shape every phrase toward its target note or moment.",
            "imagine_instrument": "Imagine each phrase as an arc with a clear destination."
        }
    },
]


# Note: V1 Capabilities have been retired.
# Capabilities are now defined in resources/capabilities.json and seeded via seed_capabilities.py

# === MATERIALS ===
MATERIALS = [
    {
        "title": "Autumn Leaves",
        "allowed_keys": "C,F,Bb,Eb,G",
        "required_capability_ids": "cap_clef_treble_known,cap_time_signature_4_4_known",
        "scaffolding_capability_ids": "cap_articulation_staccato_known",
        "musicxml_canonical": "<music-xml><part><measure><note><pitch><step>G</step><octave>4</octave></pitch></note></measure></part></music-xml>",
        "original_key_center": "G minor",
        "pitch_reference_type": "TONAL",
        "pitch_ref_json": '{"tonic": "G", "mode": "minor"}',
        "spelling_policy": "from_key"
    },
    {
        "title": "Clarke Study #2",
        "allowed_keys": "C,G,F,D,Bb",
        "required_capability_ids": "cap_clef_treble_known,cap_note_value_quarter_known",
        "scaffolding_capability_ids": "cap_articulation_tenuto_known",
        "musicxml_canonical": "<music-xml><part><measure><note><pitch><step>C</step><octave>4</octave></pitch></note></measure></part></music-xml>",
        "original_key_center": "C major",
        "pitch_reference_type": "TONAL",
        "pitch_ref_json": '{"tonic": "C", "mode": "major"}',
        "spelling_policy": "from_key"
    },
    {
        "title": "Do-Re-Do Pattern",
        "allowed_keys": "C,F,G,D,Bb,Eb,A",
        "required_capability_ids": "cap_clef_treble_known",
        "scaffolding_capability_ids": "cap_articulation_slur_known",
        "musicxml_canonical": "<music-xml><part><measure><note><pitch><step>C</step><octave>4</octave></pitch></note><note><pitch><step>D</step><octave>4</octave></pitch></note><note><pitch><step>C</step><octave>4</octave></pitch></note></measure></part></music-xml>",
        "original_key_center": None,
        "pitch_reference_type": "ANCHOR_INTERVAL",
        "pitch_ref_json": '{"pattern_kind": "semitone_offsets", "offsets": [0, 2, 0], "canonical_anchor_midi": 60}',
        "spelling_policy": "contextual"
    },
    {
        "title": "Long Tone Exercise",
        "allowed_keys": "C,F,Bb,Eb,G,D,A",
        "required_capability_ids": "cap_clef_treble_known,cap_note_value_whole_known",
        "scaffolding_capability_ids": "cap_dynamic_crescendo_known,cap_dynamic_decrescendo_known",
        "musicxml_canonical": "<music-xml><part><measure><note><pitch><step>F</step><octave>4</octave></pitch><duration>4</duration></note></measure></part></music-xml>",
        "original_key_center": "F major",
        "pitch_reference_type": "TONAL",
        "pitch_ref_json": '{"tonic": "F", "mode": "major"}',
        "spelling_policy": "from_key"
    },
    {
        "title": "Scale Pattern - Major",
        "allowed_keys": "C,G,D,A,F,Bb,Eb",
        "required_capability_ids": "cap_clef_treble_known,cap_note_value_eighth_known",
        "scaffolding_capability_ids": "cap_articulation_legato_known",
        "musicxml_canonical": "<music-xml><part><measure><note><pitch><step>C</step><octave>4</octave></pitch></note><note><pitch><step>D</step><octave>4</octave></pitch></note><note><pitch><step>E</step><octave>4</octave></pitch></note></measure></part></music-xml>",
        "original_key_center": "C major",
        "pitch_reference_type": "TONAL",
        "pitch_ref_json": '{"tonic": "C", "mode": "major"}',
        "spelling_policy": "from_key"
    },
    {
        "title": "Lip Slur - Basic",
        "allowed_keys": "C,F,Bb",
        "required_capability_ids": "cap_clef_treble_known,cap_articulation_slur_known",
        "scaffolding_capability_ids": "",
        "musicxml_canonical": "<music-xml><part><measure><note><pitch><step>C</step><octave>4</octave></pitch></note><note><pitch><step>G</step><octave>4</octave></pitch></note></measure></part></music-xml>",
        "original_key_center": "C major",
        "pitch_reference_type": "TONAL",
        "pitch_ref_json": '{"tonic": "C", "mode": "major"}',
        "spelling_policy": "from_key"
    },
    {
        "title": "Arban Variation Theme",
        "allowed_keys": "C,G,F",
        "required_capability_ids": "cap_clef_treble_known,cap_note_value_sixteenth_known",
        "scaffolding_capability_ids": "cap_articulation_staccato_known",
        "musicxml_canonical": "<music-xml><part><measure><note><pitch><step>C</step><octave>5</octave></pitch></note></measure></part></music-xml>",
        "original_key_center": "C major",
        "pitch_reference_type": "TONAL",
        "pitch_ref_json": '{"tonic": "C", "mode": "major"}',
        "spelling_policy": "from_key"
    },
    {
        "title": "Intervallic Study - 3rds",
        "allowed_keys": "C,F,G,Bb,D,Eb",
        "required_capability_ids": "cap_clef_treble_known",
        "scaffolding_capability_ids": "cap_articulation_legato_known",
        "musicxml_canonical": "<music-xml><part><measure><note><pitch><step>C</step><octave>4</octave></pitch></note><note><pitch><step>E</step><octave>4</octave></pitch></note></measure></part></music-xml>",
        "original_key_center": "C major",
        "pitch_reference_type": "ANCHOR_INTERVAL",
        "pitch_ref_json": '{"pattern_kind": "semitone_offsets", "offsets": [0, 4], "canonical_anchor_midi": 60}',
        "spelling_policy": "contextual"
    },
]


def seed_all():
    """Seed all data tables."""
    db = SessionLocal()
    try:
        # Note: Capabilities are now seeded via seed_capabilities.py (Capability)
        
        # Seed Focus Cards
        for fc_data in FOCUS_CARDS:
            existing = db.query(FocusCard).filter_by(name=fc_data["name"]).first()
            if not existing:
                fc = FocusCard(
                    name=fc_data["name"],
                    description=fc_data["description"],
                    category=fc_data["category"],
                    attention_cue=fc_data["attention_cue"],
                    micro_cues=json.dumps(fc_data["micro_cues"]),
                    prompts=json.dumps(fc_data["prompts"])
                )
                db.add(fc)
            else:
                # Update existing focus cards with new fields
                existing.description = fc_data["description"]
                existing.category = fc_data["category"]
                existing.attention_cue = fc_data["attention_cue"]
                existing.micro_cues = json.dumps(fc_data["micro_cues"])
                existing.prompts = json.dumps(fc_data["prompts"])
        
        # Seed Materials
        for mat_data in MATERIALS:
            existing = db.query(Material).filter_by(title=mat_data["title"]).first()
            if not existing:
                mat = Material(
                    title=mat_data["title"],
                    allowed_keys=mat_data["allowed_keys"],
                    required_capability_ids=mat_data["required_capability_ids"],
                    scaffolding_capability_ids=mat_data["scaffolding_capability_ids"],
                    musicxml_canonical=mat_data["musicxml_canonical"],
                    original_key_center=mat_data["original_key_center"],
                    pitch_reference_type=mat_data["pitch_reference_type"],
                    pitch_ref_json=mat_data["pitch_ref_json"],
                    spelling_policy=mat_data["spelling_policy"]
                )
                db.add(mat)
        
        # Seed onboarding data for user 1
        from app.models.core import User
        existing_user = db.query(User).filter_by(id=1).first()
        if not existing_user:
            user = User(
                id=1,
                email="user1@example.com",
                instrument=None,
                resonant_note=None,
                range_low=None,
                range_high=None,
                comfortable_capabilities=None,
                day0_completed=False,
                day0_stage=0
            )
            db.add(user)
        else:
            existing_user.instrument = None
            existing_user.resonant_note = None
            existing_user.range_low = None
            existing_user.range_high = None
            existing_user.comfortable_capabilities = None
            existing_user.day0_completed = False
            existing_user.day0_stage = 0
        db.commit()
        print("Seed data inserted successfully!")
        print(f"  - {len(FOCUS_CARDS)} focus cards")
        print(f"  - {len(MATERIALS)} materials")
        
    except Exception as e:
        db.rollback()
        print(f"Error seeding data: {e}")
        raise
    finally:
        db.close()


# For backwards compatibility
def seed_materials_and_focus_cards():
    """Legacy function - calls seed_all()"""
    seed_all()


if __name__ == "__main__":
    seed_all()
