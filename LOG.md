# Changelog

## [1.1.0] - 2025-01-25

### Added
- Improved error handling
  - SIGPIPE (141) handling for chardetect
  - Fallback encoding detection using file command
  - Case-insensitive encoding validation
  - Better error reporting and debugging

## [1.0.0] - 2025-01-24

### Added
- Initial release of CSV Normalizer Utility
- Core features:
  - CSV validation and error reporting
  - Encoding normalization to UTF-8
  - Field delimiter normalization
  - Column name normalization to snake_case
  - Custom output directory support
  - Force overwrite option
  - Verbose output option

### Requirements
- Python 3.8+
- DuckDB
- chardet
- iconv
- file (fallback encoding detection)

### Known Issues
- Large files (>1GB) may require additional memory
- Complex CSV structures may need manual verification
- Temporary files cleanup might fail on Windows systems
