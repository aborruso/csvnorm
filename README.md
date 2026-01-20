[![PyPI version](https://badge.fury.io/py/csvnorm.svg)](https://pypi.org/project/csvnorm/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/aborruso/csvnorm)

# csvnorm

A command-line utility to validate and normalize CSV files for initial exploration.

## Version 1.0 Breaking Change

**If upgrading from v0.x:** The default output has changed from file to stdout for better Unix composability.

```bash
# v0.x behavior
csvnorm data.csv              # Created data.csv in current directory

# v1.0 behavior (NEW)
csvnorm data.csv              # Outputs to stdout
csvnorm data.csv -o data.csv  # Explicitly save to file
csvnorm data.csv > data.csv   # Or use shell redirect
```

This follows the Unix philosophy and matches tools like `jq`, `csvkit`, and `xsv`.

## Installation

Recommended (uv):

```bash
uv tool install csvnorm
```

Or with pip:

```bash
pip install csvnorm
```

## Purpose

This tool prepares CSV files for **basic exploratory data analysis (EDA)**, not for complex transformations. It focuses on achieving a clean, standardized baseline format that allows you to quickly assess data quality and structure before designing more sophisticated ETL pipelines.

**What it does:**
- Validates CSV structure and reports errors
- Normalizes encoding to UTF-8 when needed
- Normalizes delimiters and field names
- Creates a consistent starting point for data exploration

**What it doesn't do:**
- Complex data transformations or business logic
- Type inference or data validation beyond structure
- Heavy processing or aggregations

## Features

- **CSV Validation**: Checks for common CSV errors and inconsistencies using DuckDB
- **Delimiter Normalization**: Converts all field separators to standard commas (`,`)
- **Field Name Normalization**: Converts column headers to snake_case format
- **Encoding Normalization**: Auto-detects encoding and converts to UTF-8 when needed (ASCII is already UTF-8 compatible)
- **Processing Summary**: Displays comprehensive statistics (rows, columns, file sizes) and error details
- **Error Reporting**: Exports detailed error file for invalid rows with summary panel
- **Remote URL Support**: Process CSV files directly from HTTP/HTTPS URLs without downloading (unless `--fix-mojibake` is used)

## Usage

```bash
csvnorm input.csv [options]
```

**By default, csvnorm writes to stdout** for easy piping and composability with other Unix tools.

### Options

| Option | Description |
|--------|-------------|
| `-o, --output-file PATH` | Write to file instead of stdout |
| `-f, --force` | Force overwrite of existing output file (when `-o` is specified) |
| `-k, --keep-names` | Keep original column names (disable snake_case) |
| `-d, --delimiter CHAR` | Set custom output delimiter (default: `,`) |
| `-s, --skip-rows N` | Skip first N rows of input file (useful for metadata/comments) |
| `--fix-mojibake [N]` | Fix mojibake using ftfy (optional sample size `N`; use `0` to force repair) |
| `--download-remote` | Download remote CSV locally before processing (needed for remote .zip/.gz) |
| `-V, --verbose` | Enable verbose output for debugging |
| `-v, --version` | Show version number |
| `-h, --help` | Show help message |

### Examples

```bash
# Default: output to stdout
csvnorm data.csv

# Preview first rows
csvnorm data.csv | head -20

# Pipe to other tools
csvnorm data.csv | csvcut -c name,age | csvstat

# Save to file
csvnorm data.csv -o output.csv

# Shell redirect
csvnorm data.csv > output.csv

# Process remote CSV from URL
csvnorm "https://raw.githubusercontent.com/aborruso/csvnorm/refs/heads/main/test/Trasporto%20Pubblico%20Locale%20Settore%20Pubblico%20Allargato%20-%20Indicatore%202000-2020%20Trasferimenti%20Correnti%20su%20Entrate%20Correnti.csv" -o output.csv

# Process remote compressed CSV (download first, then handle gzip/zip locally)
csvnorm "https://example.com/data.csv.gz" --download-remote -o output.csv

# Custom delimiter
csvnorm data.csv -d ';' -o output.csv

# Keep original headers
csvnorm data.csv --keep-names -o output.csv

# Skip first 2 rows (metadata or comments)
csvnorm data.csv --skip-rows 2 -o output.csv

# Force overwrite with verbose output
csvnorm data.csv -f -V -o processed.csv

# Fix mojibake using ftfy (default sample size)
csvnorm data.csv --fix-mojibake -o fixed.csv

# Fix mojibake with custom sample size
csvnorm data.csv --fix-mojibake 4000 -o fixed.csv

# Force mojibake repair even with low badness score
csvnorm data.csv --fix-mojibake 0 -o fixed.csv
```

### Output

**Default behavior (stdout):**
- Writes normalized CSV to stdout
- Progress and errors go to stderr
- Validation errors (if any) are written to a temporary file with path shown in stderr
- Perfect for piping to other tools or shell redirection

**File output (with `-o`):**
- Creates a normalized CSV file at the specified path with:
  - UTF-8 encoding
  - Consistent field delimiters
  - Normalized column names (unless `--keep-names` is specified)
- Error report if any invalid rows are found (saved as `{output_name}_reject_errors.csv` in the same directory)
- Shows success table with statistics (rows, columns, file sizes)
- Supports absolute and relative paths
- Any file extension is allowed (not limited to `.csv`)

**Input file protection:**
- csvnorm will **never** overwrite the input file, even with `--force`
- If you try to use the same path for input and output, you'll get an error
- Use `-o` to specify a different output path

**Remote URLs:**
- Encoding is handled automatically by DuckDB
- If `--fix-mojibake` is enabled, the URL is downloaded to a temp file first

**Mojibake repair (`--fix-mojibake [N]`):**
- Mojibake is garbled text produced by decoding bytes with the wrong character encoding (e.g., `CittÃ ` instead of `Città`).
- Enables optional mojibake repair using ftfy (for already-misdecoded text).
- `N` is the sample size (number of characters) used by the detector; default is 5000.
- The repair runs only when ftfy's badness heuristic flags the sample as "bad."
- Use `N=0` to force repair without detection (useful for files with low badness scores but visible mojibake).
- **Note**: ftfy cannot recover bytes that were irreversibly lost in the original encoding. Replacement characters (`�`) may remain where data was corrupted beyond repair.
- HTTP timeout is set to 30 seconds
- Only public URLs are supported (no authentication)

The tool provides modern terminal output (shown only when using `-o` to write to a file) with:
- Progress indicators for multi-step processing
- Color-coded error messages with panels
- Success summary table with statistics (rows, columns, file sizes)
- Encoding conversion status (converted/no conversion/remote; ASCII is already UTF-8 compatible)
- Error summary panel with reject count and error types when validation fails
- ASCII art banner with `--version` and `-V` verbose mode

**Success Example:** (shown only when using `-o`)
```
 ✓ Success
 Input:        test/utf8_basic.csv
 Output:       output/utf8_basic.csv
 Encoding:     ascii (ASCII is UTF-8 compatible; no conversion needed)
 Rows:         2
 Columns:      3
 Input size:   42 B
 Output size:  43 B
 Headers:      normalized to snake_case
```

**Error Example:** (shown only when using `-o`)
```
 ✓ Success
 Input:        test/malformed_rows.csv
 Output:       output/malformed_rows.csv
 Encoding:     ascii (ASCII is UTF-8 compatible; no conversion needed)
 Rows:         1
 Columns:      4
 Input size:   24 B
 Output size:  40 B
 Headers:      normalized to snake_case

╭──────────────────────────── ! Validation Failed ─────────────────────────────╮
│ Validation Errors:                                                           │
│                                                                              │
│ Rejected rows: 2                                                             │
│                                                                              │
│ Error types:                                                                 │
│   • Expected Number of Columns: 3 Found: 2                                   │
│   • Expected Number of Columns: 3 Found: 4                                   │
│                                                                              │
│ Details: output/malformed_rows_reject_errors.csv                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (validation failed, file not found, etc.) |

## Requirements

- Python 3.9+
- Dependencies (automatically installed):
  - `charset-normalizer>=3.0.0` - Encoding detection
  - `duckdb>=0.9.0` - CSV validation and normalization
  - `ftfy>=6.3.1` - Mojibake repair
  - `rich>=13.0.0` - Modern terminal output formatting
  - `rich-argparse>=1.0.0` - Enhanced CLI help formatting

Optional extras:
- `[dev]` - Development dependencies (`pytest>=7.0.0`, `pytest-cov>=4.0.0`, `ruff>=0.1.0`)

## Development

### Setup

```bash
git clone https://github.com/aborruso/csvnorm
cd csvnorm

# Create and activate venv with uv (recommended)
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Or with pip
pip install -e ".[dev]"
```

### Testing

```bash
pytest tests/ -v
```

### Project Structure

```
csvnorm/
├── src/csvnorm/
│   ├── __init__.py      # Package version
│   ├── __main__.py      # python -m support
│   ├── cli.py           # CLI argument parsing
│   ├── core.py          # Main processing pipeline
│   ├── encoding.py      # Encoding detection/conversion
│   ├── validation.py    # DuckDB validation
│   └── utils.py         # Helper functions
├── tests/               # Test suite
├── test/                # CSV fixtures
└── pyproject.toml       # Package configuration
```

## Stay Updated

### Get notified of new releases
**Watch → Custom → ✓ Releases** to receive notifications for all new versions.

### Get notified of breaking changes only
**[Subscribe to Announcements](https://github.com/aborruso/csvnorm/discussions/categories/announcements)** to be notified only about:
- Breaking changes (major version bumps)
- Security updates
- Important deprecation notices

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR** (e.g., 1.0.0 → 2.0.0): Breaking changes
- **MINOR** (e.g., 1.0.0 → 1.1.0): New features, backward compatible
- **PATCH** (e.g., 1.0.0 → 1.0.1): Bug fixes only

See [docs/COMMUNICATION.md](docs/COMMUNICATION.md) for details.

## License

MIT License (c) 2026 aborruso@gmail.com - See LICENSE file for details
