# Change: Preserve CRLF line endings in file output

## Why

csvnorm converts all line endings to LF, losing the semantic distinction between CRLF row terminators and LF in-cell newlines (RFC 4180 §2). A file with 20 CRLF row terminators and 7 LF in-cell newlines becomes 28 LF-only after processing, making it impossible to distinguish row boundaries without full CSV parsing.

## What Changes

- When the input file uses CRLF as row terminators, csvnorm SHALL preserve CRLF in the output file (`-o` mode only).
- Stdout mode always outputs LF (Unix pipeline compatibility).
- Detection is automatic (no user action required).

## Impact

- Affected specs: `output-location`
- Affected code: `src/csvnorm/validation.py`, `src/csvnorm/utils.py`, `src/csvnorm/core.py`
