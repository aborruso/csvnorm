# Changelog

## 2026-01-15

### Changed
- Renamed error report files from `reject_errors.csv` to `{base_name}_reject_errors.csv`
  - Each input file now generates its own uniquely named error report
  - Prevents overwriting error reports when processing multiple CSV files
  - Example: `data.csv` errors saved as `data_reject_errors.csv`

## 2026-01-15

### Added
- Python packaging support via `pyproject.toml`
  - Enables `pip install -e .` for development installations
  - Added `csv_normalizer_wrapper.py` to execute bash script from Python entry point
  - Declared dependencies: charset-normalizer (required), duckdb (optional dev)
  - Package name: `csv-normalizer`, version 0.1.0
- Created `MANIFEST.in` to include script files in distribution

### Changed
- Replaced chardet-based encoding detection with charset_normalizer via `normalizer --minimal`
- Implemented `-v/--verbose` to emit debug logs on demand
- Added basic input validation and dependency checks before processing
- Updated README installation instructions to clarify editable install requirement
- Defaulted DuckDB CSV reads to `all_varchar=true` to avoid type inference failures
- Renamed `--no-normalize` to `--keep-names` for header-only behavior
- Default output directory is now the current working directory; existing outputs stop unless `--force` is used

### Documentation
- Filled out `openspec/project.md` with comprehensive project context
  - Tech stack, architecture patterns, dependencies
  - Code style conventions, testing strategy
  - Domain context for CSV/ETL workflows
  - Constraints and performance targets
- Updated README Option 2 to reflect editable install requirement and uv support

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
