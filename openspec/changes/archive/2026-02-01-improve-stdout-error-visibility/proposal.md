# Change: Improve validation error visibility in stdout mode

## Why

When using `csvnorm` in stdout mode with pipes (e.g., `csvnorm url | head`), validation errors are poorly visible or completely lost:

1. **Warning appears after output** - By the time the warning prints to stderr, the pipe may have already closed (e.g., `head` terminates early)
2. **Reject file in /tmp** - The reject file path is printed but it's in a temporary directory that's hard to access and gets deleted
3. **No fail-fast option** - Users who want to abort on validation errors must manually check the warning and exit code

Example problem:
```bash
csvnorm https://example.com/data.csv | head
# Shows data but user never sees "Warning: 136 rows rejected"
# Reject file is in /tmp and inaccessible
```

## What Changes

1. **Early warning display** - Show validation error summary to stderr BEFORE writing output data, making errors visible even in piped scenarios
2. **Reject file in current directory for stdout mode** - Save `reject_errors.csv` in current working directory instead of /tmp when writing to stdout
3. **Add `--strict` mode** - New flag that exits with error code 1 if any validation errors occur, preventing output from being written

**BREAKING**: Reject file location changes for stdout mode (from `/tmp/csvnorm_xxxxx/reject_errors.csv` to `./reject_errors.csv`)

## Impact

- **Affected specs**: processing-summary, output-location, error-handling (new)
- **Affected code**:
  - `src/csvnorm/core.py` - Add pre-validation step, strict mode handling
  - `src/csvnorm/validation.py` - Possible dry-run validation mode
  - `src/csvnorm/cli.py` - Add `--strict` flag
  - `src/csvnorm/ui.py` - Show warning panel before output
  - `tests/` - Update tests for new behavior
