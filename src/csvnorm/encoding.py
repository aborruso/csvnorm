"""Encoding detection and conversion for CSV files."""

import codecs
import logging
from pathlib import Path

from charset_normalizer import from_path

logger = logging.getLogger("csvnorm")

# Encoding alias mapping for Python codec compatibility
ENCODING_ALIASES: dict[str, str] = {
    "macroman": "mac_roman",
    "macintosh": "mac_roman",
    "utf_8": "utf-8",
    "utf_8_sig": "utf-8-sig",
    "ascii": "ascii",
}

# Encodings that don't need conversion
UTF8_ENCODINGS = frozenset({"utf-8", "ascii", "utf-8-sig"})


def normalize_encoding_name(encoding: str) -> str:
    """Normalize encoding name to Python codec name.

    Args:
        encoding: Raw encoding name from detection.

    Returns:
        Normalized encoding name compatible with Python codecs.
    """
    encoding_lower = encoding.lower().replace("-", "_")

    # Check alias mapping
    if encoding_lower in ENCODING_ALIASES:
        return ENCODING_ALIASES[encoding_lower]

    # Try to normalize with underscores to dashes
    return encoding_lower.replace("_", "-")


def detect_encoding(file_path: Path) -> str:
    """Detect the encoding of a file using charset_normalizer.

    Args:
        file_path: Path to the file to analyze.

    Returns:
        Detected encoding name (normalized for Python codecs).

    Raises:
        ValueError: If encoding cannot be detected.
    """
    logger.debug(f"Detecting encoding for: {file_path}")

    result = from_path(file_path)
    best = result.best()

    if best is None:
        logger.debug("charset_normalizer failed, cannot detect encoding")
        raise ValueError(f"Cannot detect encoding for: {file_path}")

    encoding = best.encoding
    logger.debug(f"Detected encoding: {encoding}")

    # Normalize the encoding name
    normalized = normalize_encoding_name(encoding)
    if normalized != encoding.lower():
        logger.debug(f"Normalized encoding: {encoding} -> {normalized}")

    return normalized


def needs_conversion(encoding: str) -> bool:
    """Check if file needs encoding conversion to UTF-8.

    Args:
        encoding: Detected encoding name.

    Returns:
        True if conversion is needed, False otherwise.
    """
    encoding_lower = encoding.lower()
    return encoding_lower not in UTF8_ENCODINGS


def convert_to_utf8(input_path: Path, output_path: Path, source_encoding: str) -> Path:
    """Convert file from source encoding to UTF-8.

    Args:
        input_path: Path to input file.
        output_path: Path for UTF-8 output file.
        source_encoding: Source file encoding.

    Returns:
        Path to the converted file.

    Raises:
        UnicodeDecodeError: If file cannot be decoded with the specified encoding.
        LookupError: If the encoding is not supported.
    """
    logger.debug(f"Converting from {source_encoding} to UTF-8")

    # Validate encoding exists
    try:
        codecs.lookup(source_encoding)
    except LookupError as e:
        raise LookupError(f"Unknown encoding: {source_encoding}") from e

    # Read with source encoding, write as UTF-8
    with open(input_path, "r", encoding=source_encoding, errors="strict") as f:
        content = f.read()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    logger.debug(f"Converted file written to: {output_path}")
    return output_path
