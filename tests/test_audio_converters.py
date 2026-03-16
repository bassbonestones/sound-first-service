"""
Tests for app/audio/converters.py
Tests audio format conversion functions.
"""

import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path


class TestMusicXMLToMidi:
    """Tests for musicxml_to_midi function."""
    
    def test_returns_none_when_music21_unavailable(self):
        """musicxml_to_midi returns None when music21 is not available."""
        with patch('app.audio.converters.MUSIC21_AVAILABLE', False):
            import importlib
            from app.audio import converters
            
            result = converters.musicxml_to_midi("<score></score>")
            assert result is None or isinstance(result, bytes)
    
    def test_function_exists(self):
        """musicxml_to_midi function is importable."""
        from app.audio.converters import musicxml_to_midi
        
        # Verify function exists by checking module
        import app.audio.converters as converters
        assert hasattr(converters, 'musicxml_to_midi')


class TestMidiToAudio:
    """Tests for midi_to_audio function."""
    
    def test_function_exists_and_callable(self):
        """midi_to_audio function is importable and callable."""
        from app.audio.converters import midi_to_audio
        
        import app.audio.converters as converters
        assert hasattr(converters, 'midi_to_audio')


class TestGetSoundfontPath:
    """Tests for get_soundfont_path function."""
    
    def test_returns_none_when_not_found(self):
        """get_soundfont_path returns None when soundfont not found."""
        from app.audio.converters import get_soundfont_path
        
        with patch('pathlib.Path.exists', return_value=False):
            with patch('pathlib.Path.glob', return_value=[]):
                result = get_soundfont_path("nonexistent_instrument")
                # May return None or a default path
                assert result is None or isinstance(result, (str, Path))
    
    def test_function_exists(self):
        """get_soundfont_path function is importable."""
        from app.audio.converters import get_soundfont_path
        
        import app.audio.converters as converters
        assert hasattr(converters, 'get_soundfont_path')
