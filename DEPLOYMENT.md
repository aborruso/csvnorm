# Deployment Checklist

Procedura per rilasciare una nuova versione su PyPI.

## Pre-requisiti

**IMPORTANTE**: Usare sempre `uv` e il venv del progetto, mai `pip3 --break-system-packages`.

```bash
# Installare uv (se non già presente)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Installare build e twine nel venv del progetto
source .venv/bin/activate
uv pip install build twine
```

## Procedura Completa

### 1. Aggiornare versione

Modificare il numero di versione in `pyproject.toml`:

```toml
[project]
version = "0.3.0"  # <- aggiornare qui
```

Allineare anche la versione in `src/csvnorm/__init__.py`:

```python
__version__ = "0.3.0"  # <- aggiornare qui
```

### 2. Test locali

**IMPORTANTE**: Usare sempre il venv esistente `.venv` con `uv`.

```bash
# Attivare venv
source .venv/bin/activate

# Installare in modalità editable con dipendenze dev
uv pip install -e ".[dev]"

# Eseguire test
pytest tests/ -v

# Test manuale
csvnorm test/utf8_basic.csv -f
csvnorm test/latin1_semicolon.csv -d ';' -f -V
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
├── csvnorm-0.3.0-py3-none-any.whl
└── csvnorm-0.3.0.tar.gz
```

### 5. Verificare build

```bash
# Controllare contenuto wheel
unzip -l dist/csvnorm-*.whl

# Test installazione in venv pulito con uv
uv venv test_venv
source test_venv/bin/activate
uv pip install dist/csvnorm-*.whl
csvnorm --version
csvnorm test/utf8_basic.csv -f
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

### 7. Creare GitHub Release

**IMPORTANTE**: Creare sempre il GitHub release per ogni versione (anche patch/subrelease).

```bash
# Creare release su GitHub
gh release create v0.3.0 \
  --title "v0.3.0" \
  --notes "Breve descrizione dei cambiamenti principali"

# Esempio per patch release
gh release create v0.3.1 \
  --title "v0.3.1" \
  --notes "CLI flags improvements: -k for --keep-names, -V for --verbose, -v for --version"
```

### 8. Upload su PyPI

**Test su TestPyPI (raccomandato):**

```bash
# Upload su TestPyPI
python3 -m twine upload --repository testpypi dist/*

# Username: __token__
# Password: <TestPyPI token>

# Verificare su https://test.pypi.org/project/csvnorm/

# Test installazione da TestPyPI
pip install --index-url https://test.pypi.org/simple/ csvnorm
```

**Upload su PyPI:**

```bash
# Upload su PyPI
python3 -m twine upload dist/*

# Username: __token__
# Password: <PyPI token>

# Verificare su https://pypi.org/project/csvnorm/
```

### 9. Post-release

```bash
# Aggiornare LOG.md
echo "## $(date +%Y-%m-%d)\n\n- Released v0.3.0\n" | cat - LOG.md > temp && mv temp LOG.md

# Verificare installazione pubblica
pip install --upgrade csvnorm
csvnorm --version
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
