"""Encoding detection and conversion for CSV files."""

import codecs
import logging
from pathlib import Path
from typing import BinaryIO

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

# Preferred when charset_normalizer scores several codecs the same, in order
WESTERN_ENCODINGS = ("cp1252", "latin_1", "iso8859_15")

# Bytes read per step when converting to UTF-8
CHUNK_SIZE = 4 * 2**20


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

    # charset_normalizer's best() does not always return the most coherent
    # candidate among those with the lowest chaos, and on a tie it picks the
    # first one (e.g. cp1250 over cp1252 for Italian text). Pick the highest
    # coherence among the least chaotic; on a tie prefer a Western codec.
    least_chaotic = [m for m in result if m.chaos == best.chaos]
    top_coherence = max(m.coherence for m in least_chaotic)
    tied = [m.encoding for m in least_chaotic if m.coherence == top_coherence]
    encoding = next((e for e in WESTERN_ENCODINGS if e in tied), tied[0])
    if encoding != best.encoding:
        logger.debug(f"Candidates {tied}: choosing {encoding} over {best.encoding}")

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
    """Convert file from source encoding to UTF-8, in fixed-size chunks.

    Line breaks (CR, LF, CRLF) are kept byte for byte, also inside quoted
    fields, so the result is the same on every operating system.

    Args:
        input_path: Path to input file.
        output_path: Path for UTF-8 output file.
        source_encoding: Source file encoding.

    Returns:
        Path to the converted file.

    Raises:
        UnicodeDecodeError: If file cannot be decoded with the specified encoding.
            The ``file_offset`` attribute holds the position of the bad byte
            in the input file. The partial output is removed.
        LookupError: If the encoding is not supported.
    """
    logger.debug(f"Converting from {source_encoding} to UTF-8")

    # Validate encoding exists, before any file is opened
    try:
        codecs.lookup(source_encoding)
    except LookupError as e:
        raise LookupError(f"Unknown encoding: {source_encoding}") from e

    decoder = codecs.getincrementaldecoder(source_encoding)(errors="strict")
    offset = 0
    try:
        with open(input_path, "rb") as src, open(output_path, "wb") as dst:
            while chunk := src.read(CHUNK_SIZE):
                _decode_into(decoder, chunk, offset, dst)
                offset += len(chunk)
            _decode_into(decoder, b"", offset, dst, final=True)
    except BaseException:
        output_path.unlink(missing_ok=True)
        raise

    logger.debug(f"Converted file written to: {output_path}")
    return output_path


def _decode_into(
    decoder: codecs.IncrementalDecoder,
    chunk: bytes,
    offset: int,
    dst: BinaryIO,
    final: bool = False,
) -> None:
    """Decode one chunk and write it as UTF-8; on error record the file offset.

    ``offset`` is the number of input bytes read before ``chunk``. Bytes still
    held by the decoder from earlier chunks come before ``chunk`` in the file,
    so they are subtracted from the error position.
    """
    pending = len(decoder.getstate()[0])
    try:
        dst.write(decoder.decode(chunk, final=final).encode("utf-8"))
    except UnicodeDecodeError as e:
        e.file_offset = offset - pending + e.start  # type: ignore[attr-defined]
        raise
