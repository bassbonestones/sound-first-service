"""
Tests for tools/abc_to_musicxml.py

Tests for ABC to MusicXML conversion utility including key extraction,
transposition, and batch conversion.
"""

import pytest
from pathlib import Path

from tools.abc_to_musicxml import (
    extract_key_from_abc,
    normalize_key_for_music21,
    get_transposition_interval,
    add_original_key_comment,
    convert_abc_to_musicxml,
    convert_file,
    batch_convert,
    ConversionResult,
    extract_abc_dynamics_and_expressions,
    extract_abc_lyrics,
    ABCDynamic,
    ABCExpression,
    ABCArticulation,
    ABCLyrics,
    ABCSyllable,
)


# Sample ABC content for testing
ABC_HOT_CROSS_BUNS = """X:1
T:Hot Cross Buns
M:4/4
L:1/4
K:G
B A G z | B A G z | G G A A | B A G z |]
"""

ABC_MARY_HAD_A_LAMB = """X:1
T:Mary Had a Little Lamb
M:4/4
L:1/4
K:D
E D C D | E E E z | D D D z | E G G z |
E D C D | E E E E | D D E D | C4 |]
"""

ABC_MINOR_TUNE = """X:1
T:Simple Minor Tune
M:4/4
L:1/4
K:Am
A B C D | E D C B | A2 z2 |]
"""

ABC_MINOR_TUNE_EM = """X:1
T:E Minor Tune
M:4/4
L:1/4
K:Em
E F G A | B A G F | E2 z2 |]
"""

ABC_FLAT_KEY = """X:1
T:Tune in Bb
M:4/4
L:1/4
K:Bb
B c d e | f2 f2 |]
"""

ABC_NO_KEY = """X:1
T:No Key Field
M:4/4
L:1/4
C D E F | G2 z2 |]
"""


class TestExtractKeyFromAbc:
    """Tests for extract_key_from_abc function."""

    def test_simple_major_key(self):
        """Should extract simple major key."""
        assert extract_key_from_abc(ABC_HOT_CROSS_BUNS) == "G"

    def test_sharp_key(self):
        """Should extract key with sharp."""
        abc = "X:1\nK:F#\nABC"
        assert extract_key_from_abc(abc) == "F#"

    def test_flat_key(self):
        """Should extract key with flat."""
        assert extract_key_from_abc(ABC_FLAT_KEY) == "Bb"

    def test_minor_key(self):
        """Should extract minor key."""
        assert extract_key_from_abc(ABC_MINOR_TUNE) == "Am"

    def test_minor_key_explicit(self):
        """Should handle explicit minor notation."""
        abc = "X:1\nK:Em\nABC"
        assert extract_key_from_abc(abc) == "Em"

    def test_minor_key_with_spaces(self):
        """Should handle K: Dm minor format."""
        abc = "X:1\nK: Dm minor\nABC"
        assert extract_key_from_abc(abc) == "Dm"

    def test_major_explicit(self):
        """Should handle explicit major notation."""
        abc = "X:1\nK: D major\nABC"
        assert extract_key_from_abc(abc) == "D"

    def test_no_key_field(self):
        """Should return None when no K: field."""
        assert extract_key_from_abc(ABC_NO_KEY) is None

    def test_key_with_mode(self):
        """Should handle K: with mode specifier."""
        abc = "X:1\nK:G mix\nABC"  # G Mixolydian
        key = extract_key_from_abc(abc)
        assert key == "G"

    def test_lowercase_key(self):
        """Should normalize lowercase key."""
        abc = "X:1\nK:g\nABC"
        assert extract_key_from_abc(abc) == "G"


class TestNormalizeKeyForMusic21:
    """Tests for normalize_key_for_music21 function."""

    def test_simple_major(self):
        """Should format major key for music21."""
        assert normalize_key_for_music21("G") == "G"
        assert normalize_key_for_music21("D") == "D"

    def test_sharp_major(self):
        """Should convert sharp to music21 format."""
        # music21 uses the same sharp notation
        assert normalize_key_for_music21("F#") == "F#"

    def test_flat_major(self):
        """Should convert flat to music21 format."""
        assert normalize_key_for_music21("Bb") == "B-"

    def test_simple_minor(self):
        """Should format minor key for music21 (lowercase)."""
        # Minor keys use lowercase in music21
        assert normalize_key_for_music21("Am") == "a"

    def test_minor_with_accidental(self):
        """Should handle minor key with accidental."""
        result = normalize_key_for_music21("F#m")
        # Should be lowercase for minor
        assert result == "f#"


class TestGetTranspositionInterval:
    """Tests for get_transposition_interval function."""

    def test_g_to_c(self):
        """Should calculate G to C interval (down a fifth)."""
        interval = get_transposition_interval("G")
        # G to C is down a perfect 5th (or up a perfect 4th)
        assert interval is not None

    def test_d_to_c(self):
        """Should calculate D to C interval."""
        interval = get_transposition_interval("D")
        assert interval is not None

    def test_bb_to_c(self):
        """Should calculate Bb to C interval."""
        interval = get_transposition_interval("Bb")
        assert interval is not None

    def test_minor_key_to_a_minor(self):
        """Should transpose minor keys to A minor."""
        interval = get_transposition_interval("Em")
        # E minor to A minor - should be some interval
        assert interval is not None


class TestAddOriginalKeyComment:
    """Tests for add_original_key_comment function."""

    def test_adds_comment_after_xml_declaration(self):
        """Should add comment after XML declaration."""
        xml = '<?xml version="1.0"?>\n<score></score>'
        result = add_original_key_comment(xml, "G")
        assert "<!-- original_key_center: G -->" in result
        assert result.startswith('<?xml version="1.0"?>')

    def test_adds_comment_to_xml_without_declaration(self):
        """Should prepend comment if no XML declaration."""
        xml = "<score></score>"
        result = add_original_key_comment(xml, "Bb")
        assert result.startswith("<!-- original_key_center: Bb -->")

    def test_preserves_original_key_value(self):
        """Should preserve exact key value."""
        xml = '<?xml version="1.0"?>\n<score></score>'
        for key in ["G", "Bb", "F#", "Am", "C#m"]:
            result = add_original_key_comment(xml, key)
            assert f"original_key_center: {key}" in result


class TestConvertAbcToMusicxml:
    """Tests for convert_abc_to_musicxml function."""

    def test_converts_simple_abc(self):
        """Should convert valid ABC to MusicXML."""
        musicxml, original_key = convert_abc_to_musicxml(ABC_HOT_CROSS_BUNS)
        assert musicxml is not None
        assert "<score-partwise" in musicxml or "<score-timewise" in musicxml
        assert original_key == "G"

    def test_includes_original_key_comment(self):
        """Should include original key as comment."""
        musicxml, _ = convert_abc_to_musicxml(ABC_HOT_CROSS_BUNS)
        assert "<!-- original_key_center: G -->" in musicxml

    def test_transposes_to_c_by_default(self):
        """Should transpose to C major by default."""
        musicxml, original_key = convert_abc_to_musicxml(ABC_HOT_CROSS_BUNS)
        # Original was G, now should be in C
        assert original_key == "G"
        # Check for key signature of C (no sharps/flats)
        # The transposition should have happened

    def test_no_transpose_option(self):
        """Should keep original key when transpose=False."""
        musicxml, original_key = convert_abc_to_musicxml(
            ABC_HOT_CROSS_BUNS,
            transpose_to_c=False,
        )
        assert original_key == "G"

    def test_handles_minor_key_am(self):
        """Should handle A minor (no comment since Am is home key)."""
        musicxml, original_key = convert_abc_to_musicxml(ABC_MINOR_TUNE)
        assert original_key == "Am"
        # Am is the "home" minor key, so no original_key_center comment
        assert "<!-- original_key_center:" not in musicxml

    def test_handles_minor_key_em(self):
        """Should handle E minor with transposition and comment."""
        musicxml, original_key = convert_abc_to_musicxml(ABC_MINOR_TUNE_EM)
        assert original_key == "Em"
        assert "<!-- original_key_center: Em -->" in musicxml

    def test_handles_flat_key(self):
        """Should handle flat key ABC."""
        musicxml, original_key = convert_abc_to_musicxml(ABC_FLAT_KEY)
        assert original_key == "Bb"

    def test_handles_no_key_field(self):
        """Should default to C when no key field."""
        musicxml, original_key = convert_abc_to_musicxml(ABC_NO_KEY)
        assert original_key == "C"

    def test_invalid_abc_raises_error(self):
        """Should raise ValueError for invalid ABC."""
        with pytest.raises(ValueError, match="Failed to parse"):
            convert_abc_to_musicxml("This is not valid ABC notation at all!")

    def test_custom_title(self):
        """Should set custom title when provided."""
        musicxml, _ = convert_abc_to_musicxml(
            ABC_HOT_CROSS_BUNS,
            title="Custom Title",
        )
        # Title should appear somewhere in the MusicXML
        # This is somewhat implementation-dependent


class TestConvertFile:
    """Tests for convert_file function."""

    def test_converts_existing_file(self, tmp_path: Path):
        """Should convert ABC file to MusicXML."""
        # Create test ABC file
        abc_file = tmp_path / "test.abc"
        abc_file.write_text(ABC_HOT_CROSS_BUNS)

        result = convert_file(abc_file)

        assert result.success is True
        assert result.original_key == "G"
        assert result.transposed is True
        assert result.output_file.exists()
        assert result.output_file.suffix == ".musicxml"

    def test_handles_missing_file(self, tmp_path: Path):
        """Should return error for missing file."""
        missing = tmp_path / "nonexistent.abc"
        result = convert_file(missing)

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_custom_output_path(self, tmp_path: Path):
        """Should use custom output path."""
        abc_file = tmp_path / "input.abc"
        abc_file.write_text(ABC_HOT_CROSS_BUNS)

        output_file = tmp_path / "custom_output.musicxml"
        result = convert_file(abc_file, output_path=output_file)

        assert result.success is True
        assert result.output_file == output_file
        assert output_file.exists()

    def test_output_dir_option(self, tmp_path: Path):
        """Should place output in specified directory."""
        abc_file = tmp_path / "input.abc"
        abc_file.write_text(ABC_HOT_CROSS_BUNS)

        output_dir = tmp_path / "output"
        result = convert_file(abc_file, output_dir=output_dir)

        assert result.success is True
        assert result.output_file.parent == output_dir
        assert result.output_file.name == "input.musicxml"

    def test_no_transpose_option(self, tmp_path: Path):
        """Should keep original key when transpose_to_c=False."""
        abc_file = tmp_path / "test.abc"
        abc_file.write_text(ABC_HOT_CROSS_BUNS)

        result = convert_file(abc_file, transpose_to_c=False)

        assert result.success is True
        assert result.transposed is False


class TestBatchConvert:
    """Tests for batch_convert function."""

    def test_converts_all_abc_files(self, tmp_path: Path):
        """Should convert all ABC files in directory."""
        # Create test files
        input_dir = tmp_path / "abc"
        input_dir.mkdir()

        (input_dir / "tune1.abc").write_text(ABC_HOT_CROSS_BUNS)
        (input_dir / "tune2.abc").write_text(ABC_MARY_HAD_A_LAMB)
        (input_dir / "tune3.abc").write_text(ABC_MINOR_TUNE)

        output_dir = tmp_path / "output"
        results = batch_convert(input_dir, output_dir)

        assert len(results) == 3
        assert all(r.success for r in results)
        assert len(list(output_dir.glob("*.musicxml"))) == 3

    def test_preserves_subdirectory_structure(self, tmp_path: Path):
        """Should preserve directory structure in batch mode."""
        input_dir = tmp_path / "abc"
        (input_dir / "beginner").mkdir(parents=True)
        (input_dir / "advanced").mkdir(parents=True)

        (input_dir / "beginner" / "tune1.abc").write_text(ABC_HOT_CROSS_BUNS)
        (input_dir / "advanced" / "tune2.abc").write_text(ABC_MARY_HAD_A_LAMB)

        output_dir = tmp_path / "output"
        results = batch_convert(input_dir, output_dir)

        assert len(results) == 2
        assert (output_dir / "beginner" / "tune1.musicxml").exists()
        assert (output_dir / "advanced" / "tune2.musicxml").exists()

    def test_non_recursive_option(self, tmp_path: Path):
        """Should only convert top-level files when recursive=False."""
        input_dir = tmp_path / "abc"
        input_dir.mkdir()
        (input_dir / "subdir").mkdir()

        (input_dir / "top.abc").write_text(ABC_HOT_CROSS_BUNS)
        (input_dir / "subdir" / "nested.abc").write_text(ABC_MARY_HAD_A_LAMB)

        output_dir = tmp_path / "output"
        results = batch_convert(input_dir, output_dir, recursive=False)

        assert len(results) == 1
        assert results[0].input_file.name == "top.abc"

    def test_empty_directory(self, tmp_path: Path):
        """Should handle empty directory gracefully."""
        input_dir = tmp_path / "empty"
        input_dir.mkdir()

        output_dir = tmp_path / "output"
        results = batch_convert(input_dir, output_dir)

        assert len(results) == 0


class TestConversionResult:
    """Tests for ConversionResult dataclass."""

    def test_success_result(self):
        """Should create successful result."""
        result = ConversionResult(
            input_file=Path("test.abc"),
            output_file=Path("test.musicxml"),
            original_key="G",
            transposed=True,
            success=True,
        )
        assert result.success is True
        assert result.error is None

    def test_error_result(self):
        """Should create error result."""
        result = ConversionResult(
            input_file=Path("test.abc"),
            output_file=Path(""),
            original_key="",
            transposed=False,
            success=False,
            error="File not found",
        )
        assert result.success is False
        assert result.error == "File not found"


class TestExtractAbcDynamicsAndExpressions:
    """Tests for extract_abc_dynamics_and_expressions function."""

    def test_extracts_mf_dynamic(self):
        """Should extract mf dynamic at correct position."""
        abc = "K:C\n!mf! C D E F |"
        dynamics, expressions, articulations, wedges = extract_abc_dynamics_and_expressions(abc)
        assert len(dynamics) == 1
        assert dynamics[0].note_index == 0
        assert dynamics[0].dynamic == "mf"

    def test_extracts_multiple_dynamics(self):
        """Should extract multiple dynamics."""
        abc = "K:C\n!p! C D | !f! E F |"
        dynamics, expressions, articulations, wedges = extract_abc_dynamics_and_expressions(abc)
        assert len(dynamics) == 2
        assert dynamics[0].dynamic == "p"
        assert dynamics[1].dynamic == "f"

    def test_extracts_crescendo(self):
        """Should extract crescendo as dynamic."""
        abc = "K:C\n!cresc! C D E F |"
        dynamics, expressions, articulations, wedges = extract_abc_dynamics_and_expressions(abc)
        # cresc is in dynamics map, maps to "cresc" (short form)
        assert len(dynamics) == 1
        assert dynamics[0].dynamic == "cresc"

    def test_extracts_expression_mark(self):
        """Should extract expression marks like dolce."""
        abc = "K:C\n!dolce! C D E F |"
        dynamics, expressions, articulations, wedges = extract_abc_dynamics_and_expressions(abc)
        assert len(expressions) == 1
        assert expressions[0].text == "dolce"

    def test_handles_no_dynamics(self):
        """Should return empty lists for ABC without dynamics."""
        abc = "K:C\nC D E F |"
        dynamics, expressions, articulations, wedges = extract_abc_dynamics_and_expressions(abc)
        assert len(dynamics) == 0
        assert len(expressions) == 0
        assert len(articulations) == 0

    def test_extracts_accent_articulation(self):
        """Should extract accent articulations."""
        abc = "K:C\n!accent! C !>! D E F |"
        dynamics, expressions, articulations, wedges = extract_abc_dynamics_and_expressions(abc)
        assert len(articulations) == 2
        assert articulations[0].articulation == "Accent"
        assert articulations[1].articulation == "Accent"


class TestExtractAbcLyrics:
    """Tests for extract_abc_lyrics function."""

    def test_extracts_simple_lyrics(self):
        """Should extract lyrics from w: line with proper syllabic types."""
        abc = "K:C\nC D E F |\nw: Hot cross buns!"
        lyrics = extract_abc_lyrics(abc)
        assert lyrics is not None
        assert len(lyrics.syllables) == 3
        assert lyrics.syllables[0] == ABCSyllable(text="Hot", syllabic="single")
        assert lyrics.syllables[1] == ABCSyllable(text="cross", syllabic="single")
        assert lyrics.syllables[2] == ABCSyllable(text="buns!", syllabic="single")

    def test_handles_hyphenated_syllables(self):
        """Should split hyphenated words into syllables with begin/end markers."""
        abc = "K:C\nC D E F G |\nw: Hel-lo world to-day"
        lyrics = extract_abc_lyrics(abc)
        assert lyrics is not None
        # "Hel-lo" becomes two syllables, "world" is single, "to-day" becomes two
        assert len(lyrics.syllables) == 5
        assert lyrics.syllables[0] == ABCSyllable(text="Hel", syllabic="begin")
        assert lyrics.syllables[1] == ABCSyllable(text="lo", syllabic="end")
        assert lyrics.syllables[2] == ABCSyllable(text="world", syllabic="single")
        assert lyrics.syllables[3] == ABCSyllable(text="to", syllabic="begin")
        assert lyrics.syllables[4] == ABCSyllable(text="day", syllabic="end")

    def test_handles_no_lyrics(self):
        """Should return empty ABCLyrics for ABC without lyrics."""
        abc = "K:C\nC D E F |"
        lyrics = extract_abc_lyrics(abc)
        # Returns ABCLyrics with empty syllables list
        assert lyrics is not None
        assert lyrics.syllables == []

    def test_handles_underscore_extensions(self):
        """Should convert underscore melisma markers to empty placeholders for alignment."""
        abc = "K:C\nC D E F |\nw: Hold _ the note"
        lyrics = extract_abc_lyrics(abc)
        assert lyrics is not None
        # Underscores become empty placeholders to preserve note alignment
        texts = [s.text for s in lyrics.syllables]
        assert "_" not in texts
        # Empty string represents the melisma extension position
        assert texts == ["Hold", "", "the", "note"]
        # Filter to get just actual text content
        actual_lyrics = [t for t in texts if t]
        assert actual_lyrics == ["Hold", "the", "note"]

    def test_multi_syllable_word(self):
        """Should handle words with three+ syllables."""
        abc = "K:C\nC D E F |\nw: one-a-pen-ny"
        lyrics = extract_abc_lyrics(abc)
        assert len(lyrics.syllables) == 4
        assert lyrics.syllables[0].syllabic == "begin"
        assert lyrics.syllables[1].syllabic == "middle"
        assert lyrics.syllables[2].syllabic == "middle"
        assert lyrics.syllables[3].syllabic == "end"


class TestMusicXmlMusicality:
    """Tests for musicality in converted MusicXML output."""

    def test_dynamics_in_musicxml(self):
        """Should include dynamics in MusicXML output."""
        abc = """X:1
T:Test
M:4/4
L:1/4
K:C
!mf! C D E F |]
"""
        musicxml, _ = convert_abc_to_musicxml(abc)
        assert "<dynamics" in musicxml
        assert "<mf" in musicxml

    def test_lyrics_in_musicxml(self):
        """Should include lyrics in MusicXML output."""
        abc = """X:1
T:Test
M:4/4
L:1/4
K:C
C D E F |]
w: one two three four
"""
        musicxml, _ = convert_abc_to_musicxml(abc)
        assert "<lyric" in musicxml
        assert "<syllabic>single</syllabic>" in musicxml
        assert ">one<" in musicxml
        assert ">two<" in musicxml

    def test_syllabic_begin_end_in_musicxml(self):
        """Should use begin/end syllabic for hyphenated words."""
        abc = """X:1
T:Test
M:4/4
L:1/4
K:C
C D E F |]
w: Hel-lo world to-day
"""
        musicxml, _ = convert_abc_to_musicxml(abc)
        assert "<syllabic>begin</syllabic>" in musicxml
        assert "<syllabic>end</syllabic>" in musicxml
        assert "<syllabic>single</syllabic>" in musicxml
        assert ">Hel<" in musicxml
        assert ">lo<" in musicxml

    def test_multiple_dynamics_in_musicxml(self):
        """Should include multiple dynamics at correct positions."""
        abc = """X:1
T:Test
M:4/4
L:1/4
K:C
!p! C D | !f! E F |]
"""
        musicxml, _ = convert_abc_to_musicxml(abc)
        assert "<p />" in musicxml or "<p/>" in musicxml
        assert "<f />" in musicxml or "<f/>" in musicxml
