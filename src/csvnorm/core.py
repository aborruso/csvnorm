"""Core processing logic for csvnorm."""

import logging
import shutil
import sys
import tempfile
import urllib.error
import zipfile
from urllib.parse import urlparse
from pathlib import Path
from typing import Any, Optional, Union

import duckdb
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TaskID

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
    is_compressed_url,
    is_gzip_path,
    is_url,
    is_zip_path,
    resolve_zip_csv_entry,
    supports_http_range,
    validate_delimiter,
    validate_url,
)
from csvnorm.validation import normalize_csv, validate_csv

logger = logging.getLogger("csvnorm")
console = Console()


def _resolve_input_path(
    input_file: str, output_file: Optional[Path]
) -> tuple[Union[str, Path], bool]:
    """Validate input and return input path plus remote flag."""
    is_remote = is_url(input_file)

    if is_remote:
        try:
            validate_url(input_file)
        except ValueError as e:
            show_error_panel(str(e))
            raise
        return input_file, True

    file_path = Path(input_file)
    if not file_path.exists():
        show_error_panel(f"Input file not found\n{file_path}")
        raise FileNotFoundError(str(file_path))

    if not file_path.is_file():
        show_error_panel(f"Not a file\n{file_path}")
        raise IsADirectoryError(str(file_path))

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
            raise ValueError("Output path matches input path")

    return file_path, False


def _setup_output_paths(
    output_file: Optional[Path],
    force: bool,
    temp_dir: Path,
) -> tuple[Path, Path, Path]:
    """Determine output, reject, and temp UTF-8 paths."""
    if output_file is None:
        actual_output_file = temp_dir / "output.csv"
        reject_file = temp_dir / "reject_errors.csv"
        temp_utf8_file = temp_dir / "utf8.csv"
        return actual_output_file, reject_file, temp_utf8_file

    output_dir = output_file.parent
    actual_output_file = output_file
    reject_file = output_dir / f"{output_file.stem}_reject_errors.csv"
    temp_utf8_file = temp_dir / f"{output_file.stem}_utf8.csv"

    if output_file.exists() and not force:
        show_warning_panel(
            f"Output file already exists\n\n"
            f"{output_file}\n\n"
            f"Use [bold]--force[/bold] to overwrite."
        )
        raise FileExistsError(str(output_file))

    if reject_file.exists():
        reject_file.unlink()

    return actual_output_file, reject_file, temp_utf8_file


def _download_for_mojibake_if_needed(
    input_file: str,
    input_path: Union[str, Path],
    is_remote: bool,
    fix_mojibake_sample: Optional[int],
    temp_dir: Path,
    temp_files: list[Path],
) -> tuple[Union[str, Path], bool]:
    """Download remote file if mojibake repair is requested."""
    if not (is_remote and fix_mojibake_sample is not None):
        return input_path, is_remote

    try:
        download_path = temp_dir / "remote_download.csv"
        download_url_to_file(input_file, download_path)
    except (OSError, urllib.error.URLError) as e:
        show_error_panel(f"Failed to download remote file\n{e}")
        raise

    temp_files.append(download_path)
    return download_path, False


def _download_remote_if_needed(
    input_file: str,
    input_path: Union[str, Path],
    is_remote: bool,
    download_remote: bool,
    temp_dir: Path,
    temp_files: list[Path],
) -> tuple[Union[str, Path], bool]:
    """Download remote file if range requests are unsupported and flag enabled."""
    if not is_remote:
        return input_path, is_remote

    if download_remote:
        try:
            parsed_suffix = Path(urlparse(input_file).path).suffix.lower()
            suffix = parsed_suffix if parsed_suffix else ".csv"
            download_path = temp_dir / f"remote_download{suffix}"
            download_url_to_file(input_file, download_path)
        except (OSError, urllib.error.URLError) as e:
            show_error_panel(f"Failed to download remote file\n{e}")
            raise

        temp_files.append(download_path)
        return download_path, False

    if _check_remote_range_support(input_file):
        return input_path, is_remote

    if not download_remote:
        show_error_panel(
            "Remote server does not support HTTP range requests\n\n"
            f"URL: [cyan]{input_file}[/cyan]\n\n"
            "DuckDB requires HTTP range requests to read remote CSVs.\n"
            "Use [bold]--download-remote[/bold] to download the file locally "
            "before processing."
        )
        raise ValueError("Remote server does not support range requests")


def _check_remote_range_support(input_file: str) -> bool:
    """Verify the remote server supports HTTP range requests."""
    return supports_http_range(input_file)


def _extract_single_csv_from_zip(zip_path: Path, temp_dir: Path) -> Path:
    """Extract the single CSV entry from a zip archive into temp_dir."""
    csv_entry = resolve_zip_csv_entry(zip_path)
    safe_name = Path(csv_entry).name
    output_path = temp_dir / safe_name
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(csv_entry) as source, open(output_path, "wb") as target:
            shutil.copyfileobj(source, target)
    return output_path


def _handle_local_encoding(
    file_input_path: Path,
    temp_utf8_file: Path,
    progress: Progress,
    task: TaskID,
    temp_files: list[Path],
) -> tuple[Union[str, Path], str]:
    """Detect encoding and convert to UTF-8 if needed."""
    progress.update(task, description="[cyan]Detecting encoding...")
    encoding = detect_encoding(file_input_path)
    logger.debug(f"Detected encoding: {encoding}")
    progress.update(
        task, description=f"[green]✓[/green] Detected encoding: {encoding}"
    )

    working_file: Union[str, Path] = file_input_path
    if needs_conversion(encoding):
        progress.update(
            task,
            description=f"[cyan]Converting from {encoding} to UTF-8...",
        )
        convert_to_utf8(file_input_path, temp_utf8_file, encoding)
        working_file = temp_utf8_file
        temp_files.append(temp_utf8_file)
        progress.update(task, description="[green]✓[/green] Converted to UTF-8")
    else:
        note = (
            "ASCII is UTF-8 compatible; no conversion needed"
            if encoding == "ascii"
            else "UTF-8; no conversion needed"
        )
        progress.update(
            task,
            description=f"[green]✓[/green] Encoding: {encoding} ({note})",
        )

    return working_file, encoding


def _handle_mojibake_if_needed(
    working_file: Union[str, Path],
    temp_dir: Path,
    fix_mojibake_sample: Optional[int],
    progress: Progress,
    task: TaskID,
    temp_files: list[Path],
) -> tuple[bool, Union[str, Path]]:
    """Optionally repair mojibake in local files."""
    if fix_mojibake_sample is None:
        return False, working_file

    if not isinstance(working_file, Path):
        logger.debug("Skipping mojibake check for non-local input.")
        return False, working_file

    progress.update(task, description="[cyan]Checking mojibake...")
    sample_size = fix_mojibake_sample
    repaired_path = temp_dir / "mojibake_fixed.csv"
    mojibake_repaired, working_file = repair_file(
        working_file, repaired_path, sample_size
    )
    if mojibake_repaired:
        temp_files.append(repaired_path)
        progress.update(
            task, description="[green]✓[/green] Mojibake repaired (ftfy)"
        )
    else:
        progress.update(task, description="[green]✓[/green] Mojibake check: clean")

    return mojibake_repaired, working_file


def _validate_csv_with_http_handling(
    working_file: Union[str, Path],
    reject_file: Path,
    is_remote: bool,
    skip_rows: int,
    input_file: str,
    progress: Progress,
    task: TaskID,
) -> tuple[int, list[str], Optional[dict[str, Union[str, int]]]]:
    """Run validation with HTTP error handling."""
    progress.update(task, description="[cyan]Validating CSV...")
    logger.debug("Validating CSV with DuckDB...")

    try:
        return validate_csv(
            working_file, reject_file, is_remote=is_remote, skip_rows=skip_rows
        )
    except duckdb.Error as e:
        progress.stop()
        error_msg = str(e)

        if "zipfs" in error_msg.lower():
            show_error_panel(
                "Failed to load DuckDB zipfs extension for zip input\n\n"
                f"{error_msg}\n\n"
                "Install/upgrade DuckDB or extract the zip locally and retry."
            )
            raise

        if "HTTP Error" in error_msg or "HTTPException" in error_msg:
            if "ETag on reading file" in error_msg:
                show_error_panel(
                    "Remote file changed during read (ETag mismatch)\n\n"
                    f"URL: [cyan]{input_file}[/cyan]\n\n"
                    "Try again and use [bold]--download-remote[/bold] to download "
                    "the file locally before processing."
                )
                raise
            if "404" in error_msg:
                show_error_panel(
                    "Remote CSV file not found (HTTP 404)\n\n"
                    f"URL: [cyan]{input_file}[/cyan]\n\n"
                    "Please check the URL is correct."
                )
            elif "401" in error_msg or "403" in error_msg:
                show_error_panel(
                    "Authentication required (HTTP 401/403)\n\n"
                    f"URL: [cyan]{input_file}[/cyan]\n\n"
                    "This tool only supports public URLs without authentication.\n"
                    "Please download the file manually first."
                )
            elif (
                "timeout" in error_msg.lower() or "timed out" in error_msg.lower()
            ):
                show_error_panel(
                    "HTTP request timeout (30 seconds)\n\n"
                    f"URL: [cyan]{input_file}[/cyan]\n\n"
                    "The remote server took too long to respond.\n"
                    "Try again later or download the file manually."
                )
            elif "range" in error_msg.lower():
                show_error_panel(
                    "Remote server does not support HTTP range requests\n\n"
                    f"URL: [cyan]{input_file}[/cyan]\n\n"
                    "DuckDB requires HTTP range requests to read remote CSVs.\n"
                    "Please download the file locally and run csvnorm on the file."
                )
            else:
                show_error_panel(f"HTTP request failed\n\n{error_msg}")
            raise

        raise


def _normalize_and_refresh_errors(
    working_file: Union[str, Path],
    actual_output_file: Path,
    delimiter: str,
    keep_names: bool,
    is_remote: bool,
    skip_rows: int,
    fallback_config: Optional[dict[str, Union[str, int]]],
    reject_file: Path,
    reject_count: int,
    error_types: list[str],
) -> tuple[Optional[dict[str, Union[str, int]]], int, list[str], bool]:
    """Normalize CSV and update reject counts if fallback differs."""
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

    has_validation_errors = reject_count > 1
    if used_fallback and used_fallback != fallback_config:
        reject_count = sum(1 for _ in open(reject_file)) if reject_file.exists() else 0
        has_validation_errors = reject_count > 1
        if has_validation_errors:
            from csvnorm.validation import _get_error_types

            error_types = _get_error_types(reject_file)

    return used_fallback, reject_count, error_types, has_validation_errors


def _emit_stdout_output(
    actual_output_file: Path,
    has_validation_errors: bool,
    reject_count: int,
    reject_file: Path,
    summary: Optional[dict[str, Any]] = None,
) -> int:
    """Write output to stdout and emit validation warnings if needed."""
    try:
        with open(actual_output_file, "r") as f:
            sys.stdout.write(f.read())
    except BrokenPipeError:
        return 0

    if summary:
        stderr_console = Console(stderr=True)
        show_success_table(
            input_file=summary["input_file"],
            output_file=summary["output_file"],
            encoding=summary["encoding"],
            is_remote=summary["is_remote"],
            mojibake_repaired=summary["mojibake_repaired"],
            row_count=summary["row_count"],
            column_count=summary["column_count"],
            input_size=summary["input_size"],
            output_size=summary["output_size"],
            delimiter=summary["delimiter"],
            keep_names=summary["keep_names"],
            output_display=summary["output_display"],
            out_console=stderr_console,
        )

    if has_validation_errors:
        stderr_console = Console(stderr=True)
        stderr_console.print()
        stderr_console.print(
            f"[yellow]Warning:[/yellow] {reject_count - 1} rows rejected during validation",
            style="yellow",
        )
        stderr_console.print(f"Reject file saved to: {reject_file}", style="dim")
        stderr_console.print()
        return 1

    return 0


def _cleanup_temp_artifacts(
    use_stdout: bool, reject_file: Path, temp_files: list[Path]
) -> None:
    """Cleanup temp files and prune empty reject files."""
    import shutil

    if use_stdout and reject_file.exists():
        with open(reject_file, "r") as f:
            line_count = sum(1 for _ in f)
        if line_count <= 1:
            reject_file.unlink()

    for temp_path in temp_files:
        if temp_path.exists():
            logger.debug(f"Removing temp path: {temp_path}")
            if temp_path.is_dir():
                if use_stdout and reject_file.exists() and reject_file.parent == temp_path:
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

    if not use_stdout and reject_file.exists():
        with open(reject_file, "r") as f:
            line_count = sum(1 for _ in f)
        if line_count <= 1:
            logger.debug(f"Removing empty reject file: {reject_file}")
            reject_file.unlink()


def process_csv(
    input_file: str,
    output_file: Optional[Path],
    force: bool = False,
    keep_names: bool = False,
    delimiter: str = ",",
    skip_rows: int = 0,
    verbose: bool = False,
    fix_mojibake_sample: Optional[int] = None,
    download_remote: bool = False,
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

    try:
        input_path, is_remote = _resolve_input_path(input_file, output_file)
    except (ValueError, FileNotFoundError, IsADirectoryError):
        return 1

    try:
        validate_delimiter(delimiter)
    except ValueError as e:
        show_error_panel(str(e))
        return 1

    if is_remote and is_compressed_url(input_file) and not download_remote:
        show_warning_panel(
            "Remote compressed file detected\n\n"
            f"URL: [cyan]{input_file}[/cyan]\n\n"
            "Remote ZIP/GZIP inputs are not unpacked automatically.\n"
            "Use [bold]--download-remote[/bold] to download and process locally."
        )

    # Setup paths
    temp_dir = Path(tempfile.mkdtemp(prefix="csvnorm_"))

    try:
        actual_output_file, reject_file, temp_utf8_file = _setup_output_paths(
            output_file, force, temp_dir
        )
    except FileExistsError:
        return 1

    # Track files to clean up
    temp_files: list[Path] = [temp_dir]

    try:
        try:
            input_path, is_remote = _download_remote_if_needed(
                input_file,
                input_path,
                is_remote,
                download_remote,
                temp_dir,
                temp_files,
            )
        except (ValueError, OSError, urllib.error.URLError):
            return 1

        input_path, is_remote = _download_for_mojibake_if_needed(
            input_file,
            input_path,
            is_remote,
            fix_mojibake_sample,
            temp_dir,
            temp_files,
        )
    except (OSError, urllib.error.URLError):
        return 1

    compressed_type: Optional[str] = None
    compressed_input_path: Union[str, Path] = input_path
    local_input_path: Optional[Path]
    if isinstance(input_path, Path):
        local_input_path = input_path
    else:
        local_input_path = None
    if local_input_path:
        try:
            if is_zip_path(local_input_path):
                # Always extract local zip to allow encoding detection/conversion.
                extracted_path = _extract_single_csv_from_zip(local_input_path, temp_dir)
                input_path = extracted_path
                local_input_path = extracted_path
                temp_files.append(extracted_path)
            elif is_gzip_path(local_input_path):
                compressed_type = "gzip"
        except ValueError as e:
            show_error_panel(str(e))
            return 1

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
            elif compressed_type:
                progress.update(
                    task,
                    description=(
                        f"[green]✓[/green] {compressed_type.upper()} input "
                        "(encoding handled by DuckDB)"
                    ),
                )
                working_file = compressed_input_path
                encoding = compressed_type
            else:
                file_input_path = input_path
                assert isinstance(file_input_path, Path)

                try:
                    working_file, encoding = _handle_local_encoding(
                        file_input_path,
                        temp_utf8_file,
                        progress,
                        task,
                        temp_files,
                    )
                except ValueError as e:
                    progress.stop()
                    show_error_panel(str(e))
                    return 1
                except (UnicodeDecodeError, LookupError) as e:
                    progress.stop()
                    show_error_panel(f"Encoding conversion failed\n{e}")
                    return 1

                try:
                    mojibake_repaired, working_file = _handle_mojibake_if_needed(
                        working_file,
                        temp_dir,
                        fix_mojibake_sample,
                        progress,
                        task,
                        temp_files,
                    )
                except (OSError, UnicodeDecodeError, ValueError) as e:
                    progress.stop()
                    show_error_panel(f"Mojibake repair failed\n{e}")
                    return 1

            # Step 3: Validate CSV
            try:
                (
                    reject_count,
                    error_types,
                    fallback_config,
                ) = _validate_csv_with_http_handling(
                    working_file,
                    reject_file,
                    is_remote,
                    skip_rows,
                    input_file,
                    progress,
                    task,
                )
            except duckdb.Error:
                return 1

            has_validation_errors = reject_count > 1
            if has_validation_errors:
                progress.stop()

            progress.update(task, description="[green]✓[/green] CSV validated")

            # Step 4: Normalize and write output
            progress.update(task, description="[cyan]Normalizing and writing output...")
            logger.debug("Normalizing CSV...")
            try:
                (
                    used_fallback,
                    reject_count,
                    error_types,
                    has_validation_errors,
                ) = _normalize_and_refresh_errors(
                    working_file,
                    actual_output_file,
                    delimiter,
                    keep_names,
                    is_remote,
                    skip_rows,
                    fallback_config,
                    reject_file,
                    reject_count,
                    error_types,
                )
            except duckdb.Error as e:
                progress.stop()
                error_msg = str(e)
                if "zipfs" in error_msg.lower():
                    show_error_panel(
                        "Failed to load DuckDB zipfs extension for zip input\n\n"
                        f"{error_msg}\n\n"
                        "Ensure DuckDB can download extensions or install zipfs manually."
                    )
                else:
                    show_error_panel(f"Normalization failed\n{error_msg}")
                return 1

            logger.debug(f"Output written to: {actual_output_file}")
            progress.update(task, description="[green]✓[/green] Complete")

        # Handle output based on mode
        if local_input_path and local_input_path.exists():
            input_size = local_input_path.stat().st_size
        else:
            input_size = (
                working_file.stat().st_size if isinstance(working_file, Path) else 0
            )
        output_size = actual_output_file.stat().st_size
        row_count = get_row_count(actual_output_file)
        column_count = get_column_count(actual_output_file, delimiter)

        if use_stdout:
            summary = {
                "input_file": input_file,
                "output_file": actual_output_file,
                "encoding": encoding,
                "is_remote": is_remote,
                "mojibake_repaired": mojibake_repaired,
                "row_count": row_count,
                "column_count": column_count,
                "input_size": input_size,
                "output_size": output_size,
                "delimiter": delimiter,
                "keep_names": keep_names,
                "output_display": "stdout",
            }
            return _emit_stdout_output(
                actual_output_file,
                has_validation_errors,
                reject_count,
                reject_file,
                summary,
            )
        else:
            # File mode: show success table
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
        _cleanup_temp_artifacts(use_stdout, reject_file, temp_files)

    return 0
