# Test CSV Fixtures

Small fixtures used by `make test` and for quick manual checks.

## Files

- `utf8_basic.csv`  
  UTF-8, comma-delimited, simple headers and data.

- `latin1_semicolon.csv`  
  ISO-8859-1 (Latin-1), semicolon-delimited, includes accented characters.

- `windows1252_quotes.csv`  
  Windows-1252, comma-delimited, includes smart quotes and euro symbol.

- `utf8_sig_bom.csv`  
  UTF-8 with BOM (`utf-8-sig`) to verify BOM handling.

- `pipe_mixed_headers.csv`  
  UTF-8, pipe-delimited, headers with spaces and mixed case.

- `malformed_rows.csv`  
  UTF-8, inconsistent column counts to trigger `reject_errors.csv`.

- `Trasporto Pubblico Locale Settore Pubblico Allargato - Indicatore 2000-2020 Trasferimenti Correnti su Entrate Correnti.csv`  
  Real-world sample file for integration-style testing.
