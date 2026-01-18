"""Tests for mojibake repair utilities."""

from pathlib import Path

import pytest

from csvnorm.cli import main
from csvnorm.mojibake import detect_mojibake, repair_text, repair_file

FIXTURES_DIR = Path(__file__).parent.parent / "test"


def test_detect_mojibake_positive():
    text = "CittÃ  di prova"
    is_bad, score = detect_mojibake(text, sample_size=100)
    assert is_bad is True
    assert score > 0


def test_detect_mojibake_negative():
    text = "Città di prova"
    is_bad, score = detect_mojibake(text, sample_size=100)
    assert is_bad is False
    assert score >= 0


def test_detect_mojibake_invalid_sample():
    with pytest.raises(ValueError, match="sample_size must be non-negative"):
        detect_mojibake("test", sample_size=-1)


def test_detect_mojibake_force_mode():
    """Test that sample_size=0 forces repair without detection."""
    text = "Clean text with no mojibake"
    is_bad, score = detect_mojibake(text, sample_size=0)
    assert is_bad is True  # Force mode always returns True
    assert score == 0.0


def test_repair_text_changes():
    text = "CittÃ  di prova"
    repaired, fixed = repair_text(text)
    assert repaired is True
    assert fixed != text


def test_repair_file(tmp_path):
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"
    input_path.write_text("Nome,Citta\nGianni,CittÃ \n", encoding="utf-8")

    repaired, path_used = repair_file(input_path, output_path, sample_size=500)

    assert repaired is True
    assert path_used == output_path
    assert output_path.exists()
    assert "Città" in output_path.read_text(encoding="utf-8")


@pytest.mark.skipif(
    not (FIXTURES_DIR / "alberi_messina_mojibake.csv").exists(),
    reason="Mojibake fixture not available",
)
def test_fix_mojibake_fixture(tmp_path):
    input_path = FIXTURES_DIR / "alberi_messina_mojibake.csv"
    output_path = tmp_path / "alberi_messina_fixed.csv"

    text = input_path.read_text(encoding="utf-8", errors="replace")
    patterns = ["Ã¨", "Ã²", "Â°", "Ã©", "Ãì", "Ãù"]
    assert any(pat in text for pat in patterns)

    exit_code = main(
        [str(input_path), "--fix-mojibake", "4000", "-o", str(output_path), "-f"]
    )
    assert exit_code == 0
    fixed_text = output_path.read_text(encoding="utf-8", errors="replace")
    assert not any(pat in fixed_text for pat in patterns)


def test_fix_mojibake_force_mode(tmp_path):
    """Test that --fix-mojibake 0 forces repair even when badness is low."""
    input_path = tmp_path / "input.csv"
    output_path = tmp_path / "output.csv"

    # Create file with subtle mojibake (low badness score)
    input_path.write_text("Nome,Descrizione\nTest,â€œQuotedâ€�\n", encoding="utf-8")

    # Verify it has the mojibake pattern
    text = input_path.read_text(encoding="utf-8")
    assert "â€œ" in text or "â€�" in text

    # Use force mode (sample_size=0)
    exit_code = main(
        [str(input_path), "--fix-mojibake", "0", "-o", str(output_path), "-f"]
    )
    assert exit_code == 0

    # Verify repair happened
    fixed_text = output_path.read_text(encoding="utf-8")
    assert "â€œ" not in fixed_text
    assert "â€�" not in fixed_text
