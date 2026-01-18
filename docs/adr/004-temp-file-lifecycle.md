# ADR 004: Temp File Lifecycle and Cleanup Strategy

Date: 2024-12 (v1.0 design)
Status: Accepted

## Context

csvnorm creates multiple temporary files during processing:

**Validation artifacts:**
- Reject file (DuckDB `store_rejects=true` output)
- Contains rows that failed validation + error descriptions

**Encoding conversion artifacts:**
- UTF-8 converted file (when input is non-UTF-8)
- Intermediate file for mojibake repair

**Remote file artifacts:**
- Downloaded file (for HTTP/HTTPS URLs with `--fix-mojibake`)
- Cached for processing to avoid multiple downloads

**Challenges:**
- Temp files consume disk space
- Failed processing leaves orphaned files
- Reject files needed for debugging but clutter directories
- Different cleanup rules for stdout vs file modes
- Exception handling complicates cleanup

**Requirements:**
- Clean up all temp files on success
- Preserve reject files when validation errors exist
- Clean up on fatal errors (don't leave trash)
- Work correctly on interrupt (Ctrl+C)
- Minimal disk space usage

## Decision

Implement **mode-specific cleanup strategy** with centralized management:

### Temp Directory Management

Create single temp directory per invocation (core.py:394):

```python
temp_dir = Path(tempfile.mkdtemp(prefix="csvnorm_"))
```

All temp files created within this directory:
- UTF-8 converted files
- Downloaded remote files
- Intermediate processing files
- Reject file (stdout mode only)

### Cleanup Rules

**Stdout mode:**
- Reject file → temp directory
- Delete reject file if ≤1 line (header only = no errors)
- Keep reject file if >1 line (has validation errors)
- Delete temp directory if empty after reject file cleanup
- Keep temp directory if reject file preserved

**File mode:**
- Reject file → output directory (not temp)
- Delete reject file if ≤1 line
- Keep reject file if >1 line
- Always delete temp directory (no artifacts kept there)

### Cleanup Timing

Cleanup happens in `finally` block (core.py:556-557):

```python
finally:
    _cleanup_temp_artifacts(use_stdout, reject_file, temp_files)
```

Guarantees cleanup on:
- Successful completion
- Fatal errors (file not found, invalid args)
- Processing exceptions
- User interrupt (Ctrl+C)

## Alternatives Considered

### 1. Never create temp files (in-place processing)
**Rejected because:**
- DuckDB requires reject file path (no in-memory option)
- Encoding conversion needs output file
- Remote files must be downloaded to local filesystem
- No way to atomically replace input file

**Safety concerns:**
- Partial writes corrupt input on failure
- No rollback mechanism

### 2. Always preserve all temp files
**Rejected because:**
- Disk space accumulation
- User confusion (multiple artifacts per run)
- Debugging rarely needs intermediate files

**When useful:**
- Only reject files aid debugging
- UTF-8 files reproducible from input

### 3. Put temp files in system temp directory (`/tmp`)
**Rejected because:**
- Cross-filesystem moves slow (if output on different mount)
- Harder to find reject files (buried in `/tmp/csvnorm_*/`)
- `/tmp` cleanup varies by OS (may persist across reboots)

**Current approach better:**
- Stdout mode: temp directory known location
- File mode: reject file in same directory as output

### 4. Delete temp directory immediately after each use
**Rejected because:**
- Requires creating new directory for each temp file
- More filesystem operations (slower)
- Complicates tracking temp files

**Current approach:**
- Single directory, single cleanup operation
- List of temp files tracked in memory (core.py:404)

### 5. Use context managers for automatic cleanup
**Considered but not fully adopted:**
- Works for single files (`with tempfile.NamedTemporaryFile()`)
- Doesn't handle directory cleanup well
- Conditional preservation (reject files) requires manual logic

**Partial adoption:**
- DuckDB connections use context managers
- File handles use `with` statements
- But temp directory cleanup remains manual

## Consequences

### Positive

**Guaranteed cleanup on errors:**
- `finally` block ensures cleanup even on exceptions
- No orphaned files from crashes
- Ctrl+C handled correctly

**Debugging-friendly:**
- Reject files preserved when needed
- Location predictable (temp dir for stdout, output dir for file mode)
- Can inspect errors without re-running

**Disk space efficient:**
- Empty reject files deleted (validation success)
- Temp directory removed when empty
- Intermediate files always cleaned

**Safe cleanup:**
- Only removes files/directories csvnorm created
- Checks existence before deletion (core.py:327)
- Skips reject file when removing temp directory (core.py:330-336)

### Negative

**Complex cleanup logic:**
- Different rules for stdout vs file mode
- Conditional deletion based on reject file size
- Must track all temp files manually (core.py:404, 413)

**Temp directory may persist:**
- Stdout mode + validation errors = directory kept
- User must manually delete `csvnorm_*` directories
- Not obvious directory can be safely deleted

**No atomic operations:**
- Files written, then cleaned up (not transactional)
- Interrupt between write and cleanup leaves artifacts
- Rare but possible

**Debug mode missing:**
- No `--keep-temp` flag to preserve all artifacts
- Must modify code to debug intermediate files
- Useful for troubleshooting complex failures

## Implementation Notes

Temp file tracking (core.py:404):

```python
temp_files: list[Path] = [temp_dir]
```

Additional temp files appended during processing:
- Downloaded remote files (core.py:407-414)
- UTF-8 converted files (core.py:437-445)

Cleanup function (core.py:314-350):

```python
def _cleanup_temp_artifacts(
    use_stdout: bool,
    reject_file: Path,
    temp_files: list[Path]
) -> None:
```

Cleanup steps:
1. Delete empty reject files (≤1 line)
2. Iterate temp files list
3. Skip reject file parent directory if reject file exists
4. Remove directories recursively (`shutil.rmtree`)
5. Remove regular files (`Path.unlink`)

Reject file size check:

```python
with open(reject_file, "r") as f:
    line_count = sum(1 for _ in f)
if line_count <= 1:
    reject_file.unlink()
```

Rationale: Header line always present, so ≤1 means no errors

## Edge Cases Handled

**Remote file with mojibake:**
- Downloads to temp directory
- Repairs mojibake to second temp file
- Both cleaned up (core.py:407-414)

**Encoding conversion:**
- Creates UTF-8 file in temp directory
- Used as input for validation
- Cleaned up after normalization (core.py:437-445)

**Exception during validation:**
- `finally` block runs regardless
- Reject file may be partial but cleaned if empty
- Temp directory removed

**User interrupts (Ctrl+C):**
- Python signal handler allows `finally` to run
- Temp directory removed (unless reject file preserved)
- Some temp files may remain if interrupt mid-write

## Future Considerations

**Potential improvements:**
- `--keep-temp` flag for debugging
- `--temp-dir` to specify temp directory location
- Atomic file operations (write to temp, rename on success)
- Logging temp file locations in verbose mode

**Known limitations:**
- No cleanup on kill -9 (process terminated abruptly)
- Temp directories with validation errors require manual deletion
- No automatic cleanup of old `csvnorm_*` directories

**Related issues:**
- Consider `tempfile.TemporaryDirectory()` context manager
- Add cleanup reminder in error messages
- Document temp file behavior in README

## Related Decisions

- ADR 003: Stdout vs file modes (determines reject file location)
- ADR 001: DuckDB validation (requires reject file creation)
