# ADR 003: Stdout vs File Output Modes

Date: 2024-12 (v1.0 design)
Status: Accepted

## Context

CLI tools must balance between Unix composability and user-friendly output:

**Unix philosophy requirements:**
- Pipe support: `csvnorm input.csv | grep pattern`
- Silent success: no chatty output interfering with data
- Exit codes: 0 for success, 1 for errors

**User experience requirements:**
- Progress feedback during long operations
- Summary statistics after completion
- Error visibility without debugging

**Conflicting needs:**
- Piping requires clean stdout (data only)
- Interactive use benefits from rich formatting
- Progress bars interfere with pipes
- Error messages needed in both contexts

## Decision

Implement **dual output modes** based on presence of `-o/--output` flag:

### Stdout Mode (default: `csvnorm input.csv`)

**Behavior:**
- Normalized CSV → stdout
- Progress/errors → stderr
- Reject file → temp directory (deleted on success)
- No rich formatting (pipe-friendly)
- Exit 0 even if validation errors (output still produced)

**Use case:** Unix pipelines, command composition

```bash
csvnorm data.csv | csvcut -c name,age | csvlook
```

### File Mode (with `-o`: `csvnorm input.csv -o output.csv`)

**Behavior:**
- Normalized CSV → specified file
- Success summary → stdout (rich table)
- Reject file → output directory (preserved if errors)
- Rich formatting enabled (colors, borders)
- Exit 0 even if validation errors (output file created)

**Use case:** Interactive processing, data preparation

```bash
csvnorm messy.csv -o clean.csv
# Shows: ✓ Success table with stats
```

## Alternatives Considered

### 1. Always use rich output
**Rejected because:**
- Breaks Unix composability
- Pipe consumers receive ANSI codes and formatting
- Common pattern `csvnorm f.csv | tool` fails

**Example failure:**

```bash
csvnorm data.csv | head -5
# Output polluted with:
# ╭─────────────────╮
# │ Processing...   │
# ╰─────────────────╯
```

### 2. Auto-detect TTY and adjust formatting
**Rejected because:**
- Complexity: two code paths for similar output
- Surprising behavior: output changes based on context
- Debugging harder (pipe behavior differs from terminal)
- Doesn't solve "where does normalized data go?" question

**Problems:**
- User pipes to file: `csvnorm data.csv > out.csv`
  - Gets rich formatting in file (wrong)
- User views in terminal: `csvnorm data.csv`
  - Data scrolls past (hard to read)

### 3. Always require `-o` flag
**Rejected because:**
- Violates Unix convention (tools should default to stdout)
- Extra typing for common pipe use case
- Inconsistent with standard tools (cat, grep, awk)

### 4. Separate commands (csvnorm-pipe vs csvnorm-file)
**Rejected because:**
- Confusing UX (which one to use?)
- Duplicate code and documentation
- Package complexity (two entry points)

### 5. Use `--quiet` flag to suppress formatting
**Rejected because:**
- Doesn't solve "where does data go?" problem
- Requires flag for most common use case (pipes)
- Still need two modes internally

## Consequences

### Positive

**Unix composability preserved:**
- Default stdout mode works in pipes
- No ANSI codes or formatting pollution
- Standard behavior for CLI tools

**Rich UX when appropriate:**
- File mode provides helpful summary
- Clear success/error indication
- Statistics aid debugging

**Predictable behavior:**
- `-o` flag clearly signals intent (save to file)
- No auto-detection magic
- Explicit > implicit

**Error handling consistency:**
- stderr always used for messages
- stdout reserved for data (stdout mode)
- Success table on stdout (file mode) doesn't interfere

### Negative

**Two code paths to maintain:**
- Different output logic (core.py:468-546)
- Different error reporting
- Different cleanup strategies

**Reject file location differs:**
- Stdout mode: temp directory, deleted on success
- File mode: output directory, preserved
- May confuse users expecting consistent behavior

**Success table not shown in stdout mode:**
- Users piping data don't see validation stats
- Must check exit code and stderr for errors
- Less informative than file mode

**Documentation complexity:**
- Must explain both modes
- Examples needed for each use case
- Users may not understand when to use `-o`

## Implementation Notes

Mode detection (core.py:50-98):

```python
if output_path is None:
    # Stdout mode
    # ...temp reject file...
    # ...write to stdout...
else:
    # File mode
    # ...output directory reject file...
    # ...show success table...
```

stderr usage (all modes):
- Rich panels for errors (`ui.show_error_panel`)
- Progress messages during processing
- Warnings (encoding conversion, mojibake)
- Validation error summaries

Reject file handling:
- Stdout mode: `tempfile.NamedTemporaryFile(delete=False)` (core.py:387)
- File mode: `output_dir / f"{output_name}_reject_errors.csv"` (core.py:389)
- Deleted if no errors in both modes (core.py:520-525)

Exit codes (core.py:531-546):
- Exit 0: success, even with validation errors (data produced)
- Exit 1: fatal errors only (file not found, invalid args, processing failure)
- Rationale: validation errors don't prevent output creation

## Usage Patterns

**Stdout mode examples:**

```bash
# Pipe to other tools
csvnorm data.csv | csvcut -c name,age

# Redirect to file
csvnorm data.csv > clean.csv

# Process multiple files
for f in *.csv; do csvnorm "$f" | gzip > "clean/$f.gz"; done
```

**File mode examples:**

```bash
# Single file processing
csvnorm messy.csv -o clean.csv

# With options
csvnorm data.csv -o out.csv --skip-rows 2 --fix-mojibake

# Force overwrite
csvnorm input.csv -o output.csv --force
```

## Future Considerations

**Potential improvements:**
- `--stats` flag to show summary in stdout mode (on stderr)
- JSON output format for machine parsing
- `--reject-dir` to customize reject file location

**Known limitations:**
- No way to get rich output AND stdout data
- Reject file location not configurable
- Success table always shown in file mode (no suppress option)

## Related Decisions

- ADR 004: Temp file lifecycle (affects reject file cleanup)
- PRD: Unix philosophy section (composability requirement)
