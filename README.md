[![PyPI version](https://badge.fury.io/py/csvnorm.svg)](https://pypi.org/project/csvnorm/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
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

For ASCII art banner (shown with `--version` and `-V`):

```bash
uv tool install csvnorm[banner]
# or
pip install csvnorm[banner]
```

Example with banner:
```bash
csvnorm --version
# Output:
#   ___________   ______  ____  _________ ___
#  / ___/ ___/ | / / __ \/ __ \/ ___/ __ `__ \
# / /__(__  )| |/ / / / / /_/ / /  / / / / / /
# \___/____/ |___/_/ /_/\____/_/  /_/ /_/ /_/
#
# csvnorm 0.3.1
```

## Purpose

This tool prepares CSV files for **basic exploratory data analysis (EDA)**, not for complex transformations. It focuses on achieving a clean, standardized baseline format that allows you to quickly assess data quality and structure before designing more sophisticated ETL pipelines.

**What it does:**
- Validates CSV structure and reports errors
- Normalizes encoding to UTF-8
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
- **Encoding Normalization**: Auto-detects encoding and converts to UTF-8
- **Error Reporting**: Exports detailed error file for invalid rows

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
| `-o, --output-dir DIR` | Set output directory (default: current dir) |
| `-V, --verbose` | Enable verbose output for debugging |
| `-v, --version` | Show version number |
| `-h, --help` | Show help message |

### Examples

```bash
# Basic usage
csvnorm data.csv

# With semicolon delimiter
csvnorm data.csv -d ';'

# Custom output directory
csvnorm data.csv -o ./output

# Keep original headers
csvnorm data.csv --keep-names

# Force overwrite with verbose output
csvnorm data.csv -f -V
```

### Output

Creates a normalized CSV file in the specified output directory with:
- UTF-8 encoding
- Consistent field delimiters
- Normalized column names (unless `--keep-names` is specified)
- Error report if any invalid rows are found (saved as `{input_name}_reject_errors.csv`)

The tool provides modern terminal output with:
- Progress indicators for multi-step processing
- Color-coded error messages with panels
- Success summary table showing encoding, paths, and settings
- Optional ASCII art banner with `--version` and `-V` verbose mode (requires `pyfiglet`)

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Error (validation failed, file not found, etc.) |

## Requirements

- Python 3.8+
- Dependencies (automatically installed):
  - `charset-normalizer>=3.0.0` - Encoding detection
  - `duckdb>=0.9.0` - CSV validation and normalization
  - `rich>=13.0.0` - Modern terminal output formatting
  - `rich-argparse>=1.0.0` - Enhanced CLI help formatting

Optional extras:
- `[banner]` - ASCII art banner for `--version` and `-V` verbose mode (`pyfiglet>=1.0.0`)
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
prepare_data/
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
