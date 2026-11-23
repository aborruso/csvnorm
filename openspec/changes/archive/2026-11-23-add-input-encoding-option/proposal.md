# Change: Add `--encoding` option to declare the input encoding

## Why

Automatic detection with `charset_normalizer` (3.4.7) is unreliable for the single-byte encodings csvnorm users meet most. Measured on 2026-11-16, on synthetic CSV samples of 150 rows (7-9 KB):

- Italian cp1252 detected as `cp1258` (Vietnamese): `ì` is corrupted
- Italian cp850 detected as `cp1250`
- Polish cp1250 detected as `cp1252`
- `test/windows1252_quotes.csv` detected as `cp437`: `“Libro”` becomes `ôLibroö`, `10€` becomes `10Ç`
- 200,000 ASCII rows plus one latin1 byte detected as `cp1006`, then normalization fails

Heuristic tie-breaking (shipped in 1.3.0 for equal scores) helps only some cases, and every stronger heuristic penalizes some other encoding. When the user knows the encoding, the only reliable fix is to let them say it.

Update 2026-11-22 (change `speed-up-large-files`, release 1.4.0): files up to 50 MiB are still detected on the whole file, so the cases above are unchanged. Above 50 MiB detection uses a sample with every non-ASCII byte value and prefers Western codecs: it is fast (1.2 s instead of 94 s on 826 MB) but can return a Western codec for Turkish, Polish, Baltic or Hungarian text without any error, which is one more case where `--encoding` is the reliable fix.

## What Changes

- New option `-e/--encoding <name>`: the input is decoded with the declared encoding and automatic detection is skipped.
- The name is validated as a Python codec before processing; an unknown name exits with code 2 and a clear error.
- If the input bytes cannot be decoded with the declared encoding, csvnorm exits with code 2 and reports the byte offset of the first failure; it never falls back to detection silently.
- The processing summary shows the encoding as declared (e.g. `cp1252 → UTF-8 (declared)`) instead of detected.
- Works with local files, stdin (`-`) and remote URLs (downloaded before processing). Compressed inputs: see `design.md`.
- `--fix-mojibake` keeps working and runs after the declared decoding, as today after detection.
- Without `--encoding` the behavior is unchanged.

## Impact

- Affected specs: `encoding-detection`
- Affected code: `src/csvnorm/cli.py` (option), `src/csvnorm/core.py` (`process_csv`, `_prepare_working_file`, `_handle_local_encoding`), `src/csvnorm/encoding.py` (codec validation), `src/csvnorm/ui.py` (summary label), README
- Not breaking: the option is new and optional
- Target release: after 1.3.0
