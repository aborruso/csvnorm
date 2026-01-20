# Change: Add in-place output option

## Why
Users want to normalize a CSV while keeping the original filename, without managing separate output paths.

## What Changes
- Add `--in-place` to overwrite the input file after successful processing.
- Restrict `--in-place` to local files and disallow combining with `-o/--output-file`.
- Write reject files next to the input when using `--in-place`.
- Use a temporary file for safe atomic replacement and remove it after completion.

## Impact
- Affected specs: output-location
- Affected code: src/csvnorm/cli.py, src/csvnorm/core.py, src/csvnorm/validation.py, docs/README (if applicable)
