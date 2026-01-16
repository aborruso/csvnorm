"""Utility functions for csvnorm."""

import logging
import re
from pathlib import Path
from typing import Union
from urllib.parse import urlparse

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
    except Exception:
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
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"


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
    except Exception:
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
        import duckdb

        conn = duckdb.connect(":memory:")
        # Get column names from CSV using DuckDB DESCRIBE
        columns = conn.execute(
            f"DESCRIBE SELECT * FROM read_csv('{file_path}', delim='{delimiter}', header=true, sample_size=1)"
        ).fetchall()
        conn.close()

        return len(columns)
    except Exception:
        return 0
