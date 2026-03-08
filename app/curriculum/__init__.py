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

# Types and constants
from .types import (
    CurriculumStepData,
    JourneyMetrics,
    CURRICULUM_TEMPLATES,
    DEFAULT_CURRICULUM,
    CAPABILITY_LESSON_TEMPLATE,
    JOURNEY_STAGES,
)

# Utility functions
from .utils import (
    NOTE_TO_MIDI,
    KEY_TRANSPOSITION_OFFSET,
    note_to_midi,
    midi_to_note,
)

# Material and key filtering
from .filters import (
    check_material_in_range,
    filter_materials_by_capabilities,
    filter_materials_by_range,
    estimate_material_pitch_range,
    filter_keys_by_range,
    select_key_for_mini_session,
)

# Step generators
from .generators import (
    generate_curriculum_steps,
    get_goals_for_fatigue,
    insert_recovery_steps,
)

# Capability teaching
from .teaching import (
    should_introduce_capability,
    get_next_capability_to_introduce,
    generate_capability_lesson_steps,
    get_capabilities_for_material,
    get_help_menu_capabilities,
)

# Journey stage estimation
from .journey import (
    estimate_journey_stage,
    get_stage_adaptive_weights,
)


__all__ = [
    # Types
    "CurriculumStepData",
    "JourneyMetrics",
    "CURRICULUM_TEMPLATES",
    "DEFAULT_CURRICULUM",
    "CAPABILITY_LESSON_TEMPLATE",
    "JOURNEY_STAGES",
    # Utils
    "NOTE_TO_MIDI",
    "KEY_TRANSPOSITION_OFFSET",
    "note_to_midi",
    "midi_to_note",
    # Filters
    "check_material_in_range",
    "filter_materials_by_capabilities",
    "filter_materials_by_range",
    "estimate_material_pitch_range",
    "filter_keys_by_range",
    "select_key_for_mini_session",
    # Generators
    "generate_curriculum_steps",
    "get_goals_for_fatigue",
    "insert_recovery_steps",
    # Teaching
    "should_introduce_capability",
    "get_next_capability_to_introduce",
    "generate_capability_lesson_steps",
    "get_capabilities_for_material",
    "get_help_menu_capabilities",
    # Journey
    "estimate_journey_stage",
    "get_stage_adaptive_weights",
]
