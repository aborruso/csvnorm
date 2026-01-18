# ADR 001: Use DuckDB for CSV Validation and Normalization

Date: 2024-12 (inferred from v1.0 release)
Status: Accepted

## Context

csvnorm needs to:
- Validate CSV files with unknown dialects (delimiter, quoting, encoding)
- Detect and reject malformed rows
- Normalize column names to snake_case
- Handle large files efficiently (PRD: up to 1GB)
- Provide detailed error reporting

Initial requirements demanded:
1. Automatic dialect detection (no manual delimiter specification)
2. Strict validation (reject rows that don't match header structure)
3. Capture rejected rows with error details
4. Normalize to consistent output format

## Decision

Use **DuckDB** as the core engine for CSV validation and normalization.

Implementation:
- `validate_csv()` uses `COPY ... (store_rejects=true)` to capture errors
- `normalize_csv()` uses `COPY ... (normalize_names=true)` for output
- DuckDB's auto-detection handles delimiter, quote char, escape char
- Reject files contain problematic rows with error descriptions

## Alternatives Considered

### 1. pandas
**Rejected because:**
- Too permissive: silently coerces data types, fills missing values
- No built-in strict validation mode
- `read_csv()` auto-detection less reliable than DuckDB
- Error reporting minimal (fails on first error, no reject capture)
- Memory inefficient for large files (loads entire dataset)

**Would require:**
- Custom validation logic for structure checking
- Manual error collection and formatting
- Higher memory footprint

### 2. polars
**Rejected because:**
- No `store_rejects` equivalent for error capture
- Auto-detection comparable to pandas (less robust than DuckDB)
- Would need custom validation layer
- Smaller ecosystem, fewer CSV edge cases handled

**Advantages over pandas:**
- Better performance, lower memory
- But insufficient for validation use case

### 3. csvkit (csvsql/csvclean)
**Rejected because:**
- Python wrapper around subprocess calls (additional overhead)
- Slower processing for large files
- Less flexible error handling (fixed output formats)
- Auto-detection limited to Python csv.Sniffer

**Use case mismatch:**
- csvkit designed for data exploration, not strict validation

### 4. Python csv module
**Rejected because:**
- No auto-detection (requires manual dialect specification)
- No validation logic (just parsing)
- No reject capture mechanism
- Would require building entire validation layer from scratch

## Consequences

### Positive

**Automatic dialect detection:**
- Handles 90% of CSV files without configuration
- Detects delimiter, quote char, escape char, header presence
- Supports common edge cases (semicolon, pipe, tab delimiters)

**Strict validation:**
- Rejects rows that don't match header column count
- Captures parsing errors (unclosed quotes, invalid escapes)
- Provides detailed error descriptions via reject file

**Efficient processing:**
- Streaming parser for large files (minimal memory overhead)
- Native CSV reader optimized for performance
- Handles 100MB files in <60s (PRD requirement)

**Column normalization:**
- Built-in `normalize_names=true` converts to snake_case
- Consistent output without manual transformation

**Error reporting:**
- `store_rejects=true` captures all problematic rows
- Reject file contains original row + error description
- Enables debugging without re-running validation

### Negative

**Dependency size:**
- DuckDB wheel ~50MB (largest dependency)
- Increases installation size significantly

**Learning curve:**
- SQL-based API less familiar than pandas/polars
- Requires understanding COPY command options

**Limited flexibility:**
- Cannot customize rejection criteria beyond DuckDB's built-in rules
- Normalization rules fixed (snake_case only)

**Fallback complexity:**
- Auto-detection fails on some edge cases (metadata rows, unusual delimiters)
- Required implementing manual fallback strategy (see ADR 002)

## Implementation Notes

Key DuckDB features used:
- `auto_detect=true` - dialect detection
- `store_rejects=true` - error capture to separate file
- `normalize_names=true` - column name conversion
- `delim='X', skip=N` - manual dialect override for fallbacks
- `allow_quoted_nulls=false` - strict null handling

Error handling:
- Reject file created as `{output_name}_reject_errors.csv`
- Deleted if zero errors (validation.py:72-74)
- Preserved for debugging when errors exist

## Related Decisions

- ADR 002: Fallback delimiter strategy
- ADR 004: Temp file lifecycle (reject file cleanup)
