# Deployment Checklist

Procedura per rilasciare una nuova versione su PyPI.

## Pre-requisiti

```bash
pip install build twine --break-system-packages
```

## Procedura Completa

### 1. Aggiornare versione

Modificare il numero di versione in `pyproject.toml`:

```toml
[project]
version = "0.3.0"  # <- aggiornare qui
```

### 2. Test locali

```bash
# Creare/attivare venv
python3 -m venv .venv
source .venv/bin/activate

# Installare in modalità editable con dipendenze dev
pip install -e ".[dev]"

# Eseguire test
pytest tests/ -v

# Test manuale
csv_normalize test/utf8_basic.csv -f
csv_normalize test/latin1_semicolon.csv -d ';' -f -v
```

### 3. Pulire build precedenti

```bash
rm -rf dist/ build/ src/*.egg-info/
```

### 4. Build del package

```bash
python3 -m build
```

Output atteso:
```
dist/
├── csv_normalize-0.3.0-py3-none-any.whl
└── csv_normalize-0.3.0.tar.gz
```

### 5. Verificare build

```bash
# Controllare contenuto wheel
unzip -l dist/csv_normalize-*.whl

# Test installazione in venv pulito
python3 -m venv test_venv
source test_venv/bin/activate
pip install dist/csv_normalize-*.whl
csv_normalize --version
csv_normalize test/utf8_basic.csv -f
deactivate
rm -rf test_venv
```

### 6. Commit e tag Git

```bash
# Commit modifiche
git add pyproject.toml CHANGELOG.md  # e altri file modificati
git commit -m "chore: bump version to 0.3.0"

# Creare tag
git tag -a v0.3.0 -m "Release v0.3.0"

# Push commit e tag
git push origin main
git push origin v0.3.0
```

### 7. Upload su PyPI

**Test su TestPyPI (raccomandato):**

```bash
# Upload su TestPyPI
python3 -m twine upload --repository testpypi dist/*

# Username: __token__
# Password: <TestPyPI token>

# Verificare su https://test.pypi.org/project/csv-normalize/

# Test installazione da TestPyPI
pip install --index-url https://test.pypi.org/simple/ csv-normalize
```

**Upload su PyPI:**

```bash
# Upload su PyPI
python3 -m twine upload dist/*

# Username: __token__
# Password: <PyPI token>

# Verificare su https://pypi.org/project/csv-normalize/
```

### 8. Post-release

```bash
# Aggiornare LOG.md
echo "## $(date +%Y-%m-%d)\n\n- Released v0.3.0\n" | cat - LOG.md > temp && mv temp LOG.md

# Verificare installazione pubblica
pip install --upgrade csv-normalize
csv_normalize --version
```

## Troubleshooting

**Errore "File already exists":**
- Incrementare versione in `pyproject.toml`
- PyPI non permette re-upload della stessa versione

**Import errors dopo install:**
- Verificare struttura package in `src/`
- Controllare `[tool.setuptools.packages.find]` in `pyproject.toml`

**Dipendenze mancanti:**
- Verificare `dependencies` in `pyproject.toml`
- Testare in venv pulito prima di upload

## Note

- Non committare mai i file in `dist/` al repo
- Mantenere `.gitignore` aggiornato
- Usare sempre `python3 -m build` (non `setup.py`)
- Token PyPI salvati in `~/.pypirc` (opzionale)
