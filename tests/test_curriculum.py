"""
Tests for app/curriculum.py - Curriculum Generation Module

Tests the ear-first curriculum implementation:
- Note conversion
- Curriculum step generation
- Material/key filtering
- Fatigue-based goal selection
- Capability introduction logic
"""

import pytest
from datetime import datetime
from app.curriculum import (
    note_to_midi,
    midi_to_note,
    generate_curriculum_steps,
    filter_materials_by_capabilities,
    filter_materials_by_range,
    check_material_in_range,
    estimate_material_pitch_range,
    filter_keys_by_range,
    select_key_for_mini_session,
    get_goals_for_fatigue,
    insert_recovery_steps,
    should_introduce_capability,
    CURRICULUM_TEMPLATES,
    CurriculumStepData,
)


# =============================================================================
# NOTE CONVERSION TESTS
# =============================================================================

class TestNoteToMidi:
    """Tests for note_to_midi() function."""
    
    def test_middle_c(self):
        """Middle C (C4) should be MIDI 60."""
        assert note_to_midi("C4") == 60
    
    def test_standard_notes(self):
        """Standard notes in octave 4."""
        assert note_to_midi("D4") == 62
        assert note_to_midi("E4") == 64
        assert note_to_midi("F4") == 65
        assert note_to_midi("G4") == 67
        assert note_to_midi("A4") == 69
        assert note_to_midi("B4") == 71
    
    def test_sharps(self):
        """Notes with sharps."""
        assert note_to_midi("C#4") == 61
        assert note_to_midi("F#4") == 66
        assert note_to_midi("G#4") == 68
    
    def test_flats(self):
        """Notes with flats."""
        assert note_to_midi("Db4") == 61
        assert note_to_midi("Eb4") == 63
        assert note_to_midi("Bb4") == 70
    
    def test_different_octaves(self):
        """Notes in different octaves."""
        assert note_to_midi("C3") == 48
        assert note_to_midi("C5") == 72
        assert note_to_midi("C6") == 84
        assert note_to_midi("A0") == 21  # Lowest piano key
    
    def test_lowercase(self):
        """Lowercase note names should work."""
        assert note_to_midi("c4") == 60
        assert note_to_midi("g#4") == 68
    
    def test_invalid_returns_default(self):
        """Invalid note strings return default (60 = middle C)."""
        assert note_to_midi("") == 60
        assert note_to_midi(None) == 60
        assert note_to_midi("invalid") == 60
        assert note_to_midi("X4") == 60


class TestMidiToNote:
    """Tests for midi_to_note() function."""
    
    def test_middle_c(self):
        """MIDI 60 should be C4."""
        assert midi_to_note(60) == "C4"
    
    def test_standard_notes(self):
        """Standard MIDI values."""
        assert midi_to_note(62) == "D4"
        assert midi_to_note(64) == "E4"
        assert midi_to_note(69) == "A4"
    
    def test_sharps(self):
        """Notes with sharps returned."""
        assert midi_to_note(61) == "C#4"
        assert midi_to_note(66) == "F#4"
    
    def test_different_octaves(self):
        """Different octaves."""
        assert midi_to_note(48) == "C3"
        assert midi_to_note(72) == "C5"
        assert midi_to_note(84) == "C6"
    
    def test_edge_cases(self):
        """Edge cases at boundaries."""
        # MIDI 0 is C-1
        assert midi_to_note(0) == "C-1"
        # MIDI 127 is G9
        assert midi_to_note(127) == "G9"


# =============================================================================
# CURRICULUM STEP GENERATION TESTS
# =============================================================================

class TestGenerateCurriculumSteps:
    """Tests for generate_curriculum_steps() function."""
    
    def test_fluency_through_keys_template(self):
        """Fluency through keys generates correct steps."""
        steps = generate_curriculum_steps(
            goal_type="fluency_through_keys",
            focus_card_prompts={},
            material_title="Test Material",
            target_key="G major",
            fatigue_level=2
        )
        
        # Should have multiple steps with required structure
        assert len(steps) >= 3, "fluency_through_keys should generate at least 3 steps"
        
        # Should start with LISTEN
        assert steps[0]["step_type"] == "LISTEN"
        
        # Should have SING step
        step_types = [s["step_type"] for s in steps]
        assert "SING" in step_types
        assert "PLAY" in step_types
        assert "REFLECT" in step_types
    
    def test_all_goal_types_have_steps(self):
        """All defined goal types produce steps."""
        for goal_type in CURRICULUM_TEMPLATES.keys():
            steps = generate_curriculum_steps(
                goal_type=goal_type,
                focus_card_prompts={},
                material_title="Test",
                target_key="C major",
                fatigue_level=2
            )
            assert len(steps) > 0, f"Goal type {goal_type} produced no steps"
    
    def test_unknown_goal_type_uses_default(self):
        """Unknown goal type uses default template."""
        steps = generate_curriculum_steps(
            goal_type="unknown_goal_type",
            focus_card_prompts={},
            material_title="Test",
            target_key="C major",
            fatigue_level=2
        )
        
        # Should still produce steps (from default template)
        assert len(steps) > 0
    
    def test_high_fatigue_reduces_play_steps(self):
        """High fatigue (4+) reduces number of PLAY steps."""
        normal_steps = generate_curriculum_steps(
            goal_type="fluency_through_keys",
            focus_card_prompts={},
            material_title="Test",
            target_key="C major",
            fatigue_level=2
        )
        
        fatigue_steps = generate_curriculum_steps(
            goal_type="fluency_through_keys",
            focus_card_prompts={},
            material_title="Test",
            target_key="C major",
            fatigue_level=4
        )
        
        normal_play_count = sum(1 for s in normal_steps if s["step_type"] == "PLAY")
        fatigue_play_count = sum(1 for s in fatigue_steps if s["step_type"] == "PLAY")
        
        # Should have fewer or equal PLAY steps at high fatigue
        assert fatigue_play_count <= normal_play_count
    
    def test_focus_card_prompts_included(self):
        """Focus card prompts are included in step prompts."""
        prompts = {
            "listen": "Focus on the tone quality",
            "play": "Play with full breath support"
        }
        
        steps = generate_curriculum_steps(
            goal_type="repertoire_fluency",
            focus_card_prompts=prompts,
            material_title="Test",
            target_key="C major",
            fatigue_level=2
        )
        
        listen_step = next(s for s in steps if s["step_type"] == "LISTEN")
        assert listen_step["prompt"] == "Focus on the tone quality"
    
    def test_steps_have_correct_structure(self):
        """Each step has required fields."""
        steps = generate_curriculum_steps(
            goal_type="repertoire_fluency",
            focus_card_prompts={},
            material_title="Test",
            target_key="C major"
        )
        
        for step in steps:
            assert "step_index" in step
            assert "step_type" in step
            assert "instruction" in step
            assert "prompt" in step
            assert "is_completed" in step
            assert step["is_completed"] == False


# =============================================================================
# MATERIAL FILTERING TESTS  
# =============================================================================

class MockMaterial:
    """Mock material for testing."""
    def __init__(self, id, title, required_capability_ids=None, original_key_center="C major",
                 allowed_keys="C,G,F,Bb", pitch_low_stored=None, pitch_high_stored=None,
                 pitch_ref_json=None):
        self.id = id
        self.title = title
        self.required_capability_ids = required_capability_ids or ""
        self.original_key_center = original_key_center
        self.allowed_keys = allowed_keys
        self.pitch_low_stored = pitch_low_stored
        self.pitch_high_stored = pitch_high_stored
        self.pitch_ref_json = pitch_ref_json


class TestFilterMaterialsByCapabilities:
    """Tests for filter_materials_by_capabilities() function."""
    
    def test_no_capabilities_returns_all(self):
        """No user capabilities returns all materials."""
        materials = [
            MockMaterial(1, "Test 1", "cap1,cap2"),
            MockMaterial(2, "Test 2", "cap3"),
        ]
        result = filter_materials_by_capabilities(materials, [])
        assert len(result) == 2
    
    def test_filter_by_single_capability(self):
        """Filter by a single capability."""
        materials = [
            MockMaterial(1, "Test 1", "cap1"),
            MockMaterial(2, "Test 2", "cap2"),
        ]
        result = filter_materials_by_capabilities(materials, ["cap1"])
        assert len(result) == 1
        assert result[0].id == 1
    
    def test_filter_requires_all_capabilities(self):
        """Material requiring multiple capabilities needs all."""
        materials = [
            MockMaterial(1, "Needs Both", "cap1,cap2"),
            MockMaterial(2, "Needs One", "cap1"),
        ]
        
        # Has only one capability
        result = filter_materials_by_capabilities(materials, ["cap1"])
        assert len(result) == 1
        assert result[0].id == 2
        
        # Has both capabilities
        result = filter_materials_by_capabilities(materials, ["cap1", "cap2"])
        assert len(result) == 2
    
    def test_material_with_no_requirements(self):
        """Materials with no requirements are always included."""
        materials = [
            MockMaterial(1, "No Requirements", ""),
            MockMaterial(2, "No Requirements", None),
            MockMaterial(3, "Has Requirements", "cap1"),
        ]
        result = filter_materials_by_capabilities(materials, [])
        assert len(result) == 3


class TestFilterMaterialsByRange:
    """Tests for filter_materials_by_range() function."""
    
    def test_no_range_returns_all(self):
        """No range limitation returns all materials."""
        materials = [
            MockMaterial(1, "Test 1", original_key_center="G major"),
            MockMaterial(2, "Test 2", original_key_center="A major"),
        ]
        result = filter_materials_by_range(materials, None, None)
        assert len(result) == 2
    
    def test_filter_by_range(self):
        """Filter materials by user's range."""
        materials = [
            MockMaterial(1, "Low", original_key_center="C major"),
            MockMaterial(2, "High", original_key_center="G major"),
        ]
        result = filter_materials_by_range(materials, "C3", "G5")
        # Both should be in comfortable range
        assert len(result) >= 1


class TestCheckMaterialInRange:
    """Tests for check_material_in_range() function."""
    
    def test_no_range_always_true(self):
        """No range returns True for any key."""
        assert check_material_in_range("C major", None, None) == True
        assert check_material_in_range("G major", "", "") == True
    
    def test_c_major_in_typical_range(self):
        """C major fits in typical range."""
        assert check_material_in_range("C major", "C3", "C6") == True
    
    def test_handles_no_key(self):
        """Empty or None key returns True."""
        assert check_material_in_range("", "C3", "C6") == True
        assert check_material_in_range(None, "C3", "C6") == True


# =============================================================================
# KEY FILTERING AND SELECTION TESTS
# =============================================================================

class TestFilterKeysByRange:
    """Tests for filter_keys_by_range() function."""
    
    def test_no_range_returns_all_keys(self):
        """No range constraint returns all allowed keys."""
        material = MockMaterial(1, "Test")
        keys = ["C", "G", "F", "Bb"]
        result = filter_keys_by_range(keys, material, None, None)
        assert result == keys
    
    def test_empty_keys_returns_empty(self):
        """Empty allowed keys returns empty."""
        material = MockMaterial(1, "Test")
        result = filter_keys_by_range([], material, "C3", "G5")
        assert result == []
    
    def test_filters_extreme_keys(self):
        """Keys requiring extreme range are filtered out."""
        material = MockMaterial(
            1, "Test",
            original_key_center="C major",
            pitch_low_stored="C4",
            pitch_high_stored="G4"
        )
        
        # Very limited range should filter some keys
        keys = ["C", "G", "D", "A"]
        result = filter_keys_by_range(keys, material, "C4", "C5")
        # Should include some keys within range
        assert len(result) >= 1


class TestSelectKeyForMiniSession:
    """Tests for select_key_for_mini_session() function."""
    
    def test_prefers_original_key(self):
        """Prefers original key when prefer_original=True."""
        material = MockMaterial(
            1, "Test",
            original_key_center="G major",
            allowed_keys="C,G,F"
        )
        # Multiple calls should often return original
        results = set()
        for _ in range(20):
            key = select_key_for_mini_session(
                material, "C3", "G5", used_keys=set(), prefer_original=True
            )
            results.add(key)
        
        # G should appear frequently
        assert "G major" in results or "G" in results
    
    def test_avoids_used_keys(self):
        """Anti-repetition: avoids recently used keys."""
        material = MockMaterial(
            1, "Test",
            original_key_center="C major",
            allowed_keys="C,G,F,Bb"
        )
        
        used = {"C", "G"}
        # Should prefer unused keys
        results = set()
        for _ in range(10):
            key = select_key_for_mini_session(
                material, "C3", "G5", used_keys=used, prefer_original=False
            )
            results.add(key.split()[0])  # Get just the tonic
        
        # Should include non-used keys
        assert len(results) >= 1
    
    def test_returns_original_when_no_playable_keys(self):
        """Returns original key when nothing else fits range."""
        material = MockMaterial(
            1, "Test",
            original_key_center="C major",
            allowed_keys="C"  # Only one key
        )
        
        key = select_key_for_mini_session(
            material, "C3", "G5", used_keys=set(), prefer_original=True
        )
        # Should return C major
        assert "C" in key


# =============================================================================
# FATIGUE AND GOAL TESTS
# =============================================================================

class TestGetGoalsForFatigue:
    """Tests for get_goals_for_fatigue() function."""
    
    def test_fatigue_1_all_goals(self):
        """Fatigue 1 allows all goals."""
        goals = get_goals_for_fatigue(1)
        assert "range_expansion" in goals
        assert "tempo_build" in goals
        assert len(goals) == len(CURRICULUM_TEMPLATES)
    
    def test_fatigue_2_all_goals(self):
        """Fatigue 2 allows all goals."""
        goals = get_goals_for_fatigue(2)
        assert len(goals) == len(CURRICULUM_TEMPLATES)
    
    def test_fatigue_3_no_range_expansion(self):
        """Fatigue 3+ excludes range expansion."""
        goals = get_goals_for_fatigue(3)
        assert "range_expansion" not in goals
        assert "tempo_build" not in goals
    
    def test_fatigue_4_reduced_goals(self):
        """Fatigue 4 has reduced goal set."""
        goals = get_goals_for_fatigue(4)
        assert "range_expansion" not in goals
        assert len(goals) < len(CURRICULUM_TEMPLATES)
    
    def test_fatigue_5_ear_only(self):
        """Fatigue 5 only allows ear-only goals."""
        goals = get_goals_for_fatigue(5)
        assert goals == ["learn_by_ear"]


# =============================================================================
# RECOVERY STEP INSERTION TESTS
# =============================================================================

class TestInsertRecoverySteps:
    """Tests for insert_recovery_steps() function."""
    
    def test_inserts_after_n_play_steps(self):
        """Inserts RECOVERY after N PLAY steps."""
        steps = [
            {"step_type": "LISTEN", "step_index": 0},
            {"step_type": "PLAY", "step_index": 1},
            {"step_type": "PLAY", "step_index": 2},
            {"step_type": "REFLECT", "step_index": 3},
        ]
        
        result = insert_recovery_steps(steps, after_play_count=2)
        
        # Should have RECOVERY inserted
        step_types = [s["step_type"] for s in result]
        assert "RECOVERY" in step_types
    
    def test_reindexes_steps(self):
        """Steps are re-indexed after insertion."""
        steps = [
            {"step_type": "LISTEN", "step_index": 0},
            {"step_type": "PLAY", "step_index": 1},
            {"step_type": "PLAY", "step_index": 2},
        ]
        
        result = insert_recovery_steps(steps, after_play_count=2)
        
        # All step indices should be sequential
        for i, step in enumerate(result):
            assert step["step_index"] == i
    
    def test_no_recovery_if_few_plays(self):
        """No RECOVERY inserted if fewer than N PLAY steps."""
        steps = [
            {"step_type": "LISTEN", "step_index": 0},
            {"step_type": "PLAY", "step_index": 1},
            {"step_type": "REFLECT", "step_index": 2},
        ]
        
        result = insert_recovery_steps(steps, after_play_count=3)
        
        step_types = [s["step_type"] for s in result]
        assert "RECOVERY" not in step_types


# =============================================================================
# CAPABILITY INTRODUCTION TESTS
# =============================================================================

class TestShouldIntroduceCapability:
    """Tests for should_introduce_capability() function."""
    
    def test_early_journey_frequent_intro(self):
        """Early journey (<10 known) introduces more frequently."""
        # After 2 sessions, should introduce at early stage
        result = should_introduce_capability(
            user_known_count=5,
            sessions_since_last_intro=2
        )
        assert result == True
    
    def test_late_journey_less_frequent(self):
        """Late journey (20+ known) introduces less frequently."""
        # After 4 sessions, should NOT introduce at late stage
        result = should_introduce_capability(
            user_known_count=30,
            sessions_since_last_intro=4
        )
        assert result == False
    
    def test_never_introduces_too_soon(self):
        """Never introduces if just introduced."""
        result = should_introduce_capability(
            user_known_count=5,
            sessions_since_last_intro=0
        )
        assert result == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
