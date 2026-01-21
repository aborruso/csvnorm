# Change: Add compressed CSV input support (gzip/zip)

## Why
Users often receive CSVs compressed as .gz or .zip; requiring manual extraction slows pipelines and adds errors.

## What Changes
- Support reading `.csv.gz` inputs via DuckDB's native CSV compression autodetect.
- Support reading `.zip` inputs with exactly one CSV inside via DuckDB `zipfs` extension and `zip://` paths.
- Automatically install/load `zipfs` when a zip input is detected.
- **BREAKING**: None.

## Impact
- Affected specs: `specs/csv-input/spec.md`
- Affected code: `src/csvnorm/core.py`, `src/csvnorm/validation.py`, `src/csvnorm/utils.py` (input resolution + DuckDB read options)
