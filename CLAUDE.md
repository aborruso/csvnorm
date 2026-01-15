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

CSV Normalizer Utility - A Bash-based tool for validating and normalizing CSV files. The runtime entrypoint is `script/prepare.sh`, which wraps encoding detection, DuckDB validation, and CSV normalization into a single command.

## Common Commands

### Installation
```bash
make install              # Full install: script + Python deps + DuckDB CLI
make install_light        # Script only (manage deps separately)
make install PREFIX=~/.local  # Custom install location
make uninstall            # Remove installed utility
```

### Testing
```bash
make test                 # Run all tests
make check                # Verify dependencies
shellcheck script/prepare.sh  # Lint shell script (required before commits)
```

### Development
```bash
script/prepare.sh test/<example.csv>  # Run locally (outputs to script/tmp/)
script/prepare.sh input.csv -f       # Force overwrite
script/prepare.sh input.csv -n       # Keep original column names
script/prepare.sh input.csv -d ';'   # Custom delimiter
script/prepare.sh input.csv -o ./output  # Custom output directory
```

### Cleanup
```bash
make clean               # Remove temporary files
```

## Architecture

### Flow
1. **Encoding detection**: `normalizer --minimal` with SIGPIPE handling → fallback to `file -b --mime-encoding`
2. **Encoding conversion**: `iconv -f <detected> -t UTF-8` (only if encoding ≠ utf-8/ascii/utf-8-sig)
3. **Validation**: DuckDB `read_csv(store_rejects=true, sample_size=-1)` → rejects to `reject_errors.csv`
4. **Normalization**: DuckDB `copy` with `normalize_names=true` (unless `--keep-names`)
5. **Output**: UTF-8 CSV to `<output_dir>/<snake_cased_name>.csv`

### Key Implementation Details

**Encoding detection** (script/prepare.sh:105-130):
- Uses `shuf -n 10000` + `normalizer --minimal` with SIGPIPE (exit 141) handling
- Fallback to `file` command if normalizer fails
- Special case: MACROMAN → MACINTOSH mapping
- Only runs `iconv` when encoding is NOT utf-8/ascii/utf-8-sig

**Header normalization** (script/prepare.sh:76-81, 159-163):
- Output filename: `tr`/`sed` to snake_case
- DuckDB: `normalize_names=true` flag (unless `--keep-names`)

**Temp file cleanup** (script/prepare.sh:165-174):
- Removes `reject_errors.csv` if empty (≤1 line)
- Removes `${base_name}_utf8.csv` temp file after processing

**Shell policy** (script/prepare.sh:3-6):
- Uses `set -euo pipefail` (maintain this in any new shell code)

## Dependencies

**Required at runtime**:
- `charset_normalizer` (Python CLI: `normalizer`)
- `iconv` (encoding conversion)
- `file` (fallback encoding detection)
- DuckDB CLI (CSV validation/normalization)

**Installation**:
- Makefile automates DuckDB download and Python package installation
- System deps: `curl`, `unzip` (for DuckDB CLI download)

## Testing

Smoke test pattern:
```bash
script/prepare.sh test/<example.csv>
# Verify: script/tmp/<snake_name>.csv exists
# Verify: reject_errors.csv is absent (or has errors if expected)
```

After shell edits:
```bash
shellcheck script/prepare.sh
make test
```

## Critical Constraints

1. **No Python packaging files yet**: `pyproject.toml`/`setup.py` do not exist. README mentions `pip install .` but this is not yet supported. Update README + Makefile if adding Python packaging.

2. **ShellCheck compliance**: PRD requires passing `shellcheck`. Always run after script edits.

3. **Error modes to handle carefully**:
   - Non-UTF-8 encodings (MACROMAN, WINDOWS-1252, etc.)
   - DuckDB rejects (malformed rows)
   - Pre-existing outputs (respect `--force` flag)

4. **Simplicity**: Avoid over-engineering. Maintain minimal complexity matching current implementation.

## File Contract

**Input**: Arbitrary CSV (any encoding, any delimiter, potentially large)
**Output**:
- `<output_dir>/<clean_name>.csv` (UTF-8, comma-delimited by default)
- `reject_errors.csv` (if DuckDB finds invalid rows)

**Exit codes**:
- 0: Success
- 1: Validation errors (rejects found) or other failures

## Key Files

- `script/prepare.sh` - Runtime entrypoint (all logic)
- `PRD.md` - Product requirements
- `README.md` - User documentation, Make targets
- `LOG.md` - Changelog with behavioral fixes
- `.github/copilot-instructions.md` - Detailed implementation notes
- `Makefile` - Installation, testing, dependency management
- `test/` - Example CSVs for smoke tests
