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
- chardet (automatically installed via make)
- iconv (usually pre-installed on Linux systems)
- DuckDB (automatically installed via make)
- curl and unzip (for downloading DuckDB CLI)

## Development

### Available Make Targets

- `make install` - Install the utility and dependencies
- `make uninstall` - Remove the installed utility
- `make test` - Run tests to verify functionality
- `make check` - Verify all dependencies are installed
- `make clean` - Remove temporary files
- `make help` - Show available targets

### Testing

Run the test suite:
```bash
make test
```

### Cleaning

Remove temporary files:
```bash
make clean
```

## Installation

### Option 1: Using Makefile (Recommended)

1. Clone the repository:
```bash
git clone <repository-url>
cd prepare_data
```

2. Install using make:
```bash
make install
```

This will:
- Install required Python dependencies (chardet, duckdb)
- Download and install the DuckDB CLI tool
- Install the `csv_normalizer` command globally

For custom installation directory:
```bash
make install PREFIX=~/.local  # Install to ~/.local/bin
```

3. Verify installation:
```bash
make check
csv_normalizer --help
```

4. To uninstall:
```bash
make uninstall
```

### Option 2: Manual Installation

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
