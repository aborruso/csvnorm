[![PyPI version](https://badge.fury.io/py/csvnorm.svg)](https://pypi.org/project/csvnorm/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/aborruso/csvnorm)

# csvnorm

A command-line utility to validate and normalize CSV files for initial exploration.

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
- **Remote URL Support**: Process CSV files directly from HTTP/HTTPS URLs without downloading

## Usage

```bash
csvnorm input.csv [options]
```

### Options

| Option | Description |
|--------|-------------|
| `-f, --force` | Force overwrite of existing output files |
| `-k, --keep-names` | Keep original column names (disable snake_case) |
| `-d, --delimiter CHAR` | Set custom output delimiter (default: `,`) |
| `-o, --output-file PATH` | Set output file path (absolute or relative) |
| `-V, --verbose` | Enable verbose output for debugging |
| `-v, --version` | Show version number |
| `-h, --help` | Show help message |

### Examples

```bash
# Basic usage (output: data.csv in current directory)
csvnorm data.csv

# Specify output file path
csvnorm data.csv -o output/processed.csv

# Use absolute path
csvnorm data.csv -o /tmp/data_normalized.csv

# Process remote CSV from URL
csvnorm "https://raw.githubusercontent.com/aborruso/csvnorm/refs/heads/main/test/Trasporto%20Pubblico%20Locale%20Settore%20Pubblico%20Allargato%20-%20Indicatore%202000-2020%20Trasferimenti%20Correnti%20su%20Entrate%20Correnti.csv" -o output.csv

# With semicolon delimiter
csvnorm data.csv -d ';' -o data_semicolon.csv

# Keep original headers
csvnorm data.csv --keep-names -o output.csv

# Force overwrite with verbose output
csvnorm data.csv -f -V -o processed.csv

# Custom output name and extension
csvnorm data.csv -o results.txt
```

### Output

Creates a normalized CSV file at the specified path with:
- UTF-8 encoding
- Consistent field delimiters
- Normalized column names (unless `--keep-names` is specified)
- Error report if any invalid rows are found (saved as `{output_name}_reject_errors.csv` in the same directory)
- Temporary encoding conversion files stored in system temp directory with auto-cleanup

Output file path behavior:
- If `-o` is specified: uses the exact path provided (supports absolute and relative paths)
- If `-o` is omitted: uses input filename in current working directory
- Any file extension is allowed (not limited to `.csv`)

For remote URLs:
- You must specify `-o` to set the output filename
- Encoding is handled automatically by DuckDB
- HTTP timeout is set to 30 seconds
- Only public URLs are supported (no authentication)

The tool provides modern terminal output with:
- Progress indicators for multi-step processing
- Color-coded error messages with panels
- Success summary table with statistics (rows, columns, file sizes)
- Encoding conversion status (converted/no conversion/remote; ASCII is already UTF-8 compatible)
- Error summary panel with reject count and error types when validation fails
- ASCII art banner with `--version` and `-V` verbose mode

**Success Example:**
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

**Error Example:**
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
  - `rich>=13.0.0` - Modern terminal output formatting
  - `rich-argparse>=1.0.0` - Enhanced CLI help formatting
  - `pyfiglet>=0.8.post1,<1.0.0` - ASCII art banner

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

## License

MIT License (c) 2026 aborruso@gmail.com - See LICENSE file for details
