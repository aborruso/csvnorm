"""Tests for encoding module."""

from pathlib import Path

import pytest

from csvnorm.encoding import (
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

    def test_nonexistent_file(self):
        with pytest.raises(Exception):  # Can be ValueError or FileNotFoundError
            detect_encoding(Path("/nonexistent/file.csv"))
