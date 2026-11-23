# Tasks: add-input-encoding-option

## 1. CLI

- [x] 1.1 Add `-e/--encoding NAME` to the parser in `cli.py`, validated with `codecs.lookup`; invalid name → error on stderr, exit 2 (exit 1 until change agent-readable-cli)
- [x] 1.2 Test: invalid name exits 2 with a clear message; valid aliases (`latin-1`, `windows-1252`) are accepted

## 2. Pipeline

- [x] 2.1 Pass the declared encoding through `process_csv` to `_handle_local_encoding`; skip `detect_and_convert` when set; UTF-8 family: chunked decode check, no converted file
- [x] 2.2 Convert with the declared encoding; on `UnicodeDecodeError` stop with exit 2 and report encoding, byte offset and byte
- [x] 2.3 gzip with `--encoding`: decompress in chunks to a temp file, then convert; without `--encoding` unchanged. Zip: nothing new (already extracted)
- [x] 2.4 Tests (subprocess): `test/windows1252_quotes.csv -e cp1252` gives `“Libro”` and `10€`; Italian cp1252 sample with `ì` decodes correctly; cp850 sample with `-e cp850`; stdin with `-e`; gzip and zip with `-e`; `--check -e`; undecodable input with declared encoding exits 2; without `-e` output unchanged

## 3. Summary and docs

- [x] 3.1 Summary shows `<enc> → UTF-8 (declared)`; test on file mode and stdout mode (stderr)
- [x] 3.2 README: option table and a short section on when to use `--encoding`, with the detection limits measured in the proposal
- [x] 3.3 `--help` epilog example

## 4. Validation

- [x] 4.1 `openspec validate add-input-encoding-option --strict`
- [x] 4.2 Full test suite, mypy, smoke test `uv tool install --reinstall --force .` then `csvnorm -v`
