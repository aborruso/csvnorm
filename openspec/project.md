# Project Context

## Purpose

CSV Normalizer Utility - A command-line tool that validates, cleans, and normalizes CSV files for reliable consumption by analytics, ETL, and data-science workflows.

**Core Goals**:
- Accept raw CSV files with inconsistent encodings, delimiters, and headers
- Output fully normalized UTF-8 comma-delimited files
- Detect and report structural/encoding errors early
- Integrate seamlessly into shell scripts and CI pipelines
- Support datasets up to 1 GB on commodity hardware

**Target Users**:
- Data Engineers: batch-process hundreds of CSVs in CI pipelines
- Data Analysts: quickly clean files before importing into BI tools
- Open-Data Maintainers: validate files before publishing

## Tech Stack

**Core Runtime**:
- Bash 4+ (primary implementation language)
- DuckDB CLI (CSV validation and normalization engine)

**Utilities**:
- `charset_normalizer` (Python CLI: encoding detection)
- `iconv` (encoding conversion to UTF-8)
- `file` (fallback encoding detection)

**Build/Test Tools**:
- GNU Make (installation, dependency management, testing)
- ShellCheck (shell script linting - required before commits)

**Not Used Yet** (but mentioned in docs):
- Python packaging (pyproject.toml/setup.py) - future work

## Project Conventions

### Code Style

**Shell Script Standards**:
- Use `set -euo pipefail` at script start (already enforced in script/prepare.sh:3-6)
- MUST pass `shellcheck` before any commit (NFR-4 in PRD)
- Prioritize simplicity over cleverness - minimal complexity matching current implementation
- Impact as little code as possible for any change
- No temporary fixes - find root causes

**Naming**:
- Output files: snake_case (via `tr`/`sed` transformations)
- DuckDB columns: snake_case (via `normalize_names=true` flag)
- Variables: lowercase with underscores (Bash convention)

**Comments**:
- Add comments only where logic isn't self-evident
- Don't over-document obvious operations

### Architecture Patterns

**Pipeline Architecture** (sequential stages in script/prepare.sh):

1. **Encoding Detection** (lines 105-130):
   - `shuf -n 10000` + `normalizer --minimal` with SIGPIPE handling
   - Fallback to `file -b --mime-encoding` if normalizer fails
   - Special case: MACROMAN → MACINTOSH mapping

2. **Encoding Conversion** (conditional):
   - Only runs `iconv -f <detected> -t UTF-8` when encoding ≠ utf-8/ascii/utf-8-sig

3. **Validation** (DuckDB):
   - `read_csv(store_rejects=true, sample_size=-1)` → rejects to `reject_errors.csv`

4. **Normalization** (DuckDB):
   - `copy` with `normalize_names=true` (unless `--keep-names` flag)

5. **Cleanup** (lines 165-174):
   - Remove `reject_errors.csv` if empty (≤1 line)
   - Remove temp `${base_name}_utf8.csv` files

**Error Handling**:
- Exit code 0: success
- Exit code 1: validation errors or failures
- Exit code 141: SIGPIPE (handled gracefully in encoding detection)

**File Contract**:
- Input: Arbitrary CSV (any encoding, delimiter, size)
- Output: UTF-8 comma-delimited CSV + optional `reject_errors.csv`

### Testing Strategy

**Pre-Commit Requirements**:
- All shell edits MUST pass `shellcheck script/prepare.sh`
- Run `make test` before commits

**Smoke Test Pattern**:

```bash
script/prepare.sh test/<example.csv>
# Verify: script/tmp/<snake_name>.csv exists
# Verify: reject_errors.csv is absent (or contains expected errors)
```

**Test Scenarios to Cover**:
- Non-UTF-8 encodings (MACROMAN, WINDOWS-1252, ISO-8859-1)
- DuckDB rejects (malformed rows)
- Pre-existing outputs (respect `--force` flag)
- Custom delimiters (semicolon, tab, pipe)
- Large files (performance validation)

**Verification Commands**:
- `make check` - verify dependencies installed
- `make test` - run full test suite

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
- Run `shellcheck script/prepare.sh`
- Run `make test`
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
- `normalizer` can produce SIGPIPE (141) on large files → handled gracefully
- `file` command provides reliable fallback
- MACROMAN encoding requires mapping to MACINTOSH for iconv compatibility
- UTF-8-SIG (BOM) requires special handling to avoid conversion

**ETL Integration**:
- Designed for shell script and CI/CD pipeline integration
- Exit codes enable proper error handling in batch processes
- Verbose mode aids debugging in production environments

## Important Constraints

**Technical Constraints**:
1. **No Python Packaging Yet**: `pyproject.toml`/`setup.py` do not exist. README mentions `pip install .` but this is NOT supported. Update README + Makefile if adding Python packaging.

2. **ShellCheck Compliance**: PRD NFR-4 requires passing `shellcheck`. This is non-negotiable - always run after script edits.

3. **Simplicity Mandate**: From global CLAUDE.md:
   - Make every task and code change as simple as possible
   - Impact as little code as possible
   - Avoid over-engineering, massive changes, or complex refactors
   - No premature abstractions

4. **Bash 4+ Target**: Must work on Linux and macOS (NFR-3)

5. **Memory Constraint**: Should not exceed 2× input file size (NFR-2)

**Performance Targets**:
- 100 MB file: < 60 seconds on 4-core machine (NFR-1)
- 10 MB file: < 1 second average runtime
- Supports files up to 1 GB

**Operational Constraints**:
- Users must have write permission to output directory
- Dependencies (DuckDB, charset_normalizer, iconv, file) must be installed
- Large files may require increased system resources

## External Dependencies

**Required at Runtime**:
1. **DuckDB CLI** (v1.0.0+)
   - Purpose: CSV validation, normalization, error reporting
   - Installation: Auto-downloaded by `make install` (Linux x86_64/ARM, macOS)
   - Fallback: Manual install from duckdb.org

2. **charset_normalizer** (Python package)
   - Purpose: Primary encoding detection
   - CLI: `normalizer --minimal`
   - Installation: `pip3 install charset_normalizer` (auto via `make install`)

3. **iconv** (system utility)
   - Purpose: Encoding conversion to UTF-8
   - Usually pre-installed on Linux/macOS

4. **file** (system utility)
   - Purpose: Fallback encoding detection
   - Usually pre-installed on Linux/macOS

**Build-Time Dependencies**:
- `curl` (for DuckDB CLI download)
- `unzip` (for DuckDB CLI extraction)
- Python 3.8+ (for charset_normalizer)
- `shellcheck` (for linting - dev/CI only)

**Dependency Management**:
- `make install` - full install (script + deps + DuckDB)
- `make install_light` - script only (user manages deps separately)
- `make check` - verify all dependencies present
