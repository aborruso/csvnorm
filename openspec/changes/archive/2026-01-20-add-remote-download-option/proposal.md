# Change: Add remote download option for non-range URLs

## Why
Some public CSV URLs do not support HTTP range requests, causing DuckDB to fail. Others trigger TLS/SSL handshake errors in Python's downloader even though the URL is reachable. Users want a simple CLI option to download the file locally and continue processing without manual steps.

## What Changes
- Add a CLI flag (e.g., `--download-remote`) to download remote CSVs locally when range requests are unsupported.
- When the flag is used and a remote URL lacks range support, csvnorm downloads to a temp file and continues normal processing.
- When the flag is used and the download fails due to a TLS/SSL handshake error, csvnorm retries the download using a more compatible fallback (e.g., system curl) and continues processing if successful.
- Keep default behavior unchanged: without the flag, show the current error and exit.

## Impact
- Affected specs: `csv-input`
- Affected code: `src/csvnorm/cli.py`, `src/csvnorm/core.py`, `src/csvnorm/utils.py` (if new helper), tests
