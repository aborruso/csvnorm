# Rename Project: csv-normalize → csvnorm

## Goal
Rinominare il progetto da "csv-normalize" / "csv_normalize" / "csv_normalizer" a "csvnorm" in tutto il codice e la documentazione.

## Plan

Eseguire un rename completo e sistematico del progetto:
1. Rinominare directory package da `csv_normalizer` a `csvnorm`
2. Aggiornare pyproject.toml (nome package, script CLI)
3. Aggiornare tutti gli import Python
4. Aggiornare documentazione (README, CLAUDE, PRD, DEPLOYMENT, LOG)
5. Aggiornare test
6. Verificare e aggiornare altri file (openspec, docs, .github)

## Tasks

### Phase 1: Package Structure
- [ ] Rinominare directory `src/csv_normalizer/` → `src/csvnorm/`
- [ ] Aggiornare `pyproject.toml`:
  - name: `csv-normalize` → `csvnorm`
  - scripts: `csv_normalize` → `csvnorm`
  - PyPI URL references
  - description e keywords se necessario
- [ ] Pulire `src/csv_normalize.egg-info/` obsoleto

### Phase 2: Python Code
- [ ] Aggiornare import in `src/csvnorm/__init__.py`
- [ ] Aggiornare import in `src/csvnorm/__main__.py`
- [ ] Aggiornare import in `src/csvnorm/cli.py`
- [ ] Aggiornare import in `src/csvnorm/core.py`
- [ ] Aggiornare import in `src/csvnorm/encoding.py`
- [ ] Aggiornare import in `src/csvnorm/validation.py`
- [ ] Aggiornare import in `src/csvnorm/utils.py`

### Phase 3: Test Files
- [ ] Aggiornare import in `tests/__init__.py`
- [ ] Aggiornare import in `tests/test_encoding.py`
- [ ] Aggiornare import in `tests/test_integration.py`
- [ ] Aggiornare import in `tests/test_utils.py`

### Phase 4: Documentation
- [ ] Aggiornare README.md (nome package, install commands, esempi)
- [ ] Aggiornare CLAUDE.md (package name, commands, structure)
- [ ] Aggiornare PRD.md (nomi tool e script)
- [ ] Aggiornare DEPLOYMENT.md (nomi file dist, PyPI URL)
- [ ] Aggiornare LOG.md (aggiungere entry per rename v0.3.0)

### Phase 5: Other Files
- [ ] Verificare e aggiornare file openspec (se necessario)
- [ ] Verificare e aggiornare file in docs/ (se necessario)
- [ ] Verificare e aggiornare .github/ workflows (se necessario)

### Phase 6: Verification
- [ ] Verificare che `pytest tests/ -v` passi
- [ ] Verificare che `csvnorm --version` funzioni
- [ ] Verificare che `csvnorm test/utf8_basic.csv -f` funzioni

## Review

### Summary

Completato con successo il rename completo del progetto da `csv-normalize` / `csv_normalize` / `csv_normalizer` a `csvnorm`.

### Changes Made

**1. Package Structure**
- ✓ Directory rinominata: `src/csv_normalizer/` → `src/csvnorm/`
- ✓ Rimosso file obsoleto: `src/csv_normalize.egg-info/`

**2. Configuration (pyproject.toml)**
- ✓ Package name: `csv-normalize` → `csvnorm`
- ✓ Version bump: `0.2.3` → `0.3.0`
- ✓ Script entry point: `csv_normalize` → `csvnorm`
- ✓ Python version: `>=3.8` → `>=3.9` (per compatibilità con pyfiglet)

**3. Python Code (src/csvnorm/)**
- ✓ Tutti gli import aggiornati: `from csv_normalizer import ...` → `from csvnorm import ...`
- ✓ Logger names aggiornati: `"csv_normalizer"` → `"csvnorm"`
- ✓ CLI prog name: `"csv_normalize"` → `"csvnorm"`
- ✓ Banner text: `"CSV Normalize"` → `"csvnorm"`

**4. Test Files (tests/)**
- ✓ Tutti gli import aggiornati nei test
- ✓ Test suite completa: 35/35 test passano ✓

**5. Documentation**
- ✓ README.md: package name, install commands, esempi
- ✓ CLAUDE.md: package name, commands, structure
- ✓ PRD.md: riferimenti al tool
- ✓ DEPLOYMENT.md: nomi file dist, PyPI URL
- ✓ LOG.md: entry v0.3.0 con breaking changes e migration guide

**6. Other Files**
- ✓ openspec/: 3 files aggiornati
- ✓ docs/: 2 files aggiornati
- ✓ .github/: 2 files aggiornati

**7. Cleanup**
- ✓ Rimosso `/home/aborruso/.local/bin/csv_normalizer`
- ✓ Disinstallato `csv-normalize` da uv tool

### Verification

```bash
# Version check
csvnorm --version
# Output: csvnorm 0.3.0

# Test execution
pytest tests/ -v
# Result: 35 passed in 0.36s

# Manual test
csvnorm test/utf8_basic.csv -f
# Result: Success ✓
```

### Breaking Changes

- **CLI command**: `csv_normalize` → `csvnorm`
- **Package name**: `csv-normalize` → `csvnorm` (PyPI)
- **Python imports**: `from csv_normalizer import ...` → `from csvnorm import ...`

### Migration for Users

```bash
# Uninstall old package
pip uninstall csv-normalize

# Install new package
pip install csvnorm

# Update scripts: replace csv_normalize with csvnorm
# Update imports: from csv_normalizer → from csvnorm
```

### Ready for Release

Il progetto è pronto per essere rilasciato come v0.3.0 su PyPI con il nuovo nome `csvnorm`.
