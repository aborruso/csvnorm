"""UI formatting functions for csvnorm terminal output."""

from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from csvnorm.encoding import needs_conversion
from csvnorm.utils import format_file_size

console = Console()


def show_error_panel(message: str, title: str = "Error") -> None:
    """Display an error panel with red border.

    Args:
        message: Error message to display.
        title: Panel title (default: "Error").
    """
    console.print(Panel(f"[bold red]{title}:[/bold red] {message}", border_style="red"))


def show_warning_panel(message: str, title: str = "Warning") -> None:
    """Display a warning panel with yellow border.

    Args:
        message: Warning message to display.
        title: Panel title (default: "Warning").
    """
    console.print(
        Panel(f"[bold yellow]{title}:[/bold yellow] {message}", border_style="yellow")
    )


def show_success_table(
    input_file: str,
    output_file: Path,
    encoding: str,
    is_remote: bool,
    row_count: int,
    column_count: int,
    input_size: int,
    output_size: int,
    delimiter: str,
    keep_names: bool,
) -> None:
    """Display success summary table with processing results.

    Args:
        input_file: Input CSV file path or URL.
        output_file: Output CSV file path.
        encoding: Detected encoding (or "remote" for URLs).
        is_remote: Whether input was a remote URL.
        row_count: Number of data rows in output.
        column_count: Number of columns in output.
        input_size: Input file size in bytes (0 for remote).
        output_size: Output file size in bytes.
        delimiter: Output delimiter character.
        keep_names: Whether original column names were kept.
    """
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_row("[green]✓[/green] Success", "")
    table.add_row("Input:", f"[cyan]{input_file}[/cyan]")
    table.add_row("Output:", f"[cyan]{output_file}[/cyan]")

    # Encoding info (only for local files)
    if not is_remote:
        if needs_conversion(encoding):
            table.add_row("Encoding:", f"{encoding} → UTF-8 [dim](converted)[/dim]")
        else:
            if encoding == "ascii":
                note = "ASCII is UTF-8 compatible; no conversion needed"
            else:
                note = "UTF-8; no conversion needed"
            table.add_row("Encoding:", f"{encoding} [dim]({note})[/dim]")

    # Statistics
    table.add_row("Rows:", f"{row_count:,}")
    table.add_row("Columns:", f"{column_count}")
    if not is_remote:
        table.add_row("Input size:", format_file_size(input_size))
    table.add_row("Output size:", format_file_size(output_size))

    # Optional fields
    if delimiter != ",":
        table.add_row("Delimiter:", repr(delimiter))
    if not keep_names:
        table.add_row("Headers:", "normalized to snake_case")

    console.print()
    console.print(table)


def show_validation_error_panel(
    reject_count: int, error_types: list[str], reject_file: Path
) -> None:
    """Display validation error summary panel.

    Args:
        reject_count: Number of rejected rows (including header).
        error_types: List of error type descriptions.
        reject_file: Path to reject errors CSV file.
    """
    console.print()
    error_lines = []
    error_lines.append("[bold red]Validation Errors:[/bold red]")
    error_lines.append("")
    error_lines.append(f"Rejected rows: [yellow]{reject_count - 1}[/yellow]")

    if error_types:
        error_lines.append("")
        error_lines.append("[dim]Error types:[/dim]")
        for error_type in error_types:
            error_lines.append(f"  • {error_type}")

    error_lines.append("")
    error_lines.append(f"Details: [cyan]{reject_file}[/cyan]")

    console.print(
        Panel(
            "\n".join(error_lines),
            border_style="yellow",
            title="[yellow]![/yellow] Validation Failed",
        )
    )
