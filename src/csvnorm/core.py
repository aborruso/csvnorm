"""Core processing logic for csvnorm."""

import logging
from pathlib import Path
from typing import Union

from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from csvnorm.encoding import convert_to_utf8, detect_encoding, needs_conversion
from csvnorm.utils import (
    ensure_output_dir,
    extract_filename_from_url,
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
    output_dir: Path,
    force: bool = False,
    keep_names: bool = False,
    delimiter: str = ",",
    verbose: bool = False,
) -> int:
    """Main CSV processing pipeline.

    Args:
        input_file: Path to input CSV file or HTTP/HTTPS URL.
        output_dir: Directory for output files.
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
            console.print(Panel(f"[bold red]Error:[/bold red] {e}", border_style="red"))
            return 1
        base_name = extract_filename_from_url(input_file)
        input_path = input_file  # Keep as string for DuckDB
    else:
        # Validate local file
        file_path = Path(input_file)
        if not file_path.exists():
            console.print(
                Panel(
                    f"[bold red]Error:[/bold red] Input file not found\n{file_path}",
                    border_style="red",
                )
            )
            return 1

        if not file_path.is_file():
            console.print(
                Panel(
                    f"[bold red]Error:[/bold red] Not a file\n{file_path}",
                    border_style="red",
                )
            )
            return 1

        base_name = to_snake_case(file_path.name)
        input_path = file_path

    try:
        validate_delimiter(delimiter)
    except ValueError as e:
        console.print(Panel(f"[bold red]Error:[/bold red] {e}", border_style="red"))
        return 1

    # Setup paths
    ensure_output_dir(output_dir)

    output_file = output_dir / f"{base_name}.csv"
    reject_file = output_dir / f"{base_name}_reject_errors.csv"
    temp_utf8_file = output_dir / f"{base_name}_utf8.csv"

    # Check if output exists
    if output_file.exists() and not force:
        console.print(
            Panel(
                f"[bold yellow]Warning:[/bold yellow] Output file already exists\n\n"
                f"{output_file}\n\n"
                f"Use [bold]--force[/bold] to overwrite.",
                border_style="yellow",
            )
        )
        return 1

    # Clean up previous reject file
    if reject_file.exists():
        reject_file.unlink()

    # Track files to clean up
    temp_files: list[Path] = []

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
                    console.print(
                        Panel(f"[bold red]Error:[/bold red] {e}", border_style="red")
                    )
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
                            task, description=f"[green]✓[/green] Converted to UTF-8"
                        )
                    except (UnicodeDecodeError, LookupError) as e:
                        progress.stop()
                        console.print(
                            Panel(
                                f"[bold red]Error:[/bold red] Encoding conversion failed\n{e}",
                                border_style="red",
                            )
                        )
                        return 1
                else:
                    progress.update(
                        task,
                        description=f"[green]✓[/green] Encoding: {encoding} (no conversion needed)",
                    )

            # Step 3: Validate CSV
            progress.update(task, description="[cyan]Validating CSV...")
            logger.debug("Validating CSV with DuckDB...")

            try:
                is_valid = validate_csv(working_file, reject_file, is_remote=is_remote)
            except Exception as e:
                progress.stop()
                error_msg = str(e)

                # Check for common HTTP errors
                if "HTTP Error" in error_msg or "HTTPException" in error_msg:
                    if "404" in error_msg:
                        console.print(
                            Panel(
                                "[bold red]Error:[/bold red] Remote CSV file not found (HTTP 404)\n\n"
                                f"URL: [cyan]{input_file}[/cyan]\n\n"
                                "Please check the URL is correct.",
                                border_style="red",
                            )
                        )
                    elif "401" in error_msg or "403" in error_msg:
                        console.print(
                            Panel(
                                "[bold red]Error:[/bold red] Authentication required (HTTP 401/403)\n\n"
                                f"URL: [cyan]{input_file}[/cyan]\n\n"
                                "This tool only supports public URLs without authentication.\n"
                                "Please download the file manually first.",
                                border_style="red",
                            )
                        )
                    elif (
                        "timeout" in error_msg.lower()
                        or "timed out" in error_msg.lower()
                    ):
                        console.print(
                            Panel(
                                "[bold red]Error:[/bold red] HTTP request timeout (30 seconds)\n\n"
                                f"URL: [cyan]{input_file}[/cyan]\n\n"
                                "The remote server took too long to respond.\n"
                                "Try again later or download the file manually.",
                                border_style="red",
                            )
                        )
                    else:
                        console.print(
                            Panel(
                                f"[bold red]Error:[/bold red] HTTP request failed\n\n"
                                f"{error_msg}",
                                border_style="red",
                            )
                        )
                else:
                    # Re-raise non-HTTP errors
                    raise
                return 1

            if not is_valid:
                progress.stop()
                console.print(
                    Panel(
                        "[bold red]Error:[/bold red] DuckDB encountered invalid rows\n\n"
                        f"Details: [cyan]{reject_file}[/cyan]\n\n"
                        "Please fix the issues and try again.",
                        border_style="red",
                    )
                )
                return 1

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

        # Success summary table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_row("[green]✓[/green] Success", "")
        table.add_row("Input:", f"[cyan]{input_file}[/cyan]")
        table.add_row("Output:", f"[cyan]{output_file}[/cyan]")
        if not is_remote:
            table.add_row("Encoding:", encoding)
        if delimiter != ",":
            table.add_row("Delimiter:", repr(delimiter))
        if not keep_names:
            table.add_row("Headers:", "normalized to snake_case")

        console.print()
        console.print(table)

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
