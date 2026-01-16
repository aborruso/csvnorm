"""Integration tests for csvnorm."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from csvnorm.core import process_csv

TEST_DIR = Path(__file__).parent.parent / "test"
# Real public URL for testing
TEST_URL = "https://raw.githubusercontent.com/aborruso/csvnorm/refs/heads/main/test/utf8_basic.csv"


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

    @patch("csvnorm.validation.duckdb.connect")
    def test_http_401_unauthorized(self, mock_connect, output_dir):
        """Test handling of 401 authentication required."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        # Simulate 401 error in DuckDB HTTP request
        mock_conn.execute.side_effect = Exception("HTTP Error 401")

        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/protected.csv",
            output_file=output_file,
        )
        assert result == 1

    @patch("csvnorm.validation.duckdb.connect")
    def test_http_403_forbidden(self, mock_connect, output_dir):
        """Test handling of 403 forbidden."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        mock_conn.execute.side_effect = Exception("HTTP Error 403")

        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/forbidden.csv",
            output_file=output_file,
        )
        assert result == 1

    @patch("csvnorm.validation.duckdb.connect")
    def test_http_timeout(self, mock_connect, output_dir):
        """Test handling of HTTP timeout."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        # First: SET http_timeout, Second: COPY...read_csv (fails with timeout)
        # Error message must contain "HTTP Error" or "HTTPException" to be caught
        mock_conn.execute.side_effect = [
            None,
            Exception("HTTPException: Connection timed out"),
        ]

        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/slow.csv",
            output_file=output_file,
        )
        assert result == 1

    @patch("csvnorm.validation.duckdb.connect")
    def test_http_500_error(self, mock_connect, output_dir):
        """Test handling of HTTP 500 server error."""
        mock_conn = Mock()
        mock_connect.return_value = mock_conn
        # First: SET http_timeout, Second: COPY...read_csv (fails with HTTP error)
        mock_conn.execute.side_effect = [
            None,
            Exception("HTTP Error 500: Internal Server Error"),
        ]

        output_file = output_dir / "output.csv"
        result = process_csv(
            input_file="https://example.com/broken.csv",
            output_file=output_file,
        )
        assert result == 1
