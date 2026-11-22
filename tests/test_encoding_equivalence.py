"""Encoding detection compared with hand-checked expected encodings.

Each value was checked on 2026-11-22 by decoding the file and reading its
accented text. Values are normalized names, as returned by detect_encoding.
"""

from pathlib import Path

import pytest

from csvnorm.encoding import detect_encoding

REPO = Path(__file__).resolve().parents[1]
INPUTS = "tests/fixtures/golden/inputs"

EXPECTED = {
    "test/IMPORTAZIONI animali vivi 2025 luglio-dicembre.csv": "cp1252",  # Quantità, città
    "test/POSAS_2025_it_Comuni.csv": "utf-8",  # Età, 1°
    "test/Trasporto Pubblico Locale Settore Pubblico Allargato - Indicatore 2000-2020 Trasferimenti Correnti su Entrate Correnti.csv": "ascii",
    "test/alberi_messina_mojibake.csv": "utf-8",  # valid UTF-8 carrying mojibake
    "test/crlf_with_embedded_lf.csv": "ascii",
    "test/empty_file.csv": "utf-8",
    "test/latin1_semicolon.csv": "cp1252",  # Città, caffè, più
    "test/malformed_rows.csv": "ascii",
    "test/metadata_skip_rows.csv": "ascii",
    "test/pipe_mixed_headers.csv": "ascii",
    "test/title_row_skip.csv": "ascii",
    "test/utf8_basic.csv": "ascii",
    "test/utf8_sig_bom.csv": "utf-8",
    "test/windows1252_quotes.csv": "cp1252",  # “Libro”, 10€
    f"{INPUTS}/ascii_rrn.csv": "ascii",
    f"{INPUTS}/cp1252_cr_in_cell.csv": "cp1252",
    f"{INPUTS}/cp1252_cr_only.csv": "cp1252",
    f"{INPUTS}/cp1252_mixed_endings.csv": "cp1252",
    f"{INPUTS}/cp1252_rrn.csv": "cp1252",
    f"{INPUTS}/header_only.csv": "ascii",
    f"{INPUTS}/keywords_comma.csv": "ascii",
    f"{INPUTS}/latin1_crlf_in_cell.csv": "cp1252",  # città: same bytes in latin-1
}

# Today's detection differs from the expected encoding (known limit 7.1b):
# cp437 is returned, giving ôLibroö and 10Ç.
KNOWN_WRONG = {"test/windows1252_quotes.csv"}


def _param(path: str):
    marks = []
    if path in KNOWN_WRONG:
        marks.append(pytest.mark.xfail(strict=False, reason="known limit 7.1b"))
    return pytest.param(path, id=Path(path).name, marks=marks)


def test_expected_covers_all_csv_fixtures() -> None:
    found = {
        str(p.relative_to(REPO))
        for p in [*(REPO / "test").glob("*.csv"), *(REPO / INPUTS).glob("*.csv")]
    }
    assert found == set(EXPECTED)


@pytest.mark.parametrize("path", [_param(p) for p in EXPECTED])
def test_detected_encoding_matches_expected(path: str) -> None:
    assert detect_encoding(REPO / path) == EXPECTED[path]


def test_binary_file_is_rejected() -> None:
    with pytest.raises(ValueError, match="Cannot detect encoding"):
        detect_encoding(REPO / "test" / "binary_file.bin")
