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
csv_normalizer input.csv output.csv
```

## Requirements

- Python 3.8+
- chardet (install with: pip install chardet)
- iconv (usually pre-installed on Linux systems)

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
