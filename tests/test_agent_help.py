"""Help, version, errors and exit codes as an agent sees them (no terminal)."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
TEST_DIR = REPO / "test"
BOX_CHARS = set("╭╮╰╯│─")


def run(*args: str, cwd: Path, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "csvnorm", *args],
        cwd=cwd, input=stdin, capture_output=True, check=False,
    )


class TestHelp:
    def test_sections_and_no_escape_codes(self, tmp_path):
        r = run("--help", cwd=tmp_path)
        assert r.returncode == 0
        text = r.stdout.decode()
        assert "\x1b" not in text
        for section in ("Start here:", "Output:", "Exit codes:", "Limits and side effects:"):
            assert section in text, section
        assert len(text.splitlines()) < 100

    def test_help_mentions_where_to_find_encoding_names(self, tmp_path):
        text = run("--help", cwd=tmp_path).stdout.decode()
        assert "docs.python.org" in text

    def test_start_here_commands_work(self, tmp_path):
        shutil.copy(TEST_DIR / "utf8_basic.csv", tmp_path / "data.csv")
        assert run("data.csv", "--check", cwd=tmp_path).returncode == 0
        r = run("data.csv", cwd=tmp_path)
        assert r.returncode == 0 and r.stdout
        assert run("data.csv", "-o", "clean.csv", cwd=tmp_path).returncode == 0
        assert (tmp_path / "clean.csv").exists()

    def test_no_args_prints_help_to_stdout_exit_2(self, tmp_path):
        r = run(cwd=tmp_path)
        assert r.returncode == 2
        assert "Start here:" in r.stdout.decode()


class TestVersion:
    def test_single_line_when_not_a_terminal(self, tmp_path):
        r = run("--version", cwd=tmp_path)
        assert r.returncode == 0
        lines = r.stdout.decode().strip().splitlines()
        assert len(lines) == 1
        assert lines[0].startswith("csvnorm ")


class TestExitCodes:
    def test_clean_input_exits_0(self, tmp_path):
        assert run(str(TEST_DIR / "utf8_basic.csv"), cwd=tmp_path).returncode == 0

    def test_rejected_rows_exit_1_with_output(self, tmp_path):
        r = run(str(TEST_DIR / "malformed_rows.csv"), "-o", "out.csv", cwd=tmp_path)
        assert r.returncode == 1
        assert (tmp_path / "out.csv").exists()

    @pytest.mark.parametrize(
        "args",
        [
            ("missing.csv",),
            ("missing.csv", "-e", "no-such-codec"),
            ("x.csv", "-s", "-1"),
            ("x.csv", "--check", "-o", "out.csv"),
        ],
    )
    def test_cannot_run_exits_2(self, tmp_path, args):
        assert run(*args, cwd=tmp_path).returncode == 2

    def test_undecodable_declared_encoding_exits_2(self, tmp_path):
        (tmp_path / "bad.csv").write_bytes(b"a,b\n1,x\x81y\n")
        r = run("bad.csv", "-e", "cp1252", "-o", "out.csv", cwd=tmp_path)
        assert r.returncode == 2
        assert not (tmp_path / "out.csv").exists()


class TestPlainErrors:
    def test_error_is_plain_text_on_stderr(self, tmp_path):
        r = run("missing.csv", cwd=tmp_path)
        err = r.stderr.decode()
        assert not BOX_CHARS & set(err)
        assert "\x1b" not in err
        assert err.lstrip().startswith("Error:")
        assert r.stdout == b""

    def test_validation_report_is_plain_text(self, tmp_path):
        r = run(str(TEST_DIR / "malformed_rows.csv"), cwd=tmp_path)
        err = r.stderr.decode()
        assert not BOX_CHARS & set(err)
        assert "Rejected rows:" in err
        assert "Details:" in err
