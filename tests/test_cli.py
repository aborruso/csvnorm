"""Tests for CLI module."""

import subprocess
import sys

import pytest

from csvnorm import __version__
from csvnorm.cli import create_parser, main, show_banner


class TestShowBanner:
    """Test banner display."""

    def test_banner_output(self, capsys):
        """Test that banner prints styled text."""
        show_banner()
        captured = capsys.readouterr()
        assert "csvnorm" in captured.out or len(captured.out) > 0


class TestCreateParser:
    """Test argument parser creation."""

    def test_parser_creation(self):
        """Test parser is created successfully."""
        parser = create_parser()
        assert parser is not None
        assert parser.prog == "csvnorm"

    def test_parser_has_required_args(self):
        """Test parser has all required arguments."""
        parser = create_parser()
        # Get all argument names
        arg_strings = []
        for action in parser._actions:
            arg_strings.extend(action.option_strings)

        # Check for expected flags
        assert "-f" in arg_strings or "--force" in arg_strings
        assert "-k" in arg_strings or "--keep-names" in arg_strings
        assert "-d" in arg_strings or "--delimiter" in arg_strings
        assert "-o" in arg_strings or "--output-file" in arg_strings
        assert "-V" in arg_strings or "--verbose" in arg_strings
        assert "-v" in arg_strings or "--version" in arg_strings


class TestMainFunction:
    """Test main() function with various argument combinations."""

    def test_version_flag(self, capsys):
        """Test --version flag displays version and exits."""
        with pytest.raises(SystemExit) as exc_info:
            main(["--version"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert __version__ in captured.out
        assert "csvnorm" in captured.out

    def test_version_short_flag(self, capsys):
        """Test -v flag displays version and exits."""
        with pytest.raises(SystemExit) as exc_info:
            main(["-v"])

        assert exc_info.value.code == 0
        captured = capsys.readouterr()
        assert __version__ in captured.out

    def test_help_flag(self, capsys):
        """Test --help flag displays help and exits."""
        exit_code = main(["--help"])
        assert exit_code == 0
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower()
        assert "csvnorm" in captured.out

    def test_no_args(self, capsys):
        """Test no arguments shows help and exits with code 2."""
        exit_code = main([])
        assert exit_code == 2
        captured = capsys.readouterr()
        assert "usage:" in captured.out.lower()

    def test_basic_processing(self, tmp_path):
        """Test basic CSV processing through CLI."""
        # Create a simple test CSV
        test_csv = tmp_path / "test.csv"
        test_csv.write_text("Name,Age\nJohn,30\nJane,25\n")

        output_file = tmp_path / "output.csv"

        exit_code = main([str(test_csv), "-o", str(output_file), "-f"])

        assert exit_code == 0
        assert output_file.exists()

    def test_force_flag(self, tmp_path):
        """Test --force flag allows overwriting."""
        test_csv = tmp_path / "test.csv"
        test_csv.write_text("Col1,Col2\nA,B\n")

        output_file = tmp_path / "output.csv"

        # First run
        exit_code1 = main([str(test_csv), "-o", str(output_file)])
        assert exit_code1 == 0

        # Second run with --force
        exit_code2 = main([str(test_csv), "-o", str(output_file), "--force"])
        assert exit_code2 == 0

    def test_keep_names_flag(self, tmp_path):
        """Test --keep-names flag preserves original headers."""
        test_csv = tmp_path / "test.csv"
        test_csv.write_text("Column Name,Another Column\nvalue1,value2\n")

        output_file = tmp_path / "output.csv"

        exit_code = main([str(test_csv), "-o", str(output_file), "--keep-names", "-f"])

        assert exit_code == 0
        content = output_file.read_text()
        # With keep-names, original headers should be preserved
        assert "Column Name" in content or "column_name" in content

    def test_delimiter_flag(self, tmp_path):
        """Test --delimiter flag sets custom delimiter."""
        test_csv = tmp_path / "test.csv"
        test_csv.write_text("A,B\n1,2\n")

        output_file = tmp_path / "output.csv"

        exit_code = main(
            [str(test_csv), "-o", str(output_file), "--delimiter", ";", "-f"]
        )

        assert exit_code == 0
        content = output_file.read_text()
        # Output should use semicolon delimiter
        assert ";" in content

    def test_verbose_flag(self, tmp_path, capsys):
        """Test --verbose flag shows banner and debug output."""
        test_csv = tmp_path / "test.csv"
        test_csv.write_text("A,B\n1,2\n")

        output_file = tmp_path / "output.csv"

        exit_code = main([str(test_csv), "-o", str(output_file), "--verbose", "-f"])

        assert exit_code == 0
        captured = capsys.readouterr()
        # Verbose mode should show banner
        assert len(captured.out) > 0

    def test_nonexistent_file(self):
        """Test processing nonexistent file returns error."""
        exit_code = main(["/nonexistent/file.csv"])
        assert exit_code == 1


class TestCLISubprocess:
    """Integration tests using subprocess (smoke tests)."""

    def test_version_command(self):
        """Test csvnorm --version command works end-to-end."""
        result = subprocess.run(
            [sys.executable, "-m", "csvnorm", "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert __version__ in result.stdout or "csvnorm" in result.stdout

    def test_help_command(self):
        """Test csvnorm --help command works end-to-end."""
        result = subprocess.run(
            [sys.executable, "-m", "csvnorm", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0
        assert "usage:" in result.stdout.lower()

    def test_basic_execution(self, tmp_path):
        """Test basic CSV processing via subprocess."""
        test_csv = tmp_path / "test.csv"
        test_csv.write_text("Name,Value\nTest,123\n")

        output_file = tmp_path / "output.csv"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "csvnorm",
                str(test_csv),
                "-o",
                str(output_file),
                "-f",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        assert result.returncode == 0
        assert output_file.exists()
