"""Utility functions for csvnorm."""

import logging
import re
import shutil
import subprocess
import ssl
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

import duckdb
import requests

from rich.logging import RichHandler


def to_snake_case(name: str) -> str:
    """Convert filename to clean snake_case.

    Replicates the bash logic:
    tr '[:upper:]' '[:lower:]' |
    sed -E 's/[^a-z0-9]+/_/g' |
    sed -E 's/_+/_/g' |
    sed -E 's/^_|_$//g'
    """
    # Remove .csv extension if present
    if name.lower().endswith(".csv"):
        name = name[:-4]

    # Convert to lowercase
    name = name.lower()

    # Replace non-alphanumeric with underscore
    name = re.sub(r"[^a-z0-9]+", "_", name)

    # Collapse multiple underscores
    name = re.sub(r"_+", "_", name)

    # Remove leading/trailing underscores
    name = name.strip("_")

    return name


def setup_logger(verbose: bool = False) -> logging.Logger:
    """Setup and return a logger instance with rich formatting.

    Args:
        verbose: If True, set log level to DEBUG, else INFO.
    """
    logger = logging.getLogger("csvnorm")

    if not logger.handlers:
        handler = RichHandler(
            show_time=False, show_path=verbose, markup=True, rich_tracebacks=True
        )
        logger.addHandler(handler)

    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    return logger


def validate_delimiter(delimiter: str) -> None:
    """Validate that delimiter is a single character.

    Raises:
        ValueError: If delimiter is not exactly one character.
    """
    if len(delimiter) != 1:
        raise ValueError("--delimiter must be a single character")


def ensure_output_dir(output_dir: Path) -> None:
    """Create output directory if it doesn't exist."""
    output_dir.mkdir(parents=True, exist_ok=True)


def is_url(input_str: str) -> bool:
    """Check if input string is an HTTP/HTTPS URL.

    Args:
        input_str: String to check.

    Returns:
        True if input is HTTP/HTTPS URL, False otherwise.
    """
    try:
        result = urlparse(input_str)
        return result.scheme in ("http", "https") and bool(result.netloc)
    except (AttributeError, TypeError, ValueError):
        return False


def validate_url(url: str) -> None:
    """Validate URL has HTTP/HTTPS protocol.

    Args:
        url: URL to validate.

    Raises:
        ValueError: If URL protocol is not HTTP/HTTPS.
    """
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Only HTTP/HTTPS URLs are supported. Got: {parsed.scheme}://")


def is_compressed_url(url: str) -> bool:
    """Return True if URL path looks like a gzip or zip file."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    return path.endswith(".gz") or path.endswith(".zip")


def is_gzip_path(file_path: Path) -> bool:
    """Return True if path looks like a gzip-compressed file."""
    return file_path.suffix.lower() == ".gz"


def is_zip_path(file_path: Path) -> bool:
    """Return True if path looks like a zip archive."""
    return file_path.suffix.lower() == ".zip"


def resolve_zip_csv_entry(zip_path: Path) -> str:
    """Return the single CSV entry inside a zip archive.

    Raises:
        ValueError: If zero or multiple CSV entries are found.
    """
    with zipfile.ZipFile(zip_path) as archive:
        csv_entries = [
            info.filename
            for info in archive.infolist()
            if not info.is_dir() and info.filename.lower().endswith(".csv")
        ]

    if not csv_entries:
        raise ValueError("Zip archive contains no CSV files.")

    if len(csv_entries) > 1:
        raise ValueError(
            "The file contains more than one file. Extract the one you need and use "
            "csvnorm on that file."
        )

    return csv_entries[0]


def build_zip_path(zip_path: Path, csv_entry: str) -> str:
    """Build a DuckDB zipfs path for the given CSV entry."""
    entry = csv_entry.lstrip("/")
    return f"zip://{zip_path.resolve().as_posix()}/{entry}"


def extract_filename_from_url(url: str) -> str:
    """Extract and normalize filename from URL.

    Args:
        url: URL to extract filename from.

    Returns:
        Normalized snake_case filename without extension.
    """
    from urllib.parse import unquote

    parsed = urlparse(url)
    # Get last path segment, ignore query/fragment
    path = parsed.path.rstrip("/")
    filename = path.split("/")[-1] if path else "data"

    # Decode URL encoding (%20 -> space, etc.)
    filename = unquote(filename)

    # Remove extension if present
    if filename.lower().endswith(".csv"):
        filename = filename[:-4]

    # Apply snake_case normalization
    return to_snake_case(filename) if filename else "data"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format.

    Args:
        size_bytes: File size in bytes.

    Returns:
        Formatted size string (e.g., "1.5 MB", "256 KB").
    """
    size = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024.0:
            return f"{size:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
        size /= 1024.0
    return f"{size:.1f} TB"


def _is_ssl_handshake_error(error: urllib.error.URLError) -> bool:
    """Check if a URLError is caused by an SSL/TLS handshake failure."""
    reason = getattr(error, "reason", None)
    if isinstance(reason, ssl.SSLError):
        return True
    message = str(reason) if reason is not None else str(error)
    message = message.lower()
    return "handshake" in message and "ssl" in message


def _download_with_requests(url: str, output_path: Path, timeout: int) -> Path:
    """Download a URL using requests as a compatibility fallback."""
    response = requests.get(url, stream=True, timeout=timeout)
    response.raise_for_status()
    with open(output_path, "wb") as output_file:
        for chunk in response.iter_content(chunk_size=1024 * 64):
            if chunk:
                output_file.write(chunk)
    return output_path


def _download_with_curl(url: str, output_path: Path, timeout: int) -> Path:
    """Download a URL using curl when Python TLS fails."""
    curl_path = shutil.which("curl")
    if not curl_path:
        raise FileNotFoundError("curl not found for TLS fallback")
    subprocess.run(
        [curl_path, "-L", "--fail", "--max-time", str(timeout), "-o", str(output_path), url],
        check=True,
    )
    return output_path


def download_url_to_file(url: str, output_path: Path, timeout: int = 30) -> Path:
    """Download a URL to a local file path.

    Args:
        url: Remote HTTP/HTTPS URL.
        output_path: Destination file path.
        timeout: Timeout in seconds.

    Returns:
        Path to the downloaded file.
    """
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            with open(output_path, "wb") as output_file:
                shutil.copyfileobj(response, output_file)
        return output_path
    except urllib.error.URLError as error:
        if _is_ssl_handshake_error(error):
            try:
                return _download_with_requests(url, output_path, timeout)
            except requests.exceptions.SSLError:
                return _download_with_curl(url, output_path, timeout)
        raise


def supports_http_range(url: str, timeout: int = 10) -> bool:
    """Check whether a URL supports HTTP range requests.

    Args:
        url: Remote HTTP/HTTPS URL.
        timeout: Timeout in seconds.

    Returns:
        True if the server supports byte ranges, False otherwise.
    """
    request = urllib.request.Request(url, headers={"Range": "bytes=0-0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            # Prefer explicit partial content or headers signaling range support.
            if response.status == 206:
                return True
            accept_ranges = response.headers.get("Accept-Ranges", "")
            content_range = response.headers.get("Content-Range", "")
            return "bytes" in accept_ranges.lower() or bool(content_range)
    except (OSError, urllib.error.URLError):
        return False


def get_row_count(file_path: Union[Path, str]) -> int:
    """Count number of rows in a CSV file.

    Args:
        file_path: Path to CSV file.

    Returns:
        Number of data rows (excluding header), or 0 if file doesn't exist.
    """
    if not isinstance(file_path, Path) or not file_path.exists():
        return 0

    try:
        with open(file_path, "r") as f:
            # Skip header
            next(f, None)
            return sum(1 for _ in f)
    except (OSError, UnicodeDecodeError):
        return 0


def get_column_count(file_path: Union[Path, str], delimiter: str = ",") -> int:
    """Count number of columns in a CSV file using DuckDB.

    Args:
        file_path: Path to CSV file.
        delimiter: Field delimiter used in the CSV file.

    Returns:
        Number of columns in the CSV, or 0 if file doesn't exist or error.
    """
    if not isinstance(file_path, Path) or not file_path.exists():
        return 0

    try:
        conn = duckdb.connect(":memory:")
        # Get column names from CSV using DuckDB DESCRIBE
        columns = conn.execute(
            "DESCRIBE SELECT * FROM read_csv("
            f"'{file_path}', delim='{delimiter}', header=true, sample_size=1)"
        ).fetchall()
        conn.close()

        return len(columns)
    except (duckdb.Error, OSError):
        return 0
