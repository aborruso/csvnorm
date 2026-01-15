"""Core processing logic for CSV normalizer."""

import logging
import sys
from pathlib import Path

from csv_normalizer.encoding import convert_to_utf8, detect_encoding, needs_conversion
from csv_normalizer.utils import ensure_output_dir, to_snake_case, validate_delimiter
from csv_normalizer.validation import normalize_csv, validate_csv

logger = logging.getLogger("csv_normalizer")


def process_csv(
    input_file: Path,
    output_dir: Path,
    force: bool = False,
    keep_names: bool = False,
    delimiter: str = ",",
    verbose: bool = False,
) -> int:
    """Main CSV processing pipeline.

    Args:
        input_file: Path to input CSV file.
        output_dir: Directory for output files.
        force: If True, overwrite existing output files.
        keep_names: If True, keep original column names.
        delimiter: Output field delimiter.
        verbose: If True, enable debug logging.

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    # Validate inputs
    if not input_file.exists():
        print(f"Error: input file not found: {input_file}", file=sys.stderr)
        return 1

    if not input_file.is_file():
        print(f"Error: not a file: {input_file}", file=sys.stderr)
        return 1

    try:
        validate_delimiter(delimiter)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Setup paths
    base_name = to_snake_case(input_file.name)
    ensure_output_dir(output_dir)

    output_file = output_dir / f"{base_name}.csv"
    reject_file = output_dir / f"{base_name}_reject_errors.csv"
    temp_utf8_file = output_dir / f"{base_name}_utf8.csv"

    # Check if output exists
    if output_file.exists() and not force:
        print("Warning: Output file already exists:", file=sys.stderr)
        print(f"  - {output_file}", file=sys.stderr)
        print("Use --force to overwrite.", file=sys.stderr)
        return 1

    # Clean up previous reject file
    if reject_file.exists():
        reject_file.unlink()

    # Track files to clean up
    temp_files: list[Path] = []

    try:
        # Step 1: Detect encoding
        try:
            encoding = detect_encoding(input_file)
        except ValueError as e:
            print(f"Error: {e}", file=sys.stderr)
            return 1

        logger.debug(f"Detected encoding: {encoding}")

        # Step 2: Convert to UTF-8 if needed
        working_file = input_file
        if needs_conversion(encoding):
            print(f"Converting file from {encoding} to UTF-8...")
            try:
                convert_to_utf8(input_file, temp_utf8_file, encoding)
                working_file = temp_utf8_file
                temp_files.append(temp_utf8_file)
            except (UnicodeDecodeError, LookupError) as e:
                print(f"Error converting encoding: {e}", file=sys.stderr)
                return 1

        # Step 3: Validate CSV
        logger.debug("Validating CSV with DuckDB...")
        is_valid = validate_csv(working_file, reject_file)

        if not is_valid:
            print("Error: DuckDB encountered invalid rows while processing the CSV file.")
            print(f"Details of the errors can be found in: {reject_file}")
            print("Please fix the issues and try again.")
            return 1

        # Step 4: Normalize and write output
        logger.debug("Normalizing CSV...")
        normalize_csv(
            input_path=working_file,
            output_path=output_file,
            delimiter=delimiter,
            normalize_names=not keep_names,
        )

        logger.debug(f"Output written to: {output_file}")

    finally:
        # Cleanup temp files
        for temp_file in temp_files:
            if temp_file.exists():
                logger.debug(f"Removing temp file: {temp_file}")
                temp_file.unlink()

        # Remove reject file if empty (only header)
        if reject_file.exists():
            with open(reject_file, "r") as f:
                line_count = sum(1 for _ in f)
            if line_count <= 1:
                logger.debug(f"Removing empty reject file: {reject_file}")
                reject_file.unlink()

    return 0
