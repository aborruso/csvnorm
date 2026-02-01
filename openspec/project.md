# Project Context

## Purpose

CSV Normalizer Utility - A command-line tool that validates and normalizes CSV files for exploratory data analysis and quick pipeline checks.

**Core Goals**:
- Accept raw CSV files with inconsistent encodings, delimiters, and headers
- Output fully normalized UTF-8 CSV (comma-delimited by default)
- Detect and report structural/encoding errors early
- Integrate seamlessly into shell scripts and CI pipelines (stdout-first by default)
- Support CSV inputs from local files and HTTP/HTTPS URLs
- Support datasets up to 1 GB on commodity hardware

**Target Users**:
- Data Engineers: batch-process CSVs in CI pipelines
- Data Analysts: quickly clean files before importing into BI tools
- Open-Data Maintainers: validate files before publishing

## Tech Stack

**Core Runtime**:
- Python 3.9+ (primary implementation language)
- DuckDB (Python library for CSV validation/normalization)
- charset-normalizer (encoding detection)
- ftfy (optional mojibake repair)

**CLI & UX**:
- `rich` (modern terminal output: progress spinners, panels, tables)
- `rich-argparse` (enhanced CLI help formatting)

**Build/Test Tools**:
- setuptools (build backend for PyPI packaging)
- pytest (test framework)
- pytest-cov (coverage reporting)
- ruff (linter/formatter)

## Project Conventions

### Code Style

**Python Standards**:
- Target Python 3.9+ (specified in pyproject.toml)
- Use `ruff` for linting/formatting (line-length: 88)
- Follow PEP 8 conventions
- Type hints recommended but not enforced
- Prioritize simplicity over cleverness - minimal complexity
- Impact as little code as possible for any change
- No temporary fixes - find root causes

**Naming**:
- Column headers: snake_case (via DuckDB `normalize_names=True`)
- Variables/functions: snake_case (Python convention)
- Classes: PascalCase (Python convention)

**Comments**:
- Use docstrings for all public functions/classes (Google style)
- Add inline comments only where logic isn't self-evident
- Don't over-document obvious operations

### Architecture Patterns

**Pipeline Architecture** (sequential stages in `src/csvnorm/core.py::process_csv()`):

1. **Input Validation** (`core.py:40-96`):
   - Check file exists and is a file (for local paths)
   - Validate URL for HTTP/HTTPS inputs
   - Validate delimiter format
   - Setup output/reject paths and temp directory

2. **Encoding Detection** (`encoding.py::detect_encoding()`):
   - Uses `charset_normalizer.from_path()` for detection (local files only)
   - Samples a limited amount for efficiency
   - Returns normalized codec name (e.g., `utf-8`, `windows-1252`)

3. **Encoding Conversion** (`encoding.py::convert_to_utf8()`):
   - Runs only when `needs_conversion()` returns True (encoding ≠ UTF-8/ASCII)
   - Uses charset-normalizer for conversion
   - Writes to a temp UTF-8 file before validation/normalization

3.5. **Mojibake Repair** (`mojibake.py::repair_file()`, optional):
   - Runs only when `--fix-mojibake` flag is provided
   - Uses ftfy badness heuristic to detect garbled text in a sample (default 5000 chars)
   - Repairs entire file only if sample is flagged as "bad"
   - For remote URLs: downloads to temp file first, then processes

4. **Validation** (`validation.py::validate_csv()`):
   - **Early detection**: Pre-checks first 5 lines for header anomalies (local files only)
   - **Fallback mechanism**: If DuckDB auto-detection fails, tries common delimiter/skip combinations
   - DuckDB `read_csv(store_rejects=True, sample_size=-1, all_varchar=True)`
   - Writes rejects to `{output_stem}_reject_errors.csv`
   - Returns reject count, error summaries, and fallback_config (if used)

5. **Normalization** (`validation.py::normalize_csv()`):
   - DuckDB `COPY ... TO ... WITH (HEADER, DELIMITER, FORMAT CSV)`
   - Uses `normalize_names=True` (unless `--keep-names` is set)
   - Preserves fallback_config delimiter if provided from validation step
   - Respects custom output delimiter from `--delimiter` flag

6. **Cleanup** (`core.py:170-360`):
   - Remove temp files and directories
   - Emit success/validation panels and summary table (stderr in stdout mode)

**Error Handling**:
- Exit code 0: success
- Exit code 1: validation errors, file not found, or other failures
- Rich panels with color-coded borders (red=error, yellow=warning, green=success)
- Detailed error messages with file paths

**File Contract**:
- Input: Local CSV or HTTP/HTTPS URL
  - Remote URLs: DuckDB reads directly via httpfs extension (30s timeout)
  - If `--fix-mojibake` with URL: downloads to temp file first for processing
- Output: UTF-8 CSV to stdout (default) or file + optional `{name}_reject_errors.csv`

### Testing Strategy

**Pre-Commit Requirements**:
- Run `pytest` (or `make test` if defined) before commits
- Run `ruff` for lint/format checks

**Smoke Test Pattern**:

```bash
csvnorm test/<example.csv> -o /tmp/<example_out.csv>
# Verify: output exists and content is normalized
# Verify: reject_errors.csv is absent (or contains expected errors)
```

**Test Scenarios to Cover**:
- Non-UTF-8 encodings (MACROMAN, WINDOWS-1252, ISO-8859-1)
- DuckDB rejects (malformed rows)
- Pre-existing outputs (respect `--force` flag)
- Custom delimiters (semicolon, tab, pipe)
- Large files (performance validation)

**Verification Commands**:
- `pytest` - run full test suite
- `ruff check .` - lint
- `ruff format --check .` - format check

### Git Workflow

**Branching**:
- Main branch: `main`
- Feature branches: create as needed
- No specific naming convention enforced

**Commit Messages**:
- Extremely concise (prioritize brevity over grammar)
- Use emoji prefixes from recent history:
  - 🔧 Fix: bug fixes
  - 🔧 Add: new features
  - closes #N for issue references

**Required Updates**:
- Update `LOG.md` for any significant change
- Add entry with `YYYY-MM-DD` heading
- Place most recent entry at top
- Keep bullet points short and high-signal

**Before Commit**:
- Run `pytest` and `ruff` checks
- Update LOG.md if behavior changed

## Domain Context

**CSV Ecosystem Challenges**:
- Open data portals and legacy systems publish CSVs with inconsistent encodings (WINDOWS-1252, MACROMAN, ISO-8859-1)
- Non-standard delimiters (semicolon in European data, tabs, pipes)
- Header naming inconsistencies (spaces, camelCase, mixed styles)
- These issues break automated pipelines and require manual intervention

**DuckDB Role**:
- Industry-leading embedded analytics database
- Exceptional CSV handling with detailed error reporting
- `store_rejects=true` captures malformed rows with reasons
- `normalize_names=true` handles header standardization
- `sample_size=-1` ensures validation of entire file

**Encoding Detection Complexity**:
- charset-normalizer can fail on edge cases; errors are surfaced cleanly
- UTF-8-SIG (BOM) is handled by Python codecs and DuckDB read options
- Local files may be converted before validation to avoid mixed encodings

**ETL Integration**:
- Designed for shell script and CI/CD pipeline integration
- Exit codes enable proper error handling in batch processes
- Verbose mode aids debugging in production environments

## Important Constraints

**Technical Constraints**:
1. **Python Packaging**: `pyproject.toml` defines the package; keep metadata in sync with README.

2. **Simplicity Mandate**: From global CLAUDE.md:
   - Make every task and code change as simple as possible
   - Impact as little code as possible
   - Avoid over-engineering, massive changes, or complex refactors
   - No premature abstractions

3. **Cross-Platform**: Must work on Linux and macOS (NFR-3)

4. **Memory Constraint**: Should not exceed 2× input file size (NFR-2)

**Performance Targets**:
- 100 MB file: < 60 seconds on 4-core machine (NFR-1)
- 10 MB file: < 1 second average runtime
- Supports files up to 1 GB

**Operational Constraints**:
- Users must have write permission to output directory
- Dependencies (DuckDB, charset-normalizer, ftfy) must be installed
- Large files may require increased system resources

## External Dependencies

**Required at Runtime**:
1. **DuckDB** (Python package, v0.9+)
   - Purpose: CSV validation, normalization, error reporting
   - Installed via Python dependencies

2. **charset-normalizer** (Python package)
   - Purpose: Encoding detection and conversion

3. **ftfy** (Python package, optional feature)
   - Purpose: Mojibake repair for already-decoded text

**Build-Time Dependencies**:
- Python 3.9+
- setuptools
- pytest/ruff for dev workflows

**Dependency Management**:
- `pip install csvnorm` or `uv tool install csvnorm`
- `pip install -e .[dev]` for development

## Deployment & Release

**Release Process**:
- Publishing to PyPI is automated via GitHub Actions (Trusted Publishing)
- Release is triggered by pushing a `vX.Y.Z` tag
- A GitHub Release must be created manually after the workflow succeeds

**Local Release Checklist**:
- Update version in `pyproject.toml`
- Use the project `.venv` and `uv` for testing
- Run `pytest tests/ -v` and manual CLI smoke tests:
  - `csvnorm test/utf8_basic.csv -f`
  - `csvnorm test/latin1_semicolon.csv -d ';' -f -V`
- Commit changes and push tag (`vX.Y.Z`) to trigger the workflow

**Workflow Notes**:
- Workflow file: `.github/workflows/publish-pypi.yml`
- Tests run on Python 3.9–3.12 before publish
- OIDC Trusted Publishing is configured; no PyPI tokens stored in secrets

**Operational Rules**:
- Do not use `pip3 --break-system-packages`
- Do not commit `dist/` artifacts

**Post-Release Verification**:
- `pip install --upgrade csvnorm` and confirm `csvnorm --version`
- Check GitHub Releases shows the new version as "Latest"
