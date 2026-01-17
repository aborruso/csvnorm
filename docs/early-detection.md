# Early Detection Mechanism

## Overview

csvnorm uses a two-stage validation approach to handle CSV files with non-standard headers or structures:

1. **Early Detection** - Pre-validates first 5 lines to detect anomalies
2. **Fallback Mechanism** - Tries common delimiter/skip combinations if standard sniffing fails

## Problem Statement

CSV files may have:
- Title rows without delimiters (e.g., "Population data for 2025")
- Multiple header rows
- Metadata rows before actual data

DuckDB's automatic dialect detection can fail or miss these issues if:
- The sample size is small and doesn't include malformed rows
- The file has consistent structure after skipping problematic rows

## Early Detection Algorithm

### Input
- CSV file path (local files only)
- Number of lines to analyze (default: 5)

### Process

1. **Read first N lines** (default 5)
2. **Count separators per line** for common delimiters: `,`, `;`, `|`, `\t`
3. **Identify dominant delimiter** in lines 2-N (data lines)
   - Sum occurrences of each delimiter across data lines
   - Select delimiter with most occurrences
4. **Calculate average count** of dominant delimiter in data lines
5. **Compare line 1 with data pattern**
   - Anomaly if line 1 has < 50% of average delimiter count

### Output

If anomaly detected:
```python
{
    "delim": ";",  # Detected delimiter
    "skip": 1      # Number of rows to skip
}
```

If no anomaly: `None`

## Example

### File Structure

```
Popolazione residente per età e sesso al 1° gennaio 2025
"Codice comune";"Comune";"Età";"Totale maschi";"Totale femmine";"Totale"
"028001";"Abano Terme";0;57;48;105
"028001";"Abano Terme";1;59;51;110
"028001";"Abano Terme";2;66;44;110
```

### Detection Process

1. **Line 1**: `0` semicolons (title row)
2. **Lines 2-5**: `5` semicolons each (data rows)
3. **Average in data**: `5.0`
4. **Comparison**: `0 < (5.0 * 0.5)` → Anomaly detected
5. **Suggestion**: `{"delim": ";", "skip": 1}`

## Fallback Mechanism

If early detection doesn't find an anomaly OR suggested config fails, csvnorm tries these configurations in order:

```python
FALLBACK_CONFIGS = [
    {"delim": ";", "skip": 1},
    {"delim": ";", "skip": 2},
    {"delim": "|", "skip": 1},
    {"delim": "|", "skip": 2},
    {" delim": "\t", "skip": 1},
    {"delim": "\t", "skip": 2},
]
```

Each config is tested with:
- `ignore_errors=true` - Allow processing despite malformed rows
- `store_rejects=true` - Capture malformed rows for reporting

## Integration Points

### validate_csv()

1. Check if file is local (skip for remote URLs)
2. Run `_detect_header_anomaly(file_path)`
3. If anomaly detected, try suggested config first
4. If suggestion fails or no anomaly, try standard sniffing
5. If standard fails, try fallback configs

### normalize_csv()

1. Receive `fallback_config` from validate_csv()
2. If `fallback_config` provided:
   - Add `delim`, `skip`, and `ignore_errors=true` to read options
   - Export reject_errors if `reject_file` parameter provided
3. If normalization fails without fallback, try fallback configs

## Error Handling

### Malformed Rows

Files with malformed rows are processed with:
- `store_rejects=true` - DuckDB captures rejected rows
- `ignore_errors=true` - Processing continues despite errors
- Output: `*_reject_errors.csv` with details of malformed rows

### Exit Codes

- `0` - Success (no rejected rows)
- `1` - Success with validation errors (rejected rows exported)

## Configuration Parameters

### Threshold

**Anomaly detection**: Line 1 has < 50% of average delimiter count

Example:
- Data lines average: 5 semicolons
- Threshold: 2.5 semicolons
- Line 1 with 0 or 1 semicolons triggers anomaly

### Analysis Window

**Default**: 5 lines
- Line 1: Tested for anomaly
- Lines 2-5: Used to determine dominant pattern

Minimum: 3 lines required (1 test + 2 for pattern)

## Limitations

1. **Remote files**: Early detection only works for local files
2. **Empty lines**: Filtered out before analysis
3. **Very short files**: Need at least 3 lines for meaningful detection
4. **Complex structures**: Detection targets simple title row scenarios
5. **UTF-8 encoding**: Early detection reads with UTF-8 (errors ignored)

## Performance

- **Overhead**: Negligible (reads only first 5 lines)
- **Benefit**: Avoids full file scan when DuckDB sniffing works
- **Trigger**: Only for local files with potential anomalies

## Future Enhancements

- Remote file support (via HTTP range requests)
- Configurable threshold and analysis window
- Detection of multiple title rows (skip > 1 automatic)
- Pattern recognition for common metadata formats
- Machine learning-based dialect detection
