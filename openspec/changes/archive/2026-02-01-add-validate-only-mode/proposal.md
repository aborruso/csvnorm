# Change: Add validate-only mode (--check flag)

## Why
Users need a quick way to check if a CSV has validation errors without processing/normalizing it. Currently, they must process the entire file and check the exit code, which is wasteful for large files or CI/CD validation checks.

## What Changes
- Add `--check` flag that validates the CSV and exits immediately with exit code 0 (valid) or 1 (errors)
- In check mode: no encoding conversion, no normalization, no output written
- Output: minimal message to stderr indicating validation status
- Exit codes: 0 = valid CSV, 1 = validation errors or fatal errors

## Impact
- Affected specs: `csv-input`
- Affected code: `src/csvnorm/cli.py`, `src/csvnorm/core.py`
- No breaking changes
- New optional flag, backward compatible
