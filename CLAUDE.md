<!-- OPENSPEC:START -->
# OpenSpec Instructions

These instructions are for AI assistants working in this project.

Always open `@/openspec/AGENTS.md` when the request:
- Mentions planning or proposals (words like proposal, spec, change, plan)
- Introduces new capabilities, breaking changes, architecture shifts, or big performance/security work
- Sounds ambiguous and you need the authoritative spec before coding

Use `@/openspec/AGENTS.md` to learn:
- How to create and apply change proposals
- Spec format and conventions
- Project structure and guidelines

Keep this managed block so 'openspec update' can refresh the instructions.

<!-- OPENSPEC:END -->

# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

csvnorm - A Python CLI tool for validating and normalizing CSV files. Installable via PyPI (`pip install csvnorm`).

## Deployment

For deployment procedures (building, tagging, publishing to PyPI), see `DEPLOYMENT.md`.

**IMPORTANT**: Always use `uv` and the project's `.venv`, never `pip3 --break-system-packages`.

**PRE-RELEASE CHECKLIST**:
- NEVER release if `csvnorm -v` fails (basic smoke test)
- Verify all runtime dependencies are in `pyproject.toml`
- Test installation: `uv tool install --reinstall --force .` then `csvnorm -v`

## Common Commands

### Installation
```bash
pip install csvnorm                  # From PyPI

# Development (use uv and .venv)
source .venv/bin/activate
uv pip install -e ".[dev]"          # Editable install with dev dependencies
```

### Testing
```bash
pytest tests/ -v                    # Run all tests
pytest tests/test_utils.py -v       # Run specific test file
pytest tests/test_cli.py::TestMainFunction::test_skip_rows_metadata -v  # Single test
pytest tests/ -v --cov=csvnorm --cov-report=term  # With coverage
```

### Development
```bash
csvnorm test/utf8_basic.csv              # Basic test (stdout)
csvnorm test/utf8_basic.csv -o out.csv   # Write to file
csvnorm test/latin1_semicolon.csv -V     # Verbose mode
csvnorm input.csv -s 2 -o output.csv     # Skip first 2 rows
csvnorm input.csv --fix-mojibake -o out.csv  # Fix mojibake
```

## Architecture

### Package Structure
```
src/csvnorm/
├── __init__.py      # Version and exports
├── __main__.py      # python -m support
├── cli.py           # argparse CLI with rich formatting
├── core.py          # Main processing pipeline
├── encoding.py      # charset_normalizer integration
├── validation.py    # DuckDB validation/normalization with fallback configs
├── mojibake.py      # ftfy-based mojibake detection/repair
├── ui.py            # Rich panels and tables
└── utils.py         # Helper functions
```

### Processing Flow

**Stdout mode** (default, `csvnorm input.csv`):
1. Encoding detection → UTF-8 conversion (if needed)
2. Optional mojibake repair (if `--fix-mojibake`)
3. Validation → temp reject file
4. Normalization → stdout
5. Progress/errors → stderr

**File mode** (with `-o`, `csvnorm input.csv -o output.csv`):
1. Encoding detection → UTF-8 conversion (if needed)
2. Optional mojibake repair (if `--fix-mojibake`)
3. Validation → reject file in output dir
4. Normalization → output file
5. Success table → stdout

**Remote URLs** (`csvnorm https://example.com/data.csv`):
- DuckDB reads directly via httpfs (30s timeout)
- If `--fix-mojibake`: downloads to temp first, then processes

### Key Modules

**core.py** (`process_csv`):
- Main orchestration of the 4-step pipeline
- Handles stdout vs file mode logic
- Manages temp files and cleanup
- Remote URL detection and download

**validation.py**:
- `validate_csv()` - DuckDB validation with `store_rejects=true`
  - **Early detection**: Pre-checks first 5 lines for header anomalies (local files only)
  - **Fallback mechanism**: Tries common delimiter/skip combinations if auto-detection fails
  - Returns: (reject_count, error_types, fallback_config)
- `normalize_csv()` - DuckDB COPY with `normalize_names=true` (unless `--keep-names`)
  - Uses fallback_config from validation if provided
  - Exports to CSV with specified delimiter

**Fallback mechanism**:
When DuckDB's automatic dialect detection fails, tries these configs in order:
```python
FALLBACK_CONFIGS = [
    {"delim": ";", "skip": 1},
    {"delim": ";", "skip": 2},
    {"delim": "|", "skip": 1},
    {"delim": "|", "skip": 2},
    {"delim": "\t", "skip": 1},
    {"delim": "\t", "skip": 2},
]
```

**encoding.py**:
- `detect_encoding(path)` - charset_normalizer library
- `convert_to_utf8(input, output, encoding)` - Python codecs
- `needs_conversion(encoding)` - Check if encoding ∈ {utf-8, ascii, utf-8-sig}

**mojibake.py**:
- `detect_mojibake(text, sample_size)` - ftfy badness heuristic
- `repair_file(input, output, sample_size)` - Fix mojibake if detected

**ui.py**:
- `show_success_table()` - Rich table with stats (file mode only)
- `show_error_panel()` - Red-bordered error messages
- `show_validation_error_panel()` - Validation error summary with reject count
- `show_warning_panel()` - Yellow-bordered warnings

**utils.py**:
- `to_snake_case(name)` - Filename normalization
- `is_url()`, `validate_url()`, `download_url_to_file()` - URL handling
- `get_row_count()`, `get_column_count()` - DuckDB metadata queries

## Dependencies

**Runtime** (in pyproject.toml):
- `charset-normalizer>=3.0.0` - Encoding detection
- `duckdb>=0.9.0` - CSV validation and normalization
- `ftfy>=6.3.1` - Mojibake repair
- `rich>=13.0.0` - Terminal output formatting
- `rich-argparse>=1.0.0` - Enhanced CLI help

**Development**:
- `pytest>=7.0.0` - Testing
- `pytest-cov>=4.0.0` - Coverage
- `ruff>=0.1.0` - Linting

## Testing

Test fixtures in `test/`:
- `utf8_basic.csv` - Basic UTF-8 file
- `latin1_semicolon.csv` - Non-UTF8 encoding
- `pipe_mixed_headers.csv` - Header normalization
- `malformed_rows.csv` - Error reporting
- `metadata_skip_rows.csv` - Skip rows with metadata
- `title_row_skip.csv` - Skip title row

## Critical Constraints

1. **Cross-platform**: Pure Python, no shell dependencies

2. **Output modes**:
   - Default: stdout (for Unix pipes)
   - With `-o`: file (with rich output)

3. **Exit codes**:
   - 0: Success (even with validation errors in file mode)
   - 1: Fatal error (file not found, invalid args, etc.)

4. **Error handling**:
   - Non-UTF-8 encodings → automatic conversion
   - DuckDB rejects → captured in reject_errors.csv
   - Pre-existing outputs → respect `--force` flag
   - Input file protection → never overwrite input

5. **Simplicity**: Maintain minimal complexity, avoid over-engineering

## File Contract

**Input**: Arbitrary CSV (any encoding, any delimiter, local or HTTP/HTTPS URL)

**Output**:
- Stdout mode: normalized CSV to stdout, reject errors to temp file
- File mode: `<output_path>` + `<output_name>_reject_errors.csv` (if errors exist)
- Always UTF-8, comma-delimited (unless `-d` specified)
- Headers normalized to snake_case (unless `-k/--keep-names`)

## Key Files

- `src/csvnorm/` - Python package
- `tests/` - Test suite (105 tests)
- `test/` - CSV fixtures
- `pyproject.toml` - Package configuration
- `PRD.md` - Product requirements
- `README.md` - User documentation
- `LOG.md` - Changelog
- `DEPLOYMENT.md` - Release procedures
