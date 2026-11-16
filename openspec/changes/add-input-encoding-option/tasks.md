# Tasks: add-input-encoding-option

## 1. CLI

- [ ] 1.1 Add `-e/--encoding NAME` to the parser in `cli.py`, validated with `codecs.lookup`; invalid name → error on stderr, exit 1
- [ ] 1.2 Test: invalid name exits 1 with a clear message; valid aliases (`latin-1`, `windows-1252`) are accepted

## 2. Pipeline

- [ ] 2.1 Pass the declared encoding through `process_csv` to `_prepare_working_file`; skip `detect_encoding` when set
- [ ] 2.2 Convert with the declared encoding; on `UnicodeDecodeError` stop with exit 1 and report encoding, byte offset and byte
- [ ] 2.3 Compressed inputs: implement the option chosen in `design.md`
- [ ] 2.4 Tests (subprocess): `test/windows1252_quotes.csv -e cp1252` gives `“Libro”` and `10€`; Italian cp1252 sample with `ì` decodes correctly; cp850 sample with `-e cp850`; stdin with `-e`; undecodable input with declared encoding exits 1; without `-e` output unchanged

## 3. Summary and docs

- [ ] 3.1 Summary shows `<enc> → UTF-8 (declared)`; test on file mode and stdout mode (stderr)
- [ ] 3.2 README: option table and a short section on when to use `--encoding`, with the detection limits measured in the proposal
- [ ] 3.3 `--help` epilog example

## 4. Validation

- [ ] 4.1 `openspec validate add-input-encoding-option --strict`
- [ ] 4.2 Full test suite, mypy, smoke test `uv tool install --reinstall --force .` then `csvnorm -v`
