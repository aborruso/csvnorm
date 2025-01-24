# CSV Normalizer Utility

A command-line utility to validate and normalize CSV files.

## Features

- **CSV Validation**: Checks for common CSV errors and inconsistencies
- **Delimiter Normalization**: Converts all field separators to standard commas (`,`)
- **Field Name Normalization**: Converts column headers to snake_case format
- **Encoding Normalization**: Ensures UTF-8 encoding for proper character handling
- **Error Reporting**: Provides detailed error messages for invalid CSV files

## Usage

```bash
csv_normalizer input.csv [options]

Options:
  -f, --force         Force overwrite of existing output files
  -n, --no-normalize  Keep original column names (disable snake_case normalization)
                     By default, column names are converted to snake_case format
                     (e.g., "Column Name" becomes "column_name"). Use this option
                     to preserve the original column names as they appear in the
                     input file.
  -d, --delimiter     Set custom field delimiter (default: comma)
                     Example: -d ';' for semicolon-delimited files
                     Example: -d $'\t' for tab-delimited files
                     Example: -d '|' for pipe-delimited files
  -o, --output-dir    Set custom output directory (default: ./tmp)
                     Example: -o ./output to save files in ./output directory
  -v, --verbose       Enable verbose output for debugging
  -h, --help          Show this help message and exit

Output:
  Creates a normalized CSV file in the specified output directory with:
  - UTF-8 encoding
  - Consistent field delimiters
  - Normalized column names (unless --no-normalize is specified)
  - Error report if any invalid rows are found
```

## Requirements

- Python 3.8+
- chardet (install with: pip install chardet)
- iconv (usually pre-installed on Linux systems)
- DuckDB (install with: pip install duckdb)
- Bash 4.0+ (for script execution)
- Coreutils (standard on Linux systems)

## Installation

1. Clone the repository
2. Install the package:

```bash
pip install .
```

## Contributing

Contributions are welcome! Please follow these guidelines:
- Fork the repository
- Create a feature branch
- Submit a pull request

## License

MIT License - See LICENSE file for details
