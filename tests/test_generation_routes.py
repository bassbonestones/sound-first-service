"""Tests for generation routes (/generate/* endpoints).

Tests the content generation API endpoints including:
- POST /generate (pitch event generation)
- POST /generate/musicxml (MusicXML output)
- GET endpoints for available types and patterns
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.generation import router
from app.schemas.generation_schemas import (
    ArpeggioPattern,
    ArpeggioType,
    ArticulationType,
    DynamicType,
    GenerationType,
    MusicalKey,
    RhythmType,
    ScalePattern,
    ScaleType,
)


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="function")
def client() -> TestClient:
    """Create a test client for the generation router."""
    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def basic_scale_request() -> dict:
    """Basic scale generation request."""
    return {
        "content_type": "scale",
        "definition": "ionian",
        "octaves": 1,
        "rhythm": "quarter_notes",
    }


@pytest.fixture
def full_scale_request() -> dict:
    """Scale request with all optional parameters."""
    return {
        "content_type": "scale",
        "definition": "dorian",
        "octaves": 2,
        "pattern": "in_3rds",
        "rhythm": "eighth_notes",
        "key": "G",
        "dynamics": "crescendo",
        "articulation": "staccato",
        "range_spec": {"low_midi": 48, "high_midi": 84},
        "tempo_min_bpm": 80,
        "tempo_max_bpm": 120,
    }


@pytest.fixture
def arpeggio_request() -> dict:
    """Arpeggio generation request."""
    return {
        "content_type": "arpeggio",
        "definition": "maj7",
        "octaves": 2,
        "rhythm": "eighth_notes",
        "key": "Bb",
    }


# =============================================================================
# POST /generate TESTS
# =============================================================================

class TestGenerateEndpoint:
    """Tests for POST /generate endpoint."""

    def test_generate_basic_scale(self, client: TestClient, basic_scale_request: dict) -> None:
        """Test generating a basic scale returns expected response structure."""
        response = client.post("/generate", json=basic_scale_request)
        
        assert response.status_code == 200
        data = response.json()
        
        # Check response structure
        assert data["content_type"] == "scale"
        assert data["definition"] == "ionian"
        assert data["key"] == "C"  # Default key
        assert data["octaves"] == 1
        assert "events" in data
        assert isinstance(data["events"], list)
        assert len(data["events"]) > 0
        
        # Check event structure
        event = data["events"][0]
        assert "midi_note" in event
        assert "pitch_name" in event
        assert "duration_beats" in event

    def test_generate_with_all_options(self, client: TestClient, full_scale_request: dict) -> None:
        """Test generating with all optional parameters."""
        response = client.post("/generate", json=full_scale_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["content_type"] == "scale"
        assert data["definition"] == "dorian"
        assert data["key"] == "G"
        assert data["octaves"] == 2
        assert data["pattern"] == "in_3rds"
        assert data["rhythm"] == "eighth_notes"
        assert data["dynamics"] == "crescendo"
        assert data["articulation"] == "staccato"

    def test_generate_arpeggio(self, client: TestClient, arpeggio_request: dict) -> None:
        """Test generating an arpeggio."""
        response = client.post("/generate", json=arpeggio_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["content_type"] == "arpeggio"
        assert data["definition"] == "maj7"
        assert data["key"] == "Bb"

    def test_generate_with_pattern(self, client: TestClient) -> None:
        """Test generating with a pattern produces more events."""
        # Without pattern
        request_no_pattern = {
            "content_type": "scale",
            "definition": "ionian",
            "octaves": 1,
            "rhythm": "quarter_notes",
        }
        response_no_pattern = client.post("/generate", json=request_no_pattern)
        events_no_pattern = response_no_pattern.json()["events"]
        
        # With pattern
        request_with_pattern = {
            "content_type": "scale",
            "definition": "ionian",
            "octaves": 1,
            "rhythm": "quarter_notes",
            "pattern": "in_3rds",
        }
        response_with_pattern = client.post("/generate", json=request_with_pattern)
        events_with_pattern = response_with_pattern.json()["events"]
        
        # Pattern should produce different number of events
        assert len(events_with_pattern) != len(events_no_pattern)

    def test_generate_respects_key_transposition(self, client: TestClient) -> None:
        """Test that key parameter transposes the content."""
        # Generate in C
        request_c = {
            "content_type": "scale",
            "definition": "ionian",
            "octaves": 1,
            "rhythm": "quarter_notes",
            "key": "C",
        }
        response_c = client.post("/generate", json=request_c)
        events_c = response_c.json()["events"]
        
        # Generate in G
        request_g = {
            "content_type": "scale",
            "definition": "ionian",
            "octaves": 1,
            "rhythm": "quarter_notes",
            "key": "G",
        }
        response_g = client.post("/generate", json=request_g)
        events_g = response_g.json()["events"]
        
        # First note should differ by 7 semitones (C to G)
        assert events_g[0]["midi_note"] - events_c[0]["midi_note"] == 7

    def test_generate_lick_not_supported(self, client: TestClient) -> None:
        """Test that lick generation returns appropriate error."""
        request = {
            "content_type": "lick",
            "definition": "bebop_phrase_1",
            "octaves": 1,
            "rhythm": "eighth_notes",
        }
        response = client.post("/generate", json=request)
        
        assert response.status_code == 400
        assert "not yet supported" in response.json()["detail"].lower()

    def test_generate_missing_required_field(self, client: TestClient) -> None:
        """Test that missing required field returns 422."""
        request = {
            "content_type": "scale",
            # Missing definition
            "octaves": 1,
            "rhythm": "quarter_notes",
        }
        response = client.post("/generate", json=request)
        
        assert response.status_code == 422

    def test_generate_invalid_content_type(self, client: TestClient) -> None:
        """Test that invalid content_type returns 422."""
        request = {
            "content_type": "invalid_type",
            "definition": "ionian",
            "octaves": 1,
            "rhythm": "quarter_notes",
        }
        response = client.post("/generate", json=request)
        
        assert response.status_code == 422

    def test_generate_returns_metadata(self, client: TestClient, basic_scale_request: dict) -> None:
        """Test that response includes metadata fields."""
        response = client.post("/generate", json=basic_scale_request)
        data = response.json()
        
        # Should have range info
        assert "range_used_low_midi" in data
        assert "range_used_high_midi" in data
        assert data["range_used_low_midi"] is not None
        assert data["range_used_high_midi"] is not None
        
        # Should have total beats
        assert "total_beats" in data
        assert data["total_beats"] > 0

    def test_generate_event_has_correct_structure(self, client: TestClient, basic_scale_request: dict) -> None:
        """Test that each event has the correct structure."""
        response = client.post("/generate", json=basic_scale_request)
        events = response.json()["events"]
        
        for event in events:
            assert isinstance(event["midi_note"], int)
            assert event["midi_note"] >= 0
            assert event["midi_note"] <= 127
            
            assert isinstance(event["pitch_name"], str)
            assert len(event["pitch_name"]) >= 2  # e.g., "C4"
            
            assert isinstance(event["duration_beats"], (int, float))
            assert event["duration_beats"] > 0


# =============================================================================
# POST /generate/musicxml TESTS
# =============================================================================

class TestGenerateMusicXmlEndpoint:
    """Tests for POST /generate/musicxml endpoint."""

    def test_musicxml_returns_xml_content(self, client: TestClient, basic_scale_request: dict) -> None:
        """Test that musicxml endpoint returns valid XML."""
        response = client.post("/generate/musicxml", json=basic_scale_request)
        
        assert response.status_code == 200
        assert "<?xml" in response.text
        assert "score-partwise" in response.text

    def test_musicxml_content_type(self, client: TestClient, basic_scale_request: dict) -> None:
        """Test that response has correct content type."""
        response = client.post("/generate/musicxml", json=basic_scale_request)
        
        assert response.headers["content-type"] == "application/vnd.recordare.musicxml+xml"

    def test_musicxml_has_content_disposition(self, client: TestClient, basic_scale_request: dict) -> None:
        """Test that response includes download filename."""
        response = client.post("/generate/musicxml", json=basic_scale_request)
        
        assert "content-disposition" in response.headers
        assert "attachment" in response.headers["content-disposition"]
        assert ".musicxml" in response.headers["content-disposition"]

    def test_musicxml_with_custom_title(self, client: TestClient, basic_scale_request: dict) -> None:
        """Test that custom title is included in MusicXML."""
        response = client.post(
            "/generate/musicxml",
            json=basic_scale_request,
            params={"title": "My Custom Title"},
        )
        
        assert response.status_code == 200
        assert "My Custom Title" in response.text

    def test_musicxml_contains_notes(self, client: TestClient, basic_scale_request: dict) -> None:
        """Test that MusicXML contains note elements."""
        response = client.post("/generate/musicxml", json=basic_scale_request)
        
        assert "<note>" in response.text
        assert "<pitch>" in response.text
        assert "<step>" in response.text
        assert "<octave>" in response.text

    def test_musicxml_lick_not_supported(self, client: TestClient) -> None:
        """Test that lick musicxml generation returns appropriate error."""
        request = {
            "content_type": "lick",
            "definition": "bebop_phrase_1",
            "octaves": 1,
            "rhythm": "eighth_notes",
        }
        response = client.post("/generate/musicxml", json=request)
        
        assert response.status_code == 400


# =============================================================================
# GET ENDPOINT TESTS
# =============================================================================

class TestGetScaleTypes:
    """Tests for GET /generate/scale-types endpoint."""

    def test_returns_list(self, client: TestClient) -> None:
        """Test that endpoint returns a list."""
        response = client.get("/generate/scale-types")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_contains_expected_scales(self, client: TestClient) -> None:
        """Test that response contains expected scale types."""
        response = client.get("/generate/scale-types")
        scale_types = response.json()
        
        # Check for major modes
        assert "ionian" in scale_types
        assert "dorian" in scale_types
        assert "mixolydian" in scale_types
        
        # Check for other scale types
        assert "harmonic_minor" in scale_types
        assert "pentatonic_major" in scale_types
        assert "blues" in scale_types

    def test_matches_enum_count(self, client: TestClient) -> None:
        """Test that response count matches ScaleType enum."""
        response = client.get("/generate/scale-types")
        
        assert len(response.json()) == len(ScaleType)


class TestGetArpeggioTypes:
    """Tests for GET /generate/arpeggio-types endpoint."""

    def test_returns_list(self, client: TestClient) -> None:
        """Test that endpoint returns a list."""
        response = client.get("/generate/arpeggio-types")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_contains_expected_arpeggios(self, client: TestClient) -> None:
        """Test that response contains expected arpeggio types."""
        response = client.get("/generate/arpeggio-types")
        arpeggio_types = response.json()
        
        # Check for triads
        assert "major" in arpeggio_types
        assert "minor" in arpeggio_types
        
        # Check for 7th chords
        assert "maj7" in arpeggio_types
        assert "dom7" in arpeggio_types
        assert "min7" in arpeggio_types

    def test_matches_enum_count(self, client: TestClient) -> None:
        """Test that response count matches ArpeggioType enum."""
        response = client.get("/generate/arpeggio-types")
        
        assert len(response.json()) == len(ArpeggioType)


class TestGetScalePatterns:
    """Tests for GET /generate/scale-patterns endpoint."""

    def test_returns_list(self, client: TestClient) -> None:
        """Test that endpoint returns a list."""
        response = client.get("/generate/scale-patterns")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_contains_expected_patterns(self, client: TestClient) -> None:
        """Test that response contains expected patterns."""
        response = client.get("/generate/scale-patterns")
        patterns = response.json()
        
        assert "in_3rds" in patterns
        assert "in_4ths" in patterns
        assert "groups_of_4" in patterns

    def test_matches_enum_count(self, client: TestClient) -> None:
        """Test that response count matches ScalePattern enum."""
        response = client.get("/generate/scale-patterns")
        
        assert len(response.json()) == len(ScalePattern)


class TestGetArpeggioPatterns:
    """Tests for GET /generate/arpeggio-patterns endpoint."""

    def test_returns_list(self, client: TestClient) -> None:
        """Test that endpoint returns a list."""
        response = client.get("/generate/arpeggio-patterns")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_matches_enum_count(self, client: TestClient) -> None:
        """Test that response count matches ArpeggioPattern enum."""
        response = client.get("/generate/arpeggio-patterns")
        
        assert len(response.json()) == len(ArpeggioPattern)


class TestGetRhythmTypes:
    """Tests for GET /generate/rhythm-types endpoint."""

    def test_returns_list(self, client: TestClient) -> None:
        """Test that endpoint returns a list."""
        response = client.get("/generate/rhythm-types")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_contains_expected_rhythms(self, client: TestClient) -> None:
        """Test that response contains expected rhythm types."""
        response = client.get("/generate/rhythm-types")
        rhythms = response.json()
        
        assert "quarter_notes" in rhythms
        assert "eighth_notes" in rhythms
        assert "eighth_triplets" in rhythms

    def test_matches_enum_count(self, client: TestClient) -> None:
        """Test that response count matches RhythmType enum."""
        response = client.get("/generate/rhythm-types")
        
        assert len(response.json()) == len(RhythmType)


class TestGetKeys:
    """Tests for GET /generate/keys endpoint."""

    def test_returns_list(self, client: TestClient) -> None:
        """Test that endpoint returns a list."""
        response = client.get("/generate/keys")
        
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_contains_expected_keys(self, client: TestClient) -> None:
        """Test that response contains expected keys."""
        response = client.get("/generate/keys")
        keys = response.json()
        
        # Natural keys
        assert "C" in keys
        assert "G" in keys
        assert "F" in keys
        
        # Sharp keys
        assert "F#" in keys
        
        # Flat keys
        assert "Bb" in keys
        assert "Eb" in keys

    def test_matches_enum_count(self, client: TestClient) -> None:
        """Test that response count matches MusicalKey enum."""
        response = client.get("/generate/keys")
        
        assert len(response.json()) == len(MusicalKey)

    def test_contains_all_12_keys(self, client: TestClient) -> None:
        """Test that all 12 chromatic keys are present."""
        response = client.get("/generate/keys")
        keys = response.json()
        
        # Should have at least 12 distinct keys (some may have enharmonic variants)
        assert len(keys) >= 12


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestGenerationIntegration:
    """Integration tests for generation workflow."""

    def test_generate_all_scale_types(self, client: TestClient) -> None:
        """Test that all scale types can be generated."""
        scale_types_response = client.get("/generate/scale-types")
        scale_types = scale_types_response.json()
        
        # Test a sample of scale types (not all to keep tests fast)
        sample_scales = scale_types[:5]
        
        for scale_type in sample_scales:
            request = {
                "content_type": "scale",
                "definition": scale_type,
                "octaves": 1,
                "rhythm": "quarter_notes",
            }
            response = client.post("/generate", json=request)
            assert response.status_code == 200, f"Failed for scale type: {scale_type}"
            assert len(response.json()["events"]) > 0

    def test_generate_all_arpeggio_types(self, client: TestClient) -> None:
        """Test that all arpeggio types can be generated."""
        arpeggio_types_response = client.get("/generate/arpeggio-types")
        arpeggio_types = arpeggio_types_response.json()
        
        # Test a sample of arpeggio types
        sample_arpeggios = arpeggio_types[:5]
        
        for arpeggio_type in sample_arpeggios:
            request = {
                "content_type": "arpeggio",
                "definition": arpeggio_type,
                "octaves": 1,
                "rhythm": "quarter_notes",
            }
            response = client.post("/generate", json=request)
            assert response.status_code == 200, f"Failed for arpeggio type: {arpeggio_type}"
            assert len(response.json()["events"]) > 0

    def test_generate_all_keys(self, client: TestClient) -> None:
        """Test that content can be generated in all keys."""
        keys_response = client.get("/generate/keys")
        keys = keys_response.json()
        
        for key in keys:
            request = {
                "content_type": "scale",
                "definition": "ionian",
                "octaves": 1,
                "rhythm": "quarter_notes",
                "key": key,
            }
            response = client.post("/generate", json=request)
            assert response.status_code == 200, f"Failed for key: {key}"
            assert response.json()["key"] == key

    def test_full_workflow(self, client: TestClient) -> None:
        """Test a full workflow: query types, generate, export to MusicXML."""
        # 1. Get available scale types
        scale_types = client.get("/generate/scale-types").json()
        assert len(scale_types) > 0
        
        # 2. Get available patterns
        patterns = client.get("/generate/scale-patterns").json()
        assert len(patterns) > 0
        
        # 3. Get available keys
        keys = client.get("/generate/keys").json()
        assert len(keys) > 0
        
        # 4. Generate content
        request = {
            "content_type": "scale",
            "definition": scale_types[0],
            "octaves": 2,
            "pattern": patterns[0],
            "rhythm": "eighth_notes",
            "key": keys[0],
        }
        generate_response = client.post("/generate", json=request)
        assert generate_response.status_code == 200
        events = generate_response.json()["events"]
        assert len(events) > 0
        
        # 5. Export to MusicXML
        musicxml_response = client.post("/generate/musicxml", json=request)
        assert musicxml_response.status_code == 200
        assert "<?xml" in musicxml_response.text
        assert "<note>" in musicxml_response.text
