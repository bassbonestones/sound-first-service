"""
Shared pytest fixtures and configuration for Sound First Service tests.
"""

import pytest
import os
import sys
from datetime import datetime

# Add the app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def test_musicxml():
    """Provide sample MusicXML content for tests."""
    return '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN" "http://www.musicxml.org/dtds/partwise.dtd">
<score-partwise version="3.1">
  <part-list>
    <score-part id="P1">
      <part-name>Test Part</part-name>
    </score-part>
  </part-list>
  <part id="P1">
    <measure number="1">
      <attributes>
        <divisions>1</divisions>
        <key><fifths>0</fifths></key>
        <time><beats>4</beats><beat-type>4</beat-type></time>
        <clef><sign>G</sign><line>2</line></clef>
      </attributes>
      <note>
        <pitch><step>C</step><octave>4</octave></pitch>
        <duration>4</duration>
        <type>whole</type>
      </note>
    </measure>
  </part>
</score-partwise>
'''


@pytest.fixture
def test_user_id():
    """Provide a test user ID."""
    return 99999  # High number unlikely to conflict


@pytest.fixture
def test_timestamp():
    """Provide a test timestamp."""
    return datetime(2026, 2, 28, 12, 0, 0)


class MockMaterial:
    """Mock material for testing without database."""
    def __init__(self, 
                 id=1,
                 title="Test Material",
                 required_capability_ids="",
                 original_key_center="C major",
                 allowed_keys="C,G,F,Bb",
                 pitch_low_stored=None,
                 pitch_high_stored=None,
                 pitch_ref_json=None,
                 musicxml_canonical=None):
        self.id = id
        self.title = title
        self.required_capability_ids = required_capability_ids
        self.original_key_center = original_key_center
        self.allowed_keys = allowed_keys
        self.pitch_low_stored = pitch_low_stored
        self.pitch_high_stored = pitch_high_stored
        self.pitch_ref_json = pitch_ref_json
        self.musicxml_canonical = musicxml_canonical


class MockFocusCard:
    """Mock focus card for testing without database."""
    def __init__(self,
                 id=1,
                 name="Test Focus Card",
                 description="A test focus card",
                 category="PHYSICAL",
                 attention_cue="Focus on tone",
                 micro_cues="[]",
                 prompts="{}"):
        self.id = id
        self.name = name
        self.description = description
        self.category = category
        self.attention_cue = attention_cue
        self.micro_cues = micro_cues
        self.prompts = prompts


class MockUser:
    """Mock user for testing without database."""
    def __init__(self,
                 id=1,
                 email="test@example.com",
                 name="Test User",
                 instrument="trumpet",
                 resonant_note="Bb3",
                 range_low="E3",
                 range_high="C6",
                 comfortable_capabilities="",
                 max_melodic_interval="M2",
                 cap_mask_0=0,
                 cap_mask_1=0,
                 cap_mask_2=0,
                 cap_mask_3=0,
                 cap_mask_4=0,
                 cap_mask_5=0,
                 cap_mask_6=0,
                 cap_mask_7=0):
        self.id = id
        self.email = email
        self.name = name
        self.instrument = instrument
        self.resonant_note = resonant_note
        self.range_low = range_low
        self.range_high = range_high
        self.comfortable_capabilities = comfortable_capabilities
        self.max_melodic_interval = max_melodic_interval
        # Bitmask columns for capability eligibility
        self.cap_mask_0 = cap_mask_0
        self.cap_mask_1 = cap_mask_1
        self.cap_mask_2 = cap_mask_2
        self.cap_mask_3 = cap_mask_3
        self.cap_mask_4 = cap_mask_4
        self.cap_mask_5 = cap_mask_5
        self.cap_mask_6 = cap_mask_6
        self.cap_mask_7 = cap_mask_7


@pytest.fixture
def mock_material():
    """Provide a mock material."""
    return MockMaterial()


@pytest.fixture
def mock_focus_card():
    """Provide a mock focus card."""
    return MockFocusCard()


@pytest.fixture
def mock_user():
    """Provide a mock user."""
    return MockUser()


@pytest.fixture
def mock_materials_list():
    """Provide a list of mock materials with different capabilities."""
    return [
        MockMaterial(id=1, title="Easy Piece", required_capability_ids="reading"),
        MockMaterial(id=2, title="Medium Piece", required_capability_ids="reading,rhythm"),
        MockMaterial(id=3, title="Hard Piece", required_capability_ids="reading,rhythm,range"),
        MockMaterial(id=4, title="No Requirements", required_capability_ids=""),
    ]


# Session-scoped fixture for database tests
@pytest.fixture(scope="session")
def db_session():
    """Create a database session for integration tests."""
    from app.db import get_db, Base, engine
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Get a session
    db = next(get_db())
    
    yield db
    
    # Cleanup
    db.close()
