# Release v{VERSION}

## ⚠️ Breaking Changes

<!-- List breaking changes here. If none, remove this section -->

- **{Feature}**: {Description of the breaking change and migration path}
- **{API}**: {What changed and how to update existing code}

### Migration Guide

```bash
# Example: How to migrate from old to new behavior
# Before (v1.x.x):
csvnorm input.csv --old-flag

# After (v2.x.x):
csvnorm input.csv --new-flag
```

---

## ✨ New Features

- {Feature description}
- {Feature description}

## 🐛 Bug Fixes

- {Bug fix description}
- {Bug fix description}

## 📚 Documentation

- {Documentation updates}

## 🔧 Internal Changes

- {Refactoring, dependencies updates, etc.}

---

## Installation

```bash
# PyPI
pip install --upgrade csvnorm

# Verify version
csvnorm --version
```

## Full Changelog

**Full diff**: https://github.com/aborruso/csvnorm/compare/v{PREVIOUS_VERSION}...v{VERSION}

---

## 📢 Stay Updated

- **Watch this repo** → Custom → ✓ Releases to get notified of new versions
- **Breaking changes** are announced in [Discussions → Announcements](https://github.com/aborruso/csvnorm/discussions/categories/announcements)
- **Semantic Versioning**: `MAJOR.MINOR.PATCH`
  - `MAJOR`: Breaking changes (e.g., 1.x.x → 2.0.0)
  - `MINOR`: New features, backward compatible (e.g., 1.0.x → 1.1.0)
  - `PATCH`: Bug fixes (e.g., 1.0.0 → 1.0.1)
