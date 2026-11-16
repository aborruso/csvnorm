"""Shared test setup."""

import tempfile

import pytest


@pytest.fixture(autouse=True)
def isolated_tempdir(tmp_path_factory, monkeypatch):
    """Keep files csvnorm leaves in the system temp dir (stdout reject files) out of /tmp."""
    tmpdir = tmp_path_factory.mktemp("systemp")
    monkeypatch.setenv("TMPDIR", str(tmpdir))
    monkeypatch.setattr(tempfile, "tempdir", str(tmpdir))
