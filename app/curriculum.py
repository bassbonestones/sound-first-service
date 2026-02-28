"""
Curriculum generation following the Sound-First Ear-First Doctrine.

Core principle: The ear leads the body.
Sequence: LISTEN → SING → IMAGINE → PLAY → REFLECT

Step Types:
- LISTEN: Hear the model phrase/pitch
- SING: Vocalize the material
- IMAGINE: Audiate the instrument sound in your head
- PLAY: Play on your instrument
- REFLECT: Rate satisfaction and fatigue
- RECOVERY: Breathing reset, physical rest (inserted automatically)
"""

import json
import re
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

# MIDI note mapping for range calculations
NOTE_TO_MIDI = {
    'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11
}

def note_to_midi(note_str: str) -> int:
    """Convert note string like 'C4', 'Bb3', 'F#5' to MIDI number."""
    if not note_str:
        return 60  # default to middle C
    
    match = re.match(r'([A-Ga-g])([#b]?)(\d+)', note_str)
    if not match:
        return 60
    
    note, accidental, octave = match.groups()
    midi = NOTE_TO_MIDI.get(note.upper(), 0)
    
    if accidental == '#':
        midi += 1
    elif accidental == 'b':
        midi -= 1
    
    return midi + (int(octave) + 1) * 12


def midi_to_note(midi: int) -> str:
    """Convert MIDI number to note string."""
    notes = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    octave = (midi // 12) - 1
    note = notes[midi % 12]
    return f"{note}{octave}"


@dataclass
class CurriculumStepData:
    """Data for a single curriculum step."""
    step_type: str
    instruction: str
    prompt: str = ""


# Standard curriculum templates for different goal types
CURRICULUM_TEMPLATES = {
    "fluency_through_keys": [
        CurriculumStepData("LISTEN", "Listen to the phrase. Notice the pitch center and character."),
        CurriculumStepData("SING", "Sing the phrase, matching pitch and rhythm."),
        CurriculumStepData("IMAGINE", "Imagine your instrument producing this exact sound."),
        CurriculumStepData("PLAY", "Play the phrase in the target key."),
        CurriculumStepData("REFLECT", "How did that feel? Rate your satisfaction."),
        CurriculumStepData("PLAY", "Play again in a different key."),
        CurriculumStepData("REFLECT", "Rate this attempt."),
    ],
    "range_expansion": [
        CurriculumStepData("LISTEN", "Listen to the target pitch. Lock onto its center."),
        CurriculumStepData("SING", "Sing the target pitch, feeling where it sits."),
        CurriculumStepData("IMAGINE", "Imagine producing this pitch with ease on your instrument."),
        CurriculumStepData("PLAY", "Approach the target: play one step below."),
        CurriculumStepData("REFLECT", "How did that feel?"),
        CurriculumStepData("RECOVERY", "Take a breath. Release any tension."),
        CurriculumStepData("PLAY", "Now play the target pitch."),
        CurriculumStepData("REFLECT", "Rate your attempt. Any strain?"),
    ],
    "articulation_development": [
        CurriculumStepData("LISTEN", "Listen for the articulation style - how each note begins and ends."),
        CurriculumStepData("SING", "Vocalize with the same articulation character."),
        CurriculumStepData("IMAGINE", "Imagine your instrument producing these precise attacks."),
        CurriculumStepData("PLAY", "Play with focus on clean note beginnings."),
        CurriculumStepData("REFLECT", "Were the attacks clear?"),
        CurriculumStepData("PLAY", "Play again, now focusing on note endings."),
        CurriculumStepData("REFLECT", "How was the overall articulation?"),
    ],
    "tempo_build": [
        CurriculumStepData("LISTEN", "Listen to the phrase at the starting tempo."),
        CurriculumStepData("SING", "Sing along, internalizing the pulse."),
        CurriculumStepData("IMAGINE", "Imagine playing at this tempo with ease."),
        CurriculumStepData("PLAY", "Play at the starting tempo."),
        CurriculumStepData("REFLECT", "How solid was your time?"),
        CurriculumStepData("PLAY", "Increase tempo slightly. Maintain ease."),
        CurriculumStepData("REFLECT", "Did you maintain control?"),
        CurriculumStepData("PLAY", "One more notch faster if comfortable."),
        CurriculumStepData("REFLECT", "Final rating for this tempo sequence."),
    ],
    "dynamic_control": [
        CurriculumStepData("LISTEN", "Listen for the dynamic shape and projection."),
        CurriculumStepData("SING", "Sing the phrase with the same dynamic contour."),
        CurriculumStepData("IMAGINE", "Imagine projecting this dynamic with full resonance."),
        CurriculumStepData("PLAY", "Play piano - soft with carry."),
        CurriculumStepData("REFLECT", "Did the soft sound still project?"),
        CurriculumStepData("PLAY", "Play forte - projected without push."),
        CurriculumStepData("REFLECT", "Was the forte free and resonant?"),
    ],
    "learn_by_ear": [
        CurriculumStepData("LISTEN", "Listen to the phrase multiple times. Absorb it."),
        CurriculumStepData("SING", "Sing what you heard from memory."),
        CurriculumStepData("LISTEN", "Listen again - did you match?"),
        CurriculumStepData("SING", "Sing again, adjusting any differences."),
        CurriculumStepData("IMAGINE", "Imagine playing it on your instrument."),
        CurriculumStepData("PLAY", "Play from memory, no notation."),
        CurriculumStepData("REFLECT", "How accurate was your recall?"),
    ],
    "musical_phrase_flow": [
        CurriculumStepData("LISTEN", "Listen for the phrase direction and peak."),
        CurriculumStepData("SING", "Sing with clear forward motion toward the phrase target."),
        CurriculumStepData("IMAGINE", "Imagine the musical line as one continuous arc."),
        CurriculumStepData("PLAY", "Play thinking 'line over notes' - horizontal, not vertical."),
        CurriculumStepData("REFLECT", "Did the phrase have direction?"),
        CurriculumStepData("PLAY", "Play again with even more forward momentum."),
        CurriculumStepData("REFLECT", "Did you reach the phrase target?"),
    ],
    "repertoire_fluency": [
        CurriculumStepData("LISTEN", "Listen to the passage. Note the overall character."),
        CurriculumStepData("SING", "Sing through the melodic line."),
        CurriculumStepData("IMAGINE", "Visualize yourself playing with confidence."),
        CurriculumStepData("PLAY", "Play through once for fluency."),
        CurriculumStepData("REFLECT", "How connected was the playing?"),
        CurriculumStepData("PLAY", "Play again with your focus card attention."),
        CurriculumStepData("REFLECT", "Rate this run-through."),
    ],
}

# Default template for unknown goal types
DEFAULT_CURRICULUM = [
    CurriculumStepData("LISTEN", "Listen to the material carefully."),
    CurriculumStepData("SING", "Sing or vocalize the material."),
    CurriculumStepData("IMAGINE", "Imagine your instrument producing this sound."),
    CurriculumStepData("PLAY", "Play the material on your instrument."),
    CurriculumStepData("REFLECT", "Rate your satisfaction with this attempt."),
]


def generate_curriculum_steps(
    goal_type: str,
    focus_card_prompts: dict,
    material_title: str,
    target_key: str,
    fatigue_level: int = 2
) -> List[Dict]:
    """
    Generate curriculum steps for a mini-session.
    
    Args:
        goal_type: The goal type (e.g., 'fluency_through_keys')
        focus_card_prompts: Prompts from the focus card for each step type
        material_title: Name of the material being practiced
        target_key: The key to practice in
        fatigue_level: Current fatigue (1-5), affects curriculum
        
    Returns:
        List of step dictionaries ready for DB insertion
    """
    template = CURRICULUM_TEMPLATES.get(goal_type, DEFAULT_CURRICULUM)
    
    # At high fatigue, reduce number of PLAY steps
    if fatigue_level >= 4:
        # Filter out extra PLAY steps, keep only essential ear-first sequence
        seen_play = False
        filtered = []
        for step in template:
            if step.step_type == "PLAY":
                if not seen_play:
                    filtered.append(step)
                    seen_play = True
                # Skip additional play steps at high fatigue
            else:
                filtered.append(step)
        template = filtered
    
    steps = []
    for idx, step_data in enumerate(template):
        # Get the appropriate prompt from focus card if available
        prompt_key_map = {
            "LISTEN": "listen",
            "SING": "sing",
            "IMAGINE": "imagine_instrument",
            "PLAY": "play",
            "REFLECT": "reflect",
            "RECOVERY": "recovery"
        }
        prompt_key = prompt_key_map.get(step_data.step_type, "")
        prompt = focus_card_prompts.get(prompt_key, "") if focus_card_prompts else ""
        
        # Customize instruction with material/key info
        instruction = step_data.instruction
        if "{material}" in instruction:
            instruction = instruction.replace("{material}", material_title)
        if "{key}" in instruction:
            instruction = instruction.replace("{key}", target_key)
        
        steps.append({
            "step_index": idx,
            "step_type": step_data.step_type,
            "instruction": instruction,
            "prompt": prompt,
            "is_completed": False,
            "rating": None,
            "notes": None
        })
    
    return steps


def check_material_in_range(
    material_key: str,
    user_range_low: str,
    user_range_high: str
) -> bool:
    """
    Check if a material's key is within the user's comfortable range.
    
    This is a simplified check - real implementation would analyze
    the material's actual pitch content.
    """
    if not user_range_low or not user_range_high:
        return True  # No range set, allow all
    
    # Get the tonic of the key (e.g., "G minor" -> "G")
    if not material_key:
        return True
    
    key_tonic = material_key.split()[0] if material_key else "C"
    
    # For now, assume the material centers around octave 4
    test_note = f"{key_tonic}4"
    
    low_midi = note_to_midi(user_range_low)
    high_midi = note_to_midi(user_range_high)
    test_midi = note_to_midi(test_note)
    
    # Allow some leeway (material might go a bit outside tonic)
    return (low_midi - 5) <= test_midi <= (high_midi + 5)


def filter_materials_by_capabilities(
    materials: list,
    user_capabilities: List[str]
) -> list:
    """
    Filter materials to only those the user has capabilities for.
    
    Args:
        materials: List of Material objects
        user_capabilities: List of capability names the user knows
        
    Returns:
        Filtered list of materials
    """
    if not user_capabilities:
        return materials  # No capabilities set, allow all
    
    filtered = []
    for material in materials:
        required = material.required_capability_ids
        if not required:
            filtered.append(material)
            continue
        
        # Parse required capabilities (comma-separated)
        required_caps = [c.strip() for c in required.split(",") if c.strip()]
        
        # Check if user has all required capabilities
        has_all = all(cap in user_capabilities for cap in required_caps)
        if has_all:
            filtered.append(material)
    
    return filtered


def filter_materials_by_range(
    materials: list,
    user_range_low: str,
    user_range_high: str
) -> list:
    """
    Filter materials to only those within user's comfortable range.
    """
    if not user_range_low or not user_range_high:
        return materials
    
    return [
        m for m in materials 
        if check_material_in_range(m.original_key_center, user_range_low, user_range_high)
    ]


# =============================================================================
# KEY FILTERING BY USER RANGE
# =============================================================================

# Pitch content for each key when transposing - estimates the range shift
# Positive = higher, Negative = lower (relative to C)
KEY_TRANSPOSITION_OFFSET = {
    "C": 0, "C#": 1, "Db": 1, "D": 2, "D#": 3, "Eb": 3,
    "E": 4, "F": 5, "F#": 6, "Gb": 6, "G": 7, "G#": 8,
    "Ab": 8, "A": 9, "A#": 10, "Bb": 10, "B": 11,
}


def estimate_material_pitch_range(
    material,
    target_key: str,
    original_key: str = None
) -> tuple:
    """
    Estimate the pitch range (low, high) in MIDI when material is transposed.
    
    This uses a simplified model based on pitch_ref_json if available,
    or estimates based on key transposition from original.
    
    Args:
        material: Material object with optional pitch_low_stored, pitch_high_stored
        target_key: Key to transpose to (e.g., "G", "Bb")
        original_key: Original key center (defaults to material.original_key_center)
    
    Returns:
        (low_midi, high_midi) tuple of estimated pitch range
    """
    import json
    
    # Default range if no stored data (assume typical melody range)
    default_low = note_to_midi("C4")  # MIDI 60
    default_high = note_to_midi("C5")  # MIDI 72
    
    # Try to get stored pitch range from material
    stored_low = getattr(material, 'pitch_low_stored', None)
    stored_high = getattr(material, 'pitch_high_stored', None)
    
    if stored_low and stored_high:
        base_low = note_to_midi(stored_low)
        base_high = note_to_midi(stored_high)
    else:
        # Try pitch_ref_json for range info
        try:
            if material.pitch_ref_json:
                ref = json.loads(material.pitch_ref_json)
                if ref.get("low") and ref.get("high"):
                    base_low = note_to_midi(ref["low"])
                    base_high = note_to_midi(ref["high"])
                else:
                    base_low, base_high = default_low, default_high
            else:
                base_low, base_high = default_low, default_high
        except:
            base_low, base_high = default_low, default_high
    
    # Calculate transposition offset
    original = original_key or (material.original_key_center if material else None) or "C major"
    original_tonic = original.split()[0].strip() if original else "C"
    target_tonic = target_key.split()[0].strip() if target_key else "C"
    
    original_offset = KEY_TRANSPOSITION_OFFSET.get(original_tonic, 0)
    target_offset = KEY_TRANSPOSITION_OFFSET.get(target_tonic, 0)
    
    # Transposition shift (keep within octave to avoid extreme shifts)
    shift = target_offset - original_offset
    if shift > 6:
        shift -= 12  # Transpose down instead of way up
    elif shift < -6:
        shift += 12  # Transpose up instead of way down
    
    return (base_low + shift, base_high + shift)


def filter_keys_by_range(
    allowed_keys: list,
    material,
    user_range_low: str,
    user_range_high: str,
    original_key: str = None
) -> list:
    """
    Filter a list of allowed keys to only those playable within user's range.
    
    Per spec: "For each material: 1) Generate candidate keys, 2) Transpose pitch set,
    3) Filter keys inside comfort range, 4) Select playable keys only."
    
    Args:
        allowed_keys: List of key strings (e.g., ["C", "G", "F", "Bb"])
        material: Material object for pitch range estimation
        user_range_low: User's comfortable low note (e.g., "Bb2")
        user_range_high: User's comfortable high note (e.g., "G5")
        original_key: Material's original key (optional)
    
    Returns:
        List of keys that fit within user's comfortable range
    """
    if not user_range_low or not user_range_high:
        return allowed_keys  # No range constraint
    
    if not allowed_keys:
        return []
    
    user_low_midi = note_to_midi(user_range_low)
    user_high_midi = note_to_midi(user_range_high)
    
    playable_keys = []
    for key in allowed_keys:
        mat_low, mat_high = estimate_material_pitch_range(material, key, original_key)
        
        # Key is playable if material range fits within user range
        # Allow small leeway (1 semitone) for passing tones
        if mat_low >= (user_low_midi - 1) and mat_high <= (user_high_midi + 1):
            playable_keys.append(key)
    
    return playable_keys


def select_key_for_mini_session(
    material,
    user_range_low: str,
    user_range_high: str,
    used_keys: set = None,
    prefer_original: bool = True
) -> str:
    """
    Select an appropriate key for a mini-session.
    
    Priority:
    1. Original key (if fits in range and prefer_original=True)
    2. Random key from allowed_keys that fits in range
    3. Original key (fallback, for listen/sing-only mode)
    
    Args:
        material: Material object with allowed_keys
        user_range_low: User's comfortable low note
        user_range_high: User's comfortable high note
        used_keys: Set of keys already used this session (anti-repetition)
        prefer_original: Whether to prefer the original key
        
    Returns:
        Selected key string, or original_key_center if nothing fits
    """
    import random
    
    if used_keys is None:
        used_keys = set()
    
    original_key = material.original_key_center or "C major"
    original_tonic = original_key.split()[0].strip() if original_key else "C"
    
    # Parse allowed_keys from material
    allowed_keys = []
    if material.allowed_keys:
        allowed_keys = [k.strip() for k in material.allowed_keys.split(",") if k.strip()]
    
    if not allowed_keys:
        allowed_keys = [original_tonic]
    
    # Filter keys by user's range
    playable_keys = filter_keys_by_range(
        allowed_keys, material, user_range_low, user_range_high, original_key
    )
    
    # If nothing is playable, return original (will be listen/sing-only mode)
    if not playable_keys:
        return original_key  # Caller should handle this case
    
    # Remove already-used keys for anti-repetition
    fresh_keys = [k for k in playable_keys if k not in used_keys]
    if not fresh_keys:
        fresh_keys = playable_keys  # Reset if all used
    
    # Prefer original key if requested and available
    if prefer_original and original_tonic in fresh_keys:
        return f"{original_tonic} major"  # Append mode for consistency
    
    # Random selection from playable keys
    selected = random.choice(fresh_keys)
    return f"{selected} major"


def get_goals_for_fatigue(fatigue_level: int) -> List[str]:
    """
    Get appropriate goal types based on fatigue level.
    
    Fatigue model:
    - Level 1-2: All goals available (normal operation)
    - Level 3-4: Avoid goals that could cause bad habits (no range, reduce intensity)
    - Level 5: Ear-only or light playing (user should be prompted first)
    """
    all_goals = list(CURRICULUM_TEMPLATES.keys())
    
    # Goals that risk bad habit formation when fatigued
    high_intensity_goals = ["range_expansion", "tempo_build", "articulation_development"]
    
    if fatigue_level <= 2:
        # Normal operation - all goals available
        return all_goals
    elif fatigue_level <= 4:
        # Fatigue 3-4: Avoid goals that could cause bad habits
        # Allow ear-first and light playing goals
        safe_goals = [g for g in all_goals if g not in high_intensity_goals]
        return safe_goals if safe_goals else ["learn_by_ear", "musical_phrase_flow"]
    else:
        # Fatigue 5: Ear-only or very light work
        # User should have been prompted before reaching this
        return ["learn_by_ear"]


def insert_recovery_steps(steps: List[Dict], after_play_count: int = 2) -> List[Dict]:
    """
    Insert RECOVERY steps after every N PLAY steps.
    
    Range safety: mandatory recovery blocks after range work.
    """
    result = []
    play_count = 0
    
    for step in steps:
        result.append(step)
        if step["step_type"] == "PLAY":
            play_count += 1
            if play_count >= after_play_count:
                # Insert recovery
                recovery_idx = len(result)
                result.append({
                    "step_index": recovery_idx,
                    "step_type": "RECOVERY",
                    "instruction": "Take a moment to breathe and release tension.",
                    "prompt": "Let go of any physical tension. Breathe naturally.",
                    "is_completed": False,
                    "rating": None,
                    "notes": None
                })
                play_count = 0
    
    # Re-index steps
    for idx, step in enumerate(result):
        step["step_index"] = idx
    
    return result


# =============================================================================
# MICRO-TEACHING BLOCKS
# =============================================================================

# Template for capability introduction (mini-lesson)
CAPABILITY_LESSON_TEMPLATE = [
    CurriculumStepData("LISTEN", "Listen to this example of {capability_name}."),
    CurriculumStepData("EXPLAIN", "Read the explanation below to understand {capability_name}."),
    CurriculumStepData("VISUAL", "Look at the notation example for {capability_name}."),
    CurriculumStepData("TRY_IT", "Try it yourself - apply this concept."),
    CurriculumStepData("QUIZ", "Quick check - show you understand {capability_name}."),
]


def should_introduce_capability(
    user_known_count: int,
    sessions_since_last_intro: int,
    user_quiz_pass_rate: float = 0.8
) -> bool:
    """
    Determine if it's time to introduce a new capability.
    
    Pacing strategy:
    - Early on (< 10 known): introduce frequently (every 2-3 sessions)
    - Mid journey (10-20 known): introduce less often (every 4-5 sessions)
    - Later (20+ known): introduce sparingly (every 6-8 sessions)
    
    Args:
        user_known_count: How many capabilities user already knows
        sessions_since_last_intro: Sessions since last capability introduction
        user_quiz_pass_rate: User's quiz success rate (affects pacing)
        
    Returns:
        True if it's time to introduce a new capability
    """
    # Adjust base frequency by knowledge level
    if user_known_count < 10:
        # Rapid acquisition phase - introduce often
        intro_frequency = 2
    elif user_known_count < 20:
        # Building phase - moderate pace
        intro_frequency = 4
    else:
        # Reinforcement phase - slower pace
        intro_frequency = 6
    
    # Adjust based on quiz performance (struggling users get fewer intros)
    if user_quiz_pass_rate < 0.6:
        intro_frequency += 2  # Slow down if struggling
    
    return sessions_since_last_intro >= intro_frequency


def get_next_capability_to_introduce(
    user_known_caps: List[str],
    all_caps_ordered: List[dict]
) -> Optional[dict]:
    """
    Get the next capability to introduce based on sequence order.
    
    Args:
        user_known_caps: List of capability names user already knows
        all_caps_ordered: All capabilities ordered by sequence_order
        
    Returns:
        Next capability dict to introduce, or None if all known
    """
    for cap in sorted(all_caps_ordered, key=lambda c: c.get("sequence_order", 999)):
        if cap["name"] not in user_known_caps:
            # Must have teaching content to be introduceable
            if cap.get("explanation"):
                return cap
    return None


def generate_capability_lesson_steps(
    capability: dict
) -> List[Dict]:
    """
    Generate curriculum steps for a capability introduction mini-lesson.
    
    Flow: LISTEN → EXPLAIN → VISUAL → TRY_IT → QUIZ
    
    Args:
        capability: Capability dict with teaching content
        
    Returns:
        List of step dictionaries for the mini-lesson
    """
    cap_name = capability.get("display_name", capability["name"])
    steps = []
    
    idx = 0
    
    # Step 1: LISTEN (if audio available)
    if capability.get("audio_example_url"):
        steps.append({
            "step_index": idx,
            "step_type": "LISTEN",
            "instruction": f"Listen to this example of {cap_name}.",
            "prompt": f"Pay attention to the characteristic sound of {cap_name}.",
            "is_completed": False,
            "audio_url": capability["audio_example_url"],
            "rating": None,
            "notes": None
        })
        idx += 1
    
    # Step 2: EXPLAIN (always present if we're introducing)
    steps.append({
        "step_index": idx,
        "step_type": "EXPLAIN",
        "instruction": f"Learn about {cap_name}",
        "prompt": capability.get("explanation", f"Understanding {cap_name} in music."),
        "is_completed": False,
        "rating": None,
        "notes": None
    })
    idx += 1
    
    # Step 3: VISUAL (if image available)
    if capability.get("visual_example_url"):
        steps.append({
            "step_index": idx,
            "step_type": "VISUAL",
            "instruction": f"See how {cap_name} looks in notation.",
            "prompt": "Look at the symbol and memorize its appearance.",
            "is_completed": False,
            "visual_url": capability["visual_example_url"],
            "rating": None,
            "notes": None
        })
        idx += 1
    
    # Step 4: TRY_IT (light practice application)
    steps.append({
        "step_index": idx,
        "step_type": "TRY_IT",
        "instruction": f"Try applying {cap_name} yourself.",
        "prompt": f"Experiment with {cap_name} - no pressure, just explore.",
        "is_completed": False,
        "rating": None,
        "notes": None
    })
    idx += 1
    
    # Step 5: QUIZ (if quiz available)
    if capability.get("quiz_question"):
        steps.append({
            "step_index": idx,
            "step_type": "QUIZ",
            "instruction": capability["quiz_question"],
            "prompt": "Select the correct answer.",
            "is_completed": False,
            "quiz_type": capability.get("quiz_type", "visual_mc"),
            "quiz_options": capability.get("quiz_options"),
            "quiz_answer": capability.get("quiz_answer"),
            "rating": None,
            "notes": None
        })
        idx += 1
    
    return steps


def get_capabilities_for_material(
    material_scaffolding_caps: str,
    user_known_caps: List[str]
) -> List[str]:
    """
    Get unknown scaffolding capabilities for a material.
    
    These are capabilities referenced in the material that the user
    hasn't been formally introduced to yet.
    
    Args:
        material_scaffolding_caps: Comma-separated scaffolding capability IDs
        user_known_caps: Capabilities user already knows
        
    Returns:
        List of capability names that need introduction
    """
    if not material_scaffolding_caps:
        return []
    
    scaffolding = [c.strip() for c in material_scaffolding_caps.split(",") if c.strip()]
    unknown = [c for c in scaffolding if c not in user_known_caps]
    return unknown


def get_help_menu_capabilities(
    material_required_caps: str,
    material_scaffolding_caps: str
) -> List[str]:
    """
    Get all capabilities referenced in a material for the help menu.
    
    This allows users to review any capability they encounter,
    even ones they've already learned.
    
    Args:
        material_required_caps: Comma-separated required capability IDs
        material_scaffolding_caps: Comma-separated scaffolding capability IDs
        
    Returns:
        List of all capability names relevant to this material
    """
    caps = []
    
    if material_required_caps:
        caps.extend([c.strip() for c in material_required_caps.split(",") if c.strip()])
    if material_scaffolding_caps:
        caps.extend([c.strip() for c in material_scaffolding_caps.split(",") if c.strip()])
    
    return list(set(caps))  # Dedupe

