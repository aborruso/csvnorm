"""Core processing logic for csvnorm."""

import logging
import sys
import tempfile
from pathlib import Path
from typing import Optional, Union

from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from csvnorm.encoding import convert_to_utf8, detect_encoding, needs_conversion
from csvnorm.mojibake import repair_file
from csvnorm.ui import (
    show_error_panel,
    show_success_table,
    show_validation_error_panel,
    show_warning_panel,
)
from csvnorm.utils import (
    download_url_to_file,
    get_column_count,
    get_row_count,
    is_url,
    validate_delimiter,
    validate_url,
)
from csvnorm.validation import normalize_csv, validate_csv

logger = logging.getLogger("csvnorm")
console = Console()


def process_csv(
    input_file: str,
    output_file: Optional[Path],
    force: bool = False,
    keep_names: bool = False,
    delimiter: str = ",",
    skip_rows: int = 0,
    verbose: bool = False,
    fix_mojibake_sample: Optional[int] = None,
) -> int:
    """Main CSV processing pipeline.

    Args:
        input_file: Path to input CSV file or HTTP/HTTPS URL.
        output_file: Full path for output file, or None for stdout.
        force: If True, overwrite existing output files (only when output_file is specified).
        keep_names: If True, keep original column names.
        delimiter: Output field delimiter.
        skip_rows: Number of rows to skip at the beginning of the file.
        verbose: If True, enable debug logging.
        fix_mojibake_sample: Sample size for mojibake detection, None to disable.

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    # Determine if output mode is stdout or file
    use_stdout = output_file is None

    if fix_mojibake_sample is not None and fix_mojibake_sample < 0:
        show_error_panel("--fix-mojibake must be non-negative (use 0 to force repair)")
        return 1

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

        input_path = file_path

        # Prevent input file overwrite (never allow, even with --force)
        if output_file is not None:
            input_absolute = file_path.resolve()
            output_absolute = output_file.resolve()
            if input_absolute == output_absolute:
                show_error_panel(
                    "Cannot overwrite input file\n\n"
                    f"Input:  {input_file}\n"
                    f"Output: {output_file}\n\n"
                    "Use -o to specify a different output path."
                )
                return 1

    try:
        validate_delimiter(delimiter)
    except ValueError as e:
        show_error_panel(str(e))
        return 1

    # Setup paths
    temp_dir = Path(tempfile.mkdtemp(prefix="csvnorm_"))

    if use_stdout:
        # For stdout mode: create temp files
        actual_output_file = temp_dir / "output.csv"
        reject_file = temp_dir / "reject_errors.csv"
        temp_utf8_file = temp_dir / "utf8.csv"
    else:
        # For file mode: use specified output path
        assert output_file is not None  # Type narrowing
        output_dir = output_file.parent
        actual_output_file = output_file
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

    # If mojibake repair is enabled for a remote URL, download first
    if is_remote and fix_mojibake_sample is not None:
        try:
            download_path = temp_dir / "remote_download.csv"
            download_url_to_file(input_file, download_path)
        except Exception as e:
            show_error_panel(f"Failed to download remote file\n{e}")
            return 1
        input_path = download_path
        temp_files.append(download_path)
        is_remote = False

    # Use stderr console for progress when writing to stdout
    progress_console = Console(stderr=True) if use_stdout else console

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=progress_console,
            transient=True,
        ) as progress:
            task = progress.add_task("[cyan]Processing...", total=None)
            mojibake_repaired = False

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

                # Step 2b: Optional mojibake repair (local files only)
                if fix_mojibake_sample is not None:
                    sample_size = fix_mojibake_sample
                    progress.update(task, description="[cyan]Checking mojibake...")
                    try:
                        repaired_path = temp_dir / "mojibake_fixed.csv"
                        mojibake_repaired, working_file = repair_file(
                            working_file, repaired_path, sample_size
                        )
                        if mojibake_repaired:
                            temp_files.append(repaired_path)
                            progress.update(
                                task,
                                description="[green]✓[/green] Mojibake repaired (ftfy)",
                            )
                        else:
                            progress.update(
                                task,
                                description="[green]✓[/green] Mojibake check: clean",
                            )
                    except Exception as e:
                        progress.stop()
                        show_error_panel(f"Mojibake repair failed\n{e}")
                        return 1
                else:
                    mojibake_repaired = False

            # Step 3: Validate CSV
            progress.update(task, description="[cyan]Validating CSV...")
            logger.debug("Validating CSV with DuckDB...")

            try:
                reject_count, error_types, fallback_config = validate_csv(
                    working_file, reject_file, is_remote=is_remote, skip_rows=skip_rows
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
            used_fallback = normalize_csv(
                input_path=working_file,
                output_path=actual_output_file,
                delimiter=delimiter,
                normalize_names=not keep_names,
                is_remote=is_remote,
                skip_rows=skip_rows,
                fallback_config=fallback_config,
                reject_file=reject_file,
            )

            # If normalize used a different fallback config, update reject_count
            if used_fallback and used_fallback != fallback_config:
                # Normalize used fallback and exported reject_errors
                # Recount reject file lines
                reject_count = sum(1 for _ in open(reject_file)) if reject_file.exists() else 0
                has_validation_errors = reject_count > 1
                if has_validation_errors:
                    # Re-extract error types
                    from csvnorm.validation import _get_error_types
                    error_types = _get_error_types(reject_file)

            logger.debug(f"Output written to: {actual_output_file}")
            progress.update(task, description="[green]✓[/green] Complete")

        # Handle output based on mode
        if use_stdout:
            # Write to stdout
            with open(actual_output_file, "r") as f:
                sys.stdout.write(f.read())

            # Show validation errors on stderr if any
            if has_validation_errors:
                stderr_console = Console(stderr=True)
                stderr_console.print()
                stderr_console.print(
                    f"[yellow]Warning:[/yellow] {reject_count - 1} rows rejected during validation",
                    style="yellow",
                )
                stderr_console.print(
                    f"Reject file saved to: {reject_file}", style="dim"
                )
                stderr_console.print()
                return 1
        else:
            # File mode: show success table
            input_size = (
                working_file.stat().st_size if isinstance(working_file, Path) else 0
            )
            output_size = actual_output_file.stat().st_size
            row_count = get_row_count(actual_output_file)
            column_count = get_column_count(actual_output_file, delimiter)

            # Show success summary
            show_success_table(
                input_file=input_file,
                output_file=actual_output_file,
                encoding=encoding,
                is_remote=is_remote,
                mojibake_repaired=mojibake_repaired,
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

        # In stdout mode, preserve reject file if it has errors
        # In file mode, keep reject file in output directory
        if use_stdout and reject_file.exists():
            # Check if reject file has actual errors (more than just header)
            with open(reject_file, "r") as f:
                line_count = sum(1 for _ in f)
            if line_count <= 1:
                # Empty reject file, remove it
                reject_file.unlink()
            # If has errors, it's already been mentioned in stderr output above

        for temp_path in temp_files:
            if temp_path.exists():
                logger.debug(f"Removing temp path: {temp_path}")
                if temp_path.is_dir():
                    # Skip temp_dir removal if reject file is inside and should be preserved
                    if use_stdout and reject_file.exists() and reject_file.parent == temp_path:
                        # Remove everything except reject_file
                        for item in temp_path.iterdir():
                            if item != reject_file:
                                if item.is_dir():
                                    shutil.rmtree(item)
                                else:
                                    item.unlink()
                    else:
                        shutil.rmtree(temp_path)
                else:
                    temp_path.unlink()

        # Remove reject file if empty (only header) in file mode
        if not use_stdout and reject_file.exists():
            with open(reject_file, "r") as f:
                line_count = sum(1 for _ in f)
            if line_count <= 1:
                logger.debug(f"Removing empty reject file: {reject_file}")
                reject_file.unlink()

    return 0
