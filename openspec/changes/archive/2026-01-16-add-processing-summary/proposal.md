# Change: Add processing summary after CSV completion

## Why

After CSV processing completes, users want a clear summary of what happened during processing. The current success table shows basic information but doesn't indicate if encoding was converted, whether errors occurred, or where to find error details. Since csvnorm already uses rich formatting, a comprehensive summary would help users quickly understand processing results without examining individual files.

## What Changes

- Add comprehensive processing summary displayed after completion (success or failure)
- Show encoding conversion status (converted from X to UTF-8 / no conversion needed)
- Display error summary panel with reject count and sample error types when validation fails
- Show statistics: row count, column count, file sizes
- Maintain existing success table and add error panel
- Show both success table and error panel when validation fails

## Impact

- Affected specs: new `processing-summary` capability
- Affected code:
  - `src/csvnorm/core.py` - enhance success summary, add error summary panel, collect stats
  - `src/csvnorm/validation.py` - return reject count and error types
- No breaking changes - only enhances existing output
