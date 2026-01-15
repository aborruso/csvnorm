# Modern CLI Enhancement Plan

## Goal
Add modern UX features (rich formatting, progress bars) to csv_normalize while maintaining simplicity and scriptability.

## Constraints
- Keep argparse (no typer rewrite)
- No forced interactivity (must remain scriptable)
- Maintain all current CLI args and exit codes
- Minimal complexity

## Phase 1: Dependencies

- [ ] Add `rich` to pyproject.toml dependencies
- [ ] Add optional `pyfiglet` for verbose mode banner

## Phase 2: Core Enhancements

- [ ] Replace print() with rich Console in core.py
- [ ] Add progress spinner/bar for multi-step processing
- [ ] Format errors with Rich panels
- [ ] Add success summary table at end

## Phase 3: Optional Visual Enhancements

- [ ] Add banner in verbose mode (pyfiglet)
- [ ] Color-code log levels (info=cyan, success=green, error=red)

## Phase 4: Testing & Polish

- [ ] Test with existing test files
- [ ] Verify exit codes unchanged
- [ ] Verify scriptable (no prompts)
- [ ] Update README if needed

## Implementation Notes

**Files to modify:**
- `pyproject.toml` - add dependencies
- `src/csv_normalizer/core.py` - replace print() with rich Console
- `src/csv_normalizer/cli.py` - optional banner in verbose mode

**Rich features to use:**
- Console for colored output
- Progress for step tracking
- Panel for errors
- Table for final summary

**NOT using:**
- questionary (no interactivity needed)
- typer (too big a rewrite)

## Questions

None - approach is straightforward and low-risk.

---

## Review

### Summary

Successfully enhanced CSV Normalizer CLI with modern UX features using the `rich` library. All changes are backward-compatible and maintain existing behavior.

### Changes Made

**Dependencies (pyproject.toml):**
- Added `rich>=13.0.0` as required dependency
- Added `pyfiglet>=1.0.0` as optional dependency under `[banner]` extra

**Core Processing (core.py):**
- Replaced all `print()` calls with `rich.Console`
- Added progress spinner for 4-step pipeline (transient, non-blocking)
- Formatted all errors with `Panel` (red border)
- Formatted warnings with `Panel` (yellow border)
- Added success summary `Table` at completion showing:
  - Input/Output paths
  - Detected encoding
  - Delimiter (if non-comma)
  - Header normalization status

**CLI Interface (cli.py):**
- Added optional ASCII art banner in verbose mode (requires pyfiglet)
- Banner gracefully degrades if pyfiglet not installed

**Logging (utils.py):**
- Replaced basic StreamHandler with `RichHandler`
- Enabled rich tracebacks for better error debugging
- Color-coded log levels automatically

### Testing Results

All existing functionality preserved:
- ✓ Exit code 0 on success
- ✓ Exit code 1 on errors
- ✓ No interactive prompts (fully scriptable)
- ✓ UTF-8 encoding detection/conversion works
- ✓ CSV validation with DuckDB works
- ✓ Error panels display correctly
- ✓ Success table shows all relevant info
- ✓ Banner appears in verbose mode (with pyfiglet)
- ✓ Graceful degradation without pyfiglet

### Files Modified

- `pyproject.toml` - dependencies
- `src/csv_normalizer/core.py` - rich output formatting
- `src/csv_normalizer/cli.py` - banner support
- `src/csv_normalizer/utils.py` - rich logging
- `README.md` - documented new features

### Installation Note

Users can install with banner support via:

```bash
pip install csv-normalize[banner]
```

Or just the base tool (banner will be skipped):

```bash
pip install csv-normalize
```
