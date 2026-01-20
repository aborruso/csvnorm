"""Command-line interface for csvnorm."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich_argparse import RichHelpFormatter

from importlib.metadata import version
from csvnorm.core import process_csv
from csvnorm.mojibake import DEFAULT_MOJIBAKE_SAMPLE
from csvnorm.utils import setup_logger

console = Console()


def show_banner() -> None:
    """Show simple styled banner."""
    console.print()
    console.print("  csvnorm  ", style="bold cyan on black", justify="center")
    console.print()


class VersionAction(argparse.Action):
    """Custom action to show banner with version."""

    def __call__(
        self,
        parser: argparse.ArgumentParser,
        namespace: argparse.Namespace,
        values: object,
        option_string: Optional[str] = None,
    ) -> None:
        show_banner()
        console.print(f"csvnorm {version('csvnorm')}", style="bold")
        console.print()
        console.print(
            "Validate and normalize CSV files for exploratory data analysis",
            style="dim",
        )
        console.print()
        console.print("Author: aborruso", style="dim")
        console.print(
            "Repository: https://github.com/aborruso/csvnorm", style="dim cyan"
        )
        console.print("License: MIT", style="dim")
        parser.exit()


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="csvnorm",
        description="Validate and normalize CSV files for exploratory data analysis",
        formatter_class=RichHelpFormatter,
        epilog="""\
Examples:
  csvnorm data.csv                          # Output to stdout
  csvnorm data.csv -o output.csv            # Write to file
  csvnorm data.csv > output.csv             # Shell redirect
  csvnorm data.csv | head -20               # Preview with pipe
  csvnorm data.csv -d ';' -o output.csv     # Custom delimiter
  csvnorm data.csv --skip-rows 2 -o out.csv # Skip first 2 rows
  csvnorm https://example.com/data.csv -o processed.csv
""",
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Input CSV file path or HTTP/HTTPS URL",
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force overwrite of existing output file (when -o is specified)",
    )

    parser.add_argument(
        "-k",
        "--keep-names",
        action="store_true",
        help=(
            "Keep original column names (disable snake_case normalization). "
            "By default, column names are converted to snake_case format "
            "(e.g., 'Column Name' becomes 'column_name')."
        ),
    )

    parser.add_argument(
        "-d",
        "--delimiter",
        default=",",
        help="Set custom field delimiter (default: comma). Example: -d ';'",
    )

    parser.add_argument(
        "-s",
        "--skip-rows",
        type=int,
        default=0,
        help=(
            "Skip first N rows of input file. Useful for CSV files with "
            "metadata or comments before the header row. Example: --skip-rows 2"
        ),
    )

    parser.add_argument(
        "-o",
        "--output-file",
        type=Path,
        help="Write to file instead of stdout (default: stdout)",
    )

    parser.add_argument(
        "--fix-mojibake",
        nargs="?",
        const=DEFAULT_MOJIBAKE_SAMPLE,
        type=int,
        help=(
            "Fix mojibake using ftfy. Optionally pass sample size "
            "(chars to sample, default 5000). Use 0 to force repair "
            "without detection. Example: --fix-mojibake 4000 or --fix-mojibake 0."
        ),
    )

    parser.add_argument(
        "--download-remote",
        action="store_true",
        help=(
            "Download remote CSV locally before processing. "
            "Useful for servers that block range reads or change files during reads, "
            "and required for remote .zip/.gz inputs."
        ),
    )

    parser.add_argument(
        "-V",
        "--verbose",
        action="store_true",
        help="Enable verbose output for debugging",
    )

    parser.add_argument(
        "-v",
        "--version",
        action=VersionAction,
        nargs=0,
        help="Show version number with banner",
    )

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    parser = create_parser()

    # Handle missing arguments gracefully
    if argv is None:
        argv = sys.argv[1:]

    if not argv or (len(argv) == 1 and argv[0] in ["-h", "--help"]):
        parser.print_help()
        return 0 if argv else 2

    args = parser.parse_args(argv)

    # Show banner in verbose mode
    if args.verbose:
        show_banner()

    # Setup logging
    setup_logger(args.verbose)

    # Validate skip_rows
    if args.skip_rows < 0:
        console.print("[red]Error:[/red] --skip-rows must be non-negative", style="red")
        return 1

    # Run processing (output_file can be None for stdout)
    fix_mojibake_sample = args.fix_mojibake
    return process_csv(
        input_file=args.input_file,
        output_file=args.output_file,
        force=args.force,
        keep_names=args.keep_names,
        delimiter=args.delimiter,
        skip_rows=args.skip_rows,
        verbose=args.verbose,
        fix_mojibake_sample=fix_mojibake_sample,
        download_remote=args.download_remote,
    )


if __name__ == "__main__":
    sys.exit(main())
