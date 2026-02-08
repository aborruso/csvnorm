# Change: Add stdin support (csvnorm -)

## Why
csvnorm follows Unix-first philosophy (stdout default, pipe-friendly) but cannot read from stdin. Tools like jq, xsv, csvkit accept `-` for stdin input. This limits composability: `cat data.csv | csvnorm -` does not work.

## What Changes
- Accept `-` as input_file to read from stdin
- Save stdin data to temp file, then process as local file
- Error if stdin is a terminal (no piped data)
- Compatible with all existing flags (--check, -o, --fix-mojibake, --strict)

## Impact
- Affected specs: `csv-input`
- Affected code: `src/csvnorm/cli.py`, `src/csvnorm/core.py`
- No breaking changes
- New input mode, backward compatible
