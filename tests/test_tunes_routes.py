"""Tests for tune CRUD endpoints.

Tests the /tunes API endpoints for creating, reading, updating, and deleting
user-composed tunes with chord progressions.
"""
import json
import pytest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.db import get_db, Base, engine
from app.models.core import User, Tune
from app.schemas.tune_schemas import (
    TuneCreate,
    TuneUpdate,
    TimeSignature,
    ChordProgression,
    ChordSymbol,
    DisplaySettings,
    PlaybackSettings,
)


@pytest.fixture(scope="module")
def client():
    """Create test client with database setup."""
    # Drop and recreate tunes table for clean state
    Tune.__table__.drop(bind=engine, checkfirst=True)
    Tune.__table__.create(bind=engine, checkfirst=True)
    
    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_user_id(client):
    """Get or create a test user and return their ID."""
    db = next(get_db())
    user = db.query(User).first()
    if not user:
        user = User(email="test@example.com", name="Test User")
        db.add(user)
        db.commit()
        db.refresh(user)
    return user.id


@pytest.fixture
def cleanup_tunes(test_user_id):
    """Clean up tunes after each test."""
    yield
    db = next(get_db())
    db.query(Tune).filter(Tune.user_id == test_user_id).delete()
    db.commit()


class TestTuneSchemas:
    """Test Pydantic schema validation."""
    
    def test_time_signature_validation(self):
        """Test time signature validates beats and beat unit."""
        ts = TimeSignature(beats=4, beatUnit=4)
        assert ts.beats == 4
        assert ts.beatUnit == 4
        
    def test_time_signature_invalid_beats(self):
        """Test time signature rejects invalid beats."""
        with pytest.raises(ValueError, match="beats must be between"):
            TimeSignature(beats=0, beatUnit=4)
            
    def test_time_signature_invalid_beat_unit(self):
        """Test time signature rejects invalid beat unit."""
        with pytest.raises(ValueError, match="beatUnit must be one of"):
            TimeSignature(beats=4, beatUnit=3)
            
    def test_tune_create_validation(self):
        """Test tune create validates required fields."""
        tune = TuneCreate(
            title="My Tune",
            measures_json='[{"id": "m1", "notes": []}]'
        )
        assert tune.title == "My Tune"
        assert tune.clef == "treble"
        assert tune.key_signature == 0
        
    def test_tune_create_empty_title(self):
        """Test tune create rejects empty title."""
        with pytest.raises(ValueError, match="title cannot be empty"):
            TuneCreate(title="", measures_json='[]')
            
    def test_tune_create_invalid_clef(self):
        """Test tune create rejects invalid clef."""
        with pytest.raises(ValueError, match="clef must be"):
            TuneCreate(title="Test", clef="alto", measures_json='[]')
            
    def test_tune_create_invalid_key_signature(self):
        """Test tune create rejects key signature out of range."""
        with pytest.raises(ValueError, match="key_signature must be"):
            TuneCreate(title="Test", key_signature=10, measures_json='[]')
            
    def test_tune_create_invalid_tempo(self):
        """Test tune create rejects tempo out of range."""
        with pytest.raises(ValueError, match="tempo must be"):
            TuneCreate(title="Test", tempo=500, measures_json='[]')
            
    def test_tune_create_with_chord_progressions(self):
        """Test tune create with chord progressions."""
        tune = TuneCreate(
            title="Jazz Tune",
            measures_json='[]',
            chord_progressions=[
                ChordProgression(
                    id="prog1",
                    name="Default",
                    isDefault=True,
                    chords=[
                        ChordSymbol(
                            id="c1",
                            symbol="Cmaj7",
                            beatPosition=0,
                            measureIndex=0
                        )
                    ]
                )
            ]
        )
        assert len(tune.chord_progressions) == 1
        assert tune.chord_progressions[0].chords[0].symbol == "Cmaj7"


class TestCreateTune:
    """Test POST /tunes endpoint."""
    
    def test_create_tune_success(self, client, test_user_id, cleanup_tunes):
        """Test creating a tune successfully."""
        response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Test Tune"
        assert data["clef"] == "treble"
        assert data["key_signature"] == 0
        assert data["tempo"] == 120
        
    def test_create_tune_with_chords(self, client, test_user_id, cleanup_tunes):
        """Test creating a tune with chord progressions."""
        response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Jazz Tune",
                "measures_json": '[{"id": "m1", "notes": []}]',
                "chord_progressions": [{
                    "id": "prog1",
                    "name": "Default",
                    "isDefault": True,
                    "chords": [
                        {"id": "c1", "symbol": "Dm7", "beatPosition": 0, "measureIndex": 0},
                        {"id": "c2", "symbol": "G7", "beatPosition": 2, "measureIndex": 0},
                        {"id": "c3", "symbol": "Cmaj7", "beatPosition": 0, "measureIndex": 1},
                    ]
                }]
            }
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data["chord_progressions"]) == 1
        assert data["chord_progressions"][0]["name"] == "Default"
        assert len(data["chord_progressions"][0]["chords"]) == 3
        
    def test_create_tune_user_not_found(self, client):
        """Test creating tune with invalid user returns 404."""
        response = client.post(
            "/tunes?user_id=999999",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        
        assert response.status_code == 404
        assert "User not found" in response.json()["detail"]


class TestListTunes:
    """Test GET /tunes endpoint."""
    
    def test_list_tunes_empty(self, client, test_user_id, cleanup_tunes):
        """Test listing tunes when none exist."""
        response = client.get(f"/tunes?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["tunes"] == []
        assert data["total_count"] == 0
        
    def test_list_tunes_with_results(self, client, test_user_id, cleanup_tunes):
        """Test listing tunes returns results."""
        # Create a tune first
        client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        
        response = client.get(f"/tunes?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["tunes"]) == 1
        assert data["tunes"][0]["title"] == "Test Tune"
        assert data["total_count"] == 1


class TestGetTune:
    """Test GET /tunes/{tune_id} endpoint."""
    
    def test_get_tune_success(self, client, test_user_id, cleanup_tunes):
        """Test getting a tune by ID."""
        # Create a tune first
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.get(f"/tunes/{tune_id}?user_id={test_user_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tune_id
        assert data["title"] == "Test Tune"
        
    def test_get_tune_not_found(self, client, test_user_id):
        """Test getting non-existent tune returns 404."""
        response = client.get(f"/tunes/999999?user_id={test_user_id}")
        
        assert response.status_code == 404
        assert "Tune not found" in response.json()["detail"]


class TestUpdateTune:
    """Test PUT /tunes/{tune_id} endpoint."""
    
    def test_update_tune_title(self, client, test_user_id, cleanup_tunes):
        """Test updating tune title."""
        # Create a tune first
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Original Title",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.put(
            f"/tunes/{tune_id}?user_id={test_user_id}",
            json={"title": "Updated Title"}
        )
        
        assert response.status_code == 200
        assert response.json()["title"] == "Updated Title"
        
    def test_update_tune_chord_progressions(self, client, test_user_id, cleanup_tunes):
        """Test updating tune chord progressions."""
        # Create a tune first
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.put(
            f"/tunes/{tune_id}?user_id={test_user_id}",
            json={
                "chord_progressions": [{
                    "id": "prog1",
                    "name": "Jazz Changes",
                    "isDefault": True,
                    "chords": [
                        {"id": "c1", "symbol": "Dm7", "beatPosition": 0, "measureIndex": 0},
                        {"id": "c2", "symbol": "G7", "beatPosition": 2, "measureIndex": 0},
                    ]
                }]
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["chord_progressions"]) == 1
        assert data["chord_progressions"][0]["name"] == "Jazz Changes"

    def test_update_tune_clef(self, client, test_user_id, cleanup_tunes):
        """Test updating tune clef."""
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.put(
            f"/tunes/{tune_id}?user_id={test_user_id}",
            json={"clef": "bass"}
        )
        
        assert response.status_code == 200
        assert response.json()["clef"] == "bass"

    def test_update_tune_key_signature(self, client, test_user_id, cleanup_tunes):
        """Test updating tune key signature."""
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.put(
            f"/tunes/{tune_id}?user_id={test_user_id}",
            json={"key_signature": 1}  # 1 sharp (G major)
        )
        
        assert response.status_code == 200
        assert response.json()["key_signature"] == 1

    def test_update_tune_time_signature(self, client, test_user_id, cleanup_tunes):
        """Test updating tune time signature."""
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.put(
            f"/tunes/{tune_id}?user_id={test_user_id}",
            json={"time_signature": {"beats": 3, "beatUnit": 4}}
        )
        
        assert response.status_code == 200
        assert response.json()["time_signature"]["beats"] == 3

    def test_update_tune_tempo(self, client, test_user_id, cleanup_tunes):
        """Test updating tune tempo."""
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.put(
            f"/tunes/{tune_id}?user_id={test_user_id}",
            json={"tempo": 140}
        )
        
        assert response.status_code == 200
        assert response.json()["tempo"] == 140

    def test_update_tune_measures_json(self, client, test_user_id, cleanup_tunes):
        """Test updating tune measures_json."""
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.put(
            f"/tunes/{tune_id}?user_id={test_user_id}",
            json={"measures_json": '[{"id": "m2", "notes": [{"pitch": "C4"}]}]'}
        )
        
        assert response.status_code == 200
        assert "m2" in response.json()["measures_json"]

    def test_update_tune_not_found(self, client, test_user_id, cleanup_tunes):
        """Test updating non-existent tune returns 404."""
        response = client.put(
            f"/tunes/9999?user_id={test_user_id}",
            json={"title": "Updated Title"}
        )
        
        assert response.status_code == 404


class TestDeleteTune:
    """Test DELETE /tunes/{tune_id} endpoint."""
    
    def test_delete_tune_archives(self, client, test_user_id, cleanup_tunes):
        """Test deleting tune archives it by default."""
        # Create a tune first
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.delete(f"/tunes/{tune_id}?user_id={test_user_id}")
        
        assert response.status_code == 204
        
        # Verify it's archived (not in default list)
        list_response = client.get(f"/tunes?user_id={test_user_id}")
        assert list_response.json()["total_count"] == 0
        
        # But visible with include_archived
        list_archived = client.get(f"/tunes?user_id={test_user_id}&include_archived=true")
        assert list_archived.json()["total_count"] == 1

    def test_delete_tune_permanent(self, client, test_user_id, cleanup_tunes):
        """Test permanently deleting a tune."""
        # Create a tune first
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.delete(f"/tunes/{tune_id}?user_id={test_user_id}&permanent=true")
        
        assert response.status_code == 204
        
        # Verify it's gone completely (not even in archived)
        list_archived = client.get(f"/tunes?user_id={test_user_id}&include_archived=true")
        assert list_archived.json()["total_count"] == 0

    def test_delete_tune_not_found(self, client, test_user_id, cleanup_tunes):
        """Test deleting non-existent tune returns 404."""
        response = client.delete(f"/tunes/9999?user_id={test_user_id}")
        
        assert response.status_code == 404


class TestRestoreTune:
    """Test POST /tunes/{tune_id}/restore endpoint."""
    
    def test_restore_tune_success(self, client, test_user_id, cleanup_tunes):
        """Test restoring an archived tune."""
        # Create and archive a tune
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": '[{"id": "m1", "notes": []}]'
            }
        )
        tune_id = create_response.json()["id"]
        client.delete(f"/tunes/{tune_id}?user_id={test_user_id}")
        
        # Restore it
        response = client.post(f"/tunes/{tune_id}/restore?user_id={test_user_id}")
        
        assert response.status_code == 200
        assert response.json()["is_archived"] == False


class TestDuplicateTune:
    """Test POST /tunes/{tune_id}/duplicate endpoint."""
    
    def test_duplicate_tune_success(self, client, test_user_id, cleanup_tunes):
        """Test duplicating a tune."""
        # Create a tune first
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Original Tune",
                "measures_json": '[{"id": "m1", "notes": []}]',
                "chord_progressions": [{
                    "id": "prog1",
                    "name": "Default",
                    "isDefault": True,
                    "chords": [
                        {"id": "c1", "symbol": "Cmaj7", "beatPosition": 0, "measureIndex": 0}
                    ]
                }]
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.post(f"/tunes/{tune_id}/duplicate?user_id={test_user_id}")
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Original Tune (Copy)"
        assert data["id"] != tune_id
        # Chord progressions should be copied
        assert len(data["chord_progressions"]) == 1


class TestInferChords:
    """Test POST /tunes/{tune_id}/infer-chords endpoint."""
    
    def test_infer_chords_c_major_arpeggio(self, client, test_user_id, cleanup_tunes):
        """Test inferring chords from a C major arpeggio melody."""
        # C4, E4, G4, C5 - should infer C major
        measures = [
            {
                "id": "m1",
                "notes": [
                    {"pitch": 60, "duration": 1.0},
                    {"pitch": 64, "duration": 1.0},
                    {"pitch": 67, "duration": 1.0},
                    {"pitch": 72, "duration": 1.0},
                ]
            }
        ]
        
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": json.dumps(measures),
                "key_signature": 0,
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.post(
            f"/tunes/{tune_id}/infer-chords?user_id={test_user_id}",
            json={"use_seventh_chords": False, "chords_per_measure": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chord_count"] == 1
        assert data["progression"]["isAutoInferred"] is True
        assert data["progression"]["isSystemDefined"] is True
        assert len(data["progression"]["chords"]) == 1
        assert data["progression"]["chords"][0]["symbol"] == "C"
    
    def test_infer_chords_with_seventh_chords(self, client, test_user_id, cleanup_tunes):
        """Test inferring seventh chords."""
        measures = [
            {
                "id": "m1",
                "notes": [
                    {"pitch": 60, "duration": 1.0},  # C4
                    {"pitch": 64, "duration": 1.0},  # E4
                    {"pitch": 67, "duration": 1.0},  # G4
                    {"pitch": 60, "duration": 1.0},  # C4
                ]
            }
        ]
        
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": json.dumps(measures),
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.post(
            f"/tunes/{tune_id}/infer-chords?user_id={test_user_id}",
            json={"use_seventh_chords": True, "chords_per_measure": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should infer Cmaj7 with seventh chords enabled
        assert data["progression"]["chords"][0]["symbol"] == "Cmaj7"
    
    def test_infer_chords_multiple_measures(self, client, test_user_id, cleanup_tunes):
        """Test inferring chords for multiple measures."""
        measures = [
            {"id": "m1", "notes": [
                {"pitch": 60, "duration": 2.0}, {"pitch": 64, "duration": 2.0}
            ]},
            {"id": "m2", "notes": [
                {"pitch": 67, "duration": 2.0}, {"pitch": 71, "duration": 2.0}
            ]},
            {"id": "m3", "notes": [
                {"pitch": 65, "duration": 2.0}, {"pitch": 69, "duration": 2.0}
            ]},
        ]
        
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": json.dumps(measures),
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.post(
            f"/tunes/{tune_id}/infer-chords?user_id={test_user_id}",
            json={"use_seventh_chords": False, "chords_per_measure": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chord_count"] == 3
        assert len(data["progression"]["chords"]) == 3
    
    def test_infer_chords_two_per_measure(self, client, test_user_id, cleanup_tunes):
        """Test inferring two chords per measure."""
        measures = [
            {
                "id": "m1",
                "notes": [
                    {"pitch": 60, "duration": 1.0},
                    {"pitch": 64, "duration": 1.0},
                    {"pitch": 67, "duration": 1.0},
                    {"pitch": 71, "duration": 1.0},
                ]
            }
        ]
        
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": json.dumps(measures),
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.post(
            f"/tunes/{tune_id}/infer-chords?user_id={test_user_id}",
            json={"use_seventh_chords": False, "chords_per_measure": 2}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chord_count"] == 2
        assert len(data["progression"]["chords"]) == 2
        # First chord at beat 0, second at beat 2
        assert data["progression"]["chords"][0]["beatPosition"] == 0.0
        assert data["progression"]["chords"][1]["beatPosition"] == 2.0
    
    def test_infer_chords_tune_not_found(self, client, test_user_id):
        """Test inferring chords for non-existent tune returns 404."""
        response = client.post(
            f"/tunes/999999/infer-chords?user_id={test_user_id}",
            json={"use_seventh_chords": True, "chords_per_measure": 1}
        )
        
        assert response.status_code == 404
        assert "Tune not found" in response.json()["detail"]
    
    def test_infer_chords_f_major_key(self, client, test_user_id, cleanup_tunes):
        """Test inferring chords in F major (uses flat spellings)."""
        # Bb major arpeggio (IV chord in F major)
        measures = [
            {
                "id": "m1",
                "notes": [
                    {"pitch": 70, "duration": 1.0},  # Bb4
                    {"pitch": 74, "duration": 1.0},  # D5
                    {"pitch": 77, "duration": 1.0},  # F5
                    {"pitch": 70, "duration": 1.0},  # Bb4
                ]
            }
        ]
        
        create_response = client.post(
            f"/tunes?user_id={test_user_id}",
            json={
                "title": "Test Tune",
                "measures_json": json.dumps(measures),
                "key_signature": -1,  # F major
            }
        )
        tune_id = create_response.json()["id"]
        
        response = client.post(
            f"/tunes/{tune_id}/infer-chords?user_id={test_user_id}",
            json={"use_seventh_chords": False, "chords_per_measure": 1}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Should use Bb (flat spelling) not A#
        assert data["progression"]["chords"][0]["symbol"] == "Bb"


class TestAnalyzeChords:
    """Test POST /tunes/analyze-chords endpoint."""
    
    def test_analyze_chords_basic(self, client):
        """Test analyzing melody data directly without a saved tune."""
        measures = [
            {
                "id": "m1",
                "notes": [
                    {"pitch": 60, "duration": 1.0},  # C4
                    {"pitch": 64, "duration": 1.0},  # E4
                    {"pitch": 67, "duration": 1.0},  # G4
                    {"pitch": 72, "duration": 1.0},  # C5
                ]
            }
        ]
        
        response = client.post(
            "/tunes/analyze-chords",
            json={
                "measures_json": json.dumps(measures),
                "key_signature": 0,
                "time_signature": {"beats": 4, "beatUnit": 4},
                "use_seventh_chords": False,
                "chords_per_measure": 1,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chord_count"] == 1
        assert data["progression"]["isAutoInferred"] is True
        assert data["progression"]["chords"][0]["symbol"] == "C"
    
    def test_analyze_chords_with_defaults(self, client):
        """Test that default values work correctly."""
        measures = [
            {
                "id": "m1",
                "notes": [
                    {"pitch": 60, "duration": 1.0},
                    {"pitch": 64, "duration": 1.0},
                    {"pitch": 67, "duration": 1.0},
                    {"pitch": 60, "duration": 1.0},
                ]
            }
        ]
        
        response = client.post(
            "/tunes/analyze-chords",
            json={"measures_json": json.dumps(measures)}
        )
        
        assert response.status_code == 200
        data = response.json()
        # Default is seventh chords enabled
        assert data["progression"]["chords"][0]["symbol"] == "Cmaj7"
    
    def test_analyze_chords_multiple_measures(self, client):
        """Test analyzing multiple measures."""
        measures = [
            {"id": "m1", "notes": [
                {"pitch": 60, "duration": 2.0}, {"pitch": 64, "duration": 2.0}
            ]},
            {"id": "m2", "notes": [
                {"pitch": 67, "duration": 2.0}, {"pitch": 71, "duration": 2.0}
            ]},
        ]
        
        response = client.post(
            "/tunes/analyze-chords",
            json={
                "measures_json": json.dumps(measures),
                "chords_per_measure": 1,
            }
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["chord_count"] == 2


