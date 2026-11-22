## 0. Preparation
- [x] 0.1 Archive `preserve-crlf-line-endings`

## 1. Reference files and measurement
- [x] 1.1 This proposal and its spec deltas
- [x] 1.2 Golden cases (`tests/fixtures/golden/`, `tests/test_golden.py`)
- [x] 1.3 Encoding equivalence test with literal expected values
- [x] 1.4 `make_csv` fixture
- [x] 1.5 `scripts/bench_large.py`
- [x] 1.6 `duckdb>=2.0.0,<3`
- [x] 1.7 Baseline measurement

## 2. Header and CRLF written by DuckDB
- [x] 2.1 `_select_list`, `_copy_options`, `crlf` parameter; remove `_fix_duckdb_keyword_prefix` and `convert_row_endings_to_crlf`

## 3. Chunked UTF-8 conversion and disk space
- [x] 3.1 Chunked `convert_to_utf8` with file offset on errors
- [x] 3.2 Staged output with `os.replace`, disk-full panel, low-space warning

## 4. Encoding detection
- [x] 4.1 `_scan`, sample route above 50 MiB, `detect_and_convert` with one fallback

## 5. Conditional
- [x] 5.1 Single `COPY` for validation and normalization, only if the median stays above 60 s: not needed, median 47.8 s

## 6. Docs and release
- [x] 6.1 README, CLAUDE.md, PRD.md, LOG.md
- [ ] 6.2 Release 1.4.0
