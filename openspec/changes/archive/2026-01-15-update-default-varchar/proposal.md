# Change: Default CSV columns to VARCHAR

## Why
DuckDB type inference can fail or reject rows with inconsistent values. Defaulting all columns to VARCHAR avoids inference-driven failures without altering field values.

## What Changes
- Read CSVs with all columns as VARCHAR by default during validation and normalization
- Preserve existing normalization behavior and output format (UTF-8, comma-delimited)

## Impact
- Affected specs: csv-validation (new)
- Affected code: script/prepare.sh (DuckDB read_csv calls)
