"""
Type definitions and constants for curriculum generation.

Contains dataclasses, templates, and constants used throughout
the curriculum module.
"""

from dataclasses import dataclass
from typing import Optional


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


# Template for capability introduction (mini-lesson)
CAPABILITY_LESSON_TEMPLATE = [
    CurriculumStepData("LISTEN", "Listen to this example of {capability_name}."),
    CurriculumStepData("EXPLAIN", "Read the explanation below to understand {capability_name}."),
    CurriculumStepData("VISUAL", "Look at the notation example for {capability_name}."),
    CurriculumStepData("TRY_IT", "Try it yourself - apply this concept."),
    CurriculumStepData("QUIZ", "Quick check - show you understand {capability_name}."),
]


# Journey stages from the User Journey Spec
JOURNEY_STAGES = {
    1: {
        "name": "Arrival",
        "description": "New user discovering the app, first sessions"
    },
    2: {
        "name": "Orientation",
        "description": "Learning the Sound First method, discovering listening-first approach"
    },
    3: {
        "name": "Guided Growth",
        "description": "Building repertoire, focus cards rotating, noticing improvement"
    },
    4: {
        "name": "Expanding Musical Identity",
        "description": "Internal hearing developing, experimenting musically, self-correcting"
    },
    5: {
        "name": "Independent Fluency",
        "description": "Choosing materials intentionally, using self-directed mode frequently"
    },
    6: {
        "name": "Lifelong Practice Companion",
        "description": "App as infrastructure, maintains technique, learns new repertoire quickly"
    }
}


@dataclass
class JourneyMetrics:
    """Metrics used to estimate journey stage."""
    total_sessions: int = 0
    total_attempts: int = 0
    days_since_first_session: int = 0
    average_rating: float = 0.0
    average_fatigue: float = 3.0
    mastered_count: int = 0  # Materials with interval > 30 days
    familiar_count: int = 0  # Materials with interval 14-30 days
    stabilizing_count: int = 0  # Materials with interval 3-14 days
    learning_count: int = 0  # Materials with interval <= 3 days
    unique_keys_practiced: int = 0
    capabilities_introduced: int = 0
    self_directed_sessions: int = 0
    current_streak_days: int = 0
