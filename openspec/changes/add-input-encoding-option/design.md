# Design: `--encoding` option

## Context

Today the encoding step runs only for plain local files (`_prepare_working_file` in `core.py`). Remote URLs are downloaded first and then treated as local files. Compressed inputs (gzip, zip) skip detection: DuckDB reads them directly and assumes UTF-8.

## Decisions

### Declared encoding replaces detection, never falls back

With `--encoding`, `detect_encoding()` is not called. If decoding fails, the run stops with exit code 1. A silent fallback to detection would hide exactly the error the user tried to avoid.

### Validation before any work

`codecs.lookup(name)` runs at argument parsing time. Aliases accepted by Python (`latin-1`, `iso-8859-1`, `windows-1252`) are valid; the summary shows the normalized name.

### UTF-8 family

If the declared encoding is UTF-8 compatible (`utf-8`, `ascii`, `utf-8-sig`), no conversion file is written, as today. The file is still checked to decode as declared; on failure the run stops.

### Error message on undecodable input

The message reports the declared encoding, the byte offset and the offending byte, for example: `Input is not valid cp1252: byte 0x81 at offset 1234`. It suggests running without `--encoding` to see the detected one.

## Open points (to settle before apply)

- **Compressed inputs.** Options: (1) decompress to a temp file and convert like a local file; (2) pass the encoding to DuckDB `read_csv(encoding=...)`, which natively supports only `utf-8`, `utf-16` and `latin-1` (more through the `encodings` extension); (3) reject `--encoding` with compressed input for now. Proposal: (1), it reuses the existing path and supports every Python codec.
- **Short flag `-e`.** Free today. Proposal: use it.
- **`--check` with `--encoding`.** Proposal: allowed; validation uses the declared encoding.

## Risks

- A wrong declaration that still decodes (e.g. cp1250 declared for a cp1252 file) produces wrong characters without errors. This is the user's choice; the summary label `(declared)` makes it visible.
