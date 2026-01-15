[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/aborruso/prepare_data)

# CSV Normalizer

A command-line utility to validate and normalize CSV files for initial exploration.

## Installation

```bash
pip install csv-normalize
```

Or with uv:

```bash
uv pip install csv-normalize
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
csv_normalizer input.csv [options]
```

### Options

| Option | Description |
|--------|-------------|
| `-f, --force` | Force overwrite of existing output files |
| `-n, --keep-names` | Keep original column names (disable snake_case) |
| `-d, --delimiter CHAR` | Set custom output delimiter (default: `,`) |
| `-o, --output-dir DIR` | Set output directory (default: current dir) |
| `-v, --verbose` | Enable verbose output for debugging |
| `--version` | Show version number |
| `-h, --help` | Show help message |

### Examples

```bash
# Basic usage
csv_normalizer data.csv

# With semicolon delimiter
csv_normalizer data.csv -d ';'

# Custom output directory
csv_normalizer data.csv -o ./output

# Keep original headers
csv_normalizer data.csv --keep-names

# Force overwrite with verbose output
csv_normalizer data.csv -f -v
```

### Output

Creates a normalized CSV file in the specified output directory with:
- UTF-8 encoding
- Consistent field delimiters
- Normalized column names (unless `--keep-names` is specified)
- Error report if any invalid rows are found (saved as `{input_name}_reject_errors.csv`)

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

## Development

### Setup

```bash
git clone https://github.com/aborruso/prepare_data
cd prepare_data
pip install -e ".[dev]"
```

### Testing

```bash
pytest tests/ -v
```

### Project Structure

```
prepare_data/
├── src/csv_normalizer/
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
