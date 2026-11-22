"""Tests for encoding module."""

import tempfile
from pathlib import Path

import pytest

from csvnorm.encoding import (
    convert_to_utf8,
    detect_encoding,
    needs_conversion,
    normalize_encoding_name,
)

TEST_DIR = Path(__file__).parent.parent / "test"


class TestNormalizeEncodingName:
    """Tests for normalize_encoding_name function."""

    def test_utf8_variants(self):
        assert normalize_encoding_name("UTF_8") == "utf-8"
        assert normalize_encoding_name("utf-8") == "utf-8"
        assert normalize_encoding_name("UTF-8") == "utf-8"

    def test_utf8_sig(self):
        assert normalize_encoding_name("UTF_8_SIG") == "utf-8-sig"
        assert normalize_encoding_name("utf-8-sig") == "utf-8-sig"

    def test_macroman(self):
        assert normalize_encoding_name("MACROMAN") == "mac_roman"
        assert normalize_encoding_name("macintosh") == "mac_roman"

    def test_other_encodings(self):
        assert normalize_encoding_name("ISO-8859-1") == "iso-8859-1"
        assert normalize_encoding_name("WINDOWS-1252") == "windows-1252"


class TestNeedsConversion:
    """Tests for needs_conversion function."""

    def test_utf8_no_conversion(self):
        assert needs_conversion("utf-8") is False
        assert needs_conversion("UTF-8") is False

    def test_ascii_no_conversion(self):
        assert needs_conversion("ascii") is False

    def test_utf8_sig_no_conversion(self):
        assert needs_conversion("utf-8-sig") is False

    def test_latin1_needs_conversion(self):
        assert needs_conversion("iso-8859-1") is True

    def test_windows1252_needs_conversion(self):
        assert needs_conversion("windows-1252") is True


class TestDetectEncoding:
    """Tests for detect_encoding function with real files."""

    @pytest.mark.skipif(
        not (TEST_DIR / "utf8_basic.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_utf8_file(self):
        encoding = detect_encoding(TEST_DIR / "utf8_basic.csv")
        assert encoding.lower() in ("utf-8", "ascii")

    @pytest.mark.skipif(
        not (TEST_DIR / "latin1_semicolon.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_latin1_file(self):
        encoding = detect_encoding(TEST_DIR / "latin1_semicolon.csv")
        # charset_normalizer may detect similar encodings (cp1250, latin-1, etc.)
        # All these require conversion to UTF-8
        assert needs_conversion(encoding) is True

    @pytest.mark.skipif(
        not (TEST_DIR / "latin1_semicolon.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_latin1_file_decodes_italian_text(self):
        """Tied candidates (cp1250, cp1252, ...) must resolve to a Western codec."""
        path = TEST_DIR / "latin1_semicolon.csv"
        text = path.read_bytes().decode(detect_encoding(path))
        assert "Città" in text
        assert "più" in text
        assert "caffè" in text

    def test_ministry_file_decodes_italian_text(self):
        """cp1252 has higher coherence than cp1250 here, but best() returns cp1250."""
        path = TEST_DIR / "IMPORTAZIONI animali vivi 2025 luglio-dicembre.csv"
        if not path.exists():
            pytest.skip("Test fixture not available")
        text = path.read_bytes().decode(detect_encoding(path))
        assert "Quantità" in text

    def test_cyrillic_cp1251_not_turned_western(self, tmp_path):
        """The Western tie-break must not override a clearly non-Western file."""
        words = "город улица область район население год число значение школа больница"
        rows = ["id,descrizione"] + [f"{i},{words}" for i in range(50)]
        path = tmp_path / "ru.csv"
        path.write_bytes("\n".join(rows).encode("cp1251"))
        text = path.read_bytes().decode(detect_encoding(path))
        assert "город улица область" in text

    def test_short_latin1_western_text(self, tmp_path):
        path = tmp_path / "w.csv"
        path.write_bytes("Nom;Città\nCafé;Müller\n".encode("latin-1"))
        text = path.read_bytes().decode(detect_encoding(path))
        assert "Città" in text and "Café" in text and "Müller" in text

    def test_nonexistent_file(self):
        with pytest.raises(Exception):  # Can be ValueError or FileNotFoundError
            detect_encoding(Path("/nonexistent/file.csv"))

    @pytest.mark.skipif(
        not (TEST_DIR / "empty_file.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_empty_file(self):
        """Test that empty files can be detected (may return ascii/utf-8)."""
        # charset_normalizer may detect empty files as ascii or utf-8
        # This is an edge case but not necessarily an error
        encoding = detect_encoding(TEST_DIR / "empty_file.csv")
        # Should return a valid encoding (likely ascii or utf-8)
        assert encoding.lower() in ("ascii", "utf-8", "utf-8-sig")

    @pytest.mark.skipif(
        not (TEST_DIR / "binary_file.bin").exists(),
        reason="Test fixtures not available",
    )
    def test_binary_file(self):
        """Test that binary files raise ValueError."""
        with pytest.raises(ValueError, match="Cannot detect encoding"):
            detect_encoding(TEST_DIR / "binary_file.bin")


class TestConvertToUTF8:
    """Tests for convert_to_utf8 function."""

    @pytest.mark.skipif(
        not (TEST_DIR / "empty_file.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_empty_file_conversion(self):
        """Test that empty files can be converted (edge case)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "output.csv"
            # Should not raise, just convert empty content
            result = convert_to_utf8(
                TEST_DIR / "empty_file.csv", output_path, "utf-8"
            )
            assert result == output_path
            assert output_path.exists()
            assert output_path.stat().st_size == 0

    def test_unsupported_encoding(self):
        """Test that unsupported encoding raises LookupError."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a dummy input file
            input_file = Path(tmpdir) / "input.csv"
            input_file.write_text("test")
            output_file = Path(tmpdir) / "output.csv"

            with pytest.raises(LookupError, match="Unknown encoding"):
                convert_to_utf8(input_file, output_file, "fake-encoding-xyz")


class TestConvertToUTF8Chunked:
    """Chunked conversion: line breaks kept, file offsets on errors, bounded memory."""

    def test_cr_and_crlf_inside_cells_kept(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_bytes(b'id,nota\r\n1,"caff\xe8\rlatte"\r\n2,"citt\xe0\r\nnuova"\r\n')
        out = tmp_path / "out.csv"
        convert_to_utf8(src, out, "latin-1")
        assert out.read_bytes() == (
            b'id,nota\r\n1,"caff\xc3\xa8\rlatte"\r\n2,"citt\xc3\xa0\r\nnuova"\r\n'
        )

    def test_lf_only_file_unchanged_from_1_3_0(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_bytes(b"a,b\n1,caff\xe8\n")
        out = tmp_path / "out.csv"
        convert_to_utf8(src, out, "cp1252")
        assert out.read_bytes() == b"a,b\n1,caff\xc3\xa8\n"

    def test_multibyte_char_split_across_chunks(self, tmp_path, monkeypatch):
        import csvnorm.encoding as enc

        monkeypatch.setattr(enc, "CHUNK_SIZE", 7)
        text = "名前,住所\n東京,大阪\n"
        src = tmp_path / "in.csv"
        src.write_bytes(text.encode("shift_jis"))
        out = tmp_path / "out.csv"
        convert_to_utf8(src, out, "shift_jis")
        assert out.read_text(encoding="utf-8") == text

    def test_undecodable_byte_reports_file_offset_and_removes_partial(self, tmp_path):
        data = b"a,b\n" + b"1,ok\n" * 1000 + b"2,\x81\n"
        src = tmp_path / "in.csv"
        src.write_bytes(data)
        out = tmp_path / "out.csv"
        with pytest.raises(UnicodeDecodeError) as exc:
            convert_to_utf8(src, out, "cp1252")
        assert exc.value.file_offset == data.index(b"\x81")
        assert not out.exists()

    def test_offset_with_pending_bytes_across_chunks(self, tmp_path, monkeypatch):
        import csvnorm.encoding as enc

        monkeypatch.setattr(enc, "CHUNK_SIZE", 7)
        data = b"abcdef\x81\x20xyz\n"  # 0x81 ends the first 7-byte chunk
        src = tmp_path / "in.csv"
        src.write_bytes(data)
        out = tmp_path / "out.csv"
        with pytest.raises(UnicodeDecodeError) as exc:
            convert_to_utf8(src, out, "shift_jis")
        assert exc.value.file_offset == data.index(b"\x81")

    def test_unknown_encoding_checked_before_opening_output(self, tmp_path):
        src = tmp_path / "in.csv"
        src.write_bytes(b"a\n")
        out = tmp_path / "out.csv"
        with pytest.raises(LookupError, match="Unknown encoding"):
            convert_to_utf8(src, out, "fake-encoding-xyz")
        assert not out.exists()

    def test_memory_stays_bounded(self, make_csv, tmp_path):
        import tracemalloc

        src = make_csv(1_200_000, insert={i: b"caf\xe9" for i in range(1, 1_200_001, 100)})
        assert src.stat().st_size > 40 * 2**20
        out = tmp_path / "out.csv"
        tracemalloc.start()
        try:
            convert_to_utf8(src, out, "cp1252")
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        assert peak < 24 * 2**20
