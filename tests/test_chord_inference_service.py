"""Tests for the chord inference service.

Tests cover:
- Basic chord inference from melody notes
- Key signature handling (sharps and flats)
- Time signature handling
- Seventh chord vs triad inference
- Multiple chords per measure
- Edge cases (empty measures, rests)
"""
import json
import pytest

from app.services.chord_inference import ChordInferenceService, InferredChord


class TestChordInferenceService:
    """Tests for ChordInferenceService."""
    
    @pytest.fixture
    def service(self) -> ChordInferenceService:
        """Create a chord inference service instance."""
        return ChordInferenceService()
    
    # =========================================================================
    # Basic Chord Inference
    # =========================================================================
    
    def test_infer_c_major_chord_from_c_e_g_notes(
        self, service: ChordInferenceService
    ) -> None:
        """C, E, G notes should infer C major chord."""
        measures = [
            {"notes": [
                {"pitch": 60, "duration": 1.0},  # C4
                {"pitch": 64, "duration": 1.0},  # E4
                {"pitch": 67, "duration": 1.0},  # G4
                {"pitch": 60, "duration": 1.0},  # C4
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, key_signature=0, use_seventh_chords=False
        )
        
        assert len(chords) == 1
        assert chords[0].root == "C"
        assert chords[0].quality == ""  # Major triad
        assert chords[0].symbol == "C"
        assert chords[0].measure_index == 0
        assert chords[0].beat_position == 0.0
    
    def test_infer_c_major7_when_seventh_chords_enabled(
        self, service: ChordInferenceService
    ) -> None:
        """C, E, G notes should infer Cmaj7 when seventh chords enabled."""
        measures = [
            {"notes": [
                {"pitch": 60, "duration": 1.0},  # C4
                {"pitch": 64, "duration": 1.0},  # E4
                {"pitch": 67, "duration": 1.0},  # G4
                {"pitch": 60, "duration": 1.0},  # C4
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, key_signature=0, use_seventh_chords=True
        )
        
        assert len(chords) == 1
        assert chords[0].root == "C"
        assert chords[0].quality == "maj7"
        assert chords[0].symbol == "Cmaj7"
    
    def test_infer_d_minor_chord_from_d_f_a_notes(
        self, service: ChordInferenceService
    ) -> None:
        """D, F, A notes should infer Dm chord (ii in C major)."""
        measures = [
            {"notes": [
                {"pitch": 62, "duration": 1.0},  # D4
                {"pitch": 65, "duration": 1.0},  # F4
                {"pitch": 69, "duration": 1.0},  # A4
                {"pitch": 62, "duration": 1.0},  # D4
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, key_signature=0, use_seventh_chords=False
        )
        
        assert len(chords) == 1
        assert chords[0].root == "D"
        assert chords[0].quality == "m"
        assert chords[0].symbol == "Dm"
    
    def test_infer_g_dominant_seventh_from_scale_degree_five(
        self, service: ChordInferenceService
    ) -> None:
        """G, B, D, F notes should infer G7 (V7 in C major)."""
        measures = [
            {"notes": [
                {"pitch": 67, "duration": 1.0},  # G4
                {"pitch": 71, "duration": 1.0},  # B4
                {"pitch": 74, "duration": 1.0},  # D5
                {"pitch": 65, "duration": 1.0},  # F4
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, key_signature=0, use_seventh_chords=True
        )
        
        assert len(chords) == 1
        assert chords[0].root == "G"
        assert chords[0].quality == "7"
        assert chords[0].symbol == "G7"
    
    # =========================================================================
    # Multiple Measures
    # =========================================================================
    
    def test_infer_chords_for_multiple_measures(
        self, service: ChordInferenceService
    ) -> None:
        """Should infer one chord per measure."""
        measures = [
            {"notes": [
                {"pitch": 60, "duration": 2.0},  # C4
                {"pitch": 64, "duration": 2.0},  # E4
            ]},
            {"notes": [
                {"pitch": 67, "duration": 2.0},  # G4
                {"pitch": 71, "duration": 2.0},  # B4
            ]},
            {"notes": [
                {"pitch": 60, "duration": 4.0},  # C4
            ]},
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, key_signature=0, use_seventh_chords=False
        )
        
        assert len(chords) == 3
        assert chords[0].measure_index == 0
        assert chords[1].measure_index == 1
        assert chords[2].measure_index == 2
    
    def test_two_chords_per_measure(
        self, service: ChordInferenceService
    ) -> None:
        """Should infer two chords per measure when requested."""
        measures = [
            {"notes": [
                {"pitch": 60, "duration": 1.0},  # C4 - beat 1
                {"pitch": 64, "duration": 1.0},  # E4 - beat 2
                {"pitch": 67, "duration": 1.0},  # G4 - beat 3
                {"pitch": 71, "duration": 1.0},  # B4 - beat 4
            ]},
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json,
            key_signature=0,
            time_signature={"beats": 4, "beatUnit": 4},
            chords_per_measure=2,
        )
        
        assert len(chords) == 2
        assert chords[0].beat_position == 0.0
        assert chords[1].beat_position == 2.0
    
    # =========================================================================
    # Key Signature Handling
    # =========================================================================
    
    def test_infer_in_g_major_key(
        self, service: ChordInferenceService
    ) -> None:
        """Chords in G major should use correct scale degrees."""
        # G major arpeggio notes
        measures = [
            {"notes": [
                {"pitch": 67, "duration": 1.0},  # G4
                {"pitch": 71, "duration": 1.0},  # B4
                {"pitch": 74, "duration": 1.0},  # D5
                {"pitch": 67, "duration": 1.0},  # G4
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, key_signature=1, use_seventh_chords=False  # G major
        )
        
        assert len(chords) == 1
        assert chords[0].root == "G"
        assert chords[0].quality == ""  # I chord in G major = G major
    
    def test_infer_in_f_major_key_uses_flats(
        self, service: ChordInferenceService
    ) -> None:
        """F major (1 flat) should use flat spellings."""
        # Bb major arpeggio notes (IV in F major)
        measures = [
            {"notes": [
                {"pitch": 70, "duration": 1.0},  # Bb4
                {"pitch": 74, "duration": 1.0},  # D5
                {"pitch": 77, "duration": 1.0},  # F5
                {"pitch": 70, "duration": 1.0},  # Bb4
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, key_signature=-1, use_seventh_chords=False  # F major
        )
        
        assert len(chords) == 1
        assert chords[0].root == "Bb"  # Not A#
    
    def test_infer_in_d_major_key_uses_sharps(
        self, service: ChordInferenceService
    ) -> None:
        """D major (2 sharps) should use sharp spellings."""
        # F# minor arpeggio (iii in D major)
        measures = [
            {"notes": [
                {"pitch": 66, "duration": 1.0},  # F#4
                {"pitch": 69, "duration": 1.0},  # A4
                {"pitch": 73, "duration": 1.0},  # C#5
                {"pitch": 66, "duration": 1.0},  # F#4
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, key_signature=2, use_seventh_chords=False  # D major
        )
        
        assert len(chords) == 1
        assert chords[0].root == "F#"  # Not Gb
    
    # =========================================================================
    # Edge Cases
    # =========================================================================
    
    def test_empty_measures_returns_empty_list(
        self, service: ChordInferenceService
    ) -> None:
        """Empty measures array should return empty chord list."""
        measures_json = "[]"
        
        chords = service.infer_chords_from_measures(measures_json)
        
        assert chords == []
    
    def test_measure_with_all_rests_skipped(
        self, service: ChordInferenceService
    ) -> None:
        """Measure with only rests should not produce a chord."""
        measures = [
            {"notes": [
                {"isRest": True, "duration": 4.0},
            ]},
            {"notes": [
                {"pitch": 60, "duration": 4.0},  # C4
            ]},
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(measures_json)
        
        # Only second measure should have a chord
        assert len(chords) == 1
        assert chords[0].measure_index == 1
    
    def test_measure_with_mixed_notes_and_rests(
        self, service: ChordInferenceService
    ) -> None:
        """Notes mixed with rests should still infer chord from notes."""
        measures = [
            {"notes": [
                {"pitch": 60, "duration": 1.0},  # C4
                {"isRest": True, "duration": 1.0},
                {"pitch": 64, "duration": 1.0},  # E4
                {"pitch": 67, "duration": 1.0},  # G4
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, use_seventh_chords=False
        )
        
        assert len(chords) == 1
        assert chords[0].root == "C"
        assert chords[0].quality == ""
    
    def test_empty_notes_array_skipped(
        self, service: ChordInferenceService
    ) -> None:
        """Measure with empty notes array should be skipped."""
        measures = [
            {"notes": []},
            {"notes": [{"pitch": 60, "duration": 4.0}]},
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(measures_json)
        
        assert len(chords) == 1
        assert chords[0].measure_index == 1
    
    # =========================================================================
    # Beat Weighting
    # =========================================================================
    
    def test_strong_beat_notes_weighted_higher(
        self, service: ChordInferenceService
    ) -> None:
        """Notes on beat 1 should have more influence than weak beats."""
        # C on beat 1, D notes on other beats
        # Should still infer C chord because beat 1 is weighted higher
        measures = [
            {"notes": [
                {"pitch": 60, "duration": 1.0},  # C4 - beat 1 (weight 3)
                {"pitch": 62, "duration": 1.0},  # D4 - beat 2 (weight 1)
                {"pitch": 64, "duration": 1.0},  # E4 - beat 3 (weight 2)
                {"pitch": 67, "duration": 1.0},  # G4 - beat 4 (weight 1)
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, use_seventh_chords=False
        )
        
        assert len(chords) == 1
        # Should favor C major because C, E, G are chord tones
        # and C is on the strongest beat
        assert chords[0].root == "C"
    
    # =========================================================================
    # Resolution Pattern Detection
    # =========================================================================
    
    def test_4_3_suspension_resolves_to_chord_tone(
        self, service: ChordInferenceService
    ) -> None:
        """Quarter note F → half note E should infer C major (E is 3rd).
        
        This is a classic 4-3 suspension resolution. The F (4th) resolves
        down to E (3rd). The E is the chord tone, not the F.
        """
        measures = [
            {"notes": [
                {"pitch": 65, "duration": 1.0},  # F4 - quarter (suspension)
                {"pitch": 64, "duration": 2.0},  # E4 - half (resolution target)
                {"pitch": 67, "duration": 1.0},  # G4 - quarter
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, use_seventh_chords=False
        )
        
        assert len(chords) == 1
        # Should NOT be F major - the E (resolution target) should win
        assert chords[0].root == "C"
        assert chords[0].quality == ""
    
    def test_7_8_resolution_favors_tonic(
        self, service: ChordInferenceService
    ) -> None:
        """B resolving to C should favor C major, not Em or G."""
        measures = [
            {"notes": [
                {"pitch": 71, "duration": 0.5},  # B4 - eighth (leading tone)
                {"pitch": 72, "duration": 2.0},  # C5 - half (resolution)
                {"pitch": 64, "duration": 1.5},  # E4 - dotted quarter
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, use_seventh_chords=False
        )
        
        assert len(chords) == 1
        assert chords[0].root == "C"
    
    def test_duration_weights_longer_notes_higher(
        self, service: ChordInferenceService
    ) -> None:
        """Longer notes should be weighted higher as likely chord tones."""
        measures = [
            {"notes": [
                {"pitch": 62, "duration": 0.5},  # D4 - eighth (passing)
                {"pitch": 64, "duration": 0.5},  # E4 - eighth (passing)
                {"pitch": 67, "duration": 3.0},  # G4 - dotted half
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, key_signature=0, use_seventh_chords=False
        )
        
        assert len(chords) == 1
        # G is the longest note, should influence chord choice
        # C or G would fit, but G on half note should be significant
        # With E present, C major is most likely
        assert chords[0].root in ("C", "G")
    
    # =========================================================================
    # Confidence Scoring
    # =========================================================================
    
    def test_perfect_chord_tone_match_high_confidence(
        self, service: ChordInferenceService
    ) -> None:
        """All chord tones should result in high confidence."""
        measures = [
            {"notes": [
                {"pitch": 60, "duration": 1.0},  # C4
                {"pitch": 64, "duration": 1.0},  # E4
                {"pitch": 67, "duration": 1.0},  # G4
                {"pitch": 72, "duration": 1.0},  # C5
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, use_seventh_chords=False
        )
        
        assert chords[0].confidence > 0.8
    
    def test_passing_tones_lower_confidence(
        self, service: ChordInferenceService
    ) -> None:
        """Passing tones should result in lower but acceptable confidence."""
        # F and A passing tones around C chord
        measures = [
            {"notes": [
                {"pitch": 60, "duration": 1.0},  # C4
                {"pitch": 65, "duration": 0.5},  # F4 (passing)
                {"pitch": 64, "duration": 0.5},  # E4
                {"pitch": 67, "duration": 1.0},  # G4
                {"pitch": 69, "duration": 1.0},  # A4 (passing)
            ]}
        ]
        measures_json = json.dumps(measures)
        
        chords = service.infer_chords_from_measures(
            measures_json, use_seventh_chords=False
        )
        
        # Should still detect C but with lower confidence
        assert chords[0].root == "C"
        assert 0.3 <= chords[0].confidence <= 0.9
    
    # =========================================================================
    # Conversion to ChordProgression Dict
    # =========================================================================
    
    def test_to_chord_progression_dict(
        self, service: ChordInferenceService
    ) -> None:
        """Should convert inferred chords to ChordProgression dict format."""
        inferred = [
            InferredChord(
                root="C", quality="maj7", beat_position=0.0,
                measure_index=0, confidence=0.9
            ),
            InferredChord(
                root="G", quality="7", beat_position=0.0,
                measure_index=1, confidence=0.85
            ),
        ]
        
        result = service.to_chord_progression_dict(inferred, name="Test Progression")
        
        assert result["name"] == "Test Progression"
        assert result["isAutoInferred"] is True
        assert result["isSystemDefined"] is True
        assert result["isDefault"] is False
        assert "id" in result
        assert len(result["chords"]) == 2
        assert result["chords"][0]["symbol"] == "Cmaj7"
        assert result["chords"][1]["symbol"] == "G7"
    
    def test_chord_progression_dict_has_unique_ids(
        self, service: ChordInferenceService
    ) -> None:
        """Each chord in progression dict should have unique ID."""
        inferred = [
            InferredChord(
                root="C", quality="", beat_position=0.0,
                measure_index=0, confidence=0.9
            ),
            InferredChord(
                root="G", quality="", beat_position=0.0,
                measure_index=1, confidence=0.85
            ),
        ]
        
        result = service.to_chord_progression_dict(inferred)
        
        # All IDs should be unique
        ids = [chord["id"] for chord in result["chords"]]
        ids.append(result["id"])
        assert len(ids) == len(set(ids))


class TestInferredChord:
    """Tests for InferredChord dataclass."""
    
    def test_symbol_property_major(self) -> None:
        """Major chord symbol is just root."""
        chord = InferredChord(
            root="C", quality="", beat_position=0.0,
            measure_index=0, confidence=0.9
        )
        assert chord.symbol == "C"
    
    def test_symbol_property_minor(self) -> None:
        """Minor chord symbol includes 'm'."""
        chord = InferredChord(
            root="D", quality="m", beat_position=0.0,
            measure_index=0, confidence=0.9
        )
        assert chord.symbol == "Dm"
    
    def test_symbol_property_seventh(self) -> None:
        """Seventh chord symbol includes quality."""
        chord = InferredChord(
            root="G", quality="7", beat_position=0.0,
            measure_index=0, confidence=0.9
        )
        assert chord.symbol == "G7"
    
    def test_symbol_property_major_seventh(self) -> None:
        """Major seventh chord symbol."""
        chord = InferredChord(
            root="F", quality="maj7", beat_position=0.0,
            measure_index=0, confidence=0.9
        )
        assert chord.symbol == "Fmaj7"
