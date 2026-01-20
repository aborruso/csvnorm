# Change: Add zipfs fallback for remote ZIP downloads

## Why
Remote ZIP inputs downloaded with `--download-remote` fail when DuckDB cannot load the `zipfs` extension. Users then get a misleading HTTP 404 error. We need a local fallback that extracts ZIPs when zipfs is unavailable.

## What Changes
- Detect zipfs load failure for local ZIP inputs.
- Fallback to local ZIP extraction and process the single CSV inside.
- If the ZIP contains multiple CSV files, stop and show the existing guidance message.

## Impact
- Affected specs: csv-input
- Affected code: src/csvnorm/validation.py, src/csvnorm/core.py
