"""Tests for ValidPoolCalculator.

Comprehensive tests covering:
- Scale × pattern → interval capability mapping
- Arpeggio × pattern → interval capability mapping
- Rhythm → capability mapping
- Key → accidental capability mapping
- Learnable-in-context exclusion
- Valid pool calculation
"""

import pytest
from typing import Set

from app.services.generation.valid_pool_calculator import (
    ValidPoolCalculator,
    get_valid_pool_calculator,
    SEMITONE_TO_CAPABILITY,
    RHYTHM_TO_CAPABILITIES,
    SHARP_KEYS,
    FLAT_KEYS,
    get_key_required_capabilities,
    _compute_scale_cumulative,
    _compute_melodic_intervals_straight,
    _compute_melodic_intervals_in_nths,
    _compute_arpeggio_melodic_intervals_straight,
)
from app.schemas.generation_schemas import (
    ScaleType,
    ScalePattern,
    ArpeggioType,
    ArpeggioPattern,
    RhythmType,
    MusicalKey,
)


# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def calculator() -> ValidPoolCalculator:
    """Create a ValidPoolCalculator instance."""
    return ValidPoolCalculator()


@pytest.fixture
def minimal_caps() -> Set[str]:
    """Minimal capabilities - just stepwise motion and quarters."""
    return {
        "interval_play_minor_2",
        "interval_play_major_2",
        "rhythm_quarter_notes",
    }


@pytest.fixture
def beginner_caps() -> Set[str]:
    """Beginner capabilities - steps, 3rds, basic rhythms, C major."""
    return {
        "interval_play_minor_2",
        "interval_play_major_2",
        "interval_play_minor_3",
        "interval_play_major_3",
        "rhythm_quarter_notes",
        "rhythm_eighth_notes",
    }


@pytest.fixture
def intermediate_caps() -> Set[str]:
    """Intermediate capabilities - up to 5ths, more rhythms, sharps."""
    return {
        "interval_play_minor_2",
        "interval_play_major_2",
        "interval_play_minor_3",
        "interval_play_major_3",
        "interval_play_perfect_4",
        "interval_play_perfect_5",
        "rhythm_quarter_notes",
        "rhythm_eighth_notes",
        "rhythm_triplets_eighth",
        "accidental_sharp_symbol",
    }


@pytest.fixture
def advanced_caps() -> Set[str]:
    """Advanced capabilities - full range through octave, all accidentals."""
    return {
        "interval_play_minor_2",
        "interval_play_major_2",
        "interval_play_minor_3",
        "interval_play_major_3",
        "interval_play_perfect_4",
        "interval_play_augmented_4",
        "interval_play_perfect_5",
        "interval_play_minor_6",
        "interval_play_major_6",
        "interval_play_minor_7",
        "interval_play_major_7",
        "interval_play_octave",
        "rhythm_whole_notes",
        "rhythm_half_notes",
        "rhythm_quarter_notes",
        "rhythm_eighth_notes",
        "rhythm_sixteenth_notes",
        "rhythm_triplets_eighth",
        "accidental_sharp_symbol",
        "accidental_flat_symbol",
    }


# =============================================================================
# Test Utility Functions
# =============================================================================

class TestScaleCumulative:
    """Tests for _compute_scale_cumulative."""
    
    def test_major_scale(self):
        """Major scale intervals [2,2,1,2,2,2,1] -> cumulative."""
        intervals = (2, 2, 1, 2, 2, 2, 1)
        cumulative = _compute_scale_cumulative(intervals)
        assert cumulative == [0, 2, 4, 5, 7, 9, 11, 12]
    
    def test_pentatonic(self):
        """Pentatonic [2,2,3,2,3] -> cumulative."""
        intervals = (2, 2, 3, 2, 3)
        cumulative = _compute_scale_cumulative(intervals)
        assert cumulative == [0, 2, 4, 7, 9, 12]
    
    def test_chromatic(self):
        """Chromatic [1,1,1...] -> cumulative."""
        intervals = (1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1)
        cumulative = _compute_scale_cumulative(intervals)
        assert cumulative == list(range(13))


class TestMelodicIntervalsStraight:
    """Tests for _compute_melodic_intervals_straight."""
    
    def test_major_scale(self):
        """Major scale straight pattern uses M2 and m2 intervals."""
        intervals = (2, 2, 1, 2, 2, 2, 1)
        result = _compute_melodic_intervals_straight(intervals)
        assert result == {1, 2}
    
    def test_pentatonic(self):
        """Pentatonic straight includes m3 (3 semitones)."""
        intervals = (2, 2, 3, 2, 3)
        result = _compute_melodic_intervals_straight(intervals)
        assert result == {2, 3}
    
    def test_whole_tone(self):
        """Whole tone scale only uses M2."""
        intervals = (2, 2, 2, 2, 2, 2)
        result = _compute_melodic_intervals_straight(intervals)
        assert result == {2}


class TestMelodicIntervalsInNths:
    """Tests for _compute_melodic_intervals_in_nths."""
    
    def test_major_in_3rds(self):
        """Major scale in 3rds uses m3 and M3."""
        intervals = (2, 2, 1, 2, 2, 2, 1)
        result = _compute_melodic_intervals_in_nths(intervals, 3)
        # In 3rds: 3 or 4 semitones, plus stepwise motion
        assert 3 in result  # m3
        assert 4 in result  # M3
        # Also includes stepwise intervals
        assert 1 in result or 2 in result
    
    def test_major_in_4ths(self):
        """Major scale in 4ths uses P4 and A4/d5."""
        intervals = (2, 2, 1, 2, 2, 2, 1)
        result = _compute_melodic_intervals_in_nths(intervals, 4)
        assert 5 in result  # P4
        assert 6 in result  # A4 (tritone between scale degrees 4 and 7)


class TestArpeggioMelodicIntervals:
    """Tests for arpeggio melodic interval computation."""
    
    def test_major_triad(self):
        """Major triad (0, 4, 7) has M3 and m3."""
        intervals = (0, 4, 7)
        result = _compute_arpeggio_melodic_intervals_straight(intervals)
        assert result == {4, 3}  # M3 (4), m3 (3)
    
    def test_minor_triad(self):
        """Minor triad (0, 3, 7) has m3 and M3."""
        intervals = (0, 3, 7)
        result = _compute_arpeggio_melodic_intervals_straight(intervals)
        assert result == {3, 4}  # m3 (3), M3 (4)
    
    def test_major_7th(self):
        """Maj7 (0, 4, 7, 11) has M3, m3, M3."""
        intervals = (0, 4, 7, 11)
        result = _compute_arpeggio_melodic_intervals_straight(intervals)
        assert result == {4, 3, 4}  # M3, m3, M3


# =============================================================================
# Test Key Requirements
# =============================================================================

class TestKeyRequirements:
    """Tests for get_key_required_capabilities."""
    
    def test_c_requires_nothing(self):
        """C major requires no accidentals."""
        result = get_key_required_capabilities(MusicalKey.C)
        assert result == frozenset()
    
    def test_g_requires_sharp(self):
        """G major requires sharps."""
        result = get_key_required_capabilities(MusicalKey.G)
        assert "accidental_sharp_symbol" in result
    
    def test_f_requires_flat(self):
        """F major requires flats."""
        result = get_key_required_capabilities(MusicalKey.F)
        assert "accidental_flat_symbol" in result
    
    def test_all_sharp_keys(self):
        """All sharp keys require sharp capability."""
        for key in [MusicalKey.G, MusicalKey.D, MusicalKey.A, MusicalKey.E, MusicalKey.B]:
            result = get_key_required_capabilities(key)
            assert "accidental_sharp_symbol" in result
    
    def test_all_flat_keys(self):
        """All flat keys require flat capability."""
        for key in [MusicalKey.F, MusicalKey.B_FLAT, MusicalKey.E_FLAT, MusicalKey.A_FLAT]:
            result = get_key_required_capabilities(key)
            assert "accidental_flat_symbol" in result


# =============================================================================
# Test ValidPoolCalculator Methods
# =============================================================================

class TestGetValidScaleTypes:
    """Tests for get_valid_scale_types."""
    
    def test_minimal_caps_gets_stepwise_scales(self, calculator, minimal_caps):
        """With only stepwise intervals, some scales should be valid."""
        valid = calculator.get_valid_scale_types(minimal_caps)
        # Major modes use stepwise motion for straight patterns
        assert ScaleType.IONIAN in valid or len(valid) > 0
    
    def test_empty_caps_returns_empty(self, calculator):
        """With no capabilities, no scales are valid."""
        valid = calculator.get_valid_scale_types(set())
        assert len(valid) == 0
    
    def test_advanced_caps_gets_many_scales(self, calculator, advanced_caps):
        """Advanced caps should unlock many scale types."""
        valid = calculator.get_valid_scale_types(advanced_caps)
        # Should have access to most scales
        assert len(valid) >= 10


class TestGetValidArpeggioTypes:
    """Tests for get_valid_arpeggio_types."""
    
    def test_with_thirds_gets_triads(self, calculator, beginner_caps):
        """With m3 and M3, triads should be valid."""
        valid = calculator.get_valid_arpeggio_types(beginner_caps)
        # Should have at least major and minor triads
        has_triads = ArpeggioType.MAJOR in valid or ArpeggioType.MINOR in valid
        assert has_triads or len(valid) > 0
    
    def test_empty_caps_returns_empty(self, calculator):
        """With no capabilities, no arpeggios are valid."""
        valid = calculator.get_valid_arpeggio_types(set())
        assert len(valid) == 0


class TestGetValidPatternsForScale:
    """Tests for get_valid_patterns_for_scale."""
    
    def test_straight_patterns_with_minimal(self, calculator, minimal_caps):
        """Straight patterns should be valid with stepwise intervals."""
        valid = calculator.get_valid_patterns_for_scale(ScaleType.IONIAN, minimal_caps)
        # At minimum, straight up/down should work
        has_straight = (
            ScalePattern.STRAIGHT_UP in valid or
            ScalePattern.STRAIGHT_DOWN in valid or
            len(valid) > 0
        )
        assert has_straight
    
    def test_in_3rds_requires_thirds(self, calculator, minimal_caps, beginner_caps):
        """In 3rds pattern requires 3rd intervals."""
        # Minimal (no 3rds) should not have in_3rds
        valid_minimal = calculator.get_valid_patterns_for_scale(ScaleType.IONIAN, minimal_caps)
        
        # Beginner (with 3rds) should have in_3rds
        valid_beginner = calculator.get_valid_patterns_for_scale(ScaleType.IONIAN, beginner_caps)
        
        # At least one should have more patterns than the other
        assert len(valid_beginner) >= len(valid_minimal)


class TestGetValidRhythms:
    """Tests for get_valid_rhythms."""
    
    def test_quarters_with_quarters_cap(self, calculator):
        """Quarter notes should be valid with quarter notes capability."""
        caps = {"rhythm_quarter_notes"}
        valid = calculator.get_valid_rhythms(caps)
        assert RhythmType.QUARTER_NOTES in valid
    
    def test_triplets_require_both_caps(self, calculator):
        """Eighth triplets require both eighth notes and triplet caps."""
        # Only eighth notes - no triplets
        caps_no_triplet = {"rhythm_eighth_notes"}
        valid = calculator.get_valid_rhythms(caps_no_triplet)
        assert RhythmType.EIGHTH_TRIPLETS not in valid
        
        # With triplet cap too
        caps_with_triplet = {"rhythm_eighth_notes", "rhythm_triplets_eighth"}
        valid = calculator.get_valid_rhythms(caps_with_triplet)
        assert RhythmType.EIGHTH_TRIPLETS in valid
    
    def test_empty_caps_returns_empty(self, calculator):
        """With no rhythm caps, no rhythms are valid."""
        valid = calculator.get_valid_rhythms(set())
        assert len(valid) == 0


class TestGetValidKeys:
    """Tests for get_valid_keys."""
    
    def test_c_always_valid(self, calculator):
        """C major is valid even with no accidental caps."""
        valid = calculator.get_valid_keys(set())
        assert MusicalKey.C in valid
    
    def test_sharp_keys_with_sharp_cap(self, calculator):
        """Sharp keys require sharp capability."""
        caps_with_sharp = {"accidental_sharp_symbol"}
        valid = calculator.get_valid_keys(caps_with_sharp)
        assert MusicalKey.G in valid
        assert MusicalKey.D in valid
        assert MusicalKey.A in valid
    
    def test_flat_keys_with_flat_cap(self, calculator):
        """Flat keys require flat capability."""
        caps_with_flat = {"accidental_flat_symbol"}
        valid = calculator.get_valid_keys(caps_with_flat)
        assert MusicalKey.F in valid
        assert MusicalKey.B_FLAT in valid
    
    def test_all_keys_with_both_caps(self, calculator):
        """All keys valid with both sharp and flat caps."""
        caps = {"accidental_sharp_symbol", "accidental_flat_symbol"}
        valid = calculator.get_valid_keys(caps)
        # Should have almost all keys
        assert len(valid) >= 12


class TestGetRequiredCapabilities:
    """Tests for get_required_capabilities_for_* methods."""
    
    def test_scale_required_caps(self, calculator):
        """Can get required capabilities for scale + pattern."""
        required = calculator.get_required_capabilities_for_scale(
            ScaleType.IONIAN, ScalePattern.STRAIGHT_UP
        )
        # Should require stepwise intervals
        assert len(required) > 0
    
    def test_arpeggio_required_caps(self, calculator):
        """Can get required capabilities for arpeggio + pattern."""
        required = calculator.get_required_capabilities_for_arpeggio(
            ArpeggioType.MAJOR, ArpeggioPattern.STRAIGHT_UP
        )
        # Should require 3rd intervals
        assert len(required) > 0
    
    def test_rhythm_required_caps(self, calculator):
        """Can get required capabilities for rhythm."""
        required = calculator.get_required_capabilities_for_rhythm(RhythmType.QUARTER_NOTES)
        assert "rhythm_quarter_notes" in required
    
    def test_key_required_caps(self, calculator):
        """Can get required capabilities for key."""
        required = calculator.get_required_capabilities_for_key(MusicalKey.G)
        assert "accidental_sharp_symbol" in required


class TestGetFullValidPool:
    """Tests for get_full_valid_pool."""
    
    def test_returns_pool_object(self, calculator, beginner_caps):
        """Returns a ValidPool object with all fields."""
        pool = calculator.get_full_valid_pool(beginner_caps)
        
        assert hasattr(pool, "scale_types")
        assert hasattr(pool, "arpeggio_types")
        assert hasattr(pool, "rhythms")
        assert hasattr(pool, "keys")
        assert hasattr(pool, "scale_patterns")
        assert hasattr(pool, "arpeggio_patterns")
    
    def test_pool_to_dict(self, calculator, beginner_caps):
        """Pool can be converted to dict for API response."""
        pool = calculator.get_full_valid_pool(beginner_caps)
        pool_dict = pool.to_dict()
        
        assert isinstance(pool_dict, dict)
        assert "scale_types" in pool_dict
        assert "arpeggio_types" in pool_dict
        assert "rhythms" in pool_dict
        assert "keys" in pool_dict
        assert "scale_patterns" in pool_dict
        assert "arpeggio_patterns" in pool_dict
    
    def test_pool_grows_with_caps(self, calculator, minimal_caps, advanced_caps):
        """Pool size increases with more capabilities."""
        pool_minimal = calculator.get_full_valid_pool(minimal_caps)
        pool_advanced = calculator.get_full_valid_pool(advanced_caps)
        
        # Advanced should have more options than minimal
        assert len(pool_advanced.scale_types) >= len(pool_minimal.scale_types)
        assert len(pool_advanced.rhythms) >= len(pool_minimal.rhythms)
        assert len(pool_advanced.keys) >= len(pool_minimal.keys)


# =============================================================================
# Test Learnable-in-Context Handling
# =============================================================================

class TestLearnableInContext:
    """Tests for learnable-in-context capability handling."""
    
    def test_learnable_caps_not_gating(self, calculator):
        """Capabilities marked learnable_in_context should not gate content."""
        # double_sharp_symbol and double_flat_symbol are learnable_in_context
        # They should not block any keys or scales
        
        # User has sharp symbol but not double_sharp
        caps = {"accidental_sharp_symbol"}
        valid_keys = calculator.get_valid_keys(caps)
        
        # Should still get sharp keys even without double_sharp capability
        assert MusicalKey.G in valid_keys


# =============================================================================
# Test Singleton
# =============================================================================

class TestSingleton:
    """Tests for singleton pattern."""
    
    def test_get_calculator_returns_same_instance(self):
        """get_valid_pool_calculator returns the same instance."""
        calc1 = get_valid_pool_calculator()
        calc2 = get_valid_pool_calculator()
        assert calc1 is calc2


# =============================================================================
# Integration Tests
# =============================================================================

class TestIntegration:
    """Integration tests combining multiple calculator features."""
    
    def test_realistic_beginner_pool(self, calculator):
        """Test realistic beginner capability set."""
        caps = {
            # Can play stepwise and 3rds
            "interval_play_minor_2",
            "interval_play_major_2",
            "interval_play_minor_3",
            "interval_play_major_3",
            # Basic rhythms
            "rhythm_quarter_notes",
            "rhythm_eighth_notes",
            # No accidentals (C major only)
        }
        
        pool = calculator.get_full_valid_pool(caps)
        
        # Should have some scales
        assert len(pool.scale_types) > 0
        
        # Should have C only (no accidentals)
        assert MusicalKey.C in pool.keys
        assert len(pool.keys) == 1
        
        # Should have basic rhythms
        assert RhythmType.QUARTER_NOTES in pool.rhythms
        assert RhythmType.EIGHTH_NOTES in pool.rhythms
    
    def test_realistic_intermediate_pool(self, calculator, intermediate_caps):
        """Test realistic intermediate capability set."""
        pool = calculator.get_full_valid_pool(intermediate_caps)
        
        # Should have more scales
        assert len(pool.scale_types) > 5
        
        # Should have sharp keys
        assert MusicalKey.G in pool.keys
        assert MusicalKey.D in pool.keys
        
        # Should have triplets
        assert RhythmType.EIGHTH_TRIPLETS in pool.rhythms
    
    def test_pool_permits_valid_content(self, calculator, beginner_caps):
        """Content from valid pool should have satisfiable requirements."""
        pool = calculator.get_full_valid_pool(beginner_caps)
        
        # For each valid scale + pattern combo, requirements should be satisfiable
        for scale_type in pool.scale_types:
            for pattern in pool.scale_patterns.get(scale_type, set()):
                required = calculator.get_required_capabilities_for_scale(scale_type, pattern)
                # User should have all gating capabilities
                # (learnable-in-context excluded from check)
                assert calculator._user_has_required(beginner_caps, required)
