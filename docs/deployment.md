# Deployment & Development Notes

This document contains practical notes for developing and deploying the CSV Normalizer Utility.

## Installation Methods

### Production: Makefile (Recommended)

```bash
# Full install with all dependencies
make install

# Custom prefix
make install PREFIX=~/.local

# Lightweight (script only, manage deps separately)
make install_light
```

**What it does:**
- Installs DuckDB CLI (downloads from GitHub releases)
- Installs Python dependencies (charset-normalizer, duckdb)
- Copies `script/prepare.sh` to `$PREFIX/bin/csv_normalizer`
- Makes it executable and globally available

### Development: Python Editable Install

```bash
# Using pip
python3 -m venv venv
source venv/bin/activate
pip install -e .

# Using uv (faster)
uv venv venv
source venv/bin/activate
uv pip install -e .
```

**What it does:**
- Installs charset-normalizer dependency
- Creates `csv_normalizer` command that calls `csv_normalizer_wrapper.py`
- Wrapper executes `script/prepare.sh` with all arguments
- Changes to `prepare.sh` are immediately reflected (editable mode)

**Important:** Only editable mode (`-e` flag) works for pip installation. Non-editable install fails because bash script cannot be packaged in wheel/sdist without complex setuptools configuration.

## Python Packaging Details

### Files Created

**pyproject.toml:**
- Build system: setuptools ≥61.0
- Package name: `csv-normalizer` (PyPI-friendly hyphenated name)
- Version: 0.1.0
- Dependencies: charset-normalizer ≥3.0.0
- Optional dev deps: duckdb ≥0.9.0
- Entry point: `csv_normalizer = csv_normalizer_wrapper:main`

**csv_normalizer_wrapper.py:**
- Python wrapper script
- Searches for `script/prepare.sh` in multiple locations:
  1. `<wrapper_dir>/script/prepare.sh` (editable install)
  2. `<wrapper_dir>/prepare.sh` (direct install)
  3. `<wrapper_dir>/../script/prepare.sh` (site-packages)
- Executes bash script with `subprocess.run()`
- Passes through all CLI arguments
- Handles exit codes and keyboard interrupts

**MANIFEST.in:**
- Includes `README.md`, `LICENSE`, `script/prepare.sh` in source distribution
- Required for sdist builds (though we primarily use editable installs)

### Why Not Regular `pip install .`?

The tool is bash-based, not Python-based. Packaging a bash script in a Python wheel requires:
- Custom build hooks to include binary data
- Complex setuptools data_files configuration
- Platform-specific installation paths

For a bash utility, the Makefile provides better control and is more maintainable.

## Testing Installation

### Test Editable Install

```bash
# Create clean environment
uv venv /tmp/test_env
source /tmp/test_env/bin/activate

# Install in editable mode
uv pip install -e .

# Test command
csv_normalizer --help
csv_normalizer test/utf8_basic.csv -o /tmp/test_output

# Verify output
ls -lh /tmp/test_output/
cat /tmp/test_output/utf8_basic.csv

# Cleanup
deactivate
rm -rf /tmp/test_env /tmp/test_output
```

### Test Makefile Install

```bash
# Install to custom prefix (no sudo)
make install PREFIX=~/.local

# Verify
which csv_normalizer
csv_normalizer --help

# Test
csv_normalizer test/utf8_basic.csv

# Uninstall
make uninstall PREFIX=~/.local
```

## Development Workflow

### Making Changes to Script

```bash
# Edit the bash script
vim script/prepare.sh

# Run shellcheck
shellcheck script/prepare.sh

# Test locally
script/prepare.sh test/utf8_basic.csv

# Or if installed in editable mode
csv_normalizer test/utf8_basic.csv

# Run test suite
make test

# Commit changes
git add script/prepare.sh
git commit -m "Fix: description of change"
```

### Version Bumping

Edit version in:
1. `pyproject.toml` - `version = "x.y.z"`
2. `LOG.md` - Add new version section

### Adding Dependencies

**Runtime dependency:**
```toml
# pyproject.toml
dependencies = [
    "charset-normalizer>=3.0.0",
    "new-package>=1.0.0",
]
```

**Makefile dependency:**
```makefile
# Makefile
PYTHON_DEPS = charset_normalizer duckdb new-package
```

**DuckDB CLI version:**
```makefile
# Makefile
DUCKDB_VERSION = v1.1.3  # Update as needed
```

## Common Issues

### Issue: `csv_normalizer: command not found`

**Solution 1 (editable install):**
```bash
# Ensure virtual environment is activated
source venv/bin/activate
```

**Solution 2 (Makefile install):**
```bash
# Check if install directory is in PATH
echo $PATH | grep -o "$HOME/.local/bin"

# If not, add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.local/bin:$PATH"
```

### Issue: `Error: required command not found: normalizer`

**Solution:**
```bash
# Install charset-normalizer
pip3 install charset-normalizer

# Or in venv
uv pip install charset-normalizer
```

### Issue: `Error: required command not found: duckdb`

**Solution:**
```bash
# Use full Makefile install
make install

# Or manually download DuckDB CLI
# See: https://github.com/duckdb/duckdb/releases
```

### Issue: Python package install fails with "externally-managed-environment"

**Solution:**
```bash
# Use virtual environment
uv venv venv
source venv/bin/activate
uv pip install -e .

# Or use Makefile (installs system-wide)
make install
```

## CI/CD Notes

### Automated Testing

```bash
# Syntax check
bash -n script/prepare.sh

# ShellCheck
shellcheck script/prepare.sh

# Smoke tests
for file in test/*.csv; do
    script/prepare.sh "$file" -o /tmp/test_output
done

# Note: If outputs already exist in /tmp/test_output, re-run with --force or clean the directory.
```

### Future: PyPI Publishing

To publish to PyPI (when ready):

1. **Build source distribution:**
   ```bash
   python3 -m build --sdist
   ```

2. **Test in isolated environment:**
   ```bash
   uv venv /tmp/clean_env
   source /tmp/clean_env/bin/activate
   uv pip install -e .
   csv_normalizer --help
   ```

3. **Upload to PyPI:**
   ```bash
   twine upload dist/*
   ```

**Note:** Currently only editable installs work. Regular PyPI install would require packaging bash script as data file.

## Environment Variables

None currently used, but could add:

```bash
# Future: Override default DuckDB path
export CSV_NORMALIZER_DUCKDB_PATH=/custom/path/to/duckdb

```

## Platform Notes

**Linux:** Primary target, fully supported

**macOS:** Should work with minor adjustments:
- Install GNU coreutils for compatible `file` command
- Verify `iconv` encoding name compatibility

**Windows/WSL:** Works in WSL, native Windows not supported (bash required)

## Performance Considerations

**Memory:**
- DuckDB loads CSV into memory for validation
- Large files (>1GB) may require significant RAM
- Use `sample_size=-1` for complete validation (current default)

**Disk I/O:**
- Temporary UTF-8 conversion file created if encoding conversion needed
- Cleaned up automatically after processing

**Parallelization:**
- Single-threaded bash script
- DuckDB may use multiple cores internally
- Future: Add parallel processing for multiple files
