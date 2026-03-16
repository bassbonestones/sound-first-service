"""
Curriculum step generation functions.

Contains functions for generating curriculum steps, handling fatigue,
and inserting recovery steps.
"""

from typing import Any, List, Dict

from .types import CURRICULUM_TEMPLATES, DEFAULT_CURRICULUM


def generate_curriculum_steps(
    goal_type: str,
    focus_card_prompts: Dict[str, Any],
    material_title: str,
    target_key: str,
    fatigue_level: int = 2
) -> List[Dict[str, Any]]:
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


def insert_recovery_steps(steps: List[Dict[str, Any]], after_play_count: int = 2) -> List[Dict[str, Any]]:
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
