"""Integration tests for csvnorm."""

import gzip
import tempfile
import urllib.error
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

from csvnorm.core import process_csv
from csvnorm import core as core_module

TEST_DIR = Path(__file__).parent.parent / "test"
# Real public URL for testing
TEST_URL = (
    "https://raw.githubusercontent.com/aborruso/csvnorm/refs/heads/main/test/"
    "utf8_basic.csv"
)
MINISTRY_URL = (
    "https://www.dati.salute.gov.it/sites/default/files/2026-01/"
    "IMPORTAZIONI%20animali%20vivi%202025%20luglio-dicembre.csv"
)


class TestProcessCSV:
    """Integration tests for the full processing pipeline."""

    @pytest.fixture
    def output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.mark.skipif(
        not (TEST_DIR / "utf8_basic.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_basic_utf8(self, output_dir):
        """Test processing a basic UTF-8 file."""
        output_file = output_dir / "utf8_basic.csv"
        result = process_csv(
            input_file=str(TEST_DIR / "utf8_basic.csv"),
            output_file=output_file,
        )
        assert result == 0
        assert output_file.exists()

    @pytest.mark.skipif(
        not (TEST_DIR / "latin1_semicolon.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_latin1_with_delimiter(self, output_dir):
        """Test processing a Latin-1 file with semicolon delimiter."""
        output_file = output_dir / "latin1_semicolon.csv"
        result = process_csv(
            input_file=str(TEST_DIR / "latin1_semicolon.csv"),
            output_file=output_file,
            delimiter=";",
        )
        assert result == 0
        assert output_file.exists()

    @pytest.mark.skipif(
        not (TEST_DIR / "utf8_basic.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_gzip_input(self, output_dir, tmp_path):
        """Test processing a gzip-compressed CSV."""
        input_csv = TEST_DIR / "utf8_basic.csv"
        gz_path = tmp_path / "utf8_basic.csv.gz"
        gz_path.write_bytes(gzip.compress(input_csv.read_bytes()))

        output_file = output_dir / "utf8_basic.csv"
        result = process_csv(
            input_file=str(gz_path),
            output_file=output_file,
        )
        assert result == 0
        assert output_file.exists()

    @patch("csvnorm.core.normalize_csv")
    @patch("csvnorm.core.validate_csv")
    def test_zip_single_csv(self, mock_validate, mock_normalize, output_dir, tmp_path):
        """Test processing a zip with a single CSV entry."""
        mock_validate.return_value = (1, [], None)

        def _write_output(*, output_path, **_kwargs):
            Path(output_path).write_text("a,b\n1,2\n")
            return None

        mock_normalize.side_effect = _write_output

        zip_path = tmp_path / "data.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("data.csv", "a,b\n1,2\n")

        output_file = output_dir / "out.csv"
        result = process_csv(
            input_file=str(zip_path),
            output_file=output_file,
        )
        assert result == 0
        assert output_file.exists()
        assert mock_validate.call_count == 1
        called_path = mock_validate.call_args[0][0]
        assert isinstance(called_path, Path)
        assert called_path.name == "data.csv"

    @patch("csvnorm.core.normalize_csv")
    @patch("csvnorm.core.validate_csv")
    def test_zip_single_csv_fallback_extract(
        self,
        mock_validate,
        mock_normalize,
        output_dir,
        tmp_path,
    ):
        """Test zip extraction for nested CSV entries."""
        mock_validate.return_value = (1, [], None)

        def _write_output(*, output_path, **_kwargs):
            Path(output_path).write_text("a,b\n1,2\n")
            return None

        mock_normalize.side_effect = _write_output

        zip_path = tmp_path / "data.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("nested/data.csv", "a,b\n1,2\n")

        output_file = output_dir / "out.csv"
        result = process_csv(
            input_file=str(zip_path),
            output_file=output_file,
        )
        assert result == 0
        assert output_file.exists()
        assert mock_validate.call_count == 1
        called_path = mock_validate.call_args[0][0]
        assert isinstance(called_path, Path)
        assert called_path.name == "data.csv"

    @patch("csvnorm.core.normalize_csv")
    @patch("csvnorm.core.validate_csv")
    def test_zip_multiple_csvs(self, mock_validate, mock_normalize, output_dir, tmp_path):
        """Test zip error when multiple CSV entries exist."""
        zip_path = tmp_path / "multi.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("a.csv", "a\n1\n")
            archive.writestr("b.csv", "b\n2\n")

        output_file = output_dir / "out.csv"
        result = process_csv(
            input_file=str(zip_path),
            output_file=output_file,
        )
        assert result == 2
        mock_validate.assert_not_called()
        mock_normalize.assert_not_called()

    @patch("csvnorm.core.normalize_csv")
    @patch("csvnorm.core.validate_csv")
    def test_zip_no_csv(self, mock_validate, mock_normalize, output_dir, tmp_path):
        """Test zip error when no CSV entries exist."""
        zip_path = tmp_path / "empty.zip"
        with zipfile.ZipFile(zip_path, "w") as archive:
            archive.writestr("notes.txt", "notes")

        output_file = output_dir / "out.csv"
        result = process_csv(
            input_file=str(zip_path),
            output_file=output_file,
        )
        assert result == 2
        mock_validate.assert_not_called()
        mock_normalize.assert_not_called()

    @pytest.mark.skipif(
        not (TEST_DIR / "pipe_mixed_headers.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_keep_names(self, output_dir):
        """Test that --keep-names preserves original headers."""
        output_file = output_dir / "pipe_mixed_headers.csv"
        result = process_csv(
            input_file=str(TEST_DIR / "pipe_mixed_headers.csv"),
            output_file=output_file,
            keep_names=True,
        )
        assert result == 0

        assert output_file.exists()

        with open(output_file, "r") as f:
            header = f.readline().strip()
        # Headers should be preserved (not snake_cased)
        assert "User ID" in header or "UserName" in header

    @pytest.mark.skipif(
        not (TEST_DIR / "pipe_mixed_headers.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_normalize_names(self, output_dir):
        """Test that names are normalized by default."""
        output_file = output_dir / "pipe_mixed_headers.csv"
        result = process_csv(
            input_file=str(TEST_DIR / "pipe_mixed_headers.csv"),
            output_file=output_file,
            keep_names=False,
        )
        assert result == 0

        assert output_file.exists()

        with open(output_file, "r") as f:
            header = f.readline().strip()
        # Headers should be snake_cased
        assert "user_id" in header or "username" in header

    def test_nonexistent_file(self, output_dir):
        """Test handling of nonexistent input file."""
        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="/nonexistent/file.csv",
            output_file=output_file,
        )
        assert result == 2

    def test_force_overwrite(self, output_dir):
        """Test force overwrite behavior."""
        input_file = TEST_DIR / "utf8_basic.csv"
        if not input_file.exists():
            pytest.skip("Test fixtures not available")

        output_file = output_dir / "utf8_basic.csv"

        # First run
        result = process_csv(input_file=str(input_file), output_file=output_file)
        assert result == 0

        # Second run without force should fail
        result = process_csv(input_file=str(input_file), output_file=output_file)
        assert result == 2

        # Third run with force should succeed
        result = process_csv(
            input_file=str(input_file), output_file=output_file, force=True
        )
        assert result == 0

    @pytest.mark.network
    def test_remote_url(self, output_dir):
        """Test processing CSV from remote URL."""
        output_file = output_dir / "utf8_basic.csv"
        result = process_csv(
            input_file=TEST_URL,
            output_file=output_file,
        )
        assert result == 0
        assert output_file.exists()

    @pytest.mark.network
    def test_remote_url_404(self, output_dir):
        """Test handling of 404 error for remote URL."""
        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/nonexistent.csv",
            output_file=output_file,
        )
        assert result == 2

    @pytest.mark.network
    @pytest.mark.xfail(reason="Remote server may timeout", strict=False)
    def test_remote_url_download_fallback_ministry(self, output_dir):
        """Test remote download fallback with real public URL."""
        output_file = output_dir / "ministry.csv"
        result = process_csv(
            input_file=MINISTRY_URL,
            output_file=output_file,
            download_remote=True,
        )
        assert result == 0
        assert output_file.exists()


class TestRemoteURLErrors:
    """Tests for remote URL error scenarios (mocked)."""

    @pytest.fixture
    def output_dir(self):
        """Create a temporary output directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_invalid_url_scheme(self, output_dir):
        """Test handling of invalid URL scheme."""
        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="ftp://example.com/data.csv",
            output_file=output_file,
        )
        assert result == 2

    @patch("csvnorm.core.download_url_to_file")
    def test_remote_download_failure(self, mock_download, output_dir):
        """Fail when remote download fails."""
        mock_download.side_effect = urllib.error.URLError("download failed")
        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/nope.csv",
            output_file=output_file,
        )
        assert result == 2

    @patch.object(core_module, "show_warning_panel")
    @patch("csvnorm.core.download_url_to_file")
    @patch("csvnorm.core.normalize_csv")
    @patch("csvnorm.core.validate_csv")
    def test_download_remote_flag_warns(
        self, mock_validate, mock_normalize, mock_download, mock_warning, output_dir
    ):
        """Warn when deprecated --download-remote flag is used."""
        mock_validate.return_value = (1, [], None)

        def _write_download(_url, path):
            path.write_text("name,city\nAlice,Milan\n")

        def _write_output(*, output_path, **_kwargs):
            Path(output_path).write_text("name,city\nAlice,Milan\n")
            return None

        mock_download.side_effect = _write_download
        mock_normalize.side_effect = _write_output

        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/with-flag.csv",
            output_file=output_file,
            download_remote=True,
        )
        assert result == 0
        assert mock_warning.call_count == 1


class TestCrlfPreservation:
    """Tests for CRLF line ending preservation in file output."""

    @pytest.fixture
    def output_dir(self, tmp_path):
        return tmp_path

    def test_crlf_input_preserves_crlf_in_file_output(self, output_dir):
        """CRLF terminators + in-cell LF → output file keeps CRLF + LF."""
        input_file = TEST_DIR / "crlf_with_embedded_lf.csv"
        output_file = output_dir / "out.csv"
        result = process_csv(str(input_file), output_file)
        assert result == 0
        data = output_file.read_bytes()
        crlf_count = data.count(b"\r\n")
        lf_only_count = data.count(b"\n") - crlf_count
        assert crlf_count >= 3, f"Expected CRLF row terminators, got {crlf_count}"
        assert lf_only_count >= 2, f"Expected in-cell LF preserved, got {lf_only_count}"

    def test_lf_input_stays_lf_in_file_output(self, output_dir):
        """LF-only input produces LF-only output (no regression)."""
        input_file = TEST_DIR / "utf8_basic.csv"
        output_file = output_dir / "out.csv"
        result = process_csv(str(input_file), output_file)
        assert result == 0
        data = output_file.read_bytes()
        assert b"\r\n" not in data, "LF-only input should not produce CRLF output"

    def test_lf_rows_with_in_cell_crlf_keep_lf_rows(self, output_dir):
        """LF row terminators + CRLF inside quoted cells → rows stay LF."""
        input_file = TEST_DIR / "alberi_messina_mojibake.csv"
        output_file = output_dir / "out.csv"
        process_csv(str(input_file), output_file)
        data = output_file.read_bytes()
        header_end = data.index(b"\n")
        assert data[header_end - 1 : header_end] != b"\r", "Header row must end with LF"
        assert data.count(b"\r\n") == input_file.read_bytes().count(b"\r\n")

    def test_crlf_input_stdout_always_lf(self, output_dir, capsys):
        """CRLF input to stdout mode outputs LF (Unix pipeline compatibility)."""
        input_file = TEST_DIR / "crlf_with_embedded_lf.csv"
        result = process_csv(str(input_file), output_file=None)
        assert result == 0
        captured = capsys.readouterr()
        assert "\r\n" not in captured.out, "Stdout should never contain CRLF"


class TestOutputWrittenAtTheEnd:
    """With -o the output file is written only when processing completes."""

    PREVIOUS = b"previous,content\nkeep,me\n"

    def _existing_output(self, tmp_path):
        output_file = tmp_path / "out.csv"
        output_file.write_bytes(self.PREVIOUS)
        return output_file

    def test_strict_errors_found_during_normalization(self, tmp_path):
        """Errors that appear only after normalization still block the output with --strict."""
        output_file = self._existing_output(tmp_path)
        real = core_module._normalize_and_refresh_errors

        def late_errors(*args, **kwargs):
            used, _, _, _ = real(*args, **kwargs)
            return used, 2, ["Expected Number of Columns"], True

        with patch.object(core_module, "_normalize_and_refresh_errors", late_errors):
            result = process_csv(
                str(TEST_DIR / "utf8_basic.csv"), output_file, force=True, strict=True
            )

        assert result == 1
        assert output_file.read_bytes() == self.PREVIOUS

    def test_strict_errors_found_during_normalization_new_output(self, tmp_path):
        output_file = tmp_path / "new.csv"
        real = core_module._normalize_and_refresh_errors

        def late_errors(*args, **kwargs):
            used, _, _, _ = real(*args, **kwargs)
            return used, 2, ["Expected Number of Columns"], True

        with patch.object(core_module, "_normalize_and_refresh_errors", late_errors):
            result = process_csv(str(TEST_DIR / "utf8_basic.csv"), output_file, strict=True)

        assert result == 1
        assert not output_file.exists()

    def test_normalization_crash_keeps_existing_output(self, tmp_path):
        """A failure in the middle of writing never leaves a partial output."""
        import duckdb

        output_file = self._existing_output(tmp_path)

        def crash(*args, output_path, **kwargs):
            Path(output_path).write_bytes(b"partial")
            raise duckdb.IOException("disk full")

        with patch.object(core_module, "normalize_csv", side_effect=crash):
            result = process_csv(str(TEST_DIR / "utf8_basic.csv"), output_file, force=True)

        assert result == 2
        assert output_file.read_bytes() == self.PREVIOUS
        assert not list(tmp_path.glob(".*.csvnorm-partial"))


class TestDiskFull:
    """Disk-full errors: one panel, exit 1, input and existing output untouched."""

    PREVIOUS = b"previous,content\n"
    ENOSPC_DUCKDB = 'IO Error: Could not write file "x": No space left on device","errno":"28"'

    def _setup(self, tmp_path):
        output_file = tmp_path / "out.csv"
        output_file.write_bytes(self.PREVIOUS)
        return output_file

    def _assert_untouched(self, tmp_path, output_file):
        assert output_file.read_bytes() == self.PREVIOUS
        assert not list(tmp_path.glob(".*.csvnorm-partial"))

    def test_cuj5_disk_full_during_normalization(self, tmp_path, capsys, monkeypatch):
        import duckdb

        output_file = self._setup(tmp_path)
        monkeypatch.setattr(
            core_module.shutil, "disk_usage",
            lambda path: core_module.shutil._ntuple_diskusage(10, 9, 1),
        )
        with patch.object(
            core_module, "normalize_csv",
            side_effect=duckdb.IOException(self.ENOSPC_DUCKDB),
        ):
            result = process_csv(
                str(TEST_DIR / "latin1_semicolon.csv"), output_file, force=True
            )

        assert result == 2
        err = capsys.readouterr().err
        assert "Low disk space" in err
        assert "No space left on device" in err
        assert "Normalization failed" not in err
        self._assert_untouched(tmp_path, output_file)

    def test_disk_full_during_conversion(self, tmp_path, capsys):
        import errno

        output_file = self._setup(tmp_path)
        with patch.object(
            core_module, "_handle_local_encoding",
            side_effect=OSError(errno.ENOSPC, "No space left on device"),
        ):
            result = process_csv(
                str(TEST_DIR / "latin1_semicolon.csv"), output_file, force=True
            )

        assert result == 2
        assert "No space left on device" in capsys.readouterr().err
        self._assert_untouched(tmp_path, output_file)

    def test_disk_full_during_reject_export(self, tmp_path, capsys):
        import duckdb

        output_file = self._setup(tmp_path)
        with patch.object(
            core_module, "validate_csv",
            side_effect=duckdb.IOException(self.ENOSPC_DUCKDB),
        ):
            result = process_csv(
                str(TEST_DIR / "malformed_rows.csv"), output_file, force=True
            )

        assert result == 2
        err = capsys.readouterr().err
        assert "No space left on device" in err
        assert "Validation failed" not in err
        self._assert_untouched(tmp_path, output_file)

    def test_other_os_error_during_conversion(self, tmp_path, capsys):
        import errno

        output_file = self._setup(tmp_path)
        with patch.object(
            core_module, "_handle_local_encoding",
            side_effect=OSError(errno.EACCES, "Permission denied"),
        ):
            result = process_csv(
                str(TEST_DIR / "latin1_semicolon.csv"), output_file, force=True
            )

        assert result == 2
        assert "File error during encoding conversion" in capsys.readouterr().err
        self._assert_untouched(tmp_path, output_file)

    def test_decode_error_panel_has_title_and_offset(self, tmp_path, capsys):
        output_file = self._setup(tmp_path)
        error = UnicodeDecodeError("cp1252", b"\x81", 0, 1, "character maps to <undefined>")
        error.file_offset = 1234
        with patch.object(core_module, "_handle_local_encoding", side_effect=error):
            result = process_csv(
                str(TEST_DIR / "latin1_semicolon.csv"), output_file, force=True
            )

        assert result == 2
        err = capsys.readouterr().err
        assert "Encoding conversion failed" in err
        assert "1234" in err
        self._assert_untouched(tmp_path, output_file)


class TestDiskWarningEdgeCases:
    """The low-disk-space warning is advisory: it never breaks a run."""

    def test_output_in_missing_directory_gives_panel_not_traceback(self, tmp_path, capsys):
        result = process_csv(
            str(TEST_DIR / "utf8_basic.csv"), tmp_path / "nodir" / "out.csv"
        )
        assert result == 2
        assert "Traceback" not in capsys.readouterr().err

    def test_decode_error_names_the_source_encoding(self, tmp_path, capsys):
        src = tmp_path / "in.csv"
        src.write_bytes(b"a,b\n1,\x81\n")
        with patch("csvnorm.encoding.detect_encoding", return_value="cp1252"), patch(
            "csvnorm.encoding._detect_encoding_full", return_value="cp1252"
        ):
            result = process_csv(str(src), tmp_path / "out.csv")
        assert result == 2
        err = capsys.readouterr().err
        assert "cp1252 cannot decode byte 0x81 at file offset 6" in err
        assert "charmap" not in err


def test_disk_full_inside_convert_to_utf8(tmp_path, capsys, monkeypatch):
    """ENOSPC raised by the real conversion path reaches the disk-full panel."""
    import errno

    import csvnorm.encoding as enc

    output_file = tmp_path / "out.csv"
    output_file.write_bytes(b"previous\n")

    def full_disk(*args):
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(enc, "convert_to_utf8", full_disk)
    result = process_csv(str(TEST_DIR / "latin1_semicolon.csv"), output_file, force=True)

    assert result == 2
    err = capsys.readouterr().err
    assert "No space left on device" in err
    assert "File error" not in err
    assert output_file.read_bytes() == b"previous\n"
