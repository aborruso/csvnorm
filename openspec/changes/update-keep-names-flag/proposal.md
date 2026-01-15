# Change: Replace --no-normalize with --keep-names

## Why
The flag name "--no-normalize" implies disabling all normalization steps, but the current behavior only preserves original column names. This mismatch is confusing for users.

## What Changes
- Replace the CLI option `--no-normalize` with `--keep-names`
- Update help text and documentation to reflect the new flag
- **BREAKING**: remove `--no-normalize` immediately (no alias)

## Impact
- Affected specs: cli-options (new)
- Affected code: script/prepare.sh, README.md, docs/evaluation.md
