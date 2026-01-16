"""Command-line interface for csvnorm."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich_argparse import RichHelpFormatter

from csvnorm import __version__
from csvnorm.core import process_csv
from csvnorm.utils import setup_logger

console = Console()


def show_banner() -> None:
    """Show simple styled banner."""
    console.print()
    console.print("  csvnorm  ", style="bold cyan on black", justify="center")
    console.print()


class VersionAction(argparse.Action):
    """Custom action to show banner with version."""

    def __call__(self, parser, _namespace, _values, _option_string=None):
        show_banner()
        console.print(f"csvnorm {__version__}", style="bold")
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
  csvnorm data.csv -d ';' -o output.csv --force
  csvnorm data.csv --keep-names --delimiter '\\t'
  csvnorm https://example.com/data.csv -o processed/data.csv
  csvnorm data.csv -V
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
        help="Force overwrite of existing output files",
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
        "-o",
        "--output-file",
        type=Path,
        help="Set output file path (absolute or relative)",
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

    # Determine output file (default: input filename in current directory)
    if args.output_file is None:
        input_name = Path(args.input_file).name
        output_file = Path.cwd() / input_name
    else:
        output_file = args.output_file

    # Run processing
    return process_csv(
        input_file=args.input_file,
        output_file=output_file,
        force=args.force,
        keep_names=args.keep_names,
        delimiter=args.delimiter,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
