# Change: Add remote CSV URL support

## Why

Currently csvnorm only accepts local file paths. DuckDB has native support for reading CSV files from HTTP/HTTPS URLs via its httpfs extension. Users need to process remote CSV files without manually downloading them first, enabling direct integration with open data portals and remote data sources.

## What Changes

- Accept HTTP/HTTPS URLs as input in addition to local file paths
- Detect URL vs file path automatically
- Pass URLs directly to DuckDB for validation and normalization (leverage DuckDB httpfs)
- Maintain all existing functionality (encoding detection, validation, normalization)
- Skip encoding detection/conversion for remote URLs (DuckDB handles this)
- Use fixed 30-second timeout for remote requests
- Support only public URLs (no authentication headers)

## Impact

- Affected specs: new `csv-input` capability
- Affected code: 
  - `src/csvnorm/cli.py` - update argument type and help text
  - `src/csvnorm/core.py` - add URL detection logic, conditional pipeline
  - `src/csvnorm/validation.py` - ensure DuckDB queries work with URLs
  - `src/csvnorm/utils.py` - add URL validation utility
- No breaking changes - existing local file functionality unchanged
