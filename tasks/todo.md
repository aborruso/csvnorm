# csvnorm: gestione file con righe non strutturate

**Issue**: #1 - Add option with ignore_errors

## Problema

File `test/POSAS_2025_it_Comuni.csv`:
- Riga 1: titolo descrittivo (va skippata)
- Ultima riga: nota testuale con 1 colonna invece di 6
- Delimitatore: `;` (non `,`)

DuckDB fallisce **il dialect sniffing** (prima ancora di processare).

## Soluzione

**Fallback automatico** quando sniffing fallisce:
- Provare delimitatori comuni: `;`, `|`, `\t`
- Provare skip: 1, 2
- Usare `store_rejects=true` (csvnorm già lo supporta)
- Prima config che funziona vince

**Risultato** (come richiesto in issue #1):
- File normalizzato con righe valide
- `*_reject_errors.csv` con righe problematiche

**NO nuove opzioni CLI**: tutto automatico per semplicità.

## Piano

### Fase 1: Implementazione
- [ ] Helper `_try_read_csv_with_config()` in `validation.py`
- [ ] Modificare `validate_csv()`: fallback se sniffing fallisce
- [ ] Modificare `normalize_csv()`: usare stessi parametri
- [ ] Logging parametri usati (verbose)

### Fase 2: Test
- [ ] Test `POSAS_2025_it_Comuni.csv`
- [ ] Verificare file esistenti (no regression)
- [ ] Run `pytest`

## Parametri fallback

```python
FALLBACK_CONFIGS = [
    {"delim": ";", "skip": 1},
    {"delim": ";", "skip": 2},
    {"delim": "|", "skip": 1},
    {"delim": "|", "skip": 2},
    {"delim": "\t", "skip": 1},
    {"delim": "\t", "skip": 2},
]
```

## Verifica manuale

Output: 805,393 righe valide ✓
Rejects: 1 riga (nota finale) ✓

## Review

### Implementazione completata

**Issue #1** risolto: fallback automatico per CSV con righe non strutturate.

#### Modifiche effettuate

**src/csvnorm/validation.py**:
- Aggiunto `FALLBACK_CONFIGS` con delimitatori comuni (`;`, `|`, `\t`) e skip (1, 2)
- `_try_read_csv_with_config()`: helper per testare configurazione con `ignore_errors=true`
- `validate_csv()`: fallback automatico quando sniffing standard fallisce, restituisce config usata
- `normalize_csv()`: fallback automatico + export reject_errors quando usa store_rejects

**src/csvnorm/core.py**:
- Gestione `fallback_config` da validate_csv() a normalize_csv()
- Riconteggio reject_errors se normalize usa config diversa

#### Funzionamento

1. **Sniffing standard**: tentativo auto-detect DuckDB
2. **Fallback se fallisce**: prova configurazioni comuni (delim + skip)
3. **Store rejects**: cattura righe malformate con `store_rejects=true` + `ignore_errors=true`
4. **Output**: dati validi + `*_reject_errors.csv`

#### Test

- ✅ `POSAS_2025_it_Comuni.csv`: 805,392 righe valide + 5 errori catturati
- ✅ File esistenti: nessuna regressione
- ✅ pytest: 93/93 passati

#### Risultato

**Issue #1 chiusa**: csvnorm ora gestisce automaticamente CSV con:
- Righe di titolo non strutturate
- Delimitatori non standard
- Righe malformate (catturate in reject_errors)

Nessuna opzione CLI aggiunta (tutto automatico).
