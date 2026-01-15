# Change: Default output directory uses current working directory

## Why
The current default output directory is based on the script location, which makes outputs land in non-obvious paths (e.g., a global install under `bin/tmp`). This feels like “nowhere” to users and breaks the expectation that outputs are created near where the command is run.

## What Changes
- Default output directory becomes the current working directory when `--output-dir` is not provided.
- Temporary files (`reject_errors.csv`, `*_utf8.csv`) follow the resolved output directory.
- If the output CSV already exists, the tool SHALL stop and warn unless `--force` is provided.

## Impact
- Affected specs: output-location (new)
- Affected code: `script/prepare.sh`
- Affected docs: `README.md`, `docs/deployment.md`
