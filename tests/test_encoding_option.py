"""-e/--encoding: declared input encoding, run as a subprocess."""

import gzip
import subprocess
import sys
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TEST_DIR = REPO / "test"


def run(*args: str, cwd: Path, stdin: bytes | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "csvnorm", *args],
        cwd=cwd, input=stdin, capture_output=True, check=False,
    )


class TestOptionParsing:
    def test_unknown_encoding_exits_1_before_reading_input(self, tmp_path):
        r = run("does-not-exist.csv", "-e", "no-such-codec", cwd=tmp_path)
        assert r.returncode == 1
        err = r.stderr.decode()
        assert "no-such-codec" in err
        assert "Unknown encoding" in err
        assert "does-not-exist" not in err  # name checked first

    def test_non_text_codecs_are_rejected(self, tmp_path):
        for name in ("base64", "rot13"):
            r = run(str(TEST_DIR / "utf8_basic.csv"), "-e", name, cwd=tmp_path)
            assert r.returncode == 1, name
            assert "Unknown encoding" in r.stderr.decode()

    def test_aliases_are_accepted(self, tmp_path):
        for name in ("latin-1", "windows-1252", "cp1252"):
            r = run(str(TEST_DIR / "utf8_basic.csv"), "-e", name, cwd=tmp_path)
            assert r.returncode == 0, (name, r.stderr.decode())

    def test_long_form(self, tmp_path):
        r = run(str(TEST_DIR / "utf8_basic.csv"), "--encoding", "cp1252", cwd=tmp_path)
        assert r.returncode == 0, r.stderr.decode()

    def test_help_lists_the_option(self, tmp_path):
        out = run("--help", cwd=tmp_path).stdout.decode()
        assert "--encoding" in out and "-e" in out
