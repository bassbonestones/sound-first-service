"""
Tests for tempo/types.py

Tests for tempo type definitions, enums, and BPM mappings.
"""

import pytest

from app.tempo.types import (
    TEMPO_TERM_BPM,
    TEMPO_MODIFIER_TERMS,
    TempoSourceType,
    TempoChangeType,
)


class TestTempoTermBPM:
    """Tests for TEMPO_TERM_BPM mapping."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(TEMPO_TERM_BPM, dict)

    def test_contains_common_tempos(self):
        """Should contain common Italian tempo terms."""
        common_terms = ["allegro", "andante", "adagio", "presto", "moderato"]
        for term in common_terms:
            assert term in TEMPO_TERM_BPM, f"Missing tempo: {term}"

    def test_all_lowercase_keys(self):
        """All keys should be lowercase."""
        for key in TEMPO_TERM_BPM.keys():
            assert key == key.lower(), f"{key} should be lowercase"

    def test_values_are_tuples(self):
        """Values should be 3-tuples (min, typical, max)."""
        for term, value in TEMPO_TERM_BPM.items():
            assert isinstance(value, tuple), f"{term} value should be tuple"
            assert len(value) == 3, f"{term} should have 3 values"

    def test_bpm_ranges_sensible(self):
        """BPM ranges should be sensible (min < typical < max)."""
        for term, (min_bpm, typical_bpm, max_bpm) in TEMPO_TERM_BPM.items():
            assert min_bpm <= typical_bpm <= max_bpm, \
                f"{term}: {min_bpm} <= {typical_bpm} <= {max_bpm}"

    def test_allegro_faster_than_andante(self):
        """Allegro should be faster than andante."""
        allegro_typical = TEMPO_TERM_BPM["allegro"][1]
        andante_typical = TEMPO_TERM_BPM["andante"][1]
        assert allegro_typical > andante_typical

    def test_presto_is_fast(self):
        """Presto should be fast (>160 typical)."""
        presto_typical = TEMPO_TERM_BPM["presto"][1]
        assert presto_typical >= 160

    def test_grave_is_slow(self):
        """Grave should be slow (<50 typical)."""
        grave_typical = TEMPO_TERM_BPM["grave"][1]
        assert grave_typical < 50

    def test_all_positive_bpm(self):
        """All BPM values should be positive."""
        for term, (min_bpm, _, max_bpm) in TEMPO_TERM_BPM.items():
            assert min_bpm > 0, f"{term} min_bpm should be positive"
            assert max_bpm > 0, f"{term} max_bpm should be positive"


class TestTempoModifierTerms:
    """Tests for TEMPO_MODIFIER_TERMS mapping."""

    def test_is_dict(self):
        """Should be a dictionary."""
        assert isinstance(TEMPO_MODIFIER_TERMS, dict)

    def test_contains_accelerando(self):
        """Should contain accelerando variants."""
        accel_keys = [k for k in TEMPO_MODIFIER_TERMS if "accel" in k.lower()]
        assert len(accel_keys) > 0

    def test_contains_ritardando(self):
        """Should contain ritardando variants."""
        rit_keys = [k for k in TEMPO_MODIFIER_TERMS if "rit" in k.lower()]
        assert len(rit_keys) > 0

    def test_contains_a_tempo(self):
        """Should contain a tempo."""
        assert "a tempo" in TEMPO_MODIFIER_TERMS

    def test_abbreviated_forms(self):
        """Should contain abbreviated forms."""
        assert "rit." in TEMPO_MODIFIER_TERMS
        assert "accel." in TEMPO_MODIFIER_TERMS

    def test_values_are_canonical(self):
        """Values should be canonical form names."""
        canonical = {"accelerando", "ritardando", "a_tempo", "rubato", "meno_mosso", "piu_mosso"}
        for key, value in TEMPO_MODIFIER_TERMS.items():
            assert value in canonical, f"Value {value} for {key} is not canonical"


class TestTempoSourceType:
    """Tests for TempoSourceType enum."""

    def test_is_enum(self):
        """Should be an enum."""
        from enum import Enum
        assert issubclass(TempoSourceType, Enum)

    def test_metronome_mark(self):
        """Should have METRONOME_MARK."""
        assert TempoSourceType.METRONOME_MARK is not None
        assert TempoSourceType.METRONOME_MARK.value == "metronome_mark"

    def test_text_term(self):
        """Should have TEXT_TERM."""
        assert TempoSourceType.TEXT_TERM is not None
        assert TempoSourceType.TEXT_TERM.value == "text_term"

    def test_inferred(self):
        """Should have INFERRED."""
        assert TempoSourceType.INFERRED is not None
        assert TempoSourceType.INFERRED.value == "inferred"

    def test_default(self):
        """Should have DEFAULT."""
        assert TempoSourceType.DEFAULT is not None
        assert TempoSourceType.DEFAULT.value == "default"

    def test_string_mixin(self):
        """Should be usable as string."""
        # TempoSourceType(str, Enum) allows string operations
        assert str(TempoSourceType.METRONOME_MARK) == "TempoSourceType.METRONOME_MARK"


class TestTempoChangeType:
    """Tests for TempoChangeType enum."""

    def test_is_enum(self):
        """Should be an enum."""
        from enum import Enum
        assert issubclass(TempoChangeType, Enum)

    def test_initial(self):
        """Should have INITIAL."""
        assert TempoChangeType.INITIAL is not None
        assert TempoChangeType.INITIAL.value == "initial"

    def test_stable(self):
        """Should have STABLE."""
        assert TempoChangeType.STABLE is not None
        assert TempoChangeType.STABLE.value == "stable"

    def test_sudden_change(self):
        """Should have SUDDEN_CHANGE."""
        assert TempoChangeType.SUDDEN_CHANGE is not None

    def test_accelerando(self):
        """Should have ACCELERANDO."""
        assert TempoChangeType.ACCELERANDO is not None
        assert TempoChangeType.ACCELERANDO.value == "accelerando"

    def test_ritardando(self):
        """Should have RITARDANDO."""
        assert TempoChangeType.RITARDANDO is not None
        assert TempoChangeType.RITARDANDO.value == "ritardando"

    def test_a_tempo(self):
        """Should have A_TEMPO."""
        assert TempoChangeType.A_TEMPO is not None

    def test_rubato(self):
        """Should have RUBATO."""
        assert TempoChangeType.RUBATO is not None

    def test_relative_changes(self):
        """Should have relative tempo changes."""
        assert TempoChangeType.MENO_MOSSO is not None
        assert TempoChangeType.PIU_MOSSO is not None


class TestTempoDifficultyMetrics:
    """Tests for TempoDifficultyMetrics dataclass."""

    def test_to_dict_returns_dict(self):
        """to_dict should return a dictionary."""
        from app.tempo.types import TempoDifficultyMetrics
        
        metrics = TempoDifficultyMetrics(
            tempo_speed_difficulty=0.5,
            tempo_control_difficulty=0.3,
            raw_metrics={"test_key": 42}
        )
        
        result = metrics.to_dict()
        assert isinstance(result, dict)
        assert result["tempo_speed_difficulty"] == 0.5
        assert result["tempo_control_difficulty"] == 0.3
        assert result["raw_metrics"]["test_key"] == 42

    def test_to_dict_handles_none_values(self):
        """to_dict should handle None difficulty values."""
        from app.tempo.types import TempoDifficultyMetrics
        
        metrics = TempoDifficultyMetrics(
            tempo_speed_difficulty=None,
            tempo_control_difficulty=None,
        )
        
        result = metrics.to_dict()
        assert result["tempo_speed_difficulty"] is None
        assert result["tempo_control_difficulty"] is None

    def test_to_dict_empty_raw_metrics(self):
        """to_dict with empty raw_metrics."""
        from app.tempo.types import TempoDifficultyMetrics
        
        metrics = TempoDifficultyMetrics(
            tempo_speed_difficulty=0.8,
            tempo_control_difficulty=0.2,
        )
        
        result = metrics.to_dict()
        assert result["raw_metrics"] == {}
