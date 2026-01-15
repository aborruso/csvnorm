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

CSV Normalizer - A Python CLI tool for validating and normalizing CSV files. Installable via PyPI (`pip install csv-normalize`).

## Common Commands

### Installation
```bash
pip install csv-normalize           # From PyPI
pip install -e .                    # Editable install for development
pip install -e ".[dev]"             # With dev dependencies
```

### Testing
```bash
pytest tests/ -v                    # Run all tests
pytest tests/test_utils.py -v       # Run specific test file
```

### Development
```bash
csv_normalize test/utf8_basic.csv              # Basic test
csv_normalize test/latin1_semicolon.csv -d ';' # Non-UTF8 + delimiter
csv_normalize input.csv -f -v                  # Force + verbose
csv_normalize input.csv -n                     # Keep original names
csv_normalize input.csv -o ./output            # Custom output dir
```

## Architecture

### Package Structure
```
src/csv_normalizer/
├── __init__.py      # Version and exports
├── __main__.py      # python -m support
├── cli.py           # argparse CLI
├── core.py          # Main processing pipeline
├── encoding.py      # charset_normalizer integration
├── validation.py    # DuckDB validation/normalization
└── utils.py         # snake_case, logging helpers
```

### Processing Flow
1. **Encoding detection**: `charset_normalizer.from_path()` library call
2. **Encoding conversion**: Python codecs (only if encoding ≠ utf-8/ascii/utf-8-sig)
3. **Validation**: DuckDB `read_csv(store_rejects=true, sample_size=-1, all_varchar=true)`
4. **Normalization**: DuckDB `COPY` with `normalize_names=true` (unless `--keep-names`)
5. **Output**: UTF-8 CSV to `<output_dir>/<snake_cased_name>.csv`

### Key Modules

**encoding.py**:
- `detect_encoding(path)` - Uses charset_normalizer library
- `convert_to_utf8(input, output, encoding)` - Python codec conversion
- `needs_conversion(encoding)` - Check if UTF-8 conversion needed

**validation.py**:
- `validate_csv(path, reject_file)` - DuckDB validation with store_rejects
- `normalize_csv(input, output, delimiter, normalize_names)` - DuckDB normalization

**core.py**:
- `process_csv()` - Main pipeline orchestrating all steps

**utils.py**:
- `to_snake_case(name)` - Filename normalization
- `setup_logger(verbose)` - Logging configuration

## Dependencies

**Runtime** (in pyproject.toml):
- `charset-normalizer>=3.0.0` - Encoding detection
- `duckdb>=0.9.0` - CSV validation and normalization

**Development**:
- `pytest>=7.0.0` - Testing
- `ruff>=0.1.0` - Linting

## Testing

Run tests:
```bash
pytest tests/ -v
```

Test fixtures in `test/`:
- `utf8_basic.csv` - Basic UTF-8 file
- `latin1_semicolon.csv` - Non-UTF8 encoding
- `pipe_mixed_headers.csv` - Header normalization test
- `malformed_rows.csv` - Error reporting test

## Critical Constraints

1. **Cross-platform**: Pure Python, no shell dependencies

2. **Exit codes**:
   - 0: Success
   - 1: Error (validation failed, file not found, etc.)

3. **Error handling**:
   - Non-UTF-8 encodings
   - DuckDB rejects (malformed rows)
   - Pre-existing outputs (respect `--force` flag)

4. **Simplicity**: Maintain minimal complexity

## File Contract

**Input**: Arbitrary CSV (any encoding, any delimiter)

**Output**:
- `<output_dir>/<clean_name>.csv` (UTF-8, comma-delimited by default)
- `<output_dir>/<clean_name>_reject_errors.csv` (if DuckDB finds invalid rows)

## Key Files

- `src/csv_normalizer/` - Python package
- `tests/` - Test suite
- `test/` - CSV fixtures
- `pyproject.toml` - Package configuration
- `PRD.md` - Product requirements
- `README.md` - User documentation
- `LOG.md` - Changelog
