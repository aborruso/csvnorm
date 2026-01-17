"""CSV validation and normalization using DuckDB."""

import logging
import re
from pathlib import Path
from typing import Optional, Union

import duckdb

logger = logging.getLogger("csvnorm")

# Fallback configurations to try when automatic dialect detection fails
FALLBACK_CONFIGS = [
    {"delim": ";", "skip": 1},
    {"delim": ";", "skip": 2},
    {"delim": "|", "skip": 1},
    {"delim": "|", "skip": 2},
    {"delim": "\t", "skip": 1},
    {"delim": "\t", "skip": 2},
]


def validate_csv(
    file_path: Union[Path, str], reject_file: Path, is_remote: bool = False
) -> tuple[int, list[str], Optional[dict[str, Union[str, int]]]]:
    """Validate CSV file using DuckDB and export rejected rows.

    Args:
        file_path: Path to CSV file to validate or URL string.
        reject_file: Path to write rejected rows.
        is_remote: True if file_path is a remote URL.

    Returns:
        Tuple of (reject_count, error_types, fallback_config) where:
        - reject_count: number of lines in reject file
        - error_types: list of up to 3 unique error reasons
        - fallback_config: dict with 'delim' and 'skip' if fallback was used, None otherwise
    """
    logger.debug(f"Validating CSV: {file_path}")

    conn = duckdb.connect()
    fallback_config = None

    try:
        # Set HTTP timeout for remote URLs (30 seconds)
        if is_remote:
            conn.execute("SET http_timeout=30000")

        # Try standard automatic detection first
        try:
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
            logger.debug("Standard CSV sniffing succeeded")

        except Exception as e:
            error_msg = str(e)
            # Check if it's a dialect detection failure
            if "sniffing" in error_msg.lower() or "detect" in error_msg.lower():
                logger.debug("Standard sniffing failed, trying fallback configurations...")

                # Try each fallback configuration
                success = False
                for config in FALLBACK_CONFIGS:
                    logger.debug(f"Trying config: {config}")
                    if _try_read_csv_with_config(conn, file_path, config):
                        logger.info(f"Fallback succeeded with config: {config}")
                        fallback_config = config
                        success = True

                        # Now do the actual validation with this config
                        # Use both store_rejects and ignore_errors to handle malformed rows
                        delim = config["delim"]
                        skip = config["skip"]
                        conn.execute(f"""
                            COPY (
                                FROM read_csv(
                                    '{file_path}',
                                    delim='{delim}',
                                    skip={skip},
                                    store_rejects=true,
                                    ignore_errors=true,
                                    sample_size=-1,
                                    all_varchar=true
                                )
                            ) TO '/dev/null'
                        """)
                        break

                if not success:
                    # No fallback worked, re-raise original error
                    raise
            else:
                # Not a sniffing error, re-raise
                raise

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

    return reject_count, error_types, fallback_config


def normalize_csv(
    input_path: Union[Path, str],
    output_path: Path,
    delimiter: str = ",",
    normalize_names: bool = True,
    is_remote: bool = False,
    fallback_config: Optional[dict[str, Union[str, int]]] = None,
    reject_file: Optional[Path] = None,
) -> Optional[dict[str, Union[str, int]]]:
    """Normalize CSV file using DuckDB.

    Args:
        input_path: Path to input CSV file or URL string.
        output_path: Path for normalized output file.
        delimiter: Output field delimiter.
        normalize_names: If True, convert column names to snake_case.
        is_remote: True if input_path is a remote URL.
        fallback_config: Optional fallback configuration from validate_csv.
        reject_file: Optional path to write rejected rows (for fallback mode).

    Returns:
        Fallback config used if different from input, None otherwise.
    """
    logger.debug(f"Normalizing CSV: {input_path} -> {output_path}")

    conn = duckdb.connect()
    used_fallback_config = None

    try:
        # Set HTTP timeout for remote URLs (30 seconds)
        if is_remote:
            conn.execute("SET http_timeout=30000")

        # Build read options
        read_opts = "sample_size=-1, all_varchar=true"
        if normalize_names:
            read_opts += ", normalize_names=true"

        # Add fallback config options if available
        if fallback_config:
            delim = fallback_config["delim"]
            skip = fallback_config["skip"]
            read_opts += f", delim='{delim}', skip={skip}"
            logger.debug(f"Using fallback config: {fallback_config}")

        # Build copy options
        copy_opts = "header true, format csv"
        if delimiter != ",":
            copy_opts += f", delimiter '{delimiter}'"

        # Try to normalize with current config
        try:
            query = f"""
                COPY (
                    SELECT * FROM read_csv('{input_path}', {read_opts})
                ) TO '{output_path}' ({copy_opts})
            """

            logger.debug(f"DuckDB query: {query}")
            conn.execute(query)

        except Exception as e:
            error_msg = str(e)
            # If not already using fallback and it's a sniffing error, try fallback
            if not fallback_config and ("sniffing" in error_msg.lower() or "detect" in error_msg.lower()):
                logger.debug("Normalization sniffing failed, trying fallback configurations...")

                success = False
                for config in FALLBACK_CONFIGS:
                    logger.debug(f"Trying config: {config}")
                    if _try_read_csv_with_config(conn, input_path, config, all_varchar=True):
                        logger.info(f"Fallback succeeded with config: {config}")

                        # Rebuild read options with fallback config
                        # Use both store_rejects and ignore_errors for malformed rows
                        delim = config["delim"]
                        skip = config["skip"]
                        read_opts = f"sample_size=-1, all_varchar=true, delim='{delim}', skip={skip}"

                        # Add store_rejects and ignore_errors if reject_file provided
                        if reject_file:
                            read_opts += ", store_rejects=true, ignore_errors=true"
                        else:
                            # Without reject_file, just use ignore_errors
                            read_opts += ", ignore_errors=true"

                        if normalize_names:
                            read_opts += ", normalize_names=true"

                        query = f"""
                            COPY (
                                SELECT * FROM read_csv('{input_path}', {read_opts})
                            ) TO '{output_path}' ({copy_opts})
                        """

                        logger.debug(f"DuckDB query with fallback: {query}")
                        conn.execute(query)

                        # Export reject_errors if using store_rejects
                        if reject_file:
                            conn.execute(f"COPY (FROM reject_errors) TO '{reject_file}'")
                            logger.debug(f"Reject errors exported to: {reject_file}")

                        used_fallback_config = config
                        success = True
                        break

                if not success:
                    raise
            else:
                raise

    finally:
        conn.close()

    if normalize_names:
        _fix_duckdb_keyword_prefix(output_path)

    logger.debug(f"Normalized file written to: {output_path}")

    return used_fallback_config


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


def _try_read_csv_with_config(
    conn: duckdb.DuckDBPyConnection,
    file_path: Union[Path, str],
    config: dict[str, Union[str, int]],
    all_varchar: bool = True,
) -> bool:
    """Try to read CSV with specific configuration.

    Args:
        conn: DuckDB connection.
        file_path: Path to CSV file or URL string.
        config: Configuration dict with 'delim' and 'skip' keys.
        all_varchar: If True, read all columns as varchar.

    Returns:
        True if configuration works and has multiple columns, False otherwise.
    """
    try:
        delim = config["delim"]
        skip = config["skip"]

        read_opts = f"delim='{delim}', skip={skip}, sample_size=-1, ignore_errors=true"
        if all_varchar:
            read_opts += ", all_varchar=true"

        # Try to read and verify it has multiple columns
        # Use ignore_errors to handle potential malformed rows during testing
        result = conn.execute(f"SELECT * FROM read_csv('{file_path}', {read_opts}) LIMIT 1").fetchall()

        # Check we got at least one row with multiple columns
        if result and len(result) > 0:
            row = result[0]
            # Require at least 2 columns to consider it valid
            if len(row) >= 2:
                return True

        return False
    except Exception:
        return False


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
