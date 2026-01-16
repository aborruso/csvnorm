# Changelog

## 2026-01-16

- Released v0.3.2 to PyPI and GitHub

## 2026-01-16 (v0.3.2)

### Added
- ASCII art banner now displays with `--version` flag (requires `pyfiglet`)

## 2026-01-16

- Released v0.3.1 to PyPI and GitHub
- Created GitHub release v0.3.1
- Updated DEPLOYMENT.md: specify uv usage instead of pip3 --break-system-packages
- Added GitHub release step (step 7) to DEPLOYMENT.md - required for every version
- Added deployment section to CLAUDE.md
- README: explained [dev] and [banner] extras, updated dev setup to use uv
- Feature: ASCII banner now shows with `--version` flag (requires pyfiglet)

## 2026-01-16 (v0.3.1)

### Changed
- CLI flags: `-k` for `--keep-names`, `-V` for `--verbose`, `-v` for `--version`
- Documentation updated to reflect new short flags

### Breaking Changes
- **Project renamed**: `csv-normalize` → `csvnorm`
  - PyPI package name: `csvnorm`
  - CLI command: `csvnorm` (was `csv_normalize`)
  - Python package: `csvnorm` (was `csv_normalizer`)
  - All imports changed from `from csv_normalizer import ...` to `from csvnorm import ...`

### Repository
- Renamed GitHub repo: `csv-normalize` → `csvnorm`
- Added repository description via gh cli
- Added topics: python, csv, cli, data-validation, etl, duckdb, normalization
- Set homepage URL to PyPI package page
- Created GitHub release v0.3.0
- Added badges to README: MIT License, Python 3.8+
- Fixed DeepWiki badge URL

### Migration Guide
For existing users:
```bash
# Uninstall old package
pip uninstall csv-normalize

# Install new package
pip install csvnorm

# Update scripts: replace csv_normalize with csvnorm
# Update imports: from csv_normalizer → from csvnorm
```

## 2026-01-16 (v0.2.3)

### Changed
- Enhanced CLI help formatting with `rich-argparse`
- Show full help when command run without arguments (instead of error)
- Dependencies: added `rich-argparse>=1.0.0`

## 2026-01-16 (v0.2.2)

### Added
- Modern CLI UX with `rich` library
  - Progress spinner for 4-step pipeline (encoding detection, conversion, validation, normalization)
  - Color-coded error panels (red border)
  - Warning panels (yellow border)
  - Success summary table showing input/output paths, encoding, delimiter, header settings
  - Rich logging with RichHandler (color-coded levels, rich tracebacks)
- Optional ASCII art banner in verbose mode
  - Requires `pyfiglet` (install with `pip install csv-normalize[banner]`)
  - Gracefully degrades if not installed

### Changed
- Replaced all `print()` calls with `rich.Console`
- Enhanced logging output with colors and formatting
- Dependencies: added `rich>=13.0.0` as required
- Dependencies: added `pyfiglet>=1.0.0` as optional `[banner]` extra

### Documentation
- Updated README with modern UX features
- Added DEPLOYMENT.md with release checklist (build, test, tag, twine)
- Updated installation examples to show `uv tool install` and `[banner]` extra

## 2026-01-15

### Breaking Changes
- Complete rewrite from Bash to pure Python
- Version bumped to 0.2.0
- Removed Bash script (`script/prepare.sh`)
- Removed wrapper (`csv_normalizer_wrapper.py`)
- Removed Makefile (use pip install instead)

### Added
- Pure Python CLI package structure (`src/csv_normalizer/`)
- Cross-platform support (no longer Linux-only)
- Python package modules:
  - `cli.py` - argparse-based CLI
  - `core.py` - Main processing pipeline
  - `encoding.py` - charset_normalizer integration
  - `validation.py` - DuckDB validation
  - `utils.py` - Helper functions
- Test suite in `tests/` with pytest
- `--version` CLI option

### Changed
- DuckDB now used as Python library instead of CLI
- Encoding conversion now uses Python codecs instead of iconv
- Installation simplified to `pip install csv-normalizer`

## 2026-01-15

### Changed
- Renamed error report files from `reject_errors.csv` to `{base_name}_reject_errors.csv`
  - Each input file now generates its own uniquely named error report
  - Prevents overwriting error reports when processing multiple CSV files
  - Example: `data.csv` errors saved as `data_reject_errors.csv`

### Documentation
- Clarified README to emphasize tool purpose: preparing CSV for basic EDA, not complex transformations
- Added explicit Linux-only requirement in installation section
- Improved installation guide with clearer dependency information
- Added link to DuckDB releases for manual installation

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
