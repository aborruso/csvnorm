"""Command-line interface for CSV normalizer."""

import argparse
import sys
from pathlib import Path

from csv_normalizer import __version__
from csv_normalizer.core import process_csv
from csv_normalizer.utils import setup_logger


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="csv_normalizer",
        description="Validate and normalize CSV files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
Examples:
  csv_normalizer data.csv -d ';' -o output_folder --force
  csv_normalizer data.csv --keep-names --delimiter '\\t'
  csv_normalizer data.csv -v
""",
    )

    parser.add_argument(
        "input_file",
        type=Path,
        help="Input CSV file path",
    )

    parser.add_argument(
        "-f",
        "--force",
        action="store_true",
        help="Force overwrite of existing output files",
    )

    parser.add_argument(
        "-n",
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
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Set custom output directory (default: current working directory)",
    )

    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable verbose output for debugging",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    """Main entry point for the CLI.

    Args:
        argv: Command line arguments (defaults to sys.argv[1:]).

    Returns:
        Exit code: 0 for success, 1 for error.
    """
    parser = create_parser()
    args = parser.parse_args(argv)

    # Setup logging
    setup_logger(args.verbose)

    # Run processing
    return process_csv(
        input_file=args.input_file,
        output_dir=args.output_dir,
        force=args.force,
        keep_names=args.keep_names,
        delimiter=args.delimiter,
        verbose=args.verbose,
    )


if __name__ == "__main__":
    sys.exit(main())
