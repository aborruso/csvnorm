# Change: Refactor core.process_csv into helper steps

## Why
`process_csv` is a large orchestration function that is difficult to test and reason about. Splitting it into focused helper functions improves readability and testability without changing behavior.

## What Changes
- Extract discrete pipeline steps from `core.process_csv` into internal helper functions
- Preserve existing inputs, outputs, error handling, and UX
- Keep the external API and CLI behavior unchanged

## Impact
- Affected specs: `processing-pipeline` (new capability)
- Affected code: `src/csvnorm/core.py`
