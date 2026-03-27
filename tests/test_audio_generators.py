"""
Tests for app/audio/generators.py
Tests high-level audio generation functions.
"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path

from app.audio.types import AudioResult, AudioError, AudioErrorCode


# =============================================================================
# Tests for generate_audio_with_result
# =============================================================================


class TestGenerateAudioWithResult:
    """Tests for generate_audio_with_result function."""

    def test_function_exists(self):
        """Function is importable."""
        from app.audio.generators import generate_audio_with_result
        assert callable(generate_audio_with_result)

    def test_returns_audio_result(self):
        """Function returns AudioResult."""
        from app.audio.generators import generate_audio_with_result
        
        with patch('app.audio.generators.MUSIC21_AVAILABLE', False):
            result = generate_audio_with_result(
                musicxml_content="<score/>",
                original_key="C",
                target_key="C",
            )
        
        assert isinstance(result, AudioResult)
        assert result.success is False

    def test_returns_error_when_music21_unavailable(self):
        """Returns error when music21 is not available."""
        from app.audio.generators import generate_audio_with_result
        
        with patch('app.audio.generators.MUSIC21_AVAILABLE', False):
            result = generate_audio_with_result(
                musicxml_content="<score/>",
                original_key="C",
                target_key="C",
            )
        
        assert result.success is False
        assert result.error is not None
        assert result.error.code == AudioErrorCode.MUSIC21_NOT_INSTALLED

    def test_returns_error_for_invalid_musicxml(self):
        """Returns error for invalid/empty MusicXML."""
        from app.audio.generators import generate_audio_with_result, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        result = generate_audio_with_result(
            musicxml_content="",  # Empty content
            original_key="C",
            target_key="C",
        )
        
        assert result.success is False
        assert result.error is not None
        assert result.error.code == AudioErrorCode.INVALID_MUSICXML

    def test_returns_error_for_too_short_musicxml(self):
        """Returns error for very short MusicXML content."""
        from app.audio.generators import generate_audio_with_result, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        result = generate_audio_with_result(
            musicxml_content="<x/>",  # Too short
            original_key="C",
            target_key="C",
        )
        
        assert result.success is False
        assert result.error is not None
        assert result.error.code == AudioErrorCode.INVALID_MUSICXML

    def test_returns_cached_result(self):
        """Returns cached result when available."""
        from app.audio.generators import generate_audio_with_result, get_audio_cache
        
        cache = get_audio_cache()
        cache_key = (123, "C", "piano")
        cached_data = b"cached wav data"
        cache[cache_key] = cached_data
        
        try:
            result = generate_audio_with_result(
                musicxml_content="<score>...</score>",
                original_key="C",
                target_key="C",
                instrument="piano",
                material_id=123,
            )
            
            assert result.success is True
            assert result.data == cached_data
            assert result.content_type == "audio/wav"
        finally:
            # Clean up cache
            if cache_key in cache:
                del cache[cache_key]

    def test_transposition_calculates_interval(self):
        """Test that transposition is attempted when keys differ."""
        from app.audio.generators import generate_audio_with_result, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        valid_musicxml = '''<?xml version="1.0"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
    </measure>
  </part>
</score-partwise>'''
        
        # Mock transposition interval calculation
        with patch('app.audio.generators.get_transposition_interval', return_value=None) as mock_get:
            result = generate_audio_with_result(
                musicxml_content=valid_musicxml,
                original_key="C",
                target_key="G",  # Different key
            )
            
            # Should have called get_transposition_interval
            mock_get.assert_called_once_with("C", "G")
            # Should fail due to None transposition interval
            assert result.success is False
            assert result.error.code == AudioErrorCode.TRANSPOSITION_FAILED

    def test_no_transposition_when_keys_same(self):
        """Test that no transposition is done when keys are the same."""
        from app.audio.generators import generate_audio_with_result, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        valid_musicxml = '''<?xml version="1.0"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
    </measure>
  </part>
</score-partwise>'''
        
        with patch('app.audio.generators.get_transposition_interval') as mock_get:
            with patch('app.audio.generators.musicxml_to_midi', return_value=b'midi'):
                with patch('app.audio.generators.FLUIDSYNTH_AVAILABLE', False):
                    result = generate_audio_with_result(
                        musicxml_content=valid_musicxml,
                        original_key="C",
                        target_key="C",  # Same key
                    )
            
            # Should NOT have called get_transposition_interval
            mock_get.assert_not_called()

    def test_returns_midi_fallback_when_fluidsynth_unavailable(self):
        """Returns MIDI fallback when FluidSynth not available."""
        from app.audio.generators import generate_audio_with_result, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        valid_musicxml = '''<?xml version="1.0"?>
<score-partwise version="3.1">
  <part-list><score-part id="P1"><part-name>Test</part-name></score-part></part-list>
  <part id="P1">
    <measure number="1">
      <attributes><divisions>1</divisions></attributes>
      <note><pitch><step>C</step><octave>4</octave></pitch><duration>4</duration><type>whole</type></note>
    </measure>
  </part>
</score-partwise>'''
        
        with patch('app.audio.generators.musicxml_to_midi', return_value=b'MThd midi data'):
            with patch('app.audio.generators.FLUIDSYNTH_AVAILABLE', False):
                result = generate_audio_with_result(
                    musicxml_content=valid_musicxml,
                    original_key="C",
                    target_key="C",
                )
        
        assert result.success is True
        assert result.is_fallback is True
        assert result.content_type == "audio/midi"
        assert result.error.code == AudioErrorCode.FLUIDSYNTH_NOT_INSTALLED


# =============================================================================
# Tests for generate_single_note_audio
# =============================================================================


class TestGenerateSingleNoteAudio:
    """Tests for generate_single_note_audio function."""

    def test_function_exists(self):
        """Function is importable."""
        from app.audio.generators import generate_single_note_audio
        assert callable(generate_single_note_audio)

    def test_returns_audio_result(self):
        """Function returns AudioResult."""
        from app.audio.generators import generate_single_note_audio
        
        with patch('app.audio.generators.MUSIC21_AVAILABLE', False):
            result = generate_single_note_audio("C4")
        
        assert isinstance(result, AudioResult)

    def test_returns_error_when_music21_unavailable(self):
        """Returns error when music21 is not available."""
        from app.audio.generators import generate_single_note_audio
        
        with patch('app.audio.generators.MUSIC21_AVAILABLE', False):
            result = generate_single_note_audio("C4")
        
        assert result.success is False
        assert result.error is not None
        assert result.error.code == AudioErrorCode.MUSIC21_NOT_INSTALLED

    def test_parses_note_with_octave(self):
        """Test parsing note with octave."""
        from app.audio.generators import generate_single_note_audio, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        with patch('app.audio.generators.get_soundfont_path', return_value=None):
            result = generate_single_note_audio("C4")
        
        assert result is not None
        # Should return MIDI fallback since no soundfont
        assert result.content_type in ["audio/midi", "audio/wav"]

    def test_parses_note_without_octave(self):
        """Test parsing note without octave adds default."""
        from app.audio.generators import generate_single_note_audio, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        with patch('app.audio.generators.get_soundfont_path', return_value=None):
            result = generate_single_note_audio("C")  # No octave
        
        assert result is not None
        # Should have added default octave (4)

    def test_uses_explicit_octave_param(self):
        """Test using explicit octave parameter."""
        from app.audio.generators import generate_single_note_audio, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        with patch('app.audio.generators.get_soundfont_path', return_value=None):
            result = generate_single_note_audio("C", octave=5)
        
        assert result is not None

    def test_parses_flat_notes(self):
        """Test parsing flat notes."""
        from app.audio.generators import generate_single_note_audio, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        with patch('app.audio.generators.get_soundfont_path', return_value=None):
            result = generate_single_note_audio("Bb4")
        
        assert result is not None

    def test_parses_sharp_notes(self):
        """Test parsing sharp notes."""
        from app.audio.generators import generate_single_note_audio, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        with patch('app.audio.generators.get_soundfont_path', return_value=None):
            result = generate_single_note_audio("F#4")
        
        assert result is not None

    def test_uses_cached_result(self):
        """Test that cached results are returned."""
        from app.audio.generators import generate_single_note_audio, get_single_note_cache, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        cache = get_single_note_cache()
        cache_key = ("c4", "piano", 3)  # lowercase note
        cached_data = b"cached single note wav"
        cache[cache_key] = cached_data
        
        try:
            result = generate_single_note_audio("C4", "piano", 3)
            
            assert result.success is True
            assert result.data == cached_data
        finally:
            if cache_key in cache:
                del cache[cache_key]

    def test_sfz_rendering_attempted_first(self):
        """Test that sfizz rendering is attempted first."""
        from app.audio.generators import generate_single_note_audio, MUSIC21_AVAILABLE, get_single_note_cache
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        # Clear any cache first
        cache = get_single_note_cache()
        cache_key = ("c4", "piano", 3)
        if cache_key in cache:
            del cache[cache_key]
        
        mock_sfz_path = Path("/path/to/test.sfz")
        
        with patch('app.audio.generators.get_sfz_path', return_value=mock_sfz_path):
            with patch('app.audio.generators.SFIZZ_RENDER_AVAILABLE', True):
                with patch('app.audio.generators.render_note_with_sfizz', return_value=b"sfz wav") as mock_render:
                    result = generate_single_note_audio("C4", "piano")
                    mock_render.assert_called_once()

    def test_falls_back_to_midi_when_sfz_returns_none(self):
        """Test fallback to MIDI when sfizz render returns None."""
        from app.audio.generators import generate_single_note_audio, MUSIC21_AVAILABLE, get_single_note_cache
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        # Clear any cache first
        cache = get_single_note_cache()
        cache_key = ("c4", "piano", 3)
        if cache_key in cache:
            del cache[cache_key]
        
        mock_sfz_path = Path("/path/to/test.sfz")
        
        with patch('app.audio.generators.get_sfz_path', return_value=mock_sfz_path):
            with patch('app.audio.generators.SFIZZ_RENDER_AVAILABLE', True):
                with patch('app.audio.generators.render_note_with_sfizz', return_value=None):
                    with patch('app.audio.generators.get_soundfont_path', return_value=None):
                        result = generate_single_note_audio("C4", "piano")
        
        assert result.success is True
        assert result.is_fallback is True
        assert result.content_type == "audio/midi"

    def test_custom_duration(self):
        """Test custom duration_beats parameter."""
        from app.audio.generators import generate_single_note_audio, MUSIC21_AVAILABLE
        
        if not MUSIC21_AVAILABLE:
            pytest.skip("music21 not available")
        
        with patch('app.audio.generators.get_soundfont_path', return_value=None):
            result = generate_single_note_audio("C4", duration_beats=8)
        
        assert result is not None


# =============================================================================
# Tests for generate_audio (deprecated wrapper)
# =============================================================================


class TestGenerateAudio:
    """Tests for generate_audio function."""

    def test_function_exists(self):
        """Function is importable."""
        from app.audio.generators import generate_audio
        assert callable(generate_audio)

    def test_returns_tuple(self):
        """Function returns tuple of (bytes, content_type)."""
        from app.audio.generators import generate_audio
        
        with patch('app.audio.generators.MUSIC21_AVAILABLE', False):
            result = generate_audio(
                musicxml_content="<score/>",
                original_key="C",
                target_key="C",
            )
        
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_returns_error_on_failure(self):
        """Returns error message in content_type on failure."""
        from app.audio.generators import generate_audio
        
        with patch('app.audio.generators.MUSIC21_AVAILABLE', False):
            data, content_type = generate_audio(
                musicxml_content="<score/>",
                original_key="C",
                target_key="C",
            )
        
        assert data is None
        assert content_type.startswith("error:")

    def test_delegates_to_generate_audio_with_result(self):
        """Delegates to generate_audio_with_result."""
        from app.audio.generators import generate_audio
        
        with patch('app.audio.generators.generate_audio_with_result') as mock:
            mock.return_value = AudioResult(
                success=True,
                data=b"wav data",
                content_type="audio/wav"
            )
            
            data, content_type = generate_audio(
                musicxml_content="<score>test</score>",
                original_key="C",
                target_key="G",
                instrument="trumpet",
            )
            
            # Called with positional args
            mock.assert_called_once()
            call_args = mock.call_args[0]
            assert call_args[0] == "<score>test</score>"
            assert call_args[1] == "C"
            assert call_args[2] == "G"
            assert call_args[3] == "trumpet"
            
            assert data == b"wav data"
            assert content_type == "audio/wav"


# =============================================================================
# Tests for caching
# =============================================================================


class TestAudioCaching:
    """Tests for audio caching behavior."""

    def test_audio_cache_is_accessible(self):
        """get_audio_cache returns a dict-like object."""
        from app.audio.generators import get_audio_cache
        
        cache = get_audio_cache()
        assert hasattr(cache, '__getitem__')
        assert hasattr(cache, '__setitem__')

    def test_single_note_cache_is_accessible(self):
        """get_single_note_cache returns a dict-like object."""
        from app.audio.generators import get_single_note_cache
        
        cache = get_single_note_cache()
        assert hasattr(cache, '__getitem__')
        assert hasattr(cache, '__setitem__')
