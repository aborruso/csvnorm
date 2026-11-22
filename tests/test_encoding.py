"""Tests for encoding module."""

import logging
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


WESTERN = {"cp1252", "latin-1", "iso8859-15"}


class TestDetectEncodingSampled:
    """Encoding detection without a full decode per candidate (phase four).

    Synthetic files are small, so the sampling threshold is lowered to 0.
    """

    @pytest.fixture(autouse=True)
    def sample_every_file(self, monkeypatch):
        import csvnorm.encoding as enc

        monkeypatch.setattr(enc, "FULL_DETECTION_MAX_BYTES", 0)

    def test_sparse_byte_in_the_middle(self, make_csv, tmp_path):
        src = make_csv(200_000, insert={100_000: b"caf\xe9"})
        enc = detect_encoding(src)
        assert enc in WESTERN
        out = tmp_path / "out.csv"
        convert_to_utf8(src, out, enc)
        assert "café" in out.read_text(encoding="utf-8")

    def test_cuj2_byte_only_in_last_row_without_final_newline(self, make_csv):
        src = make_csv(200_000, insert={200_000: b"caf\xe9"})
        src.write_bytes(src.read_bytes().rstrip(b"\n"))
        assert detect_encoding(src) in WESTERN

    def test_sample_that_looks_like_utf8_is_not_utf8(self, make_csv, tmp_path):
        # 0x92 first appears inside a valid UTF-8 sequence, later alone (cp1252 ’)
        body = b"a,b\n1,caf\xc3\xa9 \xe2\x80\x99\n" + b"2,x\n" * 1000 + b"3,it\x92s\n"
        src = make_csv(body=body)
        enc = detect_encoding(src)
        assert enc != "utf-8"
        out = tmp_path / "out.csv"
        convert_to_utf8(src, out, enc)

    def test_byte_0x81_excludes_cp1252(self, make_csv):
        src = make_csv(1000, insert={10: b"caf\xe9", 500: b"x\x81y"})
        assert detect_encoding(src) != "cp1252"

    def test_binary_file_goes_to_full_detection(self, caplog):
        caplog.set_level(logging.DEBUG, logger="csvnorm")
        with pytest.raises(ValueError, match="Cannot detect encoding"):
            detect_encoding(TEST_DIR / "binary_file.bin")
        assert "Encoding route: full (nul byte)" in caplog.text

    @pytest.mark.parametrize("bom", [b"\xff\xfe", b"\xfe\xff", b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff"])
    def test_utf16_utf32_bom_goes_to_full_detection(self, make_csv, caplog, bom):
        caplog.set_level(logging.DEBUG, logger="csvnorm")
        src = make_csv(body=bom + "a,b\n1,città\n".encode("utf-16-le"))
        try:
            detect_encoding(src)
        except ValueError:
            pass
        assert "Encoding route: full (utf-16/32 bom)" in caplog.text

    def test_utf8_bom_and_empty_file(self, make_csv):
        assert detect_encoding(make_csv(body=b"\xef\xbb\xbfa,b\n1,citt\xc3\xa0\n")) == "utf-8"
        assert detect_encoding(make_csv(body=b"")) == "utf-8"

    def test_shift_jis_windows_never_split_characters(self, make_csv):
        from csvnorm.encoding import _scan

        body = ("名前,住所\n" + "東京都,大阪府の住所\n" * 60_000).encode("shift_jis")
        src = make_csv(body=body)
        result = _scan(src)
        assert result.route == "sample"
        for window in result.sample.split(b"\n"):
            window.decode("shift_jis")
        assert detect_encoding(src) in {"shift-jis", "cp932"}

    def test_scan_is_deterministic(self, make_csv):
        from csvnorm.encoding import _scan

        src = make_csv(50_000, insert={7: b"caf\xe9", 40_000: b"na\xefve"})
        assert _scan(src) == _scan(src)

    def test_whole_sample_is_examined(self):
        from charset_normalizer import from_bytes

        sample = b"\xe9" * 3000 + b"\x81" + b"\xe9" * 1095
        results = from_bytes(sample, steps=1, chunk_size=len(sample))
        assert "cp1252" not in {m.encoding for m in results}

    def test_fallback_to_full_detection_after_conversion_error(
        self, make_csv, tmp_path, monkeypatch
    ):
        import csvnorm.encoding as enc

        src = make_csv(100, insert={50: b"caf\xe9 \xfd"})
        calls = []
        real_full = enc._detect_encoding_full

        def full(path):
            calls.append(path)
            return real_full(path)

        monkeypatch.setattr(enc, "detect_encoding", lambda path: "shift-jis")
        monkeypatch.setattr(enc, "_detect_encoding_full", full)
        out = tmp_path / "out.csv"
        used = enc.detect_and_convert(src, out)
        assert len(calls) == 1
        assert used != "shift-jis"
        assert "café" in out.read_text(encoding="utf-8")

    def test_route_messages(self, make_csv, caplog):
        caplog.set_level(logging.DEBUG, logger="csvnorm")
        detect_encoding(make_csv(10))
        detect_encoding(make_csv(body="città\n".encode("utf-8")))
        detect_encoding(make_csv(100, insert={5: b"caf\xe9"}))
        assert "Encoding route: ascii" in caplog.text
        assert "Encoding route: utf-8" in caplog.text
        assert "Encoding route: sample (" in caplog.text

    def test_italian_with_grave_accents_is_cp1252_not_cp1258(self, make_csv):
        # charset_normalizer alone prefers cp1258 here (ì and ò become
        # combining marks); the sample route prefers a Western codec among
        # the least chaotic candidates.
        rows = "1,Città di Castello\n2,Forlì\n3,Cantù\n4,Agliè\n5,Rorà\n6,perché sì\n"
        body = b"id,nome\n" + b"9,x\n" * 50_000 + rows.encode("cp1252")
        assert detect_encoding(make_csv(body=body)) == "cp1252"


class TestDetectionRoutes:
    """Size threshold, 7-bit encodings, window edges, fallback."""

    def test_files_below_threshold_use_full_detection(self, make_csv, caplog):
        caplog.set_level(logging.DEBUG, logger="csvnorm")
        src = make_csv(200_000, insert={100_000: b"caf\xe9"})
        from csvnorm.encoding import _detect_encoding_full

        assert detect_encoding(src) == _detect_encoding_full(src)
        assert "below the sampling threshold" in caplog.text

    @pytest.mark.parametrize("codec", ["iso2022_jp", "iso2022_kr", "hz"])
    def test_7bit_escape_encodings_go_to_full_detection(self, make_csv, monkeypatch, codec):
        import csvnorm.encoding as enc

        monkeypatch.setattr(enc, "FULL_DETECTION_MAX_BYTES", 0)
        text = {"iso2022_jp": "名前,東京\n", "iso2022_kr": "이름,서울\n", "hz": "名字,北京\n"}[codec]
        src = make_csv(body=text.encode(codec))
        assert enc._scan(src).route == "full"

    def test_window_left_search_reads_the_right_byte(self, tmp_path):
        from csvnorm.encoding import MAX_CUT_SEARCH, WINDOW_HALF, _window

        data = bytearray(b"A" * 2000)
        pos = 1000
        data[pos + WINDOW_HALF + MAX_CUT_SEARCH] = ord(",")  # cut on the right only
        path = tmp_path / "w.bin"
        path.write_bytes(bytes(data))
        with open(path, "rb") as f:
            assert _window(f, len(data), pos) is None
        data[pos - WINDOW_HALF - MAX_CUT_SEARCH - 1] = ord(",")  # farthest left cut
        path.write_bytes(bytes(data))
        with open(path, "rb") as f:
            assert _window(f, len(data), pos) == (pos - WINDOW_HALF - MAX_CUT_SEARCH, pos + WINDOW_HALF + MAX_CUT_SEARCH + 1)

    def test_long_cjk_fields_stay_on_the_sample_route(self, make_csv, monkeypatch):
        import csvnorm.encoding as enc

        monkeypatch.setattr(enc, "FULL_DETECTION_MAX_BYTES", 0)
        field = "東京都大阪府名古屋市" * 20  # 200 characters, no cut byte inside
        body = ("名前,住所\n" + "".join(f"{i},{field}\n" for i in range(5000))).encode("shift_jis")
        assert enc._scan(make_csv(body=body)).route == "sample"

    def test_fallback_does_not_repeat_the_same_conversion(self, make_csv, tmp_path, monkeypatch):
        import csvnorm.encoding as enc

        src = make_csv(10, insert={5: b"\x81"})
        calls = []
        real = enc.convert_to_utf8

        def counting(*args):
            calls.append(args)
            return real(*args)

        monkeypatch.setattr(enc, "detect_encoding", lambda path: "cp1252")
        monkeypatch.setattr(enc, "_detect_encoding_full", lambda path: "cp1252")
        monkeypatch.setattr(enc, "convert_to_utf8", counting)
        with pytest.raises(UnicodeDecodeError):
            enc.detect_and_convert(src, tmp_path / "out.csv")
        assert len(calls) == 1
