"""Command-line interface for csvnorm."""

import argparse
import codecs
import sys
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich_argparse import RawDescriptionRichHelpFormatter

from importlib.metadata import version
from csvnorm.core import EXIT_ERROR, process_csv
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
        if not console.is_terminal:
            print(f"csvnorm {version('csvnorm')}")
            parser.exit()
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


_DESCRIPTION = """\
Validate and normalize one CSV file for exploratory data analysis.

csvnorm reads a CSV (local file, http/https URL, .zip, .gz, or - for stdin)
and writes a clean copy:
  1. text converted to UTF-8 (encoding detected, or declared with -e)
  2. every row checked with DuckDB; rows it cannot parse (wrong number of
     fields, broken quotes) are left out and listed in a reject file
  3. accepted rows written comma-separated (or -d), with snake_case header
     names (unless -k); LF line endings, CRLF kept with -o if the input has it

Values are copied as text, unchanged: no type conversion, trimming or
deduplication. No filters, joins or column selection.
"""

_EPILOG = """
Start here:
  csvnorm data.csv --check            validate only (exit 0 valid, 1 rows rejected)
  csvnorm data.csv | head -5          preview the normalized CSV
  csvnorm data.csv -o clean.csv       write it to a file, with a summary

Output:
  default (stdout)  normalized CSV on stdout; summary, warnings and errors on
                    stderr; reject file in the system temp directory, its path
                    printed on stderr ("Details: ...")
  -o FILE / -O      the file; summary on stdout; reject file
                    <output_name>_reject_errors.csv next to it
  Summary fields: Encoding (detected → UTF-8, or "declared"), Rows (data rows
  written, header excluded), Columns, Rejected rows, input and output size.
  Reject file: one row per rejected line (DuckDB reject table); main columns
  line, column_name, error_type, error_message.

Exit codes:
  0  clean: every row accepted
  1  rows rejected; the accepted rows are still written, unless --strict
  2  could not complete: invalid option, missing file, download failed,
     undecodable encoding, disk full; no output is written

Limits and side effects:
  - URLs are always downloaded to a temporary file first (30 s network timeout)
  - temporary files need free space up to about twice the input size; they
    are removed at the end. -o writes atomically: no partial file on failure
  - above 50 MiB the encoding is detected on a sample: Turkish, Polish,
    Baltic or Hungarian text can come out wrong with exit 0. Check accented
    characters, or declare the encoding with -e
  - -O writes next to the input; an existing output is never overwritten
    without -f

Encoding names (-e):
  any Python text codec or alias: cp1252, latin-1, cp850, cp1250, cp1254, utf-8
  full list: https://docs.python.org/3/library/codecs.html#standard-encodings
  offline:   python3 -c "import encodings.aliases as a; print(sorted(set(a.aliases.values())))"

Examples:
  csvnorm data.csv -e cp1252 -o out.csv        declared input encoding
  csvnorm data.csv -s 2 -o out.csv             skip 2 metadata rows before the header
  csvnorm data.csv -d ';' -k -o out.csv        ';' output, original header names
  csvnorm data.csv --strict -o out.csv         no output if any row is rejected
  cat data.csv | csvnorm - > out.csv           stdin to stdout
  csvnorm https://example.com/data.csv.gz -o out.csv

Docs: https://github.com/aborruso/csvnorm#readme
"""


def create_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser."""
    parser = argparse.ArgumentParser(
        prog="csvnorm",
        description=_DESCRIPTION,
        formatter_class=RawDescriptionRichHelpFormatter,
        epilog=_EPILOG,
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
        help='Overwrite an existing output file (-o, -O)',
    )

    parser.add_argument(
        "-k",
        "--keep-names",
        action="store_true",
        help="Keep the original header names (default: snake_case, 'Column Name' becomes 'column_name')",
    )

    parser.add_argument(
        "-d",
        "--delimiter",
        default=",",
        metavar="CHAR",
        help="Output field delimiter, one character (default: comma). Example: -d ';'",
    )

    parser.add_argument(
        "-e",
        "--encoding",
        metavar="NAME",
        help="Declare the input encoding and skip detection; no fallback, an undecodable byte exits 2. Valid names: see 'Encoding names' below. Example: -e cp1252",
    )

    parser.add_argument(
        "-s",
        "--skip-rows",
        type=int,
        metavar="N",
        default=0,
        help='Skip N lines before the header row (titles, metadata). Example: -s 2',
    )

    parser.add_argument(
        "-o",
        "--output-file",
        type=Path,
        metavar="FILE",
        help='Write to FILE instead of stdout',
    )

    parser.add_argument(
        "-O",
        "--auto-output",
        action="store_true",
        help='Write to <input_dir>/<input_name_in_snake_case>.csv; if it exists, asks on a terminal, otherwise exits 2 (use -f)',
    )

    parser.add_argument(
        "--fix-mojibake",
        nargs="?",
        const=DEFAULT_MOJIBAKE_SAMPLE,
        type=int,
        metavar="N",
        help="Repair mojibake (e.g. 'CittÃ ' to 'Città') with ftfy; N = characters sampled to decide (default 5000), 0 = always repair",
    )

    parser.add_argument(
        "--download-remote",
        action="store_true",
        help='Deprecated, no effect: URLs are always downloaded',
    )

    parser.add_argument(
        "--strict",
        action="store_true",
        help='Write no output at all if any row is rejected (exit 1)',
    )

    parser.add_argument(
        "--check",
        action="store_true",
        help='Validate only, write nothing (exit 0 valid, 1 rows rejected)',
    )

    parser.add_argument(
        "-V",
        "--verbose",
        action="store_true",
        help='Debug log on stderr; full traceback on unexpected errors',
    )

    parser.add_argument(
        "-v",
        "--version",
        action=VersionAction,
        nargs=0,
        help="Show the version (one line when not on a terminal)",
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
        return 0 if argv else EXIT_ERROR

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
            return EXIT_ERROR

    if args.skip_rows < 0:
        err_console.print("[red]Error:[/red] --skip-rows must be 0 or a positive number", style="red")
        return EXIT_ERROR

    # Resolve --auto-output into output_file
    if args.auto_output:
        if args.output_file:
            err_console.print("[red]Error:[/red] -O/--auto-output cannot be used with -o; use one of them", style="red")
            return EXIT_ERROR
        if args.input_file == "-":
            err_console.print("[red]Error:[/red] -O/--auto-output cannot be used with stdin input; use -o FILE", style="red")
            return EXIT_ERROR
        if args.input_file.startswith("http://") or args.input_file.startswith("https://"):
            err_console.print("[red]Error:[/red] -O/--auto-output cannot be used with URL input; use -o FILE", style="red")
            return EXIT_ERROR

        input_path = Path(args.input_file)
        snake_stem = to_snake_case(input_path.stem)
        auto_output = input_path.parent / f"{snake_stem}.csv"

        if auto_output.resolve() == input_path.resolve():
            err_console.print(
                f"[yellow]Warning:[/yellow] filename is already in snake_case ({input_path.name}). "
                "Use -o to specify a different output path.",
                style="yellow",
            )
            return EXIT_ERROR

        if auto_output.exists() and not args.force:
            if not sys.stdin.isatty():
                err_console.print(
                    f"[red]Error:[/red] Output file already exists: {auto_output}\n"
                    "Use --force to overwrite."
                )
                return EXIT_ERROR
            err_console.print(f"[yellow]Output file already exists:[/yellow] {auto_output}")
            try:
                confirm = input("Overwrite? [y/N] ").strip().lower()
            except (EOFError, KeyboardInterrupt):
                err_console.print("\nAborted.")
                return EXIT_ERROR
            if confirm != "y":
                err_console.print("Aborted.")
                return 0

        args.output_file = auto_output

    # Validate incompatible flag combinations
    if args.check and args.output_file:
        err_console.print(
            "[red]Error:[/red] --check writes nothing, so it cannot be used with -o; drop one of them",
            style="red"
        )
        return EXIT_ERROR

    if args.check and args.strict:
        err_console.print(
            "[yellow]Warning:[/yellow] --strict is redundant with --check (both exit on errors)",
            style="yellow"
        )

    # Run processing (output_file can be None for stdout)
    fix_mojibake_sample = args.fix_mojibake
    try:
        return _run(args, fix_mojibake_sample)
    except KeyboardInterrupt:
        err_console.print("Error: interrupted")
        return EXIT_ERROR
    except Exception as e:  # noqa: BLE001 - exit 1 is reserved for rejected rows
        if args.verbose:
            err_console.print_exception()
        err_console.print(
            f"Error: unexpected failure: {type(e).__name__}: {e}\n"
            "Run again with -V for the full traceback."
        )
        return EXIT_ERROR


def _run(args: argparse.Namespace, fix_mojibake_sample: Optional[int]) -> int:
    """Call process_csv with the parsed arguments."""
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
