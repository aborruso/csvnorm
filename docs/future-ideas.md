# Future Ideas

## Product Messaging: "Almost-good" CSVs (English)

### Short claims (hero / banner)
- "From almost-good CSVs to machine-ready."
- "Turn 'readable' into 'reliable'."
- "Step zero for public CSVs."
- "Normalize the almost-good, not the broken."
- "Make CSVs consistent before you analyze."

### Supporting lines (sub-headline / section)
- "csvnorm isn’t a heavy cleaning tool. It normalizes the CSVs that look fine but aren’t machine-ready."
- "A lightweight normalization step between 'opens in Excel' and 'works in a pipeline.'"
- "For real-world CSVs: readable, but inconsistent."

### README paragraph (positioning)
csvnorm isn’t built to rescue broken CSVs. It’s for the many CSVs that look okay but aren’t machine-ready: mixed
Delimiters, uncertain encodings, messy headers, or occasional malformed rows. It provides a consistent, validated
baseline so you can start exploration or ETL with fewer surprises.

## Lenient Mode for Robust CSVs

**Source**: [DuckDB CSV Reader and Pollock Robustness Benchmark](https://duckdb.org/2025/04/16/duckdb-csv-pollock-benchmark)

### Ideas from the article

DuckDB reached the #1 score (9.599/10) in the Pollock Benchmark using specific parameters to handle "dirty" CSVs:

**DuckDB parameters not currently used**:
- `strict_mode=false`: handles unescaped quotes, extra columns, mixed newlines
- `null_padding=true`: fills missing cells with NULL in inconsistent rows
- `ignore_errors=true`: skips problematic rows (alternative to `store_rejects`)

**Common error categories identified**:
1. ✅ Inconsistent cell counts (already handled via `store_rejects`)
2. ✅ Mixed newlines (DuckDB handles by default)
3. ❓ Multiple headers (not explicitly handled)
4. ❓ Incorrect quoting (may cause rejects)
5. ❓ Multibyte delimiters (not tested)
6. ❓ Multiple tables in one file (not handled)

### Implementation proposal

**CLI flag**:
```bash
csvnorm input.csv --lenient  # Maximum tolerance for dirty CSVs
```

**Implementation in validation.py**:
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

### Advantages

- `null_padding=true`: fixes inconsistent rows without generating rejects
- `strict_mode=false`: improves robustness on real CSVs with malformed quotes
- Keeps `store_rejects=true` for transparency (vs `ignore_errors`)

### Trade-offs

- Could introduce ambiguity (NULL vs intentionally missing data)
- More permissive = less strict validation
