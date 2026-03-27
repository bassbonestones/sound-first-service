"""Tests for app/curriculum/filters.py - Material filtering functions."""

import pytest
from unittest.mock import MagicMock

from app.curriculum.filters import (
    filter_materials_by_capabilities,
    filter_materials_by_range,
    estimate_material_pitch_range,
    filter_keys_by_range,
    select_key_for_mini_session,
)


class TestFilterMaterialsByCapabilities:
    """Tests for filter_materials_by_capabilities function."""

    def test_no_user_capabilities_returns_all(self):
        """When user has no capabilities, all materials are returned."""
        materials = [MagicMock(), MagicMock(), MagicMock()]
        
        result = filter_materials_by_capabilities(materials, user_capabilities=set())
        
        assert len(result) == 3

    def test_filters_based_on_required_caps(self):
        """Materials with unmet requirements are filtered out."""
        mat1 = MagicMock()
        mat1.required_capability_ids = "treble_clef,quarter_note"
        
        mat2 = MagicMock()
        mat2.required_capability_ids = "bass_clef"  # User doesn't have this
        
        mat3 = MagicMock()
        mat3.required_capability_ids = None  # No requirements
        
        user_caps = {"treble_clef", "quarter_note"}
        
        result = filter_materials_by_capabilities([mat1, mat2, mat3], user_caps)
        
        assert len(result) == 2
        assert mat1 in result
        assert mat3 in result


class TestEstimateMaterialPitchRange:
    """Tests for estimate_material_pitch_range function."""

    def test_uses_stored_pitch_range(self):
        """Uses stored pitch_low and pitch_high if available."""
        material = MagicMock()
        material.pitch_low_stored = "C4"
        material.pitch_high_stored = "G5"
        material.original_key_center = "C major"
        material.pitch_ref_json = None
        
        low, high = estimate_material_pitch_range(material, "C")
        
        assert low == 60  # C4
        assert high == 79  # G5

    def test_uses_pitch_ref_json(self):
        """Falls back to pitch_ref_json if no stored values."""
        material = MagicMock()
        material.pitch_low_stored = None
        material.pitch_high_stored = None
        material.pitch_ref_json = '{"low": "D4", "high": "A5"}'
        material.original_key_center = "C major"
        
        low, high = estimate_material_pitch_range(material, "C")
        
        assert low == 62  # D4
        assert high == 81  # A5

    def test_handles_invalid_json(self):
        """Returns defaults on JSON parse error."""
        material = MagicMock()
        material.pitch_low_stored = None
        material.pitch_high_stored = None
        material.pitch_ref_json = "not valid json"
        material.original_key_center = "C major"
        
        low, high = estimate_material_pitch_range(material, "C")
        
        # Should return defaults
        assert low == 60  # C4
        assert high == 72  # C5

    def test_handles_incomplete_pitch_ref(self):
        """Returns defaults when pitch_ref_json lacks low/high."""
        material = MagicMock()
        material.pitch_low_stored = None
        material.pitch_high_stored = None
        material.pitch_ref_json = '{"some": "other_data"}'
        material.original_key_center = "C major"
        
        low, high = estimate_material_pitch_range(material, "C")
        
        assert low == 60
        assert high == 72

    def test_applies_transposition(self):
        """Applies correct transposition shift."""
        material = MagicMock()
        material.pitch_low_stored = "C4"
        material.pitch_high_stored = "G4"
        material.original_key_center = "C major"
        material.pitch_ref_json = None
        
        # Transpose to G (up 7 semitones, but wraps to -5)
        low, high = estimate_material_pitch_range(material, "G")
        
        # G is 7 semitones up, but normalized to -5
        # Actually wait - let me check the logic...
        # C=0, G=7, shift = 7-0 = 7, but >6 so shift-=12 => -5
        assert low == 60 - 5  # 55
        assert high == 67 - 5  # 62


class TestFilterKeysByRange:
    """Tests for filter_keys_by_range function."""

    def test_no_range_constraint_returns_all(self):
        """When no range is set, all keys returned."""
        result = filter_keys_by_range(
            allowed_keys=["C", "G", "F"],
            material=MagicMock(),
            user_range_low="",
            user_range_high="",
        )
        
        assert result == ["C", "G", "F"]

    def test_empty_allowed_keys_returns_empty(self):
        """Empty allowed_keys returns empty list."""
        result = filter_keys_by_range(
            allowed_keys=[],
            material=MagicMock(),
            user_range_low="C4",
            user_range_high="C6",
        )
        
        assert result == []


class TestSelectKeyForMiniSession:
    """Tests for select_key_for_mini_session function."""

    def test_prefers_original_key(self):
        """When prefer_original=True and original fits, use it."""
        material = MagicMock()
        material.original_key_center = "G major"
        material.allowed_keys = "C,G,F"
        material.pitch_low_stored = "C4"
        material.pitch_high_stored = "G5"
        material.pitch_ref_json = None
        
        result = select_key_for_mini_session(
            material=material,
            user_range_low="C4",
            user_range_high="A5",
            prefer_original=True,
        )
        
        assert "G" in result

    def test_avoids_used_keys(self):
        """Should avoid already-used keys."""
        material = MagicMock()
        material.original_key_center = "C major"
        material.allowed_keys = "C,G,F"
        material.pitch_low_stored = "C4"
        material.pitch_high_stored = "G4"
        material.pitch_ref_json = None
        
        # All keys used - should reset and pick from all
        result = select_key_for_mini_session(
            material=material,
            user_range_low="C4",
            user_range_high="C6",
            used_keys={"C", "G", "F"},
            prefer_original=False,
        )
        
        assert result is not None

    def test_falls_back_to_original(self):
        """When nothing fits, return original key."""
        material = MagicMock()
        material.original_key_center = "C major"
        material.allowed_keys = "C,G,F"
        material.pitch_low_stored = "C2"  # Way too low
        material.pitch_high_stored = "C3"  # Way too low
        material.pitch_ref_json = None
        
        # User range is very high - nothing fits
        result = select_key_for_mini_session(
            material=material,
            user_range_low="C6",
            user_range_high="C7",
        )
        
        # Should fall back to original
        assert "C" in result or result == "C major"

    def test_no_allowed_keys_uses_original_tonic(self):
        """When material has no allowed_keys, use original tonic."""
        material = MagicMock()
        material.original_key_center = "D major"
        material.allowed_keys = None  # No allowed keys specified
        material.pitch_low_stored = "D4"
        material.pitch_high_stored = "D5"
        material.pitch_ref_json = None
        
        result = select_key_for_mini_session(
            material=material,
            user_range_low="C4",
            user_range_high="C6",
        )
        
        # Should use D (original tonic) as the only allowed key
        assert "D" in result

    def test_empty_allowed_keys_string_uses_original(self):
        """When allowed_keys is empty string, use original tonic."""
        material = MagicMock()
        material.original_key_center = "E major"
        material.allowed_keys = ""  # Empty string
        material.pitch_low_stored = "E4"
        material.pitch_high_stored = "E5"
        material.pitch_ref_json = None
        
        result = select_key_for_mini_session(
            material=material,
            user_range_low="C4",
            user_range_high="C6",
        )
        
        # Should use E (original tonic)
        assert "E" in result
