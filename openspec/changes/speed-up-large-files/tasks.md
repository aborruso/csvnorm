## 0. Preparation
- [x] 0.1 Archive `preserve-crlf-line-endings`

## 1. Reference files and measurement
- [ ] 1.1 This proposal and its spec deltas
- [ ] 1.2 Golden cases (`tests/fixtures/golden/`, `tests/test_golden.py`)
- [ ] 1.3 Encoding equivalence test with literal expected values
- [ ] 1.4 `make_csv` fixture
- [ ] 1.5 `scripts/bench_large.py`
- [ ] 1.6 `duckdb>=2.0.0,<3`
- [ ] 1.7 Baseline measurement

## 2. Header and CRLF written by DuckDB
- [ ] 2.1 `_select_list`, `_copy_options`, `crlf` parameter; remove `_fix_duckdb_keyword_prefix` and `convert_row_endings_to_crlf`

## 3. Chunked UTF-8 conversion and disk space
- [ ] 3.1 Chunked `convert_to_utf8` with file offset on errors
- [ ] 3.2 Staged output with `os.replace`, disk-full panel, low-space warning

## 4. Encoding detection
- [ ] 4.1 `_scan`, sample route, `detect_and_convert` with one fallback

## 5. Conditional
- [ ] 5.1 Single `COPY` for validation and normalization, only if the median stays above 60 s

## 6. Docs and release
- [ ] 6.1 README, CLAUDE.md, PRD.md, LOG.md; release 1.4.0
