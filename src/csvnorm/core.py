"""Core processing logic for csvnorm."""

import logging
import tempfile
from pathlib import Path
from typing import Union

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from csvnorm.encoding import convert_to_utf8, detect_encoding, needs_conversion
from csvnorm.ui import (
    show_error_panel,
    show_success_table,
    show_validation_error_panel,
    show_warning_panel,
)
from csvnorm.utils import (
    extract_filename_from_url,
    get_column_count,
    get_row_count,
    is_url,
    to_snake_case,
    validate_delimiter,
    validate_url,
)
from csvnorm.validation import normalize_csv, validate_csv

logger = logging.getLogger("csvnorm")
console = Console()


def process_csv(
    input_file: str,
    output_file: Path,
    force: bool = False,
    keep_names: bool = False,
    delimiter: str = ",",
    verbose: bool = False,
) -> int:
    """Main CSV processing pipeline.

    Args:
        input_file: Path to input CSV file or HTTP/HTTPS URL.
        output_file: Full path for output file.
        force: If True, overwrite existing output files.
        keep_names: If True, keep original column names.
        delimiter: Output field delimiter.
        verbose: If True, enable debug logging.

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    # Detect if input is URL or file
    is_remote = is_url(input_file)

    input_path: Union[str, Path]
    if is_remote:
        # Validate URL
        try:
            validate_url(input_file)
        except ValueError as e:
            show_error_panel(str(e))
            return 1
        base_name = extract_filename_from_url(input_file)
        input_path = input_file  # Keep as string for DuckDB
    else:
        # Validate local file
        file_path = Path(input_file)
        if not file_path.exists():
            show_error_panel(f"Input file not found\n{file_path}")
            return 1

        if not file_path.is_file():
            show_error_panel(f"Not a file\n{file_path}")
            return 1

        base_name = to_snake_case(file_path.name)
        input_path = file_path

    try:
        validate_delimiter(delimiter)
    except ValueError as e:
        show_error_panel(str(e))
        return 1

    # Setup paths
    output_dir = output_file.parent
    temp_dir = Path(tempfile.mkdtemp(prefix="csvnorm_"))
    reject_file = output_dir / f"{output_file.stem}_reject_errors.csv"
    temp_utf8_file = temp_dir / f"{output_file.stem}_utf8.csv"

    # Check if output exists
    if output_file.exists() and not force:
        show_warning_panel(
            f"Output file already exists\n\n"
            f"{output_file}\n\n"
            f"Use [bold]--force[/bold] to overwrite."
        )
        return 1

    # Clean up previous reject file (always overwrite)
    if reject_file.exists():
        reject_file.unlink()

    # Track files to clean up
    temp_files: list[Path] = [temp_dir]

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Processing...", total=None)

            # For remote URLs, skip encoding detection/conversion
            if is_remote:
                progress.update(
                    task,
                    description="[green]✓[/green] Remote URL (encoding handled by DuckDB)",
                )
                working_file = input_path  # Keep URL as string
                encoding = "remote"
            else:
                # Step 1: Detect encoding (local files only)
                # input_path is Path here (set in else block above)
                file_input_path = input_path  # Type narrowing for mypy
                assert isinstance(file_input_path, Path)

                progress.update(task, description="[cyan]Detecting encoding...")
                try:
                    encoding = detect_encoding(file_input_path)
                except ValueError as e:
                    progress.stop()
                    show_error_panel(str(e))
                    return 1

                logger.debug(f"Detected encoding: {encoding}")
                progress.update(
                    task, description=f"[green]✓[/green] Detected encoding: {encoding}"
                )

                # Step 2: Convert to UTF-8 if needed
                working_file = file_input_path
                if needs_conversion(encoding):
                    progress.update(
                        task,
                        description=f"[cyan]Converting from {encoding} to UTF-8...",
                    )
                    try:
                        convert_to_utf8(file_input_path, temp_utf8_file, encoding)
                        working_file = temp_utf8_file
                        temp_files.append(temp_utf8_file)
                        progress.update(
                            task, description="[green]✓[/green] Converted to UTF-8"
                        )
                    except (UnicodeDecodeError, LookupError) as e:
                        progress.stop()
                        show_error_panel(f"Encoding conversion failed\n{e}")
                        return 1
                else:
                    if encoding == "ascii":
                        note = "ASCII is UTF-8 compatible; no conversion needed"
                    else:
                        note = "UTF-8; no conversion needed"
                    progress.update(
                        task,
                        description=f"[green]✓[/green] Encoding: {encoding} ({note})",
                    )

            # Step 3: Validate CSV
            progress.update(task, description="[cyan]Validating CSV...")
            logger.debug("Validating CSV with DuckDB...")

            try:
                reject_count, error_types = validate_csv(
                    working_file, reject_file, is_remote=is_remote
                )
            except Exception as e:
                progress.stop()
                error_msg = str(e)

                # Check for common HTTP errors
                if "HTTP Error" in error_msg or "HTTPException" in error_msg:
                    if "404" in error_msg:
                        show_error_panel(
                            f"Remote CSV file not found (HTTP 404)\n\n"
                            f"URL: [cyan]{input_file}[/cyan]\n\n"
                            "Please check the URL is correct."
                        )
                    elif "401" in error_msg or "403" in error_msg:
                        show_error_panel(
                            f"Authentication required (HTTP 401/403)\n\n"
                            f"URL: [cyan]{input_file}[/cyan]\n\n"
                            "This tool only supports public URLs without authentication.\n"
                            "Please download the file manually first."
                        )
                    elif (
                        "timeout" in error_msg.lower()
                        or "timed out" in error_msg.lower()
                    ):
                        show_error_panel(
                            f"HTTP request timeout (30 seconds)\n\n"
                            f"URL: [cyan]{input_file}[/cyan]\n\n"
                            "The remote server took too long to respond.\n"
                            "Try again later or download the file manually."
                        )
                    else:
                        show_error_panel(f"HTTP request failed\n\n{error_msg}")
                else:
                    # Re-raise non-HTTP errors
                    raise
                return 1

            has_validation_errors = reject_count > 1
            if has_validation_errors:
                progress.stop()

            progress.update(task, description="[green]✓[/green] CSV validated")

            # Step 4: Normalize and write output
            progress.update(task, description="[cyan]Normalizing and writing output...")
            logger.debug("Normalizing CSV...")
            normalize_csv(
                input_path=working_file,
                output_path=output_file,
                delimiter=delimiter,
                normalize_names=not keep_names,
                is_remote=is_remote,
            )

            logger.debug(f"Output written to: {output_file}")
            progress.update(task, description="[green]✓[/green] Complete")

        # Collect statistics
        input_size = (
            working_file.stat().st_size if isinstance(working_file, Path) else 0
        )
        output_size = output_file.stat().st_size
        row_count = get_row_count(output_file)
        column_count = get_column_count(output_file, delimiter)

        # Show success summary
        show_success_table(
            input_file=input_file,
            output_file=output_file,
            encoding=encoding,
            is_remote=is_remote,
            row_count=row_count,
            column_count=column_count,
            input_size=input_size,
            output_size=output_size,
            delimiter=delimiter,
            keep_names=keep_names,
        )

        # Show validation errors if any
        if has_validation_errors:
            show_validation_error_panel(reject_count, error_types, reject_file)
            return 1

    finally:
        # Cleanup temp directory
        import shutil

        for temp_path in temp_files:
            if temp_path.exists():
                logger.debug(f"Removing temp path: {temp_path}")
                if temp_path.is_dir():
                    shutil.rmtree(temp_path)
                else:
                    temp_path.unlink()

        # Remove reject file if empty (only header)
        if reject_file.exists():
            with open(reject_file, "r") as f:
                line_count = sum(1 for _ in f)
            if line_count <= 1:
                logger.debug(f"Removing empty reject file: {reject_file}")
                reject_file.unlink()

    return 0
