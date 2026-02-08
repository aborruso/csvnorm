"""Tests for core.py helper functions."""

import io
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import duckdb
import pytest

from csvnorm.core import (
    _cleanup_temp_artifacts,
    _compute_and_show_output,
    _handle_post_validation,
    _prepare_working_file,
    _validate_csv_with_http_handling,
    process_csv,
)


# ---------------------------------------------------------------------------
# _prepare_working_file
# ---------------------------------------------------------------------------


class TestPrepareWorkingFile:
    """Tests for _prepare_working_file helper."""

    def _make_progress(self):
        progress = Mock()
        task = Mock()
        return progress, task

    def test_remote_url_returns_immediately(self):
        """Remote URL skips encoding detection."""
        progress, task = self._make_progress()
        result = _prepare_working_file(
            input_path="https://example.com/data.csv",
            is_remote=True,
            compressed_type=None,
            compressed_input_path="https://example.com/data.csv",
            temp_utf8_file=Path("/tmp/utf8.csv"),
            temp_dir=Path("/tmp"),
            fix_mojibake_sample=None,
            check_only=False,
            progress=progress,
            task=task,
            temp_files=[],
        )
        assert result == ("https://example.com/data.csv", "remote", False)

    def test_compressed_input_returns_immediately(self):
        """Compressed input skips encoding detection."""
        progress, task = self._make_progress()
        compressed_path = Path("/tmp/data.csv.gz")
        result = _prepare_working_file(
            input_path=Path("/tmp/data.csv.gz"),
            is_remote=False,
            compressed_type="gzip",
            compressed_input_path=compressed_path,
            temp_utf8_file=Path("/tmp/utf8.csv"),
            temp_dir=Path("/tmp"),
            fix_mojibake_sample=None,
            check_only=False,
            progress=progress,
            task=task,
            temp_files=[],
        )
        assert result == (compressed_path, "gzip", False)

    @patch("csvnorm.core._handle_local_encoding")
    def test_value_error_encoding_returns_none(self, mock_enc):
        """ValueError during encoding detection returns None."""
        mock_enc.side_effect = ValueError("unsupported encoding")
        progress, task = self._make_progress()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.csv"
            test_file.write_text("a,b\n1,2\n")
            result = _prepare_working_file(
                input_path=test_file,
                is_remote=False,
                compressed_type=None,
                compressed_input_path=test_file,
                temp_utf8_file=Path(tmpdir) / "utf8.csv",
                temp_dir=Path(tmpdir),
                fix_mojibake_sample=None,
                check_only=False,
                progress=progress,
                task=task,
                temp_files=[],
            )
        assert result is None
        progress.stop.assert_called_once()

    @patch("csvnorm.core._handle_local_encoding")
    def test_unicode_decode_error_returns_none(self, mock_enc):
        """UnicodeDecodeError during encoding detection returns None."""
        mock_enc.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "bad")
        progress, task = self._make_progress()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.csv"
            test_file.write_text("a,b\n1,2\n")
            result = _prepare_working_file(
                input_path=test_file,
                is_remote=False,
                compressed_type=None,
                compressed_input_path=test_file,
                temp_utf8_file=Path(tmpdir) / "utf8.csv",
                temp_dir=Path(tmpdir),
                fix_mojibake_sample=None,
                check_only=False,
                progress=progress,
                task=task,
                temp_files=[],
            )
        assert result is None

    @patch("csvnorm.core._handle_local_encoding")
    def test_lookup_error_returns_none(self, mock_enc):
        """LookupError during encoding detection returns None."""
        mock_enc.side_effect = LookupError("unknown encoding")
        progress, task = self._make_progress()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.csv"
            test_file.write_text("a,b\n1,2\n")
            result = _prepare_working_file(
                input_path=test_file,
                is_remote=False,
                compressed_type=None,
                compressed_input_path=test_file,
                temp_utf8_file=Path(tmpdir) / "utf8.csv",
                temp_dir=Path(tmpdir),
                fix_mojibake_sample=None,
                check_only=False,
                progress=progress,
                task=task,
                temp_files=[],
            )
        assert result is None

    @patch("csvnorm.core._handle_mojibake_if_needed")
    @patch("csvnorm.core._handle_local_encoding")
    def test_mojibake_oserror_returns_none(self, mock_enc, mock_moji):
        """OSError during mojibake repair returns None."""
        mock_enc.return_value = (Path("/tmp/working.csv"), "utf-8")
        mock_moji.side_effect = OSError("disk full")
        progress, task = self._make_progress()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.csv"
            test_file.write_text("a,b\n1,2\n")
            result = _prepare_working_file(
                input_path=test_file,
                is_remote=False,
                compressed_type=None,
                compressed_input_path=test_file,
                temp_utf8_file=Path(tmpdir) / "utf8.csv",
                temp_dir=Path(tmpdir),
                fix_mojibake_sample=1000,
                check_only=False,
                progress=progress,
                task=task,
                temp_files=[],
            )
        assert result is None

    @patch("csvnorm.core._handle_local_encoding")
    def test_check_only_skips_mojibake(self, mock_enc):
        """check_only=True skips mojibake repair."""
        mock_enc.return_value = (Path("/tmp/working.csv"), "utf-8")
        progress, task = self._make_progress()
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "data.csv"
            test_file.write_text("a,b\n1,2\n")
            result = _prepare_working_file(
                input_path=test_file,
                is_remote=False,
                compressed_type=None,
                compressed_input_path=test_file,
                temp_utf8_file=Path(tmpdir) / "utf8.csv",
                temp_dir=Path(tmpdir),
                fix_mojibake_sample=1000,
                check_only=True,
                progress=progress,
                task=task,
                temp_files=[],
            )
        assert result is not None
        working, enc, moji = result
        assert enc == "utf-8"
        assert moji is False


# ---------------------------------------------------------------------------
# _handle_post_validation
# ---------------------------------------------------------------------------


class TestHandlePostValidation:
    """Tests for _handle_post_validation helper."""

    def _make_progress(self):
        return Mock()

    def test_permissive_mode_warning(self):
        """Shows warning when strict_mode is False in fallback config."""
        progress = self._make_progress()
        result = _handle_post_validation(
            has_validation_errors=False,
            reject_count=1,
            error_types=[],
            fallback_config={"strict_mode": False},
            check_only=False,
            strict=False,
            use_stdout=False,
            reject_file=Path("/tmp/reject.csv"),
            progress=progress,
        )
        assert result is None
        progress.stop.assert_called_once()
        progress.start.assert_called_once()

    @patch("csvnorm.core.Console")
    def test_check_only_valid_returns_0(self, mock_console_cls):
        """check_only with valid CSV returns 0."""
        progress = self._make_progress()
        result = _handle_post_validation(
            has_validation_errors=False,
            reject_count=1,
            error_types=[],
            fallback_config=None,
            check_only=True,
            strict=False,
            use_stdout=False,
            reject_file=Path("/tmp/reject.csv"),
            progress=progress,
        )
        assert result == 0

    @patch("csvnorm.core.Console")
    def test_check_only_invalid_returns_1(self, mock_console_cls):
        """check_only with validation errors returns 1."""
        progress = self._make_progress()
        result = _handle_post_validation(
            has_validation_errors=True,
            reject_count=3,
            error_types=["CAST", "MISSING_COLUMNS"],
            fallback_config=None,
            check_only=True,
            strict=False,
            use_stdout=False,
            reject_file=Path("/tmp/reject.csv"),
            progress=progress,
        )
        assert result == 1

    @patch("csvnorm.core.show_validation_error_panel")
    @patch("csvnorm.core.Console")
    def test_stdout_strict_with_errors_returns_1(self, mock_console_cls, mock_panel):
        """Stdout mode with strict=True and errors returns 1."""
        progress = self._make_progress()
        result = _handle_post_validation(
            has_validation_errors=True,
            reject_count=3,
            error_types=["CAST"],
            fallback_config=None,
            check_only=False,
            strict=True,
            use_stdout=True,
            reject_file=Path("/tmp/reject.csv"),
            progress=progress,
        )
        assert result == 1

    @patch("csvnorm.core.show_validation_error_panel")
    @patch("csvnorm.core.Console")
    def test_stdout_non_strict_with_errors_continues(self, mock_console_cls, mock_panel):
        """Stdout mode with strict=False and errors returns None (continue)."""
        progress = self._make_progress()
        result = _handle_post_validation(
            has_validation_errors=True,
            reject_count=3,
            error_types=["CAST"],
            fallback_config=None,
            check_only=False,
            strict=False,
            use_stdout=True,
            reject_file=Path("/tmp/reject.csv"),
            progress=progress,
        )
        assert result is None
        progress.start.assert_called_once()

    def test_file_mode_with_errors_stops_progress(self):
        """File mode with validation errors stops progress, returns None."""
        progress = self._make_progress()
        result = _handle_post_validation(
            has_validation_errors=True,
            reject_count=3,
            error_types=["CAST"],
            fallback_config=None,
            check_only=False,
            strict=False,
            use_stdout=False,
            reject_file=Path("/tmp/reject.csv"),
            progress=progress,
        )
        assert result is None
        progress.stop.assert_called_once()

    def test_no_errors_returns_none(self):
        """No validation errors returns None (continue)."""
        progress = self._make_progress()
        result = _handle_post_validation(
            has_validation_errors=False,
            reject_count=1,
            error_types=[],
            fallback_config=None,
            check_only=False,
            strict=False,
            use_stdout=False,
            reject_file=Path("/tmp/reject.csv"),
            progress=progress,
        )
        assert result is None


# ---------------------------------------------------------------------------
# _validate_csv_with_http_handling
# ---------------------------------------------------------------------------


class TestValidateCsvWithHttpHandling:
    """Tests for _validate_csv_with_http_handling helper."""

    def _make_progress(self):
        return Mock()

    @patch("csvnorm.core.show_error_panel")
    @patch("csvnorm.core.validate_csv")
    def test_zipfs_extension_error(self, mock_validate, mock_panel):
        """DuckDB zipfs error shows appropriate panel."""
        mock_validate.side_effect = duckdb.Error("zipfs extension not found")
        progress = self._make_progress()
        with pytest.raises(duckdb.Error):
            _validate_csv_with_http_handling(
                Path("/tmp/data.csv"),
                Path("/tmp/reject.csv"),
                is_remote=False,
                skip_rows=0,
                input_file="data.csv",
                progress=progress,
                task=Mock(),
            )
        mock_panel.assert_called_once()
        assert "zipfs" in mock_panel.call_args[0][0].lower()

    @patch("csvnorm.core.show_error_panel")
    @patch("csvnorm.core.validate_csv")
    def test_http_404_error(self, mock_validate, mock_panel):
        """HTTP 404 error shows not-found panel."""
        mock_validate.side_effect = duckdb.Error("HTTP Error 404 Not Found")
        progress = self._make_progress()
        with pytest.raises(duckdb.Error):
            _validate_csv_with_http_handling(
                "https://example.com/data.csv",
                Path("/tmp/reject.csv"),
                is_remote=True,
                skip_rows=0,
                input_file="https://example.com/data.csv",
                progress=progress,
                task=Mock(),
            )
        mock_panel.assert_called_once()
        assert "404" in mock_panel.call_args[0][0]

    @patch("csvnorm.core.show_error_panel")
    @patch("csvnorm.core.validate_csv")
    def test_http_401_403_error(self, mock_validate, mock_panel):
        """HTTP 401/403 error shows auth panel."""
        mock_validate.side_effect = duckdb.Error("HTTP Error 403 Forbidden")
        progress = self._make_progress()
        with pytest.raises(duckdb.Error):
            _validate_csv_with_http_handling(
                "https://example.com/data.csv",
                Path("/tmp/reject.csv"),
                is_remote=True,
                skip_rows=0,
                input_file="https://example.com/data.csv",
                progress=progress,
                task=Mock(),
            )
        mock_panel.assert_called_once()
        assert "Authentication" in mock_panel.call_args[0][0]

    @patch("csvnorm.core.show_error_panel")
    @patch("csvnorm.core.validate_csv")
    def test_http_timeout_error(self, mock_validate, mock_panel):
        """HTTP timeout error shows timeout panel."""
        mock_validate.side_effect = duckdb.Error("HTTPException: timeout occurred")
        progress = self._make_progress()
        with pytest.raises(duckdb.Error):
            _validate_csv_with_http_handling(
                "https://example.com/data.csv",
                Path("/tmp/reject.csv"),
                is_remote=True,
                skip_rows=0,
                input_file="https://example.com/data.csv",
                progress=progress,
                task=Mock(),
            )
        mock_panel.assert_called_once()
        assert "timeout" in mock_panel.call_args[0][0].lower()

    @patch("csvnorm.core.show_error_panel")
    @patch("csvnorm.core.validate_csv")
    def test_http_range_error(self, mock_validate, mock_panel):
        """HTTP range error shows range panel."""
        mock_validate.side_effect = duckdb.Error("HTTPException: range not satisfiable")
        progress = self._make_progress()
        with pytest.raises(duckdb.Error):
            _validate_csv_with_http_handling(
                "https://example.com/data.csv",
                Path("/tmp/reject.csv"),
                is_remote=True,
                skip_rows=0,
                input_file="https://example.com/data.csv",
                progress=progress,
                task=Mock(),
            )
        mock_panel.assert_called_once()
        assert "range" in mock_panel.call_args[0][0].lower()

    @patch("csvnorm.core.show_error_panel")
    @patch("csvnorm.core.validate_csv")
    def test_generic_duckdb_error(self, mock_validate, mock_panel):
        """Non-HTTP DuckDB error shows generic panel."""
        mock_validate.side_effect = duckdb.Error("some internal error")
        progress = self._make_progress()
        with pytest.raises(duckdb.Error):
            _validate_csv_with_http_handling(
                Path("/tmp/data.csv"),
                Path("/tmp/reject.csv"),
                is_remote=False,
                skip_rows=0,
                input_file="data.csv",
                progress=progress,
                task=Mock(),
            )
        mock_panel.assert_called_once()
        assert "Validation failed" in mock_panel.call_args[0][0]

    @patch("csvnorm.core.show_error_panel")
    @patch("csvnorm.core.validate_csv")
    def test_http_etag_error(self, mock_validate, mock_panel):
        """ETag mismatch error shows retry panel."""
        mock_validate.side_effect = duckdb.Error(
            "HTTP Error: ETag on reading file changed"
        )
        progress = self._make_progress()
        with pytest.raises(duckdb.Error):
            _validate_csv_with_http_handling(
                "https://example.com/data.csv",
                Path("/tmp/reject.csv"),
                is_remote=True,
                skip_rows=0,
                input_file="https://example.com/data.csv",
                progress=progress,
                task=Mock(),
            )
        mock_panel.assert_called_once()
        assert "ETag" in mock_panel.call_args[0][0]


# ---------------------------------------------------------------------------
# _cleanup_temp_artifacts
# ---------------------------------------------------------------------------


class TestCleanupTempArtifacts:
    """Tests for _cleanup_temp_artifacts helper."""

    def test_stdout_removes_empty_reject(self):
        """Stdout mode removes reject file with only header (<=1 line)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reject = Path(tmpdir) / "reject_errors.csv"
            reject.write_text("header\n")
            _cleanup_temp_artifacts(use_stdout=True, reject_file=reject, temp_files=[])
            assert not reject.exists()

    def test_stdout_keeps_reject_with_errors(self):
        """Stdout mode keeps reject file with actual errors."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reject = Path(tmpdir) / "reject_errors.csv"
            reject.write_text("header\nerror1\nerror2\n")
            _cleanup_temp_artifacts(use_stdout=True, reject_file=reject, temp_files=[])
            assert reject.exists()

    def test_file_mode_removes_empty_reject(self):
        """File mode removes reject file with only header."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reject = Path(tmpdir) / "reject_errors.csv"
            reject.write_text("header\n")
            _cleanup_temp_artifacts(use_stdout=False, reject_file=reject, temp_files=[])
            assert not reject.exists()

    def test_cleans_temp_files(self):
        """Removes temp files from list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            temp_file = Path(tmpdir) / "temp.csv"
            temp_file.write_text("data")
            reject = Path(tmpdir) / "reject_errors.csv"
            _cleanup_temp_artifacts(
                use_stdout=False, reject_file=reject, temp_files=[temp_file]
            )
            assert not temp_file.exists()


# ---------------------------------------------------------------------------
# _compute_and_show_output
# ---------------------------------------------------------------------------


class TestComputeAndShowOutput:
    """Tests for _compute_and_show_output helper."""

    @patch("csvnorm.core.get_column_count", return_value=3)
    @patch("csvnorm.core.get_row_count", return_value=10)
    @patch("csvnorm.core.show_validation_error_panel")
    @patch("csvnorm.core.show_success_table")
    def test_file_mode_with_errors_returns_1(
        self, mock_table, mock_panel, mock_rows, mock_cols
    ):
        """File mode with validation errors returns 1."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "out.csv"
            output.write_text("a,b,c\n1,2,3\n")
            local_input = Path(tmpdir) / "in.csv"
            local_input.write_text("a,b,c\n1,2,3\n")
            reject = Path(tmpdir) / "reject.csv"

            result = _compute_and_show_output(
                input_file="in.csv",
                local_input_path=local_input,
                working_file=local_input,
                actual_output_file=output,
                encoding="utf-8",
                is_remote=False,
                mojibake_repaired=False,
                delimiter=",",
                keep_names=False,
                use_stdout=False,
                has_validation_errors=True,
                reject_count=3,
                error_types=["CAST"],
                reject_file=reject,
            )
        assert result == 1
        mock_table.assert_called_once()
        mock_panel.assert_called_once()

    @patch("csvnorm.core.get_column_count", return_value=3)
    @patch("csvnorm.core.get_row_count", return_value=10)
    @patch("csvnorm.core.show_success_table")
    def test_file_mode_no_errors_returns_0(self, mock_table, mock_rows, mock_cols):
        """File mode without errors returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "out.csv"
            output.write_text("a,b,c\n1,2,3\n")
            local_input = Path(tmpdir) / "in.csv"
            local_input.write_text("a,b,c\n1,2,3\n")
            reject = Path(tmpdir) / "reject.csv"

            result = _compute_and_show_output(
                input_file="in.csv",
                local_input_path=local_input,
                working_file=local_input,
                actual_output_file=output,
                encoding="utf-8",
                is_remote=False,
                mojibake_repaired=False,
                delimiter=",",
                keep_names=False,
                use_stdout=False,
                has_validation_errors=False,
                reject_count=1,
                error_types=[],
                reject_file=reject,
            )
        assert result == 0

    @patch("csvnorm.core.get_column_count", return_value=3)
    @patch("csvnorm.core.get_row_count", return_value=10)
    @patch("csvnorm.core.show_success_table")
    def test_input_size_fallback_when_no_local_path(self, mock_table, mock_rows, mock_cols):
        """Uses working_file size when local_input_path is None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output = Path(tmpdir) / "out.csv"
            output.write_text("a,b,c\n1,2,3\n")
            working = Path(tmpdir) / "working.csv"
            working.write_text("a,b,c\n1,2,3\n")
            reject = Path(tmpdir) / "reject.csv"

            result = _compute_and_show_output(
                input_file="https://example.com/data.csv",
                local_input_path=None,
                working_file=working,
                actual_output_file=output,
                encoding="remote",
                is_remote=True,
                mojibake_repaired=False,
                delimiter=",",
                keep_names=False,
                use_stdout=False,
                has_validation_errors=False,
                reject_count=1,
                error_types=[],
                reject_file=reject,
            )
        assert result == 0


# ---------------------------------------------------------------------------
# Stdin input (csvnorm -)
# ---------------------------------------------------------------------------


class TestStdinInput:
    """Tests for stdin input support (csvnorm -)."""

    def test_stdin_valid_data(self):
        """Stdin with valid CSV data processes correctly."""
        csv_data = b"name,age\nAlice,30\nBob,25\n"

        with patch("csvnorm.core.sys") as mock_sys, \
             tempfile.TemporaryDirectory() as tmpdir:
            mock_sys.stdin.isatty.return_value = False
            mock_sys.stdin.buffer.read.return_value = csv_data
            mock_sys.stdout = io.StringIO()

            output_file = Path(tmpdir) / "out.csv"
            result = process_csv(
                input_file="-",
                output_file=output_file,
                force=True,
            )
            assert result == 0
            assert output_file.exists()
            content = output_file.read_text()
            assert "name" in content or "alice" in content.lower()

    def test_stdin_tty_error(self):
        """Stdin from terminal (no piped data) exits with error."""
        with patch("csvnorm.core.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = True

            result = process_csv(
                input_file="-",
                output_file=None,
            )
            assert result == 1

    def test_stdin_with_output_file(self):
        """Stdin with -o flag writes to specified file."""
        csv_data = b"x,y\n1,2\n3,4\n"

        with patch("csvnorm.core.sys") as mock_sys, \
             tempfile.TemporaryDirectory() as tmpdir:
            mock_sys.stdin.isatty.return_value = False
            mock_sys.stdin.buffer.read.return_value = csv_data
            mock_sys.stdout = io.StringIO()

            output_file = Path(tmpdir) / "output.csv"
            result = process_csv(
                input_file="-",
                output_file=output_file,
                force=True,
            )
            assert result == 0
            assert output_file.exists()

    def test_stdin_with_check_mode(self):
        """Stdin with --check validates without processing."""
        csv_data = b"a,b\n1,2\n3,4\n"

        with patch("csvnorm.core.sys") as mock_sys:
            mock_sys.stdin.isatty.return_value = False
            mock_sys.stdin.buffer.read.return_value = csv_data
            mock_sys.stdout = io.StringIO()

            result = process_csv(
                input_file="-",
                output_file=None,
                check_only=True,
            )
            assert result == 0

    def test_stdin_with_non_utf8_encoding(self):
        """Stdin with non-UTF-8 data triggers encoding detection."""
        csv_data = "name,city\nAlice,Z\xfcrich\n".encode("latin-1")

        with patch("csvnorm.core.sys") as mock_sys, \
             tempfile.TemporaryDirectory() as tmpdir:
            mock_sys.stdin.isatty.return_value = False
            mock_sys.stdin.buffer.read.return_value = csv_data
            mock_sys.stdout = io.StringIO()

            output_file = Path(tmpdir) / "out.csv"
            result = process_csv(
                input_file="-",
                output_file=output_file,
                force=True,
            )
            assert result == 0
            assert output_file.exists()
