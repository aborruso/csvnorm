# Design: `--encoding` option

## Context

Updated 2026-11-23, after release 1.4.0. Plain local files, stdin (saved to a temp file), downloaded URLs and zip inputs (extracted to a temp file) all go through `_handle_local_encoding` in `core.py`, which calls `detect_and_convert` in `encoding.py`: detection (whole file up to 50 MiB, sampled above), chunked strict conversion with `convert_to_utf8`, one fallback to whole-file detection if the conversion fails. Only gzip inputs skip this step: DuckDB reads them directly and assumes UTF-8.

## Decisions

### Declared encoding replaces detection, never falls back

With `--encoding`, `detect_encoding()` is not called. If decoding fails, the run stops with exit code 2 (the code for runs that could not complete, see change `agent-readable-cli`). A silent fallback to detection would hide exactly the error the user tried to avoid.

### Validation before any work

`codecs.lookup(name)` runs at argument parsing time. Aliases accepted by Python (`latin-1`, `iso-8859-1`, `windows-1252`) are valid; the summary shows the normalized name.

### UTF-8 family

If the declared encoding is UTF-8 compatible (`utf-8`, `ascii`, `utf-8-sig`), no conversion file is written, as today. The file is still checked to decode as declared; on failure the run stops.

### Error message on undecodable input

The message reports the declared encoding, the byte offset and the offending byte, for example: `Input is not valid cp1252: byte 0x81 at offset 1234`. It suggests running without `--encoding` to see the detected one.

### Compressed inputs (decided 2026-11-23)

With `--encoding`, a gzip input is decompressed in chunks to a temp file and then converted like a local file, so every Python codec works. Without `--encoding` gzip keeps going straight to DuckDB. Zip inputs need nothing new: they are already extracted to a temp file.

### Short flag (decided 2026-11-23)

`-e` is the short form of `--encoding`.

### `--check` with `--encoding` (decided 2026-11-23)

Allowed: validation reads the input decoded with the declared encoding.

### Implementation notes

- `--encoding` skips `detect_and_convert` entirely and calls `convert_to_utf8` with the declared name; there is no fallback.
- For the UTF-8 family no converted file is written, but the input is checked to decode in chunks, with the same `file_offset` reporting as the conversion. A UTF-8 file with BOM declared as `utf-8` is handled as today.
- An invalid name exits with code 2 after argument parsing, like other invalid command lines.

## Risks

- A wrong declaration that still decodes (e.g. cp1250 declared for a cp1252 file) produces wrong characters without errors. This is the user's choice; the summary label `(declared)` makes it visible.
