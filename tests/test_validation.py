"""Tests for validation module internal functions."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, call, patch

import duckdb
import pytest

from csvnorm.validation import (
    _count_lines,
    _detect_header_anomaly,
    _ensure_zipfs_extension,
    _fix_duckdb_keyword_prefix,
    _get_error_types,
    _try_read_csv_with_config,
    normalize_csv,
    validate_csv,
)


class TestCountLines:
    """Tests for _count_lines internal function."""

    def test_nonexistent_file(self):
        """Test that nonexistent file returns 0."""
        result = _count_lines(Path("/nonexistent/file.csv"))
        assert result == 0

    def test_empty_file(self):
        """Test that empty file returns 0."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "empty.csv"
            empty_file.touch()
            result = _count_lines(empty_file)
            assert result == 0

    def test_file_with_lines(self):
        """Test counting lines in a normal file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.csv"
            test_file.write_text("line1\nline2\nline3\n")
            result = _count_lines(test_file)
            assert result == 3


class TestGetErrorTypes:
    """Tests for _get_error_types internal function."""

    def test_nonexistent_file(self):
        """Test that nonexistent file returns empty list."""
        result = _get_error_types(Path("/nonexistent/reject_errors.csv"))
        assert result == []

    def test_empty_file(self):
        """Test that empty file returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            empty_file = Path(tmpdir) / "reject_errors.csv"
            empty_file.touch()
            result = _get_error_types(empty_file)
            assert result == []

    def test_only_header(self):
        """Test that file with only header returns empty list."""
        with tempfile.TemporaryDirectory() as tmpdir:
            header_file = Path(tmpdir) / "reject_errors.csv"
            header_file.write_text("scan_id,file,line,column_idx,column_name,error\n")
            result = _get_error_types(header_file)
            assert result == []

    def test_valid_errors(self):
        """Test extracting error types from valid reject file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reject_file = Path(tmpdir) / "reject_errors.csv"
            # DuckDB reject_errors format: scan_id,file,line,column_idx,column_name,error
            reject_file.write_text(
                "scan_id,file,line,column_idx,column_name,error\n"
                "1,test.csv,2,3,age,CAST\n"
                "2,test.csv,3,1,name,UNQUOTED_VALUE\n"
                "3,test.csv,4,3,age,CAST\n"
            )
            result = _get_error_types(reject_file)
            # Should return unique error types
            assert len(result) <= 3
            assert "CAST" in result or "UNQUOTED_VALUE" in result

    def test_malformed_csv(self):
        """Test handling malformed reject file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            malformed_file = Path(tmpdir) / "reject_errors.csv"
            # Write some malformed content
            malformed_file.write_text("scan_id,file,line\ngarbage,data")
            # Should not crash, returns empty list or partial results
            result = _get_error_types(malformed_file)
            assert isinstance(result, list)

    def test_max_three_errors(self):
        """Test that maximum 3 unique error types are returned."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reject_file = Path(tmpdir) / "reject_errors.csv"
            # Create file with 5 different error types
            reject_file.write_text(
                "scan_id,file,line,column_idx,column_name,error\n"
                "1,test.csv,2,1,col1,ERROR_TYPE_1\n"
                "2,test.csv,3,1,col1,ERROR_TYPE_2\n"
                "3,test.csv,4,1,col1,ERROR_TYPE_3\n"
                "4,test.csv,5,1,col1,ERROR_TYPE_4\n"
                "5,test.csv,6,1,col1,ERROR_TYPE_5\n"
            )
            result = _get_error_types(reject_file)
            # Should return at most 3 unique errors
            assert len(result) <= 3

    def test_unicode_decode_error(self):
        """Test handling of undecodable reject file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            reject_file = Path(tmpdir) / "reject_errors.csv"
            reject_file.write_bytes(b"\xff\xfe\xfa")
            result = _get_error_types(reject_file)
            assert result == []


class TestFixDuckdbKeywordPrefix:
    """Tests for _fix_duckdb_keyword_prefix internal function."""

    def test_removes_leading_underscore_from_header(self):
        """Test removing underscore prefix from any header column."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.csv"
            test_file.write_text("_value,_location,_data,_foo,bar\n1,2,3,4,5\n")

            _fix_duckdb_keyword_prefix(test_file)

            with open(test_file, "r") as f:
                header = f.readline().strip()
                data = f.readline().strip()

            assert header == "value,location,data,foo,bar"
            assert data == "1,2,3,4,5"

    def test_empty_file_no_change(self):
        """Test that empty file is handled gracefully."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "empty.csv"
            test_file.touch()
            _fix_duckdb_keyword_prefix(test_file)
            assert test_file.read_text() == ""


class TestDetectHeaderAnomaly:
    """Tests for _detect_header_anomaly internal function."""

    def test_detects_anomalous_first_line(self):
        """Detects title row when first line has fewer delimiters."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "anomaly.csv"
            test_file.write_text(
                "Title Line\n"
                "a;b;c\n"
                "d;e;f\n"
                "g;h;i\n"
            )
            result = _detect_header_anomaly(test_file)
            assert result == {"delim": ";", "skip": 1}

    def test_insufficient_lines(self):
        """Returns None when not enough lines to detect pattern."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "short.csv"
            test_file.write_text("a,b,c\n1,2,3\n")
            result = _detect_header_anomaly(test_file)
            assert result is None

    def test_no_dominant_delimiter(self):
        """Returns None when no delimiter appears in data lines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "nodominant.txt"
            test_file.write_text("Title\nalpha\nbeta\ngamma\n")
            result = _detect_header_anomaly(test_file)
            assert result is None

    def test_os_error_returns_none(self):
        """Returns None on file open error."""
        result = _detect_header_anomaly(Path("/nonexistent/file.csv"))
        assert result is None


class TestTryReadCsvWithConfig:
    """Tests for _try_read_csv_with_config internal function."""

    def test_returns_true_for_matching_delimiter(self):
        """Returns True when delimiter matches and multiple columns exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "comma.csv"
            test_file.write_text("a,b,c\n1,2,3\n")
            conn = duckdb.connect()
            try:
                result = _try_read_csv_with_config(
                    conn,
                    test_file,
                    {"delim": ",", "skip": 0},
                )
            finally:
                conn.close()
            assert result is True

    def test_returns_false_for_single_column(self):
        """Returns False when delimiter yields a single column."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "single.csv"
            test_file.write_text("a;b;c\n1;2;3\n")
            conn = duckdb.connect()
            try:
                result = _try_read_csv_with_config(
                    conn,
                    test_file,
                    {"delim": ",", "skip": 0},
                )
            finally:
                conn.close()
            assert result is False


class TestZipfsExtension:
    """Tests for zipfs extension handling."""

    def test_ensure_zipfs_skips_non_zip(self):
        conn = Mock()
        _ensure_zipfs_extension(conn, Path("data.csv"))
        conn.execute.assert_not_called()

    def test_ensure_zipfs_installs_when_missing(self):
        conn = Mock()
        conn.execute.side_effect = [duckdb.Error("missing"), None, None]

        _ensure_zipfs_extension(conn, "zip://archive.zip/data.csv")

        assert conn.execute.call_args_list == [
            call("LOAD zipfs"),
            call("INSTALL zipfs FROM community"),
            call("LOAD zipfs"),
        ]


class TestValidateCsv:
    """Tests for validate_csv main function."""

    def test_user_skip_rows_sets_fallback_config(self):
        """User-provided skip_rows sets fallback_config even on success."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "skip.csv"
            test_file.write_text("title row\ncol1,col2\n1,2\n")
            reject_file = Path(tmpdir) / "reject_errors.csv"
            reject_count, error_types, fallback = validate_csv(
                test_file, reject_file, skip_rows=1
            )
            assert isinstance(reject_count, int)
            assert isinstance(error_types, list)
            assert fallback == {"delim": ",", "skip": 1}

    @patch("csvnorm.validation._detect_header_anomaly")
    @patch("csvnorm.validation._try_read_csv_with_config")
    @patch("csvnorm.validation.duckdb.connect")
    def test_fallback_configs_used_on_sniffing_error(
        self, mock_connect, mock_try_read, mock_detect
    ):
        """Fallback iteration is used when sniffing fails."""
        mock_detect.return_value = None
        mock_try_read.side_effect = (
            lambda _conn, _path, cfg, **_kw: cfg["delim"] == "|" and cfg["skip"] == 1
        )

        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.execute.side_effect = [
            duckdb.Error("sniffing failed"),
            Mock(fetchall=lambda: []),
            None,
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "pipe.csv"
            test_file.write_text("a|b\n1|2\n")
            reject_file = Path(tmpdir) / "reject_errors.csv"
            reject_count, error_types, fallback = validate_csv(
                test_file, reject_file
            )

        assert reject_count == 0
        assert error_types == []
        assert fallback == {"delim": "|", "skip": 1}


class TestNormalizeCsv:
    """Tests for normalize_csv main function."""

    @patch("csvnorm.validation._try_read_csv_with_config")
    @patch("csvnorm.validation.duckdb.connect")
    def test_fallback_used_on_sniffing_error(self, mock_connect, mock_try_read):
        """Fallback configs are tried when normalization sniffing fails."""
        mock_try_read.side_effect = (
            lambda _conn, _path, cfg, **_kw: cfg["delim"] == ";" and cfg["skip"] == 1
        )

        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.execute.side_effect = [
            duckdb.Error("sniffing failed"),
            None,
            None,
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            input_file = Path(tmpdir) / "semi.csv"
            output_file = Path(tmpdir) / "out.csv"
            reject_file = Path(tmpdir) / "reject_errors.csv"
            result = normalize_csv(
                input_file,
                output_file,
                normalize_names=False,
                reject_file=reject_file,
            )

        assert result == {"delim": ";", "skip": 1}
