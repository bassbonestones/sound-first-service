"""
Session generation service.

Handles business logic for practice session generation, separating it from HTTP concerns.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set, Any
import random
import json

from sqlalchemy.orm import Session as DbSession

from app.models.core import User, Material, FocusCard, PracticeSession, MiniSession
from app.curriculum import (
    filter_materials_by_range,
    filter_keys_by_range,
    select_key_for_mini_session,
    get_goals_for_fatigue,
)
from app.session_config import (
    select_capability,
    select_difficulty,
    select_intensity,
    select_novelty_or_reinforcement,
    estimate_mini_session_duration,
    should_show_notation,
)
from app.spaced_repetition import (
    build_sr_item_from_db,
    get_capability_weight_adjustment,
)
from app.utils.json_helpers import parse_focus_card_json_field


# --- Constants ---
GOAL_LABEL_MAP = {
    "repertoire_fluency": "Repertoire Fluency",
    "fluency_through_keys": "Fluency Through Keys",
    "range_expansion": "Range Expansion",
    "articulation_development": "Articulation Development",
    "tempo_build": "Tempo Building",
    "dynamic_control": "Dynamic Control",
    "learn_by_ear": "Learn By Ear",
    "musical_phrase_flow": "Musical Phrase Flow",
}

CAPABILITY_GOAL_MAP = {
    "repertoire_fluency": ["repertoire_fluency", "fluency_through_keys", "musical_phrase_flow"],
    "technique": ["articulation_development", "tempo_build"],
    "range_expansion": ["range_expansion"],
    "rhythm": ["tempo_build", "repertoire_fluency"],
    "ear_training": ["learn_by_ear", "musical_phrase_flow"],
    "articulation": ["articulation_development", "dynamic_control"],
}

CATEGORY_FOR_CAPABILITY = {
    "repertoire_fluency": "MUSICIANSHIP",
    "technique": "PHYSICAL",
    "range_expansion": "PHYSICAL",
    "rhythm": "TIME",
    "ear_training": "LISTENING",
    "articulation": "PHYSICAL",
}


@dataclass
class MiniSessionData:
    """Data for a single mini-session within a practice session."""
    material_id: int
    material_title: str
    focus_card_id: int
    focus_card_name: str
    focus_card_description: str
    focus_card_category: str
    focus_card_attention_cue: str
    focus_card_micro_cues: List[str]
    focus_card_prompts: Dict[str, Any]
    goal_type: str
    goal_label: str
    show_notation: bool
    target_key: str
    original_key_center: str
    resolved_musicxml: str
    starting_pitch: str


@dataclass
class SessionState:
    """Tracks state during session generation."""
    time_remaining: float
    used_materials: Set[int] = field(default_factory=set)
    used_focus_cards: Set[int] = field(default_factory=set)
    recent_capabilities: List[str] = field(default_factory=list)
    recent_keys: Set[str] = field(default_factory=set)
    mini_sessions: List[MiniSessionData] = field(default_factory=list)
    mini_session_records: List[MiniSession] = field(default_factory=list)


class SessionService:
    """Service for generating and managing practice sessions."""
    
    MAX_MINI_SESSIONS = 10
    
    @staticmethod
    def get_starting_pitch(material: Material, target_key: Optional[str]) -> str:
        """Determine starting pitch based on material's pitch reference type."""
        if material.pitch_reference_type == "TONAL":
            try:
                ref = json.loads(material.pitch_ref_json) if material.pitch_ref_json else {}
                tonic = ref.get("tonic", "C")
                return f"{tonic}4"
            except Exception:
                return "C4"
        elif material.pitch_reference_type == "ANCHOR_INTERVAL":
            try:
                if target_key:
                    tonic = target_key.split()[0]
                    return f"{tonic}4" if tonic else "C4"
            except Exception:
                pass
            return "C4"
        return "C4"
    
    @classmethod
    def build_mini_session_data(
        cls,
        material: Material,
        focus_card: FocusCard,
        goal_type: str,
        target_key: Optional[str] = None
    ) -> MiniSessionData:
        """Build a MiniSessionData from material and focus card."""
        if not target_key:
            target_key = material.original_key_center or "C major"
        
        prompts_data = parse_focus_card_json_field(focus_card.prompts)
        
        return MiniSessionData(
            material_id=material.id,
            material_title=material.title,
            focus_card_id=focus_card.id,
            focus_card_name=focus_card.name,
            focus_card_description=focus_card.description or "",
            focus_card_category=focus_card.category or "",
            focus_card_attention_cue=focus_card.attention_cue or "",
            focus_card_micro_cues=parse_focus_card_json_field(focus_card.micro_cues),
            focus_card_prompts=prompts_data if isinstance(prompts_data, dict) else {},
            goal_type=goal_type,
            goal_label=GOAL_LABEL_MAP.get(goal_type, goal_type.replace("_", " ").title()),
            show_notation=random.random() < 0.2,
            target_key=target_key,
            original_key_center=material.original_key_center or "C major",
            resolved_musicxml=material.musicxml_canonical or "<musicxml/>",
            starting_pitch=cls.get_starting_pitch(material, target_key)
        )
    
    @classmethod
    def select_material(
        cls,
        materials: List[Material],
        state: SessionState,
        attempt_history: Dict[int, List[Dict]],
        selection_mode: str,
        user: Optional[User] = None
    ) -> Material:
        """Select material using spaced repetition and anti-repetition logic."""
        # Filter to unused materials
        available = [m for m in materials if m.id not in state.used_materials]
        if not available:
            available = materials  # Fallback
        
        # Filter by user's range if available
        if user and user.range_low and user.range_high:
            range_filtered = filter_materials_by_range(available, user.range_low, user.range_high)
            if range_filtered:
                available = range_filtered
        
        # Build spaced repetition items
        sr_items = {}
        for m in available:
            mat_attempts = attempt_history.get(m.id, [])
            sr_item = build_sr_item_from_db(m.id, mat_attempts)
            sr_items[m.id] = sr_item
        
        if selection_mode == "novelty":
            # Prefer materials never reviewed (new)
            new_materials = [m for m in available if sr_items[m.id].repetitions == 0]
            if new_materials:
                return random.choice(new_materials)
            return random.choice(available)
        else:
            # Reinforcement: use SR weighting (due items get higher weight)
            weights = [get_capability_weight_adjustment(sr_items[m.id]) for m in available]
            total_weight = sum(weights)
            if total_weight > 0:
                probs = [w / total_weight for w in weights]
                return random.choices(available, weights=probs, k=1)[0]
            return random.choice(available)
    
    @classmethod
    def select_goal(cls, capability: str, fatigue: int) -> str:
        """Select a goal based on capability and fatigue."""
        available_goals = get_goals_for_fatigue(fatigue)
        preferred_goals = CAPABILITY_GOAL_MAP.get(capability, list(GOAL_LABEL_MAP.keys()))
        
        # Intersect with fatigue-appropriate goals
        valid_goals = [g for g in preferred_goals if g in available_goals]
        if not valid_goals:
            valid_goals = available_goals
        
        return random.choice(valid_goals)
    
    @classmethod
    def select_focus_card(
        cls,
        focus_cards: List[FocusCard],
        capability: str,
        state: SessionState
    ) -> FocusCard:
        """Select a focus card, preferring matches to capability category."""
        preferred_category = CATEGORY_FOR_CAPABILITY.get(capability)
        
        available = [fc for fc in focus_cards if fc.id not in state.used_focus_cards]
        if not available:
            available = focus_cards
        
        # Prefer focus cards matching category
        category_matched = [fc for fc in available if fc.category == preferred_category]
        if category_matched:
            return random.choice(category_matched)
        return random.choice(available)
    
    @classmethod
    def generate_mini_session(
        cls,
        materials: List[Material],
        focus_cards: List[FocusCard],
        state: SessionState,
        attempt_history: Dict[int, List[Dict]],
        user: Optional[User],
        fatigue: int
    ) -> Optional[MiniSessionData]:
        """Generate a single mini-session."""
        if state.time_remaining <= 0:
            return None
        
        # Step 1: Decide novelty vs reinforcement
        selection_mode = select_novelty_or_reinforcement()
        
        # Step 2: Choose capability bucket
        capability = select_capability(
            fatigue=fatigue,
            recent_capabilities=state.recent_capabilities,
            time_remaining=state.time_remaining
        )
        state.recent_capabilities.append(capability)
        
        # Step 3: Choose difficulty (for future use)
        _ = select_difficulty()
        
        # Step 4: Select intensity
        intensity = select_intensity(state.time_remaining)
        
        # Step 5: Select material
        material = cls.select_material(materials, state, attempt_history, selection_mode, user)
        state.used_materials.add(material.id)
        
        # Step 6: Choose goal
        goal_type = cls.select_goal(capability, fatigue)
        
        # Step 7: Choose focus card
        focus_card = cls.select_focus_card(focus_cards, capability, state)
        state.used_focus_cards.add(focus_card.id)
        
        # Step 8: Select key
        user_range_low = user.range_low if user else None
        user_range_high = user.range_high if user else None
        
        selected_key = select_key_for_mini_session(
            material=material,
            user_range_low=user_range_low,
            user_range_high=user_range_high,
            used_keys=state.recent_keys,
            prefer_original=(selection_mode == "reinforcement")
        )
        state.recent_keys.add(selected_key.split()[0])
        
        # Check if key is playable
        playable_keys = filter_keys_by_range(
            [k.strip() for k in (material.allowed_keys or "C").split(",")],
            material,
            user_range_low,
            user_range_high
        )
        mode_listen_only = len(playable_keys) == 0
        
        # Build mini-session
        mini_session = cls.build_mini_session_data(material, focus_card, goal_type, target_key=selected_key)
        mini_session.show_notation = should_show_notation()
        
        if mode_listen_only:
            mini_session.show_notation = False
        
        # Create DB record
        mini_record = MiniSession(
            material_id=material.id,
            key=mini_session.target_key,
            focus_card_id=focus_card.id,
            goal_type=goal_type
        )
        state.mini_session_records.append(mini_record)
        state.mini_sessions.append(mini_session)
        
        # Update time
        estimated_duration = estimate_mini_session_duration(capability, intensity)
        state.time_remaining -= estimated_duration
        
        return mini_session
    
    @classmethod
    def build_attempt_history(cls, attempts: List) -> Dict[int, List[Dict]]:
        """Build attempt history dict from database records."""
        history = {}
        for a in attempts:
            if a.material_id not in history:
                history[a.material_id] = []
            history[a.material_id].append({
                "rating": a.rating,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            })
        return history


# Module-level singleton for convenience
_session_service = None


def get_session_service() -> SessionService:
    """Get or create the session service singleton."""
    global _session_service
    if _session_service is None:
        _session_service = SessionService()
    return _session_service
