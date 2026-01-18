## csvnorm — Quick instructions for AI coding agents

Purpose: Get an AI contributor productive quickly. This file highlights the runtime entrypoint, important implementation details to preserve, and the minimal commands and files you will need.

### 1. Big picture
- Python CLI tool for CSV validation and normalization (not Bash)
- Installable via PyPI: `pip install csvnorm`
- Flow: encoding detection (charset_normalizer) → UTF-8 conversion (Python codecs) → optional mojibake repair (ftfy) → validation (DuckDB with `store_rejects=true`) → normalization (DuckDB COPY)
- Two output modes: **stdout** (default) or **file** (with `-o`)

### 2. Where to look (source of truth)
- `src/csvnorm/` — Python package modules
- `src/csvnorm/core.py` — Main `process_csv()` pipeline
- `src/csvnorm/validation.py` — DuckDB validation with fallback configs and early detection
- `PRD.md` / `README.md` — Product goals, usage examples
- `LOG.md` — Changelog with behavioral fixes
- `test/` — CSV fixtures for testing
- `tests/` — pytest test suite (105 tests)

### 3. Key commands & examples
```bash
# Development
source .venv/bin/activate
uv pip install -e ".[dev]"

# Testing
pytest tests/ -v
pytest tests/test_cli.py::TestMainFunction::test_skip_rows_metadata -v

# Usage
csvnorm input.csv                    # stdout mode
csvnorm input.csv -o output.csv      # file mode
csvnorm input.csv -s 2 -o out.csv    # skip first 2 rows
csvnorm input.csv --fix-mojibake     # repair mojibake
csvnorm https://example.com/data.csv # remote URL
```

### 4. Implementation details to preserve (explicit)

**Encoding** (encoding.py):
- Detection: `charset_normalizer.from_path()`
- Conversion: Only if encoding ∉ {utf-8, ascii, utf-8-sig}
- Uses Python codecs (not iconv)

**Validation** (validation.py):
- **Early detection**: Pre-checks first 5 lines for header anomalies (title rows)
- **Fallback mechanism**: If DuckDB auto-detection fails, tries common delimiter/skip combinations
- DuckDB query: `read_csv(..., store_rejects=true, sample_size=-1, all_varchar=true)`
- Returns: (reject_count, error_types, fallback_config)

**Normalization** (validation.py):
- DuckDB COPY with `normalize_names=true` (unless `--keep-names`)
- Preserves fallback_config delimiter if provided
- Output delimiter configurable via `-d`

**Mojibake repair** (mojibake.py):
- Optional with `--fix-mojibake [N]` (N = sample size, default 5000)
- Uses ftfy badness heuristic to detect, repairs only if flagged as "bad"
- For remote URLs: downloads to temp file first

**Output modes**:
- **Stdout mode** (default): CSV to stdout, progress/errors to stderr, temp reject file
- **File mode** (`-o`): CSV to file, rich success table, reject file in same dir

**Temp file cleanup**:
- UTF-8 conversion creates temp file in system temp dir
- Reject files removed if empty (< 2 lines, just header)
- Stdout mode: reject files in temp dir with path shown in stderr

### 5. Project conventions & checks
- Type hints for all functions
- Run `pytest tests/ -v` after edits
- Run `ruff check .` for linting
- Python 3.9+ compatibility
- Cross-platform (Linux, macOS, Windows)

### 6. External deps & integration points
- Runtime: charset-normalizer, duckdb, ftfy, rich, rich-argparse, pyfiglet
- Dev: pytest, pytest-cov, ruff
- All managed via `pyproject.toml`
- DuckDB used as Python library (not CLI)

### 7. Quick contract for edits
- Input: CSV path or HTTP/HTTPS URL (any encoding, any delimiter)
- Output: UTF-8, comma-delimited CSV (configurable with `-d`)
- Headers: normalized to snake_case (unless `-k/--keep-names`)
- Error modes: Non-UTF-8 encodings, DuckDB rejects, pre-existing outputs (respect `--force`)
- Input protection: Never overwrite input file, even with `--force`

### 8. Fast smoke tests
```bash
source .venv/bin/activate
csvnorm test/utf8_basic.csv | head
csvnorm test/latin1_semicolon.csv -o /tmp/out.csv
csvnorm test/metadata_skip_rows.csv -s 2 -o /tmp/out.csv
csvnorm -v  # Version check (must not fail)
```

### 9. When adding features
- Add tests in `tests/` with pytest
- Update `LOG.md` with changes
- Update `README.md` if user-facing
- Update `PRD.md` if new functional requirement
- For deployment: see `DEPLOYMENT.md` (uses GitHub Actions + Trusted Publishing)

If anything in these notes is unclear or you want more detail, check `CLAUDE.md` for comprehensive architecture documentation.
