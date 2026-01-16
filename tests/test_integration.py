"""Integration tests for csvnorm."""

import tempfile
from pathlib import Path

import pytest

from csvnorm.core import process_csv

TEST_DIR = Path(__file__).parent.parent / "test"


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
        result = process_csv(
            input_file=TEST_DIR / "utf8_basic.csv",
            output_dir=output_dir,
        )
        assert result == 0
        assert (output_dir / "utf8_basic.csv").exists()

    @pytest.mark.skipif(
        not (TEST_DIR / "latin1_semicolon.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_latin1_with_delimiter(self, output_dir):
        """Test processing a Latin-1 file with semicolon delimiter."""
        result = process_csv(
            input_file=TEST_DIR / "latin1_semicolon.csv",
            output_dir=output_dir,
            delimiter=";",
        )
        assert result == 0
        assert (output_dir / "latin1_semicolon.csv").exists()

    @pytest.mark.skipif(
        not (TEST_DIR / "pipe_mixed_headers.csv").exists(),
        reason="Test fixtures not available",
    )
    def test_keep_names(self, output_dir):
        """Test that --keep-names preserves original headers."""
        result = process_csv(
            input_file=TEST_DIR / "pipe_mixed_headers.csv",
            output_dir=output_dir,
            keep_names=True,
        )
        assert result == 0

        output_file = output_dir / "pipe_mixed_headers.csv"
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
        result = process_csv(
            input_file=TEST_DIR / "pipe_mixed_headers.csv",
            output_dir=output_dir,
            keep_names=False,
        )
        assert result == 0

        output_file = output_dir / "pipe_mixed_headers.csv"
        assert output_file.exists()

        with open(output_file, "r") as f:
            header = f.readline().strip()
        # Headers should be snake_cased
        assert "user_id" in header or "username" in header

    def test_nonexistent_file(self, output_dir):
        """Test handling of nonexistent input file."""
        result = process_csv(
            input_file=Path("/nonexistent/file.csv"),
            output_dir=output_dir,
        )
        assert result == 1

    def test_force_overwrite(self, output_dir):
        """Test force overwrite behavior."""
        input_file = TEST_DIR / "utf8_basic.csv"
        if not input_file.exists():
            pytest.skip("Test fixtures not available")

        # First run
        result = process_csv(input_file=input_file, output_dir=output_dir)
        assert result == 0

        # Second run without force should fail
        result = process_csv(input_file=input_file, output_dir=output_dir)
        assert result == 1

        # Third run with force should succeed
        result = process_csv(input_file=input_file, output_dir=output_dir, force=True)
        assert result == 0
