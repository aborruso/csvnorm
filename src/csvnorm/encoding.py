"""Encoding detection and conversion for CSV files."""

import codecs
import logging
from collections.abc import Callable
from pathlib import Path
from typing import BinaryIO, Literal, NamedTuple

from charset_normalizer import CharsetMatches, from_bytes, from_path

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

# Sampled detection: see docs/designs/speed-up-large-files.md, phase four
SCAN_CHUNK = 4 * 2**20
MAX_WINDOWS = 129  # first UTF-8 error + at most 128 high byte values
WINDOW_HALF = 256  # bytes on each side of the target byte
MAX_CUT_SEARCH = 64  # bytes searched outward on each side for a cut byte
# A byte below 0x40 that is not a digit is never a later part of a character
# in Shift_JIS, GBK, GB18030, Big5, EUC or UTF-8, so a window can end after it
CUT_BYTES = frozenset(b for b in range(0x40) if not 0x30 <= b <= 0x39)
MAX_ATTEMPTS = 8  # occurrences tried per byte value before giving up
ASCII_BYTES = bytes(range(128))

UTF16_32_BOMS = (b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff", b"\xff\xfe", b"\xfe\xff")
UTF8_BOM = b"\xef\xbb\xbf"


class _ScanResult(NamedTuple):
    route: Literal["ascii", "utf-8", "full", "sample"]
    reason: str = ""
    sample: bytes = b""
    windows: int = 0
    high_values: int = 0


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


def _pick_encoding(result: CharsetMatches, file_path: Path) -> str:
    """Pick the encoding among charset_normalizer matches (tie-break rules)."""
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


def _detect_encoding_full(file_path: Path) -> str:
    """Detection on the whole file with charset_normalizer (csvnorm <= 1.3.0)."""
    return _pick_encoding(from_path(file_path), file_path)


def _window(f: BinaryIO, size: int, pos: int) -> tuple[int, int] | None:
    """Byte range around ``pos`` that starts and ends right after a cut byte.

    The file start and end count as cut points. Returns None when no cut byte
    is found within ``MAX_CUT_SEARCH`` bytes on a side.
    """
    lo = max(0, pos - WINDOW_HALF - MAX_CUT_SEARCH)
    f.seek(lo)
    buf = f.read(min(size, pos + WINDOW_HALF + MAX_CUT_SEARCH + 1) - lo)

    left = pos - WINDOW_HALF
    start: int | None
    if left <= 0:
        start = 0
    else:
        start = None
        for k in range(left, max(left - MAX_CUT_SEARCH, 0) - 1, -1):
            if k == 0:
                start = 0
                break
            if buf[k - 1 - lo] in CUT_BYTES:
                start = k
                break
        if start is None:
            return None

    right = pos + WINDOW_HALF
    end: int | None
    if right >= size - 1:
        end = size
    else:
        end = None
        for k in range(right, min(right + MAX_CUT_SEARCH, size - 1) + 1):
            if k == size - 1:
                end = size
                break
            if buf[k - lo] in CUT_BYTES:
                end = k + 1
                break
        if end is None:
            return None
    assert start is not None and end is not None
    return start, end


def _scan(file_path: Path) -> _ScanResult:
    """Classify the file and, if it is not UTF-8, build the detection sample."""
    size = file_path.stat().st_size
    if size == 0:
        return _ScanResult("utf-8")

    with open(file_path, "rb") as f:
        head = f.read(4)
        if any(head.startswith(bom) for bom in UTF16_32_BOMS):
            return _ScanResult("full", "utf-16/32 bom")
        has_bom = head.startswith(UTF8_BOM)

        # First pass: strict UTF-8, NUL bytes, ASCII only
        f.seek(0)
        decoder = codecs.getincrementaldecoder("utf-8")(errors="strict")
        all_ascii = True
        error_pos: int | None = None
        offset = 0
        while chunk := f.read(SCAN_CHUNK):
            if b"\x00" in chunk:
                return _ScanResult("full", "nul byte")
            all_ascii = all_ascii and chunk.isascii()
            pending = len(decoder.getstate()[0])
            try:
                decoder.decode(chunk)
            except UnicodeDecodeError as e:
                error_pos = offset - pending + e.start
                break
            offset += len(chunk)
        if error_pos is None:
            try:
                decoder.decode(b"", final=True)
            except UnicodeDecodeError as e:
                error_pos = offset - len(decoder.getstate()[0]) + e.start
        if error_pos is None:
            return _ScanResult("ascii" if all_ascii and not has_bom else "utf-8")
        if has_bom:
            return _ScanResult("full", "utf-8 bom with invalid utf-8")

        # Second pass: one window per high byte value, plus the first error
        ranges: list[tuple[int, int]] = []
        first_error = _window(f, size, error_pos)
        if first_error is not None:
            ranges.append(first_error)
        covered: set[int] = set()
        seen: set[int] = set()
        offset = 0
        with open(file_path, "rb") as f2:
            while chunk := f2.read(SCAN_CHUNK):
                if b"\x00" in chunk:
                    return _ScanResult("full", "nul byte")
                values = set(chunk.translate(None, ASCII_BYTES))
                seen |= values
                for value in values - covered:
                    target = bytes([value])
                    i = chunk.find(target)
                    attempts = 0
                    while i != -1 and attempts < MAX_ATTEMPTS:
                        found = _window(f, size, offset + i)
                        if found is not None:
                            ranges.append(found)
                            covered.add(value)
                            break
                        attempts += 1
                        i = chunk.find(target, i + 1)
                    if value not in covered and attempts >= MAX_ATTEMPTS:
                        return _ScanResult("full", f"no cut point for byte 0x{value:02X}")
                offset += len(chunk)

        missing = seen - covered
        if missing:
            return _ScanResult("full", f"no cut point for byte 0x{min(missing):02X}")

        merged: list[tuple[int, int]] = []
        for start, end in sorted(ranges):
            if merged and start <= merged[-1][1]:
                merged[-1] = (merged[-1][0], max(merged[-1][1], end))
            else:
                merged.append((start, end))
        parts = []
        for start, end in merged:
            f.seek(start)
            parts.append(f.read(end - start))
    return _ScanResult("sample", "", b"\n".join(parts), len(merged), len(covered))


def _prefer_western_if_same_text(encoding: str, sample: bytes) -> str:
    """Prefer a Western codec that decodes the sample to the same text.

    The sample holds every high byte value of the file, so for single-byte
    codecs the same text on the sample means the same text on the whole file.
    """
    if encoding in {normalize_encoding_name(w) for w in WESTERN_ENCODINGS}:
        return encoding
    try:
        text = sample.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return encoding
    for western in WESTERN_ENCODINGS:
        try:
            if sample.decode(western) == text:
                logger.debug(f"Same text as {encoding}: choosing {western}")
                return normalize_encoding_name(western)
        except UnicodeDecodeError:
            continue
    return encoding


def detect_encoding(file_path: Path) -> str:
    """Detect the encoding of a file.

    Valid UTF-8 and ASCII are recognised with a strict streaming decode. For
    other files charset_normalizer examines a small sample with every high
    byte value of the file, instead of decoding the whole file once per
    candidate codec. Files with a UTF-16/32 BOM or NUL bytes use full-file
    detection as before.

    Args:
        file_path: Path to the file to analyze.

    Returns:
        Detected encoding name (normalized for Python codecs).

    Raises:
        ValueError: If encoding cannot be detected.
    """
    logger.debug(f"Detecting encoding for: {file_path}")
    scan = _scan(file_path)

    if scan.route == "sample":
        logger.debug(
            f"Encoding route: sample ({scan.windows} windows, "
            f"{scan.high_values} byte values, {len(scan.sample)} bytes)"
        )
        result = from_bytes(
            scan.sample,
            steps=1,
            chunk_size=len(scan.sample),
            cp_exclusion=["utf_8", "ascii"],
        )
        best = result.best()
        if best is None:
            logger.debug("Encoding route: full (no candidate for the sample)")
            return _detect_encoding_full(file_path)
        # On a small sample charset_normalizer's coherence is a weak signal
        # (Italian cp1252 can score best as cp1258): among the least chaotic
        # candidates, a Western codec wins (decided 2026-11-22).
        least = [m.encoding for m in result if m.chaos == best.chaos]
        western = next((w for w in WESTERN_ENCODINGS if w in least), None)
        if western is not None:
            logger.debug(f"Least chaotic {least}: choosing Western {western}")
            return normalize_encoding_name(western)
        return _prefer_western_if_same_text(
            _pick_encoding(result, file_path), scan.sample
        )

    if scan.route == "full":
        logger.debug(f"Encoding route: full ({scan.reason})")
        return _detect_encoding_full(file_path)

    logger.debug(f"Encoding route: {scan.route}")
    return scan.route


def detect_and_convert(
    input_path: Path,
    output_path: Path,
    on_detected: Callable[[str], None] | None = None,
) -> str:
    """Detect the encoding and convert to UTF-8 if needed, with one fallback.

    If the strict conversion fails, the encoding is detected again on the
    whole file and the conversion is retried once.

    Returns:
        The encoding used.

    Raises:
        UnicodeDecodeError: If the second conversion also fails.
        ValueError: If the encoding cannot be detected.
        LookupError: If the encoding is unknown.
    """
    encoding = detect_encoding(input_path)
    if on_detected is not None:
        on_detected(encoding)
    if not needs_conversion(encoding):
        return encoding
    try:
        convert_to_utf8(input_path, output_path, encoding)
        return encoding
    except UnicodeDecodeError:
        logger.debug("Encoding fallback: full detection after conversion error")
    encoding = _detect_encoding_full(input_path)
    if on_detected is not None:
        on_detected(encoding)
    if needs_conversion(encoding):
        convert_to_utf8(input_path, output_path, encoding)
    return encoding


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
    except UnicodeDecodeError as e:
        output_path.unlink(missing_ok=True)
        e.source_encoding = source_encoding  # type: ignore[attr-defined]
        raise
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
