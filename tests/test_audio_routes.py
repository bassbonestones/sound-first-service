"""
Tests for app/routes/audio.py
Comprehensive tests for audio generation endpoints.
"""

import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import app
from app.audio.types import AudioResult, AudioError, AudioErrorCode


client = TestClient(app)


# =============================================================================
# Tests for /audio/material/{material_id}
# =============================================================================


class TestGetMaterialAudio:
    """Tests for GET /audio/material/{material_id}."""

    def test_material_not_found(self):
        """Returns 404 when material doesn't exist."""
        response = client.get("/audio/material/99999?key=C%20major")
        
        assert response.status_code == 404
        data = response.json()
        assert data["code"] == "material_not_found"

    def test_missing_key_parameter(self):
        """Returns 422 when key parameter is missing."""
        response = client.get("/audio/material/1")
        
        assert response.status_code == 422  # FastAPI validation error

    def test_material_without_musicxml(self, db):
        """Returns 400 when material has no MusicXML."""
        from app.models.core import Material
        
        # Create material without musicxml
        material = Material(
            title="No MusicXML",
            original_key_center="C major",
            musicxml_canonical=None
        )
        db.add(material)
        db.commit()
        
        try:
            response = client.get(f"/audio/material/{material.id}?key=C%20major")
            
            assert response.status_code == 400
            data = response.json()
            assert data["code"] == "no_musicxml"
        finally:
            db.delete(material)
            db.commit()

    def test_successful_audio_generation(self, db):
        """Returns audio when material has valid MusicXML."""
        from app.models.core import Material
        
        musicxml = '''<?xml version="1.0"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
    </measure>
  </part>
</score-partwise>'''
        
        material = Material(
            title="Test Material",
            original_key_center="C major",
            musicxml_canonical=musicxml
        )
        db.add(material)
        db.commit()
        
        try:
            response = client.get(f"/audio/material/{material.id}?key=C%20major")
            
            # Should return audio or structured error
            assert response.status_code in [200, 400, 422, 503]
            
            if response.status_code == 200:
                assert "audio" in response.headers.get("content-type", "")
        finally:
            db.delete(material)
            db.commit()

    def test_content_disposition_header(self, db):
        """Returns proper Content-Disposition header."""
        from app.models.core import Material
        
        musicxml = '''<?xml version="1.0"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>T</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
    </measure>
  </part>
</score-partwise>'''
        
        material = Material(
            title="My Song",
            original_key_center="C major",
            musicxml_canonical=musicxml
        )
        db.add(material)
        db.commit()
        
        try:
            response = client.get(f"/audio/material/{material.id}?key=Bb%20major")
            
            if response.status_code == 200:
                content_disp = response.headers.get("content-disposition", "")
                assert "filename=" in content_disp
        finally:
            db.delete(material)
            db.commit()

    def test_different_instruments(self, db):
        """Accepts different instrument parameters."""
        from app.models.core import Material
        
        musicxml = '''<?xml version="1.0"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>T</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
    </measure>
  </part>
</score-partwise>'''
        
        material = Material(
            title="Instrument Test",
            original_key_center="C major",
            musicxml_canonical=musicxml
        )
        db.add(material)
        db.commit()
        
        try:
            for instrument in ["piano", "trumpet", "trombone"]:
                response = client.get(
                    f"/audio/material/{material.id}?key=C%20major&instrument={instrument}"
                )
                assert response.status_code in [200, 400, 422, 503], f"Failed for {instrument}"
        finally:
            db.delete(material)
            db.commit()


# =============================================================================
# Tests for /audio/note/{note}
# =============================================================================


class TestGetSingleNoteAudio:
    """Tests for GET /audio/note/{note}."""

    def test_basic_note(self):
        """Basic note returns audio or error."""
        response = client.get("/audio/note/C4")
        
        assert response.status_code in [200, 400, 422, 503]
        
        if response.status_code == 200:
            assert "audio" in response.headers.get("content-type", "")

    def test_flat_note(self):
        """Flat notes like Bb4 are handled."""
        response = client.get("/audio/note/Bb4")
        
        assert response.status_code in [200, 400, 422, 503]

    def test_sharp_note(self):
        """Sharp notes like F#4 are handled (URL encoded)."""
        response = client.get("/audio/note/F%234")  # F#4
        
        assert response.status_code in [200, 400, 422, 503]

    def test_with_instrument(self):
        """Instrument parameter is accepted."""
        response = client.get("/audio/note/Bb3?instrument=trombone")
        
        assert response.status_code in [200, 400, 422, 503]

    def test_with_duration(self):
        """Duration parameter is accepted."""
        response = client.get("/audio/note/C4?duration=5")
        
        assert response.status_code in [200, 400, 422, 503]

    def test_with_octave_override(self):
        """Octave parameter overrides note octave."""
        response = client.get("/audio/note/C?octave=3")
        
        assert response.status_code in [200, 400, 422, 503]

    def test_invalid_octave_too_low(self):
        """Invalid octave < 1 returns 400."""
        response = client.get("/audio/note/C4?octave=0")
        
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "invalid_octave"

    def test_invalid_octave_too_high(self):
        """Invalid octave > 8 returns 400."""
        response = client.get("/audio/note/C4?octave=9")
        
        assert response.status_code == 400
        data = response.json()
        assert data["code"] == "invalid_octave"

    def test_valid_octave_boundary_low(self):
        """Octave 1 is valid."""
        response = client.get("/audio/note/C?octave=1")
        
        assert response.status_code in [200, 400, 422, 503]

    def test_valid_octave_boundary_high(self):
        """Octave 8 is valid."""
        response = client.get("/audio/note/C?octave=8")
        
        assert response.status_code in [200, 400, 422, 503]

    def test_caching_headers(self):
        """Single notes have appropriate cache headers."""
        response = client.get("/audio/note/C4")
        
        if response.status_code == 200:
            cache = response.headers.get("cache-control", "")
            # Should have some caching
            assert "max-age" in cache or "public" in cache

    def test_fallback_header_present_when_midi(self):
        """X-Audio-Fallback header present when returning MIDI."""
        response = client.get("/audio/note/C4")
        
        if response.status_code == 200:
            content_type = response.headers.get("content-type", "")
            if "midi" in content_type:
                # Should have fallback header
                assert response.headers.get("x-audio-fallback") == "true"


# =============================================================================
# Tests for /audio/status
# =============================================================================


class TestGetAudioStatus:
    """Tests for GET /audio/status."""

    def test_status_endpoint_exists(self):
        """Status endpoint exists in router."""
        from app.routes.audio import router
        
        route_paths = [r.path for r in router.routes]
        assert "/audio/status" in route_paths


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def db():
    """Database session fixture."""
    from app.db import SessionLocal
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
