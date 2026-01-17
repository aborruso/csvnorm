# Changelog

## 2026-01-17

### Early Detection for Header Anomalies

**Enhancement**: Pre-validation mechanism to detect title rows before DuckDB sniffing
- Analyzes first 5 lines to detect separator pattern anomalies
- If line 1 has < 50% of data lines' average delimiter count → anomaly
- Automatically suggests delimiter + skip=1 configuration
- Works for local files only (not remote URLs)

**Benefits**:
- Catches files where DuckDB sampling misses problematic rows
- Handles small files with title rows that don't fail standard sniffing
- Provides early feedback on likely configuration

**Documentation**: `docs/early-detection.md` (technical details)
**PRD update**: Added FR-11 (early detection requirement)

**Results**:
- ✅ Detects title rows in small files (< 100 rows)
- ✅ Automatically processes files like `POSAS_2025_it_Comuni.csv`
- ✅ All 93 tests passing
- ✅ No regression on existing files

## 2026-01-17

### Issue #1: Automatic fallback for CSV with non-standard headers

**Problem**: Files with title rows or non-standard structures fail DuckDB dialect sniffing
- Example: `POSAS_2025_it_Comuni.csv` has title row + semicolon delimiter
- DuckDB unable to detect dialect automatically

**Solution**: Automatic fallback with common delimiter/skip combinations
- No new CLI options (fully automatic)
- Tries `;`, `|`, `\t` delimiters with skip 1-2 rows
- Uses `store_rejects=true` + `ignore_errors=true` for malformed rows
- Produces clean output + `*_reject_errors.csv`

**Implementation**:
- `validation.py`: added `FALLBACK_CONFIGS`, `_try_read_csv_with_config()` helper
- `validate_csv()`: tries fallback configs if standard sniffing fails
- `normalize_csv()`: exports reject_errors when using fallback, returns config used
- `core.py`: handles fallback config propagation and reject_count updates

**Results**:
- ✅ 805,392 valid rows extracted from problematic file
- ✅ 5 malformed rows captured in reject_errors
- ✅ All 93 tests passing
- ✅ No regression on existing files

## 2026-01-17 (v1.0.0)

### BREAKING CHANGE: Stdout by Default

**Major behavior change for better Unix composability:**

- **Default output is now stdout** (was: file in current directory)
  - `csvnorm data.csv` → outputs to stdout
  - `csvnorm data.csv -o output.csv` → writes to file
  - `csvnorm data.csv > output.csv` → shell redirect works

- **Input file overwrite protection**
  - Never allows overwriting input file, even with `--force`
  - Shows clear error message if input == output
  - Suggests using `-o` with different path

- **Behavior changes:**
  - Progress/errors go to stderr when using stdout
  - Success table only shown in file mode
  - Reject files in temp dir for stdout mode
  - `-f/--force` only applies when `-o` specified

**Why this change:**
- Follows Unix philosophy and standard CLI tools (`jq`, `xsv`, `csvkit`)
- Enables pipe chains: `csvnorm data.csv | head | other-tool`
- Preview without creating files: `csvnorm data.csv | less`
- Safer: no accidental file overwrites
- More composable with other tools

**Migration:**
```bash
# v0.x
csvnorm data.csv              # Created file

# v1.0
csvnorm data.csv              # Stdout
csvnorm data.csv -o data.csv  # Explicit file
```

**Technical changes:**
- cli.py: `-o` now optional (None = stdout)
- core.py: stdout mode with temp files, stderr console
- Added tests for stdout and input protection
- Updated README with migration guide

**Fixes:**
- #19: Critical bug preventing input file destruction

## 2026-01-17 (v0.3.12)

- Fixed #14: hide encoding and input size info for remote files (not available/meaningful)
- Clarified ASCII encoding message: "ASCII is UTF-8 compatible; no conversion needed"
- README now states encoding conversion happens only when needed

## 2026-01-16

### Breaking Changes
- **Changed `-o/--output-dir` to `-o/--output-file`** - now accepts full file path instead of directory
  - Old: `csvnorm data.csv -o output_folder/` → `output_folder/data.csv`
  - New: `csvnorm data.csv -o output_folder/data.csv` → `output_folder/data.csv`
  - Default behavior: `csvnorm data.csv` → `data.csv` in current directory
  - Supports both absolute and relative paths
  - User can specify any filename/extension (no .csv validation)
- Reject files placed in same directory as output file, always overwritten
- Temp UTF-8 files moved to system temp directory (`/tmp/csvnorm_xxxxx/`) with auto-cleanup

## 2026-01-16 (v0.3.10)

- Enhanced test coverage with edge cases and error paths
- Added 18 new tests (71 → 89 tests, +25%)
- Coverage improved from 80% → 87% (+7%)
- New test file: tests/test_validation.py
- Test fixtures: empty_file.csv, binary_file.bin
- Module coverage: encoding.py 100%, validation.py 93%

## 2026-01-16

- Enhanced test coverage with edge cases and error paths
  - Added 18 new tests (71 → 89 tests, +25%)
  - Coverage improved from 80% → 87% (+7%)
  - Created test fixtures: empty_file.csv, binary_file.bin
  - New test file: tests/test_validation.py (9 tests)
  - Encoding edge cases: empty files, binary files, unsupported encodings
  - Validation error paths: _count_lines, _get_error_types edge cases
  - Remote URL errors: HTTP 401/403/500, timeout, invalid schemes
  - Module coverage: encoding.py 100%, validation.py 93%
  - Used unittest.mock (no new dependencies)

## 2026-01-16

- Refactored core.py for better separation of concerns
  - Created ui.py module with 4 formatting functions
    - show_error_panel() - consolidated 5+ error panels
    - show_warning_panel() - yellow border warnings
    - show_success_table() - processing summary table
    - show_validation_error_panel() - validation error summary
  - Moved helpers from core.py to utils.py
    - get_row_count() (renamed from _get_row_count)
    - get_column_count() (renamed from _get_column_count)
  - core.py reduced from 386 → 276 lines (-110 lines, -28%)
  - process_csv reduced from 336 → 243 lines (-93 lines, -28%)
  - Coverage maintained at 80% (all 71 tests passing)
  - Module breakdown:
    - core.py: 121 statements, 79% coverage
    - ui.py: 45 statements, 71% coverage (new)
    - utils.py: 71 statements, 86% coverage (expanded)

## 2026-01-16 (v0.3.9)

- Released v0.3.9 to PyPI
- Fixed 3 critical issues and 1 high-priority issue from evaluation
- Coverage improved from 66% to 79%
- Added 16 CLI tests (total: 71 tests)

## 2026-01-16

- Added comprehensive CLI tests (tests/test_cli.py) - hybrid approach
  - 13 tests for main() function with argv mocking (fast, isolated)
  - 3 subprocess smoke tests (end-to-end validation)
  - Test coverage: --version, --help, flags (force, delimiter, keep-names, verbose)
  - Fixed test_help_flag to not expect SystemExit
  - cli.py coverage: 0% → 96% (48 statements, only 2 missed)
  - Overall coverage: 66% → 79% (+13 points)
  - Total tests: 55 → 71 (+16 CLI tests)
  - utils.py coverage improved: 80% → 92% (side effect of CLI tests)

## 2026-01-16

- Added coverage reporting to CI/CD (problem 6 from evaluation)
  - Modified .github/workflows/publish-pypi.yml to use pytest --cov
  - Added --cov=csvnorm --cov-report=term --cov-report=xml
  - Added coverage files to .gitignore (.coverage, coverage.xml, htmlcov/)
  - Initial coverage baseline: 66% (379 statements, 130 missed)
  - Breakdown: core.py 74%, encoding.py 88%, utils.py 80%, validation.py 67%
  - Gap identified: cli.py 0% (no direct CLI tests)

## 2026-01-16

- Updated PRD.md to reflect Python implementation (problem 4 from evaluation)
  - Replaced Bash references with Python 3.9+
  - Updated FR-2, FR-3: charset_normalizer + Python codecs (removed iconv)
  - Updated NFR-3: cross-platform Python instead of Bash
  - Updated NFR-4: ruff/pytest instead of shellcheck
  - Added remote URL support to in-scope features
  - Updated constraints: removed iconv, added Python dependencies
  - Updated future work: removed PyPI publishing (already done)

## 2026-01-16

- Fixed delimiter bug in column counting (core.py:379)
  - _get_column_count() now uses DuckDB DESCRIBE instead of hardcoded comma split
  - Correctly counts columns for non-comma delimiters (semicolon, pipe, tab)
  - Tested with semicolon and pipe delimiters
- Fixed Python version mismatch in pyproject.toml
  - Removed Python 3.8 classifier (requires-python is >=3.9)
  - Aligned classifiers with actual requirement

## 2026-01-16

- Fixed version drift: aligned __init__.py to 0.3.8 (was 0.3.7, now matches pyproject.toml)
- Verified csvnorm -v shows correct version 0.3.8

## 2026-01-16

- Created comprehensive project evaluation in docs/evaluation.md
- Overall assessment: 85/100
- Identified 3 critical issues: version drift, missing pyfiglet dependency, delimiter bug
- Identified 3 high-priority items for v0.4.0

## 2026-01-16 (v0.3.6)

- Released v0.3.6
- Pinned pyfiglet to >=0.8.post1,<1.0.0 to avoid missing 1.0.0 release on PyPI
- Registered pytest "network" marker to silence warnings

## 2026-01-16

- Added comprehensive processing summary after CSV completion
- Enhanced success table with statistics: rows, columns, input/output file sizes
- Display encoding conversion status (converted/no conversion/remote)
- Added error summary panel with reject count and sample error types when validation fails
- Both success table and error panel displayed when validation errors exist
- File sizes formatted in human-readable format (KB/MB/GB)
- Utility function `format_file_size()` added to utils.py
- Validation now returns reject count and error types instead of boolean

## 2026-01-16

- Added remote URL support for HTTP/HTTPS CSV files
- csvnorm now accepts URLs as input (e.g., `csvnorm https://example.com/data.csv`)
- DuckDB reads URLs directly via httpfs extension (30s timeout)
- URL encoding (%20, etc.) is decoded for output filenames
- Error handling for HTTP 404, 401/403, timeout
- Only public URLs supported (no authentication)
- Added URL validation utilities: `is_url()`, `validate_url()`, `extract_filename_from_url()`
- Added 20 new tests for URL functionality
- Updated README with remote URL examples

## 2026-01-16

- Released v0.3.3 to PyPI and GitHub
- Restored ASCII banner as core feature by adding pyfiglet to main dependencies
- ASCII banner now always displays with `--version` flag

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
