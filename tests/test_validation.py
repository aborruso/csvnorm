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

    def test_lone_cr_is_not_a_line_break(self):
        """A bare CR inside a quoted field must not be counted as a new line."""
        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = Path(tmpdir) / "test.csv"
            test_file.write_bytes(b'h\n"x\ry"\n')
            assert _count_lines(test_file) == 2

    def test_reject_count_with_cr_in_rejected_row(self):
        """One rejected row containing a bare CR counts as one reject."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_file = Path(tmpdir) / "cr.csv"
            csv_file.write_bytes(b'a,b,c\n1,2,3\n4,"x\ry",5,6\n7,8,9\n')
            reject_file = Path(tmpdir) / "reject.csv"
            reject_count, _, _ = validate_csv(csv_file, reject_file)
            assert reject_count == 2  # header + 1 rejected row

    def test_reject_file_is_valid_utf8_with_long_multibyte_row(self):
        """Issue #29: DuckDB truncates csv_line in the reject table; with
        duckdb<2.0 the cut could split a multibyte char (e.g. 'à' -> b'\\xc3')."""
        with tempfile.TemporaryDirectory() as tmpdir:
            csv_file = Path(tmpdir) / "long.csv"
            # Rejected rows longer than the cut, each shifted by one byte so that
            # in at least one of them an 'à' straddles the cut point
            long_text = "uniformità " * 2000
            rows = [f'{i},"{"x" * i}{long_text}",extra' for i in range(12)]
            csv_file.write_text("a,b\n1,2\n" + "\n".join(rows) + "\n", encoding="utf-8")
            reject_file = Path(tmpdir) / "reject.csv"
            reject_count, _, _ = validate_csv(csv_file, reject_file)
            assert reject_count == 13  # header + 12 rejected rows
            reject_file.read_bytes().decode("utf-8")  # raises if invalid


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


class TestNormalizeCsvHeaderAndLineEndings:
    """Header keyword fix and CRLF rows written by DuckDB during the COPY.

    Expected outputs with the comma delimiter are the 1.3.0 ones (2026-11-22).
    """

    def _run(self, tmp_path, data: bytes, **kwargs) -> bytes:
        src = tmp_path / "in.csv"
        src.write_bytes(data)
        out = tmp_path / "out.csv"
        normalize_csv(src, out, **kwargs)
        return out.read_bytes()

    def test_keywords_lose_duckdb_prefix(self, tmp_path):
        out = self._run(tmp_path, b"select,value,order,bar\n1,2,3,4\n")
        assert out == b"select,value,order,bar\n1,2,3,4\n"

    def test_underscore_user_columns_kept(self, tmp_path):
        # _id and _source are not keywords; a user column _value is
        # indistinguishable from DuckDB's prefix and becomes value, as today.
        out = self._run(tmp_path, b"_id,_source,_value\n1,2,3\n")
        assert out == b"_id,_source,value\n1,2,3\n"

    def test_duplicate_keyword_column_and_order(self, tmp_path):
        out = self._run(tmp_path, b"select,_id,From,a b,_select\n1,2,3,4,5\n")
        assert out == b"select,_id,from,a_b,_select_1\n1,2,3,4,5\n"

    def test_empty_file(self, tmp_path):
        assert self._run(tmp_path, b"") == b"column0\n"

    def test_escaped_quotes_inside_field(self, tmp_path):
        out = self._run(tmp_path, b'a,b\n1,"say ""hi"""\n')
        assert out == b'a,b\n1,"say ""hi"""\n'

    @pytest.mark.parametrize("delim", [";", "|", "\t"])
    def test_keyword_fix_with_any_delimiter(self, tmp_path, delim):
        out = self._run(
            tmp_path, b"select,_id,From,a b,_select\n1,2,3,4,5\n", delimiter=delim
        )
        d = delim.encode()
        header = d.join([b"select", b"_id", b"from", b"a_b", b"_select_1"])
        assert out == header + b"\n" + d.join(b"12345"[i:i + 1] for i in range(5)) + b"\n"

    def test_crlf_rows_keep_in_cell_lf(self, tmp_path):
        out = self._run(tmp_path, b'a,b\n1,"in\ncell"\n2,x\n', crlf=True)
        assert out == b'a,b\r\n1,"in\ncell"\r\n2,x\r\n'

    def test_crlf_rows_keep_in_cell_crlf(self, tmp_path):
        out = self._run(tmp_path, b'a,b\r\n1,"in\r\ncell"\r\n', crlf=True)
        assert out == b'a,b\r\n1,"in\r\ncell"\r\n'

    def test_lf_rows_by_default(self, tmp_path):
        out = self._run(tmp_path, b'a,b\n1,"in\ncell"\n2,x\n')
        assert out == b'a,b\n1,"in\ncell"\n2,x\n'

    def test_keep_names_selects_all_columns_as_is(self, tmp_path):
        out = self._run(tmp_path, b"Select,My Value\n1,2\n", normalize_names=False)
        assert out == b"Select,My Value\n1,2\n"
