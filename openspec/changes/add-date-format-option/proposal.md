# Change: Add date format hint for DuckDB normalization

## Why
Users need to disambiguate custom date formats (e.g., dd/mm/yyyy vs mm/dd/yyyy) during normalization.

## What Changes
- Add `--date-format` CLI option to pass a DuckDB `read_csv` dateformat hint.
- Apply the hint only during the normalization step (not validation), as requested.
- Support local files and HTTP/HTTPS URLs.

## Impact
- Affected specs: csv-normalization (new capability)
- Affected code: src/csvnorm/cli.py, src/csvnorm/validation.py, src/csvnorm/core.py
