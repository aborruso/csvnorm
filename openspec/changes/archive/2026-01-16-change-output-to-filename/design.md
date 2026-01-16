# Design: change-output-to-filename

## Architecture

### Current Implementation
- `-o/--output-dir` accepts directory path (defaults to `Path.cwd()`)
- Output filename generated from input: `base_name = to_snake_case(input_name)`
- All output files in same directory: `{output_dir}/{base_name}.csv`

### New Implementation
- `-o/--output-file` accepts full file path (defaults to `{input_base}.csv` in current directory)
- Reject/temp files in same directory as output file
- Path resolution: `Path(args.output_file)` handles both absolute and relative paths

### Path Handling Logic
```python
import tempfile
from pathlib import Path

output_file = Path(args.output_file)  # User-specified full path
output_dir = output_file.parent        # Directory for reject file

# System temp directory for utf8 conversion files
temp_dir = Path(tempfile.mkdtemp(prefix="csvnorm_"))
temp_utf8_file = temp_dir / f"{output_file.stem}_utf8.csv"

# Reject file in output directory (useful for user), always overwritten
reject_file = output_dir / f"{output_file.stem}_reject_errors.csv"
if reject_file.exists():
    reject_file.unlink()  # Remove old reject file
```

## Trade-offs

**Pros:**
- Precise control over output location and filename
- Consistent with common CLI tools (ffmpeg, curl, etc.)
- Better for automation scripts requiring specific output paths

**Cons:**
- Breaking change for existing users
- More verbose for simple cases: `-o output/` becomes `-o output/data.csv`
- Requires users to know input filename to specify output filename

## Dependencies
- Affects `cli.py`, `core.py`, `utils.py::ensure_output_dir()`
- Requires test updates in `test_cli.py`, `test_integration.py`
