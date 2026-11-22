# Change: Speed up csvnorm on large files

## Why

On an 826 MB cp1252 CSV (5.4 million rows, CRLF rows) csvnorm takes about 220 s, measured on 2026-11-22. About 170 s go to Python passes that read or rewrite the whole file: encoding detection (106 s, a full strict decode per candidate codec inside `charset_normalizer`), CRLF conversion byte by byte (40 s), a full rewrite to fix the header (14 s) and an in-memory UTF-8 conversion. The same passes load the whole file in RAM. Two existing defects live in the same functions: text-mode conversion turns CR inside cells into LF for non-UTF-8 files, and the header keyword fix only works with a comma delimiter. A cross-filesystem `shutil.move` can also destroy an existing output under `--force` if it fails halfway.

## What Changes

- Encoding detection: strict UTF-8 pass, then `charset_normalizer` on a small sample that contains every high byte value of the file, examined in full; UTF-16/32 BOM, NUL bytes and uncovered values keep today's full detection; one fallback to full detection if conversion fails.
- UTF-8 conversion in fixed-size chunks, preserving CR, LF and CRLF.
- Header keyword fix and CRLF row endings written by DuckDB during the `COPY` (`COLUMNS(...) AS`, `NEW_LINE`), for every delimiter.
- File output staged next to the final output and renamed atomically; disk-full errors reported with one panel and exit 1; a low-disk-space warning before starting.
- `normalize_csv` gains an optional `crlf` parameter (public API, backward compatible).

## Impact

- Affected specs: `encoding-detection`, `processing-pipeline`, `error-handling`, `output-location`
- Affected code: `src/csvnorm/encoding.py`, `src/csvnorm/validation.py`, `src/csvnorm/core.py`, tests, `scripts/bench_large.py`
- Design document: `docs/designs/speed-up-large-files.md`
- Not breaking for CLI users; visible changes: CR preserved in non-UTF-8 files, header fix with any delimiter, encoding chosen differently in some edge cases (documented per file in `tests/test_encoding_equivalence.py`)
