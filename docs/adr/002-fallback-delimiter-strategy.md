# ADR 002: Fallback Delimiter Detection Strategy

Date: 2025-01 (implemented in v1.1.x)
Status: Accepted

## Context

DuckDB's `auto_detect=true` successfully identifies CSV dialects in ~90% of cases, but fails on:

**Common failure patterns:**
- Files with metadata rows before headers (skip=1 or skip=2 needed)
- Non-comma delimiters combined with complex quoting
- CSV files with inconsistent row lengths in early samples
- Files where DuckDB's sniffing algorithm gives up

Failure symptoms:
- `Error: CSV Error: Separator...` (sniffing failed)
- `Error: CSV Error: Expected Number of Columns...` (wrong delimiter detected)
- Silent failures (reads file but with wrong structure)

User impact:
- Manual delimiter specification required (`-d` flag)
- Poor user experience (tool should "just work")
- Trial-and-error workflow for edge cases

## Decision

Implement **automatic fallback** using common delimiter/skip combinations when auto-detection fails.

Strategy:
1. Try DuckDB auto-detection first (fast path, 90% success)
2. On sniffing error, detect anomalies in first 5 header lines (local files only)
3. Try FALLBACK_CONFIGS sequentially until one succeeds
4. Pass successful config to normalization step
5. If all fallbacks fail, raise original error

Fallback configurations (validation.py:13-22):

```python
FALLBACK_CONFIGS = [
    {"delim": ";", "skip": 1},
    {"delim": ";", "skip": 2},
    {"delim": "|", "skip": 1},
    {"delim": "|", "skip": 2},
    {"delim": "\t", "skip": 1},
    {"delim": "\t", "skip": 2},
]
```

Order rationale:
- Semicolon most common in European CSVs (Excel export locale)
- Pipe delimiter common in ETL pipelines
- Tab delimiter less common but still encountered
- Skip 1-2 covers most metadata row patterns (title, date, notes)

## Alternatives Considered

### 1. Force manual delimiter specification on failure
**Rejected because:**
- Poor UX: user must re-run with `-d` flag
- Trial-and-error required to find correct delimiter
- Doesn't solve skip-rows detection

**Why fallback is better:**
- Automatic recovery in most cases
- User only intervenes on truly ambiguous files

### 2. Use csv.Sniffer (Python stdlib)
**Rejected because:**
- Less reliable than DuckDB's auto-detection
- Doesn't solve the core problem (failures on edge cases)
- Would add complexity without improving success rate

### 3. Try all common delimiters on every file
**Rejected because:**
- Performance penalty: 7× slower (6 fallbacks + auto-detect)
- Unnecessary for 90% of files
- May produce false positives (wrong delimiter validates successfully)

**Why lazy fallback is better:**
- Only pays cost on auto-detect failures
- Fails fast on successful auto-detection

### 4. Machine learning dialect classifier
**Rejected because:**
- Over-engineering for this use case
- Training data collection burden
- DuckDB + fallback already solves 99% of cases

## Consequences

### Positive

**Improved success rate:**
- Before: ~90% files processed without manual intervention
- After: ~99% files processed automatically
- Handles European CSVs (semicolon) without user action

**Preserved config for normalization:**
- `fallback_config` returned by `validate_csv()` (validation.py:178)
- Passed to `normalize_csv()` ensuring same dialect used
- Prevents re-detection failures in normalization step

**Better error messages:**
- Early anomaly detection warns about header issues
- Fallback logs show which config succeeded
- Original error preserved if all fallbacks fail

**User transparency:**
- Verbose mode shows fallback attempts (validation.py:131)
- No silent failures (explicit logging)

### Negative

**Performance penalty on failures:**
- Auto-detect: ~50ms
- Fallback attempt: ~30ms per config
- Worst case: +180ms (6 fallbacks)
- Acceptable given rarity (<10% of files)

**False positives possible:**
- A fallback config might "succeed" with wrong delimiter
- If wrong delimiter produces valid structure by coincidence
- Mitigated by trying delimiter order from most to least common

**Limited skip-rows coverage:**
- Only tries skip=1 and skip=2
- Doesn't handle skip=3+ (very rare)
- User must use `--skip-rows` flag for deeper metadata

**Maintenance burden:**
- FALLBACK_CONFIGS list requires updates if new patterns emerge
- Order matters (most common first for performance)

### Neutral

**Remote file limitation:**
- Early anomaly detection skipped for URLs (requires download)
- Fallback still works but without header analysis
- Trade-off: avoid downloading large files just for sniffing

## Implementation Notes

Early anomaly detection (validation.py:70-103):
- Reads first 5 lines locally with different delimiters
- Compares column counts across delimiters
- Warns if comma produces inconsistent structure
- Only runs for local files (not URLs)

Fallback mechanism (validation.py:124-161):
- Catches `CatalogException` with "Separator" in message
- Tries each FALLBACK_CONFIGS entry sequentially
- Uses `ignore_errors=true` to avoid failing on malformed rows
- Breaks on first successful read
- Re-raises original error if all fail

Config propagation:
- `validate_csv()` returns `fallback_config` (validation.py:178)
- `process_csv()` passes to `normalize_csv()` (core.py:391)
- Ensures consistent dialect between validation and normalization

## Future Considerations

**Potential improvements:**
- Add delimiter frequency analysis (count occurrences in first N lines)
- Support custom fallback configs via CLI flag
- Cache successful config for similar filenames

**Known limitations:**
- Fixed delimiter set (doesn't try exotic delimiters like `^` or `~`)
- Skip-rows hardcoded to 1-2 (could be configurable)
- No support for multi-character delimiters

## Related Decisions

- ADR 001: Use DuckDB for CSV validation (provides auto-detection)
- ADR 003: Stdout vs file modes (affects error reporting strategy)
