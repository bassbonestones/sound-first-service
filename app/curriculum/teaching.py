"""
Capability teaching and mini-lesson generation.

Functions for introducing new capabilities to users through
structured micro-teaching blocks.
"""

from typing import List, Dict, Optional


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
