"""CSV validation and normalization using DuckDB."""

import logging
import re
from pathlib import Path
from typing import Optional, Union

import duckdb

logger = logging.getLogger("csvnorm")

ConfigDict = dict[str, Union[str, int]]

# Fallback configurations to try when automatic dialect detection fails
FALLBACK_CONFIGS: list[ConfigDict] = [
    {"delim": ";", "skip": 1},
    {"delim": ";", "skip": 2},
    {"delim": "|", "skip": 1},
    {"delim": "|", "skip": 2},
    {"delim": "\t", "skip": 1},
    {"delim": "\t", "skip": 2},
]

# Common delimiters to check
COMMON_DELIMITERS: list[str] = [",", ";", "|", "\t"]


def _needs_zipfs(file_path: Union[Path, str]) -> bool:
    """Return True if the input uses DuckDB zipfs paths."""
    return isinstance(file_path, str) and file_path.startswith("zip://")


def _compression_option(file_path: Union[Path, str]) -> str:
    """Return DuckDB compression option for gzip inputs."""
    name = file_path.name if isinstance(file_path, Path) else file_path
    if name.lower().endswith(".gz"):
        return "compression='auto'"
    return ""


def _ensure_zipfs_extension(
    conn: duckdb.DuckDBPyConnection, file_path: Union[Path, str]
) -> None:
    """Install/load DuckDB zipfs extension when needed."""
    if not _needs_zipfs(file_path):
        return

    try:
        conn.execute("LOAD zipfs")
    except duckdb.Error:
        # Prefer community repo for zipfs if default repo doesn't have it.
        try:
            conn.execute("INSTALL zipfs FROM community")
        except duckdb.Error:
            conn.execute("INSTALL zipfs")
        conn.execute("LOAD zipfs")


def validate_csv(
    file_path: Union[Path, str],
    reject_file: Path,
    is_remote: bool = False,
    skip_rows: int = 0,
) -> tuple[int, list[str], Optional[ConfigDict]]:
    """Validate CSV file using DuckDB and export rejected rows.

    Args:
        file_path: Path to CSV file to validate or URL string.
        reject_file: Path to write rejected rows.
        is_remote: True if file_path is a remote URL.
        skip_rows: Number of rows to skip at the beginning of the file (user-provided).

    Returns:
        Tuple of (reject_count, error_types, fallback_config) where:
        - reject_count: number of lines in reject file
        - error_types: list of up to 3 unique error reasons
        - fallback_config: dict with 'delim' and 'skip' if fallback was used, None otherwise
    """
    logger.debug(f"Validating CSV: {file_path}")

    conn = duckdb.connect()
    fallback_config: Optional[ConfigDict] = None

    _ensure_zipfs_extension(conn, file_path)
    compression_opt = _compression_option(file_path)

    # Pre-check for header anomalies (local files only)
    # Skip early detection if user provided skip_rows
    suggested_config: Optional[ConfigDict] = None
    if skip_rows == 0 and not is_remote and isinstance(file_path, Path):
        suggested_config = _detect_header_anomaly(file_path)
        if suggested_config:
            logger.info(f"Early detection suggests config: {suggested_config}")

    try:
        # Set HTTP timeout for remote URLs (30 seconds)
        if is_remote:
            conn.execute("SET http_timeout=30000")

        # If early detection found anomaly, try that config first
        if suggested_config:
            logger.debug("Trying early-detected config before standard sniffing...")
            try:
                delim = suggested_config["delim"]
                skip = suggested_config["skip"]
                # Use COUNT(*) instead of COPY TO /dev/null to avoid locking issues
                read_opts = (
                    f"delim='{delim}', skip={skip}, store_rejects=true, "
                    "ignore_errors=true, sample_size=-1, all_varchar=true"
                )
                if compression_opt:
                    read_opts += f", {compression_opt}"
                conn.execute(f"""
                    SELECT COUNT(*) FROM read_csv(
                        '{file_path}',
                        {read_opts}
                    )
                """).fetchall()
                fallback_config = suggested_config
                logger.info("Early-detected config succeeded")
            except duckdb.Error as e:
                logger.debug(f"Early-detected config failed: {e}, trying standard sniffing")
                suggested_config = None  # Fall through to standard sniffing

        # Try standard automatic detection if early detection didn't work
        if not suggested_config:
            try:
                # Read CSV with store_rejects to capture malformed rows
                # Use all_varchar=true to avoid type inference failures
                # Add user-provided skip_rows if specified
                read_opts = "store_rejects=true, sample_size=-1, all_varchar=true"
                if compression_opt:
                    read_opts += f", {compression_opt}"
                if skip_rows > 0:
                    read_opts += f", skip={skip_rows}"
                    # Track that we used user-provided skip
                    fallback_config = {"delim": ",", "skip": skip_rows}

                # Use COUNT(*) instead of COPY TO /dev/null to avoid locking issues
                conn.execute(f"""
                    SELECT COUNT(*) FROM read_csv(
                        '{file_path}',
                        {read_opts}
                    )
                """).fetchall()
                logger.debug("Standard CSV sniffing succeeded")

            except duckdb.Error as e:
                error_msg = str(e)
                # Check if it's a dialect detection failure
                if "sniffing" in error_msg.lower() or "detect" in error_msg.lower():
                    logger.debug("Standard sniffing failed, trying fallback configurations...")

                    # Create fallback configs based on user-provided skip_rows
                    # If skip_rows > 0, use it; otherwise use predefined FALLBACK_CONFIGS
                    if skip_rows > 0:
                        # User provided skip_rows, try different delimiters with user's skip
                        fallback_configs: list[ConfigDict] = [
                            {"delim": delim, "skip": skip_rows}
                            for delim in COMMON_DELIMITERS
                        ]
                    else:
                        # Use predefined fallback configs
                        fallback_configs = FALLBACK_CONFIGS

                    # Try each fallback configuration
                    success = False
                    for config in fallback_configs:
                        logger.debug(f"Trying config: {config}")
                        if _try_read_csv_with_config(conn, file_path, config):
                            logger.info(f"Fallback succeeded with config: {config}")
                            fallback_config = config
                            success = True

                            # Now do the actual validation with this config
                            # Use both store_rejects and ignore_errors to handle malformed rows
                            delim = config["delim"]
                            skip = config["skip"]
                            # Use COUNT(*) instead of COPY TO /dev/null to avoid locking issues
                            read_opts = (
                                f"delim='{delim}', skip={skip}, store_rejects=true, "
                                "ignore_errors=true, sample_size=-1, all_varchar=true"
                            )
                            if compression_opt:
                                read_opts += f", {compression_opt}"
                            conn.execute(f"""
                                SELECT COUNT(*) FROM read_csv(
                                    '{file_path}',
                                    {read_opts}
                                )
                            """).fetchall()
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
    skip_rows: int = 0,
    fallback_config: Optional[ConfigDict] = None,
    reject_file: Optional[Path] = None,
) -> Optional[ConfigDict]:
    """Normalize CSV file using DuckDB.

    Args:
        input_path: Path to input CSV file or URL string.
        output_path: Path for normalized output file.
        delimiter: Output field delimiter.
        normalize_names: If True, convert column names to snake_case.
        is_remote: True if input_path is a remote URL.
        skip_rows: Number of rows to skip at the beginning of the file (user-provided).
        fallback_config: Optional fallback configuration from validate_csv.
        reject_file: Optional path to write rejected rows (for fallback mode).

    Returns:
        Fallback config used if different from input, None otherwise.
    """
    logger.debug(f"Normalizing CSV: {input_path} -> {output_path}")

    conn = duckdb.connect()
    used_fallback_config: Optional[ConfigDict] = None

    _ensure_zipfs_extension(conn, input_path)
    compression_opt = _compression_option(input_path)

    try:
        # Set HTTP timeout for remote URLs (30 seconds)
        if is_remote:
            conn.execute("SET http_timeout=30000")

        # Build read options
        read_opts = "sample_size=-1, all_varchar=true"
        if compression_opt:
            read_opts += f", {compression_opt}"
        if normalize_names:
            read_opts += ", normalize_names=true"

        # Add user-provided skip_rows if specified (takes precedence over fallback)
        if skip_rows > 0:
            read_opts += f", skip={skip_rows}"
            logger.debug(f"Using user-provided skip_rows: {skip_rows}")
            # If validation discovered a non-comma delimiter via fallback_config,
            # preserve that delimiter while still honoring the user-provided skip_rows.
            if fallback_config:
                delim = fallback_config.get("delim")
                if delim and delim != ",":
                    read_opts += f", delim='{delim}'"
                    logger.debug(
                        "Using fallback delimiter with user-provided skip_rows: %s",
                        delim,
                    )
        # Add fallback config options if available and skip_rows not provided
        elif fallback_config:
            delim = fallback_config["delim"]
            skip = fallback_config["skip"]
            # Add ignore_errors when using fallback (may have malformed rows)
            read_opts += f", delim='{delim}', skip={skip}, ignore_errors=true"
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

        except duckdb.Error as e:
            error_msg = str(e)
            # If not already using fallback and it's a sniffing error, try fallback
            if (
                not fallback_config
                and skip_rows == 0
                and (
                    "sniffing" in error_msg.lower()
                    or "detect" in error_msg.lower()
                )
            ):
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
                        read_opts = (
                            "sample_size=-1, all_varchar=true"
                            f"{', ' + compression_opt if compression_opt else ''}, "
                            f"delim='{delim}', skip={skip}"
                        )

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

    DuckDB's normalize_names option prefixes SQL keywords with an underscore to
    avoid conflicts. This function removes those prefixes from the header row only.

    Args:
        file_path: Path to CSV file to fix.
    """
    with open(file_path, "r") as f:
        lines = f.readlines()

    if not lines:
        return

    header = lines[0]

    # Remove leading underscore on any column name (start of header or after comma).
    header = re.sub(r"(^|,)_([A-Za-z0-9]+)\b", r"\1\2", header)

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
    config: ConfigDict,
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
        _ensure_zipfs_extension(conn, file_path)
        delim = config["delim"]
        skip = config["skip"]

        read_opts = f"delim='{delim}', skip={skip}, sample_size=-1, ignore_errors=true"
        compression_opt = _compression_option(file_path)
        if compression_opt:
            read_opts += f", {compression_opt}"
        if all_varchar:
            read_opts += ", all_varchar=true"

        # Try to read and verify it has multiple columns
        # Use ignore_errors to handle potential malformed rows during testing
        result = conn.execute(
            f"SELECT * FROM read_csv('{file_path}', {read_opts}) LIMIT 1"
        ).fetchall()

        # Check we got at least one row with multiple columns
        if result and len(result) > 0:
            row = result[0]
            # Require at least 2 columns to consider it valid
            if len(row) >= 2:
                return True

        return False
    except (duckdb.Error, OSError):
        return False


def _detect_header_anomaly(
    file_path: Path, num_lines: int = 5
) -> Optional[ConfigDict]:
    """Detect if first line has anomalous separator pattern.

    Analyzes the first N lines to detect if line 1 has a significantly
    different separator pattern compared to lines 2-N. This helps catch
    files with title rows that DuckDB's sampling might miss.

    Args:
        file_path: Path to CSV file.
        num_lines: Number of lines to analyze (default: 5).

    Returns:
        Suggested config dict with 'delim' and 'skip' if anomaly detected,
        None otherwise.
    """
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline().rstrip("\n") for _ in range(num_lines)]

        # Filter out empty lines
        lines = [line for line in lines if line.strip()]
        if len(lines) < 3:
            # Not enough lines to detect pattern
            return None

        # Count each delimiter type per line
        separator_counts = []
        for line in lines:
            counts = {}
            for delim in COMMON_DELIMITERS:
                counts[delim] = line.count(delim)
            separator_counts.append(counts)

        # Analyze lines 2-N to find dominant delimiter pattern
        if len(separator_counts) < 2:
            return None

        data_lines = separator_counts[1:]  # Skip first line for analysis

        # Find the most common delimiter in data lines
        delimiter_totals = {delim: 0 for delim in COMMON_DELIMITERS}
        for counts in data_lines:
            for delim, count in counts.items():
                delimiter_totals[delim] += count

        # Get dominant delimiter (most occurrences in data lines)
        dominant_delim = max(delimiter_totals.items(), key=lambda x: x[1])[0]
        dominant_count = delimiter_totals[dominant_delim]

        # Skip if no clear delimiter in data lines
        if dominant_count == 0:
            return None

        # Check if dominant delimiter is consistent across data lines
        data_counts = [counts[dominant_delim] for counts in data_lines]
        if not data_counts:
            return None

        # Average count in data lines
        avg_data_count = sum(data_counts) / len(data_counts)

        # Check first line
        first_line_count = separator_counts[0][dominant_delim]

        # Anomaly if first line has significantly fewer delimiters
        # Threshold: less than 50% of average in data lines
        if avg_data_count > 0 and first_line_count < (avg_data_count * 0.5):
            logger.info(
                f"Header anomaly detected: line 1 has {first_line_count} '{dominant_delim}', "
                f"data lines average {avg_data_count:.1f}"
            )
            return {"delim": dominant_delim, "skip": 1}

        return None

    except OSError as e:
        logger.debug(f"Header anomaly detection failed: {e}")
        return None


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
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Failed to extract error types: {e}")
        return []

    return list(error_types)[:3]
