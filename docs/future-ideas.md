# Future Ideas

## Lenient Mode per CSV Robusti

**Fonte**: [DuckDB CSV Reader and Pollock Robustness Benchmark](https://duckdb.org/2025/04/16/duckdb-csv-pollock-benchmark)

### Spunti dall'articolo

DuckDB ha ottenuto il punteggio #1 (9.599/10) nel Pollock Benchmark usando parametri specifici per gestire CSV "sporchi":

**Parametri DuckDB non usati attualmente**:
- `strict_mode=false`: gestisce quote non escapate, colonne extra, newline misti
- `null_padding=true`: riempie con NULL le celle mancanti in righe inconsistenti
- `ignore_errors=true`: salta righe problematiche (alternativa a `store_rejects`)

**Categorie di errori comuni identificate**:
1. ✅ Conteggi celle inconsistenti (già gestito via `store_rejects`)
2. ✅ Newline misti (DuckDB li gestisce di default)
3. ❓ Header multipli (non gestito esplicitamente)
4. ❓ Quote incorrette (potrebbero causare rejects)
5. ❓ Delimitatori multibyte (non testato)
6. ❓ Tabelle multiple in un file (non gestito)

### Proposta implementazione

**Flag CLI**:
```bash
csvnorm input.csv --lenient  # Massima tolleranza per CSV sporchi
```

**Implementazione in validation.py**:
```python
def validate_csv(..., lenient=False):
    if lenient:
        conn.execute(f"""
            SELECT * FROM read_csv('{input_path}',
                delim='{delimiter}',
                strict_mode=false,
                null_padding=true,
                all_varchar=true,
                store_rejects=true)
        """)
```

### Vantaggi

- `null_padding=true`: risolve righe inconsistenti senza generare rejects
- `strict_mode=false`: migliora robustness su CSV reali con quote malformate
- Mantiene `store_rejects=true` per trasparenza (vs `ignore_errors`)

### Trade-off

- Potrebbe introdurre ambiguità (NULL vs dato mancante intenzionale)
- Più permissivo = meno validazione stretta
