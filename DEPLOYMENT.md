# Deployment Checklist

Procedure to release a new version to PyPI.

## Prerequisites

**IMPORTANT**: Always use `uv` and the project venv, never `pip3 --break-system-packages`.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install build and twine in the project venv
source .venv/bin/activate
uv pip install build twine
```

## Full Procedure

### 1. Update version

Update the version number in `pyproject.toml`:

```toml
[project]
version = "0.3.0"  # <- update here
```

Also align the version in `src/csvnorm/__init__.py`:

```python
__version__ = "0.3.0"  # <- update here
```

### 2. Local tests

**IMPORTANT**: Always use the existing `.venv` with `uv`.

```bash
# Activate venv
source .venv/bin/activate

# Install editable with dev dependencies
uv pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Manual tests
csvnorm test/utf8_basic.csv -f
csvnorm test/latin1_semicolon.csv -d ';' -f -V
```

### 3. Clean previous builds

```bash
rm -rf dist/ build/ src/*.egg-info/
```

### 4. Build the package

```bash
python3 -m build
```

Expected output:
```
dist/
├── csvnorm-0.3.0-py3-none-any.whl
└── csvnorm-0.3.0.tar.gz
```

### 5. Verify build

```bash
# Inspect wheel contents
unzip -l dist/csvnorm-*.whl

# Test install in a clean venv with uv
uv venv test_venv
source test_venv/bin/activate
uv pip install dist/csvnorm-*.whl
csvnorm --version
csvnorm test/utf8_basic.csv -f
deactivate
rm -rf test_venv
```

### 6. Commit and tag Git

```bash
# Commit changes
git add pyproject.toml CHANGELOG.md  # plus any other modified files
git commit -m "chore: bump version to 0.3.0"

# Create tag
git tag -a v0.3.0 -m "Release v0.3.0"

# Push commit and tag
git push origin main
git push origin v0.3.0
```

### 7. Create GitHub Release

**IMPORTANT**: Always create a GitHub release for each version (including patch/subrelease).

```bash
# Create release on GitHub
gh release create v0.3.0 \
  --title "v0.3.0" \
  --notes "Short description of the main changes"

# Example for patch release
gh release create v0.3.1 \
  --title "v0.3.1" \
  --notes "CLI flags improvements: -k for --keep-names, -V for --verbose, -v for --version"
```

### 8. Upload to PyPI

**TestPyPI (recommended):**

```bash
# Upload to TestPyPI
python3 -m twine upload --repository testpypi dist/*

# Username: __token__
# Password: <TestPyPI token>

# Verify at https://test.pypi.org/project/csvnorm/

# Test install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ csvnorm
```

**Upload to PyPI:**

```bash
# Upload to PyPI
python3 -m twine upload dist/*

# Username: __token__
# Password: <PyPI token>

# Verify at https://pypi.org/project/csvnorm/
```

**Note for Codex CLI:**
- Do not test or experiment with filesystem operations (e.g., `os.rename()`); just run the standard commands.
- Credentials are already configured in `~/.pypirc` or the keyring: do not pass `TWINE_USERNAME/TWINE_PASSWORD`.
- Do not use `--repository-url` or `--repository testpypi` unless strictly necessary.

### 9. Post-release

```bash
# Update LOG.md
echo "## $(date +%Y-%m-%d)\n\n- Released v0.3.0\n" | cat - LOG.md > temp && mv temp LOG.md

# Verify public install
pip install --upgrade csvnorm
csvnorm --version
```

**Note:** for v0.3.6 the PyPI upload was completed manually.

## Troubleshooting

**Error "File already exists":**
- Increment version in `pyproject.toml`
- PyPI does not allow re-upload of the same version

**Import errors after install:**
- Verify package structure in `src/`
- Check `[tool.setuptools.packages.find]` in `pyproject.toml`

**Missing dependencies:**
- Verify `dependencies` in `pyproject.toml`
- Test in a clean venv before upload

## Notes

- Never commit files in `dist/` to the repo
- Keep `.gitignore` up to date
- Always use `python3 -m build` (not `setup.py`)
- PyPI tokens stored in `~/.pypirc` (optional)
