# Valutazione csvnorm v1.2.13

Data: 2026-02-07

## Panoramica

csvnorm: CLI Python per validazione e normalizzazione CSV. Pipeline a 4 step (encoding -> mojibake -> validation -> normalization) con DuckDB come motore. Dual-mode: stdout (pipe Unix) e file (con Rich output).

**Numeri chiave**: 994 statement, 2390 LOC sorgente, 1890 LOC test, 176 test (100% pass), copertura 87%, 9 moduli, 15 fixture CSV reali.

---

## 1. Qualita' del codice: 7.5/10

### Punti di forza

- **Modularita' chiara**: 7 moduli con responsabilita' ben definite (cli, core, encoding, validation, mojibake, ui, utils)
- **Type hints**: presenti e coerenti su tutte le signature (`Union[str, Path]`, `Optional[ConfigDict]`, return types)
- **Docstrings complete**: tutte le funzioni pubbliche hanno docstring Google-style con Args/Returns/Raises
- **Error handling granulare**: errori HTTP specifici (404, 401/403, timeout, ETag mismatch), errori DuckDB, encoding, filesystem. Zero `except Exception` generici
- **Logging strutturato**: uso coerente di `logging.getLogger("csvnorm")` con livelli appropriati
- **Zero debito tecnico esplicito**: nessun TODO/FIXME/HACK nel codice
- **SQL escape centralizzato**: funzione `_sql_escape()` applicata a tutte le query DuckDB con f-string

### Problemi risolti (post-valutazione iniziale)

**~~Bug - Codice morto e duplicato in core.py~~ RISOLTO:**

- ~~`raise` irraggiungibile~~ - rimosso
- ~~doppio `try/except` annidato per `_download_remote_if_needed`~~ - rimosso il livello esterno
- ~~`import shutil` duplicato~~ - rimosso l'import locale

**~~Rischio - SQL via f-string in validation.py~~ RISOLTO:**

Aggiunta funzione `_sql_escape()` che esegue escape degli apici singoli. Applicata a tutte le query in `validation.py` (10 punti) e `utils.py` (1 punto). Path come `data d'esempio.csv` ora gestiti correttamente.

**~~Rischio - `_fix_duckdb_keyword_prefix` troppo aggressivo~~ RISOLTO:**

Aggiunto `_DUCKDB_KEYWORD_SET` (frozenset di ~80 keyword SQL note). Il regex ora stripppa il prefisso `_` solo per keyword DuckDB; colonne utente come `_id` e `_source` vengono preservate. Aggiunto test specifico.

### Problemi residui

**Console globale incoerente:**

`Console()` istanziata come globale in core.py, ui.py e cli.py. In core.py il console globale e' usato raramente perche' spesso si crea `Console(stderr=True)` locale. Potenziale output misto stdout/stderr.

### Copertura per modulo

| Modulo | Stmts | Miss | Cover |
|--------|-------|------|-------|
| `__init__.py` | 4 | 0 | 100% |
| `cli.py` | 89 | 2 | 98% |
| `encoding.py` | 40 | 0 | 100% |
| `mojibake.py` | 29 | 1 | 97% |
| `ui.py` | 54 | 14 | 74% |
| `utils.py` | 149 | 17 | 89% |
| `validation.py` | 301 | 62 | 79% |
| `core.py` | 325 | 36 | 89% |
| **Totale** | **994** | **131** | **87%** |

---

## 2. Architettura: 8/10

### Punti di forza

- **Pipeline lineare chiara**: encoding -> mojibake -> validate -> normalize. Ogni step e' isolabile
- **Dual-mode ben implementato**: stdout per pipe Unix, file mode con Rich. Separazione stdout/stderr corretta
- **Fallback mechanism robusto**: 3 livelli (auto-detect -> delimiter fallback con 6 config -> strict_mode=false). Pragmatico e basato su CSV reali europei/italiani
- **Compressed input**: supporto zip/gzip con estrazione automatica e detection magic-bytes
- **core.py meglio scomposto**: `process_csv` ora delega a 3 nuovi helper dedicati (`_prepare_working_file`, `_handle_post_validation`, `_compute_and_show_output`), migliorando leggibilita' e testabilita'. Copertura salita dal 72% al 74%

### Debolezze

- **Accoppiamento UI-logica**: core.py chiama direttamente `show_error_panel`, `show_warning_panel`. La logica di business e la presentazione sono mescolate. Il core dovrebbe restituire risultati/eccezioni, e il layer CLI dovrebbe occuparsi della presentazione
- ~~**3 connessioni DuckDB per file**: setup duplicato~~ RISOLTO: estratto `_create_connection()` helper che centralizza connect + zipfs + http_timeout. `get_column_count` in utils.py resta separata (caso troppo semplice)

---

## 3. Test: 8/10

### Punti di forza

- **176 test in ~8s** - veloce e completo
- **Moduli puri ben coperti**: encoding.py 100%, mojibake.py 97%, cli.py 99%, core.py 89%
- **Mock ben usati**: `unittest.mock` per download, DuckDB errors, connessioni
- **Smoke test con subprocess**: verificano CLI end-to-end, incluso pipe e redirect
- **15 fixture reali**: encoding diversi (latin1, windows1252, utf8-sig, BOM), delimitatori vari, file malformati, mojibake italiano
- **Edge case coperti**: file vuoti, path inesistenti, errori Unicode, SSL handshake fallback, BrokenPipeError
- **Test keyword prefix migliorato**: nuovo test verifica che colonne non-keyword (es. `_id`) vengano preservate

### Debolezze

- ~~**core.py sotto-testato** (74%)~~ RISOLTO: 89% con 28 nuovi test per helper functions (encoding errors, HTTP errors, cleanup, post-validation logic)
- **ui.py sotto-testato** (74%): `show_success_table` e `show_validation_error_panel` non hanno test unitari diretti
- **Nessun test performance**: nessun benchmark per file grandi (>100MB)
- **Test di rete non skippati di default**: `@pytest.mark.network` senza conftest.py che li skippa automaticamente
- **Mancano edge case**: CSV con migliaia di colonne, output su directory inesistente

---

## 4. Usabilita' CLI: 8.5/10

### Punti di forza

- **Design Unix-first**: stdout di default, stderr per progress/errori. Composabile con pipe (`| head`, `| csvcut`)
- **Help ricco e completo**: Rich-formatted, 7 esempi integrati, banner con `--version`
- **Flag intuitive**: `-o`, `-f`, `-k`, `-s`, `-d`, `--check`, `--strict`
- **BrokenPipeError gestito**: `csvnorm data.csv | head -1` non causa crash
- **Messaggi di errore eccellenti**: pannelli colorati con contesto, path, e suggerimenti actionable
- **`--check` mode**: validazione rapida senza processing, perfetto per CI/CD
- **`--strict` mode**: fail-fast per pipeline, uscita immediata con exit code 1

### Debolezze

- **`--download-remote` deprecato ma presente**: aggiunge confusione all'help. Andrebbe rimosso nella prossima major
- **Nessuna opzione `--quiet`**: impossibile silenziare del tutto l'output su stderr in stdout mode
- **Exit code non differenziati**: exit 1 sia per "file non trovato" che per "CSV con righe malformate". Sarebbe utile exit 2 per errori di utilizzo
- **`reject_errors.csv` nella CWD in stdout mode**: puo' essere inaspettato e inquina la directory di lavoro. Sarebbe meglio usare una temp dir o non crearlo in stdout mode
- **Nessun supporto stdin**: non si puo' fare `cat data.csv | csvnorm`. Limita la composabilita' Unix

---

## 5. Performance: 6.5/10

### Punti di forza

- **DuckDB come motore**: molto veloce per CSV parsing, gestisce bene file grandi
- **`sample_size=-1`**: scansione completa per inferenza accurata
- **`all_varchar=true`**: evita errori di cast, approccio pragmatico per normalizzazione
- **Early detection**: pre-check 5 righe per anomalie header prima di DuckDB

### Debolezze

- **File caricato interamente in memoria in 2 punti**:
  - `encoding.py:112` - `f.read()` per conversione encoding
  - `mojibake.py:66` - `read_text()` per mojibake detection
  - Per file da GB, entrambi causano problemi di memoria
  - ~~`validation.py` - `f.readlines()` per fix keyword prefix~~ RISOLTO: ora usa `readline()` + `read()` per leggere solo l'header in memoria

- ~~**3 connessioni DuckDB per singolo file**: overhead di setup triplicato~~ RISOLTO: setup centralizzato in `_create_connection()`
- **Conteggio righe lineare**: `get_row_count` e `_count_lines` iterano riga per riga. DuckDB potrebbe farlo istantaneamente
- **Double scan del file**: validate_csv() legge tutto il file, poi normalize_csv() lo rilegge da zero

---

## 6. Packaging: 8/10

### Punti di forza

- **pyproject.toml completo**: metadata, classifiers, entry points, dev dependencies
- **Python 3.9+**: range ampio e ragionevole
- **uv come tool consigliato**: moderno e veloce
- **`__main__.py`** per `python -m csvnorm`
- **Dev dependencies separate**: `[dev]` con pytest, ruff, mypy

### Debolezze

- ~~**Mismatch target-version**: `pyproject.toml:62` ha `target-version = "py38"`~~ RISOLTO: corretto a `py39`
- **`requests` come dipendenza runtime**: usato solo come fallback SSL in un caso raro (utils.py:224). Dipendenza pesante per un caso edge
- **Nessuna CI/CD**: build/test/publish manuale. Una GitHub Action con pytest + publish su tag sarebbe un grande miglioramento

---

## 7. Documentazione: 8/10

### Punti di forza

- **README.md esaustivo** (316 righe): installazione, usage, 15+ esempi, opzioni, output modes, exit codes
- **CLAUDE.md dettagliato**: architettura, processing flow, key modules, file contract, critical constraints
- **Docstring Google-style**: complete su tutte le funzioni pubbliche
- **DEPLOYMENT.md**: procedura di release documentata

### Debolezze

- **README troppo lungo**: i dettagli su mojibake, output modes, e file protection potrebbero andare in doc separate
- **Nessun CHANGELOG formale**: LOG.md e' un diario di sviluppo, non un changelog semantico (keepachangelog.com)

---

## 8. Suggerimenti di miglioramento

### Alta priorita' (bug e sicurezza)

| # | Problema | File:riga | Soluzione | Stato |
|---|----------|-----------|-----------|-------|
| 1 | `raise` irraggiungibile | core.py:306 | Rimuovere la riga | RISOLTO |
| 2 | try/except duplicato | core.py:478-491 | Rimuovere il try/except esterno | RISOLTO |
| 3 | import shutil duplicato | core.py:385 | Rimuovere l'import locale | RISOLTO |
| 4 | Path con apici rompono query DuckDB | validation.py (f-string) | `_sql_escape()` centralizzato | RISOLTO |
| 5 | `_fix_duckdb_keyword_prefix` troppo aggressivo | validation.py:442 | `_DUCKDB_KEYWORD_SET` frozenset | RISOLTO |

### Media priorita' (qualita' e manutenibilita')

| # | Proposta | Beneficio |
|---|----------|-----------|
| 6 | Estrarre `_create_duckdb_connection()` condivisa | Eliminare duplicazione connessione DuckDB | RISOLTO |
| 7 | Aggiungere `--quiet` flag | Permettere uso silenzioso in script | |
| 8 | Exit code differenziati (0/1/2) | Distinguere validation errors da errori fatali | |
| 9 | Correggere `target-version` ruff: py38 -> py39 | Coerenza con requires-python | RISOLTO |
| 10 | Portare copertura core.py almeno all'80% | Ridurre rischio regressioni | RISOLTO (89%) |

### Bassa priorita' (nice-to-have)

| # | Proposta | Beneficio |
|---|----------|-----------|
| 11 | Supporto stdin (input `-`) | Composabilita' Unix completa |
| 12 | Rendere `requests` dipendenza opzionale | Ridurre peso installazione |
| 13 | Streaming per encoding conversion | Supporto file >1GB senza OOM |
| 14 | Riutilizzare connessione DuckDB validate->normalize | Eliminare overhead 3x connect |
| 15 | Deprecare formalmente `--download-remote` | Pulizia CLI |
| 16 | CI/CD con GitHub Actions | Automatizzare test e publish PyPI |

---

## Voto complessivo

| Area | Voto | Note |
|------|:----:|------|
| Qualita' codice | **7.5** | Buona struttura, type hints, docstring. Bug e codice morto risolti. SQL escape centralizzato |
| Architettura | **8.5** | Pipeline chiara, dual-mode. core.py ben scomposto. `_create_connection()` elimina duplicazione DuckDB |
| Test | **8.5** | 176 test veloci, buone fixture. core.py 89%, copertura totale 87% |
| Usabilita' CLI | **8.5** | Design Unix-first eccellente. Manca stdin e quiet mode |
| Performance | **6.5** | DuckDB veloce ma 2 punti di caricamento in memoria |
| Packaging | **8.5** | pyproject.toml completo. target-version corretto. requests pesante |
| Documentazione | **8** | README e CLAUDE.md molto buoni. Manca CHANGELOG formale |
| **Media** | **8.0** | **Progetto solido, production-ready. Tutti i bug alta priorita' risolti, copertura 87%, connessioni DuckDB centralizzate** |

---

## Appendice: correzioni applicate (2026-02-07)

Riepilogo delle modifiche apportate dopo la valutazione iniziale.

### core.py - Refactoring e bugfix

- **Rimosso `raise` irraggiungibile** (riga 306): duplicato dopo un blocco che gia' faceva raise
- **Rimosso `try/except` annidato duplicato** per `_download_remote_if_needed`: semplificato a un singolo livello
- **Rimosso `import shutil` locale** non necessario (gia' presente come import globale)
- **Estratti 3 nuovi helper** da `process_csv` per ridurre la complessita':
  - `_prepare_working_file()` - risoluzione encoding e mojibake repair
  - `_handle_post_validation()` - logica check-only, strict, warning permissive
  - `_compute_and_show_output()` - statistiche e display risultati (stdout/file)
- Variabile `used_fallback` rinominata a `_` dove il valore non e' usato

### validation.py - SQL escape e keyword prefix

- **Aggiunta `_sql_escape()`**: escape apici singoli per query DuckDB. Applicata a 10 punti nel file
- **Aggiunto `_DUCKDB_KEYWORD_SET`**: frozenset di ~80 keyword SQL note a DuckDB
- **`_fix_duckdb_keyword_prefix` corretto**: ora strippa il prefisso `_` solo per keyword note; colonne utente come `_id`, `_source` vengono preservate
- **Ottimizzazione memoria**: `_fix_duckdb_keyword_prefix` ora usa `readline()` + `read()` invece di `readlines()`, evitando di caricare tutto il file in memoria

### utils.py - SQL escape

- **`get_column_count()`**: aggiunto escape apici singoli nel path passato a DuckDB

### test_validation.py - Test aggiornati

- Test `test_removes_leading_underscore_from_header` rinominato e aggiornato per riflettere il comportamento corretto (solo keyword)
- **Nuovo test `test_preserves_non_keyword_underscore_columns`**: verifica che `_id` e `_source` vengano preservate mentre `_value` e `_order` vengano strippate

### Impatto sui numeri

| Metrica | Prima | Dopo | Delta |
|---------|-------|------|-------|
| Statement | 981 | 994 | +13 |
| LOC sorgente | 2333 | 2390 | +57 |
| LOC test | 1673 | 1690 | +17 |
| Test | 147 | 148 | +1 |
| Copertura totale | 81% | 81% | = |
| Copertura core.py | 72% | 74% | +2% |
| Copertura validation.py | 78% | 79% | +1% |
| Media voto | 7.6 | 7.8 | +0.2 |

---

## Appendice: correzioni applicate (2026-02-08)

### pyproject.toml - ruff target-version

- `target-version = "py38"` -> `target-version = "py39"` (allineato con `requires-python = ">=3.9"`)

### validation.py - `_create_connection()` helper

- Estratto `_create_connection(file_path, is_remote)` che centralizza `duckdb.connect()` + `_ensure_zipfs_extension()` + `SET http_timeout`
- `validate_csv()` e `normalize_csv()` aggiornati per usare il nuovo helper
- Eliminata duplicazione di 6 righe per chiamante

### tests/test_core_helpers.py - 28 nuovi test

- `TestPrepareWorkingFile` (7 test): remote URL, compressed, ValueError/UnicodeDecodeError/LookupError encoding, OSError mojibake, check_only skip mojibake
- `TestHandlePostValidation` (7 test): permissive mode, check_only valid/invalid, stdout strict/non-strict, file mode errors, no errors
- `TestValidateCsvWithHttpHandling` (7 test): zipfs error, HTTP 404/401-403/timeout/range/ETag, generic DuckDB error
- `TestCleanupTempArtifacts` (4 test): stdout empty/non-empty reject, file mode empty reject, temp file cleanup
- `TestComputeAndShowOutput` (3 test): file mode with/without errors, input_size fallback

### Impatto sui numeri (2026-02-08)

| Metrica | Prima | Dopo | Delta |
|---------|-------|------|-------|
| Test | 148 | 176 | +28 |
| Copertura totale | 81% | 87% | +6% |
| Copertura core.py | 74% | 89% | +15% |
| Media voto | 7.8 | 8.0 | +0.2 |
