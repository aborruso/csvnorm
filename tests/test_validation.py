"""Tests for validation module internal functions."""

import tempfile
from pathlib import Path

import pytest

from csvnorm.validation import _count_lines, _get_error_types


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
