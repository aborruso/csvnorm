# Deployment Checklist

Procedure to release a new version to PyPI.

**NOTE**: Publishing to PyPI is now **fully automated** via GitHub Actions using Trusted Publishing. You only need to push a tag to trigger the release workflow.

## Prerequisites

**IMPORTANT**: Always use `uv` and the project venv for local testing, never `pip3 --break-system-packages`.

```bash
# Install uv (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install dev dependencies in the project venv
source .venv/bin/activate
uv pip install -e ".[dev]"
```

## Full Procedure

**Overview**:
1. Update version in `pyproject.toml` and `src/csvnorm/__init__.py`
2. Run tests locally
3. Commit, tag, and push to GitHub (triggers automatic PyPI publish)
4. **Create GitHub Release manually** (workflow does NOT do this)
5. Verify installation from PyPI

### 1. Update version

Update the version number in `pyproject.toml`:

```toml
[project]
version = "0.3.0"  # <- update here
```

Also align the version in `src/csvnorm/__init__.py`:

```python
__version__ = "0.3.0"  # <- update here

**Sanity check (must match before tagging):**

```bash
rg '^version = "|^__version__ = "' -n pyproject.toml src/csvnorm/__init__.py
```
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

### 3. Commit and tag Git

```bash
# Commit changes
git add pyproject.toml CHANGELOG.md  # plus any other modified files
git commit -m "chore: bump version to 0.3.0"

# Create and push tag (this triggers the GitHub Actions workflow)
git tag v0.3.0
git push origin main
git push origin v0.3.0
```

**The GitHub Actions workflow will automatically:**
1. Run tests on Python 3.9-3.12
2. Build the package
3. Publish to PyPI using Trusted Publishing
4. Create attestations for the release

**⚠️ IMPORTANT**: The workflow does **NOT** create a GitHub Release. You must create it manually in step 4.

You can monitor the workflow at: https://github.com/aborruso/csvnorm/actions

### 4. Create GitHub Release (REQUIRED)

**Wait for the workflow to complete successfully**, then create the GitHub Release:

```bash
# Create release notes file
cat > /tmp/release_notes.md << 'EOF'
## Features
- Feature description

## Bug Fixes
- Fix description

## Changes
- Change description

Full Changelog: https://github.com/aborruso/csvnorm/compare/v0.2.0...v0.3.0
EOF

# Create GitHub Release using gh CLI
gh release create v0.3.0 --repo aborruso/csvnorm \
  --title "v0.3.0" \
  --notes-file /tmp/release_notes.md

# Alternative: Create via web UI
# 1. Go to: https://github.com/aborruso/csvnorm/releases/new
# 2. Select tag: v0.3.0
# 3. Fill in title and description
```

**Why this is required**: The GitHub Release page shows "Latest" releases to users. Without this step, the releases page will still show the old version as latest, even though PyPI has the new version.

### 5. Post-release verification

```bash
# Verify PyPI install (wait a few minutes after workflow completes)
pip install --upgrade csvnorm
csvnorm --version

# Verify GitHub Release is marked as "Latest"
# Visit: https://github.com/aborruso/csvnorm/releases
```

## Fix Post-Release

If you need to fix something after creating a tag/release:

```bash
# 1. Delete GitHub release
gh release delete v0.3.0 -y

# 2. Delete local and remote tag
git tag -d v0.3.0
git push origin :refs/tags/v0.3.0

# 3. Fix the code, commit, and re-tag
git add .
git commit -m "fix: issue description"
git tag v0.3.0
git push origin main
git push origin v0.3.0
```

The workflow will re-run and publish the fixed version.

## Automated Deployment

The project uses **GitHub Actions with Trusted Publishing** to automatically publish to PyPI.

### Workflow: `.github/workflows/publish-pypi.yml`

Triggered on tag push (`v*`):
1. **Build job**: Creates wheel and sdist packages
2. **Test job**: Runs tests on Python 3.9-3.12 matrix
3. **Publish job**: Uploads to PyPI using OIDC trusted publishing (no tokens needed!)

### Trusted Publishing Setup

Configured on PyPI at: https://pypi.org/manage/account/publishing/

- **Owner**: `aborruso`
- **Repository**: `csvnorm`
- **Workflow**: `publish-pypi.yml`
- **Environment**: `pypi`

No API tokens are stored in GitHub secrets. GitHub Actions authenticates directly with PyPI using OIDC.

## Manual Build Testing (Optional)

If you want to test the build locally before releasing:

```bash
# Clean previous builds
rm -rf dist/ build/ src/*.egg-info/

# Build the package
python3 -m build

# Test install in a clean venv with uv
uv venv test_venv
source test_venv/bin/activate
uv pip install dist/csvnorm-*.whl
csvnorm --version
csvnorm test/utf8_basic.csv -f
deactivate
rm -rf test_venv
```

## Troubleshooting

**Workflow fails on "File already exists":**
- You tried to republish an existing version
- Increment version in `pyproject.toml` and push a new tag

**Workflow fails on test matrix:**
- Check that `requires-python` in `pyproject.toml` matches the matrix
- Python 3.8 is no longer supported (requires-python = ">=3.9")

**Trusted publisher authentication fails:**
- Verify configuration at https://pypi.org/manage/account/publishing/
- Ensure workflow name, environment name, and repository match exactly

**Import errors after install:**
- Verify package structure in `src/`
- Check `[tool.setuptools.packages.find]` in `pyproject.toml`

**Missing dependencies:**
- Verify `dependencies` in `pyproject.toml`
- Test in a clean venv before releasing

## Notes

- Never commit files in `dist/` to the repo
- Keep `.gitignore` up to date
- GitHub Actions handles all build and publish steps automatically
- No PyPI tokens needed (using Trusted Publishing with OIDC)
