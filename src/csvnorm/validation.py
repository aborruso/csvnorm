"""CSV validation and normalization using DuckDB."""

import logging
import re
from pathlib import Path
from typing import Union

import duckdb

logger = logging.getLogger("csvnorm")


def validate_csv(
    file_path: Union[Path, str], reject_file: Path, is_remote: bool = False
) -> tuple[int, list[str]]:
    """Validate CSV file using DuckDB and export rejected rows.

    Args:
        file_path: Path to CSV file to validate or URL string.
        reject_file: Path to write rejected rows.
        is_remote: True if file_path is a remote URL.

    Returns:
        Tuple of (reject_count, error_types) where error_types is list of
        up to 3 unique error reasons from reject file.
    """
    logger.debug(f"Validating CSV: {file_path}")

    conn = duckdb.connect()

    try:
        # Set HTTP timeout for remote URLs (30 seconds)
        if is_remote:
            conn.execute("SET http_timeout=30000")

        # Read CSV with store_rejects to capture malformed rows
        # Use all_varchar=true to avoid type inference failures
        conn.execute(f"""
            COPY (
                FROM read_csv(
                    '{file_path}',
                    store_rejects=true,
                    sample_size=-1,
                    all_varchar=true
                )
            ) TO '/dev/null'
        """)

        # Export rejected rows to file
        conn.execute(f"COPY (FROM reject_errors) TO '{reject_file}'")

    finally:
        conn.close()

    # Check if there are rejected rows (more than just header)
    reject_count = _count_lines(reject_file)
    logger.debug(f"Reject file lines: {reject_count}")

    # Collect sample error types from reject file
    error_types = []
    if reject_count > 1:
        error_types = _get_error_types(reject_file)

    return reject_count, error_types


def normalize_csv(
    input_path: Union[Path, str],
    output_path: Path,
    delimiter: str = ",",
    normalize_names: bool = True,
    is_remote: bool = False,
) -> None:
    """Normalize CSV file using DuckDB.

    Args:
        input_path: Path to input CSV file or URL string.
        output_path: Path for normalized output file.
        delimiter: Output field delimiter.
        normalize_names: If True, convert column names to snake_case.
        is_remote: True if input_path is a remote URL.
    """
    logger.debug(f"Normalizing CSV: {input_path} -> {output_path}")

    conn = duckdb.connect()

    try:
        # Set HTTP timeout for remote URLs (30 seconds)
        if is_remote:
            conn.execute("SET http_timeout=30000")

        # Build read options
        read_opts = "sample_size=-1, all_varchar=true"
        if normalize_names:
            read_opts += ", normalize_names=true"

        # Build copy options
        copy_opts = "header true, format csv"
        if delimiter != ",":
            copy_opts += f", delimiter '{delimiter}'"

        query = f"""
            COPY (
                SELECT * FROM read_csv('{input_path}', {read_opts})
            ) TO '{output_path}' ({copy_opts})
        """

        logger.debug(f"DuckDB query: {query}")
        conn.execute(query)

    finally:
        conn.close()

    if normalize_names:
        _fix_duckdb_keyword_prefix(output_path)

    logger.debug(f"Normalized file written to: {output_path}")


def _fix_duckdb_keyword_prefix(file_path: Path) -> None:
    """Remove underscore prefix from DuckDB-prefixed SQL keywords in header.

    DuckDB's normalize_names option prefixes SQL keywords like 'value' and 'location'
    with an underscore to avoid conflicts. This function removes those prefixes
    from the header row only.

    Args:
        file_path: Path to CSV file to fix.
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    if not lines:
        return

    header = lines[0]

    header = re.sub(r",_value\b", ",value", header)
    header = re.sub(r"^_value\b", "value", header)
    header = re.sub(r",_location\b", ",location", header)
    header = re.sub(r"^_location\b", "location", header)

    lines[0] = header

    with open(file_path, "w") as f:
        f.writelines(lines)


def _count_lines(file_path: Path) -> int:
    """Count lines in a file.

    Args:
        file_path: Path to file.

    Returns:
        Number of lines in file, or 0 if file doesn't exist.
    """
    if not file_path.exists():
        return 0

    with open(file_path, "r") as f:
        return sum(1 for _ in f)


def _get_error_types(reject_file: Path) -> list[str]:
    """Extract sample error types from reject file.

    Args:
        reject_file: Path to reject_errors.csv file.

    Returns:
        List of up to 3 unique error reasons.
    """
    if not reject_file.exists():
        return []

    error_types: set[str] = set()
    try:
        with open(reject_file, "r") as f:
            # Skip header
            next(f, None)
            for line in f:
                # Error message is in the last column
                parts = line.rstrip("\n").split(",")
                if parts:
                    error_reason = parts[-1].strip()
                    if error_reason and error_reason != "error":
                        error_types.add(error_reason)
                        if len(error_types) >= 3:
                            break
    except Exception as e:
        logger.warning(f"Failed to extract error types: {e}")
        return []

    return list(error_types)[:3]
