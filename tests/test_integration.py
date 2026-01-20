"""Integration tests for csvnorm."""

import gzip
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import duckdb

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
        assert result == 1
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
        assert result == 1
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
        assert result == 1

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
        assert result == 1

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
        assert result == 1

    @pytest.mark.network
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
        assert result == 1

    @patch("csvnorm.core.supports_http_range", return_value=False)
    @patch("csvnorm.validation.duckdb.connect")
    def test_http_range_not_supported(self, mock_connect, _mock_range, output_dir):
        """Test handling when server does not support HTTP range requests."""
        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/no-range.csv",
            output_file=output_file,
        )
        assert result == 1
        mock_connect.assert_not_called()

    @patch("csvnorm.core.supports_http_range", return_value=False)
    @patch("csvnorm.core.download_url_to_file")
    @patch("csvnorm.core.normalize_csv")
    @patch("csvnorm.core.validate_csv")
    def test_http_range_not_supported_with_download(
        self, mock_validate, mock_normalize, mock_download, _mock_range, output_dir
    ):
        """Test download fallback when server does not support HTTP range requests."""
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
            input_file="https://example.com/no-range.csv",
            output_file=output_file,
            download_remote=True,
        )
        assert result == 0
        mock_download.assert_called_once()

    @patch.object(core_module, "show_warning_panel")
    @patch("csvnorm.core.supports_http_range", return_value=True)
    def test_remote_compressed_url_warns(
        self, _mock_range, mock_warning, output_dir
    ):
        """Warn when remote URL points to compressed file."""
        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/data.zip",
            output_file=output_file,
        )
        assert result == 1
        assert mock_warning.call_count == 1

    @patch("csvnorm.core.supports_http_range", return_value=True)
    @patch("csvnorm.core.download_url_to_file")
    @patch("csvnorm.core.normalize_csv")
    @patch("csvnorm.core.validate_csv")
    def test_http_range_supported_with_download(
        self, mock_validate, mock_normalize, mock_download, _mock_range, output_dir
    ):
        """Test download fallback even when server supports HTTP range requests."""
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
            input_file="https://example.com/with-range.csv",
            output_file=output_file,
            download_remote=True,
        )
        assert result == 0
        mock_download.assert_called_once()

    @patch("csvnorm.core.supports_http_range", return_value=True)
    @patch("csvnorm.validation.duckdb.connect")
    def test_http_401_unauthorized(self, mock_connect, _mock_range, output_dir):
        """Test handling of 401 authentication required."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        # Simulate 401 error in DuckDB HTTP request
        mock_conn.execute.side_effect = duckdb.Error("HTTP Error 401")

        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/protected.csv",
            output_file=output_file,
        )
        assert result == 1

    @patch("csvnorm.core.supports_http_range", return_value=True)
    @patch("csvnorm.validation.duckdb.connect")
    def test_http_403_forbidden(self, mock_connect, _mock_range, output_dir):
        """Test handling of 403 forbidden."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.execute.side_effect = duckdb.Error("HTTP Error 403")

        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/forbidden.csv",
            output_file=output_file,
        )
        assert result == 1

    @patch("csvnorm.core.supports_http_range", return_value=True)
    @patch("csvnorm.validation.duckdb.connect")
    def test_http_timeout(self, mock_connect, _mock_range, output_dir):
        """Test handling of HTTP timeout."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        # First: SET http_timeout, Second: COPY...read_csv (fails with timeout)
        # Error message must contain "HTTP Error" or "HTTPException" to be caught
        mock_conn.execute.side_effect = [
            None,
            duckdb.Error("HTTPException: Connection timed out"),
        ]

        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/slow.csv",
            output_file=output_file,
        )
        assert result == 1

    @patch("csvnorm.core.supports_http_range", return_value=True)
    @patch("csvnorm.validation.duckdb.connect")
    def test_http_500_error(self, mock_connect, _mock_range, output_dir):
        """Test handling of HTTP 500 server error."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        # First: SET http_timeout, Second: COPY...read_csv (fails with HTTP error)
        mock_conn.execute.side_effect = [
            None,
            duckdb.Error("HTTP Error 500: Internal Server Error"),
        ]

        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/broken.csv",
            output_file=output_file,
        )
        assert result == 1
