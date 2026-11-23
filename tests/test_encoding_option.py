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


def _out(tmp_path: Path, name: str = "out.csv") -> Path:
    return tmp_path / name


class TestDeclaredEncoding:
    """The declared encoding replaces detection, with no fallback."""

    def test_windows1252_quotes_with_cp1252(self, tmp_path):
        # detection alone gives cp437 here (ôLibroö, 10Ç)
        r = run(str(TEST_DIR / "windows1252_quotes.csv"), "-e", "cp1252",
                "-o", str(_out(tmp_path)), cwd=tmp_path)
        assert r.returncode == 0, r.stderr.decode()
        text = _out(tmp_path).read_text(encoding="utf-8")
        assert "“Libro”" in text and "10€" in text

    def test_italian_grave_accents(self, tmp_path):
        src = tmp_path / "it.csv"
        src.write_bytes("id,nome\n1,Forlì\n2,però\n3,Cantù\n".encode("cp1252"))
        r = run(str(src), "-e", "cp1252", "-o", str(_out(tmp_path)), cwd=tmp_path)
        assert r.returncode == 0, r.stderr.decode()
        assert _out(tmp_path).read_text(encoding="utf-8") == "id,nome\n1,Forlì\n2,però\n3,Cantù\n"

    def test_cp850(self, tmp_path):
        src = tmp_path / "dos.csv"
        src.write_bytes("id,nome\n1,città\n2,perché\n".encode("cp850"))
        r = run(str(src), "-e", "cp850", "-o", str(_out(tmp_path)), cwd=tmp_path)
        assert r.returncode == 0, r.stderr.decode()
        assert "città" in _out(tmp_path).read_text(encoding="utf-8")

    def test_stdin(self, tmp_path):
        data = "id,nome\n1,Forlì\n".encode("cp1252")
        r = run("-", "-e", "cp1252", cwd=tmp_path, stdin=data)
        assert r.returncode == 0, r.stderr.decode()
        assert "Forlì" in r.stdout.decode("utf-8")

    def test_gzip(self, tmp_path):
        src = tmp_path / "data.csv.gz"
        with gzip.open(src, "wb") as f:
            f.write("id,nome\n1,Forlì\n2,10€\n".encode("cp1252"))
        r = run(str(src), "-e", "cp1252", "-o", str(_out(tmp_path)), cwd=tmp_path)
        assert r.returncode == 0, r.stderr.decode()
        text = _out(tmp_path).read_text(encoding="utf-8")
        assert "Forlì" in text and "10€" in text

    def test_zip(self, tmp_path):
        src = tmp_path / "data.zip"
        with zipfile.ZipFile(src, "w") as z:
            z.writestr("data.csv", "id,nome\n1,Forlì\n".encode("cp1252"))
        r = run(str(src), "-e", "cp1252", "-o", str(_out(tmp_path)), cwd=tmp_path)
        assert r.returncode == 0, r.stderr.decode()
        assert "Forlì" in _out(tmp_path).read_text(encoding="utf-8")

    def test_check_mode(self, tmp_path):
        src = tmp_path / "it.csv"
        src.write_bytes("id,nome\n1,Forlì\n".encode("cp1252"))
        assert run(str(src), "--check", "-e", "cp1252", cwd=tmp_path).returncode == 0
        bad = tmp_path / "bad.csv"
        bad.write_bytes(b"id,nome\n1,x\x81y\n")
        r = run(str(bad), "--check", "-e", "cp1252", cwd=tmp_path)
        assert r.returncode == 1

    def test_undecodable_byte_stops_without_fallback(self, tmp_path):
        src = tmp_path / "bad.csv"
        data = b"id,nome\n1,caf\xe9\n2,x\x81y\n"
        src.write_bytes(data)
        out = _out(tmp_path)
        r = run(str(src), "-e", "cp1252", "-o", str(out), cwd=tmp_path)
        assert r.returncode == 1
        err = r.stderr.decode()
        assert "cp1252" in err
        assert "0x81" in err
        assert str(data.index(b"\x81")) in err
        assert "without --encoding" in err
        assert not out.exists()

    def test_declared_utf8_on_non_utf8_file(self, tmp_path):
        src = tmp_path / "latin.csv"
        src.write_bytes("id,nome\n1,Forlì\n".encode("cp1252"))
        out = _out(tmp_path)
        r = run(str(src), "-e", "utf-8", "-o", str(out), cwd=tmp_path)
        assert r.returncode == 1
        assert "utf-8" in r.stderr.decode().lower()
        assert not out.exists()

    def test_declared_utf8_on_bom_file_same_as_today(self, tmp_path):
        out = _out(tmp_path)
        r = run(str(TEST_DIR / "utf8_sig_bom.csv"), "-e", "utf-8", "-o", str(out), cwd=tmp_path)
        assert r.returncode == 0, r.stderr.decode()
        expected = REPO / "tests" / "fixtures" / "golden" / "expected" / "utf8_sig_bom.csv"
        assert out.read_bytes() == expected.read_bytes()


def test_downloaded_url_uses_declared_encoding(tmp_path, monkeypatch):
    """URLs are downloaded first, then follow the local-file path."""
    import shutil

    from csvnorm import core

    src = tmp_path / "remote.csv"
    src.write_bytes("id,nome\n1,Forlì\n".encode("cp1252"))
    monkeypatch.setattr(
        core, "download_url_to_file", lambda url, path: shutil.copy(src, path)
    )
    out = tmp_path / "out.csv"
    result = core.process_csv("https://example.org/data.csv", out, encoding="cp1252")
    assert result == 0
    assert "Forlì" in out.read_text(encoding="utf-8")


class TestSummary:
    """The summary says the encoding was declared, not detected."""

    def test_file_mode(self, tmp_path):
        src = tmp_path / "it.csv"
        src.write_bytes("id,nome\n1,Forlì\n".encode("cp1252"))
        r = run(str(src), "-e", "cp1252", "-o", str(_out(tmp_path)), cwd=tmp_path)
        assert r.returncode == 0, r.stderr.decode()
        assert "cp1252 → UTF-8 (declared)" in r.stdout.decode()

    def test_stdout_mode(self, tmp_path):
        src = tmp_path / "it.csv"
        src.write_bytes("id,nome\n1,Forlì\n".encode("cp1252"))
        r = run(str(src), "-e", "cp1252", cwd=tmp_path)
        assert r.returncode == 0, r.stderr.decode()
        assert "cp1252 → UTF-8 (declared)" in r.stderr.decode()
        assert "declared" not in r.stdout.decode()

    def test_utf8_family(self, tmp_path):
        r = run(str(TEST_DIR / "utf8_basic.csv"), "-e", "utf8",
                "-o", str(_out(tmp_path)), cwd=tmp_path)
        assert r.returncode == 0, r.stderr.decode()
        out = r.stdout.decode()
        assert "utf8 (declared)" in out
        assert "→" not in out
