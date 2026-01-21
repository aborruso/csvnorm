# Change: Always download remote inputs before processing

## Why
Remote URL processing currently delegates encoding handling to DuckDB, which can produce different results than local files. Downloading first makes remote and local behavior consistent and avoids DuckDB URL-specific quirks.

## What Changes
- Remote HTTP/HTTPS inputs are always downloaded to a local temporary file before validation/normalization.
- Encoding detection/conversion runs on the downloaded file (same as local input).
- DuckDB reads the local temp file instead of the URL.
- `--download-remote` becomes redundant (kept as a no-op compatibility flag or deprecated).

## Impact
- Affected specs: csv-input
- Affected code: src/csvnorm/core.py, src/csvnorm/encoding.py, src/csvnorm/validation.py (expected)
