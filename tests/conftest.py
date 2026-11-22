"""Shared test setup."""

import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolated_tempdir(tmp_path_factory, monkeypatch):
    """Keep files csvnorm leaves in the system temp dir (stdout reject files) out of /tmp."""
    tmpdir = tmp_path_factory.mktemp("systemp")
    monkeypatch.setenv("TMPDIR", str(tmpdir))
    monkeypatch.setattr(tempfile, "tempdir", str(tmpdir))


@pytest.fixture
def make_csv(tmp_path):
    """Return a function that writes a synthetic CSV and returns its path.

    Without ``body`` it writes the header ``a,b,c,d,e`` and ``rows`` ASCII rows
    ``i,i,i,i,i``; ``insert`` replaces column ``e`` of the given row numbers
    (1-based) with the given already-encoded bytes. With ``body`` it writes
    those bytes as they are.
    """
    counter = iter(range(1_000_000))

    def make(
        rows: int = 0,
        insert: dict[int, bytes] | None = None,
        crlf: bool = False,
        body: bytes | None = None,
    ):
        path = tmp_path / f"synthetic_{next(counter)}.csv"
        if body is not None:
            path.write_bytes(body)
            return path
        eol = b"\r\n" if crlf else b"\n"
        insert = insert or {}
        with open(path, "wb") as f:
            f.write(b"a,b,c,d,e" + eol)
            for i in range(1, rows + 1):
                n = str(i).encode()
                last = insert.get(i, n)
                f.write(b",".join([n, n, n, n, last]) + eol)
        return path

    return make
