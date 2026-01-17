"""Mojibake detection and repair utilities."""

from __future__ import annotations

from pathlib import Path

import ftfy
import ftfy.badness

DEFAULT_MOJIBAKE_SAMPLE = 5000


def detect_mojibake(text: str, sample_size: int) -> tuple[bool, float]:
    """Detect mojibake in a text sample using ftfy badness.

    Args:
        text: Full text content.
        sample_size: Number of characters to sample from start of text.

    Returns:
        Tuple of (is_bad, badness_score).
    """
    if sample_size <= 0:
        raise ValueError("sample_size must be a positive integer")

    sample = text[:sample_size] if len(text) > sample_size else text
    badness_score = ftfy.badness.badness(sample)
    is_bad = ftfy.badness.is_bad(sample)
    return is_bad, badness_score


def repair_text(text: str) -> tuple[bool, str]:
    """Repair mojibake in text using ftfy.

    Returns:
        Tuple of (was_repaired, repaired_text).
    """
    fixed_text = ftfy.fix_text(text)
    return fixed_text != text, fixed_text


def repair_file(
    input_path: Path, output_path: Path, sample_size: int
) -> tuple[bool, Path]:
    """Repair mojibake in a UTF-8 file.

    Args:
        input_path: Path to UTF-8 text file.
        output_path: Path to write repaired content.
        sample_size: Number of characters to sample for detection.

    Returns:
        Tuple of (was_repaired, path_to_use).
    """
    text = input_path.read_text(encoding="utf-8")
    is_bad, _ = detect_mojibake(text, sample_size)
    if not is_bad:
        return False, input_path

    repaired, fixed_text = repair_text(text)
    if not repaired:
        return False, input_path

    output_path.write_text(fixed_text, encoding="utf-8")
    return True, output_path
