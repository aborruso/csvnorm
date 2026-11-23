"""Command-line interface for csvnorm."""

import argparse
import codecs
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich_argparse import RawDescriptionRichHelpFormatter

from importlib.metadata import version
from csvnorm.core import process_csv
from csvnorm.mojibake import DEFAULT_MOJIBAKE_SAMPLE
from csvnorm.utils import setup_logger, to_snake_case

console = Console()
err_console = Console(stderr=True)


def show_banner(target: Console = console) -> None:
    """Show simple styled banner."""
    target.print()
    target.print("  csvnorm  ", style="bold cyan on black", justify="center")
    target.print()



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


_EXAMPLES = """
Examples:
  csvnorm data.csv                                 Output to stdout (default)
  csvnorm data.csv -o output.csv                   Write to file
  csvnorm data.csv > output.csv                    Shell redirect
  csvnorm data.csv | head -20                      Pipe to another command
  csvnorm data.csv --check                         Validate only, no output
  csvnorm data.csv --strict | process.sh           Fail-fast pipeline
  csvnorm data.csv -d ';' -o output.csv            Custom delimiter
  csvnorm data.csv --skip-rows 2 -o out.csv        Skip metadata rows
  cat data.csv | csvnorm -                         Read from stdin
  csvnorm https://example.com/data.csv -o out.csv  Remote URL
"""


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="csvnorm",
        description="Validate and normalize CSV files for exploratory data analysis",
        formatter_class=RawDescriptionRichHelpFormatter,
        epilog=_EXAMPLES,
    )

    parser.add_argument(
        "input_file",
        type=str,
        help="Input CSV file path, HTTP/HTTPS URL, or - for stdin",
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
        help="Set custom output field delimiter (default: comma). Example: -d ';'",
    )

    parser.add_argument(
        "-e",
        "--encoding",
        metavar="NAME",
        help=(
            "Declare the input encoding (any Python codec name, e.g. cp1252, "
            "latin-1, cp850) and skip automatic detection. If the input cannot "
            "be decoded with it, csvnorm stops with exit code 1. Example: -e cp1252"
        ),
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
        "-O",
        "--auto-output",
        action="store_true",
        help=(
            "Auto-derive output filename in snake_case from input filename, "
            "saved in the same directory. Example: 'My Data.csv' → 'my_data.csv'. "
            "Asks confirmation if output already exists (unless -f is set)."
        ),
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
            "Deprecated: remote URLs are always downloaded before processing. "
            "This flag is kept for compatibility and can be omitted."
        ),
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "Exit with error code 1 if any validation errors occur, "
            "preventing output from being written. Use this in pipelines "
            "where you want to fail fast on malformed data."
        ),
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help=(
            "Validate CSV structure without processing or normalizing. "
            "Exits with code 0 if valid, 1 if validation errors found. "
            "No output file is created. Use for quick validation checks."
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
        console.print()
        console.print(
            "csvnorm | Validate and normalize CSV files for exploratory data analysis | "
            "https://aborruso.github.io/csvnorm/"
        )
        console.print()
        parser.print_help()
        return 0 if argv else 2

    args = parser.parse_args(argv)

    # Show banner in verbose mode
    if args.verbose:
        show_banner(err_console)

    # Setup logging
    setup_logger(args.verbose)

    # Validate skip_rows
    if args.encoding is not None:
        try:
            info = codecs.lookup(args.encoding)
            if not getattr(info, "_is_text_encoding", True):
                raise LookupError(args.encoding)
        except LookupError:
            err_console.print(
                f"[red]Error:[/red] Unknown encoding: {args.encoding}\n"
                "Use a Python codec name, for example cp1252, latin-1 or cp850.",
                style="red",
            )
            return 1

    if args.skip_rows < 0:
        err_console.print("[red]Error:[/red] --skip-rows must be non-negative", style="red")
        return 1

    # Resolve --auto-output into output_file
    if args.auto_output:
        if args.output_file:
            err_console.print("[red]Error:[/red] -O/--auto-output cannot be used with -o", style="red")
            return 1
        if args.input_file == "-":
            err_console.print("[red]Error:[/red] -O/--auto-output cannot be used with stdin input", style="red")
            return 1
        if args.input_file.startswith("http://") or args.input_file.startswith("https://"):
            err_console.print("[red]Error:[/red] -O/--auto-output cannot be used with URL input", style="red")
            return 1

        input_path = Path(args.input_file)
        snake_stem = to_snake_case(input_path.stem)
        auto_output = input_path.parent / f"{snake_stem}.csv"

        if auto_output.resolve() == input_path.resolve():
            err_console.print(
                f"[yellow]Warning:[/yellow] filename is already in snake_case ({input_path.name}). "
                "Use -o to specify a different output path.",
                style="yellow",
            )
            return 1

        if auto_output.exists() and not args.force:
            if not sys.stdin.isatty():
                err_console.print(
                    f"[red]Error:[/red] Output file already exists: {auto_output}\n"
                    "Use --force to overwrite."
                )
                return 1
            err_console.print(f"[yellow]Output file already exists:[/yellow] {auto_output}")
            try:
                confirm = input("Overwrite? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                err_console.print("\nAborted.")
                return 1
            if confirm != "y":
                err_console.print("Aborted.")
                return 0

        args.output_file = auto_output

    # Validate incompatible flag combinations
    if args.check and args.output_file:
        err_console.print(
            "[red]Error:[/red] --check cannot be used with -o (output file)",
            style="red"
        )
        return 1

    if args.check and args.strict:
        err_console.print(
            "[yellow]Warning:[/yellow] --strict is redundant with --check (both exit on errors)",
            style="yellow"
        )

    # Run processing (output_file can be None for stdout)
    fix_mojibake_sample = args.fix_mojibake
    return process_csv(
        input_file=args.input_file,
        encoding=args.encoding,
        output_file=args.output_file,
        force=args.force,
        keep_names=args.keep_names,
        delimiter=args.delimiter,
        skip_rows=args.skip_rows,
        verbose=args.verbose,
        fix_mojibake_sample=fix_mojibake_sample,
        download_remote=args.download_remote,
        strict=args.strict,
        check_only=args.check,
    )


if __name__ == "__main__":
    sys.exit(main())
